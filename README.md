# pyagri
This is a package to read TASKDATA.xml, TLG.xml and TLG.bin files in Python. 
once data is read from the ISO-11783 format TASKDATA.xml, TLG.xml and TLG.bin it can be calidatet visualised and postprossed using a serise og jupyter notbooks. The IS0-11783 reading is based on a downscaled version of the project pyAgriculture11783 https://github.com/axelande/pyAgriculture11783
The project is under development and feedback is apritiated!

    
## Installation (recommended: micromamba/conda)



## Code organization

- **pyagri/**: main package (renamed from `pyAgriculture`)
    - `agriculture.py`: core reader (`PyAgriculture`) — parses `TASKDATA.xml`, TLG XML and BIN files and converts device output into `pandas.DataFrame` objects.
    - `export.py`: small CLI helper to export discovered tasks to CSV files.


If you want, I can expand the docstrings further, add type hints across the codebase, or run `pytest` inside a micromamba environment next.

## Environments

Use two separate conda environments to keep the library dependencies minimal and provide a richer environment for notebooks that do validation, projection, plotting and kriging.

- `environment-core.yml`: minimal environment for developing the library (raw file reading). Use for building and running unit tests.
- `environment-notebooks.yml`: full environment for interactive work — includes `geopandas`, `pyproj`, `shapely`, `rasterio`, `pykrige`, `gstools`, plotting libraries and `jupyterlab`.

Create them with:

```bash
micromamba env create -f environment-core.yml
micromamba env create -f environment-notebooks.yml
```
install the libary in edit mode
pip install . -e

Activate the notebooks environment to run and work on notebooks that perform projection, plotting and kriging.

## Running tests

- Install pytest if you don't have it: `pip install pytest`
- Run the test suite from the repository root: `pytest -q`

Notes:
- Tests use `tmp_path` and `monkeypatch` to avoid modifying repository files.
- The project has a small unit-test set that verifies exporter behavior and the Cython availability handling.

## CLI Commands

After installing the package in editable mode (`pip install -e .`) the package provides a small CLI utility and there is also a converter script for one-off conversions.

- **Extract fields -> GeoJSON**: installs the console script `pyagri-extract` that parses `TASKDATA.xml` and writes a GeoJSON file of field polygons and task metadata. If the output GeoJSON already exists and is a FeatureCollection, new task features will be appended instead of overwriting.

```bash
# example (micromamba environment active)
python -m pyagri.geo data/TASKDATA data/harvest_fields.geojson
```

- **Convert TaskData -> CSV**: use the provided converter to export task CSVs. Either run the script directly or use the package export module:

```bash
# run the script directly
python scripts/convert_taskdata.py data/TASKDATA data/ledreborg_CSV

# or via the package module
python -m pyagri.export data/TASKDATA data/ledreborg_CSV
```

Both commands assume you are in the repository root or adjust paths accordingly.

> **Note:** When exporting, the exporter now *appends* to existing CSV files for tasks with the same name instead of overwriting. This preserves multiple years or runs for the same field; you can split or reorganize the combined CSVs later as needed.

**Note on rename:** The package has been renamed to **`pyagri`** (lowercase). Importing the old `pyAgriculture` package will still work during migration but will emit a `DeprecationWarning` telling you to import `pyagri` instead.