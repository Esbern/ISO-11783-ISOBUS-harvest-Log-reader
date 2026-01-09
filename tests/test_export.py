import pandas as pd
from pathlib import Path
from pyagri import export as export_mod


def test_export_appends(tmp_path, monkeypatch):
    # Prepare two small dataframes with identical columns
    df1 = pd.DataFrame({"a": [1, 2], "b": ["x", "y"]})
    df1.attrs["task_name"] = "Test Task"
    df2 = pd.DataFrame({"a": [3], "b": ["z"]})
    df2.attrs["task_name"] = "Test Task"

    # A simple fake PyAgriculture that returns a given tasks list
    class FakePa:
        def __init__(self, tasks):
            self.tasks = tasks

        def gather_data(self, *args, **kwargs):
            return

    tasks_sequence = [[df1], [df2]]

    def fake_constructor(path):
        return FakePa(tasks_sequence.pop(0))

    # Patch the constructor used inside export_taskdata
    monkeypatch.setattr(export_mod, "PyAgriculture", fake_constructor)

    out_dir = tmp_path / "out"
    out_dir.mkdir()

    # First export: creates file with header + df1 rows
    written1 = export_mod.export_taskdata("/fake/path", str(out_dir))
    assert len(written1) == 1
    out_path = Path(written1[0])
    assert out_path.exists()
    read1 = pd.read_csv(out_path)
    assert len(read1) == 2
    assert list(read1.columns) == ["a", "b"]

    # Second export: appends df2 rows to the same file
    written2 = export_mod.export_taskdata("/fake/path", str(out_dir))
    assert len(written2) == 1
    read2 = pd.read_csv(out_path)
    assert len(read2) == 3
    assert list(read2.columns) == ["a", "b"]
