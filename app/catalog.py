"""Product SKU validation, persistence and audit."""

import re

import psycopg
from psycopg.rows import dict_row


def sku_code(value: str) -> str:
    value = value.strip()
    if not re.fullmatch(r"[A-Za-z0-9._-]{1,64}", value):
        raise ValueError("code")
    return value.upper()


def sku_details(form: dict) -> dict:
    details = {}
    for field, limit in (("description", 160), ("brand", 100), ("category", 100), ("variation", 100)):
        value = form.get(field, "").strip()
        if len(value) > limit or chr(0) in value or (field == "description" and not value):
            raise ValueError(field)
        details[field] = value or None
    barcode = form.get("barcode", "").strip()
    if barcode and not re.fullmatch(r"[0-9]{1,32}", barcode):
        raise ValueError("barcode")
    details["barcode"] = barcode or None
    return details


def list_skus(include_inactive: bool, query: str):
    with psycopg.connect(row_factory=dict_row) as connection:
        return connection.execute(
            """
            SELECT catalog_skus.*, EXISTS (
                SELECT 1 FROM catalog_images WHERE sku_id = catalog_skus.id
            ) AS has_image FROM catalog_skus
            WHERE (active OR %(include_inactive)s)
              AND (strpos(lower(code), lower(%(query)s)) > 0
                   OR strpos(lower(description), lower(%(query)s)) > 0
                   OR %(query)s = '')
            ORDER BY description, id
            """,
            {"include_inactive": include_inactive, "query": query},
        ).fetchall()


def get_sku(sku_id: int):
    with psycopg.connect(row_factory=dict_row) as connection:
        return connection.execute(
            """SELECT catalog_skus.*, EXISTS (
                   SELECT 1 FROM catalog_images WHERE sku_id = catalog_skus.id
               ) AS has_image FROM catalog_skus WHERE id = %s""",
            (sku_id,),
        ).fetchone()


def audit(connection, sku_id: int, actor_id: int, action: str):
    connection.execute(
        "INSERT INTO catalog_audit (sku_id, actor_id, action) VALUES (%s, %s, %s)",
        (sku_id, actor_id, action),
    )


def create_sku(actor_id: int, code: str, details: dict):
    with psycopg.connect() as connection:
        insert_sku(connection, actor_id, code, details)


def insert_sku(connection, actor_id: int, code: str, details: dict):
    sku_id = connection.execute(
        """
        INSERT INTO catalog_skus (code, description, brand, category, variation, barcode)
        VALUES (%(code)s, %(description)s, %(brand)s, %(category)s, %(variation)s, %(barcode)s)
        RETURNING id
        """,
        {**details, "code": code},
    ).fetchone()[0]
    audit(connection, sku_id, actor_id, "created")


def update_sku(actor_id: int, sku_id: int, version: int, details: dict) -> bool:
    with psycopg.connect() as connection:
        changed = connection.execute(
            """
            UPDATE catalog_skus SET description = %(description)s, brand = %(brand)s,
                category = %(category)s, variation = %(variation)s, barcode = %(barcode)s,
                version = version + 1
            WHERE id = %(id)s AND version = %(version)s
            RETURNING id
            """,
            {**details, "id": sku_id, "version": version},
        ).fetchone()
        if changed is None:
            return False
        audit(connection, sku_id, actor_id, "edited")
        return True


def deactivate_sku(actor_id: int, sku_id: int):
    with psycopg.connect() as connection:
        changed = connection.execute(
            """
            UPDATE catalog_skus SET active = false, version = version + 1
            WHERE id = %s AND active RETURNING id
            """,
            (sku_id,),
        ).fetchone()
        if changed:
            audit(connection, sku_id, actor_id, "deactivated")
