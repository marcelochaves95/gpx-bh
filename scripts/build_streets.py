"""Generate per-neighborhood street GPX from the PBH road network (IDE-BHGEO).

For each neighborhood it fetches the road segments (ide_bhgeo:CIRCULACAO_VIARIA)
within its bounding box, drops connector/ramp segments, clips them to the polygon
and writes docs/data/streets/<name>.gpx. Also writes docs/data/street_lengths.json
mapping each neighborhood to its total street length in km (the "Every Single
Street" distance). Run after generate_data.py.

Usage:
    python scripts/build_streets.py
"""
import json
import os
import re
import time
import unicodedata
import urllib.parse
import urllib.request
from xml.sax.saxutils import escape

from pyproj import Transformer
from shapely.geometry import shape, Polygon
from shapely.ops import transform as shp_transform, unary_union

LAYER = "ide_bhgeo:CIRCULACAO_VIARIA"
WFS = "https://geoservicos.pbh.gov.br/geoserver/wfs"
HEADERS = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                         "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"}
DATA_PATH = os.path.join("docs", "data", "neighborhoods.json")
OUT_DIR = os.path.join("docs", "data", "streets")
LENGTHS_PATH = os.path.join("docs", "data", "street_lengths.json")

to_utm = Transformer.from_crs("EPSG:4326", "EPSG:31983", always_xy=True)
to_wgs = Transformer.from_crs("EPSG:31983", "EPSG:4326", always_xy=True)


def slug(name):
    n = unicodedata.normalize("NFKD", name)
    n = "".join(c for c in n if not unicodedata.combining(c))
    return re.sub(r"\s+", "_", n)


def fetch_segments(bounds):
    minx, miny, maxx, maxy = bounds
    params = {
        "service": "WFS", "version": "2.0.0", "request": "GetFeature",
        "typeNames": LAYER, "srsName": "EPSG:31983", "outputFormat": "application/json",
        "bbox": f"{minx},{miny},{maxx},{maxy},EPSG:31983",
    }
    url = f"{WFS}?{urllib.parse.urlencode(params)}"
    for attempt in range(4):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=HEADERS), timeout=120) as r:
                return json.load(r)["features"]
        except Exception as e:
            if attempt == 3:
                raise RuntimeError(f"WFS fetch failed: {e}")
            time.sleep(5)


def build():
    neighborhoods = json.load(open(DATA_PATH, encoding="utf-8"))
    os.makedirs(OUT_DIR, exist_ok=True)
    lengths = {}

    for i, (name, polys) in enumerate(neighborhoods.items(), 1):
        shapely_polys = [
            Polygon([(p[0], p[1]) for p in poly[0]],
                    [[(p[0], p[1]) for p in ring] for ring in poly[1:]])
            for poly in polys
        ]
        area_wgs = unary_union(shapely_polys)
        area_utm = shp_transform(lambda x, y, z=None: to_utm.transform(x, y), area_wgs)

        segments = fetch_segments(area_utm.bounds)
        lines, total = [], 0.0
        for f in segments:
            props = f["properties"]
            if props.get("TIPO_TRECHO_CIRCULACAO") == "Trecho de conversão" or not props.get("LOGRADOURO"):
                continue
            inter = shape(f["geometry"]).intersection(area_utm)
            if inter.is_empty:
                continue
            geoms = ([inter] if inter.geom_type == "LineString"
                     else list(inter.geoms) if inter.geom_type in ("MultiLineString", "GeometryCollection")
                     else [])
            for g in geoms:
                parts = g.geoms if g.geom_type == "MultiLineString" else [g]
                for s in parts:
                    if s.geom_type == "LineString" and s.length > 0:
                        lines.append(list(s.coords))
                        total += s.length

        gpx = ['<?xml version="1.0" encoding="UTF-8"?>',
               '<gpx version="1.1" creator="GPX BH" xmlns="http://www.topografix.com/GPX/1/1">',
               "  <trk>", f"    <name>{escape(name)} — ruas</name>"]
        for line in lines:
            gpx.append("    <trkseg>")
            for x, y in line:
                lon, lat = to_wgs.transform(x, y)
                gpx.append(f'      <trkpt lat="{round(lat, 6)}" lon="{round(lon, 6)}"></trkpt>')
            gpx.append("    </trkseg>")
        gpx += ["  </trk>", "</gpx>", ""]
        open(os.path.join(OUT_DIR, slug(name) + ".gpx"), "w", encoding="utf-8").write("\n".join(gpx))
        lengths[name] = round(total / 1000, 2)

        if i % 50 == 0 or i == len(neighborhoods):
            print(f"  {i}/{len(neighborhoods)} bairros…")
        time.sleep(0.3)

    json.dump(lengths, open(LENGTHS_PATH, "w", encoding="utf-8"), ensure_ascii=False)
    print(f"  Done. {len(lengths)} neighborhoods. Total streets: {round(sum(lengths.values()))} km.")


if __name__ == "__main__":
    build()
