# -*- mode: python ; coding: utf-8 -*-
# Build:  pyinstaller --noconfirm FusedAuto.spec   (or run build.bat)
#
# One-folder build (dist\FusedAuto\). This is deliberate: PySide6/Qt are LGPL v3, and a
# one-folder build keeps the Qt DLLs as separate, user-replaceable files.

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
    # never bundle both Qt bindings; drop large unused packages
    excludes=['PyQt6', 'PyQt5', 'PySide2', 'tkinter', 'matplotlib', 'scipy', 'pandas', 'IPython'],
    noarchive=False,
    optimize=1,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='FusedAuto',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=['main.ico'],
    version='version_info.txt',
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name='FusedAuto',
)
