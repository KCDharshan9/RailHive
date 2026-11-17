"""Build the website artefacts from query result TSV files.

Reads data/results/qNN_name.tsv for every result in scripts/result_spec.py,
validates the column count, writes website/data/analytics.json, writes
website/data/bookings_sample.json and creates data/processed/analytics.db.
"""

from __future__ import annotations

import json
import random
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path

from result_spec import INT_FIELDS, RESULTS, SECTION_MAP  # type: ignore

ROOT = Path(__file__).resolve().parent.parent
RESULTS_DIR = ROOT / "data" / "results"
RAW = ROOT / "data" / "raw"
PROCESSED = ROOT / "data" / "processed"
SITE_DATA = ROOT / "website" / "data"

TEXT_FIELDS = {
    "month", "route", "from_station", "to_station", "train_number",
    "train_name", "train_type", "zone", "travel_class", "quota",
    "payment_mode", "channel", "reason",
}

BOOKING_COLUMNS = [
    "pnr", "train_number", "train_name", "train_type", "zone", "travel_date",
    "booking_date", "from_station_code", "from_station_name",
    "to_station_code", "to_station_name", "distance_km", "travel_class",
    "quota", "booking_status", "current_status", "waitlist_position", "fare",
    "refund_amount", "payment_mode", "channel", "passenger_age",
    "passenger_gender", "concession", "cancellation_flag",
    "cancellation_reason", "delay_minutes", "travel_month",
]

SAMPLE_SIZE = 5000


def clean(value: str) -> str:
    value = value.strip()
    if value in {"\\N", "NULL", "null", "None"}:
        return ""
    return value


def read_tsv(path: Path, columns: list[str]) -> list[dict]:
    rows: list[dict] = []
    with path.open("r", encoding="utf-8", errors="replace", newline="") as handle:
        for lineno, line in enumerate(handle, 1):
            line = line.rstrip("\r\n")
            if line == "":
                continue
            parts = line.split("\t")
            if len(parts) != len(columns):
                raise SystemExit(
                    f"{path.name} line {lineno}: expected {len(columns)} columns, "
                    f"got {len(parts)}"
                )
            record = {}
            for name, raw in zip(columns, parts):
                value = clean(raw)
                if name in TEXT_FIELDS:
                    record[name] = value
                elif name in INT_FIELDS:
                    record[name] = int(round(float(value))) if value else 0
                else:
                    record[name] = round(float(value), 2) if value else 0.0
            rows.append(record)
    return rows


def load_results() -> dict[str, list[dict]]:
    out: dict[str, list[dict]] = {}
    missing = []
    for name, columns in RESULTS.items():
        path = RESULTS_DIR / f"{name}.tsv"
        if not path.exists():
            missing.append(path.name)
            continue
        out[name] = read_tsv(path, columns)
    if missing:
        raise SystemExit("Missing result files: " + ", ".join(missing))
    return out


def build_analytics(results: dict[str, list[dict]]) -> dict:
    kpis = results["q01_kpis"][0]

    payload = {
        "meta": {
            "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "engine": engine_label(),
            "bookings": int(kpis["total_passengers"]),
            "unique_pnrs": int(kpis["total_bookings"]),
            "trains": 0,
            "stations": 0,
            "period": period_label(results["q02_monthly"]),
        },
        "kpis": kpis,
    }
    for name, section in SECTION_MAP.items():
        rows = results[name]
        if name == "q03_routes":
            rows = sorted(rows, key=lambda r: r["bookings"], reverse=True)[:40]
        if name == "q04_trains":
            rows = sorted(rows, key=lambda r: r["revenue"], reverse=True)[:40]
        if name == "q11_cancel_reasons":
            rows = [{"reason": r["reason"], "count": r["reason_count"]} for r in rows]
            rows.sort(key=lambda r: r["count"], reverse=True)
        if name == "q02_monthly":
            rows = sorted(rows, key=lambda r: r["month"])
        if name == "q10_cancellations":
            rows = sorted(rows, key=lambda r: r["month"])
        if name == "q14_delay_monthly":
            rows = sorted(rows, key=lambda r: r["month"])
        payload[section] = rows
    return payload


def engine_label() -> str:
    marker = RESULTS_DIR / "_engine.txt"
    if not marker.exists():
        return "unknown"
    return marker.read_text(encoding="utf-8").strip()


def period_label(monthly: list[dict]) -> str:
    if not monthly:
        return "unknown"
    months = sorted(r["month"] for r in monthly)
    return f"{months[0]} to {months[-1]}"


def count_lines(path: Path) -> int:
    with path.open("rb") as handle:
        return sum(1 for _ in handle)


def build_sqlite() -> None:
    PROCESSED.mkdir(parents=True, exist_ok=True)
    db_path = PROCESSED / "analytics.db"
    if db_path.exists():
        db_path.unlink()
    con = sqlite3.connect(db_path)
    con.execute(
        """
        CREATE TABLE bookings (
            pnr TEXT, train_number TEXT, train_name TEXT, train_type TEXT,
            zone TEXT, travel_date TEXT, booking_date TEXT,
            from_station_code TEXT, from_station_name TEXT,
            to_station_code TEXT, to_station_name TEXT, distance_km INTEGER,
            travel_class TEXT, quota TEXT, booking_status TEXT,
            current_status TEXT, waitlist_position INTEGER, fare REAL,
            refund_amount REAL, payment_mode TEXT, channel TEXT,
            passenger_age INTEGER, passenger_gender TEXT, concession INTEGER,
            cancellation_flag INTEGER, cancellation_reason TEXT,
            delay_minutes INTEGER, travel_month TEXT
        )
        """
    )
    insert = (
        f"INSERT INTO bookings ({', '.join(BOOKING_COLUMNS)}) "
        f"VALUES ({', '.join(['?'] * len(BOOKING_COLUMNS))})"
    )
    batch: list[tuple] = []

    def flush() -> None:
        if batch:
            con.executemany(insert, batch)
            batch.clear()

    with (RAW / "bookings.csv").open("r", encoding="utf-8", newline="") as handle:
        header = handle.readline().rstrip("\r\n").split(",")
        index = {name: header.index(name) for name in BOOKING_COLUMNS}
        for line in handle:
            parts = line.rstrip("\r\n").split(",")
            if len(parts) < len(header):
                continue
            batch.append(tuple(parts[index[name]] for name in BOOKING_COLUMNS))
            if len(batch) >= 2000:
                flush()
    flush()
    for column in ("travel_date", "train_number", "travel_class", "pnr"):
        con.execute(f"CREATE INDEX idx_bookings_{column} ON bookings({column})")
    con.commit()
    con.close()

    # The site reads data/processed/analytics.db; keep a copy beside the JSON
    # so the folder can be deployed on its own.
    SITE_DATA.mkdir(parents=True, exist_ok=True)
    site_db = SITE_DATA / "analytics.db"
    if site_db.exists():
        site_db.unlink()
    site_db.write_bytes(db_path.read_bytes())


def build_sample() -> None:
    con = sqlite3.connect(PROCESSED / "analytics.db")
    con.row_factory = sqlite3.Row
    total = con.execute("SELECT COUNT(*) FROM bookings").fetchone()[0]
    rng = random.Random(42)
    wanted = min(SAMPLE_SIZE, total)
    picks = sorted(rng.sample(range(1, total + 1), wanted))
    rows = []
    for rowid in picks:
        row = con.execute(
            f"SELECT {', '.join(BOOKING_COLUMNS)} FROM bookings WHERE rowid = ?",
            (rowid,),
        ).fetchone()
        if row is not None:
            rows.append(dict(row))
    con.close()
    (SITE_DATA / "bookings_sample.json").write_text(
        json.dumps(rows, ensure_ascii=False, separators=(",", ":")),
        encoding="utf-8",
    )


def main() -> int:
    if not (RAW / "bookings.csv").exists():
        print("data/raw/bookings.csv is missing. Run the data pipeline first.")
        return 1
    results = load_results()
    analytics = build_analytics(results)

    analytics["meta"]["trains"] = count_lines(RAW / "trains.csv") - 1
    analytics["meta"]["stations"] = count_lines(RAW / "stations.csv") - 1

    SITE_DATA.mkdir(parents=True, exist_ok=True)
    out = SITE_DATA / "analytics.json"
    out.write_text(json.dumps(analytics, ensure_ascii=False, indent=1), encoding="utf-8")

    build_sqlite()
    build_sample()

    for name, columns in RESULTS.items():
        print(f"{name:24s} {len(results[name]):6d} rows  {len(columns)} cols")
    print(f"kpis: {json.dumps(analytics['kpis'], ensure_ascii=False)}")
    print(f"wrote {out}")
    print(f"wrote {PROCESSED / 'analytics.db'}")
    print(f"wrote {SITE_DATA / 'bookings_sample.json'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
