#!/usr/bin/env python3
"""Extract field polygons and task metadata from TASKDATA.xml -> GeoJSON

Usage:
    python scripts/extract_taskdata_geojson.py \
        --src data/TASKDATA --out data/harvest_fields.geojson

If `--src` contains multiple files, the script looks for a file with
case-insensitive name 'taskdata.xml'.
"""
from pathlib import Path
import argparse
import json
import xml.etree.ElementTree as ET
from datetime import datetime
import sys


def local_tag_name(elem):
    """Return local name of XML tag (strip namespace if present)."""
    return elem.tag.split('}')[-1] if '}' in elem.tag else elem.tag


def find_taskdata_file(folder: Path) -> Path:
    """Return path to TASKDATA.xml inside folder (case-insensitive).
    Raise FileNotFoundError if not found.
    """
    for p in folder.iterdir():
        if p.is_file() and p.name.lower() == 'taskdata.xml':
            return p
    raise FileNotFoundError(f"No TASKDATA.xml found in {folder}")


def parse_taskdata_to_geojson(src_folder: str, out_path: str):
    src = Path(src_folder)
    try:
        xml_path = find_taskdata_file(src)
    except FileNotFoundError as e:
        print(e)
        return 1

    print(f"Parsing {xml_path}...")
    try:
        tree = ET.parse(xml_path)
        root = tree.getroot()
    except Exception as e:
        print(f"Failed to parse XML: {e}")
        return 1

    # 1. Map Products (PDT) -> Crop Names
    products = {}
    for elem in root.iter():
        if local_tag_name(elem) == 'PDT':
            pid = elem.attrib.get('A')
            if pid:
                products[pid] = elem.attrib.get('B')

    # 2. Extract Field Geometries (PFD)
    # Map PFD_ID -> list of polygons; each polygon is list of linear rings; each ring is list of [lon, lat]
    field_geoms = {}
    field_names = {}

    for elem in root.iter():
        if local_tag_name(elem) == 'PFD':
            pfd_id = elem.attrib.get('A')
            field_names[pfd_id] = elem.attrib.get('C', f"Unknown_{pfd_id}")
            polygons = []
            # PLN children under PFD
            for pln in list(elem):
                if local_tag_name(pln) != 'PLN':
                    continue
                # Each PLN may contain multiple LSG rings
                polygon_rings = []
                for lsg in list(pln):
                    if local_tag_name(lsg) != 'LSG':
                        continue
                    ring = []
                    for pnt in list(lsg):
                        if local_tag_name(pnt) != 'PNT':
                            continue
                        # ISOXML: C = North (lat), D = East (lon)
                        c = pnt.attrib.get('C')
                        d = pnt.attrib.get('D')
                        try:
                            lat = float(c)
                            lon = float(d)
                            ring.append([lon, lat])
                        except Exception:
                            continue
                    if len(ring) > 2:
                        # close ring if necessary
                        if ring[0] != ring[-1]:
                            ring.append(ring[0])
                        polygon_rings.append(ring)
                if polygon_rings:
                    polygons.append(polygon_rings)

            if polygons:
                field_geoms[pfd_id] = polygons

    # 3. Build GeoJSON Features from Tasks (TSK)
    features = []
    for elem in root.iter():
        if local_tag_name(elem) != 'TSK':
            continue
        tsk = elem
        # Find TLG child
        tlg = None
        pan = None
        tim = None
        for child in list(tsk):
            tag = local_tag_name(child)
            if tag == 'TLG':
                tlg = child
            elif tag == 'PAN':
                pan = child
            elif tag == 'TIM':
                tim = child
        if tlg is None:
            continue
        log_filename = tlg.attrib.get('A') + '.bin' if tlg.attrib.get('A') else None
        field_ref = tsk.attrib.get('E')

        # Crop name
        crop_name = 'Unknown'
        if pan is not None:
            prod_ref = pan.attrib.get('A')
            crop_name = products.get(prod_ref, 'Unknown')

        # Year from TIM
        year = None
        if tim is not None and tim.attrib.get('A'):
            start_str = tim.attrib.get('A')
            try:
                dt = datetime.fromisoformat(start_str.replace('Z', ''))
                year = dt.year
            except Exception:
                year = None

        # Build feature if we have geometry
        if field_ref in field_geoms:
            polygons = field_geoms[field_ref]
            # polygons is a list of polygons; each polygon is a list of rings
            if len(polygons) == 1:
                geom_type = 'Polygon'
                coordinates = polygons[0]
            else:
                geom_type = 'MultiPolygon'
                coordinates = polygons

            feature = {
                'type': 'Feature',
                'properties': {
                    'TaskID': tsk.attrib.get('A'),
                    'LogFilename': log_filename,
                    'Year': year,
                    'Crop': crop_name,
                    'FieldName': field_names.get(field_ref, 'Unknown'),
                    'FieldID': field_ref
                },
                'geometry': {
                    'type': geom_type,
                    'coordinates': coordinates
                }
            }
            features.append(feature)

    geojson_obj = {
        'type': 'FeatureCollection',
        'features': features
    }

    outp = Path(out_path)
    outp.parent.mkdir(parents=True, exist_ok=True)
    with outp.open('w', encoding='utf-8') as f:
        json.dump(geojson_obj, f, indent=2)

    print(f"Success: extracted {len(features)} features to {out_path}")
    return 0


def main(argv=None):
    parser = argparse.ArgumentParser(description='Extract TASKDATA -> GeoJSON')
    parser.add_argument('--src', '-s', default='data/TASKDATA', help='Path to TaskData folder')
    parser.add_argument('--out', '-o', default='data/harvest_fields.geojson', help='Output GeoJSON file')
    args = parser.parse_args(argv)
    return parse_taskdata_to_geojson(args.src, args.out)


if __name__ == '__main__':
    sys.exit(main())
