from typing import Literal

from fastapi import APIRouter, Depends, Request
from fastapi.responses import Response

from app import reports
from app.web import is_admin_role
from app.web import active_session, master_session, change_language, render, request_locale, TEXT

router = APIRouter()


@router.get("/reports")
def stock_report(request: Request, q: str = "", status: Literal["all", "active", "inactive"] = "active",
                 page: int = 1, lang: str | None = None, export: bool = False,
                 balance: Literal["all", "positive", "zero", "negative"] = "all", account=Depends(active_session)):
    if lang is not None:
        return change_language(request, "/reports", lang)
    selected_status = status if is_admin_role(account[1]) else "active"
    query = q.strip().replace(chr(0), "")[:160]
    page = max(1, min(page, 1000000))
    locale = request_locale(request)
    text = TEXT[locale]
    error = None
    response_status = 200
    try:
        rows, totals, has_next = reports.stock(query, selected_status, page, export, balance=balance)
    except ValueError:
        rows, totals, has_next = reports.stock(query, selected_status, page, balance=balance)
        error, response_status = "export_limit", 422
    if export and not error:
        body = reports.csv_text(
            [(r["code"], r["description"], text["active"] if r["active"] else text["inactive"], r["balance"]) for r in rows],
            [text["code"], text["description"], text["status"], text["balance"]],
        )
        return Response(
            body, media_type="text/csv; charset=utf-8",
            headers={"Content-Disposition": 'attachment; filename="stock.csv"', "Cache-Control": "private, no-store"},
        )
    return render(
        request, "reports.html", response_status, section="reports", is_master=is_admin_role(account[1]),
        csrf=account[2], rows=rows, totals=totals, query=query, selected_status=selected_status,
        page=page, has_next=has_next, error=error, balance=balance,
    )


@router.get("/audit")
def audit_page(request: Request, source: Literal["all", "identity", "catalog", "inventory", "inventory_policy", "contacts", "finance", "fx", "sales", "commissions", "company"] = "all",
               start: str = "", end: str = "", page: int = 1, lang: str | None = None, master=Depends(master_session)):
    if lang is not None:
        return change_language(request, "/audit", lang)
    error, response_status = None, 200
    try:
        lower, upper = reports.audit_period(start, end)
    except (ValueError, OverflowError):
        lower, upper = None, None
        error, response_status = "invalid_period", 400
    page = max(1, min(page, 1000000))
    rows, has_next = reports.audit(source, lower, upper, page)
    return render(
        request, "audit.html", response_status, section="audit", is_master=True, csrf=master[1],
        rows=rows, source=source, start=start[:10], end=end[:10], page=page, has_next=has_next, error=error,
    )

@router.get("/reports/cash")
def cash_report(request: Request, start: str = "", end: str = "", currency: Literal["all", "USD", "PYG"] = "all",
                page: int = 1, export: bool = False, lang: str | None = None,
                nature: Literal["all", "receivable", "payable", "reversed"] = "all", master=Depends(master_session)):
    from decimal import Decimal

    if lang is not None:
        return change_language(request, "/reports/cash", lang)
    error, status = None, 200
    try:
        lower, upper = reports.audit_period(start, end)
    except (ValueError, OverflowError):
        lower, upper, error, status = None, None, "invalid_period", 400
    page = max(1, min(page, 1000000))
    try:
        rows, totals, has_next = reports.cash(lower, upper, currency, page, export and not error, nature=nature)
    except ValueError:
        rows, totals, has_next = reports.cash(lower, upper, currency, page, nature=nature)
        error, status = "export_limit", 422
    text = TEXT[request_locale(request)]
    if export and not error:
        body = reports.csv_text(
            [(r["occurred_at"].isoformat(), r["title_id"], r["currency"],
              Decimal(r["amount_minor"]).scaleb(-2 if r["currency"] == "USD" else 0), text[r["method"]], text[r["action"]]) for r in rows],
            [text["when"], text["title"], text["currency"], text["amount"], text["method"], text["action"]],
        )
        return Response(body, media_type="text/csv; charset=utf-8",
                        headers={"Content-Disposition": 'attachment; filename="cash.csv"', "Cache-Control": "private, no-store"})
    return render(
        request, "cash_report.html", status, section="reports", is_master=True, csrf=master[1], error=error,
        rows=rows, totals=totals, currency=currency, nature=nature, start=start[:10], end=end[:10], page=page, has_next=has_next,
    )


@router.get("/reports/sales")
def sales_report(request: Request, start: str = "", end: str = "", seller_id: str = "",
                 page: int = 1, export: bool = False, lang: str | None = None, master=Depends(master_session)):
    from decimal import Decimal

    if lang is not None:
        return change_language(request, "/reports/sales", lang)
    error, status = None, 200
    try:
        lower, upper, seller_id = reports.sales_filters(start, end, seller_id)
    except (ValueError, OverflowError):
        lower, upper, seller_id, error, status = None, None, None, "invalid_period", 400
    page = max(1, min(page, 1000000))
    try:
        rows, total, has_next = reports.sale_report(lower, upper, seller_id, page, export and not error)
    except ValueError:
        rows, total, has_next = reports.sale_report(lower, upper, seller_id, page)
        error, status = "export_limit", 422
    text = TEXT[request_locale(request)]
    if export and not error:
        body = reports.csv_text(
            [(r["id"], r["confirmed_at"].isoformat(), r["seller_name"], r["customer_name"] or "",
              "USD", Decimal(r["net_minor"]).scaleb(-2)) for r in rows],
            [text["sale"], text["when"], text["seller"], text["customer"], text["currency"], text["total"]],
        )
        return Response(body, media_type="text/csv; charset=utf-8",
                        headers={"Content-Disposition": 'attachment; filename="sales.csv"', "Cache-Control": "private, no-store"})
    sellers = reports.report_sellers()
    return render(
        request, "sales_report.html", status, section="reports", is_master=True, csrf=master[1], error=error,
        rows=rows, total=total, start=start[:10], end=end[:10], seller_id=seller_id,
        sellers=sellers, page=page, has_next=has_next, top_products=reports.top_products(lower, upper, seller_id),
    )


@router.get("/reports/top-products")
def top_report(request: Request, start: str = "", end: str = "", seller_id: str = "", q: str = "",
               page: int = 1, export: bool = False, master=Depends(master_session)):
    error, status, rows, has_next = None, 200, [], False
    query = q.strip().replace(chr(0), "")[:160]
    page = max(1, min(page, 1000000))
    try:
        lower, upper, seller = reports.sales_filters(start, end, seller_id)
    except (ValueError, OverflowError):
        seller, error, status = None, "invalid_period", 400
    else:
        try:
            rows, has_next = reports.product_ranking(lower, upper, seller, query, page, export)
        except ValueError:
            rows, has_next = reports.product_ranking(lower, upper, seller, query, page, False)
            error, status = "export_limit", 422
    if export and not error:
        text = TEXT[request_locale(request)]
        body = reports.csv_text(
            [(r["code_snapshot"], r["description"], r["quantity"]) for r in rows],
            [text["code"], text["description"], text["quantity"]],
        )
        return Response(body, media_type="text/csv; charset=utf-8",
                        headers={"Content-Disposition": 'attachment; filename="top-products.csv"', "Cache-Control": "private, no-store"})
    return render(request, "top_report.html", status, section="reports", is_master=True, csrf=master[1],
                  rows=rows, error=error, page=page, has_next=has_next, query=query,
                  start=start[:10], end=end[:10], seller_id=seller, sellers=reports.report_sellers())


TEXT["pt"].update({
    "sales_dashboard": "Painel de vendas", "confirmed_sales": "Vendas confirmadas", "average_sale": "Ticket médio",
    "sales_trend": "Vendas por dia", "report_balance": "Faixa de saldo", "report_nature": "Tipo de movimento",
    "balance_positive": "Positivo", "balance_zero": "Zerado", "balance_negative": "Negativo",
    "report_equivalent": "Equivalente em guaranis", "report_missing_rate": "A soma em guaranis considera as vendas com cotação registrada.",
    "report_receivable": "Recebimentos", "report_payable": "Pagamentos", "report_reversed": "Estornos",
    "report_stock": "Estoque", "report_no_products": "Nenhum produto vendido com estes filtros.",
})
TEXT["es"].update({
    "sales_dashboard": "Panel de ventas", "confirmed_sales": "Ventas confirmadas", "average_sale": "Ticket promedio",
    "sales_trend": "Ventas por día", "report_balance": "Rango de saldo", "report_nature": "Tipo de movimiento",
    "balance_positive": "Positivo", "balance_zero": "Cero", "balance_negative": "Negativo",
    "report_equivalent": "Equivalente en guaraníes", "report_missing_rate": "La suma en guaraníes incluye las ventas con cotización registrada.",
    "report_receivable": "Cobros", "report_payable": "Pagos", "report_reversed": "Reversiones",
    "report_stock": "Inventario", "report_no_products": "Ningún producto vendido con estos filtros.",
})
