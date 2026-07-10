# -*- mode: python ; coding: utf-8 -*-

from pathlib import Path
from PyInstaller.utils.hooks import collect_submodules

block_cipher = None
hiddenimports = [
    'PySide6.QtCore',
    'PySide6.QtGui',
    'PySide6.QtWidgets',
]
for optional_pkg in ['mss', 'vgamepad', 'cv2']:
    try:
        hiddenimports += collect_submodules(optional_pkg)
    except Exception:
        pass

asset_datas = []
for file_path in Path('app/assets').rglob('*'):
    if file_path.is_file():
        asset_datas.append((str(file_path), str(file_path.parent)))

# Include app-local portable Tesseract when the folder exists.
# Expected layout: tools/tesseract/tesseract.exe + tools/tesseract/tessdata/*.traineddata
for portable_root in [Path('tools/tesseract')]:
    if portable_root.exists():
        for file_path in portable_root.rglob('*'):
            if file_path.is_file():
                asset_datas.append((str(file_path), str(file_path.parent)))

a = Analysis(
    ['app/main.py'],
    pathex=[],
    binaries=[],
    datas=asset_datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)
exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='NTE Tool',
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
    icon='app/assets/icon.ico',
)
coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='NTE Tool',
)
