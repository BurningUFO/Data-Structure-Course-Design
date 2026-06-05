# -*- mode: python ; coding: utf-8 -*-

from pathlib import Path


project_root = Path(SPECPATH).resolve().parents[1]

datas = [
    (str(project_root / "data"), "data"),
    (str(project_root / "src" / "ui" / "static"), "src/ui/static"),
]

hiddenimports = [
    "webview.platforms.edgechromium",
    "pythonnet",
    "clr",
    "clr_loader",
]

excludes = [
    "cefpython3",
    "gi",
    "gtk",
    "PyQt5",
    "PyQt6",
    "PySide2",
    "PySide6",
    "tkinter",
]

a = Analysis(
    [str(project_root / "src" / "ui" / "desktop_app.py")],
    pathex=[str(project_root)],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=excludes,
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="IntelligentCampusGuide",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="IntelligentCampusGuide",
)
