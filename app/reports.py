"""Read-only stock reporting and administrative audit."""

import csv
from datetime import date, datetime, time, timedelta, timezone
from io import StringIO

import psycopg
from psycopg.rows import dict_row

STOCK_QUERY = """
    SELECT sku.id, sku.code, sku.description, sku.active, coalesce(sum(m.delta), 0) AS balance
    FROM catalog_skus sku LEFT JOIN inventory_movements m ON m.sku_id = sku.id
    WHERE (strpos(lower(sku.code), lower(%(query)s)) > 0
           OR strpos(lower(sku.description), lower(%(query)s)) > 0)
      AND (%(status)s = 'all' OR sku.active = (%(status)s = 'active'))
    GROUP BY sku.id
"""


def stock(query, status, page=1, export=False, *, balance="all"):
    params = {"query": query, "status": status, "balance": balance, "offset": 0 if export else (page - 1) * 50, "limit": 10001 if export else 51}
    filtered = """WITH balances AS (""" + STOCK_QUERY + """)
        SELECT * FROM balances WHERE %(balance)s = 'all'
          OR (%(balance)s = 'positive' AND balance > 0)
          OR (%(balance)s = 'zero' AND balance = 0)
          OR (%(balance)s = 'negative' AND balance < 0)
    """
    with psycopg.connect(row_factory=dict_row) as connection:
        connection.execute("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ, READ ONLY")
        totals = connection.execute(
            "WITH filtered AS (" + filtered + ") SELECT count(*) AS skus, coalesce(sum(balance), 0) AS units FROM filtered",
            params,
        ).fetchone()
        rows = connection.execute(
            filtered + " ORDER BY description, id LIMIT %(limit)s OFFSET %(offset)s", params
        ).fetchall()
        if export:
            if len(rows) > 10000:
                raise ValueError("export_limit")
            return rows, totals, False
        return rows[:50], totals, len(rows) > 50


def csv_text(rows, labels):
    output = StringIO(newline="")
    writer = csv.writer(output)
    writer.writerow(labels)
    for row in rows:
        safe = [
            "'" + value if isinstance(value, str) and value.lstrip().startswith(("=", "+", "-", "@", "\t", "\r", "\n"))
            else value for value in row
        ]
        writer.writerow(safe)
    return "\ufeff" + output.getvalue()


def audit_period(start, end):
    lower = datetime.combine(date.fromisoformat(start), time.min, timezone.utc) if start else None
    upper = datetime.combine(date.fromisoformat(end) + timedelta(days=1), time.min, timezone.utc) if end else None
    if lower and upper and lower >= upper:
        raise ValueError("period")
    return lower, upper


def audit(source, start, end, page):
    with psycopg.connect(row_factory=dict_row) as connection:
        rows = connection.execute(
            """
            SELECT * FROM administrative_audit
            WHERE (%(source)s = 'all' OR source = %(source)s)
              AND (%(start)s::timestamptz IS NULL OR occurred_at >= %(start)s)
              AND (%(end)s::timestamptz IS NULL OR occurred_at < %(end)s)
            ORDER BY occurred_at DESC, source, id DESC LIMIT 51 OFFSET %(offset)s
            """, {"source": source, "start": start, "end": end, "offset": (page - 1) * 50},
        ).fetchall()
        return rows[:50], len(rows) > 50


def dashboard_stats(include_suppliers):
    with psycopg.connect() as connection:
        counts = connection.execute(
            """
            SELECT (SELECT count(*) FROM catalog_skus WHERE active),
                   (SELECT coalesce(sum(m.delta), 0) FROM inventory_movements m
                    JOIN catalog_skus sku ON sku.id = m.sku_id WHERE sku.active),
                   (SELECT count(*) FROM commercial_parties WHERE kind = 'customers' AND active),
                   (SELECT count(*) FROM commercial_parties WHERE kind = 'suppliers' AND active)
            """
        ).fetchone()
    cards = [("catalog", counts[0]), ("stock_units", counts[1]), ("customers", counts[2])]
    if include_suppliers:
        cards.append(("suppliers", counts[3]))
    return cards

CASH_QUERY = """
    SELECT 'settled'::text AS action, s.id, s.occurred_at, s.title_id,
           s.payment_currency AS currency, s.method, t.kind,
           s.payment_amount_minor * CASE WHEN t.kind = 'receivable' THEN 1 ELSE -1 END AS amount_minor
    FROM finance_settlements s JOIN finance_titles t ON t.id = s.title_id
    UNION ALL
    SELECT 'reversed', r.settlement_id, r.occurred_at, s.title_id,
           s.payment_currency, s.method, t.kind,
           s.payment_amount_minor * CASE WHEN t.kind = 'receivable' THEN -1 ELSE 1 END
    FROM finance_reversals r JOIN finance_settlements s ON s.id = r.settlement_id
    JOIN finance_titles t ON t.id = s.title_id
"""


def cash(start, end, currency, page=1, export=False, *, nature="all"):
    params = {"start": start, "end": end, "currency": currency, "nature": nature,
              "limit": 10001 if export else 51, "offset": 0 if export else (page - 1) * 50}
    filtered = """
        WITH events AS (""" + CASH_QUERY + """)
        SELECT * FROM events WHERE
            (%(start)s::timestamptz IS NULL OR occurred_at >= %(start)s)
            AND (%(end)s::timestamptz IS NULL OR occurred_at < %(end)s)
            AND (%(currency)s = 'all' OR currency = %(currency)s)
            AND (%(nature)s = 'all' OR (%(nature)s = 'reversed' AND action = 'reversed')
                 OR (action = 'settled' AND kind = %(nature)s))
    """
    with psycopg.connect(row_factory=dict_row) as connection:
        connection.execute("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ, READ ONLY")
        totals = connection.execute(
            "WITH filtered AS (" + filtered + ") SELECT currency, sum(amount_minor) AS amount_minor FROM filtered GROUP BY currency ORDER BY currency",
            params,
        ).fetchall()
        rows = connection.execute(
            filtered + " ORDER BY occurred_at DESC, action, id DESC LIMIT %(limit)s OFFSET %(offset)s", params
        ).fetchall()
        if export and len(rows) > 10000:
            raise ValueError("export_limit")
        return rows if export else rows[:50], totals, not export and len(rows) > 50


SALE_QUERY = """
        SELECT sale.id, sale.confirmed_at, sale.customer_name, sale.seller_name,
               (SELECT sum(item.quantity::numeric * item.unit_minor) FROM sale_items item
                WHERE item.sale_id = sale.id) - sale.discount_minor AS net_minor,
               rate.pyg_per_usd, rate.source AS rate_source
        FROM sales sale LEFT JOIN fx_rates rate ON rate.id = sale.fx_rate_id
        WHERE sale.status = 'confirmed'
          AND (%(start)s::timestamptz IS NULL OR sale.confirmed_at >= %(start)s)
          AND (%(end)s::timestamptz IS NULL OR sale.confirmed_at < %(end)s)
          AND (%(seller)s::bigint IS NULL OR sale.seller_id = %(seller)s)
    """

def sale_report(start, end, seller_id, page=1, export=False):
    params = {"start": start, "end": end, "seller": seller_id,
              "limit": 10001 if export else 51, "offset": 0 if export else (page - 1) * 50}
    with psycopg.connect(row_factory=dict_row) as connection:
        connection.execute("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ, READ ONLY")
        total = connection.execute(
            "WITH matched AS (" + SALE_QUERY + ") " + SALES_TOTAL,
            params,
        ).fetchone()
        rows = connection.execute(
            SALE_QUERY + " ORDER BY sale.confirmed_at DESC, sale.id DESC LIMIT %(limit)s OFFSET %(offset)s", params
        ).fetchall()
        if export and len(rows) > 10000:
            raise ValueError("export_limit")
        return rows if export else rows[:50], total, not export and len(rows) > 50


SALES_TOTAL = """
    SELECT count(*) AS count, coalesce(sum(net_minor), 0) AS net_minor,
           coalesce(sum(round(net_minor * pyg_per_usd / 100)), 0) AS pyg,
           coalesce(round(avg(net_minor)), 0) AS average_minor,
           count(*) FILTER (WHERE pyg_per_usd IS NULL) AS missing_rate
    FROM matched
"""

PRODUCT_RANKING = """
    SELECT item.sku_id, sku.code AS code_snapshot, sku.description,
           sum(item.quantity) AS quantity
    FROM matched sale JOIN sale_items item ON item.sale_id = sale.id
    JOIN catalog_skus sku ON sku.id = item.sku_id
    WHERE strpos(lower(sku.code), lower(%(query)s)) > 0
       OR strpos(lower(sku.description), lower(%(query)s)) > 0
       OR strpos(lower(item.description_snapshot), lower(%(query)s)) > 0
    GROUP BY item.sku_id, sku.code, sku.description
    ORDER BY quantity DESC, sku.code, item.sku_id
    LIMIT %(limit)s OFFSET %(offset)s
"""


def ranked_products(connection, params, query, limit, offset=0):
    return connection.execute(
        "WITH matched AS (" + SALE_QUERY + ") " + PRODUCT_RANKING,
        {**params, "query": query, "limit": limit, "offset": offset},
    ).fetchall()


def product_ranking(start, end, seller_id, query, page, export):
    with psycopg.connect(row_factory=dict_row) as connection:
        rows = ranked_products(connection, {"start": start, "end": end, "seller": seller_id},
                               query, 10001 if export else 51, 0 if export else (page - 1) * 50)
    if export and len(rows) > 10000:
        raise ValueError("export_limit")
    return rows if export else rows[:50], not export and len(rows) > 50


def top_products(start, end, seller_id=None):
    with psycopg.connect(row_factory=dict_row) as connection:
        return ranked_products(connection, {"start": start, "end": end, "seller": seller_id}, "", 20)


def dashboard_sales(start, end, seller_id):
    params = {"start": start, "end": end, "seller": seller_id}
    matched = "WITH matched AS (" + SALE_QUERY + ") "
    with psycopg.connect(row_factory=dict_row) as connection:
        connection.execute("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ, READ ONLY")
        total = connection.execute(matched + SALES_TOTAL, params).fetchone()
        trend = connection.execute(
            matched + """SELECT (confirmed_at AT TIME ZONE 'UTC')::date AS day, count(*) AS count,
                                sum(net_minor) AS amount
                         FROM matched GROUP BY day ORDER BY day""", params,
        ).fetchall()
        products = ranked_products(connection, params, "", 5)
    return total, trend, products


def sales_filters(start, end, seller_id):
    lower, upper = audit_period(start, end)
    seller = int(seller_id) if seller_id else None
    if seller is not None and not 0 < seller <= 2**63 - 1:
        raise ValueError("seller")
    return lower, upper, seller


def report_sellers():
    with psycopg.connect(row_factory=dict_row) as connection:
        return connection.execute(
            """SELECT id, username FROM identity_users u WHERE active OR EXISTS (
                   SELECT 1 FROM sales WHERE seller_id = u.id AND status = 'confirmed')
               ORDER BY username, id"""
        ).fetchall()
