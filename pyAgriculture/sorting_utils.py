"""Small XML / lookup helpers used across the package.

This module contains helpers for converting ElementTree structures to
plain dictionaries and simple lookup utilities used by higher-level
parsers.
"""

from collections import defaultdict


def etree_to_dict(t):
    """Convert an ElementTree element into a nested dict structure.

    The representation is intentionally lightweight and intended for GUI
    building or simple inspection of schema-like XML trees.
    """
    d = {t.tag: {} if t.attrib else None}
    children = list(t)
    if children:
        dd = defaultdict(list)
        for dc in map(etree_to_dict, children):
            for k, v in dc.items():
                dd[k].append(v)
        d = {t.tag: {k: v[0] if len(v) == 1 else v
                     for k, v in dd.items()}}
    if t.attrib:
        d[t.tag]['attr'] = (list(t.attrib.keys()))
    if t.text:
        text = t.text.strip()
        if children or t.attrib:
            if text:
                d[t.tag]['#text'] = text
        else:
            d[t.tag] = text
    return d


def find_by_key(data_dict: dict, key_name: str, key_value: str):
    """Return (found, key) where data_dict[key][key_name] == key_value.

    Returns `(True, key)` if found, otherwise `(False, key_value)` to match
    historical behavior used by callers.
    """
    for key in data_dict.keys():
        if data_dict[key][key_name] == key_value:
            return True, key
    return False, key_value
