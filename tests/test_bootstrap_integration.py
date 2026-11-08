"""Integration test. Set IDENTITY_TEST_DSN to a disposable PostgreSQL database."""

from concurrent.futures import ThreadPoolExecutor
import os
from pathlib import Path
from unittest import TestCase, main, skipUnless
from unittest.mock import patch
from uuid import uuid4

from argon2 import PasswordHasher
import psycopg
from psycopg import sql

from app.bootstrap_master import create_master

DSN = os.getenv("IDENTITY_TEST_DSN")
MIGRATION = Path(__file__).resolve().parents[1] / "migrations/001_identity.sql"


@skipUnless(DSN, "Configure IDENTITY_TEST_DSN para executar em PostgreSQL.")
class BootstrapIntegrationTest(TestCase):
    def test_only_one_master_and_one_audit_record(self):
        schema = f"identity_test_{uuid4().hex}"
        connect = psycopg.connect
        password = "fixture-only-password"

        def isolated_connection():
            return connect(DSN, options=f"-c search_path={schema}")

        def provision(username):
            try:
                create_master(username, password)
            except ValueError as error:
                self.assertEqual(str(error), "A conta MASTER já foi criada.")
                return False
            return True

        with connect(DSN, autocommit=True) as admin:
            admin.execute(sql.SQL("CREATE SCHEMA {}").format(sql.Identifier(schema)))
            try:
                with isolated_connection() as connection:
                    connection.execute(MIGRATION.read_text(encoding="ascii"))

                with patch("app.bootstrap_master.psycopg.connect", side_effect=isolated_connection):
                    with ThreadPoolExecutor(max_workers=2) as pool:
                        results = list(pool.map(provision, ("master-one", "master-two")))
                self.assertCountEqual(results, [True, False])

                with isolated_connection() as connection:
                    users = connection.execute(
                        "SELECT id, role, password_hash FROM identity_users"
                    ).fetchall()
                    self.assertEqual(len(users), 1)
                    user_id, role, password_hash = users[0]
                    self.assertEqual(role, "MASTER")
                    self.assertTrue(PasswordHasher().verify(password_hash, password))
                    events = connection.execute(
                        "SELECT event, user_id FROM identity_audit"
                    ).fetchall()
                    self.assertEqual(events, [("master_created", user_id)])
            finally:
                admin.execute(sql.SQL("DROP SCHEMA {} CASCADE").format(sql.Identifier(schema)))


if __name__ == "__main__":
    main()
