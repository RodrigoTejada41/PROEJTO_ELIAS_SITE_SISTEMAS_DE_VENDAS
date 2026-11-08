"""Reset the existing MASTER password from an authorized administrative terminal."""

import argparse
from getpass import GetPassWarning, getpass
import warnings

import psycopg

from app.bootstrap_master import hash_master_password


def replace_master_password(connection, password_hash):
    row = connection.execute(
        """
        UPDATE identity_users SET password_hash = %s
        WHERE role = 'MASTER'
        RETURNING id
        """,
        (password_hash,),
    ).fetchone()
    if row is None:
        return None
    user_id = row[0]
    connection.execute("DELETE FROM identity_sessions WHERE user_id = %s", (user_id,))
    return user_id


def recover_master(password: str) -> None:
    password_hash = hash_master_password(password)
    with psycopg.connect() as connection:
        user_id = replace_master_password(connection, password_hash)
        if user_id is None:
            raise ValueError("A conta MASTER ainda não existe.")
        connection.execute(
            """
            INSERT INTO identity_audit (event, user_id, actor_db_role)
            VALUES ('master_password_recovered', %s, current_user)
            """,
            (user_id,),
        )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.parse_args()
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", GetPassWarning)
            password = getpass("Nova senha do MASTER: ")
            if password != getpass("Confirme a nova senha do MASTER: "):
                raise ValueError("As senhas não coincidem.")
        recover_master(password)
    except (GetPassWarning, EOFError):
        parser.exit(1, "Execute a recuperação em um terminal interativo sem eco.\n")
    except ValueError as error:
        parser.exit(1, f"{error}\n")
    except psycopg.Error:
        parser.exit(1, "Falha no banco. Confira a conexão, as permissões e as migrações de identidade.\n")
    print("Senha do MASTER redefinida e sessões revogadas.")


if __name__ == "__main__":
    main()
