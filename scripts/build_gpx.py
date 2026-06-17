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
import unicodedata
from xml.sax.saxutils import escape

ELEVATION = 1045.55
DATA_PATH = os.path.join("docs", "data", "neighborhoods.json")
OUTPUT_DIR = os.path.join("docs", "data", "gpx")


def file_name(name):
    # ASCII slug: gpx.studio labels a remote file by its raw (non-decoded) URL
    # basename, so accents/spaces would show up percent-encoded. Strip diacritics
    # and collapse whitespace to underscores. Must mirror slug() in the web app.
    normalized = unicodedata.normalize("NFKD", name)
    ascii_name = "".join(c for c in normalized if not unicodedata.combining(c))
    return re.sub(r"\s+", "_", ascii_name) + ".gpx"


def build_gpx(name, polygons):
    safe = escape(name)
    parts = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<gpx version="1.1" creator="GPX BH" xmlns="http://www.topografix.com/GPX/1/1">',
        "  <trk>",
        f"    <name>{safe}</name>",
    ]
    # Only the outer ring of each polygon (index 0) — inner rings are holes (enclaves)
    # and shouldn't be drawn. Each polygon's boundary is its own segment so viewers
    # don't connect separate parts with spurious straight lines.
    for polygon in polygons:
        ring = polygon[0]
        parts.append("    <trkseg>")
        for point in ring:
            lng, lat = point[0], point[1]
            ele = point[2] if len(point) > 2 else ELEVATION
            parts += [
                f'      <trkpt lat="{lat}" lon="{lng}">',
                f"        <ele>{ele}</ele>",
                f"        <name>{safe}</name>",
                "      </trkpt>",
            ]
        parts.append("    </trkseg>")
    parts += ["  </trk>", "</gpx>", ""]
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
