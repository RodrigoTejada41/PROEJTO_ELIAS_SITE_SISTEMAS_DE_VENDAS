"""Smoke test for the protected dashboard, without external HTTP clients."""
import asyncio
from unittest import TestCase

from app.main import app


class DashboardAccessTest(TestCase):
    def test_anonymous_dashboard_redirects_to_login(self):
        self.assert_redirect_to_login("/")

    def test_anonymous_operator_management_redirects_to_login(self):
        self.assert_redirect_to_login("/operators")

    def test_anonymous_catalog_redirects_to_login(self):
        self.assert_redirect_to_login("/catalog")

    def test_anonymous_stock_redirects_to_login(self):
        self.assert_redirect_to_login("/stock")

    def assert_redirect_to_login(self, path):
        async def request():
            messages = []

            async def send(message):
                messages.append(message)

            async def receive():
                return {"type": "http.request", "body": b""}

            await app({
                "type": "http", "method": "GET", "scheme": "http",
                "path": path, "query_string": b"", "headers": [],
                "server": ("localhost", 80),
            }, receive, send)
            return messages[0]

        response = asyncio.run(request())
        self.assertEqual(response["status"], 303)
        self.assertEqual(dict(response["headers"])[b"location"], b"/login")
