"""Build report/report.docx from the real project artefacts.

The script is re-runnable. It reads the computed numbers from
website/data/analytics.json, the query output TSV files in data/results/,
the SQL in sql/analysis/ and sql/ddl/, and the tables in
docs/DATA_DICTIONARY.md. It writes twelve matplotlib PNG charts and one
editable DOCX file into report/.

Run with: .venv\\Scripts\\python.exe scripts\\make_report.py
"""

import json
import os
import re
import sys
import unicodedata

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Inches, Pt

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(SCRIPT_DIR)
if SCRIPT_DIR not in sys.path:
    sys.path.insert(0, SCRIPT_DIR)

from result_spec import RESULTS  # noqa: E402

REPORT_DIR = os.path.join(ROOT, "report")
ANALYTICS_PATH = os.path.join(ROOT, "website", "data", "analytics.json")
RESULTS_DIR = os.path.join(ROOT, "data", "results")
SQL_DIR = os.path.join(ROOT, "sql", "analysis")
DDL_DIR = os.path.join(ROOT, "sql", "ddl")
DICT_PATH = os.path.join(ROOT, "docs", "DATA_DICTIONARY.md")
DOCX_PATH = os.path.join(REPORT_DIR, "report.docx")

TITLE = "Railway Reservation Analytics"
SUBTITLE = "A data warehousing and SQL analytics study"

COLORS = {
    "blue": "#1F4E79",
    "teal": "#2E8B8B",
    "orange": "#C55A11",
    "green": "#548235",
    "purple": "#7030A0",
    "red": "#C00000",
    "grey": "#808080",
    "gold": "#BF8F00",
}
PALETTE = [
    "#1F4E79", "#2E8B8B", "#C55A11", "#548235", "#7030A0",
    "#C00000", "#BF8F00", "#4472C4", "#70AD47", "#9E480E",
    "#636363", "#A5A5A5",
]


# --------------------------------------------------------------------------
# Text helpers
# --------------------------------------------------------------------------
def ascii_safe(text):
    """Return text that contains only printable ASCII characters."""
    if text is None:
        return ""
    text = str(text)
    replacements = {
        "\u2014": "-", "\u2013": "-", "\u2018": "'", "\u2019": "'",
        "\u201c": '"', "\u201d": '"', "\u2026": "...", "\u00a0": " ",
        "\u2022": "-", "\u2212": "-", "\u00b7": ".",
    }
    for key, val in replacements.items():
        text = text.replace(key, val)
    text = unicodedata.normalize("NFKD", text)
    text = text.encode("ascii", "ignore").decode("ascii")
    return text


def indian_format(value):
    """Group the integer part of a number using the Indian numbering system."""
    text = ascii_safe(value).strip()
    if not re.fullmatch(r"-?\d+(\.\d+)?", text):
        return text
    sign = ""
    if text.startswith("-"):
        sign = "-"
        text = text[1:]
    if "." in text:
        whole, frac = text.split(".", 1)
        frac = "." + frac
    else:
        whole, frac = text, ""
    if len(whole) > 3:
        out = whole[-3:]
        rest = whole[:-3]
        parts = []
        while len(rest) > 2:
            parts.insert(0, rest[-2:])
            rest = rest[:-2]
        if rest:
            parts.insert(0, rest)
        whole = ",".join(parts) + "," + out
    return sign + whole + frac


def money(value):
    return "Rs " + indian_format("%.2f" % float(value))


def num(value):
    return indian_format("%d" % int(round(float(value))))


def pct(value):
    return "%.2f%%" % float(value)


# --------------------------------------------------------------------------
# Data loading
# --------------------------------------------------------------------------
def load_analytics():
    with open(ANALYTICS_PATH, "r", encoding="utf-8") as fh:
        return json.load(fh)


def read_text(path):
    with open(path, "r", encoding="utf-8") as fh:
        return ascii_safe(fh.read())


def read_tsv(stem):
    path = os.path.join(RESULTS_DIR, stem + ".tsv")
    rows = []
    with open(path, "r", encoding="utf-8") as fh:
        for line in fh:
            line = line.rstrip("\r\n")
            if line == "":
                continue
            rows.append([ascii_safe(c) for c in line.split("\t")])
    return rows


def parse_markdown_tables(path):
    """Return {section_title: (header_cells, data_rows)} for md tables."""
    section = "Tables"
    result = {}
    header = None
    rows = []

    def flush():
        if header is not None:
            result[section] = (header, rows)

    with open(path, "r", encoding="utf-8") as fh:
        for raw in fh:
            line = raw.rstrip("\r\n")
            if line.startswith("### ") or line.startswith("## "):
                flush()
                section = line.split(" ", 1)[1].strip()
                header, rows = None, []
            if line.startswith("|") and line.endswith("|"):
                cells = [c.strip() for c in line[1:-1].split("|")]
                if all(re.fullmatch(r":?-{2,}:?", c) for c in cells):
                    continue
                if header is None:
                    header = cells
                else:
                    rows.append(cells)
    flush()
    return result


# --------------------------------------------------------------------------
# Matplotlib charts
# --------------------------------------------------------------------------
def style_axis(ax):
    ax.set_facecolor("#FFFFFF")
    ax.grid(True, axis="y", linestyle="--", linewidth=0.5, color="#BFBFBF")
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.tick_params(axis="both", labelsize=8)


def save_chart(fig, filename):
    fig.tight_layout()
    path = os.path.join(REPORT_DIR, filename)
    fig.savefig(path, dpi=150, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    return path


def chart_monthly(a):
    data = a["monthly"]
    months = [r["month"] for r in data]
    bookings = [r["bookings"] for r in data]
    revenue = [r["revenue"] / 100000.0 for r in data]
    fig, ax1 = plt.subplots(figsize=(10, 4.6))
    ax1.bar(months, revenue, color=COLORS["blue"], alpha=0.85, label="Revenue (lakh Rs)")
    ax1.set_ylabel("Revenue (lakh Rs)", fontsize=9, color=COLORS["blue"])
    ax1.tick_params(axis="x", rotation=60, labelsize=7)
    style_axis(ax1)
    ax2 = ax1.twinx()
    ax2.plot(months, bookings, color=COLORS["orange"], marker="o",
             linewidth=1.8, markersize=3.5, label="Bookings (PNR)")
    ax2.set_ylabel("Bookings (PNR)", fontsize=9, color=COLORS["orange"])
    ax2.spines["top"].set_visible(False)
    ax2.tick_params(axis="y", labelsize=8)
    ax1.set_title("Monthly bookings and revenue by travel month", fontsize=11, weight="bold")
    fig.tight_layout()
    return save_chart(fig, "chart_monthly.png")


def chart_class(a):
    data = a["class_revenue"]
    labels = [r["travel_class"] for r in data]
    vals = [r["revenue"] / 100000.0 for r in data]
    fig, ax = plt.subplots(figsize=(8.5, 4.2))
    bars = ax.bar(labels, vals, color=PALETTE[:len(labels)])
    ax.set_title("Revenue by travel class", fontsize=11, weight="bold")
    ax.set_ylabel("Revenue (lakh Rs)", fontsize=9)
    style_axis(ax)
    for b, v in zip(bars, vals):
        ax.text(b.get_x() + b.get_width() / 2, v, "%.1f" % v,
                ha="center", va="bottom", fontsize=8)
    return save_chart(fig, "chart_class.png")


def chart_quota(a):
    data = a["quota_revenue"]
    labels = [r["quota"] for r in data]
    vals = [r["revenue"] / 100000.0 for r in data]
    fig, ax = plt.subplots(figsize=(8.5, 4.2))
    bars = ax.bar(labels, vals, color=COLORS["teal"])
    ax.set_title("Revenue by booking quota", fontsize=11, weight="bold")
    ax.set_ylabel("Revenue (lakh Rs)", fontsize=9)
    style_axis(ax)
    for b, v in zip(bars, vals):
        ax.text(b.get_x() + b.get_width() / 2, v, "%.1f" % v,
                ha="center", va="bottom", fontsize=8)
    return save_chart(fig, "chart_quota.png")


def chart_payments(a):
    data = a["payments"]
    labels = [r["payment_mode"] for r in data]
    vals = [r["revenue"] / 100000.0 for r in data]
    fig, ax = plt.subplots(figsize=(8.5, 4.2))
    bars = ax.bar(labels, vals, color=COLORS["green"])
    ax.set_title("Revenue by payment mode", fontsize=11, weight="bold")
    ax.set_ylabel("Revenue (lakh Rs)", fontsize=9)
    style_axis(ax)
    for b, v in zip(bars, vals):
        ax.text(b.get_x() + b.get_width() / 2, v, "%.1f" % v,
                ha="center", va="bottom", fontsize=8)
    return save_chart(fig, "chart_payments.png")


def chart_channels(a):
    data = a["channels"]
    labels = [r["channel"] for r in data]
    vals = [r["revenue"] / 100000.0 for r in data]
    fig, ax = plt.subplots(figsize=(8.2, 4.2))
    bars = ax.bar(labels, vals, color=COLORS["purple"])
    ax.set_title("Revenue by booking channel", fontsize=11, weight="bold")
    ax.set_ylabel("Revenue (lakh Rs)", fontsize=9)
    style_axis(ax)
    for b, v in zip(bars, vals):
        ax.text(b.get_x() + b.get_width() / 2, v, "%.1f" % v,
                ha="center", va="bottom", fontsize=8)
    return save_chart(fig, "chart_channels.png")


def chart_status(a):
    data = a["status"]
    labels = [r["travel_class"] for r in data]
    fig, ax = plt.subplots(figsize=(8.5, 4.4))
    bottom = [0] * len(labels)
    series = [
        ("confirmed", COLORS["green"], "Confirmed"),
        ("rac", COLORS["gold"], "RAC"),
        ("waitlist", COLORS["orange"], "Waitlist at booking"),
        ("cancelled", COLORS["red"], "Cancelled"),
    ]
    for key, color, label in series:
        vals = [r[key] for r in data]
        ax.bar(labels, vals, bottom=bottom, color=color, label=label)
        bottom = [b + v for b, v in zip(bottom, vals)]
    ax.set_title("Booking status mix by travel class", fontsize=11, weight="bold")
    ax.set_ylabel("Passenger rows", fontsize=9)
    style_axis(ax)
    ax.legend(fontsize=7, ncol=2, frameon=False)
    return save_chart(fig, "chart_status.png")


def chart_reasons(a):
    data = a["cancel_reasons"]
    labels = [r["reason"] for r in data][::-1]
    vals = [r["count"] for r in data][::-1]
    fig, ax = plt.subplots(figsize=(8.5, 4.4))
    bars = ax.barh(labels, vals, color=COLORS["red"], alpha=0.85)
    ax.set_title("Cancellation reasons", fontsize=11, weight="bold")
    ax.set_xlabel("Number of cancellations", fontsize=9)
    ax.grid(True, axis="x", linestyle="--", linewidth=0.5, color="#BFBFBF")
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.tick_params(axis="both", labelsize=8)
    for b, v in zip(bars, vals):
        ax.text(v, b.get_y() + b.get_height() / 2, " " + num(v),
                va="center", fontsize=8)
    return save_chart(fig, "chart_reasons.png")


def chart_delay_type(a):
    data = a["delay_by_type"]
    labels = [r["train_type"] for r in data]
    vals = [r["avg_delay"] for r in data]
    fig, ax = plt.subplots(figsize=(9, 4.3))
    bars = ax.bar(labels, vals, color=COLORS["orange"])
    ax.set_title("Average arrival delay by train type", fontsize=11, weight="bold")
    ax.set_ylabel("Average delay (minutes)", fontsize=9)
    style_axis(ax)
    for b, v in zip(bars, vals):
        ax.text(b.get_x() + b.get_width() / 2, v, "%.1f" % v,
                ha="center", va="bottom", fontsize=7.5)
    return save_chart(fig, "chart_delay_type.png")


def chart_delay_zone(a):
    data = a["delay_by_zone"]
    labels = [r["zone"] for r in data]
    vals = [r["avg_delay"] for r in data]
    fig, ax = plt.subplots(figsize=(9.5, 4.3))
    ax.bar(labels, vals, color=COLORS["blue"])
    ax.set_title("Average arrival delay by railway zone", fontsize=11, weight="bold")
    ax.set_ylabel("Average delay (minutes)", fontsize=9)
    ax.tick_params(axis="x", rotation=60, labelsize=7)
    style_axis(ax)
    return save_chart(fig, "chart_delay_zone.png")


def chart_routes(a):
    data = a["routes"][:10]
    labels = [r["route"] for r in data][::-1]
    vals = [r["bookings"] for r in data][::-1]
    fig, ax = plt.subplots(figsize=(8.5, 4.6))
    bars = ax.barh(labels, vals, color=COLORS["teal"])
    ax.set_title("Top ten station pairs by number of bookings", fontsize=11, weight="bold")
    ax.set_xlabel("Bookings (distinct PNR)", fontsize=9)
    ax.grid(True, axis="x", linestyle="--", linewidth=0.5, color="#BFBFBF")
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.tick_params(axis="both", labelsize=8)
    for b, v in zip(bars, vals):
        ax.text(v, b.get_y() + b.get_height() / 2, " " + str(v),
                va="center", fontsize=8)
    return save_chart(fig, "chart_routes.png")


def chart_trains(a):
    data = a["trains"][:10]
    labels = [r["train_number"] for r in data][::-1]
    vals = [r["revenue"] / 100000.0 for r in data][::-1]
    fig, ax = plt.subplots(figsize=(8.5, 4.6))
    bars = ax.barh(labels, vals, color=COLORS["purple"])
    ax.set_title("Top ten trains by gross revenue", fontsize=11, weight="bold")
    ax.set_xlabel("Gross revenue (lakh Rs)", fontsize=9)
    ax.grid(True, axis="x", linestyle="--", linewidth=0.5, color="#BFBFBF")
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.tick_params(axis="both", labelsize=8)
    for b, v in zip(bars, vals):
        ax.text(v, b.get_y() + b.get_height() / 2, " %.1f" % v,
                va="center", fontsize=8)
    return save_chart(fig, "chart_trains.png")


def chart_delay_monthly(a):
    data = a["delay_monthly"]
    months = [r["month"] for r in data]
    avg = [r["avg_delay"] for r in data]
    late = [r["late_pct"] for r in data]
    fig, ax1 = plt.subplots(figsize=(10, 4.4))
    ax1.plot(months, avg, color=COLORS["orange"], marker="o",
             linewidth=1.8, markersize=3.5, label="Average delay")
    ax1.set_ylabel("Average delay (minutes)", fontsize=9, color=COLORS["orange"])
    ax1.tick_params(axis="x", rotation=60, labelsize=7)
    style_axis(ax1)
    ax2 = ax1.twinx()
    ax2.plot(months, late, color=COLORS["blue"], linestyle="--",
             linewidth=1.5, label="Late percentage")
    ax2.set_ylabel("Late percentage (%)", fontsize=9, color=COLORS["blue"])
    ax2.spines["top"].set_visible(False)
    ax2.tick_params(axis="y", labelsize=8)
    ax1.set_title("Monthly delay profile", fontsize=11, weight="bold")
    lines1, lab1 = ax1.get_legend_handles_labels()
    lines2, lab2 = ax2.get_legend_handles_labels()
    ax1.legend(lines1 + lines2, lab1 + lab2, fontsize=7, loc="upper left", frameon=False)
    fig.tight_layout()
    return save_chart(fig, "chart_delay_monthly.png")


def build_charts(a):
    os.makedirs(REPORT_DIR, exist_ok=True)
    paths = {}
    paths["monthly"] = chart_monthly(a)
    paths["class"] = chart_class(a)
    paths["quota"] = chart_quota(a)
    paths["payments"] = chart_payments(a)
    paths["channels"] = chart_channels(a)
    paths["status"] = chart_status(a)
    paths["reasons"] = chart_reasons(a)
    paths["delay_type"] = chart_delay_type(a)
    paths["delay_zone"] = chart_delay_zone(a)
    paths["routes"] = chart_routes(a)
    paths["trains"] = chart_trains(a)
    paths["delay_monthly"] = chart_delay_monthly(a)
    return paths


# --------------------------------------------------------------------------
# DOCX helpers
# --------------------------------------------------------------------------
def set_run_font(run, name="Calibri", size=10.5, bold=False, italic=False, color=None):
    run.font.name = name
    run.font.size = Pt(size)
    run.bold = bold
    run.italic = italic
    if color is not None:
        run.font.color.rgb = color
    return run


def shade_paragraph(paragraph, fill="F2F2F2"):
    pPr = paragraph._p.get_or_add_pPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear")
    shd.set(qn("w:color"), "auto")
    shd.set(qn("w:fill"), fill)
    pPr.append(shd)


def add_para(doc, text="", size=10.5, bold=False, italic=False,
             align=None, space_after=6, style=None, color=None):
    p = doc.add_paragraph(style=style)
    run = set_run_font(p.add_run(ascii_safe(text)), size=size, bold=bold,
                       italic=italic, color=color)
    p.paragraph_format.space_after = Pt(space_after)
    if align is not None:
        p.alignment = align
    return p


def add_heading(doc, text, level=1):
    h = doc.add_heading(ascii_safe(text), level=level)
    return h


def add_bullet(doc, text, level=0):
    style = "List Bullet" if level == 0 else "List Bullet 2"
    p = doc.add_paragraph(style=style)
    set_run_font(p.add_run(ascii_safe(text)), size=10.5)
    p.paragraph_format.space_after = Pt(3)
    return p


def add_numbered(doc, text):
    p = doc.add_paragraph(style="List Number")
    set_run_font(p.add_run(ascii_safe(text)), size=10.5)
    p.paragraph_format.space_after = Pt(3)
    return p


def add_code(doc, text, size=8):
    p = doc.add_paragraph()
    p.paragraph_format.space_after = Pt(8)
    p.paragraph_format.space_before = Pt(2)
    p.paragraph_format.left_indent = Inches(0.1)
    shade_paragraph(p, "F4F4F4")
    run = set_run_font(p.add_run(ascii_safe(text)), name="Consolas", size=size)
    run.font.color.rgb = None
    return p


def set_table_font(table, size=8):
    for row in table.rows:
        for cell in row.cells:
            for p in cell.paragraphs:
                for run in p.runs:
                    run.font.name = "Calibri"
                    run.font.size = Pt(size)


def add_table(doc, headers, rows, size=8, widths=None):
    table = doc.add_table(rows=1, cols=len(headers))
    table.style = "Table Grid"
    hdr = table.rows[0].cells
    for i, h in enumerate(headers):
        hdr[i].text = ""
        p = hdr[i].paragraphs[0]
        set_run_font(p.add_run(ascii_safe(h)), size=size, bold=True)
    for row in rows:
        cells = table.add_row().cells
        for i, val in enumerate(row):
            cells[i].text = ""
            p = cells[i].paragraphs[0]
            set_run_font(p.add_run(ascii_safe(val)), size=size)
    set_table_font(table, size)
    if widths:
        for row in table.rows:
            for i, w in enumerate(widths):
                row.cells[i].width = Inches(w)
    doc.add_paragraph().paragraph_format.space_after = Pt(2)
    return table


def add_picture(doc, path, width=6.2):
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = p.add_run()
    run.add_picture(path, width=Inches(width))
    p.paragraph_format.space_after = Pt(4)
    cap = doc.add_paragraph()
    cap.alignment = WD_ALIGN_PARAGRAPH.CENTER
    set_run_font(cap.add_run(ascii_safe(os.path.basename(path).replace(".png", ""))),
                 size=8, italic=True, color=None)
    cap.paragraph_format.space_after = Pt(8)
    return p


def page_break(doc):
    doc.add_page_break()


# --------------------------------------------------------------------------
# Query metadata
# --------------------------------------------------------------------------
QUERIES = [
    ("q01_kpis", "Headline key performance indicators",
     "Compute a single row of headline measures for the whole reservation fact table, "
     "including distinct bookings, passengers, gross and net revenue, cancellation "
     "rate, waitlist share, average delay, average distance and confirmed share."),
    ("q02_monthly", "Monthly bookings and revenue",
     "Aggregate booking volume, passenger count, revenue, cancellations, waitlist "
     "rows and average delay for every travel month, so that seasonal patterns can "
     "be studied over the full twenty four month horizon."),
    ("q03_routes", "Route pair performance",
     "Rank origin and destination station pairs by number of distinct bookings and "
     "report passenger volume, revenue, average fare and average delay for each pair."),
    ("q04_trains", "Train performance",
     "Rank individual trains by gross revenue and report booking count, passenger "
     "count, average delay and cancellation rate for each train."),
    ("q05_class_revenue", "Revenue share by travel class",
     "Measure the revenue contribution of each travel class and express it as a "
     "percentage of total gross revenue using a portable cross join to the grand total."),
    ("q06_quota_revenue", "Revenue by booking quota",
     "Compare the six booking quotas by bookings, passengers, revenue and average "
     "fare to understand how reservation quota policy relates to earnings."),
    ("q07_payments", "Revenue by payment mode",
     "Group the fact table by payment mode and report booking counts and revenue, "
     "showing which settlement methods carry the largest transaction volume."),
    ("q08_channels", "Revenue by booking channel",
     "Group the fact table by booking channel and report booking counts and revenue, "
     "so that digital and counter based sales can be compared."),
    ("q09_status", "Booking status mix by class",
     "Break down every travel class into confirmed, RAC, waitlist at booking and "
     "cancelled rows, and compute confirmation rate and average waitlist position."),
    ("q10_cancellations", "Monthly cancellations and refunds",
     "Track cancellation counts, cancellation rate and refund amount for each travel "
     "month, linking refunds outflows to the timing of cancellations."),
    ("q11_cancel_reasons", "Cancellation reasons",
     "Count cancelled passengers by stated reason and order the reasons from most "
     "frequent to least frequent."),
    ("q12_delay_by_type", "Delay profile by train type",
     "Compare train types by average arrival delay and by the percentage of rows "
     "with delay greater than fifteen minutes."),
    ("q13_delay_by_zone", "Delay profile by railway zone",
     "Compare owning railway zones by average arrival delay and by the percentage "
     "of rows with delay greater than fifteen minutes."),
    ("q14_delay_monthly", "Monthly delay profile",
     "Plot average arrival delay and late percentage across travel months to reveal "
     "whether punctuality changes with season."),
]


def query_insight(stem, a, rows):
    k = a["kpis"]
    if stem == "q01_kpis":
        return ("The fact table contains %s distinct PNRs and %s passenger rows. "
                "Gross revenue is %s, refunds are %s and net revenue is %s, giving "
                "an average fare of %s per passenger."
                % (num(k["total_bookings"]), num(k["total_passengers"]),
                   money(k["gross_revenue"]), money(k["refunds"]),
                   money(k["net_revenue"]), money(k["avg_fare"])))
    if stem == "q02_monthly":
        peak = max(a["monthly"], key=lambda r: r["revenue"])
        low = min(a["monthly"], key=lambda r: r["revenue"])
        return ("The result has %d monthly rows. The highest revenue month is %s "
                "with %s from %s bookings, while the lowest is %s with %s."
                % (len(rows), peak["month"], money(peak["revenue"]),
                   num(peak["bookings"]), low["month"], money(low["revenue"])))
    if stem == "q03_routes":
        top = a["routes"][0]
        return ("The query returns many low volume pairs; the leading pair %s to %s "
                "records %s bookings, %s passengers and %s revenue."
                % (top["route"], top["to_station"], num(top["bookings"]),
                   num(top["passengers"]), money(top["revenue"])))
    if stem == "q04_trains":
        top = a["trains"][0]
        return ("The top revenue train is %s (%s) with %s from %s bookings and an "
                "average delay of %.2f minutes."
                % (top["train_number"], top["train_name"], money(top["revenue"]),
                   num(top["bookings"]), top["avg_delay"]))
    if stem == "q05_class_revenue":
        top = a["class_revenue"][0]
        return ("Class %s contributes the largest share at %s of gross revenue, "
                "or %s, from %s bookings."
                % (top["travel_class"], pct(top["share_pct"]),
                   money(top["revenue"]), num(top["bookings"])))
    if stem == "q06_quota_revenue":
        top = a["quota_revenue"][0]
        return ("The general quota GN dominates with %s bookings, %s passengers, "
                "%s revenue and an average fare of %s."
                % (num(top["bookings"]), num(top["passengers"]),
                   money(top["revenue"]), money(top["avg_fare"])))
    if stem == "q07_payments":
        top = a["payments"][0]
        return ("UPI is the leading payment mode with %s bookings and %s revenue, "
                "followed by Card with %s bookings."
                % (num(top["bookings"]), money(top["revenue"]),
                   num(a["payments"][1]["bookings"])))
    if stem == "q08_channels":
        top = a["channels"][0]
        return ("The App channel leads with %s bookings and %s revenue, ahead of "
                "Web with %s bookings."
                % (num(top["bookings"]), money(top["revenue"]),
                   num(a["channels"][1]["bookings"])))
    if stem == "q09_status":
        top = max(a["status"], key=lambda r: r["confirmation_rate"])
        return ("Confirmation rates are close across classes; class %s is highest "
                "at %s, while the overall confirmed share is %s."
                % (top["travel_class"], pct(top["confirmation_rate"]),
                   pct(k["confirmed_share"])))
    if stem == "q10_cancellations":
        total = sum(r["cancellations"] for r in a["cancellations"])
        return ("Across the %d travel months there are %s cancellations and %s in "
                "total refunds, with a monthly cancellation rate near %s."
                % (len(rows), num(total),
                   money(sum(r["refund_amount"] for r in a["cancellations"])),
                   pct(k["cancellation_rate"])))
    if stem == "q11_cancel_reasons":
        top = a["cancel_reasons"][0]
        total = sum(r["count"] for r in a["cancel_reasons"])
        return ("The leading reason is %s with %s cases, which is %s of all %s "
                "cancelled passengers."
                % (top["reason"], num(top["count"]),
                   pct(100.0 * top["count"] / total), num(total)))
    if stem == "q12_delay_by_type":
        top = max(a["delay_by_type"], key=lambda r: r["avg_delay"])
        low = min(a["delay_by_type"], key=lambda r: r["avg_delay"])
        return ("Passenger trains have the highest average delay at %.2f minutes, "
                "while Rajdhani trains have the lowest at %.2f minutes."
                % (top["avg_delay"], low["avg_delay"]))
    if stem == "q13_delay_by_zone":
        top = max(a["delay_by_zone"], key=lambda r: r["avg_delay"])
        return ("Zone %s has the highest average delay at %.2f minutes across %s "
                "bookings; the overall average delay is %.2f minutes."
                % (top["zone"], top["avg_delay"], num(top["bookings"]),
                   k["avg_delay_minutes"]))
    if stem == "q14_delay_monthly":
        top = max(a["delay_monthly"], key=lambda r: r["avg_delay"])
        low = min(a["delay_monthly"], key=lambda r: r["avg_delay"])
        return ("The worst month for punctuality is %s with %.2f minutes average "
                "delay and %s late rows, while %s is best at %.2f minutes."
                % (top["month"], top["avg_delay"], pct(top["late_pct"]),
                   low["month"], low["avg_delay"]))
    return ""


# --------------------------------------------------------------------------
# Document sections
# --------------------------------------------------------------------------
def build_title_page(doc):
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_before = Pt(90)
    set_run_font(p.add_run(TITLE), size=28, bold=True, color=None)
    p2 = doc.add_paragraph()
    p2.alignment = WD_ALIGN_PARAGRAPH.CENTER
    set_run_font(p2.add_run(SUBTITLE), size=15, italic=True)
    p3 = doc.add_paragraph()
    p3.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p3.paragraph_format.space_before = Pt(16)
    set_run_font(p3.add_run("A project report submitted in partial fulfilment of the "
                            "requirements for the award of the degree"),
                 size=10, italic=True)
    fields = [
        "[Student Name]", "[Roll Number]", "[College Name]", "[Department]",
        "[Guide Name]", "[Semester]", "[Academic Year]", "[Subject Code]",
    ]
    doc.add_paragraph().paragraph_format.space_after = Pt(18)
    add_para(doc, "Submitted by", size=10.5, bold=True,
             align=WD_ALIGN_PARAGRAPH.CENTER, space_after=2)
    add_para(doc, fields[0], size=11, align=WD_ALIGN_PARAGRAPH.CENTER, space_after=2)
    add_para(doc, fields[1], size=11, align=WD_ALIGN_PARAGRAPH.CENTER, space_after=14)
    add_para(doc, "Under the guidance of", size=10.5, bold=True,
             align=WD_ALIGN_PARAGRAPH.CENTER, space_after=2)
    add_para(doc, fields[4], size=11, align=WD_ALIGN_PARAGRAPH.CENTER, space_after=14)
    add_para(doc, fields[2], size=11, align=WD_ALIGN_PARAGRAPH.CENTER, space_after=2)
    add_para(doc, fields[3], size=11, align=WD_ALIGN_PARAGRAPH.CENTER, space_after=14)
    add_para(doc, "%s | %s | %s"
             % (fields[5], fields[6], fields[7]),
             size=10.5, align=WD_ALIGN_PARAGRAPH.CENTER, space_after=2)
    page_break(doc)


def build_certificate(doc):
    add_heading(doc, "Certificate and Declaration", level=1)
    add_para(doc, "This is to certify that the project entitled " + TITLE +
             " submitted by [Student Name], bearing roll number [Roll Number], "
             "is a bonafide record of work carried out under the supervision of "
             "[Guide Name] in the [Department], [College Name], during [Semester] "
             "of [Academic Year].", space_after=10)
    add_para(doc, "Signature of Guide: ____________________", space_after=6)
    add_para(doc, "Name of Guide: [Guide Name]", space_after=6)
    add_para(doc, "Signature of Head of Department: ____________________", space_after=6)
    add_para(doc, "Date: ____________________", space_after=14)
    add_heading(doc, "Declaration", level=2)
    add_para(doc, "I, [Student Name], declare that the work presented in this report "
             "is my own and that all sources of information have been duly "
             "acknowledged. The reservation records analysed here are generated data "
             "used for academic study and are not derived from any real passenger "
             "booking system.", space_after=10)
    add_para(doc, "Signature of Student: ____________________", space_after=6)
    add_para(doc, "Place: ____________________", space_after=6)
    add_para(doc, "Date: ____________________", space_after=6)
    page_break(doc)


def build_abstract(doc, a):
    k = a["kpis"]
    m = a["meta"]
    add_heading(doc, "Abstract", level=1)
    add_para(doc,
             "This report presents the design and implementation of " + TITLE +
             ", a data warehousing and analytics project built around Indian "
             "Railways reservation records. The study uses real public reference "
             "data for stations, trains and schedules, together with a seeded "
             "synthetic reservation fact table, to design an Apache Hive warehouse "
             "for storing, partitioning and querying a large booking dataset. The "
             "analysis was executed with DuckDB 1.1.3; Hive is the documented "
             "optional path and was not executed in this build. The analysis covers %s passenger rows grouped into %s distinct "
             "numbered reservations, drawn from %s trains and %s stations over the "
             "travel period %s."
             % (num(m["bookings"]), num(a["kpis"]["total_bookings"]),
                num(m["trains"]), num(m["stations"]), m["period"]),
             space_after=10)
    add_para(doc,
             "The Hive warehouse is specified for the railway_analytics database "
             "with external staging tables, managed ORC dimension tables and an ORC "
             "fact table that is dynamically partitioned by travel month. The DDL is "
             "provided in sql/ddl/ but was not executed in this build. Fourteen "
             "portable SQL statements were executed with %s and their outputs were "
             "exported as tab separated result files; the engine and version are "
             "recorded in data/results/_engine.txt. Gross revenue amounts to %s, "
             "refunds to %s and net revenue to %s, with an average fare of %s. "
             "The confirmed share is %s, the waitlist share is %s and the overall "
             "cancellation rate is %s. The average arrival delay is %.2f minutes "
             "over an average journey distance of %.2f kilometres."
             % (m["engine"], money(k["gross_revenue"]), money(k["refunds"]),
                money(k["net_revenue"]), money(k["avg_fare"]),
                pct(k["confirmed_share"]), pct(k["waitlist_share"]),
                pct(k["cancellation_rate"]), k["avg_delay_minutes"],
                k["avg_distance_km"]),
             space_after=10)
    add_para(doc,
             "The results are presented through a Flask website with interactive "
             "charts and a filterable explorer backed by SQLite. The principal "
             "findings are that third AC class contributes the largest revenue "
             "share, the general quota accounts for most bookings, UPI and the "
             "mobile application are the dominant payment and channel choices, "
             "and delays show a clear seasonal peak in the monsoon months. The "
             "project provides an end to end, reproducible example of batch "
             "warehousing, SQL analytics and web based reporting suitable for "
             "academic study.",
             space_after=10)
    add_para(doc, "Keywords: Apache Hive (design), DuckDB (execution engine), "
             "data warehouse, ORC, dynamic partitioning, Indian Railways, "
             "SQL analytics, Flask, Python.", italic=True,
             space_after=6)
    page_break(doc)


def build_acknowledgements(doc):
    add_heading(doc, "Acknowledgements", level=1)
    add_para(doc, "I express my sincere gratitude to [Guide Name] for continuous "
             "guidance and for suggesting improvements to the design and "
             "presentation of this work. I thank the faculty of the [Department] "
             "at [College Name] for providing the academic environment and the "
             "infrastructure needed to complete this project.", space_after=10)
    add_para(doc, "I acknowledge the DataMeet community for publishing the Indian "
             "railways reference datasets under the CC0 licence. Those datasets "
             "made it possible to anchor the analysis in real station, train and "
             "schedule information. I also thank the open source community behind "
             "Apache Hadoop, Apache Hive, DuckDB, Python, Flask and the charting "
             "libraries used in this work.", space_after=10)
    add_para(doc, "Finally, I thank my family and classmates for their constant "
             "encouragement and for the helpful discussions during the development "
             "of this project.", space_after=10)
    page_break(doc)


def build_toc(doc):
    add_heading(doc, "Table of Contents", level=1)
    entries = [
        "Title page",
        "Certificate and Declaration",
        "Abstract",
        "Acknowledgements",
        "Table of Contents",
        "1. Introduction",
        "2. Objectives",
        "3. Literature Review and Background",
        "4. System Requirements",
        "5. Methodology",
        "6. Data Description",
        "7. Hive Database Design",
        "8. Query Implementation",
        "8.1 q01_kpis - Headline key performance indicators",
        "8.2 q02_monthly - Monthly bookings and revenue",
        "8.3 q03_routes - Route pair performance",
        "8.4 q04_trains - Train performance",
        "8.5 q05_class_revenue - Revenue share by travel class",
        "8.6 q06_quota_revenue - Revenue by booking quota",
        "8.7 q07_payments - Revenue by payment mode",
        "8.8 q08_channels - Revenue by booking channel",
        "8.9 q09_status - Booking status mix by class",
        "8.10 q10_cancellations - Monthly cancellations and refunds",
        "8.11 q11_cancel_reasons - Cancellation reasons",
        "8.12 q12_delay_by_type - Delay profile by train type",
        "8.13 q13_delay_by_zone - Delay profile by railway zone",
        "8.14 q14_delay_monthly - Monthly delay profile",
        "9. Results and Analysis",
        "10. Conclusion",
        "11. Limitations and Future Scope",
        "12. References",
        "Appendix A. How to Run the Project",
    ]
    for e in entries:
        p = doc.add_paragraph()
        set_run_font(p.add_run(ascii_safe(e)), size=10.5)
        p.paragraph_format.space_after = Pt(2)
    page_break(doc)


def build_intro(doc, a):
    add_heading(doc, "1. Introduction", level=1)
    add_heading(doc, "1.1 Context", level=2)
    add_para(doc, "Indian Railways is one of the largest rail transport networks in "
             "the world, moving millions of passengers every day across thousands "
             "of stations and service types. The network operates several reserved "
             "classes, multiple booking quotas and a mix of superfast, express, "
             "passenger and premium train services. Each reservation generates a "
             "record that captures a passenger, a train, an origin and destination, "
             "a travel date, a fare and a final booking outcome. Taken together, "
             "these records form a high volume transactional dataset whose analysis "
             "can reveal patterns in demand, revenue, cancellations and "
             "punctuality.", space_after=10)
    add_para(doc, "Traditional transaction systems are designed to record and "
             "retrieve individual bookings quickly, not to scan millions of rows "
             "for aggregate trends. A data warehouse addresses this gap by "
             "extracting operational data, cleaning it, storing it in an analytical "
             "format and exposing it to query and reporting tools. Apache Hive "
             "provides a SQL like interface over data stored in Hadoop, together "
             "with columnar file formats and partitioning that reduce the cost of "
             "large scans. These properties make Hive a suitable platform for a "
             "course level study of railway reservation analytics.", space_after=10)
    add_heading(doc, "1.2 Motivation", level=2)
    add_para(doc, "Passenger level reservation data is not published as open data "
             "by the railway administration, which limits the ability of students "
             "and independent researchers to practise large scale analytics on a "
             "realistic dataset. This project addresses the problem by combining "
             "genuine public reference data with a deterministic synthetic fact "
             "table. Station, train and schedule records come from the DataMeet "
             "railways collection released under CC0. Every generated booking is "
             "attached to a real train, a real station pair taken from that train's "
             "schedule and a class that the train actually supports. The result is "
             "a dataset that is realistic in structure and distribution while "
             "remaining fully reproducible.", space_after=10)
    add_heading(doc, "1.3 Problem statement", level=2)
    add_para(doc, "The core problem is to design and build an analytical pipeline "
             "that ingests railway reservation data, stores it efficiently, "
             "computes a defined set of business measures with portable SQL and "
             "presents the findings in an accessible form. The study must satisfy "
             "several constraints. The same SQL must run on Apache Hive and on a "
             "lightweight local engine so that the work is reproducible on machines "
             "without Docker. The warehouse must use staging tables, a columnar "
             "ORC fact table and monthly dynamic partitioning. The reported figures "
             "must be derived from executed queries rather than guessed, and the "
             "web interface must read precomputed results so that page loads stay "
             "fast and independent of the warehouse runtime.", space_after=10)
    add_para(doc, "The dataset used in this study contains %s passenger rows and "
             "%s distinct PNRs spanning travel dates from %s. Fourteen analysis "
             "queries produce the measures discussed in this report and the charts "
             "presented in Section 9."
             % (num(a["meta"]["bookings"]), num(a["kpis"]["total_bookings"]),
                a["meta"]["period"]), space_after=10)
    add_heading(doc, "1.4 Scope of the study", level=2)
    add_para(doc, "The scope covers batch analytics only. The project does not "
             "attempt live seat availability, real time train tracking or "
             "ticket sales. It focuses on descriptive analytics: what happened in "
             "the dataset in terms of booking volume, revenue, class and quota "
             "composition, payment behaviour, cancellations and delays. Predictive "
             "modelling is left for future work. Section 11 discusses these "
             "boundaries and possible extensions.", space_after=10)
    page_break(doc)


def build_objectives(doc):
    add_heading(doc, "2. Objectives", level=1)
    add_para(doc, "The project sets out the following objectives.", space_after=8)
    objectives = [
        "To obtain and clean public railway reference data for stations, trains and schedules.",
        "To generate a reproducible reservation fact table of 150000 passenger rows with a fixed random seed.",
        "To design a Hive warehouse named railway_analytics with staging tables, typed dimension tables and an ORC fact table.",
        "To provide the Hive DDL that loads the fact table using dynamic partitioning by travel month.",
        "To write fourteen portable SQL queries intended to run unchanged on Apache Hive and DuckDB.",
        "To compute headline measures such as bookings, passengers, gross revenue, net revenue, cancellation and confirmation rates.",
        "To analyse monthly trends, top routes, top trains, revenue by class, quota, payment mode and channel.",
        "To study booking status, cancellations, refunds and stated cancellation reasons.",
        "To measure arrival delays by train type, railway zone and travel month.",
        "To expose the computed results through a Flask website with charts and a filterable explorer.",
        "To export a static version of the website for hosting without a server.",
        "To document the entire pipeline and produce an editable academic report.",
    ]
    for o in objectives:
        add_bullet(doc, o)
    page_break(doc)


def build_literature(doc):
    add_heading(doc, "3. Literature Review and Background", level=1)
    add_heading(doc, "3.1 Data warehousing concepts", level=2)
    add_para(doc, "A data warehouse is a subject oriented, integrated, time variant "
             "and non volatile collection of data that supports decision making. "
             "In a star schema, a central fact table holds measurable events and "
             "surrounding dimension tables hold descriptive attributes. In this "
             "project the reservation fact table plays the central role, while "
             "stations, trains and train stops provide descriptive context. The "
             "measures of interest include counts of distinct reservations, counts "
             "of passengers, sums of fare and refund, and derived percentages. "
             "Separating facts from dimensions reduces repetition and allows the "
             "same dimension to support several analytical questions.", space_after=10)
    add_heading(doc, "3.2 Apache Hive and Hadoop", level=2)
    add_para(doc, "Apache Hive is a data warehouse system built on top of Apache "
             "Hadoop. It provides a SQL like language called HiveQL, which is "
             "translated into jobs that process data stored in HDFS or compatible "
             "filesystems. Hive supports external tables for raw files, managed "
             "tables for curated data and a range of storage formats. The Optimized "
             "Row Columnar format, commonly called ORC, stores data by column, "
             "which allows a query that reads only a few columns to skip the rest. "
             "Partitioning divides a table into directories by the value of one or "
             "more partition columns. For a reservation table, partitioning by "
             "travel month means that a query restricted to one month reads only "
             "that month's files.", space_after=10)
    add_para(doc, "Dynamic partitioning in Hive allows an insert statement to "
             "create partition directories automatically from the values present "
             "in the source data. This is useful when the set of months is not known "
             "in advance. The Hive DDL in this project sets dynamic partitioning to "
             "nonstrict mode, places the partition column last in the insert select, "
             "as required by Hive, and enables MapReduce local mode for the small "
             "dimension jobs so that the warehouse can be built on a laptop. These "
             "settings belong to the optional Hive path; it was not executed in this "
             "build, and the reported figures were produced with DuckDB.",
             space_after=10)
    add_heading(doc, "3.3 Portable SQL and the DuckDB fallback", level=2)
    add_para(doc, "SQL dialects differ in date functions, string concatenation and "
             "conditional expressions. To keep a single set of analysis files, the "
             "project restricts itself to a portable subset. Months are extracted "
             "with substr on ISO date strings, strings are joined with concat, "
             "nulls are handled with coalesce and conditional logic uses case when. "
             "Window functions and common table expressions are avoided. DuckDB is "
             "an embeddable analytical database that can query CSV files directly. "
             "It is used as a fallback engine where Docker is not available; in this "
             "build it was the engine that executed the analysis, with views that "
             "expose the same table and column names as the Hive warehouse. Because "
             "the SQL is identical, both engines are designed to produce the same "
             "result structure.", space_after=10)
    add_heading(doc, "3.4 Web presentation of analytics", level=2)
    add_para(doc, "Analytical results are useful only when they can be explored. "
             "Flask is a lightweight Python web framework suitable for small data "
             "applications. Jinja2 templates render pages, Bootstrap supplies a "
             "responsive layout and Chart.js draws interactive charts in the "
             "browser. Writing query outputs to JSON once, instead of querying "
             "Hive on every page load, keeps the site responsive and allows a "
             "static export. SQLite provides a small local database for the "
             "row level explorer, with indexes on frequently filtered columns.",
             space_after=10)
    add_heading(doc, "3.5 Related work and sources", level=2)
    add_para(doc, "Public railway datasets have been used in prior community work "
             "for mapping routes and studying timetables. The DataMeet railways "
             "collection is a well known open source effort that publishes station, "
             "train and schedule information under the CC0 licence. Academic "
             "literature on data warehousing commonly uses the star schema as a "
             "reference model for fact and dimension design, and columnar storage "
             "as a standard technique for analytical workloads. The present study "
             "combines these established ideas in a single teaching oriented "
             "pipeline. The principal public sources are listed with URLs in "
             "Section 12.", space_after=10)
    page_break(doc)


def build_requirements(doc):
    add_heading(doc, "4. System Requirements", level=1)
    add_para(doc, "The software stack is entirely free and open source. No API keys "
             "or paid services are required. The technology layers are summarised "
             "below.", space_after=8)
    add_table(doc,
              ["Layer", "Tool"],
              [
                  ["Warehouse design (optional path)", "Apache Hive 4.2.1, Hadoop 3.4.1, Docker"],
                  ["Query engine used for this build", "DuckDB 1.1.3"],
                  ["Data preparation", "Python 3.10 standard library"],
                  ["Website", "Flask 3.0, Jinja2, Bootstrap 5.3, Chart.js 4.4"],
                  ["Local database", "SQLite"],
                  ["Report", "python-docx, matplotlib"],
              ], size=9)
    add_heading(doc, "4.1 Hardware requirements", level=2)
    add_bullet(doc, "A 64 bit Windows, Linux or macOS computer.")
    add_bullet(doc, "At least 4 GB of free disk space and 4 GB of RAM for the Hive path.")
    add_bullet(doc, "A multi core processor is recommended for the first ORC load.")
    add_bullet(doc, "Internet access is needed once to download the reference data and, for the Hive path, the Docker image.")
    add_heading(doc, "4.2 Software requirements", level=2)
    add_bullet(doc, "Python 3.10 or newer, with a virtual environment.")
    add_bullet(doc, "Java 17 or newer only when Hive is run directly outside Docker.")
    add_bullet(doc, "Docker Desktop for the optional Hive path.")
    add_bullet(doc, "The Python packages listed in requirements.txt, including duckdb, flask, python-docx and matplotlib.")
    add_para(doc, "The DuckDB path needs only Python. This makes the project usable "
             "on machines where Docker cannot be installed, while the SQL and the "
             "result file structure are the same for both paths.", space_after=10)
    page_break(doc)


def build_methodology(doc, engine):
    add_heading(doc, "5. Methodology", level=1)
    add_para(doc, "The project follows a batch pipeline with five stages: acquire "
             "reference data, clean it, generate the reservation fact table, run "
             "the analysis SQL, and publish results through the website. The "
             "architecture is documented in docs/ARCHITECTURE.md and is reproduced "
             "in condensed form below.", space_after=8)
    add_code(doc,
             "DataMeet JSON (CC0)\n"
             "  stations.json, trains.json, schedules.json\n"
             "         |\n"
             "         v\n"
             "scripts/build_reference.py -> data/raw/stations.csv, trains.csv,\n"
             "                              train_stops.csv\n"
             "         |\n"
             "scripts/generate_bookings.py (seed 42) -> data/raw/bookings.csv\n"
             "         |\n"
             "         +--------------------------+\n"
             "         |                          |\n"
             "         v                          v\n"
             "Hive 4.2.1 in Docker (optional)  DuckDB 1.1.3 (used)\n"
             "staging -> ORC partitioned       views over the same CSV files\n"
             "         |                          |\n"
             "         +------------+-------------+\n"
             "                      |\n"
             "         sql/analysis/q01 ... q14 (portable SELECT)\n"
             "                      |\n"
             "                      v\n"
             "         data/results/qNN_name.tsv\n"
             "                      |\n"
             "         scripts/build_site_data.py\n"
             "                      |\n"
             "         +------------+-------------------+\n"
             "         |                                |\n"
             "         v                                v\n"
             "website/data/analytics.json       data/processed/analytics.db\n"
             "         |                                |\n"
             "         v                                v\n"
             "Flask pages and Chart.js          /api/bookings explorer queries\n"
             "         |\n"
             "scripts/export_static.py -> dist/ (static copy, no server)",
             size=7.5)
    add_heading(doc, "5.1 Stage 1: acquisition and cleaning", level=2)
    add_para(doc, "The reference files are downloaded from the DataMeet railways "
             "repository. The cleaning step keeps station codes that are not "
             "placeholder codes, fills missing state and zone values with UNKNOWN "
             "and UNK, and derives latitude and longitude from GeoJSON coordinates. "
             "The train builder keeps only trains with at least one reserved class "
             "flag and at least two stop records, converts duration to minutes and "
             "stores class availability as integer flags. Stop records are ordered "
             "from one and linked only to trains retained in the train table.",
             space_after=10)
    add_heading(doc, "5.2 Stage 2: generation and validation", level=2)
    add_para(doc, "The booking generator uses random.seed(42) and writes exactly "
             "150000 passenger rows. Passengers sharing a PNR form one booking. "
             "Class is sampled from global weights and then a supporting train is "
             "chosen, so rare classes are not diluted. Fares are computed from "
             "class specific per kilometre rates, a reservation charge, a minimum "
             "fare and a demand factor. Travel dates are constrained to the defined "
             "window and delays are constant for a given train and date. The "
             "generator prints distribution checks and fails if any rule is "
             "violated.", space_after=10)
    add_heading(doc, "5.3 Stage 3: warehouse load and query execution", level=2)
    add_para(doc, "The Hive path, when run, creates the database, loads CSV files into external "
             "style staging tables whose columns are all strings, builds typed ORC "
             "dimensions and then inserts into the ORC fact table with dynamic "
             "partitioning by travel month. The DuckDB path creates views over the "
             "same CSV files with identical column names. Both paths are provided in "
             "this repository and run the same fourteen SQL files, writing one tab "
             "separated result file per query. In this build Docker was not "
             "available, so the analysis was executed with DuckDB 1.1.3 via "
             "scripts/run_local.py; the Hive runner was not executed. The execution "
             "engine and version are recorded in "
             "data/results/_engine.txt; for this build the engine is "
             + engine + ".", space_after=10)
    add_heading(doc, "5.4 Stage 4: publication", level=2)
    add_para(doc, "The site builder validates every result file, maps each result "
             "to a section of analytics.json and builds a SQLite bookings table "
             "with indexes on travel date, train number, travel class and PNR. The "
             "Flask app reads analytics.json for charts and SQLite for the "
             "explorer. A static export writes the same templates and embedded data "
             "to a dist folder that can be opened from disk or hosted on any static "
             "provider.", space_after=10)
    add_heading(doc, "5.5 Reproducibility", level=2)
    add_para(doc, "Every stage is a separate script with no hidden state. The fixed "
             "seed makes the generated data identical on each run, and the only "
             "external input is the public reference data. Re-running the pipeline "
             "and then the report generator reproduces the same figures and charts.",
             space_after=10)
    page_break(doc)


def build_data_description(doc, a):
    add_heading(doc, "6. Data Description", level=1)
    add_para(doc, "The project uses three public reference datasets and one "
             "generated fact dataset. The reference data is released under the "
             "CC0 licence by DataMeet. Reservation records are generated because "
             "passenger level PNR data is not available as open data. Every "
             "generated booking is attached to a real train, a real station pair "
             "from that train's schedule and a real class that the train supports.",
             space_after=8)
    add_table(doc,
              ["Dataset", "Origin", "Licence", "Use"],
              [
                  ["Station list with coordinates and zones", "DataMeet railways", "CC0", "Station dimension"],
                  ["Train list with type, zone, distance and class flags", "DataMeet railways", "CC0", "Train dimension"],
                  ["Train stop schedules", "DataMeet railways", "CC0", "Stop sequence and route pairs"],
                  ["Reservation records", "Generated with seed 42", "Project generated", "Fact table"],
              ], size=8.5)
    tables = parse_markdown_tables(DICT_PATH)
    for section, title in [
        ("stations", "6.1 stations"),
        ("trains", "6.2 trains"),
        ("train_stops", "6.3 train_stops"),
        ("bookings", "6.4 bookings"),
    ]:
        add_heading(doc, title, level=2)
        header, rows = tables[section]
        add_para(doc, "The following table lists the columns, types and meanings "
                 "for the %s table." % section, size=9.5, space_after=4)
        add_table(doc, header, rows, size=7.5)
    add_heading(doc, "6.5 Derived measures", level=2)
    header, rows = tables["Derived measures"]
    add_para(doc, "The following definitions are used for every derived measure "
             "reported in this document.", size=9.5, space_after=4)
    add_table(doc, header, rows, size=8)
    add_para(doc, "One row of the bookings table represents one passenger, not one "
             "reservation. Passengers on the same PNR share booking level fields "
             "such as train, travel date, class and quota. Derived measures used "
             "throughout this report are defined as follows: bookings are the "
             "count of distinct PNR, passengers are the row count, gross revenue "
             "is the sum of fare, refunds are the sum of refund amount, and net "
             "revenue is gross revenue minus refunds. Average fare is gross "
             "revenue divided by passengers. Cancellation rate, waitlist share, "
             "confirmation rate and late percentage are percentages computed with "
             "case expressions inside the SQL.", space_after=10)
    add_para(doc, "The generated dataset in this build contains %s stations, %s "
             "trains and %s passenger rows covering the period %s."
             % (num(a["meta"]["stations"]), num(a["meta"]["trains"]),
                num(a["meta"]["bookings"]), a["meta"]["period"]),
             space_after=10)
    page_break(doc)


def build_hive_design(doc):
    add_heading(doc, "7. Hive Database Design", level=1)
    add_para(doc, "The Hive warehouse is specified in the sql/ddl/ files for the "
             "railway_analytics database. The design separates raw staging from "
             "curated analytical tables. Staging tables are text tables with a "
             "single string type per column so that CSV loading never fails on "
             "type conversion. Typed dimension tables and the fact table are stored "
             "in ORC. The fact table is dynamically partitioned by travel month. The "
             "DDL was not executed in this build; the results in Section 9 were "
             "produced with DuckDB 1.1.3.", space_after=8)
    add_heading(doc, "7.1 Star like schema", level=2)
    add_code(doc,
             "                    +----------------+\n"
             "                    |    stations    |\n"
             "                    | station_code PK|\n"
             "                    +--------+-------+\n"
             "                             |\n"
             "   +--------------+    +------+-------+    +---------------+\n"
             "   | train_stops  |----|   bookings   |----|    trains     |\n"
             "   | train_number |    | FACT TABLE   |    | train_number  |\n"
             "   | stop_seq     |    | pnr, class,  |    | type, zone,   |\n"
             "   | station_code |    | fare, quota, |    | distance,     |\n"
             "   +--------------+    | status, delay|    | class flags   |\n"
             "                       +--------------+    +---------------+\n"
             "                    partitioned by travel_month",
             size=8)
    add_para(doc, "The bookings table is the fact table. It holds the measurable "
             "events, one per passenger, together with foreign key like columns "
             "such as train number, station codes and travel month. The stations, "
             "trains and train_stops tables are dimensions that describe those keys. "
             "At query time the analysis SQL reads the denormalised columns carried "
             "on the fact row, which avoids a join in every query and keeps the "
             "statements portable to DuckDB. The train_stops table supports route "
             "and schedule context but is not required by the fourteen aggregate "
             "queries.", space_after=10)
    add_heading(doc, "7.2 Database and staging tables", level=2)
    add_code(doc, read_text(os.path.join(DDL_DIR, "00_database.hql")), size=8)
    add_code(doc, read_text(os.path.join(DDL_DIR, "01_staging_tables.hql")), size=7.5)
    add_code(doc, read_text(os.path.join(DDL_DIR, "02_load_staging.hql")), size=8)
    add_heading(doc, "7.3 Typed dimension tables", level=2)
    add_code(doc, read_text(os.path.join(DDL_DIR, "03_dimensions.hql")), size=7.5)
    add_heading(doc, "7.4 Partitioned ORC fact table", level=2)
    add_code(doc, read_text(os.path.join(DDL_DIR, "04_bookings_partitioned.hql")), size=7.5)
    add_para(doc, "The partition column travel_month is declared after the regular "
             "columns and is supplied last in the select. Dynamic partition mode "
             "is set to nonstrict and the maximum partition count is raised to "
             "500 so that all twenty four months can be created in a single insert. "
             "The ORC format gives column level compression and lets the analysis "
             "queries read only the columns they need.", space_after=10)
    page_break(doc)


def build_queries(doc, a):
    add_heading(doc, "8. Query Implementation", level=1)
    add_para(doc, "This section documents all fourteen analysis queries. Each "
             "subsection gives the query identifier and title, its objective, the "
             "exact SQL read from sql/analysis/, and a result summary based on the "
             "tab separated output in data/results/. The result files were produced "
             "with DuckDB 1.1.3; the Hive path is the documented optional route and "
             "was not executed in this build. For result sets with many "
             "rows, the five leading rows are shown.", space_after=10)
    for idx, (stem, title, objective) in enumerate(QUERIES, start=1):
        add_heading(doc, "8.%d %s - %s" % (idx, stem, title), level=2)
        add_para(doc, "Objective. " + objective, space_after=6)
        add_para(doc, "SQL (source: sql/analysis/%s.sql):" % stem,
                 size=9.5, bold=True, space_after=2)
        add_code(doc, read_text(os.path.join(SQL_DIR, stem + ".sql")), size=7.5)
        rows = read_tsv(stem)
        add_para(doc, "Result summary. " + query_insight(stem, a, rows),
                 space_after=6)
        add_para(doc, "The query returned %d row%s. The leading row%s of the "
                 "tab separated output are shown below."
                 % (len(rows), "" if len(rows) == 1 else "s",
                    "" if len(rows) == 1 else "s"),
                 size=9.5, space_after=4)
        headers = RESULTS[stem]
        shown = rows[:5]
        add_table(doc, headers, shown, size=7.5)
    page_break(doc)


def build_results(doc, a, charts):
    add_heading(doc, "9. Results and Analysis", level=1)
    k = a["kpis"]
    add_heading(doc, "9.1 Headline indicators", level=2)
    add_para(doc, "The table below reports the headline indicators computed by "
             "query q01_kpis. All money values are in Indian Rupees and all "
             "percentages are rounded to two decimal places.", space_after=8)
    kpi_labels = [
        ("Total bookings (distinct PNR)", num(k["total_bookings"])),
        ("Total passengers", num(k["total_passengers"])),
        ("Gross revenue", money(k["gross_revenue"])),
        ("Refunds", money(k["refunds"])),
        ("Net revenue", money(k["net_revenue"])),
        ("Average fare", money(k["avg_fare"])),
        ("Cancellation rate", pct(k["cancellation_rate"])),
        ("Waitlist share", pct(k["waitlist_share"])),
        ("Average delay (minutes)", "%.2f" % k["avg_delay_minutes"]),
        ("Average distance (km)", "%.2f" % k["avg_distance_km"]),
        ("Confirmed share", pct(k["confirmed_share"])),
    ]
    add_table(doc, ["Measure", "Value"], kpi_labels, size=9)
    add_para(doc, "The dataset records %s distinct reservations carrying %s "
             "passengers. Gross revenue of %s is reduced by refunds of %s to give "
             "net revenue of %s. A confirmed share of %s and a waitlist share of "
             "%s indicate that most reservations are confirmed at the final state, "
             "while roughly one in six passenger rows began on a waitlist."
             % (num(k["total_bookings"]), num(k["total_passengers"]),
                money(k["gross_revenue"]), money(k["refunds"]),
                money(k["net_revenue"]), pct(k["confirmed_share"]),
                pct(k["waitlist_share"])), space_after=10)

    monthly = a["monthly"]
    peak = max(monthly, key=lambda r: r["revenue"])
    low = min(monthly, key=lambda r: r["revenue"])
    peakb = max(monthly, key=lambda r: r["bookings"])
    add_heading(doc, "9.2 Monthly bookings and revenue trend", level=2)
    add_picture(doc, charts["monthly"])
    add_para(doc, "The monthly series covers %d travel months from %s to %s. "
             "Revenue peaks in %s at %s from %s bookings, while the lowest month "
             "is %s at %s. Booking volume follows a similar seasonal shape and "
             "reaches its maximum in %s with %s distinct reservations. The pattern "
             "suggests stronger demand in the summer and year end travel windows."
             % (len(monthly), monthly[0]["month"], monthly[-1]["month"],
                peak["month"], money(peak["revenue"]), num(peak["bookings"]),
                low["month"], money(low["revenue"]), peakb["month"],
                num(peakb["bookings"])), space_after=10)

    cr = a["class_revenue"]
    add_heading(doc, "9.3 Revenue by class", level=2)
    add_picture(doc, charts["class"])
    add_para(doc, "Class %s generates the largest revenue at %s, which is %s of "
             "the gross total, followed by class %s at %s. Although class SL has "
             "the highest passenger count, its lower average fare of %s places it "
             "third by revenue at %s. Premium classes therefore contribute "
             "disproportionately to earnings because of their higher per passenger "
             "fare."
             % (cr[0]["travel_class"], money(cr[0]["revenue"]),
                pct(cr[0]["share_pct"]), cr[1]["travel_class"],
                money(cr[1]["revenue"]), money([r for r in cr if r["travel_class"] == "SL"][0]["avg_fare"]),
                money([r for r in cr if r["travel_class"] == "SL"][0]["revenue"])),
             space_after=10)

    qr = a["quota_revenue"]
    add_heading(doc, "9.4 Revenue by quota", level=2)
    add_picture(doc, charts["quota"])
    add_para(doc, "The general quota GN accounts for %s bookings and %s of revenue, "
             "far ahead of the next quota %s at %s. The average fare is broadly "
             "similar across quotas, ranging from %s for %s to %s for %s. Revenue "
             "differences between quotas are therefore driven mainly by booking "
             "volume rather than by fare."
             % (num(qr[0]["bookings"]), money(qr[0]["revenue"]),
                qr[1]["quota"], money(qr[1]["revenue"]),
                money(min(qr, key=lambda r: r["avg_fare"])["avg_fare"]),
                min(qr, key=lambda r: r["avg_fare"])["quota"],
                money(max(qr, key=lambda r: r["avg_fare"])["avg_fare"]),
                max(qr, key=lambda r: r["avg_fare"])["quota"]),
             space_after=10)

    pay = a["payments"]
    add_heading(doc, "9.5 Payment modes", level=2)
    add_picture(doc, charts["payments"])
    add_para(doc, "UPI leads with %s bookings and %s of revenue, representing the "
             "largest single settlement channel. Card is second with %s bookings "
             "and %s, while Cash is the smallest mode with %s bookings. The "
             "distribution reflects the wider shift toward digital payments in "
             "ticket booking."
             % (num(pay[0]["bookings"]), money(pay[0]["revenue"]),
                num(pay[1]["bookings"]), money(pay[1]["revenue"]),
                num(pay[-1]["bookings"])), space_after=10)

    ch = a["channels"]
    add_heading(doc, "9.6 Booking channels", level=2)
    add_picture(doc, charts["channels"])
    add_para(doc, "The App channel contributes %s bookings and %s in revenue, "
             "which is more than the Web channel at %s bookings and %s. Counter "
             "and Agent together account for the remaining bookings. The channel "
             "mix shows that self service digital interfaces carry the majority "
             "of reservation activity in this dataset."
             % (num(ch[0]["bookings"]), money(ch[0]["revenue"]),
                num(ch[1]["bookings"]), money(ch[1]["revenue"])),
             space_after=10)

    st = a["status"]
    best = max(st, key=lambda r: r["confirmation_rate"])
    worst = min(st, key=lambda r: r["confirmation_rate"])
    add_heading(doc, "9.7 Booking status mix", level=2)
    add_picture(doc, charts["status"])
    add_para(doc, "Confirmation rates lie in a narrow band across the six travel "
             "classes, from %s in class %s down to %s in class %s. The overall "
             "confirmed share is %s and the average waitlist position among "
             "waitlisted rows is about %d. Class SL carries the largest number of "
             "cancelled rows at %s, which is consistent with it having the largest "
             "passenger base."
             % (pct(best["confirmation_rate"]), best["travel_class"],
                pct(worst["confirmation_rate"]), worst["travel_class"],
                pct(k["confirmed_share"]),
                round(sum(r["avg_waitlist_position"] for r in st) / len(st)),
                num([r for r in st if r["travel_class"] == "SL"][0]["cancelled"])),
             space_after=10)

    reasons = a["cancel_reasons"]
    total_cancel = sum(r["count"] for r in reasons)
    add_heading(doc, "9.8 Cancellation reasons", level=2)
    add_picture(doc, charts["reasons"])
    add_para(doc, "Across %s cancelled passenger rows, the most frequent reason is "
             "%s with %s cases, or %s of cancellations. Medical emergency and "
             "Train cancelled follow with %s and %s cases respectively. Passenger "
             "plan change alone accounts for more than a third of all "
             "cancellations, indicating that voluntary changes dominate over "
             "railway side disruptions."
             % (num(total_cancel), reasons[0]["reason"], num(reasons[0]["count"]),
                pct(100.0 * reasons[0]["count"] / total_cancel),
                num(reasons[1]["count"]), num(reasons[2]["count"])),
             space_after=10)

    dt = a["delay_by_type"]
    dmax = max(dt, key=lambda r: r["avg_delay"])
    dmin = min(dt, key=lambda r: r["avg_delay"])
    exp_row = next((r for r in dt if r["train_type"] == "Exp"), None)
    sf_row = next((r for r in dt if r["train_type"] == "SF"), None)
    add_heading(doc, "9.9 Delay by train type", level=2)
    add_picture(doc, charts["delay_type"])
    add_para(doc, "Among train types, %s has the highest average delay at %.2f "
             "minutes and a late percentage of %s, while %s has the lowest at "
             "%.2f minutes. Express services carry most passenger rows at "
             "%.2f minutes and Superfast services run below the overall average "
             "at %.2f minutes. "
             "The spread between service types suggests that slower passenger "
             "services experience more delay than premium services."
             % (dmax["train_type"], dmax["avg_delay"], pct(dmax["late_pct"]),
                dmin["train_type"], dmin["avg_delay"],
                exp_row["avg_delay"] if exp_row else 0.0,
                sf_row["avg_delay"] if sf_row else 0.0),
             space_after=10)

    dz = a["delay_by_zone"]
    zmax = max(dz, key=lambda r: r["avg_delay"])
    zmin = min(dz, key=lambda r: r["avg_delay"])
    add_heading(doc, "9.10 Delay by zone", level=2)
    add_picture(doc, charts["delay_zone"])
    add_para(doc, "Zone %s records the highest average delay at %.2f minutes over "
             "%s bookings, whereas zone %s records the lowest at %.2f minutes. "
             "The busiest zones, including SR, NR and WR, remain close to the "
             "overall average of %.2f minutes. Differences between zones are "
             "modest compared with the seasonal variation shown in the next "
             "sections."
             % (zmax["zone"], zmax["avg_delay"], num(zmax["bookings"]),
                zmin["zone"], zmin["avg_delay"], k["avg_delay_minutes"]),
             space_after=10)

    rt = a["routes"]
    add_heading(doc, "9.11 Top routes", level=2)
    add_picture(doc, charts["routes"])
    add_para(doc, "The route ranking is long tailed: the leading pair %s, from %s "
             "to %s, records only %s bookings and %s of revenue. The next pairs "
             "are close behind, with the top ten routes each recording between "
             "%d and %d bookings. This indicates that bookings are spread across "
             "many station pairs rather than concentrated on a few trunk routes."
             % (rt[0]["route"], rt[0]["from_station"], rt[0]["to_station"],
                num(rt[0]["bookings"]), money(rt[0]["revenue"]),
                min(r["bookings"] for r in rt[:10]),
                max(r["bookings"] for r in rt[:10])), space_after=10)

    tr = a["trains"]
    add_heading(doc, "9.12 Top trains", level=2)
    add_picture(doc, charts["trains"])
    add_para(doc, "Train %s, %s, leads the revenue ranking with %s from %s "
             "bookings and an average delay of %.2f minutes. The second train, %s, "
             "earns %s. The top ten trains together show that long distance "
             "services across large station pairs generate the highest fares, "
             "with cancellation rates ranging from %s to %s among the leaders."
             % (tr[0]["train_number"], tr[0]["train_name"],
                money(tr[0]["revenue"]), num(tr[0]["bookings"]),
                tr[0]["avg_delay"], tr[1]["train_number"],
                money(tr[1]["revenue"]),
                pct(min(r["cancel_rate"] for r in tr[:10])),
                pct(max(r["cancel_rate"] for r in tr[:10]))),
             space_after=10)

    dm = a["delay_monthly"]
    dpeak = max(dm, key=lambda r: r["avg_delay"])
    dlow = min(dm, key=lambda r: r["avg_delay"])
    add_heading(doc, "9.13 Delay by month", level=2)
    add_picture(doc, charts["delay_monthly"])
    add_para(doc, "The monthly delay series shows a pronounced peak in %s, with "
             "%.2f minutes average delay and %s of rows more than fifteen minutes "
             "late. The lowest month is %s at %.2f minutes. Across the full period "
             "the late percentage ranges from %s to %s. The repeated rise in the "
             "middle of each calendar year points to a seasonal punctuality "
             "challenge that coincides with the monsoon travel period."
             % (dpeak["month"], dpeak["avg_delay"], pct(dpeak["late_pct"]),
                dlow["month"], dlow["avg_delay"],
                pct(min(r["late_pct"] for r in dm)),
                pct(max(r["late_pct"] for r in dm))),
             space_after=10)
    page_break(doc)


def build_conclusion(doc, a):
    add_heading(doc, "10. Conclusion", level=1)
    add_para(doc, "This project delivered an end to end analytical system for "
             "railway reservation data. The pipeline acquires public reference "
             "data, cleans it into three CSV dimensions, generates a 150000 row "
             "reservation fact table with a fixed seed, defines a Hive warehouse "
             "with staging tables, ORC dimensions and a dynamically partitioned "
             "fact table, and provides fourteen portable SQL queries. In this build "
             "the queries were executed on DuckDB 1.1.3, because Docker was not "
             "available, and the computed outputs were exported as result files and "
             "assembled into a JSON analytics payload. The Hive path is documented "
             "in Appendix A but was not executed in this build.",
             space_after=10)
    add_para(doc, "The analysis produced a coherent picture of the dataset. Gross "
             "revenue of %s and net revenue of %s were measured alongside a "
             "confirmed share of %s, a cancellation rate of %s and an average "
             "delay of %.2f minutes. Third AC class is the largest revenue "
             "contributor, the general quota dominates volume, UPI and the App "
             "channel lead their respective categories, cancellations are mostly "
             "driven by passenger plan changes, and delays peak during the middle "
             "months of each year. These findings were derived directly from the "
             "executed queries and are reproduced in the charts of Section 9."
             % (money(a["kpis"]["gross_revenue"]),
                money(a["kpis"]["net_revenue"]),
                pct(a["kpis"]["confirmed_share"]),
                pct(a["kpis"]["cancellation_rate"]),
                a["kpis"]["avg_delay_minutes"]), space_after=10)
    add_para(doc, "The project also illustrates good engineering practice for a "
             "data analytics coursework submission. The SQL is portable, the "
             "warehouse design uses columnar storage and partitioning, results are cached "
             "as JSON and SQLite for fast presentation, and the website can be "
             "exported as a static folder. The report generator itself reads the "
             "computed artefacts, so the written figures always match the "
             "pipeline output. The reporting objectives stated in Section 2 have been "
             "met on the DuckDB execution path; the Hive warehouse load remains the "
             "documented optional path and was not executed in this build.", space_after=10)
    page_break(doc)


def build_future(doc):
    add_heading(doc, "11. Limitations and Future Scope", level=1)
    add_heading(doc, "11.1 Limitations", level=2)
    add_bullet(doc, "The reservation fact table is synthetic. It follows realistic distributions but is not a record of actual passenger bookings.")
    add_bullet(doc, "The analysis is descriptive and does not build predictive or causal models.")
    add_bullet(doc, "Fares are generated from a formula and do not capture dynamic pricing, taxes or state specific subsidies.")
    add_bullet(doc, "Delay is generated per train and date and does not model propagation along the route.")
    add_bullet(doc, "Route rankings are based on sparse station pairs, so the leading routes have small booking counts.")
    add_bullet(doc, "The website reads precomputed results, so it does not reflect live changes until the pipeline is run again.")
    add_bullet(doc, "The Hive path requires Docker and a first time image download, which may be slow on constrained machines.")
    add_bullet(doc, "The Hive path has not been executed end to end on this machine, so Hive specific behaviour such as dynamic partitioning and ORC loading is unverified. All reported figures were produced with DuckDB 1.1.3.")
    add_heading(doc, "11.2 Future scope", level=2)
    add_bullet(doc, "Add a supervised model to estimate the probability of confirmation from class, quota and lead time.")
    add_bullet(doc, "Introduce a time series forecast of monthly demand and revenue using the twenty four month history.")
    add_bullet(doc, "Extend the star schema with a date dimension and a passenger profile dimension.")
    add_bullet(doc, "Load real open timetable changes and compare planned versus observed schedules where data is available.")
    add_bullet(doc, "Add map based visualisation of routes using the station latitude and longitude columns.")
    add_bullet(doc, "Move the scheduled pipeline to a workflow orchestrator and publish refreshed results automatically.")
    add_bullet(doc, "Add role based access and a query builder so that new analyses can be defined without editing SQL files.")
    add_para(doc, "These extensions would build on the existing warehouse and SQL "
             "layer without changing the core data model. Because the result "
             "contract fixes column names and order, new analyses can be added as "
             "additional query files while preserving the current website and "
             "report.", space_after=10)
    page_break(doc)


def build_references(doc):
    add_heading(doc, "12. References", level=1)
    add_para(doc, "All sources below are public and were consulted for this "
             "project. The URLs are given in full.", space_after=8)
    refs = [
        ("Apache Hive - official documentation", "https://hive.apache.org/"),
        ("Apache Hadoop - official site", "https://hadoop.apache.org/"),
        ("Apache Hive language manual", "https://cwiki.apache.org/confluence/display/Hive/LanguageManual"),
        ("DuckDB - official documentation", "https://duckdb.org/docs/"),
        ("Flask - official documentation", "https://flask.palletsprojects.com/"),
        ("Jinja2 - official documentation", "https://jinja.palletsprojects.com/"),
        ("Bootstrap 5 - official documentation", "https://getbootstrap.com/docs/5.3/"),
        ("Chart.js - official documentation", "https://www.chartjs.org/docs/latest/"),
        ("Python - official site", "https://www.python.org/"),
        ("DataMeet railways reference data (CC0)", "https://github.com/datameet/railways"),
        ("matplotlib - official documentation", "https://matplotlib.org/stable/"),
        ("python-docx - official documentation", "https://python-docx.readthedocs.io/"),
        ("SQLite - official site", "https://www.sqlite.org/index.html"),
        ("GitHub Pages - official documentation", "https://docs.github.com/en/pages"),
        ("Netlify - official site", "https://www.netlify.com/"),
        ("Render - official site", "https://render.com/"),
    ]
    for i, (label, url) in enumerate(refs, start=1):
        p = doc.add_paragraph()
        set_run_font(p.add_run("[%d] %s. " % (i, ascii_safe(label))), size=10)
        set_run_font(p.add_run(url), size=10)
        p.paragraph_format.space_after = Pt(3)
    page_break(doc)


def build_appendix(doc):
    add_heading(doc, "Appendix A. How to Run the Project", level=1)
    add_para(doc, "Open PowerShell in the project folder and use the virtual "
             "environment. The commands below reproduce the full pipeline and "
             "then rebuild this report.", space_after=8)
    add_heading(doc, "A.1 Setup", level=2)
    add_code(doc,
             "py -m venv .venv\n"
             ".\\.venv\\Scripts\\Activate.ps1\n"
             "python -m pip install --upgrade pip\n"
             "pip install -r requirements.txt",
             size=8.5)
    add_heading(doc, "A.2 Prepare the data", level=2)
    add_code(doc,
             "python scripts\\download_reference.py\n"
             "python scripts\\build_reference.py\n"
             "python scripts\\generate_bookings.py",
             size=8.5)
    add_heading(doc, "A.3 Run the analysis", level=2)
    add_para(doc, "Option A uses Apache Hive in Docker. Option B uses DuckDB and "
             "needs only Python. Both are designed to write the same fourteen result files. "
             "For this build, only Option B was run; the Hive option is documented "
             "but unverified.",
             space_after=6)
    add_code(doc,
             "# Option A: Apache Hive\n"
             "docker compose up -d\n"
             "python scripts\\run_hive.py\n\n"
             "# Option B: DuckDB, no Docker\n"
             "python scripts\\run_local.py",
             size=8.5)
    add_heading(doc, "A.4 Build and view the website", level=2)
    add_code(doc,
             "python scripts\\build_site_data.py\n"
             "python website\\app.py\n"
             "# open http://localhost:5000",
             size=8.5)
    add_heading(doc, "A.5 Export a static site", level=2)
    add_code(doc,
             "python scripts\\export_static.py\n"
             "# upload the dist folder to any static host",
             size=8.5)
    add_heading(doc, "A.6 Rebuild this report", level=2)
    add_code(doc,
             "python scripts\\make_report.py\n"
             "# writes report\\report.docx and the chart PNG files",
             size=8.5)
    add_para(doc, "Replace the placeholders on the title page and certificate page "
             "with your own details before final submission.", space_after=10)


# --------------------------------------------------------------------------
# Validation
# --------------------------------------------------------------------------
FORBIDDEN_CHARS = ["\u2014", "\u2013", "\u2018", "\u2019", "\u201c", "\u201d"]
WORD_RE = re.compile(r"demo", re.IGNORECASE)


def validate_document(doc):
    problems = []

    def check(text, where):
        for ch in FORBIDDEN_CHARS:
            if ch in text:
                problems.append("%s: forbidden character U+%04X" % (where, ord(ch)))
        for ch in text:
            if ord(ch) > 127:
                problems.append("%s: non ASCII character U+%04X" % (where, ord(ch)))
                break
        if WORD_RE.search(text):
            problems.append("%s: forbidden word found" % where)

    for i, p in enumerate(doc.paragraphs):
        check(p.text, "paragraph %d" % i)
    for ti, table in enumerate(doc.tables):
        for ri, row in enumerate(table.rows):
            for ci, cell in enumerate(row.cells):
                check(cell.text, "table %d cell %d,%d" % (ti, ri, ci))
    cp = doc.core_properties
    for name in ("title", "author", "subject", "keywords"):
        check(str(getattr(cp, name, "")), "core property %s" % name)
    if problems:
        raise AssertionError("Document validation failed:\n" + "\n".join(problems[:20]))


# --------------------------------------------------------------------------
# Main
# --------------------------------------------------------------------------
def main():
    a = load_analytics()
    charts = build_charts(a)

    doc = Document()
    style = doc.styles["Normal"]
    style.font.name = "Calibri"
    style.font.size = Pt(10.5)

    build_title_page(doc)
    build_certificate(doc)
    build_abstract(doc, a)
    build_acknowledgements(doc)
    build_toc(doc)
    build_intro(doc, a)
    build_objectives(doc)
    build_literature(doc)
    build_requirements(doc)
    build_methodology(doc, a["meta"]["engine"])
    build_data_description(doc, a)
    build_hive_design(doc)
    build_queries(doc, a)
    build_results(doc, a, charts)
    build_conclusion(doc, a)
    build_future(doc)
    build_references(doc)
    build_appendix(doc)

    doc.core_properties.title = TITLE
    doc.core_properties.subject = SUBTITLE
    doc.core_properties.author = "[Student Name]"
    doc.core_properties.keywords = "Apache Hive; DuckDB; data warehouse; Indian Railways; SQL analytics"
    doc.core_properties.category = "Academic project report"

    validate_document(doc)

    os.makedirs(REPORT_DIR, exist_ok=True)
    doc.save(DOCX_PATH)

    size = os.path.getsize(DOCX_PATH)
    print("Wrote: " + DOCX_PATH)
    print("File size: %d bytes (%.1f KB)" % (size, size / 1024.0))
    print("Paragraphs: %d" % len(doc.paragraphs))
    print("Tables: %d" % len(doc.tables))
    print("Embedded charts: %d" % len(doc.inline_shapes))
    print("Validation: OK (ASCII only, no forbidden characters, no forbidden word)")
    assert size > 100000, "DOCX is unexpectedly small"


if __name__ == "__main__":
    main()
