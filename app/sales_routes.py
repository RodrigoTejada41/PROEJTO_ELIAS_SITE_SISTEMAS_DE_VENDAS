import json
from typing import Literal
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse

from app import company, finance, fx, inventory, sales
from app.web import NO_STORE, TEXT, parse_form, master_session, read_catalog_form, read_form, render, redirect, check_csrf, change_language

router = APIRouter()


@router.get("/sales")
def sales_list(request: Request, state: Literal["all", "draft", "confirmed", "canceled"] = "all",
               page: int = 1, lang: str | None = None, master=Depends(master_session)):
    if lang is not None:
        return change_language(request, "/sales", lang)
    page = max(1, min(page, 1000000))
    rows, has_next = sales.list_sales(state, page)
    return render(
        request, "sales.html", section="sales", csrf=master[1], is_master=True,
        rows=rows, state=state, page=page, has_next=has_next,
    )


def create_form(request, master, status=200, error=None, *, sale=None, form=None, cart=None):
    sellers, customers, _ = sales.options(include_skus=False)
    quote = fx.state()["active"]
    if form is None:
        form = {"request_key": str(uuid4()), "discount": "0"}
        if sale:
            form.update(customer_id=str(sale["customer_id"] or ""), seller_id=str(sale["seller_id"]),
                        discount=finance.format_amount(sale["discount_minor"], 2),
                        due_date=sale["due_date"].isoformat(), version=str(sale["version"]))
    return render(
        request, "sale_form.html", status, section="sales", csrf=master[1], is_master=True,
        sellers=sellers, customers=customers, sale=sale, form=form, cart=cart or [],
        rate=str(quote["pyg_per_usd"]) if quote else "", error=error,
    )


async def read_sale_form(request: Request):
    return await parse_form(request, 512 * 1024, 9)


def read_cart(raw):
    try:
        rows = json.loads(raw)
    except (ValueError, RecursionError) as exc:
        raise ValueError("items") from exc
    if not isinstance(rows, list) or len(rows) > 200:
        raise ValueError("items")
    cart, items, seen = [], [], set()
    for row in rows:
        if not isinstance(row, dict) or any(not isinstance(row.get(key), str) for key in ("id", "code", "description", "quantity", "price")):
            raise ValueError("items")
        if len(row["id"]) > 19 or len(row["quantity"]) > 10 or len(row["price"]) > 20:
            raise ValueError("items")
        sku_id, quantity = int(row["id"]), int(row["quantity"])
        if sku_id in seen or not 0 < sku_id <= 2**63 - 1 or not 0 < quantity <= 1000000000:
            raise ValueError("items")
        seen.add(sku_id)
        cart.append({**{key: row[key] for key in ("id", "quantity", "price")},
                     "code": row["code"][:64], "description": row["description"][:160]})
        items.append((sku_id, quantity, row["price"]))
    return cart, items


def sale_error(exc):
    if isinstance(exc, inventory.StockConflict):
        return "sale_stock" if str(exc) == "balance" else "sale_sku"
    return {
        "seller": "sale_seller", "customer": "sale_customer", "sku": "sale_sku",
        "price": "sale_price", "amount": "sale_amount", "commission_rule": "sale_commission",
        "fx": "sale_rate", "version": "sale_version", "request": "sale_version",
    }.get(str(exc), "sale_conflict")


@router.get("/sales/products")
def products_for_sale(q: str, master=Depends(master_session)):
    query = q.replace(chr(0), "").strip()[:160]
    return JSONResponse(sales.search_products(query) if query else [], headers=NO_STORE)


@router.get("/sales/new")
def new_sale(request: Request, lang: str | None = None, master=Depends(master_session)):
    if lang is not None:
        return change_language(request, "/sales/new", lang)
    return create_form(request, master)


@router.post("/sales/new")
def create_sale(request: Request, master=Depends(master_session), form: dict = Depends(read_sale_form)):
    return save_sale(request, master, form)


@router.post("/sales/{sale_id}/draft")
def update_sale(sale_id: int, request: Request, master=Depends(master_session), form: dict = Depends(read_sale_form)):
    return save_sale(request, master, form, sale_id)


def save_sale(request, master, form, sale_id=None):
    check_csrf(form, master[1])
    sale = None
    if sale_id is not None:
        sale, _ = sales.detail(sale_id) if 0 < sale_id <= 2**63 - 1 else (None, [])
        if sale is None:
            raise HTTPException(404)
        if sale["status"] != "draft":
            return redirect(f"/sales/{sale_id}")
    cart = []
    try:
        cart, items = read_cart(form.get("cart", "[]"))
        customer_id = int(form["customer_id"]) if form.get("customer_id") else None
        seller_id = int(form.get("seller_id", ""))
        due, discount = form.get("due_date", ""), form.get("discount", "")
        if sale is None:
            sale_id = sales.create(master[0], customer_id, seller_id, due, discount,
                                   form.get("request_key", ""), items=items)
            version = 1
        else:
            version = sales.save_draft(master[0], sale_id, int(form.get("version", "")),
                                       customer_id, seller_id, due, discount, items)
    except (sales.SaleConflict, finance.FinanceConflict) as exc:
        return create_form(request, master, 409, sale_error(exc), sale=sale, form=form, cart=cart)
    except ValueError:
        return create_form(request, master, 400, "sale_input", sale=sale, form=form, cart=cart)
    if form.get("action") == "confirm":
        try:
            sales.confirm(master[0], sale_id, version)
        except (sales.SaleConflict, finance.FinanceConflict, inventory.StockConflict) as exc:
            return show_sale(request, master, sale_id, 409, sale_error(exc))
    return redirect(f"/sales/{sale_id}")


def show_sale(request, master, sale_id, status=200, error=None):
    sale, items = sales.detail(sale_id) if 0 < sale_id <= 2**63 - 1 else (None, [])
    if sale is None:
        raise HTTPException(404)
    if sale["status"] == "draft":
        cart = [{"id": str(item["sku_id"]), "code": item["code_snapshot"], "description": item["description_snapshot"],
                 "quantity": str(item["quantity"]), "price": finance.format_amount(item["unit_minor"], 2)}
                for item in items]
        return create_form(request, master, status, error, sale=sale, cart=cart)
    return render(
        request, "sale_detail.html", status, section="sales", csrf=master[1], is_master=True,
        sale=sale, items=items, quote=({"pyg_per_usd": sale["applied_rate"], "published_at": sale["rate_published_at"], "source": sale["rate_source"]}
               if sale["applied_rate"] is not None else fx.state()["active"]), error=error,
    )


@router.get("/sales/{sale_id}")
def sale_detail(sale_id: int, request: Request, lang: str | None = None, master=Depends(master_session)):
    if lang is not None:
        return change_language(request, f"/sales/{sale_id}", lang)
    return show_sale(request, master, sale_id)


@router.post("/sales/{sale_id}/items")
def sale_item(sale_id: int, request: Request, master=Depends(master_session), form: dict = Depends(read_catalog_form)):
    check_csrf(form, master[1])
    if not 0 < sale_id <= 2**63 - 1:
        raise HTTPException(404)
    try:
        version = int(form.get("version", ""))
        sales.set_item(master[0], sale_id, int(form.get("sku_id", "")), version,
                       int(form.get("quantity", "")), form.get("price", ""))
    except sales.SaleConflict:
        return show_sale(request, master, sale_id, 409, "sale_conflict")
    except ValueError:
        return show_sale(request, master, sale_id, 400, "finance_invalid")
    return redirect(f"/sales/{sale_id}")


@router.post("/sales/{sale_id}/remove/{sku_id}")
def remove_sale_item(sale_id: int, sku_id: int, request: Request, master=Depends(master_session), form: dict = Depends(read_form)):
    check_csrf(form, master[1])
    if not 0 < sale_id <= 2**63 - 1 or not 0 < sku_id <= 2**63 - 1:
        raise HTTPException(404)
    try:
        sales.remove_item(master[0], sale_id, sku_id, int(form.get("version", "")))
    except sales.SaleConflict:
        return show_sale(request, master, sale_id, 409, "sale_conflict")
    except ValueError:
        return show_sale(request, master, sale_id, 400, "finance_invalid")
    return redirect(f"/sales/{sale_id}")


@router.post("/sales/{sale_id}/confirm")
def confirm_sale(sale_id: int, request: Request, master=Depends(master_session), form: dict = Depends(read_form)):
    check_csrf(form, master[1])
    if not 0 < sale_id <= 2**63 - 1:
        raise HTTPException(404)
    try:
        sales.confirm(master[0], sale_id, int(form.get("version", "")))
    except (sales.SaleConflict, finance.FinanceConflict, inventory.StockConflict) as exc:
        return show_sale(request, master, sale_id, 409, sale_error(exc))
    except ValueError:
        return show_sale(request, master, sale_id, 400, "finance_invalid")
    return redirect(f"/sales/{sale_id}")


@router.post("/sales/{sale_id}/cancel")
def cancel_sale(sale_id: int, request: Request, master=Depends(master_session), form: dict = Depends(read_form)):
    check_csrf(form, master[1])
    if not 0 < sale_id <= 2**63 - 1:
        raise HTTPException(404)
    try:
        sales.cancel(master[0], sale_id)
    except (sales.SaleConflict, finance.FinanceConflict, inventory.StockConflict):
        return show_sale(request, master, sale_id, 409, "sale_conflict")
    return redirect(f"/sales/{sale_id}")


@router.post("/sales/{sale_id}/receipt")
def issue_receipt(sale_id: int, request: Request, master=Depends(master_session), form=Depends(read_form)):
    check_csrf(form, master[1])
    if not 0 < sale_id <= 2**63 - 1:
        raise HTTPException(404)
    error = company.issue(master[0], sale_id)
    if error == "not_found":
        raise HTTPException(404)
    if error:
        return show_sale(request, master, sale_id, 409, error)
    return redirect(f"/sales/{sale_id}/receipt?print=1")


@router.get("/sales/{sale_id}/receipt")
def sale_receipt(sale_id: int, request: Request, master=Depends(master_session)):
    if not 0 < sale_id <= 2**63 - 1:
        raise HTTPException(404)
    issuer = company.issuer(sale_id)
    if issuer is None:
        raise HTTPException(404)
    sale, items = sales.detail(sale_id)
    if sale is None or sale["status"] != "confirmed":
        raise HTTPException(404)
    return render(request, "sale_receipt.html", sale=sale, items=items, issuer=issuer)

TEXT["pt"].update({
    "sale_customer_label": "Cliente", "sale_no_customer": "Sem cliente identificado", "sale_choose_seller": "Selecione o vendedor",
    "sale_products": "Produtos", "sale_search": "Buscar por nome, código ou código de barras",
    "sale_loading": "Buscando produtos…", "sale_search_error": "A busca falhou. Tente novamente.",
    "sale_empty": "Adicione produtos para montar a venda.", "sale_added": "Adicionado", "sale_limit": "Limite de 200 produtos por venda nesta tela.",
    "sale_estimate": "Equivalente estimado", "sale_save_draft": "Salvar rascunho",
    "sale_js": "Ative o JavaScript do navegador para montar a venda.",
    "sale_input": "Confira vendedor, vencimento, desconto, quantidades e preços.",
    "sale_seller": "Selecione um vendedor ativo.", "sale_customer": "Selecione um cliente ativo ou deixe em branco.",
    "sale_sku": "Um produto está indisponível. Atualize a lista de itens.",
    "sale_price": "Informe o preço unitário em USD.", "sale_amount": "Confira os itens, o desconto e o limite do total.",
    "sale_stock": "Estoque insuficiente. Confira o saldo dos produtos e ajuste as quantidades.",
    "sale_commission": "Configure a comissão do vendedor antes de confirmar.",
    "sale_rate": "Configure a cotação comercial antes de confirmar.",
    "sale_version": "A venda mudou em outra aba ou já foi processada. Confira a versão atual.",
    "sale_reload": "Abrir a versão atual da venda", "receipt_line_total": "Valor do item",
    "receipt_print_hint": "Escolha sua impressora ou Salvar como PDF no diálogo de impressão.",
})
TEXT["es"].update({
    "sale_customer_label": "Cliente", "sale_no_customer": "Sin cliente identificado", "sale_choose_seller": "Selecciona al vendedor",
    "sale_products": "Productos", "sale_search": "Buscar por nombre, código o código de barras",
    "sale_loading": "Buscando productos…", "sale_search_error": "Falló la búsqueda. Inténtalo de nuevo.",
    "sale_empty": "Añade productos para preparar la venta.", "sale_added": "Añadido", "sale_limit": "Límite de 200 productos por venta en esta pantalla.",
    "sale_estimate": "Equivalente estimado", "sale_save_draft": "Guardar borrador",
    "sale_js": "Activa JavaScript en el navegador para preparar la venta.",
    "sale_input": "Revisa vendedor, vencimiento, descuento, cantidades y precios.",
    "sale_seller": "Selecciona un vendedor activo.", "sale_customer": "Selecciona un cliente activo o deja el campo vacío.",
    "sale_sku": "Un producto no está disponible. Actualiza la lista.",
    "sale_price": "Introduce el precio unitario en USD.", "sale_amount": "Revisa los artículos, el descuento y el límite del total.",
    "sale_stock": "Inventario insuficiente. Revisa las existencias y ajusta las cantidades.",
    "sale_commission": "Configura la comisión del vendedor antes de confirmar.",
    "sale_rate": "Configura la cotización comercial antes de confirmar.",
    "sale_version": "La venta cambió en otra pestaña o ya se procesó. Revisa la versión actual.",
    "sale_reload": "Abrir la versión actual de la venta", "receipt_line_total": "Importe del artículo",
    "receipt_print_hint": "Elige tu impresora o Guardar como PDF en el diálogo de impresión.",
})
