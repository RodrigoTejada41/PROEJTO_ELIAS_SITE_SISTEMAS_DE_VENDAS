from io import BytesIO
import re

from openpyxl import load_workbook

from app import catalog, fx
from db_case import PostgresCase
from test_catalog_uploads import upload
from test_login_integration import csrf, request


class CatalogWorkbookTest(PostgresCase):
    def test_rejects_formula_and_stale_mixed_batch(self):
        self.master = {**self.master, "locale": "pt"}
        path = "/catalog/import"
        token = csrf(request(path, self.master)[2])
        catalog.create_sku(self.actor_id, "EXISTING", catalog.sku_details({"description": "Original"}))
        original = catalog.list_skus(True, "")[0]
        workbook = load_workbook(BytesIO(request(path + "/xlsx/export", self.master)[2]))
        sheet = workbook.worksheets[0]
        self.assertIsNone(sheet["J2"].value)
        sheet["G2"] = "=1+2"
        stream = BytesIO()
        workbook.save(stream)
        status, _, body = upload(path + "/xlsx", self.master, stream.getvalue(), csrf=token)
        self.assertEqual(status, 400)
        self.assertIn(b"Linha 2.", body)
        sheet["G2"] = 3
        sheet.insert_rows(2)
        sheet["A2"], sheet["B2"] = "NEW", "New product"
        stream = BytesIO()
        workbook.save(stream)
        status, _, preview = upload(path + "/xlsx", self.master, stream.getvalue(), csrf=token)
        self.assertEqual(status, 200)
        catalog.update_sku(self.actor_id, original["id"], original["version"],
                           catalog.sku_details({"description": "Edited elsewhere"}))
        confirm = {"csrf": token}
        for field in ("payload", "signature"):
            confirm[field] = re.search(rb'name="' + field.encode() + rb'" value="([^"]+)"', preview).group(1).decode()
        self.assertEqual(request(path + "/xlsx/confirm", self.master, {**confirm, "signature": "invalid"})[0], 403)
        status, _, body = request(path + "/xlsx/confirm", self.master, confirm)
        self.assertEqual(status, 409)
        self.assertIn(b"Linha 3.", body)
        self.assertEqual([row["description"] for row in catalog.list_skus(True, "")], ["Edited elsewhere"])

    def test_download_preview_update_and_insert(self):
        path = "/catalog/import"
        token = csrf(request(path, self.master)[2])
        catalog.create_sku(self.actor_id, "0001", catalog.sku_details({"description": "Original", "barcode": "0000123"}))
        fx.configure(self.actor_id, "manual", "7000", "Taxa de teste")
        self.assertEqual(request(path + "/xlsx/export", self.reader)[0], 403)
        status, _, body = request(path + "/xlsx/export", self.master)
        self.assertEqual(status, 200)
        workbook = load_workbook(BytesIO(body))
        sheet = workbook.worksheets[0]
        self.assertTrue(sheet.tables)
        self.assertEqual(sheet.freeze_panes, "A2")
        self.assertEqual((sheet["A2"].value, sheet["F2"].value), ("0001", "0000123"))
        sheet["B2"] = "Atualizado"
        sheet["G2"] = 1.25
        sheet["H2"] = 2.5
        sheet["J2"] = 9999
        sheet.append(["0002", "Novo", None, None, None, "0000124", 1, 3])
        stream = BytesIO()
        workbook.save(stream)
        status, _, preview = upload(path + "/xlsx", self.master, stream.getvalue(), csrf=token)
        self.assertEqual(status, 200)
        self.assertEqual(catalog.list_skus(True, "0001")[0]["description"], "Original")
        confirm = {"csrf": token}
        for field in ("payload", "signature"):
            confirm[field] = re.search(rb'name="' + field.encode() + rb'" value="([^"]+)"', preview).group(1).decode()
        self.assertEqual(request(path + "/xlsx/confirm", self.master, confirm)[0], 200)
        updated = catalog.list_skus(True, "0001")[0]
        self.assertEqual((updated["description"], updated["usd_cost_minor"], updated["usd_price_minor"]), ("Atualizado", 125, 250))
        self.assertEqual(catalog.list_skus(True, "0002")[0]["barcode"], "0000124")
        self.assertEqual(request(path + "/xlsx/confirm", self.master, confirm)[0], 409)
        fresh = load_workbook(BytesIO(request(path + "/xlsx/export", self.master)[2]))
        self.assertEqual(fresh.worksheets[0]["J2"].value, 17500)
