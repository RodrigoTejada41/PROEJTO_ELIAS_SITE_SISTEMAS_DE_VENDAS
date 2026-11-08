"""Apply versioned SQL migrations atomically with a PostgreSQL advisory lock."""

from hashlib import sha256
from os import environ
from pathlib import Path

import psycopg


def main():
    with psycopg.connect() as connection:
        connection.execute("SELECT pg_advisory_xact_lock(510052026)")
        if connection.execute("SELECT to_regclass('schema_migrations')").fetchone()[0] is None:
            if connection.execute("SELECT to_regclass('identity_users')").fetchone()[0] is not None:
                raise RuntimeError("Banco existente sem histórico. Confira e adote as migrações antes de continuar.")
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS schema_migrations (
                name text PRIMARY KEY,
                checksum text NOT NULL,
                applied_at timestamptz NOT NULL DEFAULT now()
            )
            """
        )
        for path in sorted((Path(__file__).resolve().parents[1] / "migrations").glob("*.sql")):
            contents = path.read_bytes()
            checksum = sha256(contents).hexdigest()
            applied = connection.execute(
                "SELECT checksum FROM schema_migrations WHERE name = %s", (path.name,)
            ).fetchone()
            if applied:
                if applied[0] != checksum:
                    raise RuntimeError(f"Migração já aplicada foi alterada: {path.name}")
                continue
            script = contents.decode("ascii").strip()
            if not script.startswith("BEGIN;") or not script.endswith("COMMIT;"):
                raise RuntimeError(f"Envelope transacional inesperado: {path.name}")
            connection.execute(script[len("BEGIN;"):-len("COMMIT;")])
            connection.execute(
                "INSERT INTO schema_migrations (name, checksum) VALUES (%s, %s)",
                (path.name, checksum),
            )
            print(f"Aplicada {path.name}")
        if environ.get("ESTHER_PRODUCTION_GRANTS") == "1":
            connection.execute(Path(__file__).with_name("production_grants.sql").read_text(encoding="ascii"))


if __name__ == "__main__":
    main()
