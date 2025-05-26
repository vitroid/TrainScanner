from cx_Freeze import setup, Executable

import tomllib

# load from ../pyproject.toml
with open('../pyproject.toml', 'rb') as f:
    pyproject = tomllib.load(f)

name = 'TrainScanner'
version = pyproject['tool']['poetry']['version']
description = pyproject['tool']['poetry']['description']
author = pyproject['tool']['poetry']['authors'][0]

executables = [
    Executable('../trainscanner_exe.py',
    ),
]

setup(
    name=name,
    version=version,
    description=description,
    executables=executables,
    options={
        "bdist_mac": {
            "bundle_name": name,
            "iconfile": './TrainScanner.icns',
            "include_resources": [('../trainscanner', 'lib/trainscanner')], 
        },
        "bdist_dmg": {
            "applications_shortcut": True,
            "volume_label": name,
            "background": "builtin-arrow",
        },
    },
)
