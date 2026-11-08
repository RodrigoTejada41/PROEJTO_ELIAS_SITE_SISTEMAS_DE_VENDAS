import os
from pathlib import Path
from unittest import TestCase, skipUnless
from unittest.mock import patch
from uuid import uuid4

import psycopg
from psycopg import sql

from app import identity
from app.bootstrap_master import create_master

DSN = os.getenv("IDENTITY_TEST_DSN")


@skipUnless(DSN, "Configure IDENTITY_TEST_DSN para executar em PostgreSQL.")
class PostgresCase(TestCase):
    def setUp(self):
        self.connect = psycopg.connect
        self.schema = sql.Identifier(f"commercial_test_{uuid4().hex}")
        self.admin = self.connect(DSN, autocommit=True)
        self.admin.execute(sql.SQL("CREATE SCHEMA {}").format(self.schema))
        self.addCleanup(self.clean_schema)
        with self.isolated_connection() as connection:
            for migration in sorted((Path(__file__).resolve().parents[1] / "migrations").glob("*.sql")):
                connection.execute(migration.read_text(encoding="ascii"))
        patched = patch("psycopg.connect", side_effect=self.isolated_connection)
        patched.start()
        self.addCleanup(patched.stop)
        create_master("master-commercial", "master-fixture-password")
        with self.isolated_connection() as connection:
            self.actor_id = connection.execute("SELECT id FROM identity_users WHERE role = 'MASTER'").fetchone()[0]
        identity.create_operator(self.actor_id, "reader-commercial", "reader-fixture-password")
        master_token, _ = identity.login("master-commercial", "master-fixture-password", "127.0.0.1", None)
        operator_token, _ = identity.login("reader-commercial", "reader-fixture-password", "127.0.0.1", None)
        self.master = {"identity_session": master_token}
        self.reader = {"identity_session": operator_token}

    def isolated_connection(self, **kwargs):
        return self.connect(DSN, options=f"-c search_path={self.schema.as_string()}", **kwargs)

    def clean_schema(self):
        self.admin.execute(sql.SQL("DROP SCHEMA {} CASCADE").format(self.schema))
        self.admin.close()
