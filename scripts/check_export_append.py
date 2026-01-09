"""Quick check script that verifies the exporter appends to existing CSVs.

Run with: python scripts/check_export_append.py
"""
import pandas as pd
import tempfile
from pathlib import Path
from pyagri import export as export_mod

# Prepare sample dataframes
df1 = pd.DataFrame({"a": [1, 2], "b": ["x", "y"]})
df1.attrs["task_name"] = "Test Task"
df2 = pd.DataFrame({"a": [3], "b": ["z"]})
df2.attrs["task_name"] = "Test Task"

class FakePa:
    def __init__(self, tasks):
        self.tasks = tasks
    def gather_data(self, *args, **kwargs):
        return

# Use a simple sequence to simulate two separate exports
tasks_sequence = [[df1], [df2]]

def fake_constructor(path):
    return FakePa(tasks_sequence.pop(0))

export_mod.PyAgriculture = fake_constructor

with tempfile.TemporaryDirectory() as td:
    out_dir = Path(td) / "out"
    out_dir.mkdir()

    export_mod.export_taskdata("/fake/path", str(out_dir))
    out_files = list(out_dir.glob("*.csv"))
    if not out_files:
        raise SystemExit("First export failed: no CSV written")
    out_path = out_files[0]
    df_read = pd.read_csv(out_path)
    assert len(df_read) == 2, f"Expected 2 rows after first export, got {len(df_read)}"

    export_mod.export_taskdata("/fake/path", str(out_dir))
    df_read2 = pd.read_csv(out_path)
    assert len(df_read2) == 3, f"Expected 3 rows after second export (append), got {len(df_read2)}"

    print("Append behavior verified: CSV now has", len(df_read2), "rows")