"""MASTER-only finance screens. Currency is explicitly configured before use."""

from typing import Literal
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Request

from app import contacts, finance, fx
from app.web import master_session, read_catalog_form, read_form, parse_form, render, redirect, check_csrf, change_language

router = APIRouter()


async def read_finance_form(request: Request):
    return await parse_form(request, 8192, 8)

Kind = Literal["receivable", "payable"]


@router.get("/finance")
def finance_list(request: Request, kind: Kind = "receivable",
                 state: Literal["all", "open", "paid", "canceled"] = "open",
                 page: int = 1, lang: str | None = None, master=Depends(master_session)):
    if lang is not None:
        return change_language(request, "/finance", lang)
    page = max(1, min(page, 1000000))
    titles, has_next = finance.list_titles(kind, state, page)
    return render(
        request, "finance.html", section="finance", csrf=master[1], is_master=True,
        titles=titles, kind=kind, state=state, page=page, has_next=has_next, config=finance.settings(),
    )


@router.get("/finance/settings")
def finance_settings(request: Request, lang: str | None = None, master=Depends(master_session)):
    if lang is not None:
        return change_language(request, "/finance/settings", lang)
    return render(request, "finance_settings.html", section="finance", csrf=master[1], is_master=True, config=finance.settings(), error=None)


@router.post("/finance/settings")
def configure_finance(request: Request, master=Depends(master_session), form: dict = Depends(read_form)):
    check_csrf(form, master[1])
    error, status = None, 200
    try:
        currency = form.get("currency", "").strip().upper()
        finance.configure(master[0], currency, fx.SCALES.get(currency, -1))
    except finance.FinanceConflict:
        error, status = "currency_locked", 409
    except ValueError:
        error, status = "finance_invalid", 400
    if not error:
        return redirect("/finance")
    return render(request, "finance_settings.html", status, section="finance", csrf=master[1], is_master=True, config=finance.settings(), error=error)


def title_form(request, master, kind, form=None, status=200, error=None):
    parties, _ = contacts.list_parties("customers" if kind == "receivable" else "suppliers", False)
    return render(
        request, "finance_form.html", status, section="finance", csrf=master[1], is_master=True,
        kind=kind, form=form or {}, config=finance.settings(), parties=parties,
        request_key=(form or {}).get("request_key") or str(uuid4()), error=error,
    )


@router.get("/finance/new/{kind}")
def new_title(kind: Kind, request: Request, lang: str | None = None, master=Depends(master_session)):
    if lang is not None:
        return change_language(request, f"/finance/new/{kind}", lang)
    return title_form(request, master, kind)


@router.post("/finance/new/{kind}")
def create_title(kind: Kind, request: Request, master=Depends(master_session), form: dict = Depends(read_finance_form)):
    check_csrf(form, master[1])
    try:
        party_id = int(form["party_id"]) if form.get("party_id") else None
        title_id = finance.create_title(
            master[0], kind, party_id, form.get("description", ""), form.get("amount", ""),
            form.get("due_date", ""), form.get("request_key", ""), form.get("currency"),
        )
    except finance.FinanceConflict:
        return title_form(request, master, kind, form, 409, "finance_conflict")
    except ValueError:
        return title_form(request, master, kind, form, 400, "finance_invalid")
    return redirect(f"/finance/{title_id}")


def require_title(title_id):
    if not 0 < title_id <= 2**63 - 1:
        raise HTTPException(404)
    title, entries = finance.detail(title_id)
    if title is None:
        raise HTTPException(404)
    return title, entries


def show_title(request, master, title_id, status=200, error=None):
    title, entries = require_title(title_id)
    return render(
        request, "finance_detail.html", status, section="finance", csrf=master[1], is_master=True,
        title=title, entries=entries, request_key=str(uuid4()), error=error, quote=fx.state()["active"],
    )


@router.get("/finance/{title_id}")
def title_detail(title_id: int, request: Request, lang: str | None = None, master=Depends(master_session)):
    require_title(title_id)
    if lang is not None:
        return change_language(request, f"/finance/{title_id}", lang)
    return show_title(request, master, title_id)


@router.post("/finance/{title_id}/settle")
def settle_title(title_id: int, request: Request, master=Depends(master_session), form: dict = Depends(read_finance_form)):
    check_csrf(form, master[1])
    require_title(title_id)
    try:
        finance.settle(master[0], title_id, form.get("amount", ""), form.get("method", ""), form.get("request_key", ""), form.get("payment_currency"))
    except finance.FinanceConflict:
        return show_title(request, master, title_id, 409, "finance_conflict")
    except ValueError:
        return show_title(request, master, title_id, 400, "finance_invalid")
    return redirect(f"/finance/{title_id}")


@router.post("/finance/{title_id}/cancel")
def cancel_title(title_id: int, request: Request, master=Depends(master_session), form: dict = Depends(read_form)):
    check_csrf(form, master[1])
    require_title(title_id)
    try:
        finance.cancel(master[0], title_id)
    except finance.FinanceConflict:
        return show_title(request, master, title_id, 409, "finance_conflict")
    return redirect(f"/finance/{title_id}")


@router.post("/finance/{title_id}/reverse/{settlement_id}")
def reverse_settlement(title_id: int, settlement_id: int, request: Request, master=Depends(master_session), form: dict = Depends(read_form)):
    check_csrf(form, master[1])
    _, entries = require_title(title_id)
    if not any(entry["id"] == settlement_id for entry in entries):
        raise HTTPException(404)
    try:
        finance.reverse(master[0], settlement_id, form.get("reason", ""), form.get("request_key", ""))
    except finance.FinanceConflict:
        return show_title(request, master, title_id, 409, "finance_conflict")
    except ValueError:
        return show_title(request, master, title_id, 400, "finance_invalid")
    return redirect(f"/finance/{title_id}")
