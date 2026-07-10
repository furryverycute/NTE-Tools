from __future__ import annotations

from PySide6.QtCore import QThread, QTimer, Signal
from PySide6.QtWidgets import (
    QApplication,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from app.updater import fetch_latest_release, install_kind_label, install_update, select_asset
from app.version import APP_VERSION, GITHUB_RELEASES_URL, GITHUB_REPO


class UpdateCheckWorker(QThread):
    completed = Signal(dict)

    def run(self):
        self.completed.emit(fetch_latest_release())


class UpdateInstallWorker(QThread):
    completed = Signal(dict)

    def __init__(self, release: dict):
        super().__init__()
        self.release = release

    def run(self):
        self.completed.emit(install_update(self.release))


class SettingsPage(QWidget):
    def __init__(self):
        super().__init__()
        self.pending_release: dict | None = None
        self.check_worker: UpdateCheckWorker | None = None
        self.install_worker: UpdateInstallWorker | None = None

        root = QVBoxLayout(self)
        root.setContentsMargins(24, 24, 24, 24)
        root.setSpacing(16)

        title = QLabel('설정')
        title.setObjectName('PageTitle')
        root.addWidget(title)

        card = QFrame()
        card.setObjectName('SettingsCard')
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(18, 18, 18, 18)
        card_layout.setSpacing(12)

        update_title = QLabel('업데이트')
        update_title.setObjectName('SectionTitle')
        card_layout.addWidget(update_title)

        self.version_label = QLabel(f'현재 버전: {APP_VERSION}')
        self.version_label.setObjectName('Muted')
        card_layout.addWidget(self.version_label)

        repo_label = QLabel(f'<a href="{GITHUB_RELEASES_URL}">{GITHUB_REPO} 릴리스</a>')
        repo_label.setObjectName('Muted')
        repo_label.setOpenExternalLinks(True)
        card_layout.addWidget(repo_label)

        self.install_kind_label = QLabel(f'감지된 실행 방식: {install_kind_label()}')
        self.install_kind_label.setObjectName('Muted')
        card_layout.addWidget(self.install_kind_label)

        action_row = QHBoxLayout()
        action_row.setSpacing(8)
        self.update_btn = QPushButton('업데이트 확인')
        self.update_btn.setObjectName('PrimaryButton')
        self.update_btn.clicked.connect(self.on_update_button_clicked)
        action_row.addWidget(self.update_btn)
        action_row.addStretch(1)
        card_layout.addLayout(action_row)

        self.status_label = QLabel('GitHub 릴리스를 확인할 수 있습니다.')
        self.status_label.setObjectName('Muted')
        self.status_label.setWordWrap(True)
        card_layout.addWidget(self.status_label)

        self.assets_label = QLabel('-')
        self.assets_label.setObjectName('SettingsAssetText')
        self.assets_label.setWordWrap(True)
        card_layout.addWidget(self.assets_label)

        root.addWidget(card)
        root.addStretch(1)

    def on_update_button_clicked(self):
        if self.pending_release:
            self.install_pending_update()
        else:
            self.check_for_updates()

    def check_for_updates(self):
        self.pending_release = None
        self.update_btn.setEnabled(False)
        self.update_btn.setText('확인 중...')
        self.status_label.setText('GitHub 릴리스를 확인하는 중입니다.')
        self.assets_label.setText('-')
        self.check_worker = UpdateCheckWorker()
        self.check_worker.completed.connect(self.on_check_completed)
        self.check_worker.start()

    def on_check_completed(self, result: dict):
        self.update_btn.setEnabled(True)
        self.update_btn.setText('업데이트 확인')
        if not result.get('ok'):
            self.status_label.setText(result.get('message', '업데이트 확인에 실패했습니다.'))
            return
        if not result.get('has_release'):
            self.status_label.setText(result.get('message', '아직 게시된 릴리스가 없습니다.'))
            return

        tag = result.get('tag_name') or '-'
        assets = result.get('assets') or []
        installer_count = sum(1 for asset in assets if asset.get('type') == 'installer')
        portable_count = sum(1 for asset in assets if asset.get('type') == 'portable')
        self.assets_label.setText(
            f'감지된 릴리스 파일: 설치형 {installer_count}개 / 포터블 {portable_count}개\n'
            f'현재 실행 방식: {install_kind_label()}'
        )

        if not result.get('update_available'):
            self.status_label.setText(f'최신 버전입니다. 최신 릴리스: {tag}')
            return
        if not assets:
            self.status_label.setText(f'새 릴리스 {tag}가 있지만 지원되는 설치형/포터블 파일이 없습니다.')
            return
        if not select_asset(result):
            self.status_label.setText(f'새 릴리스 {tag}가 있지만 현재 실행 방식({install_kind_label()})에 맞는 파일이 없습니다.')
            return

        self.pending_release = result
        self.update_btn.setText('업데이트')
        self.status_label.setText(f'새 업데이트를 찾았습니다: {tag}')

    def install_pending_update(self):
        if not self.pending_release:
            return
        self.update_btn.setEnabled(False)
        self.update_btn.setText('업데이트 중...')
        self.status_label.setText(f'{install_kind_label()} 업데이트 파일을 다운로드하고 설치하는 중입니다.')
        self.install_worker = UpdateInstallWorker(self.pending_release)
        self.install_worker.completed.connect(self.on_install_completed)
        self.install_worker.start()

    def on_install_completed(self, result: dict):
        self.update_btn.setEnabled(True)
        self.update_btn.setText('업데이트')
        self.status_label.setText(result.get('message', '업데이트 작업이 끝났습니다.'))
        if result.get('ok') and result.get('quit_current'):
            self.update_btn.setEnabled(False)
            QTimer.singleShot(1200, QApplication.instance().quit)
