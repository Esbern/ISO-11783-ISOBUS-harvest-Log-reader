from setuptools import setup, find_packages
import os

try:
    from Cython.Build import cythonize
except Exception:
    cythonize = None

ext_modules = []
# Prefer cython path under the canonical lowercase package name
cython_path = os.path.join('pyagri', 'cython_agri.pyx')
if cythonize is not None and os.path.exists(cython_path):
    try:
        ext_modules = cythonize(cython_path)
    except Exception:
        ext_modules = []
else:
    # fall back to legacy path for compatibility with older source trees
    legacy_cython_path = os.path.join('pyAgriculture', 'cython_agri.pyx')
    if cythonize is not None and os.path.exists(legacy_cython_path):
        try:
            ext_modules = cythonize(legacy_cython_path)
        except Exception:
            ext_modules = []

setup(
    name="pyagri",
    version="0.2.0",
    packages=find_packages(),
    package_data={'schemas': ['schemas']},
    install_requires=["numpy", "pandas"],
    entry_points={
        'console_scripts': [
            'pyagri-extract=pyagri.geo:main',
            'pyagri-convert=pyagri.export:main'
        ]
    },
    ext_modules=ext_modules,
)