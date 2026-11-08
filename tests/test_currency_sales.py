"""USD/PYG pricing and atomic sales regression checks."""

from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from unittest.mock import patch
from uuid import uuid4

from app import catalog, finance, fx, inventory, pricing, sales, commissions
from db_case import PostgresCase
from test_login_integration import request, csrf


class CurrencySalesIntegrationTest(PostgresCase):
    def setUp(self):
        super().setUp()
        fx.configure(self.actor_id, "manual", "7000", "Fixture commercial rate")
        commissions.configure(self.actor_id, self.actor_id, "0", "received")
        for code in ("SALE-A", "SALE-B"):
            catalog.create_sku(self.actor_id, code, catalog.sku_details({"description": code}))
        self.sku_id = catalog.list_skus(True, "SALE-A")[0]["id"]
        self.other_id = catalog.list_skus(True, "SALE-B")[0]["id"]
        pricing.update(self.actor_id, self.sku_id, 1, "4.50", "10.00")
        inventory.record(self.actor_id, self.sku_id, 10, "Fixture receipt", str(uuid4()))

    def new_sale(self, quantity=1):
        sale_id = sales.create(self.actor_id, None, self.actor_id, "2026-11-30", "0", str(uuid4()))
        sales.set_item(self.actor_id, sale_id, self.sku_id, 1, quantity, "")
        return sale_id

    def test_currency_cross_payment_replay_and_cost_privacy(self):
        self.assertEqual(fx.convert_minor(123, "USD", "PYG", Decimal(7000)), 8610)
        title_id = finance.create_title(self.actor_id, "receivable", None, "USD fixture", "100", "2026-11-30", str(uuid4()), "USD")
        key = str(uuid4())
        entry = finance.settle(self.actor_id, title_id, "350000", "cash", key, "PYG")
        self.assertEqual(finance.detail(title_id)[0]["remaining"], 5000)
        fx.configure(self.actor_id, "manual", "8000", "Updated commercial rate")
        self.assertEqual(finance.settle(self.actor_id, title_id, "350000", "cash", key, "PYG"), entry)
        self.assertEqual(finance.detail(title_id)[0]["remaining"], 5000)
        title_pyg = finance.create_title(self.actor_id, "payable", None, "PYG fixture", "80000", "2026-11-30", str(uuid4()), "PYG")
        finance.settle(self.actor_id, title_pyg, "5", "cash", str(uuid4()), "USD")
        self.assertEqual(finance.detail(title_pyg)[0]["remaining"], 40000)
        self.assertEqual(pricing.list_prices(False, "", 1)[0][0]["usd_cost_minor"], None)
        self.assertNotIn(b"4,50", request("/pricing", self.reader)[2])
        self.assertNotIn(b"USD 4,50", request("/catalog", self.reader)[2])
        self.assertEqual(request(f"/pricing/{self.sku_id}", self.reader)[0], 403)

    def test_reference_cache_manual_override_and_failure(self):
        now = datetime.now(timezone.utc)
        with patch("app.fx.fetch_reference", return_value=(Decimal("7100.000000"), now, now + timedelta(days=1))):
            self.assertTrue(fx.refresh())
            self.assertFalse(fx.refresh())
        self.assertEqual(fx.state()["active"]["pyg_per_usd"], Decimal(7000))
        fx.configure(self.actor_id, "automatic")
        self.assertEqual(fx.state()["active"]["pyg_per_usd"], Decimal(7100))
        with self.isolated_connection() as connection:
            connection.execute("UPDATE fx_policy SET next_check = now() - interval '1 second'")
        with patch("app.fx.fetch_reference", side_effect=OSError("fixture unavailable")), patch(
            "app.fx.fetch_alternate", return_value=(Decimal("6900.123456"), now, now + timedelta(hours=1))
        ):
            self.assertTrue(fx.refresh())
        active = fx.state()["active"]
        self.assertEqual(active["source"], "exchangerate_api")
        self.assertEqual(active["pyg_per_usd"], Decimal("6900.123456"))
        with patch("app.fx.fetch_reference", side_effect=OSError("fixture unavailable")), patch(
            "app.fx.fetch_alternate", side_effect=OSError("fixture unavailable")
        ):
            self.assertFalse(fx.refresh(force=True))
        self.assertEqual(fx.state()["active"]["id"], active["id"])
        self.assertEqual(fx.state()["last_error"], "provider_unavailable")
        with patch("app.fx.fetch_reference", return_value=(Decimal(7200), now, now + timedelta(hours=1))):
            self.assertTrue(fx.refresh(force=True))
        self.assertEqual(fx.state()["active"]["source"], "bcp")
        self.assertIsNone(fx.state()["last_error"])

    def test_concurrent_confirmation_snapshot_and_cancellation(self):
        first, second = self.new_sale(6), self.new_sale(6)

        def confirm(sale_id):
            try:
                return sale_id, sales.confirm(self.actor_id, sale_id, 2)
            except inventory.StockConflict:
                return sale_id, None

        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(confirm, (first, second)))
        confirmed = next((sale_id, title_id) for sale_id, title_id in results if title_id)
        sale_id, title_id = confirmed
        self.assertEqual(sum(title is not None for _, title in results), 1)
        self.assertEqual(inventory.history(self.sku_id, 1)[0], 4)
        self.assertEqual(sales.confirm(self.actor_id, sale_id, 2), title_id)
        self.assertEqual(inventory.history(self.sku_id, 1)[0], 4)

        before = sales.detail(sale_id)[1][0]
        catalog.update_sku(self.actor_id, self.sku_id, catalog.get_sku(self.sku_id)["version"],
                           catalog.sku_details({"description": "Changed catalogue"}))
        pricing.update(self.actor_id, self.sku_id, catalog.get_sku(self.sku_id)["version"], "5", "20")
        fx.configure(self.actor_id, "manual", "8000", "New rate after confirmation")
        after_sale, after_items = sales.detail(sale_id)
        self.assertEqual(after_items[0]["description_snapshot"], before["description_snapshot"])
        self.assertEqual(after_items[0]["unit_minor"], 1000)
        self.assertEqual(after_sale["applied_rate"], Decimal(7000))
        original = next(m for m in inventory.history(self.sku_id, 1)[1] if m["sale_id"] == sale_id)
        with self.assertRaises(inventory.StockConflict):
            inventory.record(self.actor_id, self.sku_id, None, "Manual reversal blocked", str(uuid4()), original["id"])

        payment = finance.settle(self.actor_id, title_id, "10", "cash", str(uuid4()))
        with self.assertRaises(sales.SaleConflict):
            sales.cancel(self.actor_id, sale_id)
        finance.reverse(self.actor_id, payment, "Receipt reversal", str(uuid4()))
        catalog.deactivate_sku(self.actor_id, self.sku_id)
        sales.cancel(self.actor_id, sale_id)
        sales.cancel(self.actor_id, sale_id)
        self.assertEqual(inventory.history(self.sku_id, 1)[0], 10)
        self.assertTrue(finance.detail(title_id)[0]["canceled"])

    def test_multiline_atomic_failure_version_and_http_access(self):
        sale_id = self.new_sale(2)
        with self.assertRaises(sales.SaleConflict):
            sales.set_item(self.actor_id, sale_id, self.other_id, 1, 1, "5")
        sales.set_item(self.actor_id, sale_id, self.other_id, 2, 1, "5")
        with self.assertRaises(inventory.StockConflict):
            sales.confirm(self.actor_id, sale_id, 3)
        self.assertEqual(inventory.history(self.sku_id, 1)[0], 10)
        self.assertEqual(finance.list_titles("receivable", "all", 1)[0], [])
        self.assertEqual(sales.detail(sale_id)[0]["status"], "draft")
        self.assertEqual(request("/sales", self.reader)[0], 403)
        path = f"/sales/{sale_id}/confirm"
        form = {"csrf": csrf(request(f"/sales/{sale_id}", self.master)[2]), "version": "3"}
        self.assertEqual(request(path, self.reader, form)[0], 403)
        self.assertEqual(request(path, self.master, {**form, "csrf": "bad"})[0], 403)
