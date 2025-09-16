# setup.py
from setuptools import setup, find_packages

setup(
    name="powershell_sentinel",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
    ],
    entry_points={
        'console_scripts': [
            'sentinel-toolkit=powershell_sentinel.sentinel_toolkit:app',
            'sentinel-manager=powershell_sentinel.primitives_manager:main',
        ],
    },
)