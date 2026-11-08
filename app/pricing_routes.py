from fastapi import APIRouter, Depends, HTTPException, Request

from app import catalog, finance, fx, pricing
from app.web import is_admin_role
from app.web import active_session, master_session, read_catalog_form, render, redirect, change_language, check_csrf

router = APIRouter()


@router.get("/fx")
def fx_page(request: Request, lang: str | None = None, master=Depends(master_session)):
    if lang is not None:
        return change_language(request, "/fx", lang)
    state = fx.state()
    return render(request, "fx.html", section="pricing", csrf=master[1], is_master=True, policy=state, quote=state["active"], error=None)


@router.post("/fx")
def configure_fx(request: Request, master=Depends(master_session), form: dict = Depends(read_catalog_form)):
    check_csrf(form, master[1])
    try:
        fx.configure(master[0], form.get("mode", ""), form.get("rate", ""), form.get("reason", ""))
    except ValueError:
        state = fx.state()
        return render(request, "fx.html", 400, section="pricing", csrf=master[1], is_master=True, policy=state, quote=state["active"], error="fx_invalid")
    return redirect("/fx")


@router.post("/fx/refresh")
def refresh_fx(request: Request, master=Depends(master_session), form: dict = Depends(read_catalog_form)):
    check_csrf(form, master[1])
    fx.refresh()
    return redirect("/fx")


@router.get("/pricing")
def price_list(request: Request, q: str = "", page: int = 1, lang: str | None = None, account=Depends(active_session)):
    if lang is not None:
        return change_language(request, "/pricing", lang)
    query = q.strip().replace(chr(0), "")[:160]
    page = max(1, min(page, 1000000))
    rows, has_next = pricing.list_prices(is_admin_role(account[1]), query, page)
    return render(
        request, "pricing.html", section="pricing", csrf=account[2], is_master=is_admin_role(account[1]),
        rows=rows, query=query, page=page, has_next=has_next, quote=fx.state()["active"],
    )


def price_form(request, master, sku_id, status=200, error=None):
    sku = catalog.get_sku(sku_id) if 0 < sku_id <= 2**63 - 1 else None
    if sku is None:
        raise HTTPException(404)
    return render(request, "price_form.html", status, section="pricing", csrf=master[1], is_master=True, sku=sku, error=error)


@router.get("/pricing/{sku_id}")
def price_edit(sku_id: int, request: Request, lang: str | None = None, master=Depends(master_session)):
    if lang is not None:
        return change_language(request, f"/pricing/{sku_id}", lang)
    return price_form(request, master, sku_id)


@router.post("/pricing/{sku_id}")
def save_price(sku_id: int, request: Request, master=Depends(master_session), form: dict = Depends(read_catalog_form)):
    check_csrf(form, master[1])
    if not 0 < sku_id <= 2**63 - 1:
        raise HTTPException(404)
    try:
        version = int(form.get("version", ""))
        if not 0 < version <= 2**63 - 1:
            raise ValueError("version")
        changed = pricing.update(master[0], sku_id, version, form.get("cost", ""), form.get("price", ""))
    except ValueError:
        return price_form(request, master, sku_id, 400, "finance_invalid")
    if not changed:
        return price_form(request, master, sku_id, 409, "sku_stale")
    return redirect("/pricing")
