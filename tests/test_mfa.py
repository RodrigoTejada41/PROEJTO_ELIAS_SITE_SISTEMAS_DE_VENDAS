from base64 import b32decode
from http.cookies import SimpleCookie
from pathlib import Path
import re
from tempfile import TemporaryDirectory
from unittest import TestCase
from unittest.mock import patch

from app import identity, mfa
from app.enroll_mfa import enroll
from app.recover_master import recover_master
from db_case import PostgresCase
from test_login_integration import csrf, request


class TotpTest(TestCase):
    def test_rfc6238_sha1_vector_with_six_digits(self):
        self.assertEqual(mfa.code_at(b"12345678901234567890", 59 // 30), "287082")


class SecondFactorTest(PostgresCase):
    username = "master-commercial"
    password = "master-fixture-password"
    secret = b"12345678901234567890"
    step = 100

    def setUp(self):
        super().setUp()
        directory = self.enterContext(TemporaryDirectory())
        key = Path(directory) / "key"
        key.write_text("01" * 32, encoding="ascii")
        self.enterContext(patch.dict("os.environ", {"ESTHER_MFA_KEY_FILE": str(key), "ESTHER_MFA_REQUIRED": "1"}))
        self.clock = self.enterContext(patch.object(mfa, "time", return_value=self.step * 30))
        self.assertIsNone(identity.session_account(self.master["identity_session"]))
        self.assertEqual(identity.login(self.username, self.password, "127.0.0.3", None), (None, 403))
        enroll(self.username, self.secret, mfa.code_at(self.secret, self.step))
        self.clock.return_value += 30

    def cookies(self, headers):
        jar = SimpleCookie()
        for name, value in headers:
            if name == b"set-cookie":
                jar.load(value.decode("ascii"))
        return {name: entry.value for name, entry in jar.items()}

    def challenge(self, address):
        token, status = identity.login(self.username, self.password, address, None)
        self.assertEqual(status, 202)
        return token

    def test_web_flow_and_replay(self):
        _, headers, body = request("/login")
        cookies = self.cookies(headers)
        status, headers, _ = request("/login", cookies, {
            "username": self.username, "password": self.password, "csrf": csrf(body),
        })
        self.assertEqual(status, 303)
        self.assertIn((b"location", b"/login/verify"), headers)
        self.assertNotIn("identity_session", self.cookies(headers))
        cookies.update(self.cookies(headers))
        self.assertEqual(request("/", cookies)[0], 303)
        cookies["locale"] = "es"
        status, _, body = request("/login/verify", cookies)
        self.assertEqual(status, 200)
        self.assertIn("Código de seis dígitos".encode(), body)
        code = mfa.code_at(self.secret, self.step + 1)
        self.assertEqual(request("/login/verify", cookies, {"csrf": "wrong", "code": code})[0], 403)
        status, headers, _ = request("/login/verify", cookies, {"csrf": csrf(body), "code": code})
        self.assertEqual(status, 303)
        self.assertTrue(identity.session_account(self.cookies(headers)["identity_session"]))
        self.assertEqual(identity.verify_second_factor(cookies["login_mfa"], code, None), (None, 410))
        new_challenge = self.challenge("127.0.0.4")
        self.assertEqual(identity.verify_second_factor(new_challenge, code, None), (None, 401))

    def test_attempts_expiry_and_password_recovery(self):
        challenge = self.challenge("127.0.0.4")
        for _ in range(4):
            self.assertEqual(identity.verify_second_factor(challenge, "invalid", None), (None, 401))
        challenge = self.challenge("127.0.0.5")
        self.assertEqual(identity.verify_second_factor(challenge, "invalid", None), (None, 429))
        self.assertEqual(identity.login(self.username, self.password, "127.0.0.6", None), (None, 429))
        with self.isolated_connection() as connection:
            connection.execute("UPDATE identity_mfa_challenges SET expires_at = now() - interval '1 second'")
        code = mfa.code_at(self.secret, self.step + 1)
        self.assertEqual(identity.verify_second_factor(challenge, code, None), (None, 410))
        challenge = self.challenge("127.0.0.7")
        recover_master("new-fixture-password")
        self.assertEqual(identity.verify_second_factor(challenge, code, None), (None, 410))
        replacement, status = identity.login(self.username, "new-fixture-password", "127.0.0.8", None)
        self.assertEqual(status, 202)
        self.assertEqual(identity.verify_second_factor(replacement, code, None)[1], 303)

    def test_first_access_sets_up_authenticator_after_activation(self):
        username, password = "reader-commercial", "reader-fixture-password"
        activation = identity.issue_mfa_activation(username)
        self.assertIsNone(identity.session_account(self.reader["identity_session"]))
        _, headers, body = request("/login")
        cookies = self.cookies(headers)
        status, headers, _ = request("/login", cookies, {
            "username": username, "password": password, "csrf": csrf(body),
        })
        self.assertEqual(status, 303)
        self.assertNotIn("identity_session", self.cookies(headers))
        cookies.update(self.cookies(headers))
        status, _, body = request("/login/verify", cookies)
        self.assertEqual(status, 200)
        self.assertIn(b'name="activation"', body)
        self.assertNotIn(b"data:image/png;base64,", body)
        status, _, body = request("/login/verify", cookies, {"csrf": csrf(body), "activation": "wrong"})
        self.assertEqual(status, 401)
        self.assertNotIn(b"data:image/png;base64,", body)
        status, _, _ = request("/login/verify", cookies, {"csrf": csrf(body), "activation": activation})
        self.assertEqual(status, 303)
        self.assertEqual(request("/", cookies)[0], 303)
        status, headers, body = request("/login/verify", cookies)
        self.assertEqual(status, 200)
        self.assertIn((b"cache-control", b"private, no-store"), headers)
        self.assertIn(b"data:image/png;base64,iVBOR", body)
        key = re.search(rb'<code class="text-break">([A-Z2-7]{32})</code>', body).group(1)
        code = mfa.code_at(b32decode(key), self.step + 1)
        status, headers, _ = request("/login/verify", cookies, {"csrf": csrf(body), "code": code})
        self.assertEqual(status, 303)
        self.assertEqual(identity.session_account(self.cookies(headers)["identity_session"])[1], "OPERATOR")
        with self.isolated_connection() as connection:
            self.assertEqual(connection.execute(
                "SELECT totp_activation_hash FROM identity_users WHERE username = %s", (username,),
            ).fetchone(), (None,))
        self.assertEqual(identity.verify_second_factor(cookies["login_mfa"], code, None, activation), (None, 410))
        with self.assertRaises(ValueError):
            identity.issue_mfa_activation(username)
