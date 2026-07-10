from __future__ import annotations

import os
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.version import APP_VERSION


APP_FOLDER_NAME = 'NTE Tool Demo'
PORTABLE_DIST = ROOT / 'dist' / APP_FOLDER_NAME
RELEASE_DIR = ROOT / 'release'
PORTABLE_ZIP = RELEASE_DIR / f'NTE-Tool-{APP_VERSION}-portable.zip'
INSTALLER_NAME = f'NTE-Tool-{APP_VERSION}-installer'
INSTALLER_EXE = RELEASE_DIR / f'{INSTALLER_NAME}.exe'


def run(cmd: list[str]):
    subprocess.check_call(cmd, cwd=str(ROOT))


def remove_path(path: Path):
    if path.is_dir():
        shutil.rmtree(path)
    elif path.exists():
        path.unlink()


def zip_portable_folder():
    remove_path(PORTABLE_ZIP)
    with zipfile.ZipFile(PORTABLE_ZIP, 'w', compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for file_path in PORTABLE_DIST.rglob('*'):
            if file_path.is_file():
                archive.write(file_path, file_path.relative_to(PORTABLE_DIST.parent))


def build_portable():
    run([sys.executable, '-m', 'PyInstaller', '--noconfirm', '--clean', 'nte_tool_demo.spec'])
    if not (PORTABLE_DIST / 'NTE Tool Demo.exe').exists():
        raise FileNotFoundError(f'Portable build output was not found: {PORTABLE_DIST}')
    zip_portable_folder()


def build_installer():
    remove_path(INSTALLER_EXE)
    add_data = f'{PORTABLE_ZIP}{os.pathsep}.'
    run([
        sys.executable,
        '-m',
        'PyInstaller',
        '--noconfirm',
        '--clean',
        '--onefile',
        '--console',
        '--name',
        INSTALLER_NAME,
        '--distpath',
        str(RELEASE_DIR),
        '--workpath',
        str(ROOT / 'build' / 'installer'),
        '--specpath',
        str(ROOT / 'build' / 'installer'),
        '--add-data',
        add_data,
        str(ROOT / 'tools' / 'nte_installer.py'),
    ])
    if not INSTALLER_EXE.exists():
        raise FileNotFoundError(f'Installer build output was not found: {INSTALLER_EXE}')


def main() -> int:
    RELEASE_DIR.mkdir(parents=True, exist_ok=True)
    build_portable()
    build_installer()
    print('Release assets ready:')
    print(f'  {PORTABLE_ZIP}')
    print(f'  {INSTALLER_EXE}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
