"""Account locale persistence and CSRF check."""

from http.cookies import SimpleCookie

from app import identity
from db_case import PostgresCase
from test_login_integration import request, csrf


class LocaleIntegrationTest(PostgresCase):
    def test_locale_post_and_fresh_login(self):
        token = self.master["identity_session"]
        form = {"csrf": csrf(request("/", self.master)[2]), "locale": "es", "next": "/catalog"}
        self.assertEqual(request("/preferences/locale", self.master, {**form, "csrf": "bad"})[0], 403)
        status, headers, _ = request("/preferences/locale", self.master, form)
        self.assertEqual(status, 303)
        self.assertEqual(dict(headers)[b"location"], b"/catalog")
        self.assertEqual(identity.preferred_locale(token), "es")
        _, _, body = request("/login")
        login = {"csrf": csrf(body), "username": "master-commercial", "password": "master-fixture-password"}
        status, headers, _ = request("/login", {"login_csrf": login["csrf"]}, login)
        self.assertEqual(status, 303)
        cookies = SimpleCookie()
        for name, value in headers:
            if name == b"set-cookie":
                cookies.load(value.decode())
        self.assertEqual(cookies["locale"].value, "es")
        self.assertEqual(request("/preferences/locale", self.master, {**form, "next": "//example.test"})[0], 303)
        self.assertEqual(dict(request("/preferences/locale", self.master, {**form, "next": "//example.test"})[1])[b"location"], b"/")
