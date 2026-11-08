"""Percentage snapshots, accrual timing and payout reversal regression checks."""

from concurrent.futures import ThreadPoolExecutor
from uuid import uuid4

import psycopg

from app import catalog, commissions, finance, fx, inventory, pricing, sales
from db_case import PostgresCase
from test_login_integration import request, csrf


class CommissionIntegrationTest(PostgresCase):
    def setUp(self):
        super().setUp()
        fx.configure(self.actor_id, "manual", "7000", "Fixture rate")
        catalog.create_sku(self.actor_id, "COM-SKU", catalog.sku_details({"description": "Commission SKU"}))
        self.sku_id = catalog.list_skus(True, "")[0]["id"]
        pricing.update(self.actor_id, self.sku_id, 1, "4", "10")
        inventory.record(self.actor_id, self.sku_id, 100, "Fixture stock", str(uuid4()))

    def confirm(self, percent, event):
        commissions.configure(self.actor_id, self.actor_id, percent, event)
        sale_id = sales.create(self.actor_id, None, self.actor_id, "2026-11-30", "0", str(uuid4()))
        sales.set_item(self.actor_id, sale_id, self.sku_id, 1, 10, "")
        title_id = sales.confirm(self.actor_id, sale_id, 2)
        return sale_id, title_id

    def balance(self):
        return commissions.detail(self.actor_id)[0]["balance"]

    def test_receipts_snapshot_adjustable_percentage_and_reversals(self):
        sale_id, title_id = self.confirm("5", "received")
        self.assertEqual(self.balance(), 0)
        first = finance.settle(self.actor_id, title_id, "40", "cash", str(uuid4()))
        self.assertEqual(self.balance(), 200)
        commissions.configure(self.actor_id, self.actor_id, "20", "confirmed")
        second = finance.settle(self.actor_id, title_id, "60", "cash", str(uuid4()))
        self.assertEqual(self.balance(), 500)
        payout = commissions.payout(self.actor_id, self.actor_id, "2", "cash", "PYG", str(uuid4()))
        self.assertEqual(self.balance(), 300)
        finance.reverse(self.actor_id, first, "Reverse first receipt", str(uuid4()))
        finance.reverse(self.actor_id, second, "Reverse second receipt", str(uuid4()))
        self.assertEqual(self.balance(), -200)
        with self.assertRaises(commissions.CommissionConflict):
            commissions.payout(self.actor_id, self.actor_id, "1", "cash", "USD", str(uuid4()))
        payout_entry = next(p for p in commissions.detail(self.actor_id)[2] if p["id"] == payout)
        finance.reverse(self.actor_id, payout_entry["settlement_id"], "Reverse commission payout", str(uuid4()))
        self.assertEqual(self.balance(), 0)
        with self.assertRaises(finance.FinanceConflict):
            finance.settle(self.actor_id, payout_entry["title_id"], "2", "cash", str(uuid4()))
        sales.cancel(self.actor_id, sale_id)
        self.assertEqual(self.balance(), 0)

    def test_concurrent_payout_replay_and_sale_cancel(self):
        sale_id, _ = self.confirm("10", "confirmed")
        self.assertEqual(self.balance(), 1000)
        keys = [str(uuid4()), str(uuid4())]

        def pay(key):
            try:
                return commissions.payout(self.actor_id, self.actor_id, "8", "cash", "USD", key)
            except commissions.CommissionConflict:
                return None

        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(pay, keys))
        index = next(i for i, result in enumerate(results) if result is not None)
        self.assertEqual(sum(result is not None for result in results), 1)
        self.assertEqual(commissions.payout(self.actor_id, self.actor_id, "8", "cash", "USD", keys[index]), results[index])
        self.assertEqual(self.balance(), 200)
        sales.cancel(self.actor_id, sale_id)
        self.assertEqual(self.balance(), -800)
        self.assertEqual(inventory.history(self.sku_id, 1)[0], 100)

    def test_rules_required_access_and_payout_rollback(self):
        sale_id = sales.create(self.actor_id, None, self.actor_id, "2026-11-30", "0", str(uuid4()))
        sales.set_item(self.actor_id, sale_id, self.sku_id, 1, 1, "")
        with self.assertRaises(sales.SaleConflict):
            sales.confirm(self.actor_id, sale_id, 2)
        self.assertEqual(request("/commissions", self.reader)[0], 403)
        form = {"csrf": csrf(request("/commissions", self.master)[2]), "seller_id": self.actor_id, "percent": "101", "event": "confirmed"}
        self.assertEqual(request("/commissions/rules", self.master, form)[0], 400)
        self.assertEqual(request("/commissions/rules", self.reader, {**form, "percent": "5"})[0], 403)
        self.assertEqual(request("/commissions/rules", self.master, {**form, "percent": "5"})[0], 303)
        sales.confirm(self.actor_id, sale_id, 2)
        before = len(finance.list_titles("payable", "all", 1)[0])
        with self.assertRaises(psycopg.errors.ForeignKeyViolation):
            commissions.payout(-1, self.actor_id, "0.50", "cash", "USD", str(uuid4()))
        self.assertEqual(len(finance.list_titles("payable", "all", 1)[0]), before)
        self.assertEqual(self.balance(), 50)
