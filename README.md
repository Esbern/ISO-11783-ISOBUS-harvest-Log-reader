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