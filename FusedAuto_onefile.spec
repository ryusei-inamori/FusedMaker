# -*- mode: python ; coding: utf-8 -*-
# Single-file build: dist\FusedAuto.exe (one file, can be copied anywhere).
# Build:  build_onefile.bat
# Note: starts a few seconds slower than the folder build (it unpacks itself to %TEMP% on launch).

import glob
manuals = [(p, 'docs') for p in glob.glob('docs/FusedAuto_manual_*.pdf')]

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('main.ico', '.'),
        ('README.md', '.'),
        ('THIRD_PARTY_LICENSES.txt', '.'),
        ('LICENSE', 'licenses'),
        ('THIRD_PARTY_LICENSES.txt', 'licenses'),
        ('licenses/*.txt', 'licenses'),
    ] + manuals,
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['PyQt6', 'PyQt5', 'PySide2', 'tkinter', 'matplotlib', 'scipy', 'pandas', 'IPython'],
    noarchive=False,
    optimize=1,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='FusedAuto',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=['main.ico'],
    version='version_info.txt',
)
