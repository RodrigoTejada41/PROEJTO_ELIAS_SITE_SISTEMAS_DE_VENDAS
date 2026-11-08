"""Versioned percentage rules, accruals, reversals and financial payouts."""

from datetime import datetime, timezone
from decimal import Decimal, ROUND_HALF_UP
import re
from uuid import NAMESPACE_URL, uuid5

import psycopg
from psycopg.rows import dict_row


class CommissionConflict(ValueError):
    pass


def seller_lock(connection, seller_id):
    connection.execute("SELECT pg_advisory_xact_lock(hashtextextended(%s, 0))", (f"commission-seller:{seller_id}",))


def audit(connection, actor_id, seller_id, action):
    connection.execute(
        "INSERT INTO commission_audit (actor_id, seller_id, action) VALUES (%s, %s, %s)",
        (actor_id, seller_id, action),
    )


def configure(actor_id, seller_id, percent, event):
    value = percent.strip().replace(",", ".")
    if not re.fullmatch(r"[0-9]{1,3}(\.[0-9]{1,4})?", value) or event not in ("confirmed", "received"):
        raise ValueError("rule")
    amount = Decimal(value)
    if not 0 <= amount <= 100 or not 0 < seller_id <= 2**63 - 1:
        raise ValueError("percent")
    with psycopg.connect(row_factory=dict_row) as connection:
        seller_lock(connection, seller_id)
        if connection.execute("SELECT 1 FROM identity_users WHERE id = %s AND active FOR SHARE", (seller_id,)).fetchone() is None:
            raise ValueError("seller")
        connection.execute(
            "INSERT INTO commission_rules (seller_id, percent, event, actor_id) VALUES (%s, %s, %s, %s)",
            (seller_id, amount, event, actor_id),
        )
        audit(connection, actor_id, seller_id, "rule_configured")


def snapshot_in(connection, seller_id):
    seller_lock(connection, seller_id)
    return connection.execute(
        "SELECT * FROM commission_rules WHERE seller_id = %s ORDER BY id DESC LIMIT 1", (seller_id,)
    ).fetchone()


def accrue_in(connection, actor_id, sale_id, rule, base_minor, settlement_id=None):
    amount = int((Decimal(base_minor) * rule["percent"] / 100).quantize(Decimal(1), rounding=ROUND_HALF_UP))
    connection.execute(
        """
        INSERT INTO commission_accruals (seller_id, sale_id, settlement_id, rule_id, base_minor, amount_minor)
        VALUES (%s, %s, %s, %s, %s, %s)
        """, (rule["seller_id"], sale_id, settlement_id, rule["id"], base_minor, amount),
    )
    audit(connection, actor_id, rule["seller_id"], "accrued")


def on_received_in(connection, actor_id, title_id, settlement_id, amount_minor):
    sale = connection.execute(
        """
        SELECT sale.id AS sale_id, rule.* FROM finance_titles title
        JOIN sales sale ON sale.id = title.sale_id
        JOIN commission_rules rule ON rule.id = sale.commission_rule_id
        WHERE title.id = %s AND rule.event = 'received'
        """, (title_id,),
    ).fetchone()
    if sale:
        seller_lock(connection, sale["seller_id"])
        accrue_in(connection, actor_id, sale["sale_id"], sale, amount_minor, settlement_id)


def reverse_accruals_in(connection, actor_id, sale_id, settlement_id=None):
    sale = connection.execute("SELECT seller_id FROM sales WHERE id = %s", (sale_id,)).fetchone()
    seller_lock(connection, sale["seller_id"])
    reversed_rows = connection.execute(
        """
        INSERT INTO commission_reversals (accrual_id, actor_id, reason)
        SELECT accrual.id, %s, 'Source reversal' FROM commission_accruals accrual
        WHERE accrual.sale_id = %s AND (%s::bigint IS NULL OR accrual.settlement_id = %s)
        ON CONFLICT (accrual_id) DO NOTHING RETURNING accrual_id
        """, (actor_id, sale_id, settlement_id, settlement_id),
    ).fetchall()
    if reversed_rows:
        audit(connection, actor_id, sale["seller_id"], "accrual_reversed")


def on_reversed_in(connection, actor_id, settlement_id):
    origin = connection.execute("SELECT sale_id FROM finance_titles WHERE id = (SELECT title_id FROM finance_settlements WHERE id = %s)", (settlement_id,)).fetchone()
    if origin and origin["sale_id"] is not None:
        reverse_accruals_in(connection, actor_id, origin["sale_id"], settlement_id)
    payout = connection.execute("SELECT seller_id FROM commission_payouts WHERE settlement_id = %s", (settlement_id,)).fetchone()
    if payout:
        seller_lock(connection, payout["seller_id"])
        audit(connection, actor_id, payout["seller_id"], "payout_reversed")


def balance_in(connection, seller_id):
    earned = connection.execute(
        """
        SELECT coalesce(sum(a.amount_minor), 0) AS amount FROM commission_accruals a
        WHERE a.seller_id = %s AND NOT EXISTS (SELECT 1 FROM commission_reversals r WHERE r.accrual_id = a.id)
        """, (seller_id,),
    ).fetchone()["amount"]
    paid = connection.execute(
        """
        SELECT coalesce(sum(p.amount_minor), 0) AS amount FROM commission_payouts p
        WHERE p.seller_id = %s AND NOT EXISTS (SELECT 1 FROM finance_reversals r WHERE r.settlement_id = p.settlement_id)
        """, (seller_id,),
    ).fetchone()["amount"]
    return int(earned), int(paid), int(earned - paid)


def payout(actor_id, seller_id, amount, method, currency, key):
    from app import finance, fx

    minor = finance.parse_amount(amount, 2)
    if not 0 < seller_id <= 2**63 - 1 or currency not in fx.SCALES or method not in ("cash", "transfer", "card", "other"):
        raise ValueError("payout")
    with psycopg.connect(row_factory=dict_row) as connection:
        request_key = finance.request_lock(connection, "commission-payout:", key)
        seller_lock(connection, seller_id)
        previous = connection.execute("SELECT * FROM commission_payouts WHERE request_key = %s", (request_key,)).fetchone()
        if previous:
            if (previous["actor_id"], previous["seller_id"], previous["amount_minor"], previous["method"], previous["payment_currency"]) != (actor_id, seller_id, minor, method, currency):
                raise CommissionConflict("request")
            return previous["id"]
        if balance_in(connection, seller_id)[2] < minor:
            raise CommissionConflict("balance")
        quote = fx.current_in(connection)
        if currency != "USD" and quote is None:
            raise CommissionConflict("fx")
        payment_minor = fx.convert_minor(minor, "USD", currency, quote["pyg_per_usd"] if quote else None)
        if fx.convert_minor(payment_minor, currency, "USD", quote["pyg_per_usd"] if quote else None) != minor:
            raise CommissionConflict("rounding")
        title_id = finance.create_title_in(
            connection, actor_id, "payable", None, f"COM #{seller_id}",
            finance.format_amount(minor, 2, "en"), datetime.now(timezone.utc).date().isoformat(),
            str(uuid5(NAMESPACE_URL, f"commission/{request_key}/title")), "USD",
        )
        settlement_id = finance.settle_in(
            connection, actor_id, title_id, finance.format_amount(payment_minor, fx.SCALES[currency], "en"),
            method, str(uuid5(NAMESPACE_URL, f"commission/{request_key}/settlement")), currency,
        )
        payout_id = connection.execute(
            """
            INSERT INTO commission_payouts
                (seller_id, actor_id, amount_minor, method, payment_currency, title_id, settlement_id, request_key)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s) RETURNING id
            """, (seller_id, actor_id, minor, method, currency, title_id, settlement_id, request_key),
        ).fetchone()["id"]
        audit(connection, actor_id, seller_id, "payout")
        return payout_id


def overview():
    with psycopg.connect(row_factory=dict_row) as connection:
        connection.execute("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ, READ ONLY")
        sellers = connection.execute(
            """
            SELECT account.id, account.username, rule.percent, rule.event
            FROM identity_users account LEFT JOIN LATERAL (
                SELECT percent, event FROM commission_rules WHERE seller_id = account.id ORDER BY id DESC LIMIT 1
            ) rule ON true ORDER BY account.username
            """
        ).fetchall()
        for seller in sellers:
            seller["earned"], seller["paid"], seller["balance"] = balance_in(connection, seller["id"])
        return sellers


def detail(seller_id):
    with psycopg.connect(row_factory=dict_row) as connection:
        connection.execute("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ, READ ONLY")
        seller = connection.execute("SELECT id, username FROM identity_users WHERE id = %s", (seller_id,)).fetchone()
        if seller is None:
            return None, [], []
        seller["earned"], seller["paid"], seller["balance"] = balance_in(connection, seller_id)
        accruals = connection.execute(
            """
            SELECT a.*, rule.percent, EXISTS (SELECT 1 FROM commission_reversals r WHERE r.accrual_id = a.id) AS reversed
            FROM commission_accruals a JOIN commission_rules rule ON rule.id = a.rule_id
            WHERE a.seller_id = %s ORDER BY a.id DESC LIMIT 50
            """, (seller_id,),
        ).fetchall()
        payouts = connection.execute(
            """
            SELECT p.*, EXISTS (SELECT 1 FROM finance_reversals r WHERE r.settlement_id = p.settlement_id) AS reversed
            FROM commission_payouts p WHERE p.seller_id = %s ORDER BY p.id DESC LIMIT 50
            """, (seller_id,),
        ).fetchall()
        return seller, accruals, payouts
