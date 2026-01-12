"""Command-line helper to export TLG tasks to CSV files.

Usage:
    python -m pyagri.export /path/to/TaskData/ [output_dir]

This uses `PyAgriculture` to gather tasks and writes each DataFrame to a
CSV file named using composite TLG ID (folder_name/TLG_ID.csv).
Each CSV includes a 'CompositeTLGID' column for joining with task.csv.
"""
from __future__ import annotations
import sys
import os
from pathlib import Path
from typing import Optional

import pandas as pd

from .agriculture import PyAgriculture


def export_taskdata(path: str, out_dir: Optional[str] = None) -> list:
    """Read TLG XML/BIN files from `path` and export discovered tasks to CSV.
    
    Each TLG file is saved with composite ID: folder_name/TLG_ID.csv
    Adds 'CompositeTLGID' column to each CSV for joining with task.csv.
    
    Returns list of written file paths.
    """
    src_path = Path(path)
    folder_name = src_path.name  # e.g., 'TASKDATA' or 'TASKDATA 2'
    
    pa = PyAgriculture(path)
    # Use a guaranteed-present column so tasks are not filtered out
    pa.gather_data(most_important='time_stamp', continue_on_fail=True)
    if out_dir is None:
        out_dir = os.getcwd()
    
    out_base = Path(out_dir)
    out_base.mkdir(parents=True, exist_ok=True)
    
    written = []
    for i, df in enumerate(pa.tasks):
        if not isinstance(df, pd.DataFrame):
            continue
        
        # Extract TLG file path from task attributes
        tlg_file = df.attrs.get('tlg_file', '')
        task_name = df.attrs.get('task_name', f'task_{i}')
        
        if not tlg_file:
            # Fallback: try to extract from task_name
            tlg_id = task_name.split('_')[0] if '_' in task_name else task_name
        else:
            # Extract TLG ID from file path (e.g., 'data/TASKDATA/TLG00001' -> 'TLG00001')
            tlg_path = Path(tlg_file)
            # Remove .bin extension if present
            tlg_id = tlg_path.stem  # Gets filename without extension
        
        # Create composite TLG ID
        composite_tlg_id = f"{folder_name}/{tlg_id}"
        
        # Add CompositeTLGID column to dataframe
        df = df.copy()
        df.insert(0, 'CompositeTLGID', composite_tlg_id)
        
        # Save with composite naming: folder_name-TLG_ID.csv
        safe_folder = folder_name.replace(' ', '_')
        safe_tlg = tlg_id.replace(' ', '_').replace('/', '-')
        out_filename = f"{safe_folder}-{safe_tlg}.csv"
        out_path = out_base / out_filename
        
        # Append to existing CSVs instead of overwriting
        exists = out_path.exists()
        if exists:
            # Append without header
            df.to_csv(out_path, index=False, mode='a', header=False)
        else:
            df.to_csv(out_path, index=False)
        written.append(str(out_path))
    
    return written


def main(argv=None):
    if argv is None:
        argv = sys.argv[1:]
    if len(argv) == 0:
        print("Usage: pyagri.export <path-to-TaskData> [output-dir]")
        raise SystemExit(2)
    path = argv[0]
    out_dir = argv[1] if len(argv) > 1 else None
    written = export_taskdata(path, out_dir)
    if written:
        print('Wrote:', '\n'.join(written))
    else:
        print('No tasks exported.')


if __name__ == '__main__':
    main()
