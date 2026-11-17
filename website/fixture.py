"""Deterministic development fixture for the website.

The fixture is used only when website/data/analytics.json is absent. Its
analytics payload carries meta.engine = "fixture" so every page can label
the data clearly. Generated rows use the same field names as the SQLite
bookings table, which also makes the explorer sample file useful offline.
"""

from __future__ import annotations

import json
import random
from datetime import date, datetime, timedelta
from pathlib import Path

SEED = 42
SAMPLE_SIZE = 5000
START_DATE = date(2025, 1, 1)
LAST_BOOKING_DATE = date(2026, 10, 31)
LAST_TRAVEL_DATE = date(2026, 12, 31)

STATIONS = {
    "NDLS": ("NEW DELHI", "NR"),
    "BCT": ("MUMBAI CENTRAL", "WR"),
    "CSTM": ("MUMBAI CSMT", "CR"),
    "HWH": ("HOWRAH JN", "ER"),
    "MAS": ("MGR CHENNAI CENTRAL", "SR"),
    "SBC": ("KSR BENGALURU", "SWR"),
    "SC": ("SECUNDERABAD JN", "SCR"),
    "PUNE": ("PUNE JN", "CR"),
    "ADI": ("AHMEDABAD JN", "WR"),
    "JP": ("JAIPUR JN", "NWR"),
    "AII": ("AJMER JN", "NWR"),
    "LKO": ("LUCKNOW JN", "NR"),
    "BPL": ("BHOPAL JN", "WCR"),
    "NGP": ("NAGPUR JN", "CR"),
    "PNBE": ("PATNA JN", "ECR"),
    "GAYA": ("GAYA JN", "ECR"),
    "BSB": ("VARANASI JN", "NER"),
    "PRYJ": ("PRAYAGRAJ JN", "NCR"),
    "AGC": ("AGRA CANTT", "NCR"),
    "JAT": ("JAMMU TAWI", "NR"),
    "ASR": ("AMRITSAR JN", "NR"),
    "CDG": ("CHANDIGARH", "NR"),
    "DDN": ("DEHRADUN", "NR"),
    "GHY": ("GUWAHATI", "NFR"),
    "BBS": ("BHUBANESWAR", "ECoR"),
    "VSKP": ("VISAKHAPATNAM", "ECoR"),
    "TPTY": ("TIRUPATI", "SCR"),
    "ERS": ("ERNAKULAM TOWN", "SR"),
    "TVC": ("THIRUVANANTHAPURAM CENTRAL", "SR"),
    "MAQ": ("MANGALURU CENTRAL", "SR"),
    "MAO": ("MADGAON", "KR"),
    "ST": ("SURAT", "WR"),
    "KOTA": ("KOTA JN", "WCR"),
    "JBP": ("JABALPUR", "WCR"),
    "RNC": ("RANCHI", "SER"),
    "TATA": ("TATANAGAR JN", "SER"),
    "KGP": ("KHARAGPUR JN", "SER"),
    "BZA": ("VIJAYAWADA JN", "SCR"),
}

# number, name, type, zone, origin, destination, distance in km
TRAINS = [
    ("12301", "HOWRAH RAJDHANI EXPRESS", "Raj", "ER", "HWH", "NDLS", 1451),
    ("12951", "MUMBAI RAJDHANI EXPRESS", "Raj", "WR", "BCT", "NDLS", 1384),
    ("12627", "KARNATAKA EXPRESS", "SF", "SWR", "SBC", "NDLS", 2444),
    ("12723", "TELANGANA EXPRESS", "SF", "SCR", "SC", "NDLS", 1665),
    ("12621", "TAMIL NADU EXPRESS", "SF", "SR", "MAS", "NDLS", 2175),
    ("12002", "BHOPAL SHATABDI", "Sht", "NCR", "BPL", "NDLS", 702),
    ("12009", "SHATABDI EXPRESS", "Sht", "WR", "BCT", "ADI", 493),
    ("12259", "SEALDAH DURONTO", "Dur", "ER", "HWH", "PNBE", 530),
    ("12615", "GRAND TRUNK EXPRESS", "SF", "SR", "MAS", "NDLS", 2175),
    ("12841", "COROMANDEL EXPRESS", "SF", "SER", "HWH", "MAS", 1662),
    ("12839", "HOWRAH CHENNAI MAIL", "Mail", "SER", "HWH", "MAS", 1662),
    ("12303", "POORVA EXPRESS", "SF", "ER", "HWH", "NDLS", 1451),
    ("12424", "DIBRUGARH RAJDHANI", "Raj", "NFR", "GHY", "NDLS", 1900),
    ("12423", "DIBRUGARH RAJDHANI", "Raj", "NFR", "NDLS", "GHY", 1900),
    ("12985", "JAIPUR DOUBLE DECKER", "SF", "NWR", "JP", "NDLS", 308),
    ("12413", "AJMER INTERCITY", "SF", "NWR", "AII", "NDLS", 444),
    ("12007", "MYSURU SHATABDI", "Sht", "SWR", "MAS", "SBC", 500),
    ("12625", "KERALA EXPRESS", "SF", "SR", "TVC", "NDLS", 3050),
    ("12617", "MANGALA LAKSHADWEEP", "SF", "SR", "MAQ", "NDLS", 2600),
    ("12155", "BHOPAL EXPRESS", "SF", "WCR", "BPL", "NDLS", 702),
    ("12471", "SWARAJ EXPRESS", "SF", "NR", "ASR", "BCT", 1900),
    ("12925", "PASCHIM EXPRESS", "SF", "WR", "ASR", "BCT", 1900),
    ("12345", "SAMPARK KRANTI", "SF", "NR", "NDLS", "ASR", 448),
    ("12295", "SANGHAMITRA EXPRESS", "SF", "ECR", "PNBE", "SBC", 2400),
    ("12559", "SHIV GANGA EXPRESS", "SF", "NER", "BSB", "NDLS", 760),
    ("12451", "SHAAN E BHUJPUR", "SF", "NCR", "PRYJ", "NDLS", 635),
    ("12137", "PUNJAB MAIL", "Mail", "CR", "CSTM", "NDLS", 1540),
    ("12138", "PUNJAB MAIL", "Mail", "CR", "NDLS", "CSTM", 1540),
    ("12801", "PURUSHOTTAM EXPRESS", "SF", "ECoR", "BBS", "NDLS", 1900),
    ("12703", "FALAKNUMA EXPRESS", "SF", "SCR", "SC", "HWH", 1500),
    ("22691", "RAJDHANI EXPRESS", "Raj", "SWR", "SBC", "NDLS", 2444),
    ("22692", "RAJDHANI EXPRESS", "Raj", "SWR", "NDLS", "SBC", 2444),
    ("11077", "JHELUM EXPRESS", "Exp", "CR", "PUNE", "JAT", 1900),
    ("11078", "JHELUM EXPRESS", "Exp", "CR", "JAT", "PUNE", 1900),
    ("12163", "DADAR CHENNAI EXPRESS", "SF", "CR", "CSTM", "MAS", 1280),
    ("12245", "HOWRAH DURONTO", "Dur", "ER", "HWH", "SBC", 1950),
]

CLASS_RATE = {"SL": 0.55, "3A": 1.45, "2A": 2.05, "1A": 3.45, "CC": 1.25, "2S": 0.35}
CLASS_MIN = {"SL": 150, "3A": 400, "2A": 550, "1A": 850, "CC": 250, "2S": 100}
CLASS_ORDER = ["SL", "3A", "2A", "1A", "CC", "2S"]
CLASS_WEIGHT = [("SL", 38), ("3A", 30), ("2A", 12), ("CC", 9), ("2S", 7), ("1A", 4)]
QUOTA_ORDER = ["GN", "TQ", "LD", "SS", "RS", "PT"]
QUOTA_WEIGHT = [("GN", 78), ("TQ", 6), ("LD", 5), ("SS", 4), ("RS", 3), ("PT", 4)]
PAYMENT_ORDER = ["UPI", "Card", "NetBanking", "Wallet", "Cash"]
PAYMENT_WEIGHT = [("UPI", 55), ("Card", 18), ("NetBanking", 12), ("Wallet", 8), ("Cash", 7)]
CHANNEL_ORDER = ["App", "Web", "Counter", "Agent"]
CHANNEL_WEIGHT = [("App", 58), ("Web", 27), ("Counter", 11), ("Agent", 4)]
REASONS = [
    "Passenger plan change",
    "Medical emergency",
    "Train cancelled",
    "Schedule change",
    "Duplicate booking",
    "Other",
]

SECTION_KEYS = (
    "monthly", "routes", "trains", "class_revenue", "quota_revenue",
    "payments", "channels", "status", "cancellations", "cancel_reasons",
    "delay_by_type", "delay_by_zone", "delay_monthly",
)

def _pick(rng: random.Random, pairs):
    """Pick a value from a list of (value, weight) pairs."""
    total = sum(weight for _, weight in pairs)
    roll = rng.uniform(0, total)
    upto = 0.0
    for value, weight in pairs:
        upto += weight
        if roll <= upto:
            return value
    return pairs[-1][0]


def _round(value, digits=2):
    return round(float(value), digits)


def _mean(total, count):
    return _round(total / count, 2) if count else 0.0


def _rate(part, whole):
    return _round(part * 100.0 / whole, 2) if whole else 0.0


def _trip_delay(rng: random.Random, cache: dict, train_number: str, travel: date) -> int:
    key = (train_number, travel.isoformat())
    if key not in cache:
        if rng.random() < 0.45:
            cache[key] = int(min(600, rng.expovariate(1 / 42.0) + 1))
        else:
            cache[key] = 0
    return cache[key]


def build_rows(count: int = SAMPLE_SIZE, seed: int = SEED):
    """Return passenger level fixture rows with SQLite column names."""
    rng = random.Random(seed)
    rows = []
    delay_cache = {}
    pnr_value = 4200000000

    while len(rows) < count:
        number, name, train_type, zone, origin, destination, distance = rng.choice(TRAINS)
        party_size = _pick(rng, [(1, 40), (2, 25), (3, 15), (4, 10), (5, 6), (6, 4)])
        party_size = min(party_size, count - len(rows))
        pnr = str(pnr_value)
        pnr_value += rng.randint(1, 4)

        booking_date = START_DATE + timedelta(
            days=rng.randint(0, (LAST_BOOKING_DATE - START_DATE).days)
        )
        latest_travel = min(booking_date + timedelta(days=120), LAST_TRAVEL_DATE)
        travel_date = booking_date + timedelta(
            days=rng.randint(1, max(1, (latest_travel - booking_date).days))
        )

        travel_class = _pick(rng, CLASS_WEIGHT)
        quota = _pick(rng, QUOTA_WEIGHT)
        booking_status = _pick(rng, [("CNF", 70), ("RAC", 12), ("WL", 18)])
        if booking_status == "CNF":
            current_status = "CAN" if rng.random() < 0.06 else "CNF"
        elif booking_status == "RAC":
            current_status = _pick(rng, [("CNF", 60), ("RAC", 28), ("CAN", 12)])
        else:
            current_status = _pick(rng, [("CNF", 29), ("RAC", 15), ("WL", 44), ("CAN", 12)])

        waitlist_position = 0 if booking_status == "CNF" else rng.randint(1, 200)
        demand = rng.uniform(0.85, 1.35)
        base_fare = max(
            CLASS_MIN[travel_class],
            distance * CLASS_RATE[travel_class] + rng.randint(40, 60),
        ) * demand
        fare = max(5, int(round(base_fare / 5.0)) * 5)

        payment_mode = _pick(rng, PAYMENT_WEIGHT)
        channel = _pick(rng, CHANNEL_WEIGHT)
        delay_minutes = _trip_delay(rng, delay_cache, number, travel_date)

        for _ in range(party_size):
            cancelled = current_status == "CAN"
            rows.append({
                "pnr": pnr,
                "train_number": number,
                "train_name": name,
                "train_type": train_type,
                "zone": zone,
                "travel_date": travel_date.isoformat(),
                "booking_date": booking_date.isoformat(),
                "from_station_code": origin,
                "from_station_name": STATIONS[origin][0],
                "to_station_code": destination,
                "to_station_name": STATIONS[destination][0],
                "distance_km": distance,
                "travel_class": travel_class,
                "quota": quota,
                "booking_status": booking_status,
                "current_status": current_status,
                "waitlist_position": waitlist_position,
                "fare": fare,
                "refund_amount": _round(fare * rng.uniform(0.6, 1.0), 2) if cancelled else 0.0,
                "payment_mode": payment_mode,
                "channel": channel,
                "passenger_age": rng.randint(1, 85),
                "passenger_gender": _pick(rng, [("M", 52), ("F", 45), ("O", 3)]),
                "concession": 1 if rng.random() < 0.05 else 0,
                "cancellation_flag": 1 if cancelled else 0,
                "cancellation_reason": _pick(rng, [(reason, 1) for reason in REASONS])
                if cancelled else "",
                "delay_minutes": delay_minutes,
                "travel_month": travel_date.isoformat()[:7],
            })

    return rows


def build_analytics(rows):
    """Aggregate fixture rows into the analytics.json structure."""
    total_rows = len(rows)
    pnrs = {row["pnr"] for row in rows}
    gross_revenue = sum(row["fare"] for row in rows)
    refunds = sum(row["refund_amount"] for row in rows)

    monthly = {}
    routes = {}
    trains = {}
    classes = {}
    quotas = {}
    payments = {}
    channels = {}
    status_by_class = {}
    cancellations = {}
    reasons = {}
    delay_type = {}
    delay_zone = {}
    delay_month = {}
    months = set()

    for row in rows:
        month = row["travel_month"]
        months.add(month)
        cancelled = row["current_status"] == "CAN"

        item = monthly.setdefault(month, {
            "pnrs": set(), "passengers": 0, "revenue": 0.0,
            "cancellations": 0, "waitlist": 0, "delay": 0.0,
        })
        item["pnrs"].add(row["pnr"])
        item["passengers"] += 1
        item["revenue"] += row["fare"]
        item["cancellations"] += 1 if cancelled else 0
        item["waitlist"] += 1 if row["current_status"] == "WL" else 0
        item["delay"] += row["delay_minutes"]

        key = (row["from_station_code"], row["to_station_code"])
        item = routes.setdefault(key, {
            "pnrs": set(), "passengers": 0, "revenue": 0.0, "delay": 0.0,
            "from_name": row["from_station_name"], "to_name": row["to_station_name"],
        })
        item["pnrs"].add(row["pnr"])
        item["passengers"] += 1
        item["revenue"] += row["fare"]
        item["delay"] += row["delay_minutes"]

        item = trains.setdefault(row["train_number"], {
            "train_name": row["train_name"], "train_type": row["train_type"],
            "pnrs": set(), "passengers": 0, "revenue": 0.0, "delay": 0.0, "cancelled": 0,
        })
        item["pnrs"].add(row["pnr"])
        item["passengers"] += 1
        item["revenue"] += row["fare"]
        item["delay"] += row["delay_minutes"]
        item["cancelled"] += 1 if cancelled else 0

        item = classes.setdefault(row["travel_class"], {
            "pnrs": set(), "passengers": 0, "revenue": 0.0,
        })
        item["pnrs"].add(row["pnr"])
        item["passengers"] += 1
        item["revenue"] += row["fare"]

        item = quotas.setdefault(row["quota"], {
            "pnrs": set(), "passengers": 0, "revenue": 0.0,
        })
        item["pnrs"].add(row["pnr"])
        item["passengers"] += 1
        item["revenue"] += row["fare"]

        item = payments.setdefault(row["payment_mode"], {"pnrs": set(), "revenue": 0.0})
        item["pnrs"].add(row["pnr"])
        item["revenue"] += row["fare"]

        item = channels.setdefault(row["channel"], {"pnrs": set(), "revenue": 0.0})
        item["pnrs"].add(row["pnr"])
        item["revenue"] += row["fare"]

        item = status_by_class.setdefault(row["travel_class"], {
            "bookings": 0, "confirmed": 0, "rac": 0, "waitlist": 0,
            "cancelled": 0, "wait_total": 0, "wait_count": 0,
        })
        item["bookings"] += 1
        status = row["current_status"]
        if status == "CNF":
            item["confirmed"] += 1
        elif status == "RAC":
            item["rac"] += 1
        elif status == "WL":
            item["waitlist"] += 1
        else:
            item["cancelled"] += 1
        if row["waitlist_position"] > 0:
            item["wait_total"] += row["waitlist_position"]
            item["wait_count"] += 1

        if cancelled:
            item = cancellations.setdefault(month, {"cancellations": 0, "refund": 0.0})
            item["cancellations"] += 1
            item["refund"] += row["refund_amount"]
            reasons[row["cancellation_reason"]] = reasons.get(row["cancellation_reason"], 0) + 1

        item = delay_type.setdefault(row["train_type"], {
            "pnrs": set(), "rows": 0, "delay": 0.0, "late": 0,
        })
        item["pnrs"].add(row["pnr"])
        item["rows"] += 1
        item["delay"] += row["delay_minutes"]
        item["late"] += 1 if row["delay_minutes"] > 15 else 0

        item = delay_zone.setdefault(row["zone"], {
            "pnrs": set(), "rows": 0, "delay": 0.0, "late": 0,
        })
        item["pnrs"].add(row["pnr"])
        item["rows"] += 1
        item["delay"] += row["delay_minutes"]
        item["late"] += 1 if row["delay_minutes"] > 15 else 0

        item = delay_month.setdefault(month, {
            "pnrs": set(), "rows": 0, "delay": 0.0, "late": 0,
        })
        item["pnrs"].add(row["pnr"])
        item["rows"] += 1
        item["delay"] += row["delay_minutes"]
        item["late"] += 1 if row["delay_minutes"] > 15 else 0

    monthly_out = [
        {
            "month": month,
            "bookings": len(monthly[month]["pnrs"]),
            "passengers": monthly[month]["passengers"],
            "revenue": _round(monthly[month]["revenue"]),
            "cancellations": monthly[month]["cancellations"],
            "waitlist": monthly[month]["waitlist"],
            "avg_delay": _mean(monthly[month]["delay"], monthly[month]["passengers"]),
        }
        for month in sorted(monthly)
    ]

    routes_out = []
    for (from_code, to_code), item in routes.items():
        routes_out.append({
            "route": f"{from_code}-{to_code}",
            "from_station": item["from_name"],
            "to_station": item["to_name"],
            "bookings": len(item["pnrs"]),
            "passengers": item["passengers"],
            "revenue": _round(item["revenue"]),
            "avg_fare": _mean(item["revenue"], item["passengers"]),
            "avg_delay": _mean(item["delay"], item["passengers"]),
        })
    routes_out.sort(key=lambda row: (row["bookings"], row["revenue"]), reverse=True)

    trains_out = []
    for number, item in trains.items():
        trains_out.append({
            "train_number": number,
            "train_name": item["train_name"],
            "train_type": item["train_type"],
            "bookings": len(item["pnrs"]),
            "passengers": item["passengers"],
            "revenue": _round(item["revenue"]),
            "avg_delay": _mean(item["delay"], item["passengers"]),
            "cancel_rate": _rate(item["cancelled"], item["passengers"]),
        })
    trains_out.sort(key=lambda row: row["revenue"], reverse=True)

    def ordered(source, order):
        return [value for value in order if value in source]

    class_revenue = [
        {
            "travel_class": travel_class,
            "bookings": len(classes[travel_class]["pnrs"]),
            "passengers": classes[travel_class]["passengers"],
            "revenue": _round(classes[travel_class]["revenue"]),
            "avg_fare": _mean(classes[travel_class]["revenue"], classes[travel_class]["passengers"]),
            "share_pct": _rate(classes[travel_class]["revenue"], gross_revenue),
        }
        for travel_class in ordered(classes, CLASS_ORDER)
    ]
    quota_revenue = [
        {
            "quota": quota,
            "bookings": len(quotas[quota]["pnrs"]),
            "passengers": quotas[quota]["passengers"],
            "revenue": _round(quotas[quota]["revenue"]),
            "avg_fare": _mean(quotas[quota]["revenue"], quotas[quota]["passengers"]),
        }
        for quota in ordered(quotas, QUOTA_ORDER)
    ]
    payment_out = [
        {
            "payment_mode": mode,
            "bookings": len(payments[mode]["pnrs"]),
            "revenue": _round(payments[mode]["revenue"]),
        }
        for mode in ordered(payments, PAYMENT_ORDER)
    ]
    channel_out = [
        {
            "channel": channel,
            "bookings": len(channels[channel]["pnrs"]),
            "revenue": _round(channels[channel]["revenue"]),
        }
        for channel in ordered(channels, CHANNEL_ORDER)
    ]
    status_out = [
        {
            "travel_class": travel_class,
            "bookings": status_by_class[travel_class]["bookings"],
            "confirmed": status_by_class[travel_class]["confirmed"],
            "rac": status_by_class[travel_class]["rac"],
            "waitlist": status_by_class[travel_class]["waitlist"],
            "cancelled": status_by_class[travel_class]["cancelled"],
            "confirmation_rate": _rate(
                status_by_class[travel_class]["confirmed"],
                status_by_class[travel_class]["bookings"],
            ),
            "avg_waitlist_position": _mean(
                status_by_class[travel_class]["wait_total"],
                status_by_class[travel_class]["wait_count"],
            ),
        }
        for travel_class in ordered(status_by_class, CLASS_ORDER)
    ]
    cancellations_out = [
        {
            "month": item["month"],
            "cancellations": cancellations[item["month"]]["cancellations"],
            "cancellation_rate": _rate(
                cancellations[item["month"]]["cancellations"],
                item["passengers"],
            ),
            "refund_amount": _round(cancellations[item["month"]]["refund"]),
        }
        for item in monthly_out
        if item["month"] in cancellations
    ]
    reason_out = [
        {"reason": reason, "count": count}
        for reason, count in sorted(reasons.items(), key=lambda pair: pair[1], reverse=True)
    ]

    def delay_rows(source, label):
        result = [
            {
                label: key,
                "bookings": len(item["pnrs"]),
                "avg_delay": _mean(item["delay"], item["rows"]),
                "late_pct": _rate(item["late"], item["rows"]),
            }
            for key, item in source.items()
        ]
        result.sort(key=lambda row: row["avg_delay"], reverse=True)
        return result

    delay_monthly = [
        {
            "month": month,
            "bookings": len(item["pnrs"]),
            "avg_delay": _mean(item["delay"], item["rows"]),
            "late_pct": _rate(item["late"], item["rows"]),
        }
        for month, item in sorted(delay_month.items())
    ]

    kpis = {
        "total_bookings": len(pnrs),
        "total_passengers": total_rows,
        "gross_revenue": _round(gross_revenue),
        "refunds": _round(refunds),
        "net_revenue": _round(gross_revenue - refunds),
        "avg_fare": _mean(gross_revenue, total_rows),
        "cancellation_rate": _rate(
            sum(1 for row in rows if row["current_status"] == "CAN"), total_rows
        ),
        "waitlist_share": _rate(
            sum(1 for row in rows if row["current_status"] == "WL"), total_rows
        ),
        "avg_delay_minutes": _mean(
            sum(row["delay_minutes"] for row in rows), total_rows
        ),
        "avg_distance_km": _mean(
            sum(row["distance_km"] for row in rows), total_rows
        ),
        "confirmed_share": _rate(
            sum(1 for row in rows if row["current_status"] == "CNF"), total_rows
        ),
    }

    return {
        "meta": {
            "generated_at": datetime.now().replace(microsecond=0).isoformat(),
            "engine": "fixture",
            "bookings": total_rows,
            "unique_pnrs": len(pnrs),
            "trains": len({row["train_number"] for row in rows}),
            "stations": len({
                row["from_station_code"] for row in rows
            } | {row["to_station_code"] for row in rows}),
            "period": f"{min(months)} to {max(months)}" if months else "",
        },
        "kpis": kpis,
        "monthly": monthly_out,
        "routes": routes_out[:40],
        "trains": trains_out[:40],
        "class_revenue": class_revenue,
        "quota_revenue": quota_revenue,
        "payments": payment_out,
        "channels": channel_out,
        "status": status_out,
        "cancellations": cancellations_out,
        "cancel_reasons": reason_out,
        "delay_by_type": delay_rows(delay_type, "train_type"),
        "delay_by_zone": delay_rows(delay_zone, "zone"),
        "delay_monthly": delay_monthly,
    }


def empty_analytics():
    """Return a complete analytics object with neutral values."""
    return {
        "meta": {
            "generated_at": "",
            "engine": "",
            "bookings": 0,
            "unique_pnrs": 0,
            "trains": 0,
            "stations": 0,
            "period": "",
        },
        "kpis": {
            "total_bookings": 0,
            "total_passengers": 0,
            "gross_revenue": 0.0,
            "refunds": 0.0,
            "net_revenue": 0.0,
            "avg_fare": 0.0,
            "cancellation_rate": 0.0,
            "waitlist_share": 0.0,
            "avg_delay_minutes": 0.0,
            "avg_distance_km": 0.0,
            "confirmed_share": 0.0,
        },
        **{key: [] for key in SECTION_KEYS},
    }


def with_defaults(payload):
    """Fill missing analytics sections so templates never see undefined keys."""
    data = empty_analytics()
    if not isinstance(payload, dict):
        return data
    for key in ("meta", "kpis"):
        value = payload.get(key)
        if isinstance(value, dict):
            data[key].update(value)
    for key in SECTION_KEYS:
        value = payload.get(key)
        if isinstance(value, list):
            data[key] = value
    return data


_fixture_cache = None


def get_fixture_analytics():
    global _fixture_cache
    if _fixture_cache is None:
        _fixture_cache = build_analytics(build_rows())
    return _fixture_cache


def ensure_sample(path, count: int = SAMPLE_SIZE):
    """Create the explorer sample file when it is missing."""
    path = Path(path)
    if path.is_file() and path.stat().st_size > 2:
        return path
    path.parent.mkdir(parents=True, exist_ok=True)
    rows = build_rows(count)
    path.write_text(
        json.dumps(rows, separators=(",", ":")),
        encoding="utf-8",
    )
    return path


