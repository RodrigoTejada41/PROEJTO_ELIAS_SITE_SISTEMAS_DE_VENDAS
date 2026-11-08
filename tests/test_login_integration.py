"""Exercise the ASGI authentication flow against a disposable PostgreSQL schema."""

import asyncio
from concurrent.futures import ThreadPoolExecutor
from http.cookies import SimpleCookie
import os
from pathlib import Path
import re
from threading import Event
from time import monotonic, sleep
from unittest import TestCase, skipUnless
from unittest.mock import patch
from urllib.parse import urlencode
from uuid import uuid4

import psycopg
from psycopg import sql

from app import catalog, identity, inventory
from app.bootstrap_master import create_master
from app.main import app
from app.recover_master import recover_master

DSN = os.getenv("IDENTITY_TEST_DSN")


def request(path, cookies=None, form=None, query=b"", *, multipart=None):
    async def run():
        messages = []
        headers = [(b"cookie", "; ".join(f"{k}={v}" for k, v in (cookies or {}).items()).encode())]
        body = urlencode(form or {}).encode()
        if multipart is not None:
            content_type, body = multipart
            headers.append((b"content-type", content_type))
        elif form is not None:
            headers.append((b"content-type", b"application/x-www-form-urlencoded"))

        async def receive():
            return {"type": "http.request", "body": body}

        async def send(message):
            messages.append(message)

        await app({
            "type": "http", "method": "GET" if form is None and multipart is None else "POST",
            "scheme": "https", "path": path, "query_string": query, "headers": headers,
            "server": ("localhost", 443), "client": ("127.0.0.1", 12345),
        }, receive, send)
        return messages[0]["status"], messages[0]["headers"], messages[1]["body"]

    return asyncio.run(run())


def csrf(body):
    return re.search(rb'name="csrf" value="([^"]+)"', body).group(1).decode()


@skipUnless(DSN, "Configure IDENTITY_TEST_DSN para executar em PostgreSQL.")
class LoginIntegrationTest(TestCase):
    def test_login_rotation_logout_and_access_controls(self):
        schema = sql.Identifier(f"identity_test_{uuid4().hex}")
        connect = psycopg.connect

        def isolated_connection(**kwargs):
            return connect(DSN, options=f"-c search_path={schema.as_string()}", **kwargs)

        with connect(DSN, autocommit=True) as admin:
            admin.execute(sql.SQL("CREATE SCHEMA {}").format(schema))
            try:
                with isolated_connection() as connection:
                    for migration in sorted((Path(__file__).resolve().parents[1] / "migrations").glob("*.sql")):
                        connection.execute(migration.read_text(encoding="ascii"))

                with patch("app.identity.psycopg.connect", side_effect=isolated_connection):
                    self.exercise_flow(isolated_connection)
                    self.exercise_operator_management(isolated_connection)
                    self.exercise_catalog(isolated_connection)
                    self.exercise_inventory(isolated_connection)
            finally:
                admin.execute(sql.SQL("DROP SCHEMA {} CASCADE").format(schema))

    def exercise_flow(self, connect):
        password = "fixture-only-password"
        create_master("master-test", password)
        status, _, body = request("/login", {"locale": "es"})
        self.assertEqual(status, 200)
        self.assertIn("Contraseña".encode(), body)
        form = {"csrf": csrf(body), "username": "master-test", "password": password}
        cookies = {"login_csrf": form["csrf"]}
        self.assertEqual(request("/login", {}, form)[0], 403)

        wrong_password = request("/login", cookies, {**form, "password": "incorrect"})
        unknown_user = request("/login", cookies, {**form, "username": "unknown"})
        self.assertEqual(wrong_password[0], 401)
        self.assertEqual((wrong_password[0], wrong_password[2]), (unknown_user[0], unknown_user[2]))

        def sign_in():
            status, headers, _ = request("/login", cookies, form)
            self.assertEqual(status, 303)
            result = SimpleCookie()
            for name, value in headers:
                if name == b"set-cookie":
                    result.load(value.decode())
            session = result["identity_session"]
            self.assertTrue(session["secure"])
            self.assertTrue(session["httponly"])
            self.assertEqual(session["samesite"], "lax")
            return session.value

        first_token = sign_in()
        cookies["identity_session"] = first_token
        cookies["identity_session"] = sign_in()
        self.assertNotEqual(first_token, cookies["identity_session"])
        self.assertEqual(request("/", {"identity_session": first_token})[0], 303)

        status, _, dashboard = request("/", {**cookies, "locale": "es"})
        self.assertEqual(status, 200)
        self.assertIn(b"Panel administrativo", dashboard)
        self.assertEqual(request("/logout", cookies, {"csrf": "invalid"})[0], 403)

        with connect() as connection:
            connection.execute("UPDATE identity_users SET active = false")
        self.assertEqual(request("/", cookies)[0], 303)
        with connect() as connection:
            connection.execute("UPDATE identity_users SET active = true")
        self.assertEqual(request("/logout", cookies, {"csrf": csrf(dashboard)})[0], 303)
        self.assertEqual(request("/", cookies)[0], 303)

        cookies["identity_session"] = sign_in()
        self.assertEqual(request("/login", cookies, form)[0], 429)
        with connect() as connection:
            connection.execute("UPDATE identity_sessions SET expires_at = now()")
            events = connection.execute("SELECT event FROM identity_audit ORDER BY id").fetchall()
        self.assertEqual(request("/", cookies)[0], 303)
        self.assertEqual(events, [(event,) for event in ("master_created", "login", "login", "logout", "login")])

        with connect() as connection:
            connection.execute("DELETE FROM identity_login_limits")
        first = sign_in()
        second = sign_in()
        new_password = "new-fixture-only-password"
        recover_master(new_password)

        for token in (first, second):
            self.assertEqual(request("/", {"identity_session": token})[0], 303)
        self.assertEqual(request("/login", cookies, form)[0], 401)
        self.assertEqual(request("/login", cookies, {**form, "password": new_password})[0], 303)
        with connect() as connection:
            event = connection.execute(
                """
                SELECT audit.user_id, account.id, audit.actor_db_role = current_user
                FROM identity_audit AS audit
                JOIN identity_users AS account ON account.role = 'MASTER'
                WHERE audit.event = 'master_password_recovered'
                """
            ).fetchone()
        self.assertEqual(event, (event[1], event[1], True))

        verifying = Event()
        release_login = Event()
        verify = identity.PASSWORDS.verify

        def pause_verification(hashed_password, supplied_password):
            verifying.set()
            if not release_login.wait(10):
                raise TimeoutError("Login verification was not released.")
            return verify(hashed_password, supplied_password)

        with patch.object(type(identity.PASSWORDS), "verify", side_effect=pause_verification):
            with ThreadPoolExecutor(max_workers=2) as pool:
                pending_login = pool.submit(identity.login, "master-test", new_password, "127.0.0.1", None)
                try:
                    self.assertTrue(verifying.wait(5))
                    recovery = pool.submit(recover_master, "final-fixture-only-password")
                    deadline = monotonic() + 5
                    while monotonic() < deadline:
                        with connect() as connection:
                            blocked = connection.execute(
                                """
                                SELECT 1 FROM pg_stat_activity
                                WHERE wait_event_type = 'Lock'
                                  AND query LIKE '%%UPDATE identity_users SET password_hash%%'
                                """
                            ).fetchone()
                        if blocked:
                            break
                        sleep(0.05)
                    else:
                        self.fail("Recovery did not wait for the in-flight login.")
                finally:
                    release_login.set()
                token, status = pending_login.result(timeout=5)
                recovery.result(timeout=5)
        self.assertEqual(status, 303)
        self.assertEqual(request("/", {"identity_session": token})[0], 303)

    def exercise_operator_management(self, connect):
        from app.main import session_csrf

        with connect() as connection:
            connection.execute("DELETE FROM identity_login_limits")
        master, status = identity.login("master-test", "final-fixture-only-password", "127.0.0.1", None)
        self.assertEqual(status, 303)
        master_cookies = {"identity_session": master, "locale": "es"}
        status, _, body = request("/operators", master_cookies)
        self.assertEqual(status, 200)
        self.assertIn(b"Crear operador", body)
        form = {"csrf": csrf(body), "username": "operator-test", "password": "operator-fixture-password"}
        self.assertEqual(request("/operators", master_cookies, {**form, "csrf": "bad"})[0], 403)
        self.assertEqual(request("/operators", master_cookies, {**form, "role": "MASTER"})[0], 400)
        self.assertEqual(request("/operators", master_cookies, form)[0], 303)
        self.assertEqual(request("/operators", master_cookies, form)[0], 409)

        operator, status = identity.login(form["username"], form["password"], "127.0.0.1", None)
        self.assertEqual(status, 303)
        operator_cookies = {"identity_session": operator}
        self.assertNotIn(b'href="/operators"', request("/", operator_cookies)[2])
        self.assertEqual(request("/operators", operator_cookies)[0], 403)
        self.assertEqual(request("/operators", operator_cookies, {**form, "csrf": session_csrf(operator)})[0], 403)

        with connect() as connection:
            master_id = connection.execute("SELECT id FROM identity_users WHERE role = 'MASTER'").fetchone()[0]
            operator_id = connection.execute("SELECT id FROM identity_users WHERE role = 'OPERATOR'").fetchone()[0]
        master_action = f"/operators/{master_id}/deactivate"
        operator_action = f"/operators/{operator_id}/deactivate"
        self.assertEqual(request(operator_action, operator_cookies, {"csrf": session_csrf(operator)})[0], 403)
        self.assertEqual(request(master_action, master_cookies, {"csrf": form["csrf"]})[0], 303)
        self.assertEqual(request("/", master_cookies)[0], 200)
        self.assertEqual(request(operator_action, master_cookies, {"csrf": form["csrf"]})[0], 303)
        self.assertEqual(request(operator_action, master_cookies, {"csrf": form["csrf"]})[0], 303)
        self.assertEqual(request("/", operator_cookies)[0], 303)
        self.assertEqual(identity.login(form["username"], form["password"], "127.0.0.1", None), (None, 401))
        with connect() as connection:
            events = connection.execute(
                "SELECT event, user_id, actor_user_id FROM identity_audit WHERE actor_user_id IS NOT NULL ORDER BY id"
            ).fetchall()
            remaining = connection.execute("SELECT count(*) FROM identity_sessions WHERE user_id = %s", (operator_id,)).fetchone()[0]
        self.assertEqual(remaining, 0)
        self.assertEqual(events, [
            ("operator_created", operator_id, master_id),
            ("operator_deactivated", operator_id, master_id),
        ])

    def exercise_catalog(self, connect):
        with connect() as connection:
            connection.execute("DELETE FROM identity_login_limits")
            master_id = connection.execute("SELECT id FROM identity_users WHERE role = 'MASTER'").fetchone()[0]
        master, status = identity.login("master-test", "final-fixture-only-password", "127.0.0.1", None)
        self.assertEqual(status, 303)
        identity.create_operator(master_id, "catalog-reader", "reader-fixture-password")
        operator, status = identity.login("catalog-reader", "reader-fixture-password", "127.0.0.1", None)
        self.assertEqual(status, 303)
        admin = {"identity_session": master}
        reader = {"identity_session": operator}
        status, _, body = request("/catalog/new", admin)
        self.assertEqual(status, 200)
        form = {"csrf": csrf(body), "code": " rose-01 ", "description": "Rose body lotion",
                "variation": "100 ml", "barcode": "000123"}
        self.assertEqual(request("/catalog/new", reader, form)[0], 403)
        self.assertEqual(request("/catalog/new", admin, {**form, "csrf": "bad"})[0], 403)
        self.assertEqual(request("/catalog/new", admin, {**form, "description": ""})[0], 400)
        self.assertEqual(request("/catalog/new", admin, form)[0], 303)
        self.assertEqual(request("/catalog/new", admin, {**form, "code": "ROSE-01", "barcode": ""})[0], 409)
        self.assertEqual(request("/catalog/new", admin, {**form, "code": "rose-02"})[0], 409)
        self.assertEqual(request("/catalog/new", admin, {**form, "code": "rose-02", "barcode": "000124"})[0], 303)

        first = catalog.list_skus(True, "rose-01")[0]
        self.assertEqual(first["barcode"], "000123")
        sku_id = first["id"]
        path = f"/catalog/{sku_id}/edit"
        self.assertEqual(request(path, reader)[0], 403)
        self.assertEqual(request(path, admin)[0], 200)
        edit = {"csrf": form["csrf"], "version": 1, "description": "Rose body lotion updated", "barcode": "000123"}
        self.assertEqual(request(path, admin, {**edit, "code": "FORGED"})[0], 303)
        self.assertEqual(request(path, admin, {**edit, "description": "Stale edit"})[0], 409)
        status, _, body = request("/catalog", reader, query=b"q=rose-01")
        self.assertEqual(status, 200)
        self.assertIn(b"Rose body lotion updated", body)
        self.assertNotIn(b"ROSE-02", body)
        self.assertEqual(catalog.get_sku(sku_id)["code"], "ROSE-01")

        deactivate = f"/catalog/{sku_id}/deactivate"
        self.assertEqual(request(deactivate, admin, {"csrf": form["csrf"]})[0], 303)
        self.assertEqual(request(deactivate, admin, {"csrf": form["csrf"]})[0], 303)
        self.assertNotIn(b"ROSE-01", request("/catalog", reader)[2])
        self.assertIn(b"ROSE-01", request("/catalog", admin)[2])

        details = catalog.sku_details({"description": "Concurrent test"})
        def insert(code):
            try:
                catalog.create_sku(master_id, catalog.sku_code(code), details)
                return True
            except psycopg.errors.UniqueViolation:
                return False

        with ThreadPoolExecutor(max_workers=2) as pool:
            self.assertCountEqual(list(pool.map(insert, ["rose-03", "ROSE-03"])), [True, False])
        with self.assertRaises(psycopg.errors.ForeignKeyViolation):
            catalog.create_sku(-1, "ROLLBACK", details)
        self.assertEqual(catalog.list_skus(True, "ROLLBACK"), [])
        with connect() as connection:
            audit = connection.execute(
                "SELECT actor_id, action FROM catalog_audit WHERE sku_id = %s ORDER BY id", (sku_id,)
            ).fetchall()
        self.assertEqual(audit, [(master_id, action) for action in ("created", "edited", "deactivated")])

    def exercise_inventory(self, connect):
        with connect() as connection:
            connection.execute("DELETE FROM identity_login_limits")
            master_id = connection.execute("SELECT id FROM identity_users WHERE role = 'MASTER'").fetchone()[0]
        master, _ = identity.login("master-test", "final-fixture-only-password", "127.0.0.1", None)
        operator, _ = identity.login("catalog-reader", "reader-fixture-password", "127.0.0.1", None)
        admin = {"identity_session": master}
        reader = {"identity_session": operator}
        catalog.create_sku(master_id, "STOCK-001", catalog.sku_details({"description": "Stock fixture"}))
        sku_id = catalog.list_skus(True, "STOCK-001")[0]["id"]
        path = f"/stock/{sku_id}"
        status, _, body = request(path, admin)
        self.assertEqual(status, 200)
        form = {"csrf": csrf(body), "request_key": str(uuid4()), "kind": "entry", "quantity": "10", "reason": "Initial receipt"}
        self.assertEqual(request(path, reader, form)[0], 403)
        self.assertEqual(request(path, admin, {**form, "csrf": "bad"})[0], 403)
        for quantity in ("0", "-1", "0.5", "1000000001"):
            self.assertEqual(request(path, admin, {**form, "quantity": quantity})[0], 400)
        self.assertEqual(request(path, admin, {**form, "reason": " "})[0], 400)
        self.assertEqual(request(path, admin, form)[0], 303)
        self.assertEqual(request(path, admin, form)[0], 303)
        self.assertEqual(request(path, admin, {**form, "quantity": "11"})[0], 409)
        self.assertEqual(inventory.history(sku_id, 1)[0], 10)

        def withdraw(_):
            try:
                inventory.record(master_id, sku_id, -6, "Concurrent withdrawal", str(uuid4()))
                return True
            except inventory.StockConflict:
                return False

        with ThreadPoolExecutor(max_workers=2) as pool:
            self.assertCountEqual(list(pool.map(withdraw, range(2))), [True, False])
        self.assertEqual(inventory.history(sku_id, 1)[0], 4)
        with self.assertRaises(psycopg.errors.ForeignKeyViolation):
            inventory.record(-1, sku_id, 2, "Failed audit actor", str(uuid4()))
        self.assertEqual(inventory.history(sku_id, 1)[0], 4)

        key = str(uuid4())
        with ThreadPoolExecutor(max_workers=2) as pool:
            repeated = list(pool.map(
                lambda _: inventory.record(master_id, sku_id, 2, "Repeated receipt", key), range(2)
            ))
        self.assertEqual(repeated[0], repeated[1])
        self.assertEqual(inventory.history(sku_id, 1)[0], 6)

        balance, movements, _ = inventory.history(sku_id, 1)
        withdrawal_id = next(m["id"] for m in movements if m["delta"] == -6)
        compensation_form = {"csrf": form["csrf"], "request_key": str(uuid4()), "reason": "Reverse withdrawal"}
        compensate_path = f"{path}/compensate/{withdrawal_id}"
        self.assertEqual(request(compensate_path, admin, compensation_form)[0], 303)
        self.assertEqual(request(compensate_path, admin, compensation_form)[0], 303)
        self.assertEqual(request(compensate_path, admin, {**compensation_form, "request_key": str(uuid4())})[0], 409)
        self.assertEqual(inventory.history(sku_id, 1)[0], 12)
        self.assertEqual(request(path, reader)[0], 200)

        # Inactivation holds the same SKU lock as a movement.
        with connect() as connection:
            connection.execute("UPDATE catalog_skus SET active = false WHERE id = %s", (sku_id,))
            with ThreadPoolExecutor(max_workers=1) as pool:
                pending = pool.submit(inventory.record, master_id, sku_id, 1, "Inactive SKU", str(uuid4()))
                try:
                    deadline = monotonic() + 5
                    while monotonic() < deadline:
                        with connect() as observer:
                            waiting = observer.execute(
                                "SELECT 1 FROM pg_stat_activity WHERE wait_event_type = 'Lock' AND query LIKE '%%SELECT active FROM catalog_skus%%'"
                            ).fetchone()
                        if waiting:
                            break
                        sleep(0.05)
                    else:
                        self.fail("Movement did not wait for SKU inactivation.")
                finally:
                    connection.commit()
                with self.assertRaises(inventory.StockConflict):
                    pending.result(timeout=5)
        self.assertEqual(request(path, reader)[0], 404)
        self.assertNotIn(b"STOCK-001", request("/stock", reader)[2])
        self.assertIn(b"STOCK-001", request("/stock", admin)[2])
        self.assertEqual(inventory.history(sku_id, 1)[0], 12)
