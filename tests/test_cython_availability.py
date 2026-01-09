import importlib
import sys
import types

import pytest


def reload_agriculture_module():
    # Ensure a clean import state
    if 'pyagri.agriculture' in sys.modules:
        importlib.reload(sys.modules['pyagri.agriculture'])
    else:
        importlib.import_module('pyagri.agriculture')
    return sys.modules['pyagri.agriculture']


def test_read_with_cython_true_when_extension_present(monkeypatch):
    # Insert a fake compiled module
    fake_mod = types.ModuleType('pyagri.cython_agri')
    fake_mod.read_static_binary_data = lambda *a, **k: None
    fake_mod.cython_read_dlvs = lambda *a, **k: None
    monkeypatch.setitem(sys.modules, 'pyagri.cython_agri', fake_mod)

    ag = reload_agriculture_module()
    assert getattr(ag, '_CYTHON_AVAILABLE', False) is True

    Pa = ag.PyAgriculture
    p = Pa('/tmp')
    assert p.read_with_cython is True


def test_read_with_cython_false_when_extension_missing(monkeypatch):
    # Ensure the cython module is not importable
    monkeypatch.setitem(sys.modules, 'pyagri.cython_agri', None)

    ag = reload_agriculture_module()
    assert getattr(ag, '_CYTHON_AVAILABLE', False) is False

    Pa = ag.PyAgriculture
    p = Pa('/tmp')
    assert p.read_with_cython is False
