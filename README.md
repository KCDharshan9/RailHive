# Railway Reservation Analytics

Railway Reservation Analytics analyses Indian Railways reservation data and
presents the results in a Flask website. It uses real public railway reference
data from DataMeet (CC0) for stations, trains and schedules, and generates a
reproducible set of reservation records with a fixed seed because passenger
level booking data is not published as open data. The same set of SQL queries
is designed to run on Apache Hive or, without Docker, on DuckDB. The committed
results in data/results/ were produced with DuckDB 1.1.3; the Hive path is the
documented optional route and has not been executed on this machine (Docker is
not installed here).

## How to run the website

This is the main way to run the project. It needs only Python. Run every
command from the project folder.

### A. Local Flask run (main way)

Step 1: create the virtual environment and install the packages.

Windows PowerShell:

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

If PowerShell refuses to activate the environment, run this once and then
repeat the Activate.ps1 line:

```powershell
Set-ExecutionPolicy -Scope Process Bypass
```

Linux / macOS (same steps, different commands):

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

Step 2: run the data preparation and analysis steps in this exact order.

Windows PowerShell:

```powershell
.\.venv\Scripts\python.exe scripts\download_reference.py
.\.venv\Scripts\python.exe scripts\build_reference.py
.\.venv\Scripts\python.exe scripts\generate_bookings.py
.\.venv\Scripts\python.exe scripts\run_local.py
.\.venv\Scripts\python.exe scripts\build_site_data.py
```

Linux / macOS:

```bash
python scripts/download_reference.py
python scripts/build_reference.py
python scripts/generate_bookings.py
python scripts/run_local.py
python scripts/build_site_data.py
```

download_reference.py fetches the DataMeet JSON. build_reference.py writes the
cleaned CSV files. generate_bookings.py writes 150,000 seeded passenger rows.
run_local.py executes the 14 analysis queries with DuckDB and writes one TSV
per query to data/results/. build_site_data.py validates those results and
builds website/data/analytics.json, the explorer sample and the SQLite
database.

Step 3: start the website.

Windows PowerShell:

```powershell
.\.venv\Scripts\python.exe website\app.py
```

Linux / macOS:

```bash
python website/app.py
```

Open http://127.0.0.1:5000 in a browser. Stop the server with Ctrl+C.

### B. Optional Hive run

This alternative needs Docker Desktop (at least 4 GB of memory and 4 GB of free
disk). The DuckDB path in section A needs only Python. The Hive path is
designed to load the same CSV files into ORC tables partitioned by travel
month and to run the same SQL; it has not been executed on this machine.

Run the data preparation first (download_reference.py, build_reference.py and
generate_bookings.py from Step 2), then:

```powershell
docker compose up -d
.\.venv\Scripts\python.exe scripts\run_hive.py
.\.venv\Scripts\python.exe scripts\build_site_data.py
```

The first start pulls the Hive image, so it takes longer. Later runs reuse the
container. Both engines write the same 14 result files, and build_site_data.py
finishes the website data either way. Start the website as in Step 3.

Note: the Hive path has not been executed end to end on this machine (Docker
is not installed here), so it remains unverified. The committed results were
produced with DuckDB via section A.

## How to deploy

The simplest deployment has no server at all:

```powershell
.\.venv\Scripts\python.exe scripts\export_static.py
```

This writes a complete static site to dist/. Upload the contents of dist/ to
Netlify Drop, GitHub Pages or any static file host. It is free and needs no
runtime, database or Python on the host. The exported explorer filters an
embedded 5,000 row sample in the browser.

An optional way to host the live Flask app is Render. The repository includes
render.yaml; it runs the DuckDB pipeline during the build and starts the app
with gunicorn. Connect the repository to Render and use that file as the
service definition.

## Project structure

```
data/reference/    downloaded DataMeet JSON
data/raw/          cleaned CSV inputs and generated bookings
data/results/      one TSV per analysis query
data/processed/    SQLite database and built artefacts
sql/ddl/           Hive database and table definitions
sql/analysis/      portable SELECT statements, q01 to q14
scripts/           data pipeline, runners, site builder, export, report
website/           Flask app, templates, static assets and site data
docs/              contract, architecture and data dictionary
report/            report images and generated document
dist/              exported static site (generated)
```

## Technology

| Layer | Tool |
| --- | --- |
| Warehouse design (optional path) | Apache Hive 4.2.1, Hadoop 3.4.1, Docker |
| Query engine used for the committed results | DuckDB 1.1.3 |
| Data preparation | Python 3.10 standard library |
| Website | Flask 3.0, Jinja2, Bootstrap 5.3, Chart.js 4.4 |
| Local database | SQLite |
| Static hosting | any static file host, for example Netlify or GitHub Pages |
| Report | python-docx, matplotlib |
| Production Flask host (optional) | gunicorn on Render |

Everything is free and open source. No API keys and no paid services are
needed.

## Requirements

- Python 3.10 or newer.
- Docker Desktop with at least 4 GB of memory and 4 GB of free disk, only for
  the optional Hive path.
- Java 17 or newer, only if you run Hive outside Docker.
- Windows, Linux or macOS.

The DuckDB path (section A) needs only Python.

## Data and licence

- Station, train and schedule data: DataMeet railways, CC0.
  https://github.com/datameet/railways
- Reservation records: generated for this project with a fixed seed of 42.
  Every booking uses a real train, a real station pair from that train's
  schedule and a class the train supports.
- Code in this repository: free to use for academic work.

## Report generation

```powershell
.\.venv\Scripts\python.exe scripts\make_report.py
```

This builds report/report.docx from the analysis results and 12 chart images.
It reads the real numbers from website/data/analytics.json, so run the data
steps first. Fill in the placeholders on the title page before submission.

## Troubleshooting

**PowerShell will not activate the venv.** Run
`Set-ExecutionPolicy -Scope Process Bypass` and repeat the Activate.ps1 line.
You can always call the interpreter directly as `.\.venv\Scripts\python.exe`
without activating.

**Port 5000 is already in use.** Stop the other program that is listening on
port 5000, then start the website again. If you cannot stop it, change the port
in the `app.run` call at the bottom of website/app.py and open that port.

**The website shows no data or stale data.** Run the data steps in order
(download_reference.py through build_site_data.py) and confirm that
website/data/analytics.json exists.

**Missing data files.** Re-run build_reference.py if the data/raw CSV files are
missing, generate_bookings.py if bookings.csv is missing, and run_local.py if
the data/results TSV files are missing. Then run build_site_data.py again.

**Charts are blank.** The tables still work. Confirm that JavaScript is
enabled and that website/static/vendor/chart.umd.min.js exists.

**Docker is not running.** Start Docker Desktop and wait for it to be ready,
then run `docker compose up -d` again.

## Notes

- All amounts are in Indian Rupees.
- The generated data is for analysis practice and coursework, not for real
  travel decisions.
- The SQL is deliberately portable: the same statement is designed to run on
  Hive and DuckDB (executed on DuckDB for the committed results; Hive is the
  documented optional path).
- Numbers in the website use Indian digit grouping.
