from cx_Freeze import setup, Executable
import tomllib

# load from ../pyproject.toml
with open('../pyproject.toml', 'rb') as f:
    pyproject = tomllib.load(f)

name = 'TrainScanner'
version = pyproject['tool']['poetry']['version']
description = pyproject['tool']['poetry']['description']
author = pyproject['tool']['poetry']['authors'][0]
copyright = '(C) 2025 ' + author

build_exe_options = dict(
    packages = ['trainscanner'],
    include_msvcr=True, 
)

bdist_msi_options = dict(
    upgrade_code='{57b549d4-4041-4503-a1b3-d3f521a99540}',  # UUID for TrainScanner
    all_users=False,
    add_to_path=False,
    initial_target_dir=r'[ProgramFiles64Folder]\%s' % name,
    data=dict(
        Directory=[
            ("ProgramMenuFolder", "TARGETDIR", "."),
            ('MyProgramMenu', 'ProgramMenuFolder', name), 
        ],
    ),
)

options = dict(
    build_exe = build_exe_options,
    bdist_msi = bdist_msi_options,
)

executables = [
    Executable(r'..\trainscanner_exe.py',
               base='gui',
               copyright=copyright,
               icon=r'.\trainscanner.drawio.ico',
               shortcut_name=name,
               shortcut_dir='MyProgramMenu'
    ),
    Executable(r'..\ts_converter_exe.py',
               base='console',
               copyright=copyright,
               icon=r'.\ts_converter.drawio.ico',
               shortcut_name='ts_converter',
               shortcut_dir='MyProgramMenu'
    ),
]

setup(name=name,
      version = version,
      description = description,
      author = author,
      options = options,
      executables = executables
)
