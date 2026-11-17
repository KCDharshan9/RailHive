"""Run the portable analysis SQL on Hive 4.2.1 and write data/results.

Pipeline:
  1. make sure the hive4 container is owned by docker compose and is up
  2. wait for HiveServer2
  3. run sql/ddl/*.hql in file name order (load staging, dims, partitioned fact)
  4. run each sql/analysis/*.sql as INSERT OVERWRITE DIRECTORY into /tmp/results
  5. copy the part files back and concatenate them into data/results/qNN_name.tsv
  6. write data/results/_engine.txt

Standard library only. Use --skip-load to rerun only the queries.
"""

import argparse
import os
import pathlib
import re
import shutil
import subprocess
import sys
import time

ROOT = pathlib.Path(__file__).resolve().parents[1]
SCRIPTS = pathlib.Path(__file__).resolve().parent
DATA = ROOT / "data"
DEFAULT_RAW = DATA / "raw"
RESULTS = DATA / "results"
DDL_DIR = ROOT / "sql" / "ddl"
ANALYSIS_DIR = ROOT / "sql" / "analysis"
TMP_DIR = ROOT / ".tmp" / "hive_run"

CONTAINER = "hive4"
COMPOSE_PROJECT = "bda-project"
DATABASE = "railway_analytics"
HIVE_FALLBACK_VERSION = "4.2.1"
CONTAINER_RESULT_ROOT = "/tmp/results"
CONTAINER_SCRIPT = "/tmp/opencode_script.hql"
CONTAINER_FIXTURE_RAW = "/tmp/opencode_raw"

BEELINE_INNER = (
    "export HADOOP_CLIENT_OPTS='-Dorg.jline.terminal.dumb=true'; "
    "beeline -u 'jdbc:hive2://localhost:10000/' "
    "--silent=true --showHeader=false -f " + CONTAINER_SCRIPT
)

sys.path.insert(0, str(SCRIPTS))
try:
    from result_spec import RESULTS as RESULT_COLUMNS
except ImportError:  # pragma: no cover - only when copied elsewhere
    RESULT_COLUMNS = {}


def log(message):
    print("[hive] " + message, flush=True)


def fail(message):
    print("[hive] ERROR: " + message, file=sys.stderr, flush=True)
    raise SystemExit(1)


def shell(args, timeout=600, stdin_text=None, cwd=None):
    return subprocess.run(
        args,
        input=stdin_text,
        cwd=str(cwd) if cwd else None,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=timeout,
    )


# ---------------------------------------------------------------- docker setup

def docker_ready():
    probe = shell(["docker", "version", "--format", "{{.Server.Version}}"], timeout=60)
    return probe.returncode == 0 and probe.stdout.strip() != ""


def ensure_docker_daemon():
    if docker_ready():
        return
    log("docker daemon is not answering, trying to start Docker Desktop")
    candidates = [
        pathlib.Path(os.environ.get("ProgramFiles", r"C:\Program Files")) / "Docker" / "Docker" / "Docker Desktop.exe",
    ]
    started = False
    for exe in candidates:
        if exe.exists():
            subprocess.Popen([str(exe)])
            started = True
            break
    if not started:
        fail("Docker Desktop was not found. Start Docker manually and rerun.")
    deadline = time.time() + 180
    while time.time() < deadline:
        if docker_ready():
            log("docker daemon is up")
            return
        time.sleep(5)
    fail("docker daemon did not start within 180 seconds")


def container_exists():
    return shell(["docker", "inspect", CONTAINER], timeout=60).returncode == 0


def compose_label():
    probe = shell(
        ["docker", "inspect", "--format",
         '{{index .Config.Labels "com.docker.compose.project"}}', CONTAINER],
        timeout=60,
    )
    if probe.returncode != 0:
        return ""
    return probe.stdout.strip()


def remove_stale_container():
    if not container_exists():
        return
    label = compose_label()
    if label == COMPOSE_PROJECT:
        log("reusing compose managed container " + CONTAINER)
        return
    log("removing stale container " + CONTAINER + " (compose label: %r)" % label)
    removed = shell(["docker", "rm", "-f", CONTAINER], timeout=120)
    if removed.returncode != 0:
        fail("could not remove stale container: " + removed.stderr.strip())


def compose_up():
    log("docker compose up -d")
    up = shell(["docker", "compose", "up", "-d"], timeout=300, cwd=ROOT)
    if up.returncode != 0:
        fail("docker compose up failed:\n" + up.stdout + up.stderr)


# ------------------------------------------------------------------- beeline

def beeline_run(sql_text, label, timeout=1800):
    """Run SQL through beeline inside the container, feeding the script on stdin."""
    if not sql_text.rstrip().endswith(";"):
        sql_text = sql_text.rstrip() + ";\n"
    command = "cat > " + CONTAINER_SCRIPT + "; " + BEELINE_INNER
    try:
        proc = shell(
            ["docker", "exec", "-i", "-e", "TERM=dumb", CONTAINER, "sh", "-c", command],
            timeout=timeout,
            stdin_text=sql_text,
        )
    except subprocess.TimeoutExpired:
        fail(label + " timed out after %d seconds" % timeout)
    # stdout matters; stderr is full of SLF4J noise.
    if proc.stdout.strip():
        for line in proc.stdout.strip().splitlines():
            log("  " + line)
    if proc.returncode != 0:
        detail = proc.stderr.strip().splitlines()
        tail = "\n".join(detail[-25:]) if detail else "(no stderr)"
        fail(label + " failed with exit code %d:\n%s" % (proc.returncode, tail))
    return proc.stdout


def beeline_probe(sql_text, timeout=120):
    """Same as beeline_run but without failing, for the readiness loop."""
    if not sql_text.rstrip().endswith(";"):
        sql_text = sql_text.rstrip() + ";\n"
    try:
        return shell(
            ["docker", "exec", "-i", "-e", "TERM=dumb", CONTAINER, "sh", "-c", BEELINE_INNER],
            timeout=timeout,
            stdin_text=sql_text,
        )
    except subprocess.TimeoutExpired:
        return None


def wait_for_hive_server2(limit=180):
    log("waiting up to %d seconds for HiveServer2" % limit)
    deadline = time.time() + limit
    while time.time() < deadline:
        proc = beeline_probe("show databases;\n")
        if proc is not None and proc.returncode == 0 and "default" in proc.stdout:
            log("HiveServer2 is accepting queries")
            return
        time.sleep(5)
    fail("HiveServer2 did not answer SHOW DATABASES within %d seconds" % limit)


def hive_version():
    proc = shell(["docker", "exec", CONTAINER, "hive", "--version"], timeout=120)
    if proc.returncode == 0:
        match = re.search(r"(\d+\.\d+\.\d+)", proc.stdout)
        if match:
            return match.group(1)
    return HIVE_FALLBACK_VERSION


# ---------------------------------------------------------------------- loading

def prepare_raw_dir(raw_dir):
    """Return the path the container should read the CSV files from."""
    resolved = raw_dir.resolve()
    if resolved == DEFAULT_RAW.resolve():
        return "/data/raw"
    log("copying fixture raw dir into container: " + str(resolved))
    cleanup = shell(["docker", "exec", CONTAINER, "rm", "-rf", CONTAINER_FIXTURE_RAW], timeout=60)
    if cleanup.returncode != 0:
        fail("could not clear " + CONTAINER_FIXTURE_RAW)
    copied = shell(["docker", "cp", str(resolved), CONTAINER + ":" + CONTAINER_FIXTURE_RAW], timeout=300)
    if copied.returncode != 0:
        fail("docker cp of raw dir failed: " + copied.stderr.strip())
    return CONTAINER_FIXTURE_RAW


def run_ddl(container_raw):
    files = sorted(DDL_DIR.glob("*.hql"))
    if not files:
        fail("no DDL files found in " + str(DDL_DIR))
    for path in files:
        text = path.read_text(encoding="utf-8")
        if container_raw != "/data/raw":
            text = text.replace("/data/raw/", container_raw + "/")
        log("ddl " + path.name)
        started = time.time()
        beeline_run(text, "ddl " + path.name, timeout=1800)
        log("ddl " + path.name + " finished in %.1f s" % (time.time() - started))


# ---------------------------------------------------------------------- queries

def clear_results():
    RESULTS.mkdir(parents=True, exist_ok=True)
    for path in list(RESULTS.glob("*.tsv")) + list(RESULTS.glob("_engine.txt")):
        path.unlink()
    log("cleared old result files in " + str(RESULTS))


def analysis_files():
    files = sorted(ANALYSIS_DIR.glob("q*.sql"))
    if len(files) != 14:
        fail("expected 14 analysis files, found %d" % len(files))
    return files


def wrap_query(name, select_sql):
    target = CONTAINER_RESULT_ROOT + "/" + name
    select_sql = select_sql.strip().rstrip(";")
    return (
        "use " + DATABASE + ";\n"
        "insert overwrite directory '" + target + "'\n"
        "row format delimited fields terminated by '\\t'\n"
        "null defined as ''\n"
        + select_sql + ";\n"
    )


def fetch_result(name):
    """Copy the directory out of the container and concatenate part files."""
    host_dir = TMP_DIR / name
    if host_dir.exists():
        shutil.rmtree(host_dir)
    host_dir.mkdir(parents=True)
    copied = shell(
        ["docker", "cp", CONTAINER + ":" + CONTAINER_RESULT_ROOT + "/" + name, str(host_dir)],
        timeout=300,
    )
    if copied.returncode != 0:
        fail("docker cp failed for " + name + ": " + copied.stderr.strip())
    source = host_dir / name
    if source.is_dir():
        parts = sorted(
            path for path in source.iterdir()
            if path.is_file() and not path.name.endswith(".crc") and not path.name.startswith(".")
        )
    else:
        parts = [source]
    if not parts:
        fail("no part files produced for " + name)

    chunks = []
    for part in parts:
        text = part.read_text(encoding="utf-8", errors="replace")
        if text:
            chunks.append(text)
    body = "".join(chunks).replace("\r\n", "\n")
    lines = [line for line in body.split("\n") if line.strip() != ""]
    if not lines:
        fail("query produced an empty result: " + name)

    out_path = RESULTS / (name + ".tsv")
    out_path.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")

    expected = RESULT_COLUMNS.get(name)
    widths = set(len(line.split("\t")) for line in lines)
    if expected and widths != {len(expected)}:
        fail("%s expected %d columns, found widths %s" % (name, len(expected), sorted(widths)))
    return len(lines), len(expected) if expected else sorted(widths)[-1]


def run_queries():
    timings = []
    for path in analysis_files():
        name = path.stem
        select_sql = path.read_text(encoding="utf-8")
        log("query " + name)
        started = time.time()
        beeline_run(wrap_query(name, select_sql), "query " + name, timeout=900)
        rows, columns = fetch_result(name)
        elapsed = time.time() - started
        timings.append((name, rows, columns, elapsed))
        log("query %s ok: %d rows, %d columns, %.1f s" % (name, rows, columns, elapsed))
    return timings


# ------------------------------------------------------------------------- main

def main():
    parser = argparse.ArgumentParser(description="Run the analysis SQL on Hive.")
    parser.add_argument("--skip-load", action="store_true",
                        help="skip docker compose start and DDL, only rerun the queries")
    parser.add_argument("--raw-dir", default=str(DEFAULT_RAW),
                        help="directory holding stations/trains/train_stops/bookings CSV")
    args = parser.parse_args()

    raw_dir = pathlib.Path(args.raw_dir)
    if not (raw_dir / "bookings.csv").exists():
        fail("missing " + str(raw_dir / "bookings.csv"))

    ensure_docker_daemon()
    remove_stale_container()

    container_raw = "/data/raw"
    if args.skip_load:
        log("--skip-load: leaving existing tables untouched")
    else:
        compose_up()
        wait_for_hive_server2()
        container_raw = prepare_raw_dir(raw_dir)
        run_ddl(container_raw)

    clear_results()
    timings = run_queries()

    version = hive_version()
    (RESULTS / "_engine.txt").write_text("hive " + version + "\n", encoding="utf-8", newline="\n")
    log("_engine.txt written: hive " + version)

    log("done, %d result files" % len(timings))
    for name, rows, columns, elapsed in timings:
        log("  %-22s %7d rows %2d cols %6.1f s" % (name, rows, columns, elapsed))


if __name__ == "__main__":
    main()
