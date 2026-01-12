# TLG Data Management Workflow

## Overview

TLG (Time Log) files contain the actual harvest data points collected by combines. This document describes how to manage TLG data using composite IDs for proper tracking across multiple TASKDATA folders and preparing data for large-scale spatial analysis.

## Problem Statement

- **Multiple TASKDATA sources**: One year's harvest data may be split across multiple TASKDATA folders (e.g., `TASKDATA`, `TASKDATA 2`)
- **No unique field names**: Some fields lack names, making them hard to track
- **Large datasets**: TLG files can contain millions of data points, requiring efficient database queries
- **Need for joins**: Analysis requires joining TLG points → tasks → fields → geometries

## Solution: Composite ID System

### Components

1. **CompositeFieldID**: `folder_name/field_id` (e.g., `TASKDATA/PFD43`)
   - Maintains separate geometry definitions when same field has different shapes across folders
   - Used in GeoJSON features and task.csv

2. **CompositeTLGID**: `folder_name/TLG_ID` (e.g., `TASKDATA/TLG00001`)
   - Uniquely identifies TLG files across all TASKDATA folders
   - Used in task.csv (CompositeTLGIDs column) and individual TLG CSV files (CompositeTLGID column)

### File Naming Convention

TLG CSV files are saved as: `{folder_name}-{TLG_ID}.csv`

Examples:
- `TASKDATA-TLG00001.csv`
- `TASKDATA_2-TLG00001.csv`

## Workflow Steps

### 1. Export TLG Files to CSV

```python
from pyagri.export import export_taskdata

# Export TLG files from each TASKDATA folder
files = export_taskdata('data/TASKDATA', 'data/tlg_csvs')
files2 = export_taskdata('data/TASKDATA 2', 'data/tlg_csvs')
```

Each TLG CSV file contains:
- **CompositeTLGID** column (first column): For joining with task.csv
- All original TLG data columns (timestamp, lat/lon, yield, moisture, etc.)

### 2. Generate Task Metadata

```python
from pyagri.taskdata_report import parse_taskdata_to_dataframe

taskdata_paths = [
    'data/TASKDATA/TASKDATA.XML',
    'data/TASKDATA 2/TASKDATA.XML'
]

df = parse_taskdata_to_dataframe(taskdata_paths, 'data/tasks.csv')
```

The resulting `tasks.csv` contains:
- **CompositeFieldID**: For joining with GeoJSON
- **CompositeTLGIDs**: Comma-separated list of TLG files for this task (e.g., `TASKDATA/TLG00001, TASKDATA/TLG00002`)
- Task metadata: Farm, Year, Field, Machine, Crop, Start, End, etc.
- Property columns: Yield, Moisture, etc.

### 3. Load TLG Data into DuckDB

```python
from pyagri.duckdb_loader import create_tlg_database

# Create database from all TLG CSV files
conn = create_tlg_database('data/tlg_csvs', db_path='data/tlg_points.duckdb')

# Or use in-memory for faster queries (requires enough RAM)
conn = create_tlg_database('data/tlg_csvs', db_path=':memory:')
```

### 4. Query TLG Points by Task

```python
from pyagri.duckdb_loader import query_tlg_by_task
import pandas as pd

# Load tasks
tasks_df = pd.read_csv('data/tasks.csv')

# Find tasks matching criteria (e.g., year 2023, specific crop)
filtered_tasks = tasks_df[(tasks_df['Year'] == 2023) & (tasks_df['Crop'] == 'Majs')]

# Collect all CompositeTLGIDs
all_tlg_ids = []
for tlg_str in filtered_tasks['CompositeTLGIDs'].dropna():
    all_tlg_ids.extend(tlg_str.split(', '))

# Query DuckDB for these TLG points
points_df = query_tlg_by_task(conn, all_tlg_ids)
```

### 5. Join with Field Geometries

```python
import geopandas as gpd

# Load field geometries
fields_gdf = gpd.read_file('data/harvest_fields.geojson')

# Join tasks with fields on CompositeFieldID
tasks_with_geom = tasks_df.merge(
    fields_gdf[['CompositeID', 'geometry']],
    left_on='CompositeFieldID',
    right_on='CompositeID'
)

# Now you have task metadata + geometry
# Use CompositeTLGIDs to get actual data points from DuckDB
```

## Database Schema

### tlg_points Table (DuckDB)

```
CompositeTLGID  | VARCHAR  | Index for fast joins
time_stamp      | TIMESTAMP
latitude        | FLOAT
longitude       | FLOAT
position_status | VARCHAR
hastighed       | FLOAT
aktuelt_udbytte | FLOAT
fugtighed       | FLOAT
tørstofindhold  | FLOAT
... (other yield/quality columns)
```

### tasks.csv

```
Farm               | VARCHAR
Year               | INTEGER
Field              | VARCHAR
CompositeFieldID   | VARCHAR  | Join key for GeoJSON
Folder             | VARCHAR
FieldID            | VARCHAR
TaskID             | VARCHAR
Machine            | VARCHAR
Crop               | VARCHAR
Start              | TIMESTAMP
End                | TIMESTAMP
TimeRange          | VARCHAR
TLGs               | INTEGER   | Count of TLG files
CompositeTLGIDs    | VARCHAR   | Comma-separated list (e.g., "TASKDATA/TLG00001, TASKDATA/TLG00002")
... (property columns)
```

### harvest_fields.geojson

```json
{
  "type": "FeatureCollection",
  "features": [
    {
      "type": "Feature",
      "properties": {
        "CompositeID": "TASKDATA/PFD43",
        "FieldID": "PFD43",
        "Folder": "TASKDATA",
        "FieldName": "Monica",
        "Years": "2021, 2022, 2023",
        "YearList": [2021, 2022, 2023],
        "TaskYears": [
          {"year": 2021, "tasks": 3},
          {"year": 2022, "tasks": 2}
        ],
        "TotalTasks": 5
      },
      "geometry": { ... }
    }
  ]
}
```

## Example Analysis: Kriging for Specific Field

```python
import pandas as pd
import geopandas as gpd
from pyagri.duckdb_loader import query_tlg_by_task, create_tlg_database

# 1. Load data
tasks_df = pd.read_csv('data/tasks.csv')
fields_gdf = gpd.read_file('data/harvest_fields.geojson')
conn = create_tlg_database('data/tlg_csvs', db_path=':memory:')

# 2. Find field of interest
field_name = "Monica"
field_year = 2021

field_tasks = tasks_df[
    (tasks_df['Field'] == field_name) &
    (tasks_df['Year'] == field_year)
]

# 3. Get CompositeTLGIDs for these tasks
tlg_ids = []
for tlg_str in field_tasks['CompositeTLGIDs'].dropna():
    tlg_ids.extend(tlg_str.split(', '))

# 4. Query all points
points_df = query_tlg_by_task(conn, tlg_ids)

# 5. Perform kriging analysis
# points_df contains latitude, longitude, and yield columns
# Use pykrige or gstools for kriging interpolation
```

## Benefits

1. **Memory Efficient**: DuckDB handles large datasets without loading everything into RAM
2. **Fast Queries**: Indexed CompositeTLGID enables fast filtering
3. **Flexible Filtering**: Filter tasks by year/crop/field, then load only relevant TLG points
4. **Proper Tracking**: Composite IDs ensure data isn't mixed up across TASKDATA folders
5. **Reproducible**: All joins use consistent composite key system

## Files and Directories

```
data/
  ├── TASKDATA/           # Original TASKDATA folder
  ├── TASKDATA 2/         # Second TASKDATA folder
  ├── tlg_csvs/           # Exported TLG CSV files
  │   ├── TASKDATA-TLG00001.csv
  │   ├── TASKDATA-TLG00002.csv
  │   ├── TASKDATA_2-TLG00001.csv
  │   └── ...
  ├── tasks.csv           # Task metadata with CompositeFieldID and CompositeTLGIDs
  ├── harvest_fields.geojson  # Field geometries with CompositeID
  └── tlg_points.duckdb   # Optional: Persistent DuckDB database
```

## API Reference

See:
- [pyagri.export](../pyagri/export.py) - `export_taskdata()` function
- [pyagri.taskdata_report](../pyagri/taskdata_report.py) - `parse_taskdata_to_dataframe()` function
- [pyagri.duckdb_loader](../pyagri/duckdb_loader.py) - DuckDB integration functions
- [pyagri.geo](../pyagri/geo.py) - `extract_unique_fields_to_geojson()` function
