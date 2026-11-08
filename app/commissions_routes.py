from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Request

from app import commissions, finance, fx, sales
from app.web import master_session, read_catalog_form, render, redirect, change_language, check_csrf

router = APIRouter()


def overview_page(request, master, status=200, error=None):
    sellers = commissions.overview()
    return render(
        request, "commissions.html", status, section="commissions", csrf=master[1], is_master=True,
        sellers=sellers, error=error,
    )


@router.get("/commissions")
def commission_list(request: Request, lang: str | None = None, master=Depends(master_session)):
    if lang is not None:
        return change_language(request, "/commissions", lang)
    return overview_page(request, master)


@router.post("/commissions/rules")
def configure_commission(request: Request, master=Depends(master_session), form: dict = Depends(read_catalog_form)):
    check_csrf(form, master[1])
    try:
        commissions.configure(master[0], int(form.get("seller_id", "")), form.get("percent", ""), "confirmed")
    except ValueError:
        return overview_page(request, master, 400, "commission_invalid")
    return redirect("/commissions")


def show_seller(request, master, seller_id, status=200, error=None):
    seller, accruals, payouts = commissions.detail(seller_id) if 0 < seller_id <= 2**63 - 1 else (None, [], [])
    if seller is None:
        raise HTTPException(404)
    return render(
        request, "commission_detail.html", status, section="commissions", csrf=master[1], is_master=True,
        seller=seller, accruals=accruals, payouts=payouts, request_key=str(uuid4()),
        quote=fx.state()["active"], error=error,
    )


@router.get("/commissions/{seller_id}")
def commission_seller(seller_id: int, request: Request, lang: str | None = None, master=Depends(master_session)):
    if lang is not None:
        return change_language(request, f"/commissions/{seller_id}", lang)
    return show_seller(request, master, seller_id)


@router.post("/commissions/{seller_id}/payout")
def payout_commission(seller_id: int, request: Request, master=Depends(master_session), form: dict = Depends(read_catalog_form)):
    check_csrf(form, master[1])
    if not 0 < seller_id <= 2**63 - 1:
        raise HTTPException(404)
    try:
        commissions.payout(
            master[0], seller_id, form.get("amount", ""), form.get("method", ""),
            form.get("currency", ""), form.get("request_key", ""),
        )
    except (commissions.CommissionConflict, finance.FinanceConflict):
        return show_seller(request, master, seller_id, 409, "commission_conflict")
    except ValueError:
        return show_seller(request, master, seller_id, 400, "commission_invalid")
    return redirect(f"/commissions/{seller_id}")
