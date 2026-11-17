"""Build data/raw/stations.csv, trains.csv and train_stops.csv from the
DataMeet reference JSON in data/reference/.

Column order follows docs/CONTRACT.md exactly. Values are sanitised so the
output can be loaded by Hive and DuckDB as unquoted comma delimited text.
"""

import csv
import json
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
REFERENCE_DIR = BASE_DIR / "data" / "reference"
RAW_DIR = BASE_DIR / "data" / "raw"

STATION_COLUMNS = ["station_code", "station_name", "state", "zone", "latitude", "longitude"]
TRAIN_COLUMNS = [
    "train_number",
    "train_name",
    "train_type",
    "zone",
    "source_code",
    "destination_code",
    "distance_km",
    "duration_min",
    "has_sleeper",
    "has_3ac",
    "has_2ac",
    "has_1ac",
    "has_cc",
]
STOP_COLUMNS = [
    "train_number",
    "stop_seq",
    "station_code",
    "station_name",
    "arrival_time",
    "departure_time",
    "day",
]

RESERVED_KEYS = ["sleeper", "third_ac", "second_ac", "first_ac", "chair_car"]
FLAG_COLUMNS = ["has_sleeper", "has_3ac", "has_2ac", "has_1ac", "has_cc"]


def clean(value):
    """Make a value safe for an unquoted comma delimited file."""
    if value is None:
        return ""
    text = str(value)
    text = text.replace("\t", " ").replace("\n", " ").replace("\r", " ").replace(",", " ")
    return " ".join(text.split())


def zone_text(value):
    """Normalise the source zone marker for unknown zones to UNK."""
    text = clean(value)
    return text if text and text != "?" else "UNK"


def load_json(name):
    path = REFERENCE_DIR / name
    if not path.exists():
        raise SystemExit("ERROR: missing %s, run scripts/download_reference.py first" % path)
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def coordinate_text(value):
    if value is None or isinstance(value, bool):
        return ""
    try:
        number = float(value)
    except (TypeError, ValueError):
        return ""
    return ("%.6f" % number).rstrip("0").rstrip(".")


def build_stations():
    data = load_json("stations.json")
    rows = []
    seen = set()
    skipped_prefix = 0
    skipped_duplicate = 0

    for feature in data.get("features", []):
        props = feature.get("properties") or {}
        code = clean(props.get("code"))
        if not code:
            continue
        if code.startswith("XX-") or code.startswith("YY-"):
            skipped_prefix += 1
            continue
        if code in seen:
            skipped_duplicate += 1
            continue
        seen.add(code)

        latitude = ""
        longitude = ""
        geometry = feature.get("geometry") or {}
        coordinates = geometry.get("coordinates") if isinstance(geometry, dict) else None
        if isinstance(coordinates, (list, tuple)) and len(coordinates) >= 2:
            longitude = coordinate_text(coordinates[0])
            latitude = coordinate_text(coordinates[1])

        rows.append([
            code,
            clean(props.get("name")),
            clean(props.get("state")) or "UNKNOWN",
            zone_text(props.get("zone")),
            latitude,
            longitude,
        ])

    with (RAW_DIR / "stations.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle, lineterminator="\n")
        writer.writerow(STATION_COLUMNS)
        writer.writerows(rows)

    if skipped_prefix or skipped_duplicate:
        print("stations: skipped %d XX-/YY- codes and %d duplicate codes"
              % (skipped_prefix, skipped_duplicate))
    return rows


def build_trains_and_stops():
    trains_data = load_json("trains.json")
    schedules_data = load_json("schedules.json")

    candidates = []
    reserved_numbers = set()
    for feature in trains_data.get("features", []):
        props = feature.get("properties") or {}
        number = clean(props.get("number"))
        if not number:
            continue
        flags = {key: 1 if props.get(key) else 0 for key in RESERVED_KEYS}
        if not any(flags.values()):
            continue
        if number in reserved_numbers:
            continue

        distance = props.get("distance")
        duration_h = props.get("duration_h")
        duration_m = props.get("duration_m")
        if duration_h is None or duration_m is None:
            duration_min = ""
        else:
            try:
                duration_min = int(duration_h) * 60 + int(duration_m)
            except (TypeError, ValueError):
                duration_min = ""

        candidates.append({
            "train_number": number,
            "train_name": clean(props.get("name")),
            "train_type": clean(props.get("type")) or "OTH",
            "zone": zone_text(props.get("zone")),
            "source_code": clean(props.get("from_station_code")),
            "destination_code": clean(props.get("to_station_code")),
            "distance_km": "" if distance is None else int(distance),
            "duration_min": duration_min,
            "has_sleeper": flags["sleeper"],
            "has_3ac": flags["third_ac"],
            "has_2ac": flags["second_ac"],
            "has_1ac": flags["first_ac"],
            "has_cc": flags["chair_car"],
        })
        reserved_numbers.add(number)

    # Group schedule records in file order, which is also the stop order.
    stops_by_train = {}
    for record in schedules_data:
        number = clean(record.get("train_number"))
        if number in reserved_numbers:
            stops_by_train.setdefault(number, []).append(record)

    train_rows = []
    stop_rows = []
    dropped_short = 0

    for train in candidates:
        number = train["train_number"]
        records = stops_by_train.get(number, [])
        if len(records) < 2:
            dropped_short += 1
            continue

        train_rows.append([train[column] for column in TRAIN_COLUMNS])

        for seq, record in enumerate(records, start=1):
            arrival = clean(record.get("arrival"))
            departure = clean(record.get("departure"))
            if arrival.lower() == "none":
                arrival = ""
            if departure.lower() == "none":
                departure = ""
            day = record.get("day")
            stop_rows.append([
                number,
                seq,
                clean(record.get("station_code")),
                clean(record.get("station_name")),
                arrival,
                departure,
                "" if day is None else int(day),
            ])

    with (RAW_DIR / "trains.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle, lineterminator="\n")
        writer.writerow(TRAIN_COLUMNS)
        writer.writerows(train_rows)

    with (RAW_DIR / "train_stops.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle, lineterminator="\n")
        writer.writerow(STOP_COLUMNS)
        writer.writerows(stop_rows)

    if dropped_short:
        print("trains: dropped %d reserved trains with fewer than 2 stops" % dropped_short)
    return train_rows, stop_rows


def first_rows(path, count=3):
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.reader(handle)
        rows = []
        for index, row in enumerate(reader):
            if index > count:
                break
            rows.append(row)
        return rows


def main():
    RAW_DIR.mkdir(parents=True, exist_ok=True)

    stations = build_stations()
    trains, stops = build_trains_and_stops()

    print("stations.csv: %d rows" % len(stations))
    print("trains.csv: %d rows" % len(trains))
    print("train_stops.csv: %d rows" % len(stops))

    for name, count in [
        ("stations.csv", len(stations)),
        ("trains.csv", len(trains)),
        ("train_stops.csv", len(stops)),
    ]:
        print("sample rows from %s:" % name)
        for row in first_rows(RAW_DIR / name, 3):
            print("  " + ",".join(row))

    if not (2200 <= len(trains) <= 2400):
        print("ASSERTION FAILED: trains.csv has %d rows, expected roughly 2200 to 2400" % len(trains))
        return 1
    if len(stops) <= 300000:
        print("ASSERTION FAILED: train_stops.csv has %d rows, expected more than 300000" % len(stops))
        return 1
    if len(stations) <= 0:
        print("ASSERTION FAILED: stations.csv is empty")
        return 1

    print("build_reference: all assertions passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
