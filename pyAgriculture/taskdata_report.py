"""Utilities to summarize TASKDATA.xml into a readable report.

Functions
- format_iso_time: friendly ISO time formatter.
- parse_isoxml_taskdata: returns nested dict farm -> year -> field -> tasks.
- taskdata_report: prints a text report and returns the nested dict.
- taskdata_report_df: flattens the report into a pandas DataFrame.
"""
from collections import defaultdict
from datetime import datetime
from pathlib import Path
import xml.etree.ElementTree as ET
from typing import Dict, List, Any

try:
    import pandas as pd
except Exception:  # pragma: no cover - pandas is expected to be installed
    pd = None


def format_iso_time(iso_str: str) -> str:
    """Convert ISO 8601 string to 'YYYY-MM-DD HH:MM:SS' (best effort)."""
    if not iso_str:
        return "Unknown"
    try:
        dt_str = iso_str.split('.')[0]
        return dt_str.replace('T', ' ')
    except Exception:
        return iso_str


def parse_isoxml_taskdata(file_path: Path) -> Dict[str, Any]:
    tree = ET.parse(file_path)
    root = tree.getroot()

    # 1. Farms
    farms = {frm.attrib.get('A'): frm.attrib.get('B', 'Unknown Farm') for frm in root.findall('FRM')}

    # 2. Fields
    fields = {}
    for pfd in root.findall('PFD'):
        pfd_id = pfd.attrib.get('A')
        name = pfd.attrib.get('C') or pfd.attrib.get('B') or f"Field {pfd_id}"
        fields[pfd_id] = name

    # 3. Products
    products = {pdt.attrib.get('A'): pdt.attrib.get('B', 'Unknown Product') for pdt in root.findall('PDT')}

    # 4. Device data (DVC/DET/DPD/DVP)
    det_to_dvc = {}
    dvc_info = {}

    for dvc in root.findall('DVC'):
        dvc_id = dvc.attrib.get('A')
        """Legacy stub for the old camelCase package.

        This module is kept only to avoid import errors; the active implementation
        is in `pyagri.taskdata_report` (lowercase package)."""

        from pyagri.taskdata_report import *  # noqa: F401,F403
    if pd is None:
        raise ImportError("pandas is required for taskdata_report_df")

    report_data = parse_isoxml_taskdata(file_path)
    rows = []
    for farm, years in report_data.items():
        for year, fields in years.items():
            for field, tasks in fields.items():
                for task in tasks:
                    rows.append({
                        'Farm': farm,
                        'Year': year,
                        'Field': field,
                        'TaskID': task['TaskID'],
                        'Machine': task['Machine'],
                        'Crop': task['Crop'],
                        'TimeRange': task['TimeRange'],
                        'TLGs': ', '.join(task['TLGs']) if task['TLGs'] else '',
                        'Properties': '; '.join(task['Properties']) if task['Properties'] else '',
                    })
    return pd.DataFrame(rows)
