"""Contact administration and read-only customer access."""

from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Request
from psycopg.errors import UniqueViolation

from app import contacts
from app.web import is_admin_role
from app.web import (
    active_session, master_session, read_catalog_form, read_form,
    render, redirect, change_language, check_csrf,
)

router = APIRouter()
Kind = Literal["customers", "suppliers"]


def require_party(kind, party_id):
    party = contacts.get_party(kind, party_id) if 0 < party_id <= 2**63 - 1 else None
    if party is None:
        raise HTTPException(404)
    return party


def contact_form(request, kind, csrf, party=None, status=200, error=None):
    return render(
        request, "contact_form.html", status, section=kind, kind=kind,
        csrf=csrf, is_master=True, party=party or {}, error=error,
    )


@router.get("/contacts/{kind}")
def contact_list(kind: Kind, request: Request, q: str = "", page: int = 1, lang: str | None = None, account=Depends(active_session)):
    if kind == "suppliers" and not is_admin_role(account[1]):
        raise HTTPException(403)
    if not 1 <= page <= 1000000:
        raise HTTPException(400)
    if lang is not None:
        return change_language(request, f"/contacts/{kind}", lang)
    query = q.strip().replace(chr(0), "")[:160]
    parties, has_next = contacts.list_parties(kind, is_admin_role(account[1]), query, page)
    return render(
        request, "contacts.html", section=kind, kind=kind, parties=parties,
        csrf=account[2], is_master=is_admin_role(account[1]), query=query, page=page, has_next=has_next,
    )


@router.get("/contacts/{kind}/new")
def new_contact(kind: Kind, request: Request, lang: str | None = None, master=Depends(master_session)):
    if lang is not None:
        return change_language(request, f"/contacts/{kind}/new", lang)
    return contact_form(request, kind, master[1])


@router.post("/contacts/{kind}/new")
def create_contact(kind: Kind, request: Request, master=Depends(master_session), form: dict = Depends(read_catalog_form)):
    check_csrf(form, master[1])
    draft = {key: form.get(key, "") for key in ("name", "external_ref", "contact", "phone", "email")}
    try:
        contacts.create(kind, master[0], contacts.details(form))
    except ValueError:
        return contact_form(request, kind, master[1], draft, 400, "contact_invalid")
    except UniqueViolation:
        return contact_form(request, kind, master[1], draft, 409, "contact_duplicate")
    return redirect(f"/contacts/{kind}")


@router.get("/contacts/{kind}/{party_id}/edit")
def edit_contact(kind: Kind, party_id: int, request: Request, lang: str | None = None, master=Depends(master_session)):
    party = require_party(kind, party_id)
    if lang is not None:
        return change_language(request, f"/contacts/{kind}/{party_id}/edit", lang)
    return contact_form(request, kind, master[1], party)


@router.post("/contacts/{kind}/{party_id}/edit")
def save_contact(kind: Kind, party_id: int, request: Request, master=Depends(master_session), form: dict = Depends(read_catalog_form)):
    check_csrf(form, master[1])
    party = require_party(kind, party_id)
    draft = {**party, **{key: form.get(key, "") for key in ("name", "external_ref", "contact", "phone", "email", "version")}}
    try:
        version = int(form.get("version", ""))
        if not 0 < version <= 2**63 - 1:
            raise ValueError("version")
        changed = contacts.edit(kind, party_id, master[0], version, contacts.details(form))
    except ValueError:
        return contact_form(request, kind, master[1], draft, 400, "contact_invalid")
    except UniqueViolation:
        return contact_form(request, kind, master[1], draft, 409, "contact_duplicate")
    if not changed:
        return contact_form(request, kind, master[1], draft, 409, "sku_stale")
    return redirect(f"/contacts/{kind}")


@router.post("/contacts/{kind}/{party_id}/deactivate")
def deactivate_contact(kind: Kind, party_id: int, master=Depends(master_session), form: dict = Depends(read_form)):
    check_csrf(form, master[1])
    require_party(kind, party_id)
    contacts.deactivate(kind, party_id, master[0])
    return redirect(f"/contacts/{kind}")
