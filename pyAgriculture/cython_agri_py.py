"""Pure-Python fallback implementation for cython_agri functions.

This module is intentionally named differently from the compiled
`cython_agri` extension so Python will not load the .so by mistake when a
compatible symbol set is not available. `agriculture.py` will try to import
from the compiled extension first and fall back to this module when needed.
"""
from __future__ import annotations
import numpy as np
from datetime import timedelta


def read_static_binary_data(data_row, read_point: int, binary_data: bytes, tlg_dict: dict, dt, start_date):
    nr_d = 3
    np_data = np.frombuffer(binary_data, dt, count=1, offset=read_point)
    millis_from_midnight = int(np_data[0][0])
    days = int(np_data[0][1])
    actual_time = start_date + timedelta(days=days, milliseconds=millis_from_midnight)
    data_row[0] = actual_time.strftime('%Y-%m-%dT%H:%M:%S')
    data_row[1] = np_data[0][2] * pow(10, -7)
    data_row[2] = np_data[0][3] * pow(10, -7)
    for key in tlg_dict['PTN'][''].keys():
        if key in ['C', 'D', 'E', 'F', 'G']:
            data_row[nr_d] = np_data[0][nr_d + 1]
            nr_d += 1
    if 'H' in tlg_dict['PTN'][''].keys() and 'I' in tlg_dict['PTN'][''].keys():
        millis_from_midnight = int(np_data[0][nr_d + 1])
        days = int(np_data[0][nr_d + 2])
        actual_time = start_date + timedelta(days=days, milliseconds=millis_from_midnight)
        data_row[nr_d] = actual_time.strftime('%Y-%m-%dT%H:%M:%S')
        nr_d += 2
    nr_dlvs = np_data[0][nr_d + 1]
    return [data_row, nr_dlvs, nr_d]


def cython_read_dlvs(binary_data: bytes, read_point: int, nr_dlvs: int, nr_static: int,
                     dpd_ids: dict, task_dicts: dict, unit_row: list, data_row: list,
                     dlvs: list, dlv_idx: dict):
    for nr, dlv in np.frombuffer(binary_data, [('DLVn', np.dtype('uint8')), ('PDV', np.dtype('int32'))],
                                 count=nr_dlvs, offset=read_point):
        read_point += 5
        dpd_key = dlvs[nr]['A']
        idx = dlv_idx[dpd_key]
        if dpd_key in dpd_ids.keys():
            dpd = dpd_ids[dpd_key]
            dvp_key = dpd.get('F')
        else:
            continue
        # If DVP scaling/unit is missing, keep raw DLV value instead of skipping.
        if dvp_key is None or dvp_key not in task_dicts['DVP'].keys():
            dlv_val = int(dlv)
        else:
            dvp = task_dicts['DVP'][dvp_key]
            decimals = float(10**int(dvp['D']))
            dlv_val = int((dlv + float(dvp['B'])) * float(dvp['C']) * decimals + 0.5) / decimals
            if unit_row[idx] is None:
                if 'E' in dvp.keys():
                    unit_row[idx] = dvp['E']
        try:
            data_row[idx + nr_static - 1] = dlv_val
        except Exception as e:
            # Keep processing but surface a warning if an assignment fails
            import warnings
            warnings.warn(f"Failed to assign DLV value at idx {idx}: {e}")
    return [read_point, data_row, unit_row]
