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
    if mode == 'installer':
        return installers[0] if installers else None
    if mode == 'portable':
        return portables[0] if portables else None
    portable_zips = [asset for asset in portables if Path(asset.get('name', '')).suffix.lower() == '.zip']
    portable_exes = [asset for asset in portables if Path(asset.get('name', '')).suffix.lower() == '.exe']
    return (portable_zips or portable_exes or installers or [None])[0]


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


def has_app_layout(root: Path) -> bool:
    return (root / f'{APP_NAME}.exe').exists() and (root / '_internal').is_dir()


def can_write_to(path: Path) -> bool:
    try:
        path.mkdir(parents=True, exist_ok=True)
        probe = path / '.nte_update_write_probe'
        probe.write_text('ok', encoding='utf-8')
        probe.unlink(missing_ok=True)
        return True
    except Exception:
        return False


def quote_ps(value: Path | str) -> str:
    return "'" + str(value).replace("'", "''") + "'"


def launch_update_helper(source_dir: Path, target_dir: Path, launch_exe: Path) -> bool:
    source_dir = source_dir.resolve()
    target_dir = target_dir.resolve()
    launch_exe = launch_exe.resolve()
    if not has_app_layout(source_dir):
        raise RuntimeError(f'업데이트 원본 폴더 구조가 올바르지 않습니다: {source_dir}')
    if not has_app_layout(target_dir):
        raise RuntimeError(f'현재 앱 폴더 구조가 올바르지 않습니다: {target_dir}')
    if source_dir == target_dir:
        raise RuntimeError('업데이트 원본과 대상 폴더가 같습니다.')

    helper_dir = local_update_root() / 'helpers'
    helper_dir.mkdir(parents=True, exist_ok=True)
    script_path = helper_dir / f'apply_update_{os.getpid()}.ps1'
    log_path = helper_dir / f'apply_update_{os.getpid()}.log'
    script = f"""
$ErrorActionPreference = 'Stop'
$PidToWait = {os.getpid()}
$Source = {quote_ps(source_dir)}
$Target = {quote_ps(target_dir)}
$Exe = {quote_ps(launch_exe)}
$Log = {quote_ps(log_path)}
Start-Transcript -Path $Log -Force | Out-Null
try {{
  try {{ Wait-Process -Id $PidToWait -Timeout 90 -ErrorAction SilentlyContinue }} catch {{ }}
  Start-Sleep -Milliseconds 800
  if (!(Test-Path -LiteralPath (Join-Path $Source '{APP_NAME}.exe'))) {{ throw '업데이트 원본 실행 파일이 없습니다.' }}
  if (!(Test-Path -LiteralPath (Join-Path $Source '_internal'))) {{ throw '업데이트 원본 내부 파일이 없습니다.' }}
  if (!(Test-Path -LiteralPath (Join-Path $Target '{APP_NAME}.exe'))) {{ throw '현재 앱 실행 파일을 찾지 못했습니다.' }}
  & robocopy $Source $Target /E /IS /IT /R:2 /W:1 /NFL /NDL /NJH /NJS /NC /NS
  $code = $LASTEXITCODE
  if ($code -gt 7) {{ throw "파일 교체 실패: robocopy exit $code" }}
  Start-Process -FilePath $Exe -WorkingDirectory $Target
}} finally {{
  Stop-Transcript | Out-Null
}}
"""
    script_path.write_text(script, encoding='utf-8-sig')
    args = ['-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', str(script_path)]
    if can_write_to(target_dir):
        subprocess.Popen(['powershell.exe', *args], cwd=str(helper_dir))
        return False

    if os.name != 'nt':
        raise RuntimeError('현재 앱 폴더에 쓰기 권한이 없습니다.')
    import ctypes
    params = subprocess.list2cmdline(args)
    result = ctypes.windll.shell32.ShellExecuteW(None, 'runas', 'powershell.exe', params, str(helper_dir), 1)
    if result <= 32:
        raise RuntimeError('관리자 권한 업데이트 helper를 실행하지 못했습니다.')
    return True


def install_update(release: dict[str, Any]) -> dict[str, Any]:
    asset = select_asset(release)
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
        return {'ok': False, 'message': '현재 폴더 업데이트는 zip asset만 지원합니다.'}

    staging = unique_dir(work_dir / f'extracted-{safe_name(tag)}')
    staging.mkdir(parents=True, exist_ok=True)
    safe_extract_zip(downloaded, staging)
    launch = find_launch_candidate(staging)
    if not launch:
        return {'ok': False, 'message': f'업데이트 파일을 풀었지만 실행 파일을 찾지 못했습니다: {staging}'}

    source_dir = launch.parent
    target_dir = app_root()
    target_launch = target_dir / f'{APP_NAME}.exe'
    elevated = launch_update_helper(source_dir, target_dir, target_launch)
    return {
        'ok': True,
        'message': '업데이트를 현재 앱 폴더에 적용합니다. 앱을 종료합니다.' + (' 관리자 권한 확인 창을 승인해주세요.' if elevated else ''),
        'installed_dir': str(target_dir),
        'quit_current': True,
    }
