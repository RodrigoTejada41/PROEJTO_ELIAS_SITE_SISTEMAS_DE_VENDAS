"""Enroll or replace an authenticator from an authorized private terminal."""

import argparse
from base64 import b32encode
from getpass import GetPassWarning, getpass
from secrets import token_bytes
import sys
import warnings

import psycopg

from app import mfa
from app.bootstrap_master import validate_username
from app.identity import issue_mfa_activation


def enroll(username, secret, code):
    validate_username(username)
    step = mfa.matching_step(secret, code)
    if step is None:
        raise ValueError("Código do novo autenticador inválido.")
    with psycopg.connect() as connection:
        account = connection.execute(
            "SELECT id, totp_secret IS NOT NULL FROM identity_users WHERE username = %s AND active FOR UPDATE",
            (username,),
        ).fetchone()
        if account is None:
            raise ValueError("Conta ativa não encontrada.")
        user_id, replacing = account
        connection.execute(
            """
            UPDATE identity_users SET totp_secret = %s, totp_last_step = %s,
                   totp_activation_hash = NULL, totp_activation_expires_at = NULL WHERE id = %s
            """,
            (mfa.encrypt(secret, user_id), step, user_id),
        )
        connection.execute("DELETE FROM identity_mfa_challenges WHERE user_id = %s", (user_id,))
        connection.execute("DELETE FROM identity_sessions WHERE user_id = %s", (user_id,))
        connection.execute(
            "INSERT INTO identity_audit (event, user_id, actor_db_role) VALUES (%s, %s, current_user)",
            ("mfa_replaced" if replacing else "mfa_enrolled", user_id),
        )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("username")
    parser.add_argument("--issue-activation", action="store_true", help="emitir código para o primeiro acesso")
    args = parser.parse_args()
    if not sys.stdin.isatty() or not sys.stdout.isatty():
        parser.exit(1, "Use um terminal privado e interativo.\n")
    try:
        username = args.username.strip().lower()
        validate_username(username)
        if args.issue_activation:
            code = issue_mfa_activation(username)
            print("Código de ativação válido por 24 horas. Entregue por um canal separado da senha.")
            print(code)
            return
        mfa.cipher()
        secret = token_bytes(20)
        print("Adicione uma conta do tipo baseado em tempo ao seu aplicativo autenticador.")
        print(f"Conta: Esther Beauty 777 / {username}")
        print(f"Chave de configuração: {b32encode(secret).decode('ascii')}")
        with warnings.catch_warnings():
            warnings.simplefilter("error", GetPassWarning)
            enroll(username, secret, getpass("Código de seis dígitos do novo autenticador: ").strip())
    except (GetPassWarning, EOFError):
        parser.exit(1, "Use um terminal privado com entrada sem eco.\n")
    except ValueError as error:
        parser.exit(1, f"{error}\n")
    except (OSError, psycopg.Error):
        parser.exit(1, "Falha no cadastro. Confira a chave e a conexão ao banco.\n")
    print("Autenticador cadastrado. Aguarde o próximo código para entrar.")


if __name__ == "__main__":
    main()
