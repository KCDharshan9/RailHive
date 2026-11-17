"""Result file contract shared by the runners, the site builder and tests."""

RESULTS = {
    "q01_kpis": [
        "total_bookings", "total_passengers", "gross_revenue", "refunds",
        "net_revenue", "avg_fare", "cancellation_rate", "waitlist_share",
        "avg_delay_minutes", "avg_distance_km", "confirmed_share",
    ],
    "q02_monthly": [
        "month", "bookings", "passengers", "revenue", "cancellations",
        "waitlist", "avg_delay",
    ],
    "q03_routes": [
        "route", "from_station", "to_station", "bookings", "passengers",
        "revenue", "avg_fare", "avg_delay",
    ],
    "q04_trains": [
        "train_number", "train_name", "train_type", "bookings", "passengers",
        "revenue", "avg_delay", "cancel_rate",
    ],
    "q05_class_revenue": [
        "travel_class", "bookings", "passengers", "revenue", "avg_fare",
        "share_pct",
    ],
    "q06_quota_revenue": [
        "quota", "bookings", "passengers", "revenue", "avg_fare",
    ],
    "q07_payments": ["payment_mode", "bookings", "revenue"],
    "q08_channels": ["channel", "bookings", "revenue"],
    "q09_status": [
        "travel_class", "bookings", "confirmed", "rac", "waitlist",
        "cancelled", "confirmation_rate", "avg_waitlist_position",
    ],
    "q10_cancellations": [
        "month", "cancellations", "cancellation_rate", "refund_amount",
    ],
    "q11_cancel_reasons": ["reason", "reason_count"],
    "q12_delay_by_type": [
        "train_type", "bookings", "avg_delay", "late_pct",
    ],
    "q13_delay_by_zone": [
        "zone", "bookings", "avg_delay", "late_pct",
    ],
    "q14_delay_monthly": [
        "month", "bookings", "avg_delay", "late_pct",
    ],
}

# Kept for the site builder: maps result file to the analytics.json section.
SECTION_MAP = {
    "q02_monthly": "monthly",
    "q03_routes": "routes",
    "q04_trains": "trains",
    "q05_class_revenue": "class_revenue",
    "q06_quota_revenue": "quota_revenue",
    "q07_payments": "payments",
    "q08_channels": "channels",
    "q09_status": "status",
    "q10_cancellations": "cancellations",
    "q11_cancel_reasons": "cancel_reasons",
    "q12_delay_by_type": "delay_by_type",
    "q13_delay_by_zone": "delay_by_zone",
    "q14_delay_monthly": "delay_monthly",
}

INT_FIELDS = {
    "total_bookings", "total_passengers", "bookings", "passengers",
    "cancellations", "waitlist", "confirmed", "rac", "cancelled",
    "reason_count",
}
