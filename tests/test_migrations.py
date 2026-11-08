"""Verify migration history, repeatability and rollback in an isolated schema."""

import os
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase, skipUnless
from unittest.mock import patch
from uuid import uuid4

import psycopg
from psycopg import sql

from app import migrate

DSN = os.getenv("IDENTITY_TEST_DSN")


@skipUnless(DSN, "Configure IDENTITY_TEST_DSN para executar em PostgreSQL.")
class MigrationIntegrationTest(TestCase):
    def test_repeat_checksum_and_atomic_failure(self):
        connect = psycopg.connect
        schema = sql.Identifier(f"migration_test_{uuid4().hex}")

        def isolated_connection():
            return connect(DSN, options=f"-c search_path={schema.as_string()}")

        with connect(DSN, autocommit=True) as admin:
            admin.execute(sql.SQL("CREATE SCHEMA {}").format(schema))
            try:
                with TemporaryDirectory() as directory:
                    root = Path(directory)
                    scripts = root / "migrations"
                    scripts.mkdir()
                    script = scripts / "001_test.sql"
                    script.write_text("BEGIN; CREATE TABLE sample (id int); COMMIT;", encoding="ascii")
                    with patch.object(migrate, "__file__", str(root / "app" / "migrate.py")):
                        with patch.object(migrate.psycopg, "connect", side_effect=isolated_connection):
                            migrate.main()
                            migrate.main()
                            with isolated_connection() as connection:
                                self.assertEqual(connection.execute("SELECT count(*) FROM schema_migrations").fetchone()[0], 1)
                            script.write_text("BEGIN; CREATE TABLE changed (id int); COMMIT;", encoding="ascii")
                            with self.assertRaises(RuntimeError):
                                migrate.main()
                            script.write_text("BEGIN; CREATE TABLE sample (id int); COMMIT;", encoding="ascii")
                            (scripts / "002_fail.sql").write_text(
                                "BEGIN; CREATE TABLE partial (id int); SELECT 1/0; COMMIT;", encoding="ascii"
                            )
                            with self.assertRaises(psycopg.errors.DivisionByZero):
                                migrate.main()
                            with isolated_connection() as connection:
                                self.assertIsNone(connection.execute("SELECT to_regclass('partial')").fetchone()[0])
                                self.assertEqual(connection.execute("SELECT count(*) FROM schema_migrations").fetchone()[0], 1)
            finally:
                admin.execute(sql.SQL("DROP SCHEMA {} CASCADE").format(schema))
