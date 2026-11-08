"""Export active SKUs and record a signed Excel batch through the stock ledger."""

from hashlib import sha256
from hmac import compare_digest, digest
from io import BytesIO
import json
from uuid import UUID, uuid4, uuid5

from openpyxl import Workbook
from openpyxl.worksheet.table import Table, TableStyleInfo
import psycopg
from psycopg.rows import dict_row, tuple_row
from psycopg.types.json import Jsonb

from app import catalog, inventory
from app.catalog_workbook import ImportErrorAtLine, LIMIT, WORKBOOK_ERRORS, load_bounded_workbook

HEADERS = {
    "pt": ("Código interno", "Descrição", "Código de barras", "Saldo na exportação", "Quantidade a adicionar"),
    "es": ("Código interno", "Descripción", "Código de barras", "Saldo al exportar", "Cantidad a añadir"),
}


def export_token(connection, batch_id):
    key = connection.execute("SELECT workbook_key FROM inventory_policy WHERE id").fetchone()["workbook_key"]
    return digest(key.bytes, b"inventory-entry:" + batch_id.bytes, "sha256").hex()


def export(page, locale, labels):
    batch_id = uuid4()
    with psycopg.connect(row_factory=dict_row) as connection:
        rows = connection.execute(
            """SELECT sku.code, sku.description, sku.barcode,
                      (SELECT coalesce(sum(delta), 0) FROM inventory_movements WHERE sku_id = sku.id) AS balance
               FROM catalog_skus sku WHERE sku.active ORDER BY sku.id LIMIT %s OFFSET %s""",
            (LIMIT, (page - 1) * LIMIT),
        ).fetchall()
        signature = export_token(connection, batch_id)
    if page > 1 and not rows:
        return None
    book = Workbook()
    sheet = book.active
    sheet.title = labels["stock"]
    sheet.append(HEADERS[locale])
    sheet.freeze_panes = "A2"
    for column, width in zip("ABCDE", (19, 42, 23, 23, 24), strict=True):
        sheet.column_dimensions[column].width = width
    for row in rows:
        sheet.append([row["code"], row["description"], row["barcode"], int(row["balance"]), None])
    if not rows:
        sheet.append([None] * 5)
    for cells in sheet.iter_rows(min_row=2, max_col=5):
        for cell in cells[:3]:
            if isinstance(cell.value, str):
                cell.data_type = "s"
        cells[0].number_format = cells[2].number_format = "@"
        cells[4].number_format = "0"
    table = Table(displayName="InventoryEntries", ref=f"A1:E{sheet.max_row}")
    table.tableStyleInfo = TableStyleInfo(name="TableStyleMedium4", showRowStripes=True)
    sheet.add_table(table)
    instructions = book.create_sheet(labels["workbook_instructions"])
    instructions.column_dimensions["A"].width = 120
    instructions.append([labels["stock_batch_help"]])
    instructions.append([labels["stock_batch_once"]])
    meta = book.create_sheet("InventoryBatch")
    meta.append([str(batch_id), signature])
    meta.sheet_state = "veryHidden"
    output = BytesIO()
    book.save(output)
    return output.getvalue()


def parse(data):
    book = load_bounded_workbook(data)
    try:
        meta = book["InventoryBatch"]
        batch_id, signature = UUID(meta["A1"].value), meta["B1"].value
        if not isinstance(signature, str) or len(signature) != 64 or not signature.isascii():
            raise ValueError("signature")
        sheet = book.worksheets[0]
        sheet.reset_dimensions()
        rows = sheet.iter_rows(max_col=5)
        if tuple(cell.value for cell in next(rows, ())) not in HEADERS.values():
            raise ImportErrorAtLine("import_header", 1)
        entries, seen = [], set()
        for line, cells in enumerate(rows, 2):
            if line > LIMIT + 1:
                raise ImportErrorAtLine("import_limit", line)
            quantity = cells[4].value
            if cells[4].data_type in ("f", "e") or (quantity is not None and type(quantity) not in (str, int, float)):
                raise ImportErrorAtLine("stock_batch_invalid", line)
            if isinstance(quantity, str):
                quantity = quantity.strip()
                if not quantity:
                    continue
                if not quantity.isascii() or not quantity.isdecimal() or len(quantity) > 10:
                    raise ImportErrorAtLine("stock_batch_invalid", line)
                quantity = int(quantity)
            if quantity in (None, 0):
                continue
            if not 0 < quantity <= 1000000000 or int(quantity) != quantity:
                raise ImportErrorAtLine("stock_batch_invalid", line)
            code = cells[0].value
            if cells[0].data_type in ("f", "e") or not isinstance(code, str):
                raise ImportErrorAtLine("stock_batch_invalid", line)
            try:
                code = catalog.sku_code(code)
            except ValueError as exc:
                raise ImportErrorAtLine("stock_batch_invalid", line) from exc
            if code in seen:
                raise ImportErrorAtLine("sku_duplicate", line)
            seen.add(code)
            entries.append((line, code, int(quantity)))
        if not entries:
            raise ImportErrorAtLine("import_empty")
        return batch_id, signature, entries
    except ImportErrorAtLine:
        raise
    except (*WORKBOOK_ERRORS, AttributeError) as exc:
        raise ImportErrorAtLine("workbook_invalid") from exc
    finally:
        book.close()


def process(data, actor_id, reason, *, confirm=False):
    reason = (reason or "").strip()
    if not 3 <= len(reason) <= 240 or chr(0) in reason:
        raise ImportErrorAtLine("stock_batch_reason")
    batch_id, signature, entries = parse(data)
    fingerprint = sha256(json.dumps([reason, sorted((code, amount) for _, code, amount in entries)]).encode()).hexdigest()
    with psycopg.connect(row_factory=dict_row) as connection:
        if not compare_digest(signature, export_token(connection, batch_id)):
            raise ImportErrorAtLine("stock_batch_file")
        if confirm:
            connection.execute("SELECT pg_advisory_xact_lock(hashtextextended(%s, 0))", ("stock-batch:" + str(batch_id),))
        previous = connection.execute(
            "SELECT fingerprint, result FROM inventory_entry_batches WHERE id = %s", (batch_id,),
        ).fetchone()
        if previous:
            if previous["fingerprint"] != fingerprint:
                raise ImportErrorAtLine("stock_batch_used")
            return previous["result"], True
        keys = {code: str(uuid5(batch_id, code)) for _, code, _ in entries}
        codes = list(keys)
        if confirm:
            for key in sorted(keys.values()):
                connection.execute("SELECT pg_advisory_xact_lock(hashtextextended(%s, 0))", (key,))
            connection.execute(
                "SELECT id FROM catalog_skus WHERE code = ANY(%s) ORDER BY id FOR UPDATE", (codes,),
            ).fetchall()
        products = connection.execute(
            """SELECT sku.id, sku.code, sku.active, sku.description,
                      (SELECT coalesce(sum(delta), 0) FROM inventory_movements WHERE sku_id = sku.id) AS balance
               FROM catalog_skus sku WHERE sku.code = ANY(%s)""", (codes,),
        ).fetchall()
        by_code = {product["code"]: product for product in products}
        result = []
        with connection.cursor(row_factory=tuple_row) as ledger:
            for line, code, amount in entries:
                product = by_code.get(code)
                if not product or not product["active"]:
                    raise ImportErrorAtLine("stock_batch_sku", line)
                balance = int(product["balance"])
                if balance + amount > 2000000000:
                    raise ImportErrorAtLine("stock_batch_balance", line)
                if confirm:
                    try:
                        inventory.record_in(ledger, actor_id, product["id"], amount, reason, keys[code])
                    except inventory.StockConflict as exc:
                        raise ImportErrorAtLine("stock_batch_balance", line) from exc
                result.append({"code": code, "description": product["description"], "balance": balance,
                               "amount": amount, "updated": balance + amount})
        if confirm:
            connection.execute(
                "INSERT INTO inventory_entry_batches (id, actor_id, fingerprint, result) VALUES (%s, %s, %s, %s)",
                (batch_id, actor_id, fingerprint, Jsonb(result)),
            )
    return result, confirm
