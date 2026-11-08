"""Money in integer minor units, immutable settlements and explicit reversals."""

from datetime import date
from decimal import Decimal
import re
from uuid import UUID

import psycopg
from psycopg.rows import dict_row

from app import fx, commissions


class FinanceConflict(ValueError):
    pass


def parse_amount(value, scale, allow_zero=False):
    value = value.strip()
    if not re.fullmatch(r"[0-9]{1,16}([.,][0-9]{1,4})?", value):
        raise ValueError("amount")
    normalized = value.replace(",", ".")
    if "." in normalized and len(normalized.split(".")[1]) > scale:
        raise ValueError("amount")
    scaled = Decimal(normalized) * (10 ** scale)
    if scaled != scaled.to_integral_value() or not (0 if allow_zero else 1) <= scaled <= 999999999999:
        raise ValueError("amount")
    return int(scaled)


def format_amount(minor, scale, locale="pt"):
    value = f"{Decimal(minor).scaleb(-scale):.{scale}f}"
    return value.replace(".", ",") if locale in ("pt", "es") else value


def settings():
    with psycopg.connect(row_factory=dict_row) as connection:
        return connection.execute("SELECT * FROM finance_settings WHERE id").fetchone()


def audit(connection, actor_id, action, title_id=None):
    connection.execute(
        "INSERT INTO finance_audit (actor_id, action, title_id) VALUES (%s, %s, %s)",
        (actor_id, action, title_id),
    )


def configure(actor_id, currency, scale):
    currency = currency.strip().upper()
    if currency not in fx.SCALES or scale != fx.SCALES[currency]:
        raise ValueError("currency")
    with psycopg.connect() as connection:
        connection.execute("SELECT pg_advisory_xact_lock(510052027)")
        current = connection.execute("SELECT currency, scale FROM finance_settings WHERE id FOR UPDATE").fetchone()
        if current == (currency, scale):
            return
        if connection.execute("SELECT 1 FROM finance_titles UNION ALL SELECT 1 FROM sales LIMIT 1").fetchone():
            raise FinanceConflict("currency_locked")
        connection.execute(
            """
            INSERT INTO finance_settings (currency, scale) VALUES (%s, %s)
            ON CONFLICT (id) DO UPDATE SET currency = excluded.currency, scale = excluded.scale
            """, (currency, scale),
        )
        audit(connection, actor_id, "configured")


def request_lock(connection, namespace, key):
    request_key = UUID(key)
    connection.execute("SELECT pg_advisory_xact_lock(hashtextextended(%s, 0))", (namespace + str(request_key),))
    return request_key


def create_title(actor_id, kind, party_id, description, amount, due_date, key, currency=None):
    with psycopg.connect(row_factory=dict_row) as connection:
        return create_title_in(connection, actor_id, kind, party_id, description, amount, due_date, key, currency)


def create_title_in(connection, actor_id, kind, party_id, description, amount, due_date, key, currency=None):
    description = description.strip()
    due = date.fromisoformat(due_date)
    if kind not in ("receivable", "payable") or not 1 <= len(description) <= 160 or chr(0) in description:
        raise ValueError("title")
    if party_id is not None and not 0 < party_id <= 2**63 - 1:
        raise ValueError("party")
    request_key = request_lock(connection, "title:", key)
    config = connection.execute("SELECT currency, scale FROM finance_settings WHERE id FOR SHARE").fetchone()
    if config is None:
        raise FinanceConflict("currency_required")
    currency = currency or config["currency"]
    if currency not in fx.SCALES:
        raise ValueError("currency")
    scale = fx.SCALES[currency]
    minor = parse_amount(amount, scale)
    quote = fx.current_in(connection)
    previous = connection.execute("SELECT * FROM finance_titles WHERE request_key = %s", (request_key,)).fetchone()
    if previous:
        if (previous["actor_id"], previous["kind"], previous["party_id"], previous["description"],
            previous["amount_minor"], previous["due_date"], previous["currency"]) != (actor_id, kind, party_id, description, minor, due, currency):
            raise FinanceConflict("request")
        return previous["id"]
    if party_id is not None:
        party = connection.execute(
            "SELECT kind, active FROM commercial_parties WHERE id = %s FOR SHARE", (party_id,)
        ).fetchone()
        if not party or not party["active"] or party["kind"] != ("customers" if kind == "receivable" else "suppliers"):
            raise ValueError("party")
    title_id = connection.execute(
        """
        INSERT INTO finance_titles
            (kind, party_id, description, amount_minor, currency, scale, due_date, actor_id, request_key, fx_rate_id)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s) RETURNING id
        """,
        (kind, party_id, description, minor, currency, scale, due, actor_id, request_key, quote["id"] if quote else None),
    ).fetchone()["id"]
    audit(connection, actor_id, "created", title_id)
    return title_id


def paid(connection, title_id):
    return connection.execute(
        """
        SELECT coalesce(sum(s.amount_minor), 0) AS paid FROM finance_settlements s
        WHERE s.title_id = %s AND NOT EXISTS (
            SELECT 1 FROM finance_reversals r WHERE r.settlement_id = s.id)
        """, (title_id,),
    ).fetchone()["paid"]


def locked_title(connection, title_id):
    row = connection.execute("SELECT * FROM finance_titles WHERE id = %s FOR UPDATE", (title_id,)).fetchone()
    if row is None:
        raise FinanceConflict("title")
    return row


def settle(actor_id, title_id, amount, method, key, payment_currency=None):
    with psycopg.connect(row_factory=dict_row) as connection:
        return settle_in(connection, actor_id, title_id, amount, method, key, payment_currency)


def settle_in(connection, actor_id, title_id, amount, method, key, payment_currency=None):
    if method not in ("cash", "transfer", "card", "other"):
        raise ValueError("method")
    request_key = request_lock(connection, "settlement:", key)
    title = locked_title(connection, title_id)
    currency = payment_currency or title["currency"]
    if currency not in fx.SCALES:
        raise ValueError("currency")
    payment_minor = parse_amount(amount, fx.SCALES[currency])
    previous = connection.execute("SELECT * FROM finance_settlements WHERE request_key = %s", (request_key,)).fetchone()
    if previous:
        if (previous["actor_id"], previous["title_id"], previous["payment_amount_minor"], previous["payment_currency"], previous["method"]) != (actor_id, title_id, payment_minor, currency, method):
            raise FinanceConflict("request")
        return previous["id"]
    if connection.execute("SELECT 1 FROM commission_payouts WHERE title_id = %s", (title_id,)).fetchone():
        raise FinanceConflict("commission_payout")
    quote = fx.current_in(connection)
    if currency != title["currency"] and quote is None:
        raise FinanceConflict("fx")
    minor = fx.convert_minor(payment_minor, currency, title["currency"], quote["pyg_per_usd"] if quote else None)
    if minor < 1 or title["canceled"] or minor > title["amount_minor"] - paid(connection, title_id):
        raise FinanceConflict("balance")
    settlement_id = connection.execute(
        """
        INSERT INTO finance_settlements (title_id, actor_id, amount_minor, method, request_key, payment_currency, payment_amount_minor, fx_rate_id)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s) RETURNING id
        """, (title_id, actor_id, minor, method, request_key, currency, payment_minor, quote["id"] if quote and currency != title["currency"] else None),
    ).fetchone()["id"]
    commissions.on_received_in(connection, actor_id, title_id, settlement_id, minor)
    audit(connection, actor_id, "settled", title_id)
    return settlement_id


def reverse(actor_id, settlement_id, reason, key):
    reason = reason.strip()
    if not 3 <= len(reason) <= 240 or chr(0) in reason:
        raise ValueError("reason")
    with psycopg.connect(row_factory=dict_row) as connection:
        request_key = request_lock(connection, "reversal:", key)
        settlement = connection.execute("SELECT * FROM finance_settlements WHERE id = %s", (settlement_id,)).fetchone()
        if settlement is None:
            raise FinanceConflict("settlement")
        locked_title(connection, settlement["title_id"])
        previous = connection.execute(
            "SELECT * FROM finance_reversals WHERE request_key = %s OR settlement_id = %s",
            (request_key, settlement_id),
        ).fetchone()
        if previous:
            if (previous["settlement_id"], previous["actor_id"], previous["reason"], previous["request_key"]) != (settlement_id, actor_id, reason, request_key):
                raise FinanceConflict("request")
            return
        connection.execute(
            "INSERT INTO finance_reversals (settlement_id, actor_id, reason, request_key) VALUES (%s, %s, %s, %s)",
            (settlement_id, actor_id, reason, request_key),
        )
        commissions.on_reversed_in(connection, actor_id, settlement_id)
        audit(connection, actor_id, "reversed", settlement["title_id"])


def cancel(actor_id, title_id):
    with psycopg.connect(row_factory=dict_row) as connection:
        title = locked_title(connection, title_id)
        if title["sale_id"] is not None:
            raise FinanceConflict("sale")
        if title["canceled"]:
            return
        if paid(connection, title_id) != 0:
            raise FinanceConflict("balance")
        connection.execute("UPDATE finance_titles SET canceled = true WHERE id = %s", (title_id,))
        audit(connection, actor_id, "canceled", title_id)


def detail(title_id):
    with psycopg.connect(row_factory=dict_row) as connection:
        connection.execute("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ, READ ONLY")
        title = connection.execute(
            """
            SELECT title.*, party.name AS party_name,
                   (SELECT seller_id FROM commission_payouts WHERE title_id = title.id) AS commission_seller_id
            FROM finance_titles title
            LEFT JOIN commercial_parties party ON party.id = title.party_id WHERE title.id = %s
            """, (title_id,),
        ).fetchone()
        if title is None:
            return None, []
        title["paid"] = paid(connection, title_id)
        title["remaining"] = title["amount_minor"] - title["paid"]
        entries = connection.execute(
            """
            SELECT s.*, r.reason AS reversal_reason, r.occurred_at AS reversed_at, rate.pyg_per_usd AS applied_rate, rate.source AS rate_source
            FROM finance_settlements s LEFT JOIN finance_reversals r ON r.settlement_id = s.id
            LEFT JOIN fx_rates rate ON rate.id = s.fx_rate_id
            WHERE s.title_id = %s ORDER BY s.id DESC
            """, (title_id,),
        ).fetchall()
        return title, entries


def list_titles(kind, state, page):
    with psycopg.connect(row_factory=dict_row) as connection:
        rows = connection.execute(
            """
            WITH titles AS (
                SELECT t.*, coalesce(p.paid, 0) AS paid
                FROM finance_titles t LEFT JOIN (
                    SELECT s.title_id, sum(s.amount_minor) AS paid FROM finance_settlements s
                    WHERE NOT EXISTS (SELECT 1 FROM finance_reversals r WHERE r.settlement_id = s.id)
                    GROUP BY s.title_id
                ) p ON p.title_id = t.id WHERE t.kind = %(kind)s
            )
            SELECT *, (NOT canceled AND amount_minor > paid AND due_date < (now() AT TIME ZONE 'UTC')::date) AS overdue
            FROM titles WHERE
                (%(state)s = 'all'
                 OR (%(state)s = 'canceled' AND canceled)
                 OR (%(state)s = 'paid' AND NOT canceled AND amount_minor = paid)
                 OR (%(state)s = 'open' AND NOT canceled AND amount_minor > paid))
            ORDER BY due_date, id LIMIT 51 OFFSET %(offset)s
            """, {"kind": kind, "state": state, "offset": (page - 1) * 50},
        ).fetchall()
        return rows[:50], len(rows) > 50
