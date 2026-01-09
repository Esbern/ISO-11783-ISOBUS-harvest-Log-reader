from pathlib import Path
import sys
import os

import pytest

from scripts import convert_taskdata as conv_script


def test_convert_taskdata_main_calls_export(tmp_path, monkeypatch, capsys):
    # Create a fake source path with TaskData.xml to satisfy the script check
    src = tmp_path / 'TaskDataDir'
    src.mkdir()
    (src / 'TaskData.xml').write_text('<TaskData></TaskData>')

    out = tmp_path / 'out'

    called = {}

    def fake_export(path, out_dir=None):
        # ensure path is the src string and out_dir equals out
        called['path'] = path
        called['out_dir'] = out_dir
        # simulate writing a file
        p = Path(out_dir) / 'fake.csv'
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text('a,b\n1,2')
        return [str(p)]

    monkeypatch.setattr('pyagri.export.export_taskdata', fake_export)

    conv_script.main([str(src), str(out)])

    captured = capsys.readouterr()
    assert 'Wrote:' in captured.out
    assert called['path'] == str(src)
    assert called['out_dir'] == str(out)
    # ensure file exists
    assert (out / 'fake.csv').exists()
