"""Commercial contacts, reporting and audit HTTP regression checks."""

from concurrent.futures import ThreadPoolExecutor
import csv
from io import StringIO
import os
from pathlib import Path
from unittest import TestCase, skipUnless
from unittest.mock import patch
from uuid import uuid4

import psycopg
from psycopg import sql

from app import catalog, contacts, identity, inventory
from app.bootstrap_master import create_master
from test_login_integration import request, csrf
from db_case import PostgresCase

DSN = os.getenv("IDENTITY_TEST_DSN")


@skipUnless(DSN, "Configure IDENTITY_TEST_DSN para executar em PostgreSQL.")
class CommercialIntegrationTest(PostgresCase):
    def test_contacts_access_concurrent_reference_and_stale_edit(self):
        for kind in ("customers", "suppliers"):
            path = f"/contacts/{kind}"
            self.assertEqual(request(path)[0], 303)
            self.assertEqual(request(path, self.reader)[0], 200 if kind == "customers" else 403)
            self.assertEqual(request(path + "/new", self.reader)[0], 403)
            form = {"csrf": csrf(request(path + "/new", self.master)[2]), "name": "Demo contact",
                    "external_ref": " ext-001 ", "email": "demo@example.test"}
            self.assertEqual(request(path + "/new", self.master, {**form, "csrf": "invalid"})[0], 403)
            self.assertEqual(request(path + "/new", self.master, {**form, "email": "invalid"})[0], 400)
            self.assertEqual(request(path + "/new", self.master, form)[0], 303)
            self.assertEqual(request(path + "/new", self.master, {**form, "external_ref": "EXT-001"})[0], 409)
            party = contacts.list_parties(kind, True)[0][0]
            edit = {**form, "name": "Edited contact", "version": party["version"]}
            endpoint = f'{path}/{party["id"]}/edit'
            self.assertEqual(request(endpoint, self.master, edit)[0], 303)
            self.assertEqual(request(endpoint, self.master, edit)[0], 409)
            self.assertEqual(request(endpoint, self.reader, edit)[0], 403)
            endpoint = f'{path}/{party["id"]}/deactivate'
            for _ in range(2):
                self.assertEqual(request(endpoint, self.master, {"csrf": form["csrf"]})[0], 303)
            self.assertFalse(contacts.get_party(kind, party["id"])["active"])
            if kind == "customers":
                self.assertNotIn(b"Edited contact", request(path, self.reader)[2])
            with self.isolated_connection() as connection:
                events = connection.execute(
                    "SELECT action FROM commercial_party_audit WHERE party_id = %s ORDER BY id", (party["id"],)
                ).fetchall()
            self.assertEqual(events, [("created",), ("edited",), ("deactivated",)])

        def create_reference(_):
            try:
                contacts.create("customers", self.actor_id, contacts.details({"name": "Concurrent", "external_ref": "UNIQUE"}))
                return True
            except psycopg.errors.UniqueViolation:
                return False

        with ThreadPoolExecutor(max_workers=2) as pool:
            self.assertCountEqual(list(pool.map(create_reference, range(2))), [True, False])
        with self.assertRaises(psycopg.errors.ForeignKeyViolation):
            contacts.create("customers", -1, contacts.details({"name": "Rollback", "external_ref": "ROLLBACK"}))
        self.assertEqual(contacts.list_parties("customers", True, "ROLLBACK")[0], [])

    def test_report_csv_permissions_and_audit_secrecy(self):
        for code in ("RPT-A", "RPT-B"):
            catalog.create_sku(self.actor_id, code, catalog.sku_details({"description": "=1+1" if code == "RPT-A" else "Inactive"}))
        active_id = next(r["id"] for r in catalog.list_skus(True, "") if r["code"] == "RPT-A")
        inactive_id = next(r["id"] for r in catalog.list_skus(True, "") if r["code"] == "RPT-B")
        inventory.record(self.actor_id, active_id, 5, "Report receipt", str(uuid4()))
        inventory.record(self.actor_id, inactive_id, 2, "Inactive receipt", str(uuid4()))
        catalog.deactivate_sku(self.actor_id, inactive_id)

        for cookies, expected in ((self.master, 7), (self.reader, 5)):
            status, headers, body = request("/reports", cookies, query=b"status=all&export=true")
            self.assertEqual(status, 200)
            rows = list(csv.DictReader(StringIO(body.decode("utf-8-sig"))))
            self.assertEqual(sum(int(row["Saldo"]) for row in rows), expected)
            self.assertEqual(rows[0]["Descrição"], "'=1+1")
            self.assertIn(b"attachment", dict(headers)[b"content-disposition"])

        self.assertEqual(request("/audit", self.reader)[0], 403)
        self.assertIn(b"Acceso denegado", request("/audit", {**self.reader, "locale": "es"})[2])
        self.assertEqual(request("/audit")[0], 303)
        status, _, body = request("/audit", self.master, query=b"source=inventory")
        self.assertEqual(status, 200)
        self.assertIn(b"master-commercial", body)
        self.assertNotIn(b"password_hash", body)
        self.assertNotIn(self.master["identity_session"].encode(), body)
        self.assertEqual(request("/audit", self.master, query=b"start=2026-11-05&end=2026-01-01")[0], 400)
        self.assertEqual(request("/audit", self.master, query=b"start=2100-01-01&end=2100-01-02")[0], 200)

    def test_contact_pagination(self):
        for index in range(51):
            contacts.create("customers", self.actor_id, contacts.details({"name": f"Contact {index:03d}"}))
        rows, has_next = contacts.list_parties("customers", True, page=1)
        self.assertEqual(len(rows), 50)
        self.assertTrue(has_next)
        self.assertEqual(len(contacts.list_parties("customers", True, page=2)[0]), 1)
