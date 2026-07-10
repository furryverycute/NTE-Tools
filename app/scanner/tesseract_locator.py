from __future__ import annotations

import os
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class TesseractLocation:
    exe: str
    tessdata_dir: str = ''


def _existing_root_candidates() -> list[Path]:
    """Return app/project roots to search for a portable Tesseract bundle."""
    roots: list[Path] = []

    try:
        # Source layout: app/scanner/tesseract_locator.py -> project root
        roots.append(Path(__file__).resolve().parents[2])
    except Exception:
        pass

    try:
        # PyInstaller one-folder: executable lives in dist/NTE Tool/
        roots.append(Path(sys.executable).resolve().parent)
    except Exception:
        pass

    try:
        # PyInstaller one-file: data is unpacked into sys._MEIPASS
        meipass = getattr(sys, '_MEIPASS', '')
        if meipass:
            roots.append(Path(meipass).resolve())
    except Exception:
        pass

    try:
        roots.append(Path.cwd().resolve())
    except Exception:
        pass

    result: list[Path] = []
    seen: set[str] = set()
    for root in roots:
        key = str(root).lower()
        if key not in seen:
            seen.add(key)
            result.append(root)
    return result


def _portable_candidate_paths() -> list[Path]:
    paths: list[Path] = []
    rels = [
        Path('tools') / 'tesseract' / 'tesseract.exe',
        Path('tesseract') / 'tesseract.exe',
        Path('runtime') / 'tesseract' / 'tesseract.exe',
        Path('vendor') / 'tesseract' / 'tesseract.exe',
        Path('_internal') / 'tools' / 'tesseract' / 'tesseract.exe',
    ]
    for root in _existing_root_candidates():
        for rel in rels:
            paths.append(root / rel)
    return paths


def _candidate_paths() -> list[Path]:
    paths: list[Path] = []

    configured = os.environ.get('NTE_TESSERACT_EXE', '').strip().strip('"')
    if configured:
        paths.append(Path(configured))

    # App-local portable bundle first. This avoids PATH/registry dependency.
    paths.extend(_portable_candidate_paths())

    found = shutil.which('tesseract')
    if found:
        paths.append(Path(found))

    env_roots = [
        os.environ.get('ProgramFiles', r'C:\Program Files'),
        os.environ.get('ProgramFiles(x86)', r'C:\Program Files (x86)'),
        os.environ.get('LOCALAPPDATA', ''),
        os.environ.get('APPDATA', ''),
        os.environ.get('PROGRAMDATA', ''),
        os.environ.get('ChocolateyInstall', ''),
        os.environ.get('SCOOP', ''),
    ]

    explicit = [
        r'C:\Program Files\Tesseract-OCR\tesseract.exe',
        r'C:\Program Files (x86)\Tesseract-OCR\tesseract.exe',
        r'C:\Users\%USERNAME%\AppData\Local\Programs\Tesseract-OCR\tesseract.exe',
        r'C:\ProgramData\chocolatey\bin\tesseract.exe',
        r'C:\ProgramData\scoop\apps\tesseract\current\tesseract.exe',
    ]
    username = os.environ.get('USERNAME', '')
    for p in explicit:
        if '%USERNAME%' in p and username:
            p = p.replace('%USERNAME%', username)
        paths.append(Path(p))

    for root in env_roots:
        if not root:
            continue
        root_path = Path(root)
        paths.extend([
            root_path / 'Tesseract-OCR' / 'tesseract.exe',
            root_path / 'Programs' / 'Tesseract-OCR' / 'tesseract.exe',
            root_path / 'scoop' / 'apps' / 'tesseract' / 'current' / 'tesseract.exe',
            root_path / 'chocolatey' / 'bin' / 'tesseract.exe',
        ])

    # UB Mannheim installer sometimes installs below a versioned directory.
    for base in [Path(os.environ.get('ProgramFiles', r'C:\Program Files')), Path(os.environ.get('ProgramFiles(x86)', r'C:\Program Files (x86)')), Path(os.environ.get('LOCALAPPDATA', ''))]:
        if not base.exists():
            continue
        for pattern in ('Tesseract*\\tesseract.exe', '*Tesseract*\\tesseract.exe'):
            try:
                paths.extend(base.glob(pattern))
            except Exception:
                pass

    # Windows registry lookup.  Kept optional so the module still imports on non-Windows.
    if os.name == 'nt':
        try:
            import winreg  # type: ignore
            roots = [winreg.HKEY_LOCAL_MACHINE, winreg.HKEY_CURRENT_USER]
            subkeys = [
                r'SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall',
                r'SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall',
            ]
            for root in roots:
                for subkey in subkeys:
                    try:
                        with winreg.OpenKey(root, subkey) as key:
                            count = winreg.QueryInfoKey(key)[0]
                            for i in range(count):
                                try:
                                    name = winreg.EnumKey(key, i)
                                    with winreg.OpenKey(key, name) as appkey:
                                        display = ''
                                        install = ''
                                        try:
                                            display = str(winreg.QueryValueEx(appkey, 'DisplayName')[0])
                                        except Exception:
                                            pass
                                        try:
                                            install = str(winreg.QueryValueEx(appkey, 'InstallLocation')[0])
                                        except Exception:
                                            pass
                                        if 'tesseract' in display.lower() and install:
                                            paths.append(Path(install) / 'tesseract.exe')
                                except Exception:
                                    continue
                    except Exception:
                        continue
        except Exception:
            pass

    # Deduplicate while preserving order.
    result: list[Path] = []
    seen: set[str] = set()
    for path in paths:
        try:
            key = str(path.expanduser())
        except Exception:
            key = str(path)
        low = key.lower()
        if low not in seen:
            seen.add(low)
            result.append(Path(key))
    return result


def _find_tessdata_dir(exe_path: Path) -> str:
    candidates = []
    exe_dir = exe_path.parent
    env = os.environ.get('TESSDATA_PREFIX', '').strip().strip('"')
    if env:
        candidates.extend([Path(env), Path(env) / 'tessdata'])

    candidates.extend([
        exe_dir / 'tessdata',
        exe_dir.parent / 'tessdata',
        exe_dir.parent / 'share' / 'tessdata',
    ])

    for root in _existing_root_candidates():
        candidates.extend([
            root / 'tools' / 'tesseract' / 'tessdata',
            root / 'tesseract' / 'tessdata',
            root / 'runtime' / 'tesseract' / 'tessdata',
            root / 'vendor' / 'tesseract' / 'tessdata',
            root / '_internal' / 'tools' / 'tesseract' / 'tessdata',
        ])

    candidates.extend([
        Path(os.environ.get('ProgramFiles', r'C:\Program Files')) / 'Tesseract-OCR' / 'tessdata',
        Path(os.environ.get('ProgramFiles(x86)', r'C:\Program Files (x86)')) / 'Tesseract-OCR' / 'tessdata',
    ])

    # Prefer Korean/English complete tessdata.
    for td in candidates:
        try:
            if td.exists() and ((td / 'kor.traineddata').exists() or (td / 'Hangul.traineddata').exists()) and (td / 'eng.traineddata').exists():
                return str(td)
        except Exception:
            continue
    for td in candidates:
        try:
            if td.exists() and any(td.glob('*.traineddata')):
                return str(td)
        except Exception:
            continue
    return ''


def has_required_tessdata(tessdata_dir: str) -> bool:
    if not tessdata_dir:
        return False
    td = Path(tessdata_dir)
    try:
        return (td / 'eng.traineddata').exists() and ((td / 'kor.traineddata').exists() or (td / 'Hangul.traineddata').exists())
    except Exception:
        return False


def locate_tesseract(*, verify: bool = True, require_languages: bool = False) -> TesseractLocation:
    errors: list[str] = []
    for path in _candidate_paths():
        try:
            if not path.exists() or not path.is_file():
                continue
            exe = str(path)
            if verify:
                proc = subprocess.run([exe, '--version'], capture_output=True, text=True, timeout=8)
                if proc.returncode != 0:
                    errors.append(f'{exe}: exit {proc.returncode}')
                    continue
            tessdata = _find_tessdata_dir(path)
            if require_languages and not has_required_tessdata(tessdata):
                errors.append(f'{exe}: missing kor/eng traineddata')
                continue
            return TesseractLocation(exe=exe, tessdata_dir=tessdata)
        except Exception as exc:
            errors.append(f'{path}: {exc.__class__.__name__}')
            continue
    suffix = ''
    if errors:
        suffix = ' / ' + '; '.join(errors[:3])
    raise RuntimeError('Tesseract OCR v5 실행 파일 또는 kor/eng 언어 데이터를 찾을 수 없습니다. setup.bat를 실행하거나 tools\\tesseract\\ 폴더에 tesseract.exe와 tessdata를 넣으세요.' + suffix)
