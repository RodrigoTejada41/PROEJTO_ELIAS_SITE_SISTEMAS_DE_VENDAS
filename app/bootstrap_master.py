"""Provision the first MASTER account from an administrative terminal."""

import argparse
from getpass import getpass
import re

from argon2 import PasswordHasher
import psycopg
from psycopg.errors import UniqueViolation


def hash_master_password(password: str) -> str:
    if not 15 <= len(password) <= 128:
        raise ValueError("A senha deve ter de 15 a 128 caracteres.")
    return PasswordHasher().hash(password)


def validate_username(username: str) -> None:
    if not re.fullmatch(r"[a-z0-9][a-z0-9._-]{2,63}", username):
        raise ValueError("Informe um usuário com 3 a 64 caracteres válidos.")


def create_master(username: str, password: str) -> None:
    validate_username(username)
    password_hash = hash_master_password(password)
    with psycopg.connect() as connection:
        row = connection.execute(
            """
            INSERT INTO identity_users (username, password_hash, role)
            VALUES (%s, %s, 'MASTER')
            ON CONFLICT (role) WHERE role = 'MASTER' DO NOTHING
            RETURNING id
            """,
            (username, password_hash),
        ).fetchone()
        if row is None:
            raise ValueError("A conta MASTER já foi criada.")
        connection.execute(
            "INSERT INTO identity_audit (event, user_id) VALUES (%s, %s)",
            ("master_created", row[0]),
        )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("username")
    args = parser.parse_args()
    try:
        password = getpass("Senha do MASTER: ")
        if password != getpass("Confirme a senha: "):
            raise ValueError("As senhas não coincidem.")
        create_master(args.username.strip().lower(), password)
    except ValueError as error:
        parser.exit(1, f"{error}\n")
    except UniqueViolation:
        parser.exit(1, "O nome de usuário já existe.\n")
    except psycopg.Error:
        parser.exit(1, "Falha no banco. Confira a conexão e a migração de identidade.\n")
    print("Conta MASTER criada.")


if __name__ == "__main__":
    main()
