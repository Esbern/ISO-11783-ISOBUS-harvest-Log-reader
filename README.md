# pyAgriculture11783
This is a package to read TASKDATA.xml, TLG.xml and TLG.bin files in Python. 
The project is under development and feedback is apritiated!

The idea is to give a path to the xml/bin files and extract the data as pandas dataframes. The following code snipped is 
an example of how the data extraction are suppose to work. 

    from pandas import ExcelWriter
    py_agri = PyAgriculture('path/to/TaskData/')
    py_agri.gather_data()
    
    writer = ExcelWriter('PythonExport.xlsx')
    for i in range(len(py_agri.tasks)):
        if isinstance(py_agri.tasks[i], pd.DataFrame):
            py_agri.tasks[i].to_excel(writer, 'Sheet' + str(i))
    writer.save()
    
## Installation (recommended: micromamba/conda)

This repository is now focused on reading TLG XML and BIN files and exporting
them to CSV. The minimal environment needed is Python with `numpy`, `pandas`
and `Cython` if you plan to build the optional Cython extension.

Create the environment with micromamba (recommended) or conda using the
provided `environment.yml`:

```bash
# using micromamba
micromamba create -f environment.yml -n pyagri -y
micromamba activate pyagri

# or using conda
conda env create -f environment.yml -n pyagri
conda activate pyagri
```

Then install the package in editable mode for development:

```bash
pip install -e .
```

If you prefer a pure-`pip` workflow, create a virtualenv and run:

```bash
pip install -r requirements.txt
pip install -e .
```

## Code organization

- **pyAgriculture/**: main package
    - `agriculture.py`: core reader (`PyAgriculture`) — parses `TASKDATA.xml`, TLG XML and BIN files and converts device output into `pandas.DataFrame` objects.
    - `export.py`: small CLI helper to export discovered tasks to CSV files.
    - `sorting_utils.py`: small XML-to-dict and lookup helpers used by the parsers.
    - `errors.py`: lightweight exception helper used by non-GUI code.

If you want, I can expand the docstrings further, add type hints across the codebase, or run `pytest` inside a micromamba environment next.

## Environments

Use two separate conda environments to keep the library dependencies minimal and provide a richer environment for notebooks that do validation, projection, plotting and kriging.

- `environment-core.yml`: minimal environment for developing the library (raw file reading). Use for building and running unit tests.
- `environment-notebooks.yml`: full environment for interactive work — includes `geopandas`, `pyproj`, `shapely`, `rasterio`, `pykrige`, `gstools`, plotting libraries and `jupyterlab`.

Create them with:

```bash
conda env create -f environment-core.yml
conda env create -f environment-notebooks.yml
```

Activate the notebooks environment to run and work on notebooks that perform projection, plotting and kriging.

## CLI Commands

After installing the package in editable mode (`pip install -e .`) the package provides a small CLI utility and there is also a converter script for one-off conversions.

- **Extract fields -> GeoJSON**: installs the console script `pyagri-extract` that parses `TASKDATA.xml` and writes a GeoJSON file of field polygons and task metadata.

```bash
# example (micromamba environment active)
pyagri-extract data/TASKDATA data/harvest_fields.geojson
```

- **Convert TaskData -> CSV**: use the provided converter to export task CSVs. Either run the script directly or use the package export module:

```bash
# run the script directly
python scripts/convert_taskdata.py data/TASKDATA data/ledreborg_CSV

# or via the package module
python -m pyAgriculture.export data/TASKDATA data/ledreborg_CSV
```

Both commands assume you are in the repository root or adjust paths accordingly.