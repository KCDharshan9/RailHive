"""Flask application for Railway Reservation Analytics."""

from __future__ import annotations

import json
import math
import sqlite3
from datetime import date
from pathlib import Path

from flask import Flask, current_app, jsonify, render_template, request, url_for

try:
    from . import fixture
except ImportError:
    import fixture

BASE_DIR = Path(__file__).resolve().parent.parent
WEB_DIR = BASE_DIR / "website"
ANALYTICS_FILE = WEB_DIR / "data" / "analytics.json"
SAMPLE_FILE = WEB_DIR / "data" / "bookings_sample.json"
DB_FILES = (
    BASE_DIR / "data" / "processed" / "analytics.db",
    WEB_DIR / "data" / "analytics.db",
)
# page key: (static filename, Flask endpoint)
PAGES = {
    "index": ("index.html", "index"),
    "routes": ("routes.html", "routes_page"),
    "revenue": ("revenue.html", "revenue_page"),
    "waitlist": ("waitlist.html", "waitlist_page"),
    "delays": ("delays.html", "delays_page"),
    "explorer": ("explorer.html", "explorer_page"),
}
STATUS_CODES = ("CNF", "RAC", "WL", "CAN")
_analytics_cache = {"mtime": None, "data": None}
_sample_cache = {"mtime": None, "data": None}

def indian_number(value, decimals=0):
    """Format a number with Indian digit grouping without extra packages."""
    try:
        number = float(value)
    except (TypeError, ValueError):
        number = 0.0
    negative = number < 0
    text = f"{abs(number):.{decimals}f}"
    whole, _, fraction = text.partition(".")
    if len(whole) > 3:
        head, tail = whole[:-3], whole[-3:]
        chunks = []
        while len(head) > 2:
            chunks.insert(0, head[-2:])
            head = head[:-2]
        if head:
            chunks.insert(0, head)
        whole = ",".join(chunks + [tail])
    result = whole + (f".{fraction}" if decimals else "")
    return ("-" if negative else "") + result

def rupee(value):
    return "Rs " + indian_number(value, 0)

def rupee_compact(value):
    try:
        number = float(value)
    except (TypeError, ValueError):
        number = 0.0
    if abs(number) >= 10000000:
        return "Rs " + indian_number(number / 10000000, 2) + " crore"
    if abs(number) >= 100000:
        return "Rs " + indian_number(number / 100000, 2) + " lakh"
    return rupee(number)

def percent(value):
    return indian_number(value, 1) + "%"

def get_analytics():
    """Read analytics.json, reloading only when its mtime changes."""
    try:
        mtime = ANALYTICS_FILE.stat().st_mtime
    except OSError:
        return fixture.get_fixture_analytics()
    if _analytics_cache["mtime"] == mtime and _analytics_cache["data"] is not None:
        return _analytics_cache["data"]
    try:
        payload = json.loads(ANALYTICS_FILE.read_text(encoding="utf-8"))
        data = fixture.with_defaults(payload)
    except (OSError, ValueError):
        data = fixture.get_fixture_analytics()
    _analytics_cache["mtime"] = mtime
    _analytics_cache["data"] = data
    return data

def load_sample():
    """Load the explorer sample JSON, creating it when absent."""
    try:
        if not SAMPLE_FILE.is_file():
            fixture.ensure_sample(SAMPLE_FILE)
        mtime = SAMPLE_FILE.stat().st_mtime
    except OSError:
        return fixture.build_rows(500)
    if _sample_cache["mtime"] == mtime and _sample_cache["data"] is not None:
        return _sample_cache["data"]
    try:
        data = json.loads(SAMPLE_FILE.read_text(encoding="utf-8"))
        if not isinstance(data, list):
            raise ValueError("sample is not a list")
    except (OSError, ValueError):
        data = []
    _sample_cache["mtime"] = mtime
    _sample_cache["data"] = data
    return data

def _bounded_int(raw, default, low, high):
    try:
        value = int(raw)
    except (TypeError, ValueError):
        return default
    return max(low, min(high, value))
def _clean(value, limit=80):
    return str(value or "").strip()[:limit]

def _iso_date(raw):
    value = _clean(raw, 10)
    if not value:
        return None
    try:
        return date.fromisoformat(value).isoformat()
    except ValueError:
        return None

def _like_pattern(value):
    return value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")

def _sql_filters(args):
    where, params = [], []
    train = _clean(args.get("train"))
    if train:
        where.append("(train_number = ? OR train_name LIKE ? ESCAPE '\\')")
        params.extend([train, f"%{_like_pattern(train)}%"])
    travel_class = _clean(args.get("travel_class"), 4).upper()
    if travel_class:
        where.append("travel_class = ?")
        params.append(travel_class)
    quota = _clean(args.get("quota"), 4).upper()
    if quota:
        where.append("quota = ?")
        params.append(quota)
    status = _clean(args.get("status"), 4).upper()
    if status in STATUS_CODES:
        where.append("current_status = ?")
        params.append(status)
    from_date = _iso_date(args.get("from_date"))
    if from_date:
        where.append("travel_date >= ?")
        params.append(from_date)
    to_date = _iso_date(args.get("to_date"))
    if to_date:
        where.append("travel_date <= ?")
        params.append(to_date)
    station = _clean(args.get("station"), 10).upper()
    if station:
        where.append("(from_station_code = ? OR to_station_code = ?)")
        params.extend([station, station])
    pnr = _clean(args.get("pnr"), 20)
    if pnr:
        where.append("pnr = ?")
        params.append(pnr)
    return (" WHERE " + " AND ".join(where)) if where else "", params

def _page_numbers(args):
    page = _bounded_int(args.get("page"), 1, 1, 1000000)
    size = _bounded_int(args.get("size"), 25, 1, 200)
    return page, size

def query_database(path, args):
    page, size = _page_numbers(args)
    where, params = _sql_filters(args)
    connection = sqlite3.connect(str(path))
    connection.row_factory = sqlite3.Row
    try:
        total = connection.execute(
            "SELECT COUNT(*) FROM bookings" + where, params
        ).fetchone()[0]
        pages = max(1, math.ceil(total / size))
        page = min(page, pages)
        sql = (
            "SELECT * FROM bookings" + where
            + " ORDER BY travel_date DESC, pnr DESC LIMIT ? OFFSET ?"
        )
        rows = [
            dict(row) for row in connection.execute(
                sql, params + [size, (page - 1) * size]
            ).fetchall()
        ]
    finally:
        connection.close()
    return {"rows": rows, "total": int(total), "page": page, "pages": pages}

def _sample_matches(row, args):
    train = _clean(args.get("train"))
    if train:
        number = str(row.get("train_number", ""))
        name = str(row.get("train_name", "")).lower()
        if number != train and train.lower() not in name:
            return False
    travel_class = _clean(args.get("travel_class"), 4).upper()
    if travel_class and str(row.get("travel_class", "")).upper() != travel_class:
        return False
    quota = _clean(args.get("quota"), 4).upper()
    if quota and str(row.get("quota", "")).upper() != quota:
        return False
    status = _clean(args.get("status"), 4).upper()
    if status in STATUS_CODES and row.get("current_status") != status:
        return False
    from_date = _iso_date(args.get("from_date"))
    to_date = _iso_date(args.get("to_date"))
    travel_date = str(row.get("travel_date", ""))
    if from_date and travel_date < from_date:
        return False
    if to_date and travel_date > to_date:
        return False
    station = _clean(args.get("station"), 10).upper()
    if station:
        codes = (
            str(row.get("from_station_code", "")).upper(),
            str(row.get("to_station_code", "")).upper(),
        )
        if station not in codes:
            return False
    pnr = _clean(args.get("pnr"), 20)
    if pnr and str(row.get("pnr", "")) != pnr:
        return False
    return True

def _page_payload(rows, total, page, size):
    pages = max(1, math.ceil(total / size))
    page = min(page, pages)
    start = (page - 1) * size
    return {
        "rows": rows[start:start + size],
        "total": int(total),
        "page": page,
        "pages": pages,
    }

def query_sample(args, rows=None):
    page, size = _page_numbers(args)
    source = load_sample() if rows is None else rows
    filtered = [row for row in source if _sample_matches(row, args)]
    filtered.sort(
        key=lambda row: (str(row.get("travel_date", "")), str(row.get("pnr", ""))),
        reverse=True,
    )
    return _page_payload(filtered, len(filtered), page, size)

def get_bookings(args):
    for path in DB_FILES:
        if path.is_file():
            try:
                return query_database(path, args)
            except sqlite3.Error:
                current_app.logger.warning(
                    "Could not read %s, falling back to the sample rows", path
                )
                break
    return query_sample(args)

def create_app(config=None):
    app = Flask(__name__)
    app.config.update(STATIC_MODE=False, JSON_SORT_KEYS=False)
    if config:
        app.config.update(config)
    app.jinja_env.filters.update(
        num=indian_number, inr=rupee, inr_compact=rupee_compact, pct=percent
    )

    def page_url(name):
        filename, endpoint = PAGES.get(name, PAGES["index"])
        if current_app.config.get("STATIC_MODE"):
            return filename
        return url_for(endpoint)

    def asset(path):
        path = path.lstrip("/")
        if current_app.config.get("STATIC_MODE"):
            return "static/" + path
        return url_for("static", filename=path)

    app.jinja_env.globals.update(page_url=page_url, asset=asset)
    try:
        fixture.ensure_sample(SAMPLE_FILE)
    except OSError as error:
        app.logger.warning("Could not create the sample file: %s", error)
    get_analytics()

    def page(template, active, **extra):
        static_mode = bool(app.config.get("STATIC_MODE"))
        return render_template(
            template,
            analytics=get_analytics(),
            active_page=active,
            static_mode=static_mode,
            bookings_endpoint="" if static_mode else url_for("api_bookings"),
            **extra,
        )

    @app.get("/")
    def index():
        return page("overview.html", "overview")

    simple_pages = (
        ("/routes", "routes_page", "routes.html", "routes"),
        ("/revenue", "revenue_page", "revenue.html", "revenue"),
        ("/waitlist", "waitlist_page", "waitlist.html", "waitlist"),
        ("/delays", "delays_page", "delays.html", "delays"),
    )
    for rule, endpoint, template, active in simple_pages:
        app.add_url_rule(
            rule, endpoint,
            lambda template=template, active=active: page(template, active),
        )

    @app.get("/explorer")
    def explorer_page():
        analytics = get_analytics()
        classes = [row.get("travel_class") for row in analytics["status"]]
        quotas = [row.get("quota") for row in analytics["quota_revenue"]]
        if app.config.get("STATIC_MODE"):
            initial = query_sample(request.args)
        else:
            initial = get_bookings(request.args)
        return page(
            "explorer.html", "explorer", initial=initial, filters=request.args,
            class_options=[value for value in classes if value],
            quota_options=[value for value in quotas if value],
            status_options=STATUS_CODES, size_options=(25, 50, 100, 200),
            bookings_sample=load_sample() if app.config.get("STATIC_MODE") else [],
        )

    @app.get("/api/summary")
    def api_summary():
        return jsonify(get_analytics())

    @app.get("/api/bookings")
    def api_bookings():
        return jsonify(get_bookings(request.args))

    return app

app = create_app()

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=False)
