from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QIcon

from app.paths import resource_path
from app.ui.main_window import MainWindow
from app.version import APP_NAME


def main() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setOrganizationName('Minong')

    icon_path = resource_path('app', 'assets', 'icon.ico')
    if icon_path.exists():
        app.setWindowIcon(QIcon(str(icon_path)))

    window = MainWindow()
    if icon_path.exists():
        window.setWindowIcon(QIcon(str(icon_path)))
    window.show()

    if '--smoke-test' in sys.argv:
        return 0
    return app.exec()


if __name__ == '__main__':
    raise SystemExit(main())
