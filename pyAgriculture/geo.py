"""TASKDATA -> GeoJSON utilities for pyAgriculture.

Provides `extract_taskdata_to_geojson()` which mirrors the standalone
script but is part of the package API so it can be used from code or by
CLI entry points.
"""
from pathlib import Path
import json
import xml.etree.ElementTree as ET
from datetime import datetime
import argparse
import sys


def _local_tag_name(elem):
    return elem.tag.split('}')[-1] if '}' in elem.tag else elem.tag


def _find_taskdata_file(folder: Path) -> Path:
    for p in folder.iterdir():
        if p.is_file() and p.name.lower() == 'taskdata.xml':
            return p
    raise FileNotFoundError(f"No TASKDATA.xml found in {folder}")


def extract_taskdata_to_geojson(src_folder: str = 'data/TASKDATA', out_path: str = 'data/harvest_fields.geojson') -> int:
    """Extract polygons and task metadata from a TaskData folder and write GeoJSON.

    Defaults allow calling the function without arguments (for older console
    scripts that call it with no parameters).

    Returns 0 on success, non-zero on error.
    """
    src = Path(src_folder)
    xml_path = _find_taskdata_file(src)

    tree = ET.parse(xml_path)
    root = tree.getroot()

    # Products
    products = {}
    for elem in root.iter():
        if _local_tag_name(elem) == 'PDT':
            pid = elem.attrib.get('A')
            if pid:
                products[pid] = elem.attrib.get('B')

    # Fields
    field_geoms = {}
    field_names = {}
    for elem in root.iter():
        if _local_tag_name(elem) == 'PFD':
            pfd_id = elem.attrib.get('A')
            field_names[pfd_id] = elem.attrib.get('C', f"Unknown_{pfd_id}")
            polygons = []
            for pln in list(elem):
                if _local_tag_name(pln) != 'PLN':
                    continue
                polygon_rings = []
                for lsg in list(pln):
                    if _local_tag_name(lsg) != 'LSG':
                        continue
                    ring = []
                    for pnt in list(lsg):
                        if _local_tag_name(pnt) != 'PNT':
                            continue
                        c = pnt.attrib.get('C')
                        d = pnt.attrib.get('D')
                        try:
                            lat = float(c)
                            lon = float(d)
                            ring.append([lon, lat])
                        except Exception:
                            continue
                    if len(ring) > 2:
                        if ring[0] != ring[-1]:
                            ring.append(ring[0])
                        polygon_rings.append(ring)
                if polygon_rings:
                    polygons.append(polygon_rings)
            if polygons:
                field_geoms[pfd_id] = polygons

    # Tasks -> features
    features = []
    for elem in root.iter():
        if _local_tag_name(elem) != 'TSK':
            continue
        tsk = elem
        tlg = None
        pan = None
        tim = None
        for child in list(tsk):
            tag = _local_tag_name(child)
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

        crop_name = 'Unknown'
        if pan is not None:
            prod_ref = pan.attrib.get('A')
            crop_name = products.get(prod_ref, 'Unknown')

        year = None
        if tim is not None and tim.attrib.get('A'):
            start_str = tim.attrib.get('A')
            try:
                dt = datetime.fromisoformat(start_str.replace('Z', ''))
                year = dt.year
            except Exception:
                year = None

        if field_ref in field_geoms:
            polygons = field_geoms[field_ref]
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

    geojson_obj = {'type': 'FeatureCollection', 'features': features}
    outp = Path(out_path)
    outp.parent.mkdir(parents=True, exist_ok=True)
    with outp.open('w', encoding='utf-8') as f:
        json.dump(geojson_obj, f, indent=2)

    return 0


def main(argv=None) -> int:
    """Console entry point for extracting TASKDATA -> GeoJSON.

    Accepts optional positional args: [src_folder] [out_path].
    Returns exit code (0 success).
    """
    parser = argparse.ArgumentParser(description='Extract TASKDATA -> GeoJSON')
    parser.add_argument('src', nargs='?', default='data/TASKDATA', help='Path to TaskData folder')
    parser.add_argument('out', nargs='?', default='data/harvest_fields.geojson', help='Output GeoJSON file')
    args = parser.parse_args(argv)
    try:
        return extract_taskdata_to_geojson(args.src, args.out)
    except FileNotFoundError as e:
        print(e, file=sys.stderr)
        return 2


if __name__ == '__main__':
    sys.exit(main())
