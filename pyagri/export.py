"""Command-line helper to export TLG tasks to CSV files.

Usage:
    python -m pyagri.export /path/to/TaskData/ [output_dir]

This uses `PyAgriculture` to gather tasks and writes each DataFrame to a
CSV file named using `df.attrs['task_name']` (falling back to index).
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

    Returns list of written file paths.
    """
    pa = PyAgriculture(path)
    # Use a guaranteed-present column so tasks are not filtered out
    pa.gather_data(most_important='time_stamp', continue_on_fail=True)
    if out_dir is None:
        out_dir = os.getcwd()
    Path(out_dir).mkdir(parents=True, exist_ok=True)
    written = []
    for i, df in enumerate(pa.tasks):
        if not isinstance(df, pd.DataFrame):
            continue
        name = df.attrs.get('task_name') or f'task_{i}'
        safe_name = ''.join(c if c.isalnum() or c in (' ', '-', '_') else '_' for c in name).strip()
        out_path = Path(out_dir) / f"{safe_name}.csv"
        # Append to existing CSVs instead of overwriting so multi-year
        # exports for the same task are preserved and can be split later.
        exists = out_path.exists()
        if exists:
            # Append without header to avoid duplicate header rows
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
