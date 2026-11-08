"""USD costs and selling prices with versioned catalogue updates."""

import psycopg
from psycopg.rows import dict_row

from app import catalog, finance


def list_prices(is_master, query, page):
    with psycopg.connect(row_factory=dict_row) as connection:
        rows = connection.execute(
            """
            SELECT id, code, description, active, usd_price_minor,
                   CASE WHEN %(master)s THEN usd_cost_minor END AS usd_cost_minor
            FROM catalog_skus WHERE (active OR %(master)s)
              AND (strpos(lower(code), lower(%(query)s)) > 0 OR strpos(lower(description), lower(%(query)s)) > 0)
            ORDER BY description, id LIMIT 51 OFFSET %(offset)s
            """, {"master": is_master, "query": query, "offset": (page - 1) * 50},
        ).fetchall()
        return rows[:50], len(rows) > 50


def update(actor_id, sku_id, version, cost, price):
    cost_minor = finance.parse_amount(cost, 2, allow_zero=True)
    price_minor = finance.parse_amount(price, 2)
    with psycopg.connect() as connection:
        changed = connection.execute(
            """
            UPDATE catalog_skus SET usd_cost_minor = %s, usd_price_minor = %s, version = version + 1
            WHERE id = %s AND version = %s RETURNING id
            """, (cost_minor, price_minor, sku_id, version),
        ).fetchone()
        if changed:
            catalog.audit(connection, sku_id, actor_id, "edited")
        return changed is not None
