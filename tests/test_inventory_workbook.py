from concurrent.futures import ThreadPoolExecutor
from io import BytesIO
import re
from uuid import uuid4

from openpyxl import load_workbook

from app import catalog, commissions, fx, inventory, sales
from db_case import PostgresCase
from test_catalog_uploads import upload
from test_login_integration import csrf, request


class StockPolicyAndWorkbookTest(PostgresCase):
    def product(self, code):
        catalog.create_sku(self.actor_id, code, catalog.sku_details({"description": code, "barcode": "000" + code}))
        return catalog.list_skus(True, code)[0]["id"]

    def move(self, sku, quantity):
        return inventory.record(self.actor_id, sku, quantity, "Fixture movement", str(uuid4()))

    def test_policy_applies_to_sale_and_allows_gradual_recovery_after_disabling(self):
        sku = self.product("001")
        path = "/stock/settings"
        token = csrf(request(path, self.master)[2])
        self.assertEqual(request(path, self.reader)[0], 403)
        self.assertEqual(request(path, self.reader, {"csrf": token, "allow_negative": "1"})[0], 403)
        self.assertEqual(request(path, self.master, {"csrf": "invalid", "allow_negative": "1"})[0], 403)
        with self.assertRaises(inventory.StockConflict):
            self.move(sku, -1)
        self.assertEqual(request(path, self.master, {"csrf": token, "allow_negative": "1"})[0], 303)
        with ThreadPoolExecutor(max_workers=2) as pool:
            self.assertEqual(len(list(pool.map(lambda _: self.move(sku, -1), range(2)))), 2)
        fx.configure(self.actor_id, "manual", "7000", "Fixture commercial rate")
        commissions.configure(self.actor_id, self.actor_id, "0", "confirmed")
        sale_id = sales.create(self.actor_id, None, self.actor_id, "2026-11-30", "0", str(uuid4()),
                               items=[(sku, 3, "2")])
        sales.confirm(self.actor_id, sale_id, 1)
        self.assertEqual(inventory.history(sku, 1)[0], -5)
        self.assertEqual(request(path, self.master, {"csrf": token})[0], 303)
        with self.assertRaises(inventory.StockConflict):
            self.move(sku, -1)
        self.move(sku, 1)
        self.assertEqual(inventory.history(sku, 1)[0], -4)
        sales.cancel(self.actor_id, sale_id)
        self.assertEqual(inventory.history(sku, 1)[0], -1)
        with self.isolated_connection() as connection:
            self.assertEqual(connection.execute(
                "SELECT allow_negative FROM inventory_policy_audit ORDER BY id"
            ).fetchall(), [(True,), (False,)])
        other = self.product("002")
        inventory.set_negative_policy(self.actor_id, True)
        sales_ids = [
            sales.create(self.actor_id, None, self.actor_id, "2026-11-30", "0", str(uuid4()),
                         items=[(sku, 1, "2")])
            for _ in range(2)
        ]
        with ThreadPoolExecutor(max_workers=2) as pool:
            titles = list(pool.map(lambda sale: sales.confirm(self.actor_id, sale, 1), sales_ids))
        self.assertEqual(len(set(titles)), 2)
        self.assertEqual(inventory.history(sku, 1)[0], -3)
        self.move(other, -1000000000)
        self.move(other, -1000000000)
        with self.assertRaises(inventory.StockConflict):
            self.move(other, -1)
        self.assertEqual(inventory.history(other, 1)[0], -2000000000)

    def test_entry_preview_rechecks_stock_and_concurrent_confirm_is_idempotent(self):
        first, second = self.product("001"), self.product("002")
        inventory.set_negative_policy(self.actor_id, True)
        self.move(first, -3)
        path = "/stock/import"
        token = csrf(request(path, self.master)[2])
        self.assertEqual(request(path + "/export", self.reader)[0], 403)
        download = request(path + "/export", {**self.master, "locale": "es"})
        self.assertEqual(download[0], 200)
        workbook = load_workbook(BytesIO(download[2]))
        sheet = workbook.worksheets[0]
        self.assertTrue(sheet.tables)
        self.assertEqual((sheet["A2"].value, sheet["C2"].value, sheet["D2"].value), ("001", "000001", -3))
        sheet["E2"], sheet["E3"] = 10, 5
        data = BytesIO()
        workbook.save(data)
        reason = "Reposição em lote"
        status, _, body = upload(path, {**self.master, "locale": "pt"}, data.getvalue(), csrf=token, reason=reason)
        self.assertEqual(status, 200)
        self.assertIn(b"Saldo projetado", body)
        self.assertEqual(inventory.history(first, 1)[0], -3)
        form = {"csrf": token, "reason": reason}
        for field in ("payload", "signature"):
            form[field] = re.search(rb'name="' + field.encode() + rb'" value="([^"]+)"', body).group(1).decode()
        self.move(first, 1)
        self.assertEqual(request(path + "/confirm", self.master, {**form, "reason": "Alterado"})[0], 403)
        with ThreadPoolExecutor(max_workers=2) as pool:
            outcomes = list(pool.map(lambda _: request(path + "/confirm", self.master, form), range(2)))
        self.assertEqual([item[0] for item in outcomes], [200, 200])
        self.assertEqual(outcomes[0][2], outcomes[1][2])
        self.assertEqual(inventory.history(first, 1)[0], 8)
        self.assertEqual(inventory.history(second, 1)[0], 5)
        with self.isolated_connection() as connection:
            self.assertEqual(connection.execute("SELECT count(*) FROM inventory_entry_batches").fetchone(), (1,))
        sheet["E2"] = 11
        data = BytesIO()
        workbook.save(data)
        self.assertEqual(upload(path, self.master, data.getvalue(), csrf=token, reason=reason)[0], 409)

    def test_deactivation_after_preview_does_not_partially_import(self):
        first, second = self.product("001"), self.product("002")
        path = "/stock/import"
        token = csrf(request(path, self.master)[2])
        workbook = load_workbook(BytesIO(request(path + "/export", self.master)[2]))
        sheet = workbook.worksheets[0]
        sheet["E2"], sheet["E3"] = 4, 2
        stream = BytesIO()
        workbook.save(stream)
        status, _, body = upload(path, self.master, stream.getvalue(), csrf=token, reason="Fixture batch")
        self.assertEqual(status, 200)
        form = {"csrf": token, "reason": "Fixture batch"}
        for field in ("payload", "signature"):
            form[field] = re.search(rb'name="' + field.encode() + rb'" value="([^"]+)"', body).group(1).decode()
        catalog.deactivate_sku(self.actor_id, second)
        self.assertEqual(request(path + "/confirm", self.master, form)[0], 409)
        self.assertEqual(inventory.history(first, 1)[0], 0)
