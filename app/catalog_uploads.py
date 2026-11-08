"""Bounded catalog imports and product photos."""

from base64 import b64decode, urlsafe_b64encode
from binascii import Error as Base64Error
import csv
from hashlib import sha256
from hmac import compare_digest, digest
from io import BytesIO, StringIO

import psycopg
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import Response
from PIL import Image, ImageOps
from psycopg.errors import UniqueViolation
from python_multipart.exceptions import MultipartParseError
from starlette.concurrency import run_in_threadpool
from starlette.datastructures import UploadFile
from starlette.formparsers import MultiPartException, MultiPartParser

from app import catalog, catalog_workbook, fx
from app.catalog_workbook import ImportErrorAtLine
from app.web import is_admin_role
from app.web import (
    NO_STORE, SESSION_COOKIE, TEXT, parse_form, active_session, change_language, check_csrf, master_session,
    read_form, redirect, render,
)

router = APIRouter()
CSV_FIELDS = ("code", "description", "brand", "category", "variation", "barcode")
CSV_LIMIT = 1024 * 1024
PHOTO_LIMIT = 5 * 1024 * 1024


async def upload(request, csrf, limit, *, extra_field=None):
    if request.headers.get("content-type", "").split(";")[0].strip().lower() != "multipart/form-data":
        raise HTTPException(400)

    async def bounded_stream():
        total = 0
        async for chunk in request.stream():
            total += len(chunk)
            if total > limit + 16 * 1024:
                raise MultiPartException("Upload exceeds request limit")
            yield chunk

    parser = MultiPartParser(
        request.headers, bounded_stream(), max_files=1,
        max_fields=2 if extra_field else 1, max_part_size=1024,
    )
    try:
        form = await parser.parse()
    except (MultiPartException, MultipartParseError) as exc:
        raise HTTPException(400) from exc
    try:
        file = form.get("file")
        if not isinstance(file, UploadFile) or not file.size or file.size > limit:
            raise HTTPException(400)
        check_csrf(form, csrf)
        return await file.read(), form.get(extra_field)
    finally:
        await form.close()


def import_skus(data, actor_id):
    line = 1
    try:
        source = StringIO(data.decode("utf-8-sig"), newline="")
        header = source.readline()
        source.seek(0)
        delimiter = ";" if ";" in header else ","
        reader = csv.reader(source, delimiter=delimiter, strict=True)
        fields = [field.strip().lower() for field in next(reader, ())]
        if (
            not {"code", "description"}.issubset(fields)
            or len(fields) != len(set(fields))
            or set(fields).difference(CSV_FIELDS)
        ):
            raise ImportErrorAtLine("import_header")
        rows = []
        while True:
            line = reader.line_num + 1
            row = next(reader, None)
            if row is None:
                break
            if not row or (len(row) == len(fields) and not any(value.strip() for value in row)):
                continue
            if len(rows) == 1000:
                raise ImportErrorAtLine("import_limit", line)
            if len(row) != len(fields):
                raise ImportErrorAtLine("import_row", line)
            form = dict(zip(fields, row, strict=True))
            rows.append((line, catalog.sku_code(form["code"]), catalog.sku_details(form)))
    except ImportErrorAtLine:
        raise
    except (ValueError, csv.Error) as exc:
        raise ImportErrorAtLine("import_row", line) from exc
    if not rows:
        raise ImportErrorAtLine("import_empty")
    try:
        with psycopg.connect() as connection:
            # Serialize batches so overlapping unique keys cannot deadlock across imports.
            connection.execute("SELECT pg_advisory_xact_lock(210574793, 2)")
            for line, code, details in rows:
                catalog.insert_sku(connection, actor_id, code, details)
    except UniqueViolation as exc:
        raise ImportErrorAtLine("sku_duplicate", line) from exc
    return len(rows)


@router.get("/catalog/import")
def import_page(request: Request, lang: str | None = None, master=Depends(master_session)):
    if lang is not None:
        return change_language(request, "/catalog/import", lang)
    return render(request, "sku_import.html", csrf=master[1], is_master=True, in_catalog=True)


@router.get("/catalog/import/template")
def import_template(master=Depends(master_session)):
    return Response(
        "\ufeff" + ",".join(CSV_FIELDS) + "\r\n",
        media_type="text/csv",
        headers={"Content-Disposition": 'attachment; filename="produtos.csv"', **NO_STORE},
    )


@router.post("/catalog/import")
async def submit_import(request: Request, master=Depends(master_session)):
    actor_id, csrf = master
    try:
        data, _ = await upload(request, csrf, CSV_LIMIT)
        count = await run_in_threadpool(import_skus, data, actor_id)
    except ImportErrorAtLine as exc:
        status = 409 if exc.key == "sku_duplicate" else 400
        return render(
            request, "sku_import.html", status, csrf=csrf, is_master=True, in_catalog=True,
            error=exc.key, line=exc.line,
        )
    return render(
        request, "sku_import.html", csrf=csrf, is_master=True, in_catalog=True, count=count,
    )


def normalize_photo(data):
    with Image.open(BytesIO(data), formats=("JPEG", "PNG", "WEBP")) as source:
        if source.width * source.height > 20_000_000 or getattr(source, "is_animated", False):
            raise ValueError("photo dimensions or frames")
        image = ImageOps.exif_transpose(source)
        image.thumbnail((960, 960))
        rgba = image.convert("RGBA")
        background = Image.new("RGB", rgba.size, "white")
        background.paste(rgba, mask=rgba.getchannel("A"))
        output = BytesIO()
        background.save(output, "JPEG", quality=85)
        return output.getvalue()


def write_photo(request, master, sku_id, version, data):
    sku = catalog.get_sku(sku_id) if 0 < sku_id <= 2**63 - 1 else None
    if sku is None:
        raise HTTPException(404)
    try:
        version = int(version)
        if not 0 < version <= 2**63 - 1:
            raise ValueError("version")
        image = normalize_photo(data) if data is not None else None
    except (TypeError, ValueError, OSError, SyntaxError, Image.DecompressionBombError):
        return render(
            request, "sku_form.html", 400, csrf=master[1], is_master=True, in_catalog=True,
            sku=sku, error="photo_invalid",
        )
    with psycopg.connect() as connection:
        changed = connection.execute(
            """UPDATE catalog_skus SET version = version + 1
               WHERE id = %s AND version = %s RETURNING id""",
            (sku_id, version),
        ).fetchone()
        if changed:
            if image is None:
                connection.execute("DELETE FROM catalog_images WHERE sku_id = %s", (sku_id,))
            else:
                connection.execute(
                    """INSERT INTO catalog_images (sku_id, image) VALUES (%s, %s)
                       ON CONFLICT (sku_id) DO UPDATE SET image = EXCLUDED.image""",
                    (sku_id, image),
                )
            catalog.audit(connection, sku_id, master[0], "edited")
    if not changed:
        return render(
            request, "sku_form.html", 409, csrf=master[1], is_master=True, in_catalog=True,
            sku=catalog.get_sku(sku_id), error="sku_stale",
        )
    return redirect(f"/catalog/{sku_id}/edit")


@router.get("/catalog/{sku_id}/image")
def read_photo(sku_id: int, account=Depends(active_session)):
    if not 0 < sku_id <= 2**63 - 1:
        raise HTTPException(404)
    with psycopg.connect() as connection:
        photo = connection.execute(
            """SELECT image FROM catalog_images JOIN catalog_skus ON catalog_skus.id = sku_id
               WHERE sku_id = %s AND (active OR %s)""",
            (sku_id, is_admin_role(account[1])),
        ).fetchone()
    if photo is None:
        raise HTTPException(404)
    return Response(photo[0], media_type="image/jpeg", headers={**NO_STORE, "X-Content-Type-Options": "nosniff"})


@router.post("/catalog/{sku_id}/image")
async def submit_photo(sku_id: int, request: Request, master=Depends(master_session)):
    data, version = await upload(request, master[1], PHOTO_LIMIT, extra_field="version")
    return await run_in_threadpool(write_photo, request, master, sku_id, version, data)


@router.post("/catalog/{sku_id}/image/remove")
def remove_photo(sku_id: int, request: Request, master=Depends(master_session), form=Depends(read_form)):
    check_csrf(form, master[1])
    return write_photo(request, master, sku_id, form.get("version"), None)


def download_workbook(request, rows, filename, rate=None):
    locale = request.cookies.get("locale", "pt")
    if locale not in catalog_workbook.HEADERS:
        locale = "pt"
    return Response(
        catalog_workbook.workbook_bytes(locale, rows, TEXT[locale], rate),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{filename}"', **NO_STORE},
    )


@router.get("/catalog/import/xlsx/template")
def xlsx_template(request: Request, master=Depends(master_session)):
    return download_workbook(request, [], "modelo-produtos.xlsx")


@router.get("/catalog/import/xlsx/export")
def xlsx_export(request: Request, page: int = 1, master=Depends(master_session)):
    if not 1 <= page <= 1_000_000:
        raise HTTPException(400)
    rows = catalog_workbook.export_rows(page)
    if page > 1 and not rows:
        raise HTTPException(404)
    active = fx.state()["active"]
    rate = active["pyg_per_usd"] if active else None
    return download_workbook(request, rows, f"produtos-{page}.xlsx", rate)


def workbook_signature(request, data):
    key = request.cookies[SESSION_COOKIE].encode()
    return digest(key, b"catalog-workbook:" + sha256(data).digest(), "sha256").hex()


def workbook_error(request, csrf, exc):
    status = 409 if exc.key in ("sku_duplicate", "workbook_conflict") else 400
    return render(request, "sku_import.html", status, csrf=csrf, is_master=True,
                  in_catalog=True, error=exc.key, line=exc.line)


@router.post("/catalog/import/xlsx")
async def preview_xlsx(request: Request, master=Depends(master_session)):
    actor_id, csrf = master
    data, _ = await upload(request, csrf, catalog_workbook.FILE_LIMIT)
    try:
        preview, totals = await run_in_threadpool(catalog_workbook.process, data, actor_id)
    except ImportErrorAtLine as exc:
        return workbook_error(request, csrf, exc)
    return render(
        request, "sku_import.html", csrf=csrf, is_master=True, in_catalog=True,
        preview=preview, totals=totals, payload=urlsafe_b64encode(data).decode(),
        signature=workbook_signature(request, data),
    )


@router.post("/catalog/import/xlsx/confirm")
async def confirm_xlsx(request: Request, master=Depends(master_session)):
    actor_id, csrf = master
    form = await parse_form(request, 4 * ((catalog_workbook.FILE_LIMIT + 2) // 3) + 1024, 3)
    check_csrf(form, csrf)
    try:
        data = b64decode(form.get("payload", ""), altchars=b"-_", validate=True)
    except (Base64Error, ValueError):
        raise HTTPException(400)
    if not compare_digest(form.get("signature", "").encode(), workbook_signature(request, data).encode()):
        raise HTTPException(403)
    try:
        _, totals = await run_in_threadpool(catalog_workbook.process, data, actor_id, confirm=True)
    except ImportErrorAtLine as exc:
        return workbook_error(request, csrf, exc)
    return render(request, "sku_import.html", csrf=csrf, is_master=True, in_catalog=True,
                  totals=totals, workbook_saved=True)


TEXT["pt"].update({
    "workbook_sheet": "Produtos", "workbook_instructions": "Instruções",
    "workbook_template": "Baixar modelo Excel vazio", "workbook_export": "Baixar produtos do banco",
    "workbook_batch": "Lote da exportação", "workbook_file": "Planilha Excel (.xlsx)",
    "workbook_help": "Edite a tabela no Excel e salve o arquivo .xlsx. Adicione novos produtos nas linhas abaixo da tabela.",
    "workbook_edit": "Preencha código interno, descrição e demais dados. Informe custo e preço em USD. Preserve os códigos como texto.",
    "workbook_readonly": "PYG, saldo e status são para consulta. Preserve o código e a referência das linhas exportadas.",
    "workbook_blank": "Campos opcionais em branco limpam o valor existente. Apagar uma linha da planilha preserva o produto no banco.",
    "workbook_limit": "Até 1.000 linhas por lote. Se precisar de mais, exporte os lotes seguintes.",
    "workbook_no_rate": "Sem cotação comercial para esta planilha.",
    "workbook_preview": "Conferir planilha", "workbook_confirm": "Confirmar importação",
    "workbook_new": "Novos", "workbook_update": "Atualizados", "workbook_same": "Sem alteração",
    "workbook_saved": "Planilha processada.", "workbook_invalid": "Não foi possível ler o arquivo. Use o modelo Excel do sistema.",
    "workbook_row": "Confira os campos, os valores em USD e os códigos em formato texto.",
    "workbook_conflict": "Produto existente ou alterado desde a exportação. Baixe a planilha atual e revise a linha.",
    "workbook_formula": "Use valores nas colunas editáveis, sem fórmulas.",
})
TEXT["es"].update({
    "workbook_sheet": "Productos", "workbook_instructions": "Instrucciones",
    "workbook_template": "Descargar plantilla Excel vacía", "workbook_export": "Descargar productos registrados",
    "workbook_batch": "Lote de exportación", "workbook_file": "Hoja Excel (.xlsx)",
    "workbook_help": "Edita la tabla en Excel y guarda el archivo .xlsx. Añade productos nuevos en las filas debajo de la tabla.",
    "workbook_edit": "Completa el código interno, la descripción y los demás datos. Introduce costo y precio en USD. Conserva los códigos como texto.",
    "workbook_readonly": "PYG, saldo y estado son de consulta. Conserva el código y la referencia de las filas exportadas.",
    "workbook_blank": "Los campos opcionales vacíos borran el valor anterior. Quitar una fila conserva el producto en el sistema.",
    "workbook_limit": "Hasta 1.000 filas por lote. Si necesitas más, exporta los lotes siguientes.",
    "workbook_no_rate": "Sin cotización comercial para esta hoja.",
    "workbook_preview": "Revisar hoja", "workbook_confirm": "Confirmar importación",
    "workbook_new": "Nuevos", "workbook_update": "Actualizados", "workbook_same": "Sin cambios",
    "workbook_saved": "Hoja procesada.", "workbook_invalid": "No se pudo leer el archivo. Usa la plantilla Excel del sistema.",
    "workbook_row": "Revisa los campos, los valores en USD y los códigos en formato de texto.",
    "workbook_conflict": "Producto existente o modificado desde la exportación. Descarga la hoja actual y revisa la fila.",
    "workbook_formula": "Usa valores en las columnas editables, sin fórmulas.",
})
