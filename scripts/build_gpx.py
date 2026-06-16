"""Generate one GPX file per neighborhood from docs/data/neighborhoods.json.

Reads the static dataset (lat/lon coordinates) and writes
docs/data/gpx/<name>.gpx for every neighborhood. These files are served
statically (e.g. by GitHub Pages) so external tools such as gpx.studio can
load a neighborhood by its public URL.

Usage:
    python scripts/build_gpx.py
"""
import json
import os
import re
from xml.sax.saxutils import escape

ELEVATION = 1045.55
DATA_PATH = os.path.join("docs", "data", "neighborhoods.json")
OUTPUT_DIR = os.path.join("docs", "data", "gpx")


def file_name(name):
    # Mirror the web app: collapse whitespace runs to a single underscore.
    return re.sub(r"\s+", "_", name) + ".gpx"


def build_gpx(name, polygons):
    safe = escape(name)
    parts = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<gpx version="1.1" creator="Mapa BH" xmlns="http://www.topografix.com/GPX/1/1">',
        "  <trk>",
        f"    <name>{safe}</name>",
        "    <trkseg>",
    ]
    for polygon in polygons:
        for ring in polygon:
            for lng, lat in ring:
                parts += [
                    f'      <trkpt lat="{lat}" lon="{lng}">',
                    f"        <ele>{ELEVATION}</ele>",
                    f"        <name>{safe}</name>",
                    "      </trkpt>",
                ]
    parts += ["    </trkseg>", "  </trk>", "</gpx>", ""]
    return "\n".join(parts)


def main():
    with open(DATA_PATH, encoding="utf-8") as f:
        neighborhoods = json.load(f)

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    for name, polygons in neighborhoods.items():
        path = os.path.join(OUTPUT_DIR, file_name(name))
        with open(path, "w", encoding="utf-8") as f:
            f.write(build_gpx(name, polygons))

    print(f"  Wrote {len(neighborhoods)} GPX files to {OUTPUT_DIR}.")


if __name__ == "__main__":
    main()
