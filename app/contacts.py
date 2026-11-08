"""Customers and suppliers share contact data and preserve separate identities."""

import re

import psycopg
from psycopg.rows import dict_row


def details(form):
    result = {}
    for name, limit in (("name", 160), ("external_ref", 64), ("contact", 160), ("phone", 40), ("email", 254)):
        value = form.get(name, "").strip()
        if len(value) > limit or chr(0) in value or (name == "name" and not value):
            raise ValueError(name)
        result[name] = value or None
    if result["external_ref"]:
        if not re.fullmatch(r"[A-Za-z0-9._/-]{1,64}", result["external_ref"]):
            raise ValueError("external_ref")
        result["external_ref"] = result["external_ref"].upper()
    if result["email"] and not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", result["email"]):
        raise ValueError("email")
    return result


def list_parties(kind, include_inactive, query="", page=1):
    with psycopg.connect(row_factory=dict_row) as connection:
        rows = connection.execute(
            """
            SELECT * FROM commercial_parties
            WHERE kind = %(kind)s AND (active OR %(all)s)
              AND (strpos(lower(name), lower(%(query)s)) > 0
                   OR strpos(lower(coalesce(external_ref, '')), lower(%(query)s)) > 0)
            ORDER BY name, id LIMIT 51 OFFSET %(offset)s
            """,
            {"kind": kind, "all": include_inactive, "query": query, "offset": (page - 1) * 50},
        ).fetchall()
        return rows[:50], len(rows) > 50


def get_party(kind, party_id):
    with psycopg.connect(row_factory=dict_row) as connection:
        return connection.execute(
            "SELECT * FROM commercial_parties WHERE kind = %s AND id = %s",
            (kind, party_id),
        ).fetchone()


def audit(connection, party_id, actor_id, action):
    connection.execute(
        "INSERT INTO commercial_party_audit (party_id, actor_id, action) VALUES (%s, %s, %s)",
        (party_id, actor_id, action),
    )


def create(kind, actor_id, data):
    with psycopg.connect() as connection:
        party_id = connection.execute(
            """
            INSERT INTO commercial_parties (kind, name, external_ref, contact, phone, email)
            VALUES (%(kind)s, %(name)s, %(external_ref)s, %(contact)s, %(phone)s, %(email)s)
            RETURNING id
            """, {**data, "kind": kind},
        ).fetchone()[0]
        audit(connection, party_id, actor_id, "created")
        return party_id


def edit(kind, party_id, actor_id, version, data):
    with psycopg.connect() as connection:
        changed = connection.execute(
            """
            UPDATE commercial_parties SET name = %(name)s, external_ref = %(external_ref)s,
                contact = %(contact)s, phone = %(phone)s, email = %(email)s, version = version + 1
            WHERE id = %(id)s AND kind = %(kind)s AND version = %(version)s RETURNING id
            """, {**data, "kind": kind, "id": party_id, "version": version},
        ).fetchone()
        if changed:
            audit(connection, party_id, actor_id, "edited")
        return changed is not None


def deactivate(kind, party_id, actor_id):
    with psycopg.connect() as connection:
        changed = connection.execute(
            """
            UPDATE commercial_parties SET active = false, version = version + 1
            WHERE id = %s AND kind = %s AND active RETURNING id
            """, (party_id, kind),
        ).fetchone()
        if changed:
            audit(connection, party_id, actor_id, "deactivated")
