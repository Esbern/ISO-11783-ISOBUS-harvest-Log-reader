"""TASKDATA -> GeoJSON utilities for pyagri.

Provides utilities for extracting field geometries and task metadata from
TASKDATA.xml files, with support for unique field representation and
multi-file merging.
"""
from pathlib import Path
import json
import xml.etree.ElementTree as ET
from datetime import datetime
import argparse
import sys
from collections import defaultdict
from typing import Dict, List, Tuple, Any


def _local_tag_name(elem):
    return elem.tag.split('}')[-1] if '}' in elem.tag else elem.tag


def _find_taskdata_file(folder: Path) -> Path:
    for p in folder.iterdir():
        if p.is_file() and p.name.lower() == 'taskdata.xml':
            return p
    raise FileNotFoundError(f"No TASKDATA.xml found in {folder}")


def _geometry_to_key(geom: Dict[str, Any]) -> str:
    """Hash a geometry for comparison (simple string repr)."""
    import json
    return json.dumps(geom, sort_keys=True)


def extract_unique_fields_to_geojson(src_folders: List[str], out_path: str = 'data/harvest_fields.geojson') -> int:
    """Extract unique field geometries and aggregate task data from one or more TaskData folders.

    Creates one GeoJSON feature per unique field+source combination.
    Uses composite key: folder_name/field_id (e.g., 'TASKDATA/PFD1', 'TASKDATA 2/PFD1').
    This maintains separate geometry definitions when the same field ID has different
    geometries across TASKDATA folders.
    
    Args:
        src_folders: Single folder path (str) or list of folder paths
        out_path: Output GeoJSON file path
    
    Returns:
        0 on success, non-zero on error.
    """
    if isinstance(src_folders, str):
        src_folders = [src_folders]
    
    # Collect all field and task data using composite key: folder_name/field_id
    fields_by_composite_id: Dict[str, Dict[str, Any]] = {}  # composite_id -> {name, geom, folder, pfd_id}
    tasks_by_composite_id: Dict[str, Dict[int, List[Dict]]] = defaultdict(lambda: defaultdict(list))  # composite_id -> year -> [tasks]
    
    for src_folder in src_folders:
        src = Path(src_folder)
        folder_name = src.name  # e.g., 'TASKDATA' or 'TASKDATA 2'
        
        try:
            xml_path = _find_taskdata_file(src)
        except FileNotFoundError as e:
            print(f"Warning: {e}", file=sys.stderr)
            continue
        
        tree = ET.parse(xml_path)
        root = tree.getroot()
        
        # Parse products
        products = {}
        for elem in root.iter():
            if _local_tag_name(elem) == 'PDT':
                pid = elem.attrib.get('A')
                if pid:
                    products[pid] = elem.attrib.get('B')
        
        # Parse fields and geometries
        for elem in root.iter():
            if _local_tag_name(elem) != 'PFD':
                continue
            
            pfd_id = elem.attrib.get('A')
            composite_id = f"{folder_name}/{pfd_id}"
            field_name = elem.attrib.get('C', f"Unknown_{pfd_id}")
            
            # Extract geometry
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
                if len(polygons) == 1:
                    geom = {'type': 'Polygon', 'coordinates': polygons[0]}
                else:
                    geom = {'type': 'MultiPolygon', 'coordinates': polygons}
                
                # Store with composite key - each folder/field combination is unique
                fields_by_composite_id[composite_id] = {
                    'name': field_name,
                    'geom': geom,
                    'folder': folder_name,
                    'pfd_id': pfd_id,
                    'source': str(xml_path)
                }
        
        # Parse tasks
        for elem in root.iter():
            if _local_tag_name(elem) != 'TSK':
                continue
            
            tsk = elem
            field_ref = tsk.attrib.get('E')
            if not field_ref:
                continue
            
            # Use composite key for task association
            composite_field_ref = f"{folder_name}/{field_ref}"
            
            tsk_id = tsk.attrib.get('A')
            
            # Extract year from TIM
            year = None
            tim = None
            for child in list(tsk):
                if _local_tag_name(child) == 'TIM':
                    tim = child
                    break
            
            if tim is not None and tim.attrib.get('A'):
                start_str = tim.attrib.get('A')
                try:
                    dt = datetime.fromisoformat(start_str.replace('Z', ''))
                    year = dt.year
                except Exception:
                    year = None
            
            # Extract crop
            crop_name = 'Unknown'
            for child in list(tsk):
                if _local_tag_name(child) == 'PAN':
                    prod_ref = child.attrib.get('A')
                    crop_name = products.get(prod_ref, 'Unknown')
                    break
            
            # Extract log filename
            log_filename = None
            for child in list(tsk):
                if _local_tag_name(child) == 'TLG':
                    log_filename = child.attrib.get('A')
                    if log_filename:
                        log_filename += '.bin'
                    break
            
            task_info = {
                'TaskID': tsk_id,
                'Crop': crop_name,
                'LogFile': log_filename,
                'Source': str(xml_path)
            }
            
            if year:
                tasks_by_composite_id[composite_field_ref][year].append(task_info)
            else:
                tasks_by_composite_id[composite_field_ref]['unknown'].append(task_info)
    
    # Build GeoJSON features
    features = []
    for composite_id, field_data in fields_by_composite_id.items():
        # Aggregate tasks by year
        task_summary = []
        years_with_tasks = sorted([y for y in tasks_by_composite_id.get(composite_id, {}).keys() if y != 'unknown'])
        
        for year in years_with_tasks:
            tasks = tasks_by_composite_id[composite_id][year]
            task_ids = [t['TaskID'] for t in tasks]
            crops = list(set(t['Crop'] for t in tasks))
            count = len(tasks)
            task_summary.append({
                'Year': year,
                'TaskCount': count,
                'TaskIDs': task_ids,
                'Crops': crops
            })
        
        # Handle unknown year tasks
        if 'unknown' in tasks_by_composite_id.get(composite_id, {}):
            tasks = tasks_by_composite_id[composite_id]['unknown']
            task_ids = [t['TaskID'] for t in tasks]
            crops = list(set(t['Crop'] for t in tasks))
            task_summary.append({
                'Year': None,
                'TaskCount': len(tasks),
                'TaskIDs': task_ids,
                'Crops': crops
            })
        
        # Extract years from task summary for easier filtering
        years = [t['Year'] for t in task_summary if t['Year'] is not None]
        years_str = ', '.join(str(y) for y in sorted(years)) if years else None
        
        feature = {
            'type': 'Feature',
            'properties': {
                'CompositeID': composite_id,  # e.g., 'TASKDATA/PFD1'
                'FieldID': field_data['pfd_id'],
                'Folder': field_data['folder'],
                'FieldName': field_data['name'],
                'Years': years_str,  # e.g., '2024, 2025'
                'YearList': years,  # e.g., [2024, 2025]
                'TaskYears': task_summary,
                'TotalTasks': sum(len(tasks_by_composite_id[composite_id].get(y, [])) 
                                   for y in tasks_by_composite_id.get(composite_id, {}).keys()),
                'Source': field_data['source']
            },
            'geometry': field_data['geom']
        }
        features.append(feature)
    
    geojson_obj = {'type': 'FeatureCollection', 'features': features}
    
    outp = Path(out_path)
    outp.parent.mkdir(parents=True, exist_ok=True)
    
    with outp.open('w', encoding='utf-8') as f:
        json.dump(geojson_obj, f, indent=2)
    
    return 0




def main(argv=None) -> int:
    """Console entry point for extracting unique fields from TASKDATA -> GeoJSON.

    Accepts optional arguments: [src_folder] [src_folder2 ...] [--out output.geojson]
    
    Examples:
        pyagri-extract data/TASKDATA
        pyagri-extract data/TASKDATA data/TASKDATA\ 2 --out data/fields.geojson
    
    Returns exit code (0 success).
    """
    parser = argparse.ArgumentParser(description='Extract unique fields from TASKDATA -> GeoJSON')
    parser.add_argument('src', nargs='*', default=['data/TASKDATA'], help='Path(s) to TaskData folder(s)')
    parser.add_argument('--out', '-o', default='data/harvest_fields.geojson', help='Output GeoJSON file')
    args = parser.parse_args(argv)
    
    src_folders = args.src if args.src else ['data/TASKDATA']
    try:
        return extract_unique_fields_to_geojson(src_folders, args.out)
    except FileNotFoundError as e:
        print(e, file=sys.stderr)
        return 2


if __name__ == '__main__':
    sys.exit(main())
