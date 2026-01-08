# CLAAS Telematics ISO-11783 Forensic Log Reader

## Overview
This tool is a specialized Python parser for agricultural harvest data exported from **CLAAS Telematics** (CLAAS Connect). 

Standard ISO-11783 reading tools often fail with these specific log files (`TLG...BIN`) because the data stream is wrapped in a proprietary framing protocol. This project implements a **Forensic Packet Scanner** that bypasses the proprietary overhead to extract the raw ISO 11783-10 (Type 1) data.

It links the binary sensor data with the `TASKDATA.XML` metadata to generate a fully validated, research-grade dataset including:
* **True GPS Speed** (calculated to replace broken speed sensors).
* **Crop Density** (physics-based verification).
* **Yield Calculation** (corrected for crop type and machine state).

## Key Findings: The Data Structure
Through forensic binary analysis, the proprietary stream was reverse-engineered. The scanner identifies a dynamic **Fixed-Frame Packet Structure**:

1.  **Harvest Mode:** Data is transmitted in **93-byte frames**, consisting of a **68-byte payload** (standard ISO 11783-10 Type 1 records) wrapped in a **25-byte proprietary overhead** (likely checksums and CAN identifiers).
2.  **Transport/Idle Mode:** The frame structure shifts to a reduced format with a **10-byte overhead**.

This tool automatically detects these headers ("Header Gap") to maintain sync with the data stream.

## Features
* **Universal Geofencing:** Automatically detects field boundaries from `TASKDATA.XML`.
* **Multi-Year Support:** Handles complex task files spanning multiple harvest seasons.
* **Physics-Based Validation:** * Calculates `Density (kg/L)` to differentiate between valid crop flow and machine idling.
    * Corrects a known **10x scaling factor** in the raw volume data for specific crop types.
* **GPS Speed Derivation:** Re-calculates speed (`Distance / Time`) from coordinates to fix sensor dropouts.
* **Header Monitor:** Outputs a log of skipped bytes (`HEADER_GAP_MONITOR.csv`) to validate the parsing integrity.

## Installation

This project uses a Conda environment.

1.  Clone the repository.
2.  Install dependencies:
    ```bash
    conda env create -f environment.yml
    conda activate agri_analysis
    ```
3.  Place your `TASKDATA.XML` and `TLG...BIN` files in the `./data/taskdata/` folder.

## Usage
Run the Jupyter Notebook:
```bash
jupyter lab ISO11783_TaskData.ipynb