"""USD/PYG rate selection and a cache of the public daily reference."""

from datetime import datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from html.parser import HTMLParser
import json
import re
from urllib.request import Request, urlopen
from urllib.parse import urlparse

import psycopg
from psycopg.rows import dict_row

SCALES = {"USD": 2, "PYG": 0}
URL = "https://www.bcp.gov.py/webapps/web/cotizacion/monedas"
ALTERNATE_URL = "https://open.er-api.com/v6/latest/USD"
PROVIDER_ERRORS = (OSError, ValueError, KeyError, TypeError, OverflowError, InvalidOperation)


def convert_minor(minor, source, target, rate):
    if source not in SCALES or target not in SCALES:
        raise ValueError("currency")
    if source == target:
        return minor
    value = Decimal(minor).scaleb(-SCALES[source])
    converted = value * rate if source == "USD" else value / rate
    return int((converted * (10 ** SCALES[target])).quantize(Decimal(1), rounding=ROUND_HALF_UP))


def current_in(connection):
    return connection.execute(
        """
        SELECT rate.* FROM fx_policy policy JOIN fx_rates rate ON rate.id = policy.active_rate_id
        WHERE policy.id FOR SHARE OF policy
        """
    ).fetchone()


def state():
    with psycopg.connect(row_factory=dict_row) as connection:
        policy = connection.execute("SELECT * FROM fx_policy WHERE id").fetchone()
        policy["active"] = connection.execute("SELECT * FROM fx_rates WHERE id = %s", (policy["active_rate_id"],)).fetchone()
        policy["reference"] = connection.execute("SELECT * FROM fx_rates WHERE id = %s", (policy["reference_rate_id"],)).fetchone()
        return policy


def configure(actor_id, mode, value="", reason=""):
    if mode not in ("manual", "automatic"):
        raise ValueError("mode")
    with psycopg.connect(row_factory=dict_row) as connection:
        policy = connection.execute("SELECT * FROM fx_policy WHERE id FOR UPDATE").fetchone()
        if mode == "manual":
            normalized = value.strip().replace(",", ".")
            try:
                rate = Decimal(normalized)
            except InvalidOperation as error:
                raise ValueError("rate") from error
            reason = reason.strip()
            if not rate.is_finite() or not 0 < rate <= 1000000 or rate.as_tuple().exponent < -6 or not 3 <= len(reason) <= 240 or chr(0) in reason:
                raise ValueError("rate")
            selected = connection.execute(
                """
                INSERT INTO fx_rates (pyg_per_usd, source, published_at, actor_id, reason)
                VALUES (%s, 'manual', now(), %s, %s) RETURNING id
                """, (rate, actor_id, reason),
            ).fetchone()["id"]
        else:
            selected = policy["reference_rate_id"]
            if selected is None:
                raise ValueError("reference")
        connection.execute("UPDATE fx_policy SET mode = %s, active_rate_id = %s WHERE id", (mode, selected))
        connection.execute("INSERT INTO fx_audit (actor_id, action) VALUES (%s, %s)", (actor_id, "fx_" + mode))


class QuoteTable(HTMLParser):
    def __init__(self):
        super().__init__()
        self.rows = []
        self.row = None
        self.cell = None

    def handle_starttag(self, tag, attrs):
        if tag == "tr":
            self.row = []
        elif tag in ("td", "th") and self.row is not None:
            self.cell = []

    def handle_data(self, data):
        if self.cell is not None:
            self.cell.append(data)

    def handle_endtag(self, tag):
        if tag in ("td", "th") and self.cell is not None and self.row is not None:
            self.row.append(" ".join("".join(self.cell).split()))
            self.cell = None
        elif tag == "tr" and self.row is not None:
            self.rows.append(self.row)
            self.row = None
            self.cell = None


def parse_reference(html, now):
    table = QuoteTable()
    table.feed(html)
    headings = [cell for row in table.rows for cell in row if cell.startswith("PLANILLA DE COTIZACIONES AL ")]
    quotes = [row for row in table.rows if len(row) == 4 and row[1:3] == ["USD", "1,0000"]]
    if len(headings) != 1 or len(quotes) != 1:
        raise ValueError("BCP table")
    match = re.search(r" ([0-9]{1,2}) DE ([A-Z]+) DEL ([0-9]{4})$", headings[0])
    if match is None:
        raise ValueError("BCP date")
    day, month, year = match.groups()
    months = "ENERO FEBRERO MARZO ABRIL MAYO JUNIO JULIO AGOSTO SEPTIEMBRE OCTUBRE NOVIEMBRE DICIEMBRE".split()
    # The table provides a reference day, stored at UTC midnight.
    published = datetime(int(year), months.index(month) + 1, int(day), tzinfo=timezone.utc)
    value = quotes[0][3]
    if not re.fullmatch(r"[0-9]{1,3}(?:\.[0-9]{3})*,[0-9]{2}", value):
        raise ValueError("BCP rate")
    rate = Decimal(value.replace(".", "").replace(",", "."))
    if not 0 < rate <= 1000000 or not now - timedelta(days=7) <= published <= now:
        raise ValueError("BCP reference")
    return rate, published, now + timedelta(hours=1)


def fetch_reference():
    request = Request(URL, headers={"User-Agent": "Mozilla/5.0", "Accept": "text/html"})
    with urlopen(request, timeout=10) as response:
        if urlparse(response.url).hostname != "www.bcp.gov.py":
            raise ValueError("provider")
        payload = response.read(1000001)
        if len(payload) > 1000000:
            raise ValueError("payload")
    return parse_reference(payload.decode("utf-8"), datetime.now(timezone.utc))


def fetch_alternate():
    request = Request(ALTERNATE_URL, headers={"Accept": "application/json"})
    with urlopen(request, timeout=10) as response:
        origin = urlparse(response.url)
        if origin.scheme != "https" or origin.hostname != "open.er-api.com":
            raise ValueError("provider")
        payload = response.read(1000001)
        if len(payload) > 1000000:
            raise ValueError("payload")
    return parse_alternate(payload, datetime.now(timezone.utc))


def parse_alternate(payload, now):
    quote = json.loads(payload, parse_float=Decimal)
    if quote["result"] != "success" or quote["base_code"] != "USD":
        raise ValueError("alternate quote")
    timestamp = quote["time_last_update_unix"]
    value = quote["rates"]["PYG"]
    if type(timestamp) is not int or type(value) not in (int, Decimal):
        raise ValueError("alternate data")
    published = datetime.fromtimestamp(timestamp, timezone.utc)
    rate = Decimal(value)
    if not rate.is_finite() or not 0 < rate <= 1000000 or not now - timedelta(days=2) <= published <= now:
        raise ValueError("alternate reference")
    rate = rate.quantize(Decimal("0.000001"), rounding=ROUND_HALF_UP)
    if rate == 0:
        raise ValueError("alternate rate")
    return rate, published, now + timedelta(hours=1)


def fetch_automatic():
    try:
        return "bcp", fetch_reference()
    except PROVIDER_ERRORS:
        return "exchangerate_api", fetch_alternate()


def refresh(*, force=False):
    with psycopg.connect(row_factory=dict_row) as connection:
        locked = connection.execute("SELECT pg_try_advisory_xact_lock(510052028) AS locked").fetchone()["locked"]
        if not locked:
            return False
        policy = connection.execute("SELECT * FROM fx_policy WHERE id").fetchone()
        now = datetime.now(timezone.utc)
        if not force and policy["next_check"] and policy["next_check"] > now:
            return False
        try:
            source, (rate, published, next_check) = fetch_automatic()
        except PROVIDER_ERRORS:
            connection.execute(
                "UPDATE fx_policy SET last_checked = now(), next_check = now() + interval '1 hour', last_error = 'provider_unavailable' WHERE id"
            )
            return False
        row = connection.execute(
            """
            INSERT INTO fx_rates (pyg_per_usd, source, published_at)
            VALUES (%s, %s, %s)
            ON CONFLICT (source, published_at, pyg_per_usd)
            DO UPDATE SET checked_at = now() RETURNING id
            """, (rate, source, published),
        ).fetchone()
        # Re-read mode after the HTTP request so a simultaneous manual choice is respected.
        policy = connection.execute("SELECT * FROM fx_policy WHERE id FOR UPDATE").fetchone()
        connection.execute(
            """
            UPDATE fx_policy SET reference_rate_id = %s,
                active_rate_id = CASE WHEN mode = 'automatic' THEN %s ELSE active_rate_id END,
                last_checked = now(), next_check = %s, last_error = NULL WHERE id
            """, (row["id"], row["id"], next_check),
        )
        return True
