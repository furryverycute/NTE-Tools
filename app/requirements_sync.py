from __future__ import annotations

import argparse
import hashlib
import subprocess
import sys
from pathlib import Path


RUNTIME_REQUIREMENTS = ('requirements.txt', 'requirements-scan.txt')
BUILD_REQUIREMENTS = ('requirements-build.txt',)


def project_root() -> Path:
    return Path(__file__).resolve().parents[1]


def selected_requirement_files(root: Path, include_build: bool = False) -> list[Path]:
    names = list(RUNTIME_REQUIREMENTS)
    if include_build:
        names.extend(BUILD_REQUIREMENTS)
    return [root / name for name in names if (root / name).exists()]


def requirement_hash(files: list[Path]) -> str:
    digest = hashlib.sha256()
    for path in files:
        digest.update(path.name.encode('utf-8'))
        digest.update(b'\0')
        digest.update(path.read_bytes())
        digest.update(b'\0')
    return digest.hexdigest()


def state_file(include_build: bool = False) -> Path:
    suffix = 'build' if include_build else 'runtime'
    return Path(sys.prefix) / f'.nte_requirements_{suffix}.sha256'


def sync_requirements(include_build: bool = False, force: bool = False) -> bool:
    root = project_root()
    files = selected_requirement_files(root, include_build=include_build)
    if not files:
        print('[requirements] No requirement files found.')
        return True

    current_hash = requirement_hash(files)
    marker = state_file(include_build=include_build)
    if not force and marker.exists() and marker.read_text(encoding='utf-8').strip() == current_hash:
        print('[requirements] Requirement files unchanged. Skipping pip install.')
        return True

    print('[requirements] Installing updated requirements...')
    subprocess.check_call([sys.executable, '-m', 'pip', 'install', '--upgrade', 'pip'])
    cmd = [sys.executable, '-m', 'pip', 'install']
    for path in files:
        cmd.extend(['-r', str(path)])
    subprocess.check_call(cmd)
    marker.write_text(current_hash, encoding='utf-8')
    print('[requirements] Requirement sync complete.')
    return True


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('--include-build', action='store_true')
    parser.add_argument('--force', action='store_true')
    args = parser.parse_args(argv)
    sync_requirements(include_build=args.include_build, force=args.force)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
