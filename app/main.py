import logging
import re
from datetime import datetime, timedelta, timezone
from uuid import uuid4
from secrets import token_urlsafe

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from fastapi.staticfiles import StaticFiles
import psycopg
from psycopg.errors import UniqueViolation

from app import catalog, identity, inventory, reports, fx
from app.admin_routes import router as admin_router
from app.inventory_routes import router as inventory_router
from app.catalog_uploads import router as catalog_upload_router
from app.web import is_admin_role
from app.web import (
    APP, LOGIN_CSRF_COOKIE, NO_STORE, SESSION_COOKIE, TEXT,
    active_session, master_session, redirect, set_cookie, change_language, render,
    parse_form, read_form, read_catalog_form, check_csrf, session_csrf,
)

app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)
app.include_router(catalog_upload_router)
app.include_router(inventory_router)
app.include_router(admin_router)
app.mount("/static", StaticFiles(directory=APP / "static"), name="static")
MFA_COOKIE = "login_mfa"

@app.exception_handler(psycopg.OperationalError)
async def database_unavailable(request, error):
    logging.getLogger(__name__).error("Banco indisponível (%s)", error.sqlstate or type(error).__name__)
    return render(request, "error.html", 503, error_key="database_unavailable")


@app.exception_handler(StarletteHTTPException)
async def http_error(request, error):
    headers = error.headers or {}
    if error.status_code in (301, 302, 303, 307, 308) and "Location" in headers:
        return RedirectResponse(headers["Location"], status_code=error.status_code, headers=headers)
    key = {403: "access_denied", 404: "not_found"}.get(error.status_code, "request_invalid")
    response = render(request, "error.html", error.status_code, error_key=key)
    response.headers.update(headers)
    return response


@app.exception_handler(RequestValidationError)
async def validation_error(request, error):
    return render(request, "error.html", 422, error_key="request_invalid")

@app.get("/login", response_class=HTMLResponse)
def login_page(request: Request, lang: str | None = None):
    if lang is not None:
        return change_language(request, "/login", lang)
    return render_login(request)


def render_login(request, status=200, error=None):
    csrf = request.cookies.get(LOGIN_CSRF_COOKIE) or token_urlsafe(32)
    response = render(request, "login.html", status, csrf=csrf, error=error)
    set_cookie(response, request, LOGIN_CSRF_COOKIE, csrf, 600)
    return response


@app.post("/login")
def submit_login(request: Request, form: dict = Depends(read_form)):
    check_csrf(form, request.cookies.get(LOGIN_CSRF_COOKIE))
    username = form.get("username", "").strip().lower()
    password = form.get("password", "")
    # Invalid identifiers still use the same failure path and consume an attempt.
    if len(username) > 64 or "\x00" in username:
        username = ""
    if len(password) > 128:
        password = ""
    address = request.client.host if request.client else "127.0.0.1"
    token, status = identity.login(username, password, address, request.cookies.get(SESSION_COOKIE))
    if token is None:
        errors = {429: "limited", 403: "mfa_enrollment"}
        return render_login(request, status, errors.get(status, "invalid"))
    if status == 202:
        response = redirect("/login/verify")
        set_cookie(response, request, MFA_COOKIE, token, 300)
        return response
    return finish_login(request, token)


@app.get("/login/verify", response_class=HTMLResponse)
def second_factor_page(request: Request, lang: str | None = None):
    if not request.cookies.get(MFA_COOKIE) or not request.cookies.get(LOGIN_CSRF_COOKIE):
        return redirect("/login")
    if lang is not None:
        return change_language(request, "/login/verify", lang)
    return render_second_factor(request)


def render_second_factor(request, status=200, error=None):
    stage, setup = identity.second_factor_state(request.cookies[MFA_COOKIE])
    if stage == "expired":
        status, error = 410, "mfa_expired"
    elif stage == "unavailable":
        status, error = 503, "mfa_unavailable"
    return render(request, "login.html", status, csrf=request.cookies.get(LOGIN_CSRF_COOKIE),
                  error=error, second_factor=True, mfa_stage=stage, mfa_setup=setup)


@app.post("/login/verify")
def submit_second_factor(request: Request, form: dict = Depends(read_form)):
    check_csrf(form, request.cookies.get(LOGIN_CSRF_COOKIE))
    challenge = request.cookies.get(MFA_COOKIE)
    if not challenge:
        return redirect("/login")
    token, status = identity.verify_second_factor(
        challenge, form.get("code", ""), request.cookies.get(SESSION_COOKIE), form.get("activation", ""),
    )
    if status == 202:
        return redirect("/login/verify")
    if token is None:
        errors = {429: "limited", 410: "mfa_expired", 503: "mfa_unavailable"}
        invalid = "mfa_activation_invalid" if "activation" in form else "mfa_invalid"
        return render_second_factor(request, status, errors.get(status, invalid))
    return finish_login(request, token)


def finish_login(request, token):
    response = redirect("/")
    response.delete_cookie(LOGIN_CSRF_COOKIE)
    response.delete_cookie(MFA_COOKIE)
    set_cookie(response, request, SESSION_COOKIE, token, identity.SESSION_SECONDS)
    locale = request.cookies.get("locale")
    if locale not in TEXT:
        locale = identity.preferred_locale(token)
    identity.set_locale(token, locale)
    set_cookie(response, request, "locale", locale, 365 * 24 * 60 * 60)
    return response


@app.post("/preferences/locale")
def store_locale(request: Request, account=Depends(active_session), form: dict = Depends(read_form)):
    check_csrf(form, account[2])
    locale = form.get("locale", "pt")
    if locale not in TEXT:
        locale = "pt"
    token = request.cookies[SESSION_COOKIE]
    identity.set_locale(token, locale)
    target = form.get("next", "/")
    if not re.fullmatch(r"/[A-Za-z0-9/_-]*", target) or target.startswith("//"):
        target = "/"
    return change_language(request, target, locale)


@app.post("/logout")
def logout(request: Request, form: dict = Depends(read_form)):
    token = request.cookies.get(SESSION_COOKIE)
    if not token:
        return redirect("/login")
    check_csrf(form, session_csrf(token))
    identity.logout(token)
    response = redirect("/login")
    response.delete_cookie(SESSION_COOKIE)
    return response


@app.get("/", response_class=HTMLResponse)
def dashboard(request: Request, lang: str | None = None, start: str = "", end: str = "", seller_id: str = ""):
    token = request.cookies.get(SESSION_COOKIE)
    account = identity.session_account(token) if token else None
    if account is None:
        return redirect("/login")
    if lang is not None:
        return change_language(request, "/", lang)
    request.state.role = account[1]
    is_master = is_admin_role(account[1])
    context = {}
    status = 200
    if is_master:
        today = datetime.now(timezone.utc).date()
        start = start or (today - timedelta(days=29)).isoformat()
        end = end or today.isoformat()
        context = {"start": start[:10], "end": end[:10], "seller_id": None, "sellers": reports.report_sellers()}
        try:
            lower, upper, seller = reports.sales_filters(start, end, seller_id)
        except (ValueError, OverflowError):
            context["error"] = "invalid_period"
            status = 400
        else:
            total, trend, products = reports.dashboard_sales(lower, upper, seller)
            context.update(seller_id=seller, sales_summary=total, trend=trend, ranked=products,
                           trend_max=max((row["count"] for row in trend), default=1))
    return render(request, "dashboard.html", status, csrf=session_csrf(token), is_master=is_master,
                  cards=reports.dashboard_stats(is_master), **context)

def render_operators(request, csrf, status=200, error=None):
    return render(
        request, "operators.html", status, csrf=csrf, is_master=True,
        operators=identity.list_operators(), error=error, managing_operators=True,
    )


@app.get("/operators", response_class=HTMLResponse)
def operators_page(request: Request, lang: str | None = None, master=Depends(master_session)):
    if lang is not None:
        return change_language(request, "/operators", lang)
    return render_operators(request, master[1])


@app.post("/operators")
def submit_operator(request: Request, master=Depends(master_session), form: dict = Depends(read_form)):
    actor_id, csrf = master
    check_csrf(form, csrf)
    try:
        created = identity.create_operator(actor_id, form.get("username", "").strip().lower(), form.get("password", ""))
    except ValueError:
        return render_operators(request, csrf, 400, "operator_invalid")
    if not created:
        return render_operators(request, csrf, 409, "operator_duplicate")
    return redirect("/operators")


@app.post("/operators/{user_id}/deactivate")
def deactivate_operator(user_id: int, master=Depends(master_session), form: dict = Depends(read_form)):
    actor_id, csrf = master
    check_csrf(form, csrf)
    if not 0 < user_id <= 2**63 - 1:
        raise HTTPException(404)
    identity.deactivate_operator(actor_id, user_id)
    return redirect("/operators")

@app.get("/catalog", response_class=HTMLResponse)
def catalog_page(request: Request, q: str = "", lang: str | None = None, account=Depends(active_session)):
    if lang is not None:
        return change_language(request, "/catalog", lang)
    is_master = is_admin_role(account[1])
    query = q.strip().replace(chr(0), "")[:160]
    return render(
        request, "catalog.html", csrf=account[2], is_master=is_master, in_catalog=True,
        skus=catalog.list_skus(is_master, query), query=query, quote=fx.state()["active"],
    )


def sku_form(request, csrf, sku=None, status=200, error=None):
    return render(
        request, "sku_form.html", status, csrf=csrf, is_master=True,
        in_catalog=True, sku=sku or {}, error=error,
    )


@app.get("/catalog/new", response_class=HTMLResponse)
def new_sku(request: Request, lang: str | None = None, master=Depends(master_session)):
    if lang is not None:
        return change_language(request, "/catalog/new", lang)
    return sku_form(request, master[1])


@app.post("/catalog/new")
def submit_sku(request: Request, master=Depends(master_session), form: dict = Depends(read_catalog_form)):
    actor_id, csrf = master
    check_csrf(form, csrf)
    draft = {key: form.get(key, "") for key in ("code", "description", "brand", "category", "variation", "barcode")}
    try:
        catalog.create_sku(actor_id, catalog.sku_code(form.get("code", "")), catalog.sku_details(form))
    except ValueError:
        return sku_form(request, csrf, draft, 400, "sku_invalid")
    except UniqueViolation:
        return sku_form(request, csrf, draft, 409, "sku_duplicate")
    return redirect("/catalog")


def require_sku(sku_id):
    sku = catalog.get_sku(sku_id) if 0 < sku_id <= 2**63 - 1 else None
    if sku is None:
        raise HTTPException(404)
    return sku


@app.get("/catalog/{sku_id}/edit", response_class=HTMLResponse)
def edit_sku(sku_id: int, request: Request, lang: str | None = None, master=Depends(master_session)):
    sku = require_sku(sku_id)
    if lang is not None:
        return change_language(request, f"/catalog/{sku_id}/edit", lang)
    return sku_form(request, master[1], sku)


@app.post("/catalog/{sku_id}/edit")
def submit_sku_edit(sku_id: int, request: Request, master=Depends(master_session), form: dict = Depends(read_catalog_form)):
    actor_id, csrf = master
    check_csrf(form, csrf)
    sku = require_sku(sku_id)
    fields = ("description", "brand", "category", "variation", "barcode", "version")
    draft = {**sku, **{key: form.get(key, "") for key in fields}}
    try:
        version = int(draft["version"])
        if not 0 < version <= 2**63 - 1:
            raise ValueError("version")
        updated = catalog.update_sku(actor_id, sku_id, version, catalog.sku_details(form))
    except ValueError:
        return sku_form(request, csrf, draft, 400, "sku_invalid")
    except UniqueViolation:
        return sku_form(request, csrf, draft, 409, "sku_duplicate")
    if not updated:
        return sku_form(request, csrf, draft, 409, "sku_stale")
    return redirect("/catalog")


@app.post("/catalog/{sku_id}/deactivate")
def deactivate_sku(sku_id: int, master=Depends(master_session), form: dict = Depends(read_form)):
    actor_id, csrf = master
    check_csrf(form, csrf)
    if not 0 < sku_id <= 2**63 - 1:
        raise HTTPException(404)
    catalog.deactivate_sku(actor_id, sku_id)
    return redirect("/catalog")

async def read_stock_form(request: Request):
    return await parse_form(request, 8192, 5)


@app.get("/stock", response_class=HTMLResponse)
def stock_page(request: Request, lang: str | None = None, account=Depends(active_session)):
    if lang is not None:
        return change_language(request, "/stock", lang)
    return render(
        request, "stock.html", csrf=account[2], is_master=is_admin_role(account[1]),
        in_stock=True, balances=inventory.list_balances(is_admin_role(account[1])),
        allow_negative=inventory.negative_allowed(),
    )


def render_stock_detail(request, account, sku, page=1, status=200, error=None):
    balance, movements, has_next = inventory.history(sku["id"], page)
    return render(
        request, "stock_detail.html", status, csrf=account[2], is_master=is_admin_role(account[1]),
        in_stock=True, sku=sku, balance=balance, movements=movements,
        page=page, has_next=has_next, request_key=str(uuid4()), error=error,
    )


@app.get("/stock/{sku_id}", response_class=HTMLResponse)
def stock_detail(sku_id: int, request: Request, page: int = 1, lang: str | None = None, account=Depends(active_session)):
    sku = require_sku(sku_id)
    if not sku["active"] and not is_admin_role(account[1]):
        raise HTTPException(404)
    if not 1 <= page <= 1000000:
        raise HTTPException(400)
    if lang is not None:
        return change_language(request, f"/stock/{sku_id}", lang)
    return render_stock_detail(request, account, sku, page)


@app.post("/stock/{sku_id}")
def submit_stock(sku_id: int, request: Request, master=Depends(master_session), form: dict = Depends(read_stock_form)):
    check_csrf(form, master[1])
    sku = require_sku(sku_id)
    try:
        raw_quantity = form.get("quantity", "")
        if not raw_quantity.isascii() or not raw_quantity.isdecimal() or len(raw_quantity) > 10:
            raise ValueError("quantity")
        quantity = int(raw_quantity)
        kind = form.get("kind")
        if kind not in ("entry", "exit"):
            raise ValueError("kind")
        inventory.record(
            master[0], sku_id, quantity if kind == "entry" else -quantity,
            form.get("reason", ""), form.get("request_key", ""),
        )
    except inventory.StockConflict:
        return render_stock_detail(request, (master[0], "MASTER", master[1]), sku, status=409, error="stock_conflict")
    except ValueError:
        return render_stock_detail(request, (master[0], "MASTER", master[1]), sku, status=400, error="stock_invalid")
    return redirect(f"/stock/{sku_id}")


@app.post("/stock/{sku_id}/compensate/{movement_id}")
def compensate_stock(sku_id: int, movement_id: int, request: Request, master=Depends(master_session), form: dict = Depends(read_form)):
    check_csrf(form, master[1])
    sku = require_sku(sku_id)
    if not 0 < movement_id <= 2**63 - 1:
        raise HTTPException(404)
    try:
        inventory.record(
            master[0], sku_id, None, form.get("reason", ""),
            form.get("request_key", ""), compensates_id=movement_id,
        )
    except inventory.StockConflict:
        return render_stock_detail(request, (master[0], "MASTER", master[1]), sku, status=409, error="stock_conflict")
    except ValueError:
        return render_stock_detail(request, (master[0], "MASTER", master[1]), sku, status=400, error="stock_invalid")
    return redirect(f"/stock/{sku_id}")

from app.contacts_routes import router as contacts_router

app.include_router(contacts_router)

from app.reports_routes import router as reports_router

app.include_router(reports_router)

from app.finance_routes import router as finance_router

app.include_router(finance_router)

from app.pricing_routes import router as pricing_router

app.include_router(pricing_router)

from app.sales_routes import router as sales_router

app.include_router(sales_router)

from app.commissions_routes import router as commissions_router

app.include_router(commissions_router)
