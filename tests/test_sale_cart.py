import json
from uuid import uuid4

from app import catalog, commissions, fx, inventory, pricing, sales
from db_case import PostgresCase
from test_login_integration import csrf, request


class SaleCartTest(PostgresCase):
    def test_cart_can_resume_after_stock_error_and_close_once(self):
        path = "/sales/new"
        page = request(path, self.master)
        self.assertEqual(page[0], 200)
        token = csrf(page[2])
        catalog.create_sku(self.actor_id, "CART-A", catalog.sku_details({"description": "Produto A", "barcode": "000123"}))
        sku = catalog.list_skus(True, "")[0]["id"]
        pricing.update(self.actor_id, sku, 1, "1", "3")
        fx.configure(self.actor_id, "manual", "7000", "Taxa para teste")
        commissions.configure(self.actor_id, self.actor_id, "0", "confirmed")
        inventory.record(self.actor_id, sku, 2, "Estoque para teste", str(uuid4()))
        self.assertEqual(request("/sales/products", self.reader, query=b"q=000123")[0], 403)
        products = json.loads(request("/sales/products", self.master, query=b"q=000123")[2])
        self.assertEqual((products[0]["id"], products[0]["balance"], products[0]["usd_price_minor"]), (str(sku), 2, 300))
        line = {"id": str(sku), "code": "CART-A", "description": "Produto A", "quantity": "3", "price": "3"}
        form = {"csrf": token, "request_key": str(uuid4()), "seller_id": str(self.actor_id),
                "due_date": "2026-11-30", "discount": "1", "cart": json.dumps([line]), "action": "confirm"}
        status, _, body = request(path, self.master, form)
        self.assertEqual(status, 409)
        self.assertIn(b"Estoque insuficiente", body)
        draft = sales.list_sales("draft", 1)[0][0]
        self.assertEqual(sales.detail(draft["id"])[1][0]["quantity"], 3)
        self.assertEqual(inventory.history(sku, 1)[0], 2)
        form.pop("request_key")
        form["version"] = str(draft["version"])
        form["cart"] = json.dumps([{**line, "quantity": "2"}])
        update = f'/sales/{draft["id"]}/draft'
        self.assertEqual(request(update, self.master, form)[0], 303)
        self.assertEqual(request(update, self.master, form)[0], 303)
        self.assertEqual(inventory.history(sku, 1)[0], 0)
        self.assertEqual(sales.detail(draft["id"])[0]["net"], 500)
        self.assertEqual(request(f'/sales/{draft["id"]}', self.master)[0], 200)
