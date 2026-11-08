from base64 import b64decode, urlsafe_b64encode
from binascii import Error as Base64Error
from hmac import compare_digest

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import Response
from starlette.concurrency import run_in_threadpool

from app import inventory, inventory_workbook
from app.catalog_uploads import upload, workbook_signature
from app.catalog_workbook import FILE_LIMIT, ImportErrorAtLine
from app.web import NO_STORE, TEXT, check_csrf, master_session, parse_form, read_form, redirect, render, request_locale

router = APIRouter()


@router.get("/stock/settings")
def settings(request: Request, master=Depends(master_session)):
    return render(request, "stock_settings.html", csrf=master[1], is_master=True,
                  in_stock=True, allow_negative=inventory.negative_allowed())


@router.post("/stock/settings")
def save_settings(request: Request, master=Depends(master_session), form=Depends(read_form)):
    check_csrf(form, master[1])
    value = form.get("allow_negative", "0")
    if value not in ("0", "1"):
        raise HTTPException(400)
    inventory.set_negative_policy(master[0], value == "1")
    return redirect("/stock/settings")


def entries_page(request, csrf, status=200, **context):
    return render(request, "stock_import.html", status, csrf=csrf, is_master=True, in_stock=True, **context)


@router.get("/stock/import")
def import_page(request: Request, master=Depends(master_session)):
    return entries_page(request, master[1])


@router.get("/stock/import/export")
def export_entries(request: Request, page: int = 1, master=Depends(master_session)):
    if not 1 <= page <= 1_000_000:
        raise HTTPException(400)
    locale = request_locale(request)
    data = inventory_workbook.export(page, locale, TEXT[locale])
    if data is None:
        raise HTTPException(404)
    return Response(data, media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    headers={"Content-Disposition": f'attachment; filename="estoque-entradas-{page}.xlsx"', **NO_STORE})


def sign_preview(request, reason, data):
    return workbook_signature(request, b"stock-entries\0" + reason.encode() + b"\0" + data)


def show_error(request, csrf, exc, reason):
    conflicts = ("stock_batch_sku", "stock_batch_balance", "stock_batch_used", "sku_duplicate")
    return entries_page(request, csrf, 409 if exc.key in conflicts else 400,
                        error=exc.key, line=exc.line, reason=reason)


@router.post("/stock/import")
async def preview_entries(request: Request, master=Depends(master_session)):
    actor_id, csrf = master
    data, reason = await upload(request, csrf, FILE_LIMIT, extra_field="reason")
    reason = (reason if isinstance(reason, str) else "").strip()
    try:
        rows, saved = await run_in_threadpool(inventory_workbook.process, data, actor_id, reason)
    except ImportErrorAtLine as exc:
        return show_error(request, csrf, exc, reason)
    if saved:
        return entries_page(request, csrf, rows=rows, saved=True, reason=reason)
    return entries_page(request, csrf, rows=rows, reason=reason,
                        payload=urlsafe_b64encode(data).decode(), signature=sign_preview(request, reason, data))


@router.post("/stock/import/confirm")
async def confirm_entries(request: Request, master=Depends(master_session)):
    actor_id, csrf = master
    form = await parse_form(request, 4 * ((FILE_LIMIT + 2) // 3) + 4096, 4)
    check_csrf(form, csrf)
    reason = form.get("reason", "").strip()
    try:
        data = b64decode(form.get("payload", ""), altchars=b"-_", validate=True)
    except (Base64Error, ValueError):
        raise HTTPException(400)
    if not compare_digest(form.get("signature", "").encode(), sign_preview(request, reason, data).encode()):
        raise HTTPException(403)
    try:
        rows, _ = await run_in_threadpool(inventory_workbook.process, data, actor_id, reason, confirm=True)
    except ImportErrorAtLine as exc:
        return show_error(request, csrf, exc, reason)
    return entries_page(request, csrf, rows=rows, saved=True, reason=reason)


TEXT["pt"].update({
    "stock_settings": "Configurações de estoque", "stock_allow_negative": "Permitir estoque negativo para todos os produtos",
    "stock_negative_enabled": "Estoque negativo permitido", "stock_negative_disabled": "Estoque negativo bloqueado para novas saídas",
    "inventory_policy": "Política de estoque",
    "stock_negative_help": "Ao desmarcar, saldos negativos existentes continuam visíveis e podem ser recuperados com entradas.",
    "stock_batch": "Importar entradas", "stock_batch_download": "Baixar produtos e saldos",
    "stock_batch_help": "Preencha a coluna Quantidade a adicionar com unidades inteiras. Branco ou zero ignora a linha.",
    "stock_batch_once": "Cada arquivo registra um lote de até 1.000 produtos. Baixe outro arquivo para registrar novas entradas.",
    "stock_batch_amount": "Quantidade a adicionar", "stock_batch_projected": "Saldo projetado",
    "stock_batch_result": "Saldo gravado", "stock_batch_saved": "Entradas registradas.",
    "stock_batch_confirm": "Confirmar entradas", "stock_batch_reason": "Informe um motivo de 3 a 240 caracteres.",
    "stock_batch_invalid": "Confira o código do produto e informe uma quantidade inteira positiva, zero ou em branco.",
    "stock_batch_sku": "Produto inexistente ou inativo. Baixe a planilha atual.",
    "stock_batch_balance": "A quantidade ultrapassa o limite de saldo.",
    "stock_batch_file": "Use uma planilha de entradas exportada por este sistema.",
    "stock_batch_used": "Este arquivo já registrou outro lote. Baixe uma nova planilha.",
})
TEXT["es"].update({
    "stock_settings": "Configuración de inventario", "stock_allow_negative": "Permitir inventario negativo para todos los productos",
    "stock_negative_enabled": "Inventario negativo permitido", "stock_negative_disabled": "Inventario negativo bloqueado para nuevas salidas",
    "inventory_policy": "Política de inventario",
    "stock_negative_help": "Al desmarcar, los saldos negativos existentes siguen visibles y pueden recuperarse con entradas.",
    "stock_batch": "Importar entradas", "stock_batch_download": "Descargar productos y saldos",
    "stock_batch_help": "Completa Cantidad a añadir con unidades enteras. En blanco o cero omite la fila.",
    "stock_batch_once": "Cada archivo registra un lote de hasta 1.000 productos. Descarga otro archivo para registrar nuevas entradas.",
    "stock_batch_amount": "Cantidad a añadir", "stock_batch_projected": "Saldo proyectado",
    "stock_batch_result": "Saldo registrado", "stock_batch_saved": "Entradas registradas.",
    "stock_batch_confirm": "Confirmar entradas", "stock_batch_reason": "Indica un motivo de 3 a 240 caracteres.",
    "stock_batch_invalid": "Revisa el código e indica una cantidad entera positiva, cero o en blanco.",
    "stock_batch_sku": "Producto inexistente o inactivo. Descarga la hoja actual.",
    "stock_batch_balance": "La cantidad supera el límite de saldo.",
    "stock_batch_file": "Usa una hoja de entradas exportada por este sistema.",
    "stock_batch_used": "Este archivo ya registró otro lote. Descarga una hoja nueva.",
})
