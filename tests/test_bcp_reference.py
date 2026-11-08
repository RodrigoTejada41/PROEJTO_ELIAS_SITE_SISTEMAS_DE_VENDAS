from datetime import datetime, timezone
from decimal import Decimal
from unittest import TestCase
from unittest.mock import patch

from app.fx import fetch_automatic, parse_alternate, parse_reference


class BcpReferenceTest(TestCase):
    def test_extracts_usd_rate_and_reference_date(self):
        html = """<table>
          <tr><th>PLANILLA DE COTIZACIONES AL JUEVES 05 DE NOVIEMBRE DEL 2026</th></tr>
          <tr><td>DOLAR</td><td>USD</td><td>1,0000</td><td>6.388,47</td></tr>
          <tr><td>EURO</td><td>EUR</td><td>1,3459</td><td>8.598,24</td></tr>
        </table>"""
        now = datetime(2026, 11, 5, 16, tzinfo=timezone.utc)
        rate, published, next_check = parse_reference(html, now)
        self.assertEqual(rate, Decimal("6388.47"))
        self.assertEqual(published.date(), now.date())
        self.assertGreater(next_check, now)
        with self.assertRaises(ValueError):
            parse_reference(html.replace("USD", "EUR"), now)

    def test_alternate_quote_validates_base_and_publication(self):
        now = datetime(2026, 11, 8, 10, tzinfo=timezone.utc)
        payload = b'{"result":"success","base_code":"USD","time_last_update_unix":1794096000,"rates":{"PYG":6107.599103}}'
        rate, published, next_check = parse_alternate(payload, now)
        self.assertEqual(rate, Decimal("6107.599103"))
        self.assertEqual(int(published.timestamp()), 1794096000)
        self.assertGreater(next_check, now)
        for invalid in (payload.replace(b"USD", b"EUR"), payload.replace(b"1794096000", b"1")):
            with self.assertRaises(ValueError):
                parse_alternate(invalid, now)

    @patch("app.fx.fetch_alternate")
    @patch("app.fx.fetch_reference")
    def test_uses_alternate_only_when_bcp_fails(self, bcp, alternate):
        self.assertEqual(fetch_automatic(), ("bcp", bcp.return_value))
        alternate.assert_not_called()
        bcp.side_effect = OSError("BCP unavailable")
        self.assertEqual(fetch_automatic(), ("exchangerate_api", alternate.return_value))
