from __future__ import annotations

import argparse
import hashlib
import os
import shutil
import subprocess
import sys
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path

VIGEMBUS_VERSION = '1.22.0'
VIGEMBUS_INSTALLER_NAME = 'ViGEmBus_1.22.0_x64_x86_arm64.exe'
VIGEMBUS_INSTALLER_URL = (
    'https://github.com/nefarius/ViGEmBus/releases/download/'
    f'v{VIGEMBUS_VERSION}/{VIGEMBUS_INSTALLER_NAME}'
)
VIGEMBUS_INSTALLER_SHA256 = '89220a7865076b342892f98865f3499fb7c4cfd673159e89d352c360fd014c6a'


@dataclass
class RuntimeSetupResult:
    ok: bool = True
    messages: list[str] = field(default_factory=list)
    installer_started: bool = False

    def add_error(self, message: str):
        self.ok = False
        self.messages.append(message)

    def add_info(self, message: str):
        self.messages.append(message)

    @property
    def message(self) -> str:
        return '\n'.join(self.messages)


def runtime_dir() -> Path:
    base = Path(os.environ.get('LOCALAPPDATA') or os.environ.get('APPDATA') or Path.home())
    target = base / 'NTE Tool' / 'runtime'
    target.mkdir(parents=True, exist_ok=True)
    return target


def controller_installer_path() -> Path:
    return runtime_dir() / VIGEMBUS_INSTALLER_NAME


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open('rb') as fp:
        for chunk in iter(lambda: fp.read(1024 * 1024), b''):
            digest.update(chunk)
    return digest.hexdigest().lower()


def ensure_controller_installer(download: bool = True) -> Path | None:
    target = controller_installer_path()
    if target.exists() and target.stat().st_size > 0:
        if _sha256(target) == VIGEMBUS_INSTALLER_SHA256:
            return target
        try:
            target.unlink()
        except OSError:
            return None
    if not download:
        return None

    request = urllib.request.Request(VIGEMBUS_INSTALLER_URL, headers={'User-Agent': 'NTE-Tool'})
    tmp = target.with_suffix('.download')
    with urllib.request.urlopen(request, timeout=30) as response:
        tmp.write_bytes(response.read())
    if _sha256(tmp) != VIGEMBUS_INSTALLER_SHA256:
        try:
            tmp.unlink()
        except OSError:
            pass
        raise RuntimeError('ViGEmBus 설치 파일 해시 검증에 실패했습니다.')
    tmp.replace(target)
    return target


def launch_controller_installer(path: Path | None = None) -> bool:
    installer = Path(path or controller_installer_path())
    if not installer.exists():
        return False
    if os.name == 'nt':
        env = os.environ.copy()
        env['NTE_VIGEMBUS_INSTALLER'] = str(installer)
        subprocess.Popen(
            [
                'powershell.exe',
                '-NoProfile',
                '-ExecutionPolicy',
                'Bypass',
                '-Command',
                'Start-Process -FilePath $env:NTE_VIGEMBUS_INSTALLER -Verb RunAs',
            ],
            env=env,
        )
        return True
    subprocess.Popen([str(installer)])
    return True


def _can_create_virtual_gamepad() -> tuple[bool, str]:
    try:
        import vgamepad as vg  # type: ignore
    except Exception as exc:
        return False, f'vgamepad Python 패키지를 불러올 수 없습니다: {exc}'
    try:
        pad = vg.VX360Gamepad()
        pad.reset()
        pad.update()
        return True, ''
    except Exception as exc:
        return False, f'ViGEmBus 가상 패드를 만들 수 없습니다: {exc}'


def _launch_tesseract_installer() -> bool:
    winget = shutil.which('winget')
    if not winget:
        return False
    cmd = [
        winget,
        'install',
        '--id',
        'UB-Mannheim.TesseractOCR',
        '--accept-package-agreements',
        '--accept-source-agreements',
    ]
    creationflags = 0x00000010 if os.name == 'nt' else 0
    subprocess.Popen(cmd, creationflags=creationflags)
    return True


def prepare_scan_runtime(*, download: bool = True, launch_installers: bool = True) -> RuntimeSetupResult:
    result = RuntimeSetupResult()

    try:
        from app.scanner.tesseract_locator import locate_tesseract

        location = locate_tesseract(require_languages=True)
        result.add_info(f'OCR 확인 완료: {location.exe}')
    except Exception as exc:
        started = False
        if launch_installers:
            try:
                started = _launch_tesseract_installer()
            except Exception:
                started = False
        suffix = 'winget 설치 창을 열었습니다. 설치가 끝나면 다시 스캔하세요.' if started else 'setup.bat를 실행해 portable Tesseract를 설치하세요.'
        result.installer_started = result.installer_started or started
        result.add_error(f'OCR 엔진을 사용할 수 없습니다: {exc}\n{suffix}')

    ok, reason = _can_create_virtual_gamepad()
    if ok:
        result.add_info('컨트롤러 런타임 확인 완료: ViGEmBus 가상 패드 생성 가능')
    else:
        installer: Path | None = None
        try:
            installer = ensure_controller_installer(download=download)
        except Exception as exc:
            result.add_error(f'컨트롤러 설치 파일 다운로드 실패: {exc}')
        started = False
        if installer and launch_installers:
            try:
                started = launch_controller_installer(installer)
            except Exception:
                started = False
        result.installer_started = result.installer_started or started
        if started:
            result.add_error(f'{reason}\nViGEmBus 설치 창을 열었습니다. 설치 완료 후 다시 스캔하세요.')
        else:
            hint = f'설치 파일 위치: {installer}' if installer else 'setup.bat를 실행해 컨트롤러 런타임을 준비하세요.'
            result.add_error(f'{reason}\n{hint}')

    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('--download-only', action='store_true')
    parser.add_argument('--no-download', action='store_true')
    parser.add_argument('--no-launch', action='store_true')
    args = parser.parse_args(argv)

    if args.download_only:
        path = ensure_controller_installer(download=not args.no_download)
        print(f'[OK] Controller installer: {path}' if path else '[WARN] Controller installer not available.')
        return 0 if path else 1

    result = prepare_scan_runtime(download=not args.no_download, launch_installers=not args.no_launch)
    print(result.message)
    return 0 if result.ok else 2


if __name__ == '__main__':
    raise SystemExit(main())
