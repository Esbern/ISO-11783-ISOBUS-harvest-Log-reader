"""Convert TASKDATA to CSV using pyAgriculture.export

Usage:
    python scripts/convert_taskdata.py [source_taskdata_dir] [output_dir]

Defaults:
    source: data/TASKDATA
    output: data/ledreborg_CSV
"""
from pathlib import Path
import sys

from pyAgriculture.export import export_taskdata


def main(argv=None):
    if argv is None:
        argv = sys.argv[1:]
    src = argv[0] if len(argv) > 0 else 'data/TASKDATA'
    out = argv[1] if len(argv) > 1 else 'data/ledreborg_CSV'
    src_path = Path(src)
    if not src_path.exists():
        print(f"Source path '{src}' does not exist.")
        raise SystemExit(2)
    written = export_taskdata(str(src_path), str(out))
    if written:
        print('Wrote:', '\n'.join(written))
    else:
        print('No tasks exported.')


if __name__ == '__main__':
    main()
