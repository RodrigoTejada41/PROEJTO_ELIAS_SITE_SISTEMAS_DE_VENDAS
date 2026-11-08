from datetime import datetime, timezone
from decimal import Decimal
from unittest import TestCase

from app.fx import parse_reference


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
