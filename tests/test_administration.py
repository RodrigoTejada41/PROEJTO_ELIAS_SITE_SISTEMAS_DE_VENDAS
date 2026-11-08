"""Exercise company settings, receipt replay and developer authorization."""
from concurrent.futures import ThreadPoolExecutor
from uuid import uuid4

from app import catalog, commissions, fx, identity, inventory, sales
from db_case import PostgresCase
from test_login_integration import csrf, request


class AdministrationIntegrationTest(PostgresCase):
    def test_dev_can_recover_master_but_master_cannot_manage_dev(self):
        password = "developer-fixture-password"
        identity.create_dev("dev-commercial", password)
        with self.assertRaises(ValueError):
            identity.create_dev("dev-duplicate", password)
        token, _ = identity.login("dev-commercial", password, "127.0.0.2", None)
        dev = {"identity_session": token}
        self.assertEqual(request("/maintenance", self.master)[0], 403)
        self.assertEqual(request("/maintenance", self.reader)[0], 403)
        self.assertEqual(request("/sales", dev)[0], 200)
        status, _, body = request("/maintenance", dev)
        self.assertEqual(status, 200)
        form = {"csrf": csrf(body), "dev_password": password, "password": "new-master-fixture-password"}
        self.assertEqual(request("/maintenance", dev, {**form, "csrf": "invalid"})[0], 403)
        self.assertEqual(request("/maintenance", dev, {**form, "dev_password": "wrong"})[0], 403)
        self.assertEqual(request("/maintenance", dev, form)[0], 303)
        self.assertIsNone(identity.session_account(self.master["identity_session"]))
        self.assertEqual(identity.login("master-commercial", form["password"], "127.0.0.3", None)[1], 303)
        with self.isolated_connection() as connection:
            self.assertEqual(connection.execute(
                """SELECT actor.role FROM identity_audit a JOIN identity_users actor
                   ON actor.id = a.actor_user_id WHERE event = 'master_password_reset_by_dev'"""
            ).fetchone(), ("DEV",))

    def test_receipt_preserves_company_snapshot_and_blocks_ineligible_sales(self):
        company_path = "/settings/company"
        self.assertEqual(request(company_path, self.reader)[0], 403)
        form = {"csrf": csrf(request(company_path, self.master)[2]), "name": "Original company", "tax_id": "123-4"}
        self.assertEqual(request(company_path, self.master, {**form, "name": ""})[0], 400)
        fx.configure(self.actor_id, "manual", "7000", "Fixture rate")
        commissions.configure(self.actor_id, self.actor_id, "0", "confirmed")
        catalog.create_sku(self.actor_id, "REC-A", catalog.sku_details({"description": "Receipt item"}))
        sku = catalog.list_skus(True, "REC-A")[0]["id"]
        inventory.record(self.actor_id, sku, 4, "Fixture", str(uuid4()))
        sale = sales.create(self.actor_id, None, self.actor_id, "2026-11-30", "1", str(uuid4()))
        sales.set_item(self.actor_id, sale, sku, 1, 2, "10")
        path = f"/sales/{sale}/receipt"
        submit = {"csrf": form["csrf"]}
        self.assertEqual(request(path, self.master, submit)[0], 409)
        sales.confirm(self.actor_id, sale, 2)
        self.assertEqual(request(path, self.master, submit)[0], 409)
        self.assertEqual(request(company_path, self.master, form)[0], 303)
        self.assertEqual(request(path, self.reader, submit)[0], 403)
        with ThreadPoolExecutor(max_workers=2) as pool:
            self.assertEqual(list(pool.map(lambda _: request(path, self.master, submit)[0], range(2))), [303, 303])
        self.assertEqual(request(company_path, self.master, {**form, "name": "Updated company"})[0], 303)
        status, _, body = request(path, {**self.master, "locale": "es"})
        self.assertEqual(status, 200)
        for expected in (b"Original company", b"Receipt item", b"USD 19,00", b"PYG 133000", b"sin valor fiscal"):
            self.assertIn(expected, body)
        with self.isolated_connection() as connection:
            self.assertEqual(connection.execute("SELECT count(*) FROM sale_receipts").fetchone(), (1,))
        sales.cancel(self.actor_id, sale)
        self.assertEqual(request(path, self.master)[0], 404)
        self.assertEqual(request(path, self.master, submit)[0], 409)
