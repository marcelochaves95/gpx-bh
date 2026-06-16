from pyproj import Proj, Transformer
from urllib.parse import urlencode, urlunparse
from xml.dom import minidom
import json
import urllib.request
import xml.etree.ElementTree as ET

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
        "outputFormat": "application/json"
    }

    return urlunparse(("https", "geoservicos.pbh.gov.br", "/geoserver/wfs", "", urlencode(params), ""))

def convert_utm_to_latitude_and_longitude(x, y):
    utm_proj = Proj(proj='utm', zone=23, south=True, datum='WGS84')
    latlon_proj = Proj(proj='latlong', datum='WGS84')
    transformer = Transformer.from_proj(utm_proj, latlon_proj)
    return transformer.transform(x, y)

def fetch_neighborhoods():
    request = urllib.request.Request(get_url(), headers=HEADERS)

    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            data = json.load(response)
    except Exception as e:
        raise RuntimeError(f"Erro ao buscar os dados: {e}")

    neighborhoods = {
        feature["properties"].get("NOME", "Nome não disponível"): feature["geometry"]["coordinates"]
        for feature in data.get("features", [])
    }

    return dict(sorted(neighborhoods.items()))

def generate_gpx(selected_neighborhood, coordinates, file_path, elevation=1045.55):
    gpx = ET.Element("gpx", version="1.1", creator="GPX BH", xmlns="http://www.topografix.com/GPX/1/1")
    trk = ET.SubElement(gpx, "trk")
    ET.SubElement(trk, "name").text = selected_neighborhood

    # Each ring (outer boundary or inner hole) is its own segment, otherwise viewers
    # connect the end of one ring to the start of the next with spurious straight lines.
    for polygon in coordinates:
        for ring in polygon:
            trkseg = ET.SubElement(trk, "trkseg")
            for point in ring:
                longitude, latitude = convert_utm_to_latitude_and_longitude(point[0], point[1])
                trkpt = ET.SubElement(trkseg, "trkpt", lat=str(latitude), lon=str(longitude))
                ET.SubElement(trkpt, "ele").text = str(elevation)
                ET.SubElement(trkpt, "name").text = selected_neighborhood

    tree = ET.ElementTree(gpx)

    rough_string = ET.tostring(gpx, encoding='utf-8')
    reparsed = minidom.parseString(rough_string)

    with open(file_path, "w", encoding="UTF-8") as f:
        f.write(reparsed.toprettyxml(indent="  "))

    return f"Arquivo GPX salvo com sucesso em {file_path}."
