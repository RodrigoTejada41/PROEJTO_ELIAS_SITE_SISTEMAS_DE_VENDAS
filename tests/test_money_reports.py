"""Sales totals and cash events must remain distinct and currency-separated."""

import csv
from decimal import Decimal
from io import StringIO
from uuid import uuid4

from app import catalog, commissions, finance, fx, inventory, pricing, reports, sales
from db_case import PostgresCase
from test_login_integration import request


class MoneyReportIntegrationTest(PostgresCase):
    def test_cash_dates_currencies_and_sales_csv(self):
        fx.configure(self.actor_id, "manual", "7000", "Fixture rate")
        commissions.configure(self.actor_id, self.actor_id, "5", "received")
        catalog.create_sku(self.actor_id, "REPORT-SALE", catalog.sku_details({"description": "Report sale"}))
        sku_id = catalog.list_skus(True, "")[0]["id"]
        pricing.update(self.actor_id, sku_id, 1, "4", "10")
        inventory.record(self.actor_id, sku_id, 10, "Fixture stock", str(uuid4()))
        sale_id = sales.create(self.actor_id, None, self.actor_id, "2030-11-30", "0", str(uuid4()))
        sales.set_item(self.actor_id, sale_id, sku_id, 1, 2, "")
        title_id = sales.confirm(self.actor_id, sale_id, 2)
        receipt = finance.settle(self.actor_id, title_id, "70000", "cash", str(uuid4()), "PYG")
        finance.reverse(self.actor_id, receipt, "Fixture reversal", str(uuid4()))
        expense = finance.create_title(self.actor_id, "payable", None, "Report expense", "5", "2030-11-30", str(uuid4()), "USD")
        finance.settle(self.actor_id, expense, "5", "cash", str(uuid4()))
        with self.isolated_connection() as connection:
            connection.execute("UPDATE finance_settlements SET occurred_at = '2030-11-04 12:00:00+00' WHERE id = %s", (receipt,))
            connection.execute("UPDATE finance_reversals SET occurred_at = '2030-11-05 12:00:00+00' WHERE settlement_id = %s", (receipt,))
        lower, upper = reports.audit_period("2030-11-04", "2030-11-04")
        rows, totals, _ = reports.cash(lower, upper, "all")
        self.assertEqual(totals, [{"currency": "PYG", "amount_minor": 70000}])
        lower, upper = reports.audit_period("2030-11-05", "2030-11-05")
        self.assertEqual(reports.cash(lower, upper, "all")[1], [{"currency": "PYG", "amount_minor": -70000}])
        totals = {row["currency"]: row["amount_minor"] for row in reports.cash(None, None, "all")[1]}
        self.assertEqual(totals, {"USD": -500, "PYG": 0})
        self.assertEqual(reports.sale_report(None, None, None)[1]["net_minor"], 2000)
        self.assertEqual(reports.top_products(None, None)[0]["quantity"], 2)

        for path in ("/reports/cash", "/reports/sales"):
            self.assertEqual(request(path, self.reader)[0], 403)
            self.assertEqual(request(path, self.master)[0], 200)
        self.assertEqual(request("/reports/sales", self.master, query=b"seller_id=")[0], 200)
        status, _, data = request("/reports/cash", self.master, query=b"export=true")
        self.assertEqual(status, 200)
        rows = list(csv.DictReader(StringIO(data.decode("utf-8-sig"))))
        self.assertTrue(any(Decimal(row["Valor"]) < 0 for row in rows))
        status, _, data = request("/reports/sales", self.master, query=b"export=true")
        self.assertEqual(status, 200)
        self.assertIn(b"20.00", data)

        dashboard, trend, ranking = reports.dashboard_sales(None, None, self.actor_id)
        self.assertEqual(dashboard, reports.sale_report(None, None, self.actor_id)[1])
        self.assertEqual((dashboard["count"], dashboard["pyg"], dashboard["average_minor"]), (1, 140000, 2000))
        self.assertEqual((trend[0]["count"], ranking[0]["quantity"]), (1, 2))
        self.assertIn(b"Painel de vendas", request("/", self.master)[2])
        self.assertIn(b"PYG 140000", request("/", self.master)[2])
        self.assertNotIn(b"Painel de vendas", request("/", self.reader)[2])
        self.assertEqual(request("/", self.master, query=b"start=2030-11-05&end=2030-11-04")[0], 400)
        self.assertEqual(request("/reports/top-products", self.reader)[0], 403)
        status, _, data = request("/reports/top-products", self.master, query=b"q=REPORT-SALE&export=true")
        self.assertEqual(status, 200)
        self.assertIn(b"REPORT-SALE,Report sale,2", data)
        self.assertNotIn(b"REPORT-SALE", request("/reports/top-products", self.master, query=b"q=unmatched&export=true")[2])

        status, _, data = request("/reports/cash", self.master, query=b"nature=reversed&currency=PYG&export=true")
        self.assertEqual(status, 200)
        reversed_rows = list(csv.DictReader(StringIO(data.decode("utf-8-sig"))))
        self.assertEqual([Decimal(row["Valor"]) for row in reversed_rows], [Decimal(-70000)])
        self.assertEqual(reports.cash(None, None, "all", nature="payable")[1], [{"currency": "USD", "amount_minor": -500}])

        inventory.set_negative_policy(self.actor_id, True)
        inventory.record(self.actor_id, sku_id, -9, "Fixture stock exit", str(uuid4()))
        status, _, data = request("/reports", self.master, query=b"balance=negative&export=true")
        self.assertEqual(status, 200)
        self.assertIn(b"REPORT-SALE,Report sale,Ativo,-1", data)
        self.assertNotIn(b"REPORT-SALE", request("/reports", self.master, query=b"balance=zero&export=true")[2])
        sales.cancel(self.actor_id, sale_id)
        self.assertEqual(reports.dashboard_sales(None, None, self.actor_id)[0]["count"], 0)
        self.assertEqual(reports.product_ranking(None, None, self.actor_id, "", 1, False)[0], [])
