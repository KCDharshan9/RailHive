# Railway Reservation Analytics

A big data analytics project on Indian Railways reservation data. It builds
150,000 reservation records on top of real, open DataMeet data (stations,
trains and schedules, CC0), runs 14 SQL analysis queries, and presents the
results in a small Flask website with charts: Overview, Routes, Revenue,
Waitlist, Delays and an Explorer with filters and CSV export.

The SQL is portable: it is designed to run on Apache Hive or, without
Docker, on DuckDB. The committed results were produced with DuckDB 1.1.3;
the Hive path (docker-compose.yml + scripts/run_hive.py) is documented but
has not been executed on this machine.

## How to run

You need Python 3.10 or newer. Docker is needed only for the optional Hive
path, not for the main one. Run every command from the project folder.

### 1. Set up

Windows PowerShell:

```powershell
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

Linux / macOS:

```bash
python3 -m venv .venv
./.venv/bin/python -m pip install -r requirements.txt
```

If PowerShell refuses to activate the venv, call the interpreter directly as
`.\.venv\Scripts\python.exe`, or run `Set-ExecutionPolicy -Scope Process Bypass` first.

### 2. Build the data (one time, in this order)

```powershell
.\.venv\Scripts\python.exe scripts\download_reference.py
.\.venv\Scripts\python.exe scripts\build_reference.py
.\.venv\Scripts\python.exe scripts\generate_bookings.py
.\.venv\Scripts\python.exe scripts\run_local.py
.\.venv\Scripts\python.exe scripts\build_site_data.py
```

On Linux / macOS, replace `.\.venv\Scripts\python.exe` with `./.venv/bin/python`.

### 3. Start the website

```powershell
.\.venv\Scripts\python.exe website\app.py
```

Open http://127.0.0.1:5000 in your browser. Stop the server with Ctrl+C.

## Good to know

- The report is built with `.\.venv\Scripts\python.exe scripts\make_report.py`
  from the numbers in the results (report/report.docx). Fill in the
  placeholders on the title page before submission.
- No server needed: `scripts\export_static.py` writes a static site to
  `dist/` you can upload to Netlify or GitHub Pages. `render.yaml` is
  included for a free Render deployment of the Flask app.
- The reservation records are generated with a fixed seed (42) because
  passenger level booking data is not published as open data; each booking
  uses a real train, a real station pair from its schedule and a class the
  train supports. Amounts are in Indian Rupees.
- Reference data: DataMeet railways, CC0, https://github.com/datameet/railways
