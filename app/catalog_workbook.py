"""Bounded Excel catalog round trips with optimistic updates."""
from collections import Counter
from decimal import Decimal
from io import BytesIO
import re
from zipfile import BadZipFile, ZipFile
from xml.etree.ElementTree import ParseError

from defusedxml.common import DefusedXmlException
from openpyxl import Workbook, load_workbook
from openpyxl.styles import Alignment
from openpyxl.utils import get_column_letter
from openpyxl.utils.exceptions import InvalidFileException
from openpyxl.worksheet.table import Table, TableStyleInfo
import psycopg
from psycopg.errors import UniqueViolation
from psycopg.rows import dict_row

from app import catalog, finance, fx

LIMIT = 1000
FILE_LIMIT = 1024 * 1024
DETAILS = ("description", "brand", "category", "variation", "barcode")
PRICES = ("usd_cost_minor", "usd_price_minor")
HEADERS = {
    "pt": ("Código interno", "Descrição", "Marca", "Categoria", "Variação", "Código de barras",
           "Custo USD", "Preço de venda USD", "Custo PYG", "Preço de venda PYG", "Status", "Saldo atual", "Referência"),
    "es": ("Código interno", "Descripción", "Marca", "Categoría", "Variación", "Código de barras",
           "Costo USD", "Precio de venta USD", "Costo PYG", "Precio de venta PYG", "Estado", "Saldo actual", "Referencia"),
}


class ImportErrorAtLine(ValueError):
    def __init__(self, key, line=None):
        super().__init__(key)
        self.key = key
        self.line = line


def export_rows(page):
    with psycopg.connect(row_factory=dict_row) as connection:
        return connection.execute(
            """
            SELECT sku.*, (SELECT coalesce(sum(delta), 0) FROM inventory_movements
                           WHERE sku_id = sku.id) AS balance
            FROM catalog_skus sku ORDER BY sku.id LIMIT %s OFFSET %s
            """,
            (LIMIT, (page - 1) * LIMIT),
        ).fetchall()


def workbook_bytes(locale, rows, labels, rate=None):
    book = Workbook()
    sheet = book.active
    sheet.title = labels["workbook_sheet"]
    sheet.append(HEADERS[locale])
    sheet.freeze_panes = "A2"
    sheet.column_dimensions["M"].hidden = True
    for index, width in enumerate((18, 38, 22, 22, 22, 23, 15, 21, 15, 21, 14, 15), 1):
        sheet.column_dimensions[get_column_letter(index)].width = width
    for column in ("A", "F"):
        sheet.column_dimensions[column].number_format = "@"
    for row in rows:
        costs = [row[key] for key in PRICES]
        sheet.append([
            row["code"], *(row[key] for key in DETAILS),
            *(Decimal(value).scaleb(-2) if value is not None else None for value in costs),
            *(fx.convert_minor(value, "USD", "PYG", rate) if rate and value is not None else None for value in costs),
            labels["active" if row["active"] else "inactive"], int(row["balance"]), f'{row["id"]}:{row["version"]}',
        ])
        for cell in sheet[sheet.max_row][:6]:
            if isinstance(cell.value, str):
                cell.data_type = "s"
    if not rows:
        sheet.append([None] * len(HEADERS[locale]))
    for cells in sheet.iter_rows(min_row=2, max_col=8):
        cells[0].number_format = cells[5].number_format = "@"
        cells[6].number_format = cells[7].number_format = "0.00"
    table = Table(displayName="CatalogProducts", ref=f"A1:M{sheet.max_row}")
    table.tableStyleInfo = TableStyleInfo(name="TableStyleMedium4", showRowStripes=True)
    sheet.add_table(table)
    instructions = book.create_sheet(labels["workbook_instructions"])
    instructions.column_dimensions["A"].width = 115
    for text in (
        labels["workbook_instructions"], labels["workbook_help"], labels["workbook_edit"],
        labels["workbook_readonly"], labels["workbook_blank"], labels["workbook_limit"],
        f"1 USD = {rate:f} PYG" if rate else labels["workbook_no_rate"],
    ):
        instructions.append([text])
        instructions[f"A{instructions.max_row}"].alignment = Alignment(wrap_text=True, vertical="top")
        instructions.row_dimensions[instructions.max_row].height = 33
    output = BytesIO()
    book.save(output)
    return output.getvalue()


def amount(value, *, allow_zero=False):
    if value is None or value == "":
        return None
    if type(value) not in (int, float, str):
        raise ValueError("amount")
    return finance.parse_amount(str(value), 2, allow_zero=allow_zero)


WORKBOOK_ERRORS = (BadZipFile, InvalidFileException, DefusedXmlException, ParseError, ValueError,
            IndexError, KeyError, TypeError, OverflowError, OSError, NotImplementedError)


def load_bounded_workbook(data):
    try:
        with ZipFile(BytesIO(data)) as archive:
            members = archive.infolist()
            if (len(data) > FILE_LIMIT or len(members) > 64
                    or sum(member.file_size for member in members) > 12 * FILE_LIMIT
                    or any(member.flag_bits & 1 or "vbaproject" in member.filename.lower() for member in members)):
                raise ImportErrorAtLine("workbook_invalid")
        return load_workbook(BytesIO(data), read_only=True, keep_links=False)
    except WORKBOOK_ERRORS as exc:
        raise ImportErrorAtLine("workbook_invalid") from exc


def read_rows(data):
    book = None
    try:
        book = load_bounded_workbook(data)
        sheet = book.worksheets[0]
        sheet.reset_dimensions()
        rows = sheet.iter_rows(max_col=13)
        header = next(rows, ())
        if tuple(cell.value for cell in header) not in HEADERS.values():
            raise ImportErrorAtLine("import_header", 1)
        seen_codes, seen_barcodes, parsed = set(), set(), []
        for line, cells in enumerate(rows, 2):
            if line > LIMIT + 1:
                raise ImportErrorAtLine("import_limit", line)
            if not any(cell.value is not None for cell in cells):
                continue
            values = [cell.value for cell in cells]
            if any(cell.data_type in ("f", "e") for cell in (*cells[:8], cells[12])):
                raise ImportErrorAtLine("workbook_formula", line)
            try:
                if any(value is not None and not isinstance(value, str) for value in values[:6]):
                    raise ValueError("text")
                code = catalog.sku_code(values[0] or "")
                details = catalog.sku_details(dict(zip(DETAILS, (value or "" for value in values[1:6]), strict=True)))
                details[PRICES[0]] = amount(values[6], allow_zero=True)
                details[PRICES[1]] = amount(values[7])
                ref = values[12]
                if ref is not None:
                    if not isinstance(ref, str) or not re.fullmatch(r"[1-9][0-9]{0,18}:[1-9][0-9]{0,18}", ref):
                        raise ValueError("reference")
                    ref = tuple(map(int, ref.split(":")))
                    if max(ref) > 2**63 - 1:
                        raise ValueError("reference")
            except ValueError as exc:
                raise ImportErrorAtLine("workbook_row", line) from exc
            barcode = details["barcode"]
            if code in seen_codes or (barcode and barcode in seen_barcodes):
                raise ImportErrorAtLine("sku_duplicate", line)
            seen_codes.add(code)
            if barcode:
                seen_barcodes.add(barcode)
            parsed.append((line, code, details, ref))
        if not parsed:
            raise ImportErrorAtLine("import_empty")
        return parsed
    except ImportErrorAtLine:
        raise
    except WORKBOOK_ERRORS as exc:
        raise ImportErrorAtLine("workbook_invalid") from exc
    finally:
        if book:
            book.close()


def process(data, actor_id, *, confirm=False):
    rows = read_rows(data)
    line = None
    result = []
    try:
        with psycopg.connect(row_factory=dict_row) as connection:
            if confirm:
                connection.execute("SELECT pg_advisory_xact_lock(210574793, 2)")
            codes = [row[1] for row in rows]
            barcodes = [row[2]["barcode"] for row in rows if row[2]["barcode"]]
            current = connection.execute(
                """SELECT * FROM catalog_skus WHERE code = ANY(%s) OR barcode = ANY(%s)
                   ORDER BY id""" + (" FOR UPDATE" if confirm else ""), (codes, barcodes),
            ).fetchall()
            by_code = {row["code"]: row for row in current}
            by_barcode = {row["barcode"]: row["code"] for row in current}
            for line, code, details, ref in rows:
                previous = by_code.get(code)
                if ref is not None and (not previous or (previous["id"], previous["version"]) != ref):
                    raise ImportErrorAtLine("workbook_conflict", line)
                if ref is None and previous:
                    raise ImportErrorAtLine("workbook_conflict", line)
                if by_barcode.get(details["barcode"], code) != code and details["barcode"]:
                    raise ImportErrorAtLine("sku_duplicate", line)
                action = "workbook_new"
                if previous:
                    action = "workbook_update" if any(previous[key] != value for key, value in details.items()) else "workbook_same"
                result.append((line, code, details["description"], action))
                if confirm and action != "workbook_same":
                    write_row(connection, actor_id, code, details, previous)
    except UniqueViolation as exc:
        raise ImportErrorAtLine("sku_duplicate", line) from exc
    return result, Counter(row[3] for row in result)


def write_row(connection, actor_id, code, details, previous):
    values = {**details, "code": code}
    if previous:
        sku = connection.execute(
            """UPDATE catalog_skus SET description = %(description)s, brand = %(brand)s,
               category = %(category)s, variation = %(variation)s, barcode = %(barcode)s,
               usd_cost_minor = %(usd_cost_minor)s, usd_price_minor = %(usd_price_minor)s,
               version = version + 1 WHERE id = %(id)s RETURNING id""",
            {**values, "id": previous["id"]},
        ).fetchone()
    else:
        sku = connection.execute(
            """INSERT INTO catalog_skus (code, description, brand, category, variation, barcode, usd_cost_minor, usd_price_minor)
               VALUES (%(code)s, %(description)s, %(brand)s, %(category)s, %(variation)s, %(barcode)s,
                       %(usd_cost_minor)s, %(usd_price_minor)s) RETURNING id""",
            values,
        ).fetchone()
    catalog.audit(connection, sku["id"], actor_id, "edited" if previous else "created")
