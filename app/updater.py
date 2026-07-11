from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import urllib.error
import urllib.request
import zipfile
from pathlib import Path
from typing import Any

from app.version import APP_NAME, APP_VERSION, GITHUB_LATEST_RELEASE_API


USER_AGENT = 'NTE-Tool-Updater/1.0'
LEGACY_SUFFIX = bytes([68, 101, 109, 111]).decode('ascii')
LEGACY_APP_NAME = f'NTE Tool {LEGACY_SUFFIX}'
LEGACY_RUN_SCRIPT = f'run_{LEGACY_SUFFIX.lower()}.bat'


def app_root() -> Path:
    if getattr(sys, 'frozen', False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parents[1]


def installed_app_roots() -> list[Path]:
    base = Path(os.environ.get('LOCALAPPDATA') or Path.home()) / 'NTE Tool'
    # Keep the old v41 installer path so existing installed copies are still detected as installer mode.
    return [base / APP_NAME, base / LEGACY_APP_NAME]


def install_kind() -> str:
    if not getattr(sys, 'frozen', False):
        return 'portable'
    try:
        root = app_root().resolve()
        for installed_root in installed_app_roots():
            installed = installed_root.resolve()
            if root == installed or installed in root.parents:
                return 'installer'
    except Exception:
        pass
    return 'portable'


def install_kind_label() -> str:
    return '설치형 exe' if install_kind() == 'installer' else '포터블'


LEGACY_VERSION_MAP = {
    'v41': '1.4.1',
    '41': '1.4.1',
}


def normalize_version(value: str) -> str:
    cleaned = (value or '').strip()
    return LEGACY_VERSION_MAP.get(cleaned, LEGACY_VERSION_MAP.get(cleaned.lstrip('vV'), cleaned.lstrip('vV')))


def version_key(value: str) -> tuple[int, ...]:
    numbers = re.findall(r'\d+', normalize_version(value))
    return tuple(int(number) for number in numbers) if numbers else (0,)


def is_newer_version(latest: str, current: str = APP_VERSION) -> bool:
    latest_key = version_key(latest)
    current_key = version_key(current)
    width = max(len(latest_key), len(current_key), 3)
    return latest_key + (0,) * (width - len(latest_key)) > current_key + (0,) * (width - len(current_key))


def request_json(url: str) -> dict[str, Any]:
    request = urllib.request.Request(url, headers={'User-Agent': USER_AGENT, 'Accept': 'application/vnd.github+json'})
    with urllib.request.urlopen(request, timeout=15) as response:
        return json.loads(response.read().decode('utf-8'))


def fetch_latest_release() -> dict[str, Any]:
    try:
        release = request_json(GITHUB_LATEST_RELEASE_API)
    except urllib.error.HTTPError as exc:
        if exc.code == 404:
            return {'ok': True, 'has_release': False, 'message': '아직 게시된 릴리스가 없습니다.'}
        return {'ok': False, 'message': f'GitHub 응답 오류: HTTP {exc.code}'}
    except Exception as exc:
        return {'ok': False, 'message': f'업데이트 확인 실패: {exc}'}

    assets = []
    for asset in release.get('assets') or []:
        asset_type = classify_asset(asset.get('name', ''))
        if asset_type:
            assets.append({
                'name': asset.get('name', ''),
                'type': asset_type,
                'size': asset.get('size') or 0,
                'url': asset.get('browser_download_url', ''),
            })

    tag = release.get('tag_name') or ''
    return {
        'ok': True,
        'has_release': True,
        'update_available': is_newer_version(tag),
        'tag_name': tag,
        'name': release.get('name') or tag,
        'html_url': release.get('html_url') or '',
        'body': release.get('body') or '',
        'assets': assets,
    }


def classify_asset(name: str) -> str:
    lower = (name or '').lower()
    suffix = Path(lower).suffix
    if suffix in ('.exe', '.msi') and any(key in lower for key in ('setup', 'installer', 'install')):
        return 'installer'
    if 'portable' in lower and suffix in ('.zip', '.exe'):
        return 'portable'
    return ''


def select_asset(release: dict[str, Any], mode: str | None = None) -> dict[str, Any] | None:
    assets = release.get('assets') or []
    installers = [asset for asset in assets if asset.get('type') == 'installer']
    portables = [asset for asset in assets if asset.get('type') == 'portable']
    mode = mode or install_kind()
    if mode == 'installer':
        return installers[0] if installers else None
    if mode == 'portable':
        return portables[0] if portables else None
    return (portables or installers or [None])[0]


def download_asset(asset: dict[str, Any], download_dir: Path) -> Path:
    url = asset.get('url')
    if not url:
        raise RuntimeError('다운로드 URL이 없습니다.')
    download_dir.mkdir(parents=True, exist_ok=True)
    target = download_dir / asset.get('name', 'nte-tool-update.bin')
    request = urllib.request.Request(url, headers={'User-Agent': USER_AGENT})
    with urllib.request.urlopen(request, timeout=60) as response:
        with open(target, 'wb') as file:
            shutil.copyfileobj(response, file)
    return target


def local_update_root() -> Path:
    base = Path(os.environ.get('LOCALAPPDATA') or Path.home()) / 'NTE Tool' / 'updates'
    base.mkdir(parents=True, exist_ok=True)
    return base


def portable_install_base() -> Path:
    root = app_root()
    parent = root.parent
    try:
        probe = parent / '.nte_write_probe'
        probe.write_text('ok', encoding='utf-8')
        probe.unlink(missing_ok=True)
        return parent
    except Exception:
        base = Path(os.environ.get('LOCALAPPDATA') or Path.home()) / 'NTE Tool'
        base.mkdir(parents=True, exist_ok=True)
        return base


def safe_name(value: str) -> str:
    return re.sub(r'[^A-Za-z0-9._-]+', '-', value or 'update').strip('-') or 'update'


def unique_dir(base: Path) -> Path:
    if not base.exists():
        return base
    for index in range(1, 100):
        candidate = base.with_name(f'{base.name}-{index}')
        if not candidate.exists():
            return candidate
    return base.with_name(f'{base.name}-{os.getpid()}')


def safe_extract_zip(archive_path: Path, target_dir: Path):
    target_root = target_dir.resolve()
    with zipfile.ZipFile(archive_path) as archive:
        for member in archive.infolist():
            resolved = (target_dir / member.filename).resolve()
            if target_root not in resolved.parents and resolved != target_root:
                raise RuntimeError('포터블 압축 파일 경로가 안전하지 않습니다.')
        archive.extractall(target_dir)


def find_launch_candidate(root: Path) -> Path | None:
    preferred_names = ('NTE Tool.exe', f'{LEGACY_APP_NAME}.exe', 'run_app.bat', LEGACY_RUN_SCRIPT)
    for name in preferred_names:
        found = list(root.rglob(name))
        if found:
            return found[0]
    exe_candidates = sorted(root.rglob('*.exe'), key=lambda path: ('nte' not in path.name.lower(), len(path.parts)))
    if exe_candidates:
        return exe_candidates[0]
    bat_candidates = sorted(root.rglob('*.bat'), key=lambda path: ('run' not in path.name.lower(), len(path.parts)))
    return bat_candidates[0] if bat_candidates else None


def launch_path(path: Path):
    if path.suffix.lower() == '.msi':
        subprocess.Popen(['msiexec', '/i', str(path)], cwd=str(path.parent))
    elif path.suffix.lower() == '.bat':
        subprocess.Popen(['cmd', '/c', 'start', '', str(path)], cwd=str(path.parent))
    else:
        subprocess.Popen([str(path)], cwd=str(path.parent))


def install_update(release: dict[str, Any]) -> dict[str, Any]:
    mode = install_kind()
    asset = select_asset(release, mode)
    if not asset:
        return {'ok': False, 'message': '이 앱에 맞는 릴리스 파일이 없습니다.'}

    tag = release.get('tag_name') or 'latest'
    work_dir = local_update_root() / safe_name(tag)
    downloaded = download_asset(asset, work_dir)
    asset_type = asset.get('type')

    if asset_type == 'installer':
        launch_path(downloaded)
        return {'ok': True, 'message': '설치형 업데이트를 실행했습니다.', 'quit_current': True}

    if downloaded.suffix.lower() == '.exe':
        launch_path(downloaded)
        return {'ok': True, 'message': '포터블 실행 파일을 실행했습니다.', 'quit_current': True}

    if downloaded.suffix.lower() != '.zip':
        return {'ok': False, 'message': '포터블 업데이트는 zip 또는 exe asset만 지원합니다.'}

    target = unique_dir(portable_install_base() / f'NTE-Tool-{safe_name(tag)}-portable')
    target.mkdir(parents=True, exist_ok=True)
    safe_extract_zip(downloaded, target)
    launch = find_launch_candidate(target)
    if not launch:
        return {'ok': False, 'message': f'포터블 파일을 풀었지만 실행 파일을 찾지 못했습니다: {target}'}

    launch_path(launch)
    return {
        'ok': True,
        'message': f'포터블 업데이트를 새 폴더에 설치했습니다: {target}',
        'installed_dir': str(target),
        'quit_current': True,
    }
