from __future__ import annotations

from functools import partial
from pathlib import Path
import os
import urllib.request

from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDoubleSpinBox,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from app.core.cafe_optimizer import CafeOptimizerEngine, CafeResult
from app.data import CAFE_TREND_OPTIONS, CHARACTER_AVATAR_FILES, EMPLOYEE_NAMES, MENU_IMAGE_FILES, STORE_NAMES
from app.paths import asset_path
from app.ui.widgets import Card


class TopMetric(QFrame):
    def __init__(self, title: str, value: str = '-', caption: str = ''):
        super().__init__()
        self.setObjectName('CafeTopBox')
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 14, 18, 14)
        layout.setSpacing(5)

        self.title_label = QLabel(title)
        self.title_label.setObjectName('CafeTopTitle')
        self.value_label = QLabel(value)
        self.value_label.setObjectName('CafeTopValue')
        self.caption_label = QLabel(caption)
        self.caption_label.setObjectName('CafeCaption')
        self.caption_label.setWordWrap(True)

        layout.addWidget(self.title_label)
        layout.addWidget(self.value_label)
        layout.addWidget(self.caption_label)

    def set_value(self, value: str, caption: str = ''):
        self.value_label.setText(value)
        self.caption_label.setText(caption)


class AssetImage(QLabel):
    def __init__(self, size: int, object_name: str):
        super().__init__()
        self.image_size = size
        self.setObjectName(object_name)
        self.setFixedSize(size, size)
        self.setAlignment(Qt.AlignCenter)
        self.setText('')

    def set_asset(self, folder: str, filename: str | None):
        if not filename:
            self.clear()
            self.setText('-')
            return
        if str(filename).startswith(('http://', 'https://')):
            cache = Path(os.environ.get('APPDATA') or Path.home()) / 'NTE Tool' / 'asset_cache'
            cache.mkdir(parents=True, exist_ok=True)
            path = cache / str(filename).rstrip('/').split('/')[-1]
            if not path.exists() or path.stat().st_size == 0:
                try:
                    req = urllib.request.Request(str(filename), headers={'User-Agent': 'Mozilla/5.0'})
                    with urllib.request.urlopen(req, timeout=8) as response:
                        path.write_bytes(response.read())
                except Exception:
                    path = None
        else:
            path = asset_path(folder, filename)
        pixmap = QPixmap(str(path)) if path else QPixmap()
        if pixmap.isNull():
            self.clear()
            self.setText('-')
            return
        scaled = pixmap.scaled(
            self.image_size,
            self.image_size,
            Qt.KeepAspectRatio,
            Qt.SmoothTransformation,
        )
        self.setPixmap(scaled)
        self.setText('')


class StoreResultCard(QFrame):
    def __init__(self, index: int):
        super().__init__()
        self.index = index
        self.setObjectName('StoreResultCard')
        self.setMinimumHeight(220)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(8)

        self.title = QLabel(f'가게{index + 1}')
        self.title.setObjectName('StoreTitle')
        self.store_name = QLabel('-')
        self.store_name.setObjectName('CafeCaption')

        self.menu_image = AssetImage(66, 'MenuThumb')
        image_row = QHBoxLayout()
        image_row.addStretch(1)
        image_row.addWidget(self.menu_image)
        image_row.addStretch(1)

        self.menu_name = QLabel('계산 전')
        self.menu_name.setObjectName('MenuName')
        self.menu_name.setWordWrap(True)
        self.menu_name.setAlignment(Qt.AlignCenter)

        self.staff_avatar_1 = AssetImage(28, 'SmallEmployeeAvatar')
        self.staff_avatar_2 = AssetImage(28, 'SmallEmployeeAvatar')
        self.staff = QLabel('-')
        self.staff.setObjectName('CafeCaption')
        self.staff.setWordWrap(True)
        staff_row = QHBoxLayout()
        staff_row.setSpacing(6)
        staff_row.addWidget(self.staff_avatar_1)
        staff_row.addWidget(self.staff_avatar_2)
        staff_row.addWidget(self.staff, 1)

        self.income = QLabel('-')
        self.income.setObjectName('IncomeValue')
        self.income.setAlignment(Qt.AlignCenter)
        self.trend = QLabel('')
        self.trend.setObjectName('TrendBadge')
        self.trend.setAlignment(Qt.AlignCenter)

        layout.addWidget(self.title)
        layout.addWidget(self.store_name)
        layout.addLayout(image_row)
        layout.addWidget(self.menu_name)
        layout.addLayout(staff_row)
        layout.addStretch(1)
        layout.addWidget(self.income)
        layout.addWidget(self.trend)

    def _set_staff_images(self, employees: tuple[str, str] | tuple):
        names = list(employees)
        first = names[0] if len(names) > 0 else None
        second = names[1] if len(names) > 1 else None
        self.staff_avatar_1.set_asset('datamine/characters', CHARACTER_AVATAR_FILES.get(first or ''))
        self.staff_avatar_2.set_asset('datamine/characters', CHARACTER_AVATAR_FILES.get(second or ''))

    def set_pick(self, pick, trend_value: float):
        self.setProperty('inactive', False)
        self.style().unpolish(self)
        self.style().polish(self)
        self.title.setText(f'가게{self.index + 1}')
        self.store_name.setText(pick.store_name)
        self.menu_image.set_asset('menu', MENU_IMAGE_FILES.get(pick.menu.name) or f'menu_{pick.menu.id:02d}.webp')
        self.menu_name.setText(pick.menu.display_name)
        self.staff.setText(' / '.join(pick.employees))
        self._set_staff_images(pick.employees)
        self.income.setText(f'{pick.income:,.2f} 폰즈')
        self.trend.setText(f'트렌드 +{trend_value:g}' if pick.trend_applied else '트렌드 미적용')

    def set_inactive(self, message: str):
        self.setProperty('inactive', True)
        self.style().unpolish(self)
        self.style().polish(self)
        self.title.setText(f'가게{self.index + 1}')
        self.store_name.setText('비활성 지점')
        self.menu_image.set_asset('', None)
        self.menu_name.setText(message)
        self.staff.setText('-')
        self.staff_avatar_1.set_asset('', None)
        self.staff_avatar_2.set_asset('', None)
        self.income.setText('-')
        self.trend.setText('')


class EmployeeWidget(QFrame):
    def __init__(self, name: str, default_level: int = 5):
        super().__init__()
        self.name = name
        self.setObjectName('EmployeeMiniCard')
        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)

        self.avatar = AssetImage(34, 'EmployeeAvatar')
        self.avatar.set_asset('datamine/characters', CHARACTER_AVATAR_FILES.get(name))
        self.active = QCheckBox(name)
        self.active.setChecked(True)
        self.active.setMinimumWidth(64)
        self.level = QSpinBox()
        self.level.setRange(0, 5)
        self.level.setValue(default_level)
        self.level.setPrefix('Lv.')
        self.level.setFixedWidth(86)
        self.level.setAlignment(Qt.AlignCenter)

        layout.addWidget(self.avatar, 0)
        layout.addWidget(self.active, 1)
        layout.addWidget(self.level, 0)

    def state(self) -> tuple[bool, int]:
        return self.active.isChecked(), self.level.value()

    def set_level(self, level: int):
        self.level.setValue(level)

    def set_active(self, checked: bool):
        self.active.setChecked(checked)


class CafePage(QWidget):
    def __init__(self):
        super().__init__()
        self.engine = CafeOptimizerEngine()
        self.employee_widgets: dict[str, EmployeeWidget] = {}
        self.store_cards: list[StoreResultCard] = []

        root = QVBoxLayout(self)
        root.setContentsMargins(20, 18, 20, 18)
        root.setSpacing(14)

        # ------------------------------------------------------------------
        # Top row: hour income / trend dropdown / applied skill summary
        # ------------------------------------------------------------------
        top = QHBoxLayout()
        top.setSpacing(14)

        self.income_box = TopMetric('시간당 매출', '계산 전', '인테리어 계수를 포함한 값도 함께 표시됩니다.')
        top.addWidget(self.income_box, 2)

        trend_panel = QFrame()
        trend_panel.setObjectName('CafeTopBox')
        trend_layout = QVBoxLayout(trend_panel)
        trend_layout.setContentsMargins(18, 14, 18, 14)
        trend_layout.setSpacing(8)
        trend_title = QLabel('오늘의 트렌드')
        trend_title.setObjectName('CafeTopTitle')
        self.trend_combo = QComboBox()
        self.trend_combo.addItems(CAFE_TREND_OPTIONS)
        if '커피 원두' in CAFE_TREND_OPTIONS:
            self.trend_combo.setCurrentText('커피 원두')
        trend_layout.addWidget(trend_title)
        trend_layout.addWidget(self.trend_combo)
        top.addWidget(trend_panel, 2)

        skill_panel = QFrame()
        skill_panel.setObjectName('CafeTopBox')
        skill_layout = QVBoxLayout(skill_panel)
        skill_layout.setContentsMargins(18, 14, 18, 14)
        skill_layout.setSpacing(6)
        skill_title = QLabel('적용 효과 요약')
        skill_title.setObjectName('CafeTopTitle')
        self.skill_summary = QLabel('계산 전')
        self.skill_summary.setObjectName('CafeSkillSummary')
        self.skill_summary.setWordWrap(True)
        skill_layout.addWidget(skill_title)
        skill_layout.addWidget(self.skill_summary, 1)
        top.addWidget(skill_panel, 3)
        root.addLayout(top)

        # ------------------------------------------------------------------
        # Result section: 5 store cards
        # ------------------------------------------------------------------
        result_panel = QFrame()
        result_panel.setObjectName('CafeResultPanel')
        result_layout = QVBoxLayout(result_panel)
        result_layout.setContentsMargins(0, 0, 0, 0)
        result_layout.setSpacing(0)

        result_title = QLabel('추천 결과')
        result_title.setObjectName('ResultPanelTitle')
        result_title.setAlignment(Qt.AlignCenter)
        result_layout.addWidget(result_title)

        store_grid = QHBoxLayout()
        store_grid.setContentsMargins(0, 0, 0, 0)
        store_grid.setSpacing(0)
        for index in range(5):
            card = StoreResultCard(index)
            self.store_cards.append(card)
            store_grid.addWidget(card, 1)
        result_layout.addLayout(store_grid)
        root.addWidget(result_panel, 2)

        # ------------------------------------------------------------------
        # Condition area: left rail + employee skills + condition controls
        # ------------------------------------------------------------------
        bottom = QHBoxLayout()
        bottom.setSpacing(0)

        rail = QFrame()
        rail.setObjectName('ConditionRail')
        rail.setFixedWidth(130)
        rail_layout = QVBoxLayout(rail)
        rail_layout.setAlignment(Qt.AlignCenter)
        rail_label = QLabel('조건 설정')
        rail_label.setObjectName('ConditionRailLabel')
        rail_label.setAlignment(Qt.AlignCenter)
        rail_layout.addWidget(rail_label)
        bottom.addWidget(rail)

        condition_right = QVBoxLayout()
        condition_right.setSpacing(0)

        employee_panel = QFrame()
        employee_panel.setObjectName('ConditionPanel')
        employee_layout = QVBoxLayout(employee_panel)
        employee_layout.setContentsMargins(22, 18, 22, 16)
        employee_layout.setSpacing(12)
        employee_header = QHBoxLayout()
        employee_title = QLabel('직원 스킬')
        employee_title.setObjectName('LargeSectionTitle')
        employee_hint = QLabel('ON/OFF와 Lv.0~5를 조정한 뒤 계산을 실행합니다.')
        employee_hint.setObjectName('CafeCaption')
        employee_header.addWidget(employee_title)
        employee_header.addWidget(employee_hint, 1)
        employee_layout.addLayout(employee_header)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.viewport().setStyleSheet("background: transparent;")
        scroll.setMinimumHeight(130)
        employee_container = QWidget()
        employee_container.setObjectName("EmployeeGridContainer")
        employee_container.setStyleSheet("background: transparent;")
        employee_grid = QGridLayout(employee_container)
        employee_grid.setContentsMargins(0, 0, 0, 0)
        employee_grid.setHorizontalSpacing(10)
        employee_grid.setVerticalSpacing(10)
        for idx, name in enumerate(EMPLOYEE_NAMES):
            widget = EmployeeWidget(name, 5)
            self.employee_widgets[name] = widget
            row, col = divmod(idx, 3)
            employee_grid.addWidget(widget, row, col)
            widget.active.stateChanged.connect(self.calculate)
            widget.level.valueChanged.connect(self.calculate)
        scroll.setWidget(employee_container)
        employee_layout.addWidget(scroll)
        condition_right.addWidget(employee_panel, 2)

        control_row = QHBoxLayout()
        control_row.setSpacing(0)

        level_panel = self._control_panel('매장 레벨')
        self.level_spin = QSpinBox()
        self.level_spin.setRange(1, 40)
        self.level_spin.setValue(25)
        self.level_spin.setSuffix(' Lv')
        self.shop_count_label = QLabel('활성 지점: 5개')
        self.shop_count_label.setObjectName('CafeCaption')
        level_panel.layout.addWidget(self.level_spin)
        level_panel.layout.addWidget(self.shop_count_label)
        control_row.addWidget(level_panel, 1)

        interior_panel = self._control_panel('인테리어 계수')
        self.interior_spin = QDoubleSpinBox()
        self.interior_spin.setRange(0.0, 10.0)
        self.interior_spin.setSingleStep(0.01)
        self.interior_spin.setDecimals(3)
        self.interior_spin.setValue(0.0)
        self.interior_spin.setPrefix('+')
        interior_hint = QLabel('예: 0.150 입력 시 최종 매출 ×1.15')
        interior_hint.setObjectName('CafeCaption')
        interior_panel.layout.addWidget(self.interior_spin)
        interior_panel.layout.addWidget(interior_hint)
        control_row.addWidget(interior_panel, 1)

        action_panel = self._control_panel('계산 / 프리셋')
        all_lv5 = QPushButton('전원 Lv.5')
        all_lv0 = QPushButton('전원 Lv.0')
        all_on = QPushButton('전원 ON')
        action_buttons = QHBoxLayout()
        action_buttons.setSpacing(8)
        action_buttons.addWidget(all_lv5)
        action_buttons.addWidget(all_lv0)
        action_buttons.addWidget(all_on)
        action_panel.layout.addLayout(action_buttons)
        control_row.addWidget(action_panel, 1)

        condition_right.addLayout(control_row, 1)
        bottom.addLayout(condition_right, 1)
        root.addLayout(bottom, 3)

        all_lv5.clicked.connect(partial(self.set_all_levels, 5))
        all_lv0.clicked.connect(partial(self.set_all_levels, 0))
        all_on.clicked.connect(self.set_all_on)
        self.level_spin.valueChanged.connect(self.calculate)
        self.interior_spin.valueChanged.connect(self.calculate)
        self.trend_combo.currentTextChanged.connect(self.calculate)

        self.calculate()

    def _control_panel(self, title: str) -> Card:
        panel = Card(title)
        panel.setObjectName('ConditionControlPanel')
        panel.layout.setContentsMargins(20, 16, 20, 16)
        panel.layout.setSpacing(10)
        return panel

    def set_all_levels(self, level: int):
        for widget in self.employee_widgets.values():
            widget.set_level(level)
        self.calculate()

    def set_all_on(self):
        for widget in self.employee_widgets.values():
            widget.set_active(True)
        self.calculate()

    def _employee_state(self) -> tuple[dict[str, int], dict[str, bool]]:
        levels: dict[str, int] = {}
        active: dict[str, bool] = {}
        for name, widget in self.employee_widgets.items():
            checked, level = widget.state()
            levels[name] = level
            active[name] = checked
        return levels, active

    def calculate(self, *args):
        if not hasattr(self, 'level_spin'):
            return
        levels, active = self._employee_state()
        try:
            result = self.engine.calculate(
                shop_level=self.level_spin.value(),
                trend=self.trend_combo.currentText(),
                interior_rate=self.interior_spin.value(),
                employee_levels=levels,
                employee_active=active,
            )
        except ValueError as exc:
            QMessageBox.warning(self, '계산 실패', str(exc))
            return
        self.apply_result(result)

    def apply_result(self, result: CafeResult):
        self.shop_count_label.setText(f'활성 지점: {result.shop_count}개')
        self.income_box.set_value(
            f'{result.final_total_with_interior:,.2f}',
            f'기본 {result.final_total:,.2f} 폰즈 / 시간 · 인테리어 ×{result.interior_mult:.3f}',
        )

        active_count = len(result.active_skills)
        skill_text = (
            f'유동인구: {result.traffic:,}명  ·  {result.traffic_bonus_text}\n'
            f'가격 보너스: {result.price_bonus_text}\n'
            f'활성 스킬: {active_count}개 적용'
        )
        self.skill_summary.setText(skill_text)

        inactive_requirements = ['Lv.1 이상', 'Lv.5 이상', 'Lv.10 이상', 'Lv.17 이상', 'Lv.25 이상']
        for index, card in enumerate(self.store_cards):
            if index < len(result.picks):
                card.set_pick(result.picks[index], result.trend_value)
            else:
                card.set_inactive(f'{inactive_requirements[index]} 필요')
