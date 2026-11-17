"""Generate data/raw/bookings.csv: 150000 passenger rows, seeded with 42.

The file follows docs/CONTRACT.md exactly: 29 columns, no commas, tabs or
newlines inside fields, and a validation pass that checks every contract
rule before the script reports success.
"""

import calendar
import csv
import random
import sys
from datetime import date, timedelta
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
RAW_DIR = BASE_DIR / "data" / "raw"
TRAINS_CSV = RAW_DIR / "trains.csv"
STOPS_CSV = RAW_DIR / "train_stops.csv"
BOOKINGS_CSV = RAW_DIR / "bookings.csv"

COLUMNS = [
    "pnr",
    "passenger_seq",
    "train_number",
    "train_name",
    "train_type",
    "zone",
    "travel_date",
    "booking_date",
    "from_station_code",
    "from_station_name",
    "to_station_code",
    "to_station_name",
    "distance_km",
    "travel_class",
    "quota",
    "booking_status",
    "current_status",
    "waitlist_position",
    "fare",
    "refund_amount",
    "payment_mode",
    "channel",
    "passenger_age",
    "passenger_gender",
    "concession",
    "cancellation_flag",
    "cancellation_reason",
    "delay_minutes",
    "travel_month",
]

TARGET_ROWS = 150000
TARGET_PNRS = 88000
CANCEL_RATE = 0.09
BOOKING_STATUS_WEIGHTS = [("CNF", 70.0), ("RAC", 12.0), ("WL", 18.0)]

CLASS_ORDER = ["SL", "3A", "2A", "CC", "2S", "1A"]
CLASS_WEIGHTS = {"SL": 38.0, "3A": 30.0, "2A": 12.0, "CC": 9.0, "2S": 7.0, "1A": 4.0}
CLASS_RATE = {"SL": 0.55, "3A": 1.45, "2A": 2.05, "1A": 3.45, "CC": 1.25, "2S": 0.35}
CLASS_MIN_FARE = {"SL": 150, "3A": 400, "2A": 550, "1A": 850, "CC": 250, "2S": 100}

QUOTA_WEIGHTS = [("GN", 78.0), ("TQ", 6.0), ("LD", 5.0), ("SS", 4.0), ("RS", 3.0), ("PT", 4.0)]
PAYMENT_WEIGHTS = [("UPI", 55.0), ("Card", 18.0), ("NetBanking", 12.0), ("Wallet", 8.0), ("Cash", 7.0)]
CHANNEL_WEIGHTS = [("App", 58.0), ("Web", 27.0), ("Counter", 11.0), ("Agent", 4.0)]

CANCEL_REASONS = [
    ("Passenger plan change", 40.0),
    ("Medical emergency", 16.0),
    ("Train cancelled", 15.0),
    ("Schedule change", 10.0),
    ("Duplicate booking", 9.0),
    ("Other", 10.0),
]

DELAY_BASE = {
    "Raj": 6,
    "SF": 12,
    "Exp": 20,
    "Mail": 25,
    "Pass": 30,
    "DEMU": 8,
    "MEMU": 8,
    "Drnt": 10,
    "OTH": 18,
}
ZONE_FACTOR = {
    "NR": 1.10,
    "NWR": 1.15,
    "NER": 1.20,
    "NCR": 1.05,
    "WCR": 1.10,
    "WR": 1.05,
    "SR": 1.00,
    "SCR": 1.05,
    "SWR": 1.00,
    "CR": 1.05,
    "ER": 1.05,
    "SER": 1.10,
    "SECR": 1.10,
    "ECoR": 1.10,
    "ECR": 1.10,
    "NFR": 1.20,
    "KR": 1.00,
    "UNK": 1.00,
}

SEASON_WEIGHT = {
    1: 1.00,
    2: 1.00,
    3: 1.05,
    4: 1.00,
    5: 1.25,
    6: 1.25,
    7: 1.00,
    8: 1.00,
    9: 1.00,
    10: 1.15,
    11: 1.15,
    12: 1.25,
}

MIN_BOOKING = date(2024, 9, 1)
MAX_BOOKING = date(2026, 10, 31)
MIN_TRAVEL = date(2025, 1, 1)
MAX_TRAVEL = date(2026, 12, 31)

ZERO_DELAY_PROB = 0.535
MAX_DISTANCE = 4500


def load_trains():
    trains = {}
    with TRAINS_CSV.open("r", encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            number = row["train_number"]
            distance_text = row.get("distance_km", "").strip()
            try:
                distance = int(float(distance_text)) if distance_text else None
            except ValueError:
                distance = None
            trains[number] = {
                "train_number": number,
                "train_name": row["train_name"],
                "train_type": row["train_type"] or "OTH",
                "zone": row["zone"] or "UNK",
                "distance": distance,
                "has_sleeper": row["has_sleeper"] == "1",
                "has_3ac": row["has_3ac"] == "1",
                "has_2ac": row["has_2ac"] == "1",
                "has_1ac": row["has_1ac"] == "1",
                "has_cc": row["has_cc"] == "1",
            }
    return trains


def load_stops(valid_numbers):
    stops = {}
    with STOPS_CSV.open("r", encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            number = row["train_number"]
            if number not in valid_numbers:
                continue
            stops.setdefault(number, []).append(
                (row["station_code"], row["station_name"])
            )
    return stops


def allowed_classes(train):
    allowed = []
    weights = []
    checks = [
        ("SL", "has_sleeper"),
        ("3A", "has_3ac"),
        ("2A", "has_2ac"),
        ("1A", "has_1ac"),
        ("CC", "has_cc"),
        ("2S", None),
    ]
    for code, flag in checks:
        if flag is None or train[flag]:
            allowed.append(code)
            weights.append(CLASS_WEIGHTS[code])
    return allowed, weights


def weighted_pick(pairs):
    values = [item[0] for item in pairs]
    weights = [item[1] for item in pairs]
    return random.choices(values, weights=weights, k=1)[0]


def pick_travel_date():
    """Pick a travel month first so all 24 months are evenly covered.

    The booking date is then derived inside the 120 day window, which keeps
    every travel month free of ramp up while still respecting booking_date
    between 2024-09-01 and 2026-10-31.
    """
    options = []
    weights = []
    for year in (2025, 2026):
        for month in range(1, 13):
            options.append((year, month))
            weights.append(SEASON_WEIGHT[month])
    year, month = random.choices(options, weights=weights, k=1)[0]
    day = random.randint(1, calendar.monthrange(year, month)[1])
    return date(year, month, day)


def compute_delay(train, travel_day, cache):
    key = (train["train_number"], travel_day)
    if key in cache:
        return cache[key]
    if random.random() < ZERO_DELAY_PROB:
        delay = 0
    else:
        base = DELAY_BASE.get(train["train_type"], DELAY_BASE["OTH"])
        factor = ZONE_FACTOR.get(train["zone"], 1.0)
        seasonal = 15 if 6 <= travel_day.month <= 9 else 0
        noise = random.gauss(10.0, 15.0)
        delay = int(round(base * factor + seasonal + noise))
        if delay < 0:
            delay = 0
        if delay > 600:
            delay = 600
    cache[key] = delay
    return delay


def group_sizes():
    weights = [0.55, 0.30, 0.08, 0.04, 0.02, 0.01]
    sizes = random.choices([1, 2, 3, 4, 5, 6], weights=weights, k=TARGET_PNRS)
    total = sum(sizes)
    while total > TARGET_ROWS:
        index = random.randrange(TARGET_PNRS)
        if sizes[index] > 1:
            sizes[index] -= 1
            total -= 1
    while total < TARGET_ROWS:
        index = random.randrange(TARGET_PNRS)
        if sizes[index] < 6:
            sizes[index] += 1
            total += 1
    return sizes


def unique_pnrs(count):
    seen = set()
    pnrs = []
    while len(pnrs) < count:
        candidate = random.randint(1000000000, 9999999999)
        if candidate in seen:
            continue
        seen.add(candidate)
        pnrs.append(str(candidate))
    return pnrs


def main():
    random.seed(42)

    if not TRAINS_CSV.exists() or not STOPS_CSV.exists():
        print("ERROR: run scripts/build_reference.py before this script")
        return 1

    trains = load_trains()
    stops = load_stops(set(trains))
    usable = [number for number in trains if len(stops.get(number, [])) >= 2]
    if not usable:
        print("ERROR: no trains with at least 2 stops in data/raw")
        return 1

    class_pools = {}
    for code in CLASS_ORDER:
        class_pools[code] = [
            number for number in usable if code in allowed_classes(trains[number])[0]
        ]
        if not class_pools[code]:
            print("ERROR: no train supports class %s" % code)
            return 1
    class_choices = [(code, CLASS_WEIGHTS[code]) for code in CLASS_ORDER]

    sizes = group_sizes()
    pnrs = unique_pnrs(TARGET_PNRS)

    delay_cache = {}
    booking_dates = []
    travel_dates = []

    counts = {
        "booking_status": {},
        "current_status": {},
        "class": {},
        "quota": {},
        "payment": {},
        "channel": {},
        "reason": {},
        "month": {},
        "gender": {},
    }
    rows_written = 0
    cancelled_total = 0
    fare_total = 0.0
    refund_total = 0.0
    delay_sum = 0
    delay_max = 0
    late_rows = 0
    zero_delay_rows = 0
    zero_delay_groups = 0
    group_count = 0
    min_fare = None
    max_fare = None
    min_distance = None
    max_distance = 0
    sample = []

    def bump(bucket, key, amount=1):
        counts[bucket][key] = counts[bucket].get(key, 0) + amount

    with BOOKINGS_CSV.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle, lineterminator="\n")
        writer.writerow(COLUMNS)

        for group_index, size in enumerate(sizes):
            group_count += 1
            pnr = pnrs[group_index]
            travel_class = weighted_pick(class_choices)
            train_number = random.choice(class_pools[travel_class])
            train = trains[train_number]
            train_stops = stops[train_number]
            n_stops = len(train_stops)
            index_from, index_to = sorted(random.sample(range(n_stops), 2))
            from_code, from_name = train_stops[index_from]
            to_code, to_name = train_stops[index_to]

            legs = index_to - index_from
            if train["distance"]:
                distance = int(round(train["distance"] * legs / (n_stops - 1)))
                if distance > train["distance"]:
                    distance = train["distance"]
            else:
                distance = 55 * legs
                if distance > 3500:
                    distance = 3500
            if distance > MAX_DISTANCE:
                distance = MAX_DISTANCE
            if distance > max_distance:
                max_distance = distance
            if min_distance is None or distance < min_distance:
                min_distance = distance

            allowed, _ = allowed_classes(train)
            assert travel_class in allowed, "train %s does not support %s" % (
                train_number, travel_class)
            bump("class", travel_class, size)

            quota_options = [(code, weight) for code, weight in QUOTA_WEIGHTS
                             if code != "PT" or travel_class in ("SL", "3A")]
            quota = weighted_pick(quota_options)
            bump("quota", quota, size)

            booking_status = weighted_pick(BOOKING_STATUS_WEIGHTS)
            bump("booking_status", booking_status, size)

            travel_day = pick_travel_date()
            low_offset = max(1, (travel_day - MAX_BOOKING).days)
            high_offset = min(120, (travel_day - MIN_BOOKING).days)
            assert low_offset <= high_offset, "no booking window for %s" % travel_day
            offset = random.randint(low_offset, high_offset)
            booking_day = travel_day - timedelta(days=offset)
            booking_dates.append(booking_day)
            travel_dates.append(travel_day)

            delay = compute_delay(train, travel_day, delay_cache)
            if delay == 0:
                zero_delay_groups += 1

            charge = random.randint(40, 60)
            raw_fare = distance * CLASS_RATE[travel_class] + charge
            minimum = CLASS_MIN_FARE[travel_class]
            if raw_fare < minimum:
                raw_fare = minimum
            raw_fare *= random.uniform(0.85, 1.35)
            fare = int(round(raw_fare / 5.0)) * 5
            if fare <= 0:
                fare = 5

            if min_fare is None or fare < min_fare:
                min_fare = fare
            if max_fare is None or fare > max_fare:
                max_fare = fare

            cancellations_left = 2
            cancelled_in_group = 0
            travel_date_text = travel_day.isoformat()
            booking_date_text = booking_day.isoformat()
            travel_month = travel_date_text[:7]
            bump("month", travel_month, size)

            for seq in range(1, size + 1):
                cancelled = False
                if cancellations_left > 0 and random.random() < CANCEL_RATE:
                    cancelled = True
                    cancellations_left -= 1
                    cancelled_in_group += 1

                if cancelled:
                    current_status = "CAN"
                elif booking_status == "CNF":
                    current_status = "CNF"
                elif booking_status == "RAC":
                    current_status = "CNF" if random.random() < 0.45 else "RAC"
                else:
                    roll = random.random()
                    if roll < 0.20:
                        current_status = "CNF"
                    elif roll < 0.45:
                        current_status = "RAC"
                    else:
                        current_status = "WL"

                if booking_status == "CNF":
                    waitlist_position = 0
                elif booking_status == "RAC":
                    waitlist_position = random.randint(1, 60)
                else:
                    waitlist_position = random.randint(1, 200)

                if cancelled:
                    refund = round(fare * random.uniform(0.60, 1.00), 2)
                    refund_total += refund
                    reason = weighted_pick(CANCEL_REASONS)
                    bump("reason", reason)
                    cancelled_total += 1
                else:
                    refund = 0.0
                    reason = ""

                payment_mode = weighted_pick(PAYMENT_WEIGHTS)
                channel = weighted_pick(CHANNEL_WEIGHTS)
                bump("payment", payment_mode)
                bump("channel", channel)

                age = random.randint(1, 85)
                gender = random.choices(["M", "F", "O"], weights=[52.0, 46.0, 2.0], k=1)[0]
                concession = 1 if random.random() < 0.08 else 0
                bump("gender", gender)
                bump("current_status", current_status)

                row = [
                    pnr,
                    str(seq),
                    train_number,
                    train["train_name"],
                    train["train_type"],
                    train["zone"],
                    travel_date_text,
                    booking_date_text,
                    from_code,
                    from_name,
                    to_code,
                    to_name,
                    str(distance),
                    travel_class,
                    quota,
                    booking_status,
                    current_status,
                    str(waitlist_position),
                    str(fare),
                    "%.2f" % refund,
                    payment_mode,
                    channel,
                    str(age),
                    gender,
                    str(concession),
                    "1" if cancelled else "0",
                    reason,
                    str(delay),
                    travel_month,
                ]

                # Field level contract checks.
                assert len(row) == len(COLUMNS), "row has %d fields" % len(row)
                for value in row:
                    assert "," not in value, "comma in field %r" % value
                    assert "\t" not in value, "tab in field %r" % value
                    assert "\n" not in value and "\r" not in value, "newline in field %r" % value
                assert travel_class in allowed, "unsupported class %s for train %s" % (
                    travel_class, train_number)
                assert booking_status in ("CNF", "RAC", "WL"), "bad booking status"
                assert current_status in ("CNF", "RAC", "WL", "CAN"), "bad current status"
                assert current_status != "CAN" or cancelled, "CAN without cancellation"
                if booking_status == "CNF":
                    assert current_status in ("CNF", "CAN"), "CNF passenger changed status"
                    assert waitlist_position == 0, "CNF with waitlist position"
                elif booking_status == "RAC":
                    assert current_status in ("CNF", "RAC", "CAN"), "bad RAC transition"
                    assert 1 <= waitlist_position <= 60, "RAC position out of range"
                else:
                    assert current_status in ("CNF", "RAC", "WL", "CAN"), "bad WL transition"
                    assert 1 <= waitlist_position <= 200, "WL position out of range"
                assert quota in ("GN", "TQ", "LD", "SS", "RS", "PT"), "bad quota"
                assert quota != "PT" or travel_class in ("SL", "3A"), "PT on non reserved class"
                assert MIN_BOOKING <= booking_day <= MAX_BOOKING, "booking date out of range"
                assert booking_day < travel_day, "travel date not after booking date"
                assert (travel_day - booking_day).days <= 120, "travel more than 120 days later"
                assert travel_day >= MIN_TRAVEL, "travel date before 2025-01-01"
                assert travel_day <= MAX_TRAVEL, "travel date after 2026-12-31"
                assert 0 <= distance <= MAX_DISTANCE, "distance out of range"
                if train["distance"]:
                    assert distance <= train["distance"], "distance above train total"
                assert travel_month == travel_date_text[:7], "travel_month mismatch"
                assert 0 <= delay <= 600, "delay out of range"
                assert delay == delay_cache[(train_number, travel_day)], "delay not stable"
                assert refund >= 0, "negative refund"
                if cancelled:
                    assert fare * 0.60 - 0.01 <= refund <= fare * 1.00 + 0.01, "refund out of range"
                    assert reason != "", "cancelled without reason"
                else:
                    assert refund == 0, "refund on a live booking"
                    assert reason == "", "reason on a live booking"
                assert fare > 0, "non positive fare"
                assert 1 <= age <= 85, "age out of range"
                assert gender in ("M", "F", "O"), "bad gender"
                assert concession in (0, 1), "bad concession"
                assert payment_mode in ("UPI", "Card", "NetBanking", "Wallet", "Cash"), "bad payment"
                assert channel in ("App", "Web", "Counter", "Agent"), "bad channel"

                writer.writerow(row)
                rows_written += 1
                fare_total += fare
                delay_sum += delay
                if delay > delay_max:
                    delay_max = delay
                if delay == 0:
                    zero_delay_rows += 1
                if delay > 15:
                    late_rows += 1
                if len(sample) < 2:
                    sample.append(row)

            assert cancelled_in_group <= 2, "more than 2 cancellations in a PNR"

    # Global assertions on the finished file.
    assert rows_written == TARGET_ROWS, "wrote %d rows, expected %d" % (
        rows_written, TARGET_ROWS)
    assert len(set(pnrs)) == TARGET_PNRS, "PNR count mismatch"
    average_group = rows_written / float(TARGET_PNRS)
    assert 1.6 <= average_group <= 1.8, "average group size %.3f" % average_group

    share = {key: 100.0 * value / rows_written for key, value in counts["booking_status"].items()}
    assert abs(share.get("CNF", 0) - 70) <= 3, "CNF share %.2f" % share.get("CNF", 0)
    assert abs(share.get("RAC", 0) - 12) <= 3, "RAC share %.2f" % share.get("RAC", 0)
    assert abs(share.get("WL", 0) - 18) <= 3, "WL share %.2f" % share.get("WL", 0)

    cancel_rate = 100.0 * cancelled_total / rows_written
    assert 7 <= cancel_rate <= 11, "cancellation rate %.2f" % cancel_rate

    class_share = {key: 100.0 * value / rows_written for key, value in counts["class"].items()}
    for key in CLASS_ORDER:
        target = CLASS_WEIGHTS[key]
        actual = class_share.get(key, 0.0)
        assert abs(actual - target) <= 2, "class %s share %.2f, target %.0f" % (
            key, actual, target)

    delay_avg = delay_sum / float(rows_written)
    assert 15 <= delay_avg <= 30, "average delay %.2f" % delay_avg
    positive_delay_pct = 100.0 * (rows_written - zero_delay_rows) / rows_written
    assert 42 <= positive_delay_pct <= 48, "rows with delay > 0 %.2f" % positive_delay_pct
    zero_group_pct = 100.0 * zero_delay_groups / group_count
    assert 35 <= zero_group_pct <= 55, "zero delay group share %.2f" % zero_group_pct
    assert delay_max <= 600, "max delay out of range"

    assert min_distance is not None and min_distance >= 0, "negative distance"
    assert max_distance <= MAX_DISTANCE, "distance above 4500 km"

    months = sorted(counts["month"])
    assert len(months) == 24, "expected 24 travel months, found %d" % len(months)
    assert months[0] == "2025-01", "first travel month %s" % months[0]
    assert months[-1] == "2026-12", "last travel month %s" % months[-1]
    min_month = min(counts["month"].values())
    for month in months:
        assert counts["month"][month] >= 4000, "travel month %s has %d rows" % (
            month, counts["month"][month])

    # Header sanity.
    with BOOKINGS_CSV.open("r", encoding="utf-8", newline="") as handle:
        header = next(csv.reader(handle))
    assert header == COLUMNS, "header does not match the contract"

    size_bytes = BOOKINGS_CSV.stat().st_size
    print("bookings.csv rows: %d" % rows_written)
    print("bookings.csv size: %.2f MB" % (size_bytes / (1024.0 * 1024.0)))
    print("unique PNRs: %d, passengers per PNR average: %.4f" % (TARGET_PNRS, average_group))
    print("booking dates: %s to %s" % (min(booking_dates).isoformat(), max(booking_dates).isoformat()))
    print("travel dates: %s to %s" % (min(travel_dates).isoformat(), max(travel_dates).isoformat()))
    print("")
    print("distribution summary")
    print("booking_status:")
    for key in ("CNF", "RAC", "WL"):
        print("  %-4s %7d  %5.2f%%" % (key, counts["booking_status"].get(key, 0), share.get(key, 0)))
    current = counts["current_status"]
    print("current_status:")
    for key in ("CNF", "RAC", "WL", "CAN"):
        value = current.get(key, 0)
        print("  %-4s %7d  %5.2f%%" % (key, value, 100.0 * value / rows_written))
    print("cancellation rate: %.2f%% (%d passengers)" % (cancel_rate, cancelled_total))
    print("class share:")
    for key in CLASS_ORDER:
        value = counts["class"].get(key, 0)
        print("  %-4s %7d  %5.2f%%" % (key, value, 100.0 * value / rows_written))
    print("quota share:")
    for key, _ in QUOTA_WEIGHTS:
        value = counts["quota"].get(key, 0)
        print("  %-4s %7d  %5.2f%%" % (key, value, 100.0 * value / rows_written))
    print("payment_mode share:")
    for key, _ in PAYMENT_WEIGHTS:
        value = counts["payment"].get(key, 0)
        print("  %-10s %7d  %5.2f%%" % (key, value, 100.0 * value / rows_written))
    print("channel share:")
    for key, _ in CHANNEL_WEIGHTS:
        value = counts["channel"].get(key, 0)
        print("  %-8s %7d  %5.2f%%" % (key, value, 100.0 * value / rows_written))
    positive_delay_pct = 100.0 * (rows_written - zero_delay_rows) / rows_written
    print("delay: average %.2f minutes, max %d, rows with delay > 0 %.2f%%, rows with delay > 15 %d" % (
        delay_avg, delay_max, positive_delay_pct, late_rows))
    print("groups with zero delay: %d of %d (%.2f%%)" % (
        zero_delay_groups, group_count, zero_group_pct))
    print("travel months: %d distinct, %s to %s, min rows in a month %d (%s), max %d" % (
        len(counts["month"]), months[0], months[-1], min_month,
        min(months, key=lambda month: counts["month"][month]),
        max(counts["month"].values())))
    print("distance_km: min %d, max %d" % (min_distance, max_distance))
    print("fare: min %d, max %d, average %.2f; gross revenue %.2f; refunds %.2f" % (
        min_fare, max_fare, fare_total / rows_written, fare_total, refund_total))
    print("cancellation reasons:")
    for key, _ in CANCEL_REASONS:
        print("  %-22s %6d" % (key, counts["reason"].get(key, 0)))
    print("")
    print("first 2 data rows:")
    for row in sample:
        print(",".join(row))
    print("")
    print("generate_bookings: all assertions passed")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except AssertionError as exc:
        print("VALIDATION FAILED: %s" % exc)
        sys.exit(1)
