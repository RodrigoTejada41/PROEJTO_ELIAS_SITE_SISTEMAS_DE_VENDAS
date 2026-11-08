"""PostgreSQL authentication and revocable sessions for the local pilot."""

from hashlib import sha256
from hmac import compare_digest
import logging
from secrets import token_bytes, token_urlsafe

from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
from cryptography.exceptions import InvalidTag
import psycopg

from app import mfa
from app.bootstrap_master import hash_master_password, validate_username
from app.recover_master import replace_master_password

SESSION_SECONDS = 8 * 60 * 60
DEFAULT_LOCALE = "es"
PASSWORDS = PasswordHasher()
DUMMY_HASH = PASSWORDS.hash(token_urlsafe(32))


def digest(token: str) -> bytes:
    return sha256(token.encode()).digest()


def allow_password_attempt(address: str) -> bool:
    with psycopg.connect() as connection:
        attempt = connection.execute(
            """
            INSERT INTO identity_login_limits AS limits (address, attempts, expires_at)
            VALUES (%s, 1, now() + interval '5 minutes')
            ON CONFLICT (address) DO UPDATE SET
                attempts = CASE WHEN limits.expires_at <= now() THEN 1 ELSE limits.attempts + 1 END,
                expires_at = CASE WHEN limits.expires_at <= now()
                                  THEN excluded.expires_at ELSE limits.expires_at END
            WHERE limits.expires_at <= now() OR limits.attempts < 5
            RETURNING attempts
            """,
            (address,),
        ).fetchone()
        return attempt is not None


def login(username: str, password: str, address: str, previous: str | None):
    if not allow_password_attempt(address):
        return None, 429

    # Commit the attempt before hashing so concurrent requests share the same limit.
    # The account lock serializes password recovery with verification and session creation.
    with psycopg.connect() as connection:
        user = connection.execute(
            """
            SELECT id, password_hash, totp_secret IS NOT NULL, totp_activation_hash IS NOT NULL,
                   totp_activation_expires_at > now()
            FROM identity_users WHERE username = %s AND active FOR SHARE
            """,
            (username,),
        ).fetchone()
        try:
            PASSWORDS.verify(user[1] if user else DUMMY_HASH, password)
        except VerifyMismatchError:
            return None, 401
        if user is None:
            return None, 401

        if user[2] or (user[3] and user[4]):
            token = token_urlsafe(32)
            challenge = connection.execute(
                """
                INSERT INTO identity_mfa_challenges AS pending
                    (user_id, token_hash, password_version, expires_at)
                VALUES (%s, %s, %s, now() + interval '5 minutes')
                ON CONFLICT (user_id) DO UPDATE SET
                    token_hash = excluded.token_hash, password_version = excluded.password_version,
                    setup_secret = NULL,
                    attempts = CASE WHEN pending.expires_at <= now() THEN 0 ELSE pending.attempts END,
                    expires_at = CASE WHEN pending.expires_at <= now() THEN excluded.expires_at
                                      ELSE pending.expires_at END
                WHERE pending.expires_at <= now() OR pending.attempts < 5
                RETURNING user_id
                """,
                (user[0], digest(token), digest(user[1])),
            ).fetchone()
            return (token, 202) if challenge else (None, 429)
        if mfa.required() or user[3]:
            return None, 403
        return create_session(connection, user[0], previous), 303


def create_session(connection, user_id, previous, mfa_verified=False):
    token = token_urlsafe(32)
    if previous:
        connection.execute("DELETE FROM identity_sessions WHERE token_hash = %s", (digest(previous),))
    connection.execute(
        """
        INSERT INTO identity_sessions (token_hash, user_id, expires_at, mfa_verified)
        VALUES (%s, %s, now() + %s * interval '1 second', %s)
        """,
        (digest(token), user_id, SESSION_SECONDS, mfa_verified),
    )
    connection.execute("INSERT INTO identity_audit (event, user_id) VALUES ('login', %s)", (user_id,))
    return token


def issue_mfa_activation(username):
    validate_username(username)
    mfa.cipher()
    code = token_urlsafe(24)
    with psycopg.connect() as connection:
        row = connection.execute(
            """
            UPDATE identity_users SET totp_activation_hash = %s,
                   totp_activation_expires_at = now() + interval '24 hours'
            WHERE username = %s AND active AND totp_secret IS NULL
            RETURNING id
            """,
            (digest(code), username),
        ).fetchone()
        if not row:
            raise ValueError("Conta ativa sem autenticador não encontrada.")
        connection.execute("DELETE FROM identity_mfa_challenges WHERE user_id = %s", (row[0],))
        connection.execute("DELETE FROM identity_sessions WHERE user_id = %s", (row[0],))
        connection.execute(
            "INSERT INTO identity_audit (event, user_id, actor_db_role) VALUES ('mfa_activation_issued', %s, current_user)",
            (row[0],),
        )
    return code


def second_factor_state(challenge):
    with psycopg.connect() as connection:
        row = connection.execute(
            """
            SELECT account.id, account.username, account.password_hash, pending.password_version,
                   account.totp_secret IS NOT NULL,
                   account.totp_activation_expires_at > now(), pending.setup_secret
            FROM identity_mfa_challenges pending JOIN identity_users account ON account.id = pending.user_id
            WHERE pending.token_hash = %s AND account.active AND pending.expires_at > now()
            """,
            (digest(challenge),),
        ).fetchone()
    if not row or not compare_digest(digest(row[2]), row[3]):
        return "expired", None
    if row[4]:
        return "verify", None
    if not row[5]:
        return "expired", None
    if row[6] is None:
        return "activate", None
    try:
        return "setup", mfa.setup_image(mfa.decrypt(row[6], row[0]), row[1])
    except (InvalidTag, OSError, ValueError):
        logging.getLogger(__name__).error("Chave do segundo fator indisponível ou incompatível.")
        return "unavailable", None


def verify_second_factor(challenge, code, previous, activation_code=""):
    token_hash = digest(challenge)
    with psycopg.connect() as connection:
        user = connection.execute(
            """
            SELECT id, password_hash, totp_secret, totp_last_step, totp_activation_hash,
                   totp_activation_expires_at > now()
            FROM identity_users
            WHERE active AND id = (SELECT user_id FROM identity_mfa_challenges WHERE token_hash = %s)
            FOR UPDATE
            """,
            (token_hash,),
        ).fetchone()
        if not user or (user[2] is None and not user[5]):
            return None, 410
        pending = connection.execute(
            """
            SELECT attempts, setup_secret FROM identity_mfa_challenges
            WHERE user_id = %s AND token_hash = %s AND expires_at > now() AND password_version = %s
            FOR UPDATE
            """,
            (user[0], token_hash, digest(user[1])),
        ).fetchone()
        if pending is None:
            return None, 410
        if pending[0] >= 5:
            return None, 429
        enrolling = user[2] is None
        try:
            if enrolling and pending[1] is None:
                if user[4] and compare_digest(digest(activation_code.strip()), user[4]):
                    connection.execute(
                        "UPDATE identity_mfa_challenges SET setup_secret = %s WHERE user_id = %s",
                        (mfa.encrypt(token_bytes(20), user[0]), user[0]),
                    )
                    return None, 202
                return reject_second_factor(connection, user[0], pending[0])
            secret = mfa.decrypt(pending[1] if enrolling else user[2], user[0])
        except (InvalidTag, OSError, ValueError):
            logging.getLogger(__name__).error("Chave do segundo fator indisponível ou incompatível.")
            return None, 503
        step = mfa.matching_step(secret, code, user[3])
        if step is None:
            return reject_second_factor(connection, user[0], pending[0])
        if enrolling:
            connection.execute(
                """
                UPDATE identity_users SET totp_secret = %s, totp_last_step = %s,
                       totp_activation_hash = NULL, totp_activation_expires_at = NULL WHERE id = %s
                """,
                (pending[1], step, user[0]),
            )
            connection.execute("DELETE FROM identity_sessions WHERE user_id = %s", (user[0],))
            connection.execute("INSERT INTO identity_audit (event, user_id) VALUES ('mfa_enrolled', %s)", (user[0],))
        else:
            connection.execute("UPDATE identity_users SET totp_last_step = %s WHERE id = %s", (step, user[0]))
        connection.execute("DELETE FROM identity_mfa_challenges WHERE user_id = %s", (user[0],))
        return create_session(connection, user[0], previous, mfa_verified=True), 303


def reject_second_factor(connection, user_id, attempts):
    connection.execute("UPDATE identity_mfa_challenges SET attempts = attempts + 1 WHERE user_id = %s", (user_id,))
    return None, 429 if attempts == 4 else 401


def session_account(token: str) -> tuple[int, str] | None:
    with psycopg.connect() as connection:
        return connection.execute(
            """
            SELECT account.id, account.role FROM identity_sessions AS session
            JOIN identity_users AS account ON account.id = session.user_id
            WHERE session.token_hash = %s AND session.expires_at > now() AND account.active
              AND (session.mfa_verified OR (NOT %s AND account.totp_secret IS NULL
                                            AND account.totp_activation_hash IS NULL))
            """,
            (digest(token), mfa.required()),
        ).fetchone()


def logout(token: str) -> None:
    with psycopg.connect() as connection:
        connection.execute(
            """
            WITH revoked AS (
                DELETE FROM identity_sessions WHERE token_hash = %s RETURNING user_id
            )
            INSERT INTO identity_audit (event, user_id) SELECT 'logout', user_id FROM revoked
            """,
            (digest(token),),
        )

def list_operators():
    with psycopg.connect() as connection:
        return connection.execute(
            "SELECT id, username, active FROM identity_users WHERE role = 'OPERATOR' ORDER BY username"
        ).fetchall()


def create_operator(actor_id: int, username: str, password: str) -> bool:
    validate_username(username)
    password_hash = hash_master_password(password)
    with psycopg.connect() as connection:
        row = connection.execute(
            """
            INSERT INTO identity_users (username, password_hash, role)
            VALUES (%s, %s, 'OPERATOR') ON CONFLICT (username) DO NOTHING
            RETURNING id
            """,
            (username, password_hash),
        ).fetchone()
        if row is None:
            return False
        connection.execute(
            "INSERT INTO identity_audit (event, user_id, actor_user_id) VALUES ('operator_created', %s, %s)",
            (row[0], actor_id),
        )
        return True


def deactivate_operator(actor_id: int, user_id: int) -> None:
    with psycopg.connect() as connection:
        changed = connection.execute(
            """
            UPDATE identity_users SET active = false
            WHERE id = %s AND role = 'OPERATOR' AND active RETURNING id
            """,
            (user_id,),
        ).fetchone()
        if changed is None:
            return
        connection.execute("DELETE FROM identity_sessions WHERE user_id = %s", (user_id,))
        connection.execute(
            "INSERT INTO identity_audit (event, user_id, actor_user_id) VALUES ('operator_deactivated', %s, %s)",
            (user_id, actor_id),
        )

def preferred_locale(token: str) -> str:
    with psycopg.connect() as connection:
        row = connection.execute(
            """
            SELECT account.preferred_locale FROM identity_sessions session
            JOIN identity_users account ON account.id = session.user_id
            WHERE session.token_hash = %s AND session.expires_at > now() AND account.active
            """, (digest(token),),
        ).fetchone()
        return row[0] if row else DEFAULT_LOCALE


def set_locale(token: str, locale: str) -> None:
    if locale not in ("pt", "es"):
        raise ValueError("locale")
    with psycopg.connect() as connection:
        connection.execute(
            """
            UPDATE identity_users account SET preferred_locale = %s
            FROM identity_sessions session
            WHERE session.user_id = account.id AND session.token_hash = %s
              AND session.expires_at > now() AND account.active
            """, (locale, digest(token)),
        )


def create_dev(username: str, password: str) -> None:
    validate_username(username)
    password_hash = hash_master_password(password)
    with psycopg.connect() as connection:
        row = connection.execute(
            """
            INSERT INTO identity_users (username, password_hash, role)
            VALUES (%s, %s, 'DEV')
            ON CONFLICT DO NOTHING RETURNING id
            """,
            (username, password_hash),
        ).fetchone()
        if row is None:
            raise ValueError("A conta DEV ou o nome de usuário já existe.")
        connection.execute(
            """
            INSERT INTO identity_audit (event, user_id, actor_db_role)
            VALUES ('dev_created', %s, current_user)
            """,
            (row[0],),
        )


def reset_master_as_dev(dev_id, dev_password, password, address):
    if not allow_password_attempt(address):
        return 429, "limited"
    if not 15 <= len(password) <= 128:
        return 400, "master_password_invalid"
    if not 15 <= len(dev_password) <= 128:
        return 403, "dev_password_invalid"
    with psycopg.connect() as connection:
        row = connection.execute(
            """
            SELECT password_hash FROM identity_users
            WHERE id = %s AND role = 'DEV' AND active FOR SHARE
            """,
            (dev_id,),
        ).fetchone()
        try:
            if row is None or not PASSWORDS.verify(row[0], dev_password):
                return 403, "dev_password_invalid"
        except VerifyMismatchError:
            return 403, "dev_password_invalid"
        user_id = replace_master_password(connection, hash_master_password(password))
        if user_id is None:
            return 409, "master_missing"
        connection.execute(
            """
            INSERT INTO identity_audit (event, user_id, actor_user_id)
            VALUES ('master_password_reset_by_dev', %s, %s)
            """,
            (user_id, dev_id),
        )
    return 303, None
