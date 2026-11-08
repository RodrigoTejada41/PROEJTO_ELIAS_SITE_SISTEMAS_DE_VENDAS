"""Finance precision, idempotency, reversals and access controls."""

from concurrent.futures import ThreadPoolExecutor
from uuid import uuid4

from app import finance
from db_case import PostgresCase
from test_login_integration import request, csrf


class FinanceIntegrationTest(PostgresCase):
    def test_explicit_currency_precision_and_access(self):
        self.assertEqual(finance.settings()["currency"], "USD")
        self.assertEqual(request("/finance", self.reader)[0], 403)
        self.assertEqual(request("/finance/settings", self.reader)[0], 403)
        form = {"csrf": csrf(request("/finance/settings", self.master)[2]), "currency": "USD", "scale": "2"}
        self.assertEqual(request("/finance/settings", self.master, {**form, "csrf": "bad"})[0], 403)
        self.assertEqual(request("/finance/settings", self.master, form)[0], 303)
        self.assertEqual(finance.parse_amount("12,34", 2), 1234)
        for value in ("1.001", "0", "-1", "1,000.00", "NaN", "99999999999999"):
            with self.assertRaises(ValueError):
                finance.parse_amount(value, 2)
        self.assertEqual(finance.parse_amount("123", 0), 123)
        self.assertEqual(finance.format_amount(1234, 2, "pt"), "12,34")

    def test_partial_settlement_replay_concurrency_reversal_and_cancel(self):
        finance.configure(self.actor_id, "USD", 2)
        key = str(uuid4())
        title_id = finance.create_title(self.actor_id, "receivable", None, "Fixture title", "100.00", "2026-11-30", key)
        self.assertEqual(finance.create_title(self.actor_id, "receivable", None, "Fixture title", "100,00", "2026-11-30", key), title_id)
        with self.assertRaises(finance.FinanceConflict):
            finance.configure(self.actor_id, "PYG", 0)
        payment_key = str(uuid4())
        payment = finance.settle(self.actor_id, title_id, "40.00", "transfer", payment_key)
        self.assertEqual(finance.settle(self.actor_id, title_id, "40,00", "transfer", payment_key), payment)
        self.assertEqual(finance.detail(title_id)[0]["remaining"], 6000)
        with self.assertRaises(finance.FinanceConflict):
            finance.settle(self.actor_id, title_id, "41", "transfer", payment_key)
        with self.assertRaises(finance.FinanceConflict):
            finance.cancel(self.actor_id, title_id)

        def receive(_):
            try:
                finance.settle(self.actor_id, title_id, "50", "cash", str(uuid4()))
                return True
            except finance.FinanceConflict:
                return False

        with ThreadPoolExecutor(max_workers=2) as pool:
            self.assertCountEqual(list(pool.map(receive, range(2))), [True, False])
        self.assertEqual(finance.detail(title_id)[0]["remaining"], 1000)

        reversal_key = str(uuid4())
        finance.reverse(self.actor_id, payment, "Fixture reversal", reversal_key)
        finance.reverse(self.actor_id, payment, "Fixture reversal", reversal_key)
        self.assertEqual(finance.detail(title_id)[0]["remaining"], 5000)
        with self.assertRaises(finance.FinanceConflict):
            finance.reverse(self.actor_id, payment, "Another reversal", str(uuid4()))
        other_payment = next(r["id"] for r in finance.detail(title_id)[1] if r["id"] != payment)
        finance.reverse(self.actor_id, other_payment, "Final reversal", str(uuid4()))
        finance.cancel(self.actor_id, title_id)
        finance.cancel(self.actor_id, title_id)
        self.assertTrue(finance.detail(title_id)[0]["canceled"])
        with self.assertRaises(finance.FinanceConflict):
            finance.settle(self.actor_id, title_id, "1", "cash", str(uuid4()))

    def test_http_payable_flow_and_audit(self):
        finance.configure(self.actor_id, "USD", 2)
        path = "/finance/new/payable"
        form = {"csrf": csrf(request(path, self.master)[2]), "request_key": str(uuid4()),
                "description": "Fixture expense", "amount": "20,50", "due_date": "2026-11-30", "party_id": ""}
        self.assertEqual(request(path, self.reader, form)[0], 403)
        self.assertEqual(request(path, self.master, form)[0], 303)
        title = finance.list_titles("payable", "open", 1)[0][0]
        detail = f'/finance/{title["id"]}'
        self.assertEqual(request(detail, self.master)[0], 200)
        settlement = {"csrf": form["csrf"], "request_key": str(uuid4()), "amount": "5,25", "method": "cash"}
        self.assertEqual(request(detail + "/settle", self.master, settlement)[0], 303)
        self.assertEqual(finance.detail(title["id"])[0]["remaining"], 1525)
        status, _, body = request(detail + "/cancel", self.master, {"csrf": form["csrf"]})
        self.assertEqual(status, 409)
        self.assertIn(f'name="next" value="{detail}"'.encode(), body)
        self.assertNotIn(f'name="next" value="{detail}/cancel"'.encode(), body)
        self.assertEqual(request("/audit", self.master, query=b"source=finance")[0], 200)
