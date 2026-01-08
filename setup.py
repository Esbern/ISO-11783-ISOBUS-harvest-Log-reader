from setuptools import setup, find_packages
import os

try:
    from Cython.Build import cythonize
except Exception:
    cythonize = None

ext_modules = []
cython_path = os.path.join('pyAgriculture', 'cython_agri.pyx')
if cythonize is not None and os.path.exists(cython_path):
    try:
        ext_modules = cythonize(cython_path)
    except Exception:
        ext_modules = []

setup(
    name="pyAgriculture11783",
    version="0.2.0",
    packages=find_packages(),
    package_data={'schemas': ['schemas']},
    install_requires=["numpy", "pandas"],
    entry_points={
        'console_scripts': [
            'pyagri-extract=pyAgriculture.geo:main',
            'pyagri-convert=pyAgriculture.export:main'
        ]
    },
    ext_modules=ext_modules,
)