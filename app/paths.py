from __future__ import annotations

from pathlib import Path
import sys


def resource_path(*parts: str) -> Path:
    """Return a resource path that works both in source and PyInstaller builds."""
    if hasattr(sys, '_MEIPASS'):
        base = Path(getattr(sys, '_MEIPASS'))
    else:
        base = Path(__file__).resolve().parent.parent
    return base.joinpath(*parts)


def asset_path(*parts: str) -> Path:
    return resource_path('app', 'assets', *parts)
