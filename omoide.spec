# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec for the one-file Omoide executable."""

from PyInstaller.utils.hooks import collect_all

packages = (
    "rapidocr_onnxruntime",
    "pywebview",
    "pystray",
    "mcp",
    "PIL",
    "cv2",
    "onnxruntime",
)

datas = [("omoide/ui/*", "omoide/ui")]
binaries = []
hiddenimports = [
    "win32api",
    "win32clipboard",
    "win32con",
    "win32gui",
    "win32process",
    "keyboard",
    "PIL.ImageGrab",
    "pythonnet",
    "clr_loader",
]

for package in packages:
    package_datas, package_binaries, package_hidden = collect_all(package)
    datas.extend(package_datas)
    binaries.extend(package_binaries)
    hiddenimports.extend(package_hidden)

a = Analysis(
    ["omoide/entry.py"],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="Omoide",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    icon="assets/icon.ico",
)
