"""Administrative drafts, atomic confirmation and whole-sale cancellation."""

from datetime import date
from uuid import NAMESPACE_URL, uuid5

import psycopg
from psycopg.rows import dict_row, tuple_row

from app import finance, fx, inventory, commissions


class SaleConflict(ValueError):
    pass


def audit(connection, actor_id, sale_id, action):
    connection.execute(
        "INSERT INTO sale_audit (actor_id, sale_id, action) VALUES (%s, %s, %s)",
        (actor_id, sale_id, action),
    )


def parties(connection, customer_id, seller_id):
    seller = connection.execute(
        "SELECT username FROM identity_users WHERE id = %s AND active FOR SHARE", (seller_id,)
    ).fetchone()
    if seller is None:
        raise SaleConflict("seller")
    customer = None
    if customer_id is not None:
        customer = connection.execute(
            "SELECT name FROM commercial_parties WHERE id = %s AND kind = 'customers' AND active FOR SHARE",
            (customer_id,),
        ).fetchone()
        if customer is None:
            raise SaleConflict("customer")
    return customer["name"] if customer else None, seller["username"]


def create(actor_id, customer_id, seller_id, due_date, discount, key, *, items=None):
    due = date.fromisoformat(due_date)
    if not 0 < seller_id <= 2**63 - 1 or (customer_id is not None and not 0 < customer_id <= 2**63 - 1):
        raise ValueError("party")
    discount_minor = finance.parse_amount(discount or "0", 2, allow_zero=True)
    with psycopg.connect(row_factory=dict_row) as connection:
        request_key = finance.request_lock(connection, "sale:", key)
        previous = connection.execute("SELECT * FROM sales WHERE request_key = %s", (request_key,)).fetchone()
        if previous:
            if (previous["actor_id"], previous["customer_id"], previous["seller_id"], previous["due_date"], previous["discount_minor"]) != (actor_id, customer_id, seller_id, due, discount_minor):
                raise SaleConflict("request")
            if items is not None:
                saved = connection.execute(
                    "SELECT sku_id, quantity, unit_minor FROM sale_items WHERE sale_id = %s ORDER BY sku_id",
                    (previous["id"],),
                ).fetchall()
                expected = [(sku, quantity, finance.parse_amount(price, 2) if price.strip() else None)
                            for sku, quantity, price in sorted(items)]
                if len(saved) != len(expected) or any(
                    (row["sku_id"], row["quantity"]) != (sku, quantity)
                    or (minor is not None and row["unit_minor"] != minor)
                    for row, (sku, quantity, minor) in zip(saved, expected)
                ):
                    raise SaleConflict("request")
            return previous["id"]
        customer_name, seller_name = parties(connection, customer_id, seller_id)
        sale_id = connection.execute(
            """
            INSERT INTO sales (customer_id, seller_id, actor_id, currency, scale, discount_minor,
                               due_date, request_key, customer_name, seller_name)
            VALUES (%s, %s, %s, 'USD', 2, %s, %s, %s, %s, %s) RETURNING id
            """, (customer_id, seller_id, actor_id, discount_minor, due, request_key, customer_name, seller_name),
        ).fetchone()["id"]
        audit(connection, actor_id, sale_id, "created")
        if items:
            replace_items(connection, actor_id, locked(connection, sale_id), items)
        return sale_id


def locked(connection, sale_id):
    sale = connection.execute("SELECT * FROM sales WHERE id = %s FOR UPDATE", (sale_id,)).fetchone()
    if sale is None:
        raise SaleConflict("sale")
    return sale


def draft_version(sale, version):
    if sale["status"] != "draft" or sale["version"] != version:
        raise SaleConflict("version")


def total(connection, sale):
    gross = connection.execute(
        "SELECT coalesce(sum(quantity::numeric * unit_minor), 0) AS gross FROM sale_items WHERE sale_id = %s", (sale["id"],)
    ).fetchone()["gross"]
    net = int(gross) - sale["discount_minor"]
    if gross > 999999999999:
        raise SaleConflict("amount")
    return int(gross), net


def set_item(actor_id, sale_id, sku_id, version, quantity, price):
    if not 0 < sku_id <= 2**63 - 1 or not 0 < quantity <= 1000000000:
        raise ValueError("quantity")
    with psycopg.connect(row_factory=dict_row) as connection:
        sale = locked(connection, sale_id)
        draft_version(sale, version)
        set_item_in(connection, sale_id, sku_id, quantity, price)
        total(connection, sale)
        connection.execute("UPDATE sales SET version = version + 1 WHERE id = %s", (sale_id,))
        audit(connection, actor_id, sale_id, "item_set")


def set_item_in(connection, sale_id, sku_id, quantity, price):
    sku = connection.execute(
        "SELECT * FROM catalog_skus WHERE id = %s AND active FOR SHARE", (sku_id,)
    ).fetchone()
    if sku is None:
        raise SaleConflict("sku")
    minor = finance.parse_amount(price, 2) if price.strip() else sku["usd_price_minor"]
    if minor is None:
        raise SaleConflict("price")
    connection.execute(
        """
        INSERT INTO sale_items (sale_id, sku_id, code_snapshot, description_snapshot, quantity, unit_minor)
        VALUES (%s, %s, %s, %s, %s, %s)
        ON CONFLICT (sale_id, sku_id) DO UPDATE SET
            code_snapshot = excluded.code_snapshot, description_snapshot = excluded.description_snapshot,
            quantity = excluded.quantity, unit_minor = excluded.unit_minor
        """, (sale_id, sku_id, sku["code"], sku["description"], quantity, minor),
    )


def replace_items(connection, actor_id, sale, items):
    sale_id = sale["id"]
    connection.execute(
        "DELETE FROM sale_items WHERE sale_id = %s AND NOT (sku_id = ANY(%s))",
        (sale_id, [item[0] for item in items]),
    )
    for sku_id, quantity, price in sorted(items):
        set_item_in(connection, sale_id, sku_id, quantity, price)
    total(connection, sale)
    audit(connection, actor_id, sale_id, "item_set")


def save_draft(actor_id, sale_id, version, customer_id, seller_id, due_date, discount, items):
    due = date.fromisoformat(due_date)
    discount_minor = finance.parse_amount(discount or "0", 2, allow_zero=True)
    if not 0 < seller_id <= 2**63 - 1 or (customer_id is not None and not 0 < customer_id <= 2**63 - 1):
        raise ValueError("party")
    with psycopg.connect(row_factory=dict_row) as connection:
        sale = locked(connection, sale_id)
        draft_version(sale, version)
        customer_name, seller_name = parties(connection, customer_id, seller_id)
        connection.execute(
            """UPDATE sales SET customer_id = %s, seller_id = %s, due_date = %s,
               discount_minor = %s, customer_name = %s, seller_name = %s, version = version + 1 WHERE id = %s""",
            (customer_id, seller_id, due, discount_minor, customer_name, seller_name, sale_id),
        )
        sale["discount_minor"] = discount_minor
        replace_items(connection, actor_id, sale, items)
        return version + 1


def search_products(query):
    with psycopg.connect(row_factory=dict_row) as connection:
        return connection.execute(
            """
            SELECT sku.id::text AS id, sku.code, sku.description, sku.usd_price_minor,
                   EXISTS (SELECT 1 FROM catalog_images WHERE sku_id = sku.id) AS has_image,
                   (SELECT coalesce(sum(delta), 0)::bigint FROM inventory_movements
                    WHERE sku_id = sku.id) AS balance
            FROM catalog_skus sku
            WHERE sku.active AND (strpos(lower(sku.code), lower(%s)) > 0
                OR strpos(lower(sku.description), lower(%s)) > 0 OR strpos(sku.barcode, %s) > 0)
            ORDER BY CASE WHEN sku.code = upper(%s) OR sku.barcode = %s THEN 0 ELSE 1 END,
                     sku.description, sku.id LIMIT 20
            """,
            (query, query, query, query, query),
        ).fetchall()


def remove_item(actor_id, sale_id, sku_id, version):
    with psycopg.connect(row_factory=dict_row) as connection:
        sale = locked(connection, sale_id)
        draft_version(sale, version)
        connection.execute("DELETE FROM sale_items WHERE sale_id = %s AND sku_id = %s", (sale_id, sku_id))
        connection.execute("UPDATE sales SET version = version + 1 WHERE id = %s", (sale_id,))
        audit(connection, actor_id, sale_id, "item_removed")


def stock_key(sale_id, sku_id, action):
    return str(uuid5(NAMESPACE_URL, f"esther-sale/{sale_id}/{sku_id}/{action}"))


def lock_stock_keys(connection, sale_id, items, action):
    # Keep the ledger lock order: request keys first, then SKU rows in ID order.
    for item in items:
        connection.execute(
            "SELECT pg_advisory_xact_lock(hashtextextended(%s, 0))",
            (stock_key(sale_id, item["sku_id"], action),),
        )
    connection.execute(
        "SELECT id FROM catalog_skus WHERE id = ANY(%s) ORDER BY id FOR UPDATE",
        ([item["sku_id"] for item in items],),
    ).fetchall()


def confirm(actor_id, sale_id, version):
    with psycopg.connect(row_factory=dict_row) as connection:
        sale = locked(connection, sale_id)
        if sale["status"] == "confirmed":
            return connection.execute("SELECT id FROM finance_titles WHERE sale_id = %s", (sale_id,)).fetchone()["id"]
        draft_version(sale, version)
        items = connection.execute("SELECT * FROM sale_items WHERE sale_id = %s ORDER BY sku_id", (sale_id,)).fetchall()
        _, net = total(connection, sale)
        if not items or not 0 < net <= 999999999999:
            raise SaleConflict("amount")
        customer_name, seller_name = parties(connection, sale["customer_id"], sale["seller_id"])
        rule = commissions.snapshot_in(connection, sale["seller_id"])
        if rule is None:
            raise SaleConflict("commission_rule")
        quote = fx.current_in(connection)
        if quote is None:
            raise SaleConflict("fx")
        lock_stock_keys(connection, sale_id, items, "confirm")
        for item in items:
            sku = connection.execute("SELECT * FROM catalog_skus WHERE id = %s", (item["sku_id"],)).fetchone()
            connection.execute(
                "UPDATE sale_items SET code_snapshot = %s, description_snapshot = %s WHERE sale_id = %s AND sku_id = %s",
                (sku["code"], sku["description"], sale_id, item["sku_id"]),
            )
            with connection.cursor(row_factory=tuple_row) as ledger:
                inventory.record_in(
                    ledger, actor_id, item["sku_id"], -item["quantity"], f"VEN #{sale_id}",
                    stock_key(sale_id, item["sku_id"], "confirm"), sale_id=sale_id,
                )
        title_id = finance.create_title_in(
            connection, actor_id, "receivable", sale["customer_id"], f"VEN #{sale_id}",
            finance.format_amount(net, 2, "en"), sale["due_date"].isoformat(),
            str(uuid5(NAMESPACE_URL, f"esther-sale/{sale_id}/receivable")), "USD",
        )
        connection.execute("UPDATE finance_titles SET sale_id = %s WHERE id = %s", (sale_id, title_id))
        connection.execute(
            """
            UPDATE sales SET status = 'confirmed', version = version + 1, confirmed_at = now(),
                customer_name = %s, seller_name = %s, fx_rate_id = %s WHERE id = %s
            """, (customer_name, seller_name, quote["id"], sale_id),
        )
        connection.execute("UPDATE sales SET commission_rule_id = %s WHERE id = %s", (rule["id"], sale_id))
        if rule["event"] == "confirmed":
            commissions.accrue_in(connection, actor_id, sale_id, rule, net)
        audit(connection, actor_id, sale_id, "confirmed")
        return title_id


def cancel(actor_id, sale_id):
    with psycopg.connect(row_factory=dict_row) as connection:
        sale = locked(connection, sale_id)
        if sale["status"] == "canceled":
            return
        if sale["status"] == "confirmed":
            title = connection.execute("SELECT * FROM finance_titles WHERE sale_id = %s FOR UPDATE", (sale_id,)).fetchone()
            if finance.paid(connection, title["id"]) != 0:
                raise SaleConflict("paid")
            originals = connection.execute(
                "SELECT id, sku_id FROM inventory_movements WHERE sale_id = %s AND compensates_id IS NULL ORDER BY sku_id",
                (sale_id,),
            ).fetchall()
            lock_stock_keys(connection, sale_id, originals, "cancel")
            for original in originals:
                with connection.cursor(row_factory=tuple_row) as ledger:
                    inventory.record_in(
                        ledger, actor_id, original["sku_id"], None, f"VEN #{sale_id} CANCEL",
                        stock_key(sale_id, original["sku_id"], "cancel"), compensates_id=original["id"],
                        sale_id=sale_id, allow_inactive=True,
                    )
            connection.execute("UPDATE finance_titles SET canceled = true WHERE id = %s", (title["id"],))
            commissions.reverse_accruals_in(connection, actor_id, sale_id)
            finance.audit(connection, actor_id, "canceled", title["id"])
        connection.execute("UPDATE sales SET status = 'canceled', canceled_at = now(), version = version + 1 WHERE id = %s", (sale_id,))
        audit(connection, actor_id, sale_id, "canceled")


def detail(sale_id):
    with psycopg.connect(row_factory=dict_row) as connection:
        connection.execute("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ, READ ONLY")
        sale = connection.execute(
            """
            SELECT sale.*, rate.pyg_per_usd AS applied_rate, rate.published_at AS rate_published_at, rate.source AS rate_source,
                   (SELECT id FROM finance_titles WHERE sale_id = sale.id) AS title_id
            FROM sales sale LEFT JOIN fx_rates rate ON rate.id = sale.fx_rate_id WHERE sale.id = %s
            """, (sale_id,),
        ).fetchone()
        if sale is None:
            return None, []
        items = connection.execute("SELECT * FROM sale_items WHERE sale_id = %s ORDER BY sku_id", (sale_id,)).fetchall()
        sale["gross"], sale["net"] = total(connection, sale)
        return sale, items


def list_sales(state, page):
    with psycopg.connect(row_factory=dict_row) as connection:
        rows = connection.execute(
            "SELECT * FROM sales WHERE %s = 'all' OR status = %s ORDER BY id DESC LIMIT 51 OFFSET %s",
            (state, state, (page - 1) * 50),
        ).fetchall()
        return rows[:50], len(rows) > 50


def options(*, include_skus=True):
    with psycopg.connect(row_factory=dict_row) as connection:
        sellers = connection.execute("SELECT id, username FROM identity_users WHERE active ORDER BY username").fetchall()
        customers = connection.execute("SELECT id, name FROM commercial_parties WHERE kind = 'customers' AND active ORDER BY name LIMIT 1000").fetchall()
        skus = connection.execute("SELECT id, code, description, usd_price_minor FROM catalog_skus WHERE active ORDER BY code LIMIT 1000").fetchall() if include_skus else []
        return sellers, customers, skus
