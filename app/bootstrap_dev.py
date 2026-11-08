"""Provision the DEV account from an authorized local terminal."""

import argparse
from getpass import GetPassWarning, getpass
import warnings

import psycopg

from app.identity import create_dev


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("username")
    args = parser.parse_args()
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", GetPassWarning)
            password = getpass("Senha do DEV: ")
            if password != getpass("Confirme a senha: "):
                raise ValueError("As senhas não coincidem.")
        create_dev(args.username.strip().lower(), password)
    except (GetPassWarning, EOFError):
        parser.exit(1, "Use um terminal interativo sem eco.\n")
    except ValueError as error:
        parser.exit(1, f"{error}\n")
    except psycopg.Error:
        parser.exit(1, "Falha no banco. Confira a conexão e a migração de administração.\n")
    print("Conta DEV criada.")


if __name__ == "__main__":
    main()
