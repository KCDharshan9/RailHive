"""Run the portable analysis SQL on DuckDB and write data/results.

The CSV files are exposed as views named bookings, trains, stations and
train_stops. Every column is read as VARCHAR so the view has the same string
semantics as the Hive staging tables; the analysis SQL does its own casts.
"""

import argparse
import pathlib
import sys
import time

import duckdb

ROOT = pathlib.Path(__file__).resolve().parents[1]
SCRIPTS = pathlib.Path(__file__).resolve().parent
DEFAULT_RAW = ROOT / "data" / "raw"
RESULTS = ROOT / "data" / "results"
ANALYSIS_DIR = ROOT / "sql" / "analysis"

sys.path.insert(0, str(SCRIPTS))
try:
    from result_spec import RESULTS as RESULT_COLUMNS
except ImportError:  # pragma: no cover - only when copied elsewhere
    RESULT_COLUMNS = {}

VIEW_SOURCES = {
    "bookings": "bookings.csv",
    "trains": "trains.csv",
    "stations": "stations.csv",
    "train_stops": "train_stops.csv",
}


def log(message):
    print("[duckdb] " + message, flush=True)


def fail(message):
    print("[duckdb] ERROR: " + message, file=sys.stderr, flush=True)
    raise SystemExit(1)


def sql_string(value):
    return "'" + str(value).replace("\\", "/").replace("'", "''") + "'"


def clear_results():
    RESULTS.mkdir(parents=True, exist_ok=True)
    for path in list(RESULTS.glob("*.tsv")) + list(RESULTS.glob("_engine.txt")):
        path.unlink()
    log("cleared old result files in " + str(RESULTS))


def create_views(con, raw_dir):
    for view, filename in VIEW_SOURCES.items():
        path = raw_dir / filename
        if not path.exists():
            fail("missing input " + str(path))
        con.execute(
            "create or replace view " + view + " as "
            "select * from read_csv(" + sql_string(path) + ", header=true, all_varchar=true)"
        )
        count = con.execute("select count(*) from " + view).fetchone()[0]
        log("view %-11s %7d rows  <- %s" % (view, count, filename))


def analysis_files():
    files = sorted(ANALYSIS_DIR.glob("q*.sql"))
    if len(files) != 14:
        fail("expected 14 analysis files, found %d" % len(files))
    return files


def run_queries(con):
    results = []
    languages = []
    for path in analysis_files():
        name = path.stem
        select_sql = path.read_text(encoding="utf-8").strip().rstrip(";")
        out_path = (RESULTS / (name + ".tsv")).resolve()
        # Empty QUOTE/ESCAPE keeps values unquoted. The contract guarantees no
        # tabs or newlines inside fields. NULL is written as an empty string.
        copy_sql = (
            "copy (\n" + select_sql + "\n) to " + sql_string(out_path) +
            " (format csv, header false, delimiter '\\t', quote '', escape '')"
        )
        log("query " + name)
        started = time.time()
        try:
            con.execute(copy_sql)
        except Exception as exc:
            fail(name + " failed: " + type(exc).__name__ + ": " + str(exc))
        elapsed = time.time() - started

        text = out_path.read_text(encoding="utf-8", errors="replace")
        lines = [line for line in text.replace("\r\n", "\n").split("\n") if line.strip() != ""]
        if not lines:
            fail("query produced an empty result: " + name)
        expected = RESULT_COLUMNS.get(name)
        widths = set(len(line.split("\t")) for line in lines)
        if expected and widths != {len(expected)}:
            fail("%s expected %d columns, found widths %s" % (name, len(expected), sorted(widths)))
        columns = len(expected) if expected else sorted(widths)[-1]
        results.append((name, len(lines), columns, elapsed))
        log("query %s ok: %d rows, %d columns, %.1f s" % (name, len(lines), columns, elapsed))
    return results


def main():
    parser = argparse.ArgumentParser(description="Run the analysis SQL on DuckDB.")
    parser.add_argument("--raw-dir", default=str(DEFAULT_RAW),
                        help="directory holding stations/trains/train_stops/bookings CSV")
    args = parser.parse_args()

    raw_dir = pathlib.Path(args.raw_dir)
    if not (raw_dir / "bookings.csv").exists():
        fail("missing " + str(raw_dir / "bookings.csv"))

    started = time.time()
    clear_results()
    con = duckdb.connect()
    create_views(con, raw_dir)
    results = run_queries(con)
    con.close()

    version = duckdb.__version__
    (RESULTS / "_engine.txt").write_text("duckdb " + version + "\n", encoding="utf-8", newline="\n")
    log("_engine.txt written: duckdb " + version)
    log("done in %.1f s, %d result files" % (time.time() - started, len(results)))
    for name, rows, columns, elapsed in results:
        log("  %-22s %7d rows %2d cols %6.1f s" % (name, rows, columns, elapsed))


if __name__ == "__main__":
    main()
