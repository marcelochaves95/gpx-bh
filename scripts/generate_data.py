"""Generate docs/data/neighborhoods.json from the PBH WFS service.

Fetches the neighborhoods over HTTP, converts UTM (EPSG:31983) coordinates to
lat/lon (WGS84), looks up the real elevation of each point from a DEM and writes
the static JSON consumed by the web app. Each point is stored as [lng, lat, ele].

Usage:
    python scripts/generate_data.py
"""
import json
import os
import time
import urllib.parse
import urllib.request

from pyproj import Transformer

OUTPUT_PATH = os.path.join("docs", "data", "neighborhoods.json")

# The PBH WAF rejects requests with a default/empty User-Agent (and any request
# carrying an Origin header), so a browser-like User-Agent is required.
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "application/json",
}


def get_url():
    params = {
        "service": "WFS",
        "version": "1.0.0",
        "request": "GetFeature",
        "typeName": "ide_bhgeo:BAIRRO_POPULAR",
        "srsName": "EPSG:31983",
        "outputFormat": "application/json",
    }
    return urllib.parse.urlunparse(
        ("https", "geoservicos.pbh.gov.br", "/geoserver/wfs", "",
         urllib.parse.urlencode(params), "")
    )


def fetch_neighborhoods():
    request = urllib.request.Request(get_url(), headers=HEADERS)
    with urllib.request.urlopen(request, timeout=60) as response:
        data = json.load(response)
    neighborhoods = {
        feature["properties"].get("NOME", "Nome não disponível"): feature["geometry"]["coordinates"]
        for feature in data.get("features", [])
    }
    return dict(sorted(neighborhoods.items()))

# Free, no-key DEM elevation API (SRTM 30 m). Public limits: 100 points/call,
# 1 call/sec, 1000 calls/day.
ELEVATION_API = "https://api.opentopodata.org/v1/srtm30m"
ELEVATION_BATCH = 100
CELL_DECIMALS = 3  # ~110 m grid — matches the DEM resolution and dedupes vertices
DEFAULT_ELEVATION = 850.0  # fallback (BH average) if the DEM has no value for a cell


def _cell(lng, lat):
    return (round(lng, CELL_DECIMALS), round(lat, CELL_DECIMALS))


def fetch_elevations(points):
    """Map each DEM cell touched by the points to its elevation in meters.

    OpenStreetMap/Leaflet tiles carry no elevation, so we query a DEM. Vertices are
    snapped to a ~110 m grid (the DEM's own resolution) so the tens of thousands of
    boundary points collapse to a few thousand cells, keeping requests low.
    """
    cells = sorted({_cell(lng, lat) for lng, lat in points})
    elevations = {}
    total_batches = (len(cells) + ELEVATION_BATCH - 1) // ELEVATION_BATCH
    print(f"  Looking up elevation for {len(cells)} DEM cells ({total_batches} requests)…")

    for i in range(0, len(cells), ELEVATION_BATCH):
        batch = cells[i:i + ELEVATION_BATCH]
        locations = "|".join(f"{lat},{lng}" for lng, lat in batch)
        url = f"{ELEVATION_API}?locations={urllib.parse.quote(locations)}"
        req = urllib.request.Request(url, headers={"User-Agent": "gpx-bh"})

        for attempt in range(4):
            try:
                with urllib.request.urlopen(req, timeout=60) as response:
                    results = json.load(response)["results"]
                values = [r["elevation"] for r in results]
                break
            except Exception as e:
                if attempt == 3:
                    raise RuntimeError(f"Elevation lookup failed: {e}")
                time.sleep(5)

        for cell, ele in zip(batch, values):
            elevations[cell] = round(ele, 1)
        time.sleep(1.0)  # ~60 requests/min, comfortably under the rate limit

    return elevations


def main():
    print("Fetching neighborhoods from PBH…")
    data = fetch_neighborhoods()
    print(f"  {len(data)} neighborhoods received.")

    transformer = Transformer.from_crs("EPSG:31983", "EPSG:4326", always_xy=True)

    def convert_ring(ring):
        lons, lats = transformer.transform([p[0] for p in ring], [p[1] for p in ring])
        return [[round(lon, 6), round(lat, 6)] for lon, lat in zip(lons, lats)]

    converted = {
        name: [[convert_ring(ring) for ring in polygon] for polygon in polygons]
        for name, polygons in data.items()
    }
    converted = dict(sorted(converted.items()))

    # Collect every point, resolve elevations, then append ele to each [lng, lat].
    all_points = [
        (pt[0], pt[1])
        for polygons in converted.values()
        for polygon in polygons
        for ring in polygon
        for pt in ring
    ]
    elevations = fetch_elevations(all_points)
    for polygons in converted.values():
        for polygon in polygons:
            for ring in polygon:
                for pt in ring:
                    pt.append(elevations[_cell(pt[0], pt[1])])

    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(converted, f, ensure_ascii=False, separators=(",", ":"))

    size_mb = os.path.getsize(OUTPUT_PATH) / 1024 / 1024
    print(f"  Saved to {OUTPUT_PATH} ({size_mb:.2f} MB).")


if __name__ == "__main__":
    main()
