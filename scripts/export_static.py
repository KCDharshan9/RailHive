"""Render the Flask pages into a self contained dist/ folder."""

from __future__ import annotations

import re
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
WEBSITE = ROOT / "website"
DIST = ROOT / "dist"

sys.path.insert(0, str(WEBSITE))

from app import create_app  # noqa: E402

PAGES = (
    ("index.html", "/"),
    ("routes.html", "/routes"),
    ("revenue.html", "/revenue"),
    ("waitlist.html", "/waitlist"),
    ("delays.html", "/delays"),
    ("explorer.html", "/explorer"),
)

ABSOLUTE_LINK = re.compile(r"""(?:href|src|action)\s*=\s*["']?/""", re.IGNORECASE)
ABSOLUTE_CSS = re.compile(r"""url\(\s*["']?/""", re.IGNORECASE)


def main():
    app = create_app({"STATIC_MODE": True, "TESTING": True})
    client = app.test_client()

    if DIST.exists():
        shutil.rmtree(DIST)
    DIST.mkdir(parents=True)

    written = []
    for filename, path in PAGES:
        response = client.get(path)
        if response.status_code != 200:
            raise SystemExit(f"{path} returned HTTP {response.status_code}")
        html = response.get_data(as_text=True)
        if "window.ANALYTICS" not in html:
            raise SystemExit(f"{filename} does not embed window.ANALYTICS")
        if ABSOLUTE_LINK.search(html) or ABSOLUTE_CSS.search(html):
            raise SystemExit(f"{filename} still contains an absolute link")
        target = DIST / filename
        with target.open("w", encoding="utf-8", newline="\n") as handle:
            handle.write(html)
        written.append((filename, len(html)))

    shutil.copytree(
        WEBSITE / "static",
        DIST / "static",
        ignore=shutil.ignore_patterns("__pycache__", "*.pyc"),
    )

    required = [
        DIST / "static" / "css" / "app.css",
        DIST / "static" / "js" / "app.js",
        DIST / "static" / "js" / "charts.js",
        DIST / "static" / "vendor" / "bootstrap.min.css",
        DIST / "static" / "vendor" / "bootstrap.bundle.min.js",
        DIST / "static" / "vendor" / "chart.umd.min.js",
    ]
    missing = [str(path.relative_to(DIST)) for path in required if not path.is_file()]
    if missing:
        raise SystemExit("Missing static assets: " + ", ".join(missing))

    for filename, size in written:
        print(f"wrote dist/{filename} ({size:,} bytes)")
    print("copied static assets into dist/static")
    print("export complete")


if __name__ == "__main__":
    main()
