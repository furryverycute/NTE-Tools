from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from typing import Any


STATE_FILE_NAME = 'app_state.json'


def state_dir() -> Path:
    base = Path(os.environ.get('LOCALAPPDATA') or os.environ.get('APPDATA') or Path.home())
    target = base / 'NTE Tool'
    target.mkdir(parents=True, exist_ok=True)
    return target


def state_path() -> Path:
    return state_dir() / STATE_FILE_NAME


def load_state() -> dict[str, Any]:
    path = state_path()
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding='utf-8'))
    except Exception:
        return {}
    return data if isinstance(data, dict) else {}


def save_state(data: dict[str, Any]) -> None:
    path = state_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(prefix=f'.{STATE_FILE_NAME}.', suffix='.tmp', dir=str(path.parent))
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as fp:
            json.dump(data, fp, ensure_ascii=False, indent=2)
        Path(tmp_name).replace(path)
    finally:
        try:
            Path(tmp_name).unlink(missing_ok=True)
        except OSError:
            pass


def load_section(name: str) -> dict[str, Any]:
    section = load_state().get(name, {})
    return section if isinstance(section, dict) else {}


def save_section(name: str, section: dict[str, Any]) -> None:
    data = load_state()
    data[name] = section
    save_state(data)
