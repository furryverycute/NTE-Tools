from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from PySide6.QtCore import QPoint, QRect, QRectF, Qt, QTimer
from PySide6.QtGui import QColor, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import (
    QCheckBox,
    QDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from app.state_store import load_section, save_section


TUTORIAL_VERSION = 'nte-tool-guide-2026-07-11-1'


def should_show_tutorial() -> bool:
    return load_section('tutorial').get('dismissed_version') != TUTORIAL_VERSION


def mark_tutorial_dismissed() -> None:
    state = load_section('tutorial')
    state['dismissed_version'] = TUTORIAL_VERSION
    save_section('tutorial', state)


@dataclass
class TutorialStep:
    page: str
    title: str
    targets: Callable[[], list[QWidget]]
    messages: list[str]
    prepare: Callable[[], None] | None = None


class TutorialOverlay(QDialog):
    def __init__(self, main_window):
        super().__init__(main_window)
        self.main_window = main_window
        self.index = 0
        self._target_rects: list[QRect] = []
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Dialog)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setModal(True)

        self.card = QFrame(self)
        self.card.setObjectName('TutorialCard')
        self.card.setStyleSheet(
            'QFrame#TutorialCard { background: #111827; border: 1px solid #ffd25e; border-radius: 14px; }'
            'QLabel#TutorialTitle { color: #ffffff; font-size: 16px; font-weight: 900; }'
            'QLabel#TutorialText { color: #dbe7ff; font-size: 12px; line-height: 1.35; }'
            'QPushButton { background: #1a2540; border: 1px solid #314465; border-radius: 8px; padding: 8px 12px; }'
            'QPushButton#TutorialPrimary { background: #4f7cff; border-color: #7ea0ff; font-weight: 800; }'
        )
        card_layout = QVBoxLayout(self.card)
        card_layout.setContentsMargins(16, 14, 16, 14)
        card_layout.setSpacing(10)
        self.title_label = QLabel()
        self.title_label.setObjectName('TutorialTitle')
        card_layout.addWidget(self.title_label)
        self.body_layout = QVBoxLayout()
        self.body_layout.setContentsMargins(0, 0, 0, 0)
        self.body_layout.setSpacing(6)
        card_layout.addLayout(self.body_layout)
        self.dont_show_again = QCheckBox('다시 보지 않기')
        self.dont_show_again.setVisible(False)
        card_layout.addWidget(self.dont_show_again)
        button_row = QHBoxLayout()
        button_row.addStretch(1)
        self.prev_btn = QPushButton('이전')
        self.skip_btn = QPushButton('닫기')
        self.next_btn = QPushButton('다음')
        self.next_btn.setObjectName('TutorialPrimary')
        self.prev_btn.clicked.connect(self.prev_step)
        self.skip_btn.clicked.connect(self.close)
        self.next_btn.clicked.connect(self.next_step)
        button_row.addWidget(self.prev_btn)
        button_row.addWidget(self.skip_btn)
        button_row.addWidget(self.next_btn)
        card_layout.addLayout(button_row)

        self.steps = self._build_steps()

    def _build_steps(self) -> list[TutorialStep]:
        cafe = self.main_window.cafe_page
        loadout = self.main_window.loadout_page
        return [
            TutorialStep(
                page='cafe',
                title='별미 카페 자동화 1/3',
                targets=lambda: [cafe.trend_panel, cafe.level_panel, cafe.interior_panel],
                messages=[
                    '게임 내 트렌드를 확인하고 이곳을 변경합니다.',
                    '게임 내 매장 레벨과 동일하게 설정해주세요.',
                    "인테리어 계수: 인테리어의 인기도를 클릭하면 속성 상세정보를 볼 수 있습니다. '모든 가게의 수입 계수 증가 총합' 부분을 여기에 입력해주세요.",
                ],
            ),
            TutorialStep(
                page='cafe',
                title='별미 카페 자동화 2/3',
                targets=lambda: [cafe.employee_panel],
                messages=[
                    '캐릭터의 ON/OFF로 보유한 캐릭터 설정이 가능합니다.',
                    '각 캐릭터의 도시 스킬 레벨을 설정해주세요.',
                ],
            ),
            TutorialStep(
                page='cafe',
                title='별미 카페 자동화 3/3',
                targets=lambda: [cafe.result_panel],
                messages=['모든 설정이 끝나면 이곳에서 실시간으로 최적의 메뉴와 직원을 추천해줍니다.'],
            ),
            TutorialStep(
                page='loadout',
                title='장착 시뮬레이터 1/5',
                targets=lambda: [loadout.character_tile, loadout.ark_tile],
                messages=['이곳에서 캐릭터와 아크를 변경할 수 있습니다.'],
            ),
            TutorialStep(
                page='loadout',
                title='장착 시뮬레이터 2/5',
                targets=lambda: [loadout.scan_panel],
                messages=[
                    '가방을 스캔합니다. 스캔 중 마우스나 키보드 입력이 감지되면 스캔이 꼬일 수 있으니 가만히 기다려주세요. 스캔을 다시 시도할 경우, 기존 가방을 초기화하고 다시 스캔합니다.',
                    '추천 장착을 통해 현재 장비로 가장 최적화된 장비를 찾아줍니다.',
                    '장착이 끝나면 이곳을 통해 변동된 수치를 확인할 수 있습니다.',
                ],
            ),
            TutorialStep(
                page='loadout',
                title='장착 시뮬레이터 3/5',
                targets=lambda: [loadout.cartridge_tabs, loadout.module_tabs],
                messages=['카트리지와 드라이브의 옵션을 입맛대로 커스텀하여 장착해볼 수 있는 기능입니다.'],
                prepare=lambda: (loadout.cartridge_tabs.setCurrentIndex(0), loadout.module_tabs.setCurrentIndex(0)),
            ),
            TutorialStep(
                page='loadout',
                title='장착 시뮬레이터 4/5',
                targets=lambda: [loadout.cartridge_bag_tab, loadout.module_bag_tab],
                messages=['스캔된 카트리지와 드라이브는 이곳에 보관됩니다.'],
                prepare=lambda: (loadout.cartridge_tabs.setCurrentIndex(1), loadout.module_tabs.setCurrentIndex(1)),
            ),
            TutorialStep(
                page='loadout',
                title='장착 시뮬레이터 5/5',
                targets=lambda: [loadout.device],
                messages=['드라이브 모듈 선택 후 이곳의 빈칸을 클릭하여 장착할 수 있습니다.'],
            ),
        ]

    def showEvent(self, event):
        super().showEvent(event)
        self.update_step()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.update_card_position()

    def update_step(self):
        step = self.steps[self.index]
        self.main_window.set_current_page(step.page)
        if step.prepare:
            step.prepare()
        self.prev_btn.setEnabled(self.index > 0)
        self.next_btn.setText('완료' if self.index == len(self.steps) - 1 else '다음')
        self.dont_show_again.setVisible(self.index == len(self.steps) - 1)
        self.title_label.setText(step.title)
        while self.body_layout.count():
            item = self.body_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()
        for message in step.messages:
            label = QLabel(f'• {message}')
            label.setObjectName('TutorialText')
            label.setWordWrap(True)
            self.body_layout.addWidget(label)
        QTimer.singleShot(0, self.rebuild_targets)

    def rebuild_targets(self):
        self.setGeometry(self.main_window.geometry())
        step = self.steps[self.index]
        rects: list[QRect] = []
        for widget in step.targets():
            if widget is None or not widget.isVisible():
                continue
            top_left = self.mapFromGlobal(widget.mapToGlobal(QPoint(0, 0)))
            rects.append(QRect(top_left, widget.size()).adjusted(-8, -8, 8, 8))
        self._target_rects = rects
        self.update_card_position()
        self.update()

    def update_card_position(self):
        if not self._target_rects:
            self.card.setGeometry(24, 24, 460, self.card.sizeHint().height())
            return
        union = self._target_rects[0]
        for rect in self._target_rects[1:]:
            union = union.united(rect)
        card_w = 470
        card_h = self.card.sizeHint().height()
        margin = 24

        def clamp_rect(x: int, y: int) -> QRect:
            max_x = max(margin, self.width() - card_w - margin)
            max_y = max(margin, self.height() - card_h - margin)
            return QRect(
                min(max(margin, x), max_x),
                min(max(margin, y), max_y),
                card_w,
                card_h,
            )

        anchors = [union, *self._target_rects]
        candidates: list[QRect] = []
        for rect in anchors:
            candidates.extend([
                clamp_rect(rect.center().x() - card_w // 2, rect.bottom() + 18),
                clamp_rect(rect.center().x() - card_w // 2, rect.top() - card_h - 18),
                clamp_rect(rect.right() + 18, rect.center().y() - card_h // 2),
                clamp_rect(rect.left() - card_w - 18, rect.center().y() - card_h // 2),
            ])
        candidates.extend([
            clamp_rect(margin, margin),
            clamp_rect(self.width() - card_w - margin, margin),
            clamp_rect(margin, self.height() - card_h - margin),
            clamp_rect(self.width() - card_w - margin, self.height() - card_h - margin),
            clamp_rect(self.width() // 2 - card_w // 2, self.height() // 2 - card_h // 2),
        ])

        def intersection_area(a: QRect, b: QRect) -> int:
            inter = a.intersected(b)
            return max(0, inter.width()) * max(0, inter.height())

        target_center = union.center()

        def score(candidate: QRect) -> tuple[int, int]:
            padded = candidate.adjusted(-10, -10, 10, 10)
            overlap = sum(intersection_area(padded, rect) for rect in self._target_rects)
            distance = (
                abs(candidate.center().x() - target_center.x()) +
                abs(candidate.center().y() - target_center.y())
            )
            return overlap, distance

        best = min(candidates, key=score)
        self.card.setGeometry(best)

    def next_step(self):
        if self.index >= len(self.steps) - 1:
            if self.dont_show_again.isChecked():
                mark_tutorial_dismissed()
            self.close()
            return
        self.index += 1
        self.update_step()

    def prev_step(self):
        if self.index <= 0:
            return
        self.index -= 1
        self.update_step()

    def closeEvent(self, event):
        if self.dont_show_again.isVisible() and self.dont_show_again.isChecked():
            mark_tutorial_dismissed()
        super().closeEvent(event)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        overlay = QPainterPath()
        overlay.addRect(QRectF(self.rect()))
        holes = QPainterPath()
        for rect in self._target_rects:
            holes.addRoundedRect(QRectF(rect), 12, 12)
        painter.fillPath(overlay.subtracted(holes), QColor(0, 0, 0, 190))
        painter.setPen(QPen(QColor('#ffd25e'), 3))
        for rect in self._target_rects:
            painter.drawRoundedRect(QRectF(rect), 12, 12)
