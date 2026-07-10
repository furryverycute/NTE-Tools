from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path


APP_DIR_NAME = 'NTE Tool Demo'
EXE_NAME = 'NTE Tool Demo.exe'


def bundle_root() -> Path:
    return Path(getattr(sys, '_MEIPASS', Path(__file__).resolve().parent))


def find_portable_zip() -> Path:
    if len(sys.argv) > 1:
        candidate = Path(sys.argv[1])
        if candidate.exists():
            return candidate
    candidates = sorted(bundle_root().glob('*portable*.zip'))
    if candidates:
        return candidates[0]
    raise FileNotFoundError('Portable zip asset was not found.')


def safe_extract_zip(archive_path: Path, target_dir: Path):
    target_root = target_dir.resolve()
    with zipfile.ZipFile(archive_path) as archive:
        for member in archive.infolist():
            resolved = (target_dir / member.filename).resolve()
            if target_root not in resolved.parents and resolved != target_root:
                raise RuntimeError('Unsafe archive path.')
        archive.extractall(target_dir)


def find_app_source(extract_dir: Path) -> Path:
    matches = list(extract_dir.rglob(EXE_NAME))
    if not matches:
        raise FileNotFoundError(f'{EXE_NAME} was not found in portable package.')
    return matches[0].parent


def install_dir() -> Path:
    return Path(os.environ.get('LOCALAPPDATA') or Path.home()) / 'NTE Tool' / APP_DIR_NAME


def create_shortcut(target_exe: Path):
    desktop = Path(os.environ.get('USERPROFILE', str(Path.home()))) / 'Desktop'
    shortcut = desktop / 'NTE Tool.lnk'
    command = (
        "$s=(New-Object -ComObject WScript.Shell).CreateShortcut($env:SHORTCUT_PATH);"
        "$s.TargetPath=$env:TARGET_PATH;"
        "$s.WorkingDirectory=$env:WORKING_DIR;"
        "$s.Save()"
    )
    env = os.environ.copy()
    env['SHORTCUT_PATH'] = str(shortcut)
    env['TARGET_PATH'] = str(target_exe)
    env['WORKING_DIR'] = str(target_exe.parent)
    subprocess.run(['powershell.exe', '-NoProfile', '-ExecutionPolicy', 'Bypass', '-Command', command], env=env, check=False)


def main() -> int:
    archive = find_portable_zip()
    with tempfile.TemporaryDirectory(prefix='nte-tool-install-') as temp_name:
        extract_dir = Path(temp_name) / 'portable'
        extract_dir.mkdir(parents=True, exist_ok=True)
        safe_extract_zip(archive, extract_dir)
        source_dir = find_app_source(extract_dir)
        target_dir = install_dir()
        if target_dir.exists():
            shutil.rmtree(target_dir)
        shutil.copytree(source_dir, target_dir)

    target_exe = target_dir / EXE_NAME
    create_shortcut(target_exe)
    subprocess.Popen([str(target_exe)], cwd=str(target_dir))
    print(f'NTE Tool installed: {target_dir}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
