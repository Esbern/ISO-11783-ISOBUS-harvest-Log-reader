import xml.etree.ElementTree as ET
from pathlib import Path
from collections import defaultdict
import pandas as pd


def parse_taskdata_xml(xml_path):
    """
    Parse TASKDATA.XML and return a report structured by year and field.
    Returns a pandas DataFrame with columns: Year, Field, TaskID, TaskName, StartTime, EndTime, Device, Product, Details
    """
    tree = ET.parse(xml_path)
    root = tree.getroot()
    report_rows = []
    for tsk in root.findall('.//TSK'):
        task_id = tsk.attrib.get('A')
        field_name = tsk.attrib.get('B')
        product = tsk.attrib.get('E')
        details = tsk.attrib.get('G')
        # Crop info: try PAN E or other relevant attribute
        crop = None
        pan = tsk.find('.//PAN')
        if pan is not None:
            crop = pan.attrib.get('E')
        # Find year from ASP or TIM
        year = None
        start_time = None
        end_time = None
        for asp in tsk.findall('.//ASP'):
            dt = asp.attrib.get('A')
            if dt:
                year = dt[:4]
                start_time = dt
                break
        for tim in tsk.findall('.//TIM'):
            st = tim.attrib.get('A')
            et = tim.attrib.get('B')
            if st and not start_time:
                start_time = st
            if et:
                end_time = et
        device = None
        for dan in tsk.findall('.//DAN'):
            device = dan.attrib.get('C')
            break
        # TLG log reference
        tlg = None
        tlg_elem = tsk.find('.//TLG')
        if tlg_elem is not None:
            tlg = tlg_elem.attrib.get('A')
        # Sensors/channels used in TIM/DLV
        sensors = set()
        for tim in tsk.findall('.//TIM'):
            for dlv in tim.findall('.//DLV'):
                sensor = dlv.attrib.get('A')
                if sensor:
                    sensors.add(sensor)
        sensors_str = ', '.join(sorted(sensors)) if sensors else None
        # Compose row
        report_rows.append({
            'Year': year,
            'Field': field_name,
            'TaskID': task_id,
            'Product': product,
            'Crop': crop,
            'Details': details,
            'StartTime': start_time,
            'EndTime': end_time,
            'Device': device,
            'TLG': tlg,
            'Sensors': sensors_str,
        })
    df = pd.DataFrame(report_rows)
    df = df.sort_values(['Year', 'Field', 'StartTime'])
    return df


def taskdata_report_df(xml_path):
    """
    Return the parsed TASKDATA.XML report as a pandas DataFrame for notebook display.
    """
    df = parse_taskdata_xml(xml_path)
    return df

def taskdata_report(xml_path):
    """
    Print a human-readable report from TASKDATA.XML, grouped by year and field.
    """
    df = parse_taskdata_xml(xml_path)
    if df.empty:
        print("No tasks found in XML.")
        return
    for year in sorted(df['Year'].dropna().unique()):
        print(f"\nYear: {year}")
        df_year = df[df['Year'] == year]
        for field in sorted(df_year['Field'].dropna().unique()):
            print(f"  Field: {field}")
            df_field = df_year[df_year['Field'] == field]
            for _, row in df_field.iterrows():
                print(f"    Task {row['TaskID']}: Product={row['Product']} Device={row['Device']} Details={row['Details']}")
                print(f"      Start: {row['StartTime']} End: {row['EndTime']}")

# Example usage:
if __name__ == "__main__":
    xml_path = Path(r"C:/dev/agri_analysis/data/taskdata/TASKDATA.XML")
    taskdata_report(xml_path)
