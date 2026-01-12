"""TASKDATA XML reporting helpers (pyagri).

Functions:
- format_iso_time: friendly ISO time formatter.
- parse_taskdata_to_dataframe: reads TASKDATA and returns normalized DataFrame with all properties.
- generate_report_from_dataframe: formats a DataFrame into human-readable text report.
- taskdata_report: convenience function that combines both (legacy).
"""
from collections import defaultdict
from datetime import datetime
from pathlib import Path
import xml.etree.ElementTree as ET
from typing import Dict, List, Any, Tuple

try:
    import pandas as pd
except Exception:  # pragma: no cover - pandas is expected
    pd = None


def format_iso_time(iso_str: str) -> str:
    if not iso_str:
        return "Unknown"
    try:
        dt_str = iso_str.split('.')[0]
        return dt_str.replace('T', ' ')
    except Exception:
        return iso_str


def _parse_property_entry(prop: str) -> Tuple[str, Any]:
    """Return (name, parsed_value) from a "Name: value unit" string."""
    if ':' not in prop:
        return prop.strip(), None
    name, value_part = prop.split(':', 1)
    value_part = value_part.strip()
    if not value_part:
        return name.strip(), None
    # Try to coerce numeric values; keep string on failure.
    tokens = value_part.split()
    numeric_candidate = tokens[0].replace(',', '')
    try:
        if '.' in numeric_candidate:
            value = float(numeric_candidate)
        else:
            value = int(numeric_candidate)
        return name.strip(), value
    except Exception:
        return name.strip(), value_part


def parse_taskdata_to_dataframe(file_paths: List[Path], output_csv: str = None) -> 'pd.DataFrame':
    """Parse one or more TASKDATA.XML files into a normalized DataFrame.
    
    Returns a DataFrame with columns: Farm, Year, Field, CompositeFieldID, Folder,
    FieldID, TaskID, Machine, Crop, Start, End, TimeRange, TLGs, and one column
    per property (e.g., Fugtighed, Tørstofindhold, etc.).
    
    Args:
        file_paths: List of Path objects to TASKDATA.XML files
        output_csv: Optional path to save CSV (readable by QGIS)
    
    Returns:
        Normalized pandas DataFrame
    """
    if pd is None:
        raise ImportError("pandas is required for parse_taskdata_to_dataframe")
    
    if not isinstance(file_paths, list):
        file_paths = [file_paths]
    
    all_task_rows = []
    all_prop_names = set()
    
    for file_path in file_paths:
        file_path = Path(file_path)  # Convert to Path if string
        folder_name = file_path.parent.name  # e.g., 'TASKDATA' or 'TASKDATA 2'
        
        tree = ET.parse(file_path)
        root = tree.getroot()

        farms = {frm.attrib.get('A'): frm.attrib.get('B', 'Unknown Farm') for frm in root.findall('FRM')}

        fields = {}
        for pfd in root.findall('PFD'):
            pfd_id = pfd.attrib.get('A')
            name = pfd.attrib.get('C') or pfd.attrib.get('B') or f"Field {pfd_id}"
            fields[pfd_id] = name

        products = {pdt.attrib.get('A'): pdt.attrib.get('B', 'Unknown Product') for pdt in root.findall('PDT')}

        det_to_dvc = {}
        dvc_info = {}

        for dvc in root.findall('DVC'):
            dvc_id = dvc.attrib.get('A')
            dvc_name = dvc.attrib.get('B', 'Unknown Machine')

            for det in dvc.findall('.//DET'):
                det_to_dvc[det.attrib.get('A')] = dvc_id

            dvp_map = {}
            for dvp in dvc.findall('.//DVP'):
                try:
                    dvp_id = dvp.attrib.get('A')
                    dvp_map[dvp_id] = {
                        'scale': float(dvp.attrib.get('C', 1)),
                        'offset': float(dvp.attrib.get('B', 0)),
                        'unit': dvp.attrib.get('E', ''),
                    }
                except Exception:
                    continue

            dpd_map = {}
            for dpd in dvc.findall('.//DPD'):
                ddi = dpd.attrib.get('B')
                prop_name = dpd.attrib.get('E', f"DDI_{ddi}")
                dvp_ref = dpd.attrib.get('F')
                dpd_map[ddi] = {'name': prop_name, 'dvp': dvp_map.get(dvp_ref)}

            dvc_info[dvc_id] = {'name': dvc_name, 'dpds': dpd_map}

        for tsk in root.findall('TSK'):
            tsk_id = tsk.attrib.get('A')
            field_ref = tsk.attrib.get('E')
            field_name = fields.get(field_ref, f"Unknown Field ({field_ref})")
            composite_field_id = f"{folder_name}/{field_ref}"

            task_crops = [products[pan.attrib.get('A')] for pan in tsk.findall('PAN') if pan.attrib.get('A') in products]
            crop_name = ", ".join(task_crops) if task_crops else "None"

            dan = tsk.find('DAN')
            machine_name = "Generic Machine"
            dvc_id_for_task = None
            if dan is not None:
                dvc_id_for_task = dan.attrib.get('C')
                if dvc_id_for_task in dvc_info:
                    machine_name = dvc_info[dvc_id_for_task]['name']

            tlg_files = [tlg.attrib.get('A') for tlg in tsk.findall('TLG')]
            # Create composite TLG IDs for joining with TLG CSV files
            composite_tlg_ids = [f"{folder_name}/{tlg_id}" for tlg_id in tlg_files if tlg_id]

            start_times: List[str] = []
            end_times: List[str] = []
            logged_values: List[str] = []

            for tim in tsk.findall('TIM'):
                if 'A' in tim.attrib:
                    start_times.append(tim.attrib['A'])
                if 'B' in tim.attrib:
                    end_times.append(tim.attrib['B'])

                for dlv in tim.findall('DLV'):
                    ddi = dlv.attrib.get('A')
                    raw_value = int(dlv.attrib.get('B', 0))
                    det_ref = dlv.attrib.get('C')

                    prop_name = f"DDI {ddi}"
                    final_val = raw_value
                    unit = ""

                    if ddi == '0106':
                        prop_name = "Fugtighed"
                        final_val = raw_value * 0.0001
                        unit = "%"
                    elif ddi == '013B':
                        prop_name = "Tørstofindhold"
                        final_val = raw_value * 0.0001
                        unit = "%"
                    else:
                        current_dvc_id = det_to_dvc.get(det_ref, dvc_id_for_task)
                        if current_dvc_id and current_dvc_id in dvc_info:
                            dvc_defs = dvc_info[current_dvc_id]['dpds']
                            if ddi in dvc_defs:
                                def_info = dvc_defs[ddi]
                                prop_name = def_info['name']
                                if def_info['dvp']:
                                    dvp = def_info['dvp']
                                    final_val = (raw_value * dvp['scale']) + dvp['offset']
                                    unit = dvp['unit']
                                elif ddi == '0074':
                                    unit = "m²"
                                elif ddi == '005A':
                                    unit = "kg"

                    val_str = f"{final_val:,.2f}" if isinstance(final_val, float) else str(final_val)
                    entry = f"{prop_name}: {val_str} {unit}".rstrip()
                    if entry not in logged_values:
                        logged_values.append(entry)

            start_ts = min(start_times) if start_times else None
            end_ts = max(end_times) if end_times else None
            year = start_ts[:4] if start_ts else "Unknown Year"
            time_range = f"{format_iso_time(start_ts)} - {format_iso_time(end_ts)}"

            # Parse properties into columns
            prop_map = {}
            for prop in logged_values:
                name, value = _parse_property_entry(prop)
                all_prop_names.add(name)
                prop_map[name] = value

            farm_name = list(farms.values())[0] if farms else "Unknown Farm"
            
            base_row = {
                'Farm': farm_name,
                'Year': year,
                'Field': field_name,
                'CompositeFieldID': composite_field_id,
                'Folder': folder_name,
                'FieldID': field_ref,
                'TaskID': tsk_id,
                'Machine': machine_name,
                'Crop': crop_name,
                'Start': format_iso_time(start_ts),
                'End': format_iso_time(end_ts),
                'TimeRange': time_range,
                'TLGs': ', '.join(tlg_files) if tlg_files else '',
                'CompositeTLGIDs': ', '.join(composite_tlg_ids) if composite_tlg_ids else '',
            }
            base_row.update(prop_map)
            all_task_rows.append(base_row)
    
    # Ensure all property columns exist for every row
    for row in all_task_rows:
        for prop_name in all_prop_names:
            row.setdefault(prop_name, None)

    ordered_cols = [
        'Farm',
        'Year',
        'Field',
        'CompositeFieldID',
        'Folder',
        'FieldID',
        'TaskID',
        'Machine',
        'Crop',
        'Start',
        'End',
        'TimeRange',
        'TLGs',
        'CompositeTLGIDs',
    ] + sorted(all_prop_names)

    df = pd.DataFrame(all_task_rows)[ordered_cols]
    
    if output_csv:
        csv_path = Path(output_csv)
        csv_path.parent.mkdir(parents=True, exist_ok=True)
        df.to_csv(csv_path, index=False)
        print(f"Saved task data to {csv_path}")
    
    return df


# Legacy function - wrapper for compatibility  
def parse_isoxml_taskdata(file_path: Path) -> Dict[str, Any]:
    """Legacy function - parses single TASKDATA file into nested dict."""
    df = parse_taskdata_to_dataframe([file_path])
    
    # Convert back to nested dict for compatibility
    report_data = defaultdict(lambda: defaultdict(lambda: defaultdict(list)))
    
    for _, row in df.iterrows():
        farm = row['Farm']
        year = row['Year']
        field = row['Field']
        
        # Collect properties
        props = []
        for col in df.columns:
            if col not in ['Farm', 'Year', 'Field', 'CompositeFieldID', 'Folder', 'FieldID',
                           'TaskID', 'Machine', 'Crop', 'Start', 'End', 'TimeRange', 'TLGs']:
                if pd.notna(row[col]):
                    if isinstance(row[col], float):
                        props.append(f"{col}: {row[col]:,.2f}")
                    else:
                        props.append(f"{col}: {row[col]}")
        
        task_info = {
            'TaskID': row['TaskID'],
            'Machine': row['Machine'],
            'Crop': row['Crop'],
            'TimeRange': row['TimeRange'],
            'StartTime': row['Start'],
            'EndTime': row['End'],
            'TLGs': row['TLGs'].split(', ') if row['TLGs'] else [],
            'Properties': props,
        }
        report_data[farm][year][field].append(task_info)
    
    return dict(report_data)


def taskdata_report(file_path: Path) -> Dict[str, Any]:
    """Legacy function - prints report and returns nested dict."""
    df = parse_taskdata_to_dataframe([file_path])
    report = generate_report_from_dataframe(df)
    print(report)
    return parse_isoxml_taskdata(file_path)


def taskdata_report_df(file_path: Path):
    """Legacy function - returns DataFrame from single file."""
    return parse_taskdata_to_dataframe([file_path])


# Backward-compatible alias
parse_taskdata_xml = parse_isoxml_taskdata

