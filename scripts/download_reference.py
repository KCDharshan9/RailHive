"""Download the DataMeet railway reference JSON files.

Source: https://github.com/datameet/railways (CC0).
The files live in data/reference/ and are only fetched when missing or
truncated (smaller than 1 MB). Re-running the script is safe: valid local
files are kept and re-validated.
"""

import json
import sys
import urllib.request
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
REFERENCE_DIR = BASE_DIR / "data" / "reference"

MIN_BYTES = 1_000_000
CHUNK = 1024 * 1024

BASE_URL = "https://raw.githubusercontent.com/datameet/railways/master/"

FILES = {
    "stations.json": "geojson",
    "trains.json": "geojson",
    "schedules.json": "list",
}

# Expected record counts are only used for a warning, never to reject a file.
EXPECTED = {"stations.json": 8990, "trains.json": 5208, "schedules.json": 417080}


def human_size(num_bytes):
    if num_bytes >= 1024 * 1024:
        return "%.2f MB" % (num_bytes / (1024.0 * 1024.0))
    if num_bytes >= 1024:
        return "%.1f KB" % (num_bytes / 1024.0)
    return "%d bytes" % num_bytes


def validate(path, kind):
    """Parse the JSON file and return its record count."""
    with path.open("r", encoding="utf-8") as handle:
        data = json.load(handle)
    if kind == "geojson":
        if not isinstance(data, dict) or not isinstance(data.get("features"), list):
            raise ValueError("not a GeoJSON FeatureCollection")
        return len(data["features"])
    if not isinstance(data, list):
        raise ValueError("not a JSON array")
    return len(data)


def download(name):
    url = BASE_URL + name
    target = REFERENCE_DIR / name
    temp = target.with_suffix(target.suffix + ".part")
    print("downloading %s from %s" % (name, url))
    request = urllib.request.Request(url, headers={"User-Agent": "railway-analytics/1.0"})
    downloaded = 0
    try:
        with urllib.request.urlopen(request, timeout=120) as response, temp.open("wb") as out:
            while True:
                block = response.read(CHUNK)
                if not block:
                    break
                out.write(block)
                downloaded += len(block)
                if downloaded % (10 * CHUNK) < CHUNK:
                    print("  %s: %s received" % (name, human_size(downloaded)))
        temp.replace(target)
    except Exception:
        if temp.exists():
            temp.unlink()
        raise
    print("  %s: finished, %s on disk" % (name, human_size(target.stat().st_size)))


def main():
    REFERENCE_DIR.mkdir(parents=True, exist_ok=True)
    failures = []

    for name, kind in FILES.items():
        path = REFERENCE_DIR / name
        size = path.stat().st_size if path.exists() else 0

        if size >= MIN_BYTES:
            print("%s already present (%s), skipping download" % (name, human_size(size)))
        else:
            if size:
                print("%s is %s, below the 1 MB threshold, fetching again" % (name, human_size(size)))
            try:
                download(name)
            except Exception as exc:
                print("ERROR: download failed for %s: %s" % (name, exc))
                failures.append(name)
                continue

        size = path.stat().st_size
        try:
            count = validate(path, kind)
        except Exception as exc:
            print("ERROR: %s did not parse as JSON: %s" % (name, exc))
            failures.append(name)
            continue

        print("%s: %s, %d records%s" % (
            name,
            human_size(size),
            count,
            "" if count == EXPECTED.get(name) else " (expected %d)" % EXPECTED[name],
        ))

    if failures:
        print("FAILED: %s" % ", ".join(failures))
        return 1
    print("all reference files present and valid")
    return 0


if __name__ == "__main__":
    sys.exit(main())
