"""Company profile and immutable issuer snapshots for sale receipts."""

import psycopg
from psycopg.rows import dict_row

from app import sales

FIELDS = {"name": 160, "trade_name": 160, "tax_id": 32, "address": 240, "phone": 48}


def profile():
    with psycopg.connect(row_factory=dict_row) as connection:
        return connection.execute("SELECT * FROM company_profile WHERE id = 1").fetchone() or {}


def save_profile(actor_id, values):
    if not values["name"] or any(len(values[key]) > limit or "\x00" in values[key]
                                 for key, limit in FIELDS.items()):
        raise ValueError("company_invalid")
    with psycopg.connect() as connection:
        connection.execute(
            """
            INSERT INTO company_profile (id, name, trade_name, tax_id, address, phone)
            VALUES (1, %(name)s, %(trade_name)s, %(tax_id)s, %(address)s, %(phone)s)
            ON CONFLICT (id) DO UPDATE SET name = excluded.name, trade_name = excluded.trade_name,
                tax_id = excluded.tax_id, address = excluded.address, phone = excluded.phone
            """,
            values,
        )
        connection.execute("INSERT INTO company_audit (actor_id) VALUES (%s)", (actor_id,))


def issue(actor_id, sale_id):
    with psycopg.connect() as connection:
        sale = connection.execute("SELECT status FROM sales WHERE id = %s FOR UPDATE", (sale_id,)).fetchone()
        if sale is None:
            return "not_found"
        if sale[0] != "confirmed":
            return "sale_conflict"
        if connection.execute("SELECT 1 FROM sale_receipts WHERE sale_id = %s", (sale_id,)).fetchone():
            return None
        issued = connection.execute(
            """
            INSERT INTO sale_receipts (sale_id, company_snapshot)
            SELECT %s, to_jsonb(profile) - 'id' FROM company_profile profile WHERE id = 1
            RETURNING sale_id
            """,
            (sale_id,),
        ).fetchone()
        if issued is None:
            return "receipt_company_required"
        sales.audit(connection, actor_id, sale_id, "receipt_issued")
        return None


def issuer(sale_id):
    with psycopg.connect() as connection:
        row = connection.execute(
            """
            SELECT receipt.company_snapshot FROM sale_receipts receipt
            JOIN sales sale ON sale.id = receipt.sale_id
            WHERE receipt.sale_id = %s AND sale.status = 'confirmed'
            """,
            (sale_id,),
        ).fetchone()
        return row[0] if row else None
