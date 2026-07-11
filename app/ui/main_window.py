from __future__ import annotations

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QFrame, QLabel, QVBoxLayout, QHBoxLayout,
    QPushButton, QButtonGroup, QStackedWidget, QSizePolicy
)

from app.ui.cafe_page import CafePage
from app.ui.loadout_page import LoadoutPage
from app.ui.settings_page import SettingsPage
from app.ui.style import APP_QSS
from app.ui.tutorial import TutorialOverlay, should_show_tutorial
from app.version import APP_NAME, APP_VERSION


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(f'{APP_NAME} - {APP_VERSION}')
        self.resize(1530, 920)
        self.setMinimumSize(1510, 800)
        self.setStyleSheet(APP_QSS)

        root = QWidget()
        root.setObjectName('Root')
        self.setCentralWidget(root)
        main_layout = QHBoxLayout(root)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        sidebar = QFrame()
        sidebar.setObjectName('Sidebar')
        sidebar.setFixedWidth(230)
        side_layout = QVBoxLayout(sidebar)
        side_layout.setContentsMargins(18, 22, 18, 18)
        side_layout.setSpacing(12)

        app_title = QLabel('NTE Tool')
        app_title.setObjectName('AppTitle')
        app_subtitle = QLabel('Neverness To Everness')
        app_subtitle.setObjectName('AppSubtitle')
        app_subtitle.setWordWrap(True)
        side_layout.addWidget(app_title)
        side_layout.addWidget(app_subtitle)
        side_layout.addSpacing(18)

        self.stack = QStackedWidget()
        self.cafe_page = CafePage()
        self.loadout_page = LoadoutPage()
        self.settings_page = SettingsPage()
        self.stack.addWidget(self.cafe_page)
        self.stack.addWidget(self.loadout_page)
        self.stack.addWidget(self.settings_page)

        nav_group = QButtonGroup(self)
        nav_group.setExclusive(True)
        cafe_button = self.make_nav_button('☕  별미 카페 자동화')
        loadout_button = self.make_nav_button('◇  장착 시뮬레이터')
        settings_button = self.make_nav_button('⚙  설정')
        nav_group.addButton(cafe_button, 0)
        nav_group.addButton(loadout_button, 1)
        nav_group.addButton(settings_button, 2)
        nav_group.idClicked.connect(self.stack.setCurrentIndex)
        cafe_button.setChecked(True)
        self.nav_group = nav_group
        self.nav_buttons = [cafe_button, loadout_button, settings_button]
        side_layout.addWidget(cafe_button)
        side_layout.addWidget(loadout_button)
        side_layout.addWidget(settings_button)
        side_layout.addSpacing(10)

        divider = QFrame()
        divider.setFrameShape(QFrame.HLine)
        divider.setStyleSheet('color: #263653; background: #263653; max-height: 1px;')
        side_layout.addWidget(divider)
        self.sidebar_scan_status = QLabel('드라이브 불러오는 중... 0% (0/0개)')
        self.sidebar_scan_status.setObjectName('AppSubtitle')
        self.sidebar_scan_status.setWordWrap(True)
        side_layout.addWidget(self.sidebar_scan_status)
        side_layout.addStretch(1)
        try:
            self.loadout_page.scan_status_changed.connect(self.sidebar_scan_status.setText)
        except Exception:
            pass
        version = QLabel(APP_VERSION)
        version.setObjectName('AppSubtitle')
        version.setAlignment(Qt.AlignLeft | Qt.AlignBottom)
        side_layout.addWidget(version)

        main_layout.addWidget(sidebar)
        main_layout.addWidget(self.stack, 1)
        self.tutorial_overlay: TutorialOverlay | None = None
        QTimer.singleShot(600, self.show_tutorial)

    @staticmethod
    def make_nav_button(text: str) -> QPushButton:
        button = QPushButton(text)
        button.setObjectName('NavButton')
        button.setCheckable(True)
        button.setCursor(Qt.PointingHandCursor)
        button.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        return button

    def set_current_page(self, page: str):
        index = {'cafe': 0, 'loadout': 1, 'settings': 2}.get(page, 0)
        self.stack.setCurrentIndex(index)
        if 0 <= index < len(self.nav_buttons):
            self.nav_buttons[index].setChecked(True)

    def show_tutorial(self):
        if not self.isVisible() or not should_show_tutorial():
            return
        self.tutorial_overlay = TutorialOverlay(self)
        self.tutorial_overlay.show()
