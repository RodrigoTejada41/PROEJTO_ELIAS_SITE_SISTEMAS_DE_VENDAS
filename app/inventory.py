"""Inventory ledger with serialized SKU movements and idempotent requests."""

from uuid import UUID

import psycopg
from psycopg.rows import dict_row


class StockConflict(ValueError):
    pass


def negative_allowed():
    with psycopg.connect() as connection:
        return connection.execute("SELECT allow_negative FROM inventory_policy WHERE id").fetchone()[0]


def set_negative_policy(actor_id, allowed):
    with psycopg.connect() as connection:
        changed = connection.execute(
            """UPDATE inventory_policy SET allow_negative = %s
               WHERE id AND allow_negative <> %s RETURNING id""", (allowed, allowed),
        ).fetchone()
        if changed:
            connection.execute(
                "INSERT INTO inventory_policy_audit (actor_id, allow_negative) VALUES (%s, %s)",
                (actor_id, allowed),
            )


def list_balances(include_inactive: bool):
    with psycopg.connect(row_factory=dict_row) as connection:
        return connection.execute(
            """
            SELECT sku.id, sku.code, sku.description, sku.active, coalesce(sum(m.delta), 0) AS balance
            FROM catalog_skus AS sku LEFT JOIN inventory_movements AS m ON m.sku_id = sku.id
            WHERE sku.active OR %s
            GROUP BY sku.id ORDER BY sku.description, sku.id
            """, (include_inactive,),
        ).fetchall()


def history(sku_id: int, page: int):
    with psycopg.connect(row_factory=dict_row) as connection:
        balance = connection.execute(
            "SELECT coalesce(sum(delta), 0) AS balance FROM inventory_movements WHERE sku_id = %s", (sku_id,)
        ).fetchone()["balance"]
        movements = connection.execute(
            """
            SELECT m.*, actor.username,
                   EXISTS (SELECT 1 FROM inventory_movements AS compensation
                           WHERE compensation.compensates_id = m.id) AS compensated
            FROM inventory_movements AS m
            JOIN identity_users AS actor ON actor.id = m.actor_id
            WHERE m.sku_id = %s ORDER BY m.id DESC LIMIT 51 OFFSET %s
            """, (sku_id, (page - 1) * 50),
        ).fetchall()
        return balance, movements[:50], len(movements) > 50


def record(actor_id: int, sku_id: int, delta: int | None, reason: str,
           request_key: str, compensates_id: int | None = None) -> int:
    with psycopg.connect() as connection:
        return record_in(connection, actor_id, sku_id, delta, reason, request_key, compensates_id)


def record_in(connection, actor_id: int, sku_id: int, delta: int | None, reason: str,
           request_key: str, compensates_id: int | None = None, sale_id: int | None = None, allow_inactive: bool = False) -> int:
    reason = reason.strip()
    if not 3 <= len(reason) <= 240 or chr(0) in reason:
        raise ValueError("reason")
    key = UUID(request_key)
    if compensates_id is None and (type(delta) is not int or not 0 < abs(delta) <= 1000000000):
        raise ValueError("quantity")
    connection.execute("SELECT pg_advisory_xact_lock(hashtextextended(%s, 0))", (str(key),))
    if compensates_id is not None:
        original = connection.execute(
            "SELECT delta, sale_id FROM inventory_movements WHERE id = %s AND sku_id = %s",
            (compensates_id, sku_id),
        ).fetchone()
        if original is None:
            raise ValueError("original")
        if original[1] is not None and original[1] != sale_id:
            raise StockConflict("sale")
        delta = -original[0]

    previous = connection.execute(
        """
        SELECT id, actor_id, sku_id, delta, reason, compensates_id, sale_id
        FROM inventory_movements WHERE request_key = %s
        """, (key,),
    ).fetchone()
    if previous:
        if previous[1:] != (actor_id, sku_id, delta, reason, compensates_id, sale_id):
            raise StockConflict("request")
        return previous[0]

    sku = connection.execute(
        "SELECT active FROM catalog_skus WHERE id = %s FOR UPDATE", (sku_id,)
    ).fetchone()
    if sku is None or (not sku[0] and not allow_inactive):
        raise StockConflict("inactive")
    if compensates_id is not None and connection.execute(
        "SELECT 1 FROM inventory_movements WHERE compensates_id = %s", (compensates_id,)
    ).fetchone():
        raise StockConflict("compensated")
    balance = connection.execute(
        "SELECT coalesce(sum(delta), 0) AS balance FROM inventory_movements WHERE sku_id = %s", (sku_id,)
    ).fetchone()[0]
    updated = balance + delta
    if not -2000000000 <= updated <= 2000000000:
        raise StockConflict("balance")
    if delta < 0:
        # Lock order is request key, SKU, policy. The policy writer only locks its own row.
        allowed = connection.execute("SELECT allow_negative FROM inventory_policy WHERE id FOR SHARE").fetchone()[0]
        if updated < 0 and not allowed:
            raise StockConflict("balance")
    return connection.execute(
        """
        INSERT INTO inventory_movements (sku_id, actor_id, delta, reason, request_key, compensates_id, sale_id)
        VALUES (%s, %s, %s, %s, %s, %s, %s) RETURNING id
        """, (sku_id, actor_id, delta, reason, key, compensates_id, sale_id),
    ).fetchone()[0]
