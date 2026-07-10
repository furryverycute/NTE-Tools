from __future__ import annotations

from functools import partial
from copy import deepcopy
from typing import Any

from PySide6.QtCore import Qt, Signal, QSize, QThread
from PySide6.QtGui import QBrush, QColor, QIcon, QPixmap, QMouseEvent, QImage
from PySide6.QtWidgets import (
    QButtonGroup,
    QComboBox,
    QDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QInputDialog,
    QMessageBox,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QScrollArea,
    QTabWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from app.loadout_data import (
    ARCS,
    ARK_RECOMMENDATIONS,
    CARTRIDGES,
    CHARACTERS,
    DRIVE_MODULES,
    DRIVE_SUB_OPTIONS,
    CARTRIDGE_MAIN_OPTIONS,
    CARTRIDGE_SUB_OPTIONS,
    DEFAULT_CARTRIDGE_ATTRIBUTES,
    DEFAULT_DRIVE_ATTRIBUTES,
    ELEMENT_LABELS,
    GEOMETRY_LABELS,
    SLOT_EFFECTS,
    aggregate_attribute_lines,
    build_final_stat_lines,
    build_promotion_progress,
    character_avatar_path,
    format_option,
    format_percent,
    geometry_cell_count,
    get_drive_main_stats,
    module_image_path,
    normalize_name,
    preferred_cartridge,
    preferred_module,
    quality_from_rarity,
    resolve_module_placement,
    roman_grid,
    slot_meta_for_character,
    slot_rows_for_character,
    trim_slot_matrix,
)


QUALITY_FILTERS = ['S급', 'A급', 'B급', '전체']
LOADOUT_SIDE_PANEL_WIDTH = 380
BAG_GRID_ITEM_SIZE = QSize(110, 108)
BAG_GRID_ICON_SIZE = QSize(44, 44)
SLOT_CELL_SIZE = 48
MODULE_QUALITY_COLORS = {
    'S급': ('#ffcf68', '#d1782a'),
    'A급': ('#c39bff', '#6b49bf'),
    'B급': ('#8cb4ff', '#355ea8'),
}


def text_cut(value: str, limit: int = 160) -> str:
    value = value or ''
    value = ' '.join(value.split())
    return value if len(value) <= limit else value[:limit - 1] + '…'


def option_lines(option_ids: list[str], quality: str, context: dict[str, Any] | None = None) -> str:
    return '\n'.join(format_option(item, quality, context) for item in option_ids if item)


def first_module_for_geometry(geometry: str, quality: str | None = None) -> dict[str, Any] | None:
    return (
        next((item for item in DRIVE_MODULES if item.get('geometry') == geometry and (not quality or item.get('quality') == quality)), None)
        or next((item for item in DRIVE_MODULES if item.get('geometry') == geometry), None)
    )


class ImageLabel(QLabel):
    def __init__(self, size: int = 56, object_name: str = 'LoadoutImage'):
        super().__init__()
        self.image_size = size
        self.setFixedSize(size, size)
        self.setAlignment(Qt.AlignCenter)
        self.setObjectName(object_name)
        self.setText('-')

    def set_path(self, path, grayscale: bool = False):
        pixmap = QPixmap(str(path)) if path else QPixmap()
        if pixmap.isNull():
            self.setPixmap(QPixmap())
            self.setText('-')
            return
        if grayscale:
            image = pixmap.toImage().convertToFormat(QImage.Format_Grayscale8)
            pixmap = QPixmap.fromImage(image)
        self.setText('')
        self.setPixmap(pixmap.scaled(
            self.image_size,
            self.image_size,
            Qt.KeepAspectRatio,
            Qt.SmoothTransformation,
        ))


class HeaderBadge(QLabel):
    def __init__(self, text: str = ''):
        super().__init__(text)
        self.setObjectName('LoadoutHeaderBadge')
        self.setAlignment(Qt.AlignCenter)
        self.setMinimumHeight(34)


class SelectorTile(QFrame):
    clicked = Signal()

    def __init__(self, title: str):
        super().__init__()
        self.title = title
        self.setObjectName('LoadoutSelectorTile')
        self.setCursor(Qt.PointingHandCursor)
        self.setFixedSize(96, 96)
        root = QVBoxLayout(self)
        root.setContentsMargins(8, 8, 8, 8)
        root.setSpacing(0)
        self.image = ImageLabel(78, 'LoadoutSelectorImage')
        root.addWidget(self.image, 0, Qt.AlignCenter)
        self.name = ''
        self.meta = ''

    def set_content(self, image_path, name: str, meta: str = ''):
        self.image.set_path(image_path)
        self.name = name or '-'
        self.meta = meta or ''
        suffix = f"\n{self.meta}" if self.meta else ''
        self.setToolTip(f"{self.title}: {self.name}{suffix}\n클릭하여 변경")

    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.LeftButton:
            self.clicked.emit()
        super().mousePressEvent(event)


class SelectionDialog(QDialog):
    _pixmap_cache: dict[str, QPixmap] = {}

    @classmethod
    def cached_pixmap(cls, image_path) -> QPixmap:
        cache_key = str(image_path) if image_path else ''
        if not cache_key:
            return QPixmap()
        pixmap = cls._pixmap_cache.get(cache_key)
        if pixmap is None:
            pixmap = QPixmap(cache_key)
            cls._pixmap_cache[cache_key] = pixmap
        return pixmap

    def __init__(
        self,
        title: str,
        items: list[dict[str, Any]],
        *,
        id_key: str = 'id',
        name_key: str = 'name',
        image_getter=None,
        meta_getter=None,
        quality_filter: bool = False,
        recommended_ids: tuple[str, ...] | list[str] = (),
        parent=None,
    ):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.resize(660, 520)
        self.selected_id = None
        self._id_key = id_key
        self._name_key = name_key
        self._items = list(items)
        self._image_getter = image_getter
        self._meta_getter = meta_getter
        self._recommended_ids = {str(item_id) for item_id in recommended_ids}
        self._quality_filter = '전체'

        root = QVBoxLayout(self)
        root.setContentsMargins(16, 16, 16, 16)
        root.setSpacing(12)
        header = QLabel(title)
        header.setObjectName('SectionTitle')
        root.addWidget(header)
        help_text = QLabel('항목을 더블클릭하거나 선택 후 확인하세요.')
        help_text.setObjectName('Muted')
        root.addWidget(help_text)

        if quality_filter:
            filters = QHBoxLayout()
            filters.setSpacing(8)
            self.quality_filter_group = QButtonGroup(self)
            self.quality_filter_group.setExclusive(True)
            for quality in ('전체', 'S급', 'A급', 'B급'):
                button = QPushButton(quality)
                button.setObjectName('LoadoutFilterButton')
                button.setCheckable(True)
                button.setChecked(quality == '전체')
                button.clicked.connect(partial(self._set_quality_filter, quality))
                self.quality_filter_group.addButton(button)
                filters.addWidget(button)
            filters.addStretch(1)
            root.addLayout(filters)

        self.list_widget = QListWidget()
        self.list_widget.setViewMode(QListWidget.IconMode)
        self.list_widget.setResizeMode(QListWidget.Adjust)
        self.list_widget.setMovement(QListWidget.Static)
        self.list_widget.setSpacing(14)
        self.list_widget.setIconSize(QSize(84, 84))
        self.list_widget.setGridSize(QSize(132, 152))
        self.list_widget.itemDoubleClicked.connect(self.accept)
        root.addWidget(self.list_widget, 1)
        self._rebuild_items()

        buttons = QHBoxLayout()
        buttons.addStretch(1)
        cancel = QPushButton('취소')
        ok = QPushButton('확인')
        ok.setObjectName('PrimaryButton')
        cancel.clicked.connect(self.reject)
        ok.clicked.connect(self.accept)
        buttons.addWidget(cancel)
        buttons.addWidget(ok)
        root.addLayout(buttons)

    def _set_quality_filter(self, quality: str):
        self._quality_filter = quality
        self._rebuild_items()

    def _rebuild_items(self):
        current_id = self.list_widget.currentItem().data(Qt.UserRole) if self.list_widget.currentItem() else None
        items = [
            item for item in self._items
            if self._quality_filter == '전체' or item.get('quality') == self._quality_filter
        ]
        items.sort(key=lambda item: (
            0 if str(item.get(self._id_key)) in self._recommended_ids else 1,
            normalize_name(item.get(self._name_key)),
        ))
        self.list_widget.clear()
        for item in items:
            item_id = item.get(self._id_key)
            is_recommended = str(item_id) in self._recommended_ids
            text = str(item.get(self._name_key, '-'))
            meta = self._meta_getter(item) if self._meta_getter else ''
            if is_recommended:
                meta = f'추천 · {meta}' if meta else '추천'
            list_item = QListWidgetItem(text + (f'\n{meta}' if meta else ''))
            list_item.setData(Qt.UserRole, item_id)
            image_path = self._image_getter(item) if self._image_getter else None
            pixmap = self.cached_pixmap(image_path)
            if not pixmap.isNull():
                list_item.setIcon(QIcon(pixmap))
            self.list_widget.addItem(list_item)
            if item_id == current_id:
                self.list_widget.setCurrentItem(list_item)

    def set_current_id(self, value):
        for i in range(self.list_widget.count()):
            item = self.list_widget.item(i)
            if item.data(Qt.UserRole) == value:
                self.list_widget.setCurrentRow(i)
                return

    def accept(self):
        item = self.list_widget.currentItem()
        self.selected_id = item.data(Qt.UserRole) if item else None
        super().accept()


class SlotCell(QFrame):
    clicked = Signal(int, int)

    def __init__(self, row: int, col: int, active: bool):
        super().__init__()
        self.row = row
        self.col = col
        self.active = active
        self.setFixedSize(SLOT_CELL_SIZE, SLOT_CELL_SIZE)
        self.setCursor(Qt.PointingHandCursor if active else Qt.ArrowCursor)
        self.setObjectName('LoadoutSlotCellActive' if active else 'LoadoutSlotCellEmpty')
        self.badge = QLabel('', self)
        self.badge.setAlignment(Qt.AlignCenter)
        self.badge.setGeometry(0, 0, SLOT_CELL_SIZE, SLOT_CELL_SIZE)
        self.badge.setStyleSheet('background: transparent; font-weight: 900; color: white;')

    def set_visual(self, style: str | None = None, label: str = ''):
        if style:
            self.setStyleSheet(style)
        else:
            self.setStyleSheet('')
        self.badge.setText(label)

    def mousePressEvent(self, event: QMouseEvent):
        if self.active and event.button() == Qt.LeftButton:
            self.clicked.emit(self.row, self.col)
        super().mousePressEvent(event)


class ModuleListItem(QFrame):
    clicked = Signal(str)

    def __init__(self, module: dict[str, Any]):
        super().__init__()
        self.module = module
        self.setObjectName('LoadoutModuleItem')
        self.setCursor(Qt.PointingHandCursor)
        root = QHBoxLayout(self)
        root.setContentsMargins(10, 10, 10, 10)
        root.setSpacing(10)
        self.icon = ImageLabel(42, 'LoadoutSmallItemImage')
        self.icon.set_path(module_image_path(module))
        root.addWidget(self.icon)
        text = QVBoxLayout()
        name = QLabel(normalize_name(module.get('name')))
        name.setObjectName('LoadoutItemName')
        name.setWordWrap(True)
        meta = QLabel(f"{module.get('quality')} · {GEOMETRY_LABELS.get(module.get('geometry'), module.get('geometry'))}")
        meta.setObjectName('Muted')
        text.addWidget(name)
        text.addWidget(meta)
        root.addLayout(text, 1)

    def set_active(self, active: bool):
        self.setProperty('active', active)
        self.style().unpolish(self)
        self.style().polish(self)

    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.LeftButton:
            self.clicked.emit(self.module['id'])
        super().mousePressEvent(event)


class DeviceBoard(QFrame):
    cell_clicked = Signal(int, int)

    def __init__(self):
        super().__init__()
        self.setObjectName('LoadoutDevice')
        self.setFixedSize(440, 530)
        self.cell_widgets: dict[tuple[int, int], SlotCell] = {}
        root = QVBoxLayout(self)
        root.setContentsMargins(16, 16, 16, 14)
        root.setSpacing(12)

        screen = QFrame()
        screen.setObjectName('LoadoutDeviceScreen')
        screen_layout = QVBoxLayout(screen)
        screen_layout.setContentsMargins(14, 14, 14, 14)
        screen_layout.setSpacing(12)

        self.message = QLabel('빈 슬롯을 클릭하면 선택한 드라이브 모듈을 배치합니다. 장착된 슬롯을 클릭하면 해제됩니다.')
        self.message.setObjectName('Muted')
        self.message.setWordWrap(True)
        screen_layout.addWidget(self.message)

        self.grid_widget = QWidget()
        self.grid = QGridLayout(self.grid_widget)
        self.grid.setContentsMargins(0, 0, 0, 0)
        self.grid.setHorizontalSpacing(5)
        self.grid.setVerticalSpacing(5)
        screen_layout.addWidget(self.grid_widget, 1, Qt.AlignCenter)
        root.addWidget(screen, 1)

        dock = QFrame()
        dock.setObjectName('LoadoutCartridgeDock')
        dock_layout = QHBoxLayout(dock)
        dock_layout.setContentsMargins(14, 12, 14, 12)
        dock_layout.setSpacing(10)
        self.core_img = ImageLabel(64, 'LoadoutCoreImage')
        dock_layout.addWidget(self.core_img)
        core_text = QVBoxLayout()
        core_text.setSpacing(6)
        self.core_name = QLabel('-')
        self.core_name.setObjectName('LoadoutStripValue')
        self.core_name.setWordWrap(True)
        core_text.addWidget(self.core_name)
        req_line = QHBoxLayout()
        req_line.setSpacing(6)
        self.core_req_title = QLabel('진급')
        self.core_req_title.setObjectName('Muted')
        req_line.addWidget(self.core_req_title)
        self.core_req_icons = QHBoxLayout()
        self.core_req_icons.setSpacing(5)
        req_line.addLayout(self.core_req_icons)
        req_line.addStretch(1)
        core_text.addLayout(req_line)
        dock_layout.addLayout(core_text, 1)
        root.addWidget(dock)

    def _clear_req_icons(self):
        while self.core_req_icons.count():
            item = self.core_req_icons.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()

    def set_core(self, cartridge: dict[str, Any] | None, progress: dict[str, Any] | None = None):
        self.core_img.set_path(module_image_path(cartridge))
        self.core_name.setText(normalize_name(cartridge.get('name')) if cartridge else '카트리지 없음')
        self._clear_req_icons()
        if not cartridge:
            self.core_req_title.setVisible(False)
            return
        self.core_req_title.setVisible(True)
        # 로컬 앱에 포함된 이미지 파일만 사용합니다. 실행 중 웹 호출은 하지 않습니다.
        set_icon = (cartridge.get('set') or {}).get('icon')
        if set_icon:
            holder = ImageLabel(26, 'PromotionReqIcon')
            holder.set_path(module_image_path({'image': set_icon}))
            holder.setToolTip('카트리지 세트')
            self.core_req_icons.addWidget(holder)
        statuses = (progress or {}).get('requirement_status') or []
        for req in statuses:
            module = first_module_for_geometry(req['geometry'], cartridge.get('quality'))
            active = bool(req.get('active'))
            holder = ImageLabel(26, 'PromotionReqIconActive' if active else 'PromotionReqIcon')
            holder.set_path(module_image_path(module), grayscale=not active)
            holder.setToolTip(('충족: ' if active else '필요: ') + GEOMETRY_LABELS.get(req['geometry'], req['geometry']))
            self.core_req_icons.addWidget(holder)

    def draw(self, character_id: str, placements: list[dict[str, Any]]):
        while self.grid.count():
            item = self.grid.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()
        self.cell_widgets.clear()
        slot_layout = trim_slot_matrix(slot_rows_for_character(character_id))
        occupied: dict[tuple[int, int], tuple[int, dict[str, Any]]] = {}
        for idx, placement in enumerate(placements, start=1):
            for cell in placement.get('cells', []):
                occupied[cell] = (idx, placement)

        rows = slot_layout['rows']
        for r, row in enumerate(rows):
            for c, value in enumerate(row):
                active = value != -1
                cell = SlotCell(r, c, active)
                if active and (r, c) in occupied:
                    idx, placement = occupied[(r, c)]
                    palette = MODULE_QUALITY_COLORS.get(placement['module'].get('quality'), MODULE_QUALITY_COLORS['B급'])
                    style = (
                        f"background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 {palette[0]}, stop:1 {palette[1]});"
                        f"border: 2px solid {palette[0]}; border-radius: 10px;"
                    )
                    cell.set_visual(style, str(idx))
                    cell.setToolTip(f"#{idx} {normalize_name(placement['module'].get('name'))}")
                elif active:
                    cell.set_visual(None, '')
                cell.clicked.connect(self.cell_clicked.emit)
                self.grid.addWidget(cell, r, c)
                self.cell_widgets[(r, c)] = cell



class InventoryScanWorker(QThread):
    progress = Signal(int, str)
    completed = Signal(dict)
    failed = Signal(str)

    def __init__(self, count: int, debug_dir):
        super().__init__()
        self.count = int(count)
        self.debug_dir = debug_dir

    def run(self):
        try:
            from app.scanner.inventory_scan import InventoryScanRunner
            runner = InventoryScanRunner(
                self.count,
                debug_dir=self.debug_dir,
                progress_callback=lambda index, message: self.progress.emit(index, message),
                # 기본은 경량 디버그 저장을 켭니다. scan_debug가 비어 있으면
                # OCR/캡처 실패 원인을 추적할 수 없기 때문입니다.
                save_debug=True,
                progress_interval=5,
            )
            result = runner.run()
            self.completed.emit(result)
        except Exception as exc:
            self.failed.emit(str(exc))


class LoadoutPage(QWidget):
    scan_status_changed = Signal(str)

    def __init__(self):
        super().__init__()
        self.characters_by_id = {str(item['id']): item for item in CHARACTERS}
        self.arks_by_id = {item['id']: item for item in ARCS}
        self.cartridges_by_id = {item['id']: item for item in CARTRIDGES}
        self.modules_by_id = {item['id']: item for item in DRIVE_MODULES}

        self.current_character_id = str(CHARACTERS[0]['id'])
        self.current_ark_id = ARCS[0]['id'] if ARCS else ''
        self.current_cartridge_id = preferred_cartridge(CHARACTERS[0])['id'] if preferred_cartridge(CHARACTERS[0]) else ''
        owner_count = slot_meta_for_character(self.current_character_id).get('owner_grid_count', 3)
        self.current_module_id = preferred_module(owner_count)['id'] if preferred_module(owner_count) else ''
        self.module_quality_filter = 'S급'
        self.placements: list[dict[str, Any]] = []
        self.placement_counter = 0
        self.cartridge_attr_selections: dict[str, dict[str, Any]] = {}
        self.drive_attr_selections: dict[str, dict[str, Any]] = {}
        self.module_items: dict[str, ModuleListItem] = {}
        self._refreshing = False
        # 가방은 실제 스캔 결과만 표시합니다. 샘플 장비를 넣어두면
        # 스캔 결과 유입 여부를 확인하기 어려우므로 빈 상태로 시작합니다.
        self.cartridge_bag_items = []
        self.drive_bag_items = []
        self.current_cartridge_bag_id = ''
        self.current_drive_bag_id = ''
        self.character_loadouts: dict[str, dict[str, Any]] = {}
        self.inventory_usage: dict[str, dict[str, Any]] = {}
        self._preload_picker_images()

        root = QVBoxLayout(self)
        root.setContentsMargins(18, 14, 18, 14)
        root.setSpacing(10)
        root.addWidget(self._build_top_strip())

        body = QHBoxLayout()
        body.setSpacing(16)
        body.setAlignment(Qt.AlignTop)
        body.addWidget(self._build_left_panel())
        body.addLayout(self._build_center_panel(), 1)
        body.addWidget(self._build_right_panel())
        root.addLayout(body, 1)
        self.refresh_all()

    def _preload_picker_images(self):
        for character in CHARACTERS:
            SelectionDialog.cached_pixmap(character_avatar_path(character))
        for ark in ARCS:
            SelectionDialog.cached_pixmap(module_image_path(ark, prefer_icon=True))
        for cartridge in CARTRIDGES:
            SelectionDialog.cached_pixmap(module_image_path(cartridge))

    # ------------------------------------------------------------------ UI build
    def _build_top_strip(self) -> QFrame:
        frame = QFrame()
        frame.setObjectName('LoadoutTopStrip')
        layout = QHBoxLayout(frame)
        layout.setContentsMargins(14, 10, 14, 10)
        layout.setSpacing(14)

        self.character_tile = SelectorTile('캐릭터')
        self.ark_tile = SelectorTile('아크')
        self.character_tile.clicked.connect(self.open_character_picker)
        self.ark_tile.clicked.connect(self.open_ark_picker)
        layout.addWidget(self.character_tile)
        layout.addWidget(self.ark_tile)

        ark_effect_box = QFrame()
        ark_effect_box.setObjectName('LoadoutTopEffectBox')
        ark_effect_box.setMinimumWidth(320)
        ark_effect_box.setMaximumWidth(420)
        effect_layout = QVBoxLayout(ark_effect_box)
        effect_layout.setContentsMargins(12, 10, 12, 10)
        effect_layout.setSpacing(2)
        effect_title = QLabel('아크 효과')
        effect_title.setObjectName('LoadoutOptionGroupTitle')
        self.top_ark_effect = QLabel('-')
        self.top_ark_effect.setObjectName('Muted')
        self.top_ark_effect.setWordWrap(True)
        self.top_ark_effect.setAlignment(Qt.AlignTop | Qt.AlignLeft)
        effect_layout.addWidget(effect_title)
        effect_layout.addWidget(self.top_ark_effect, 1)
        layout.addWidget(ark_effect_box, 1)

        self.special_top_box = QFrame()
        self.special_top_box.setObjectName('LoadoutSpecialTopBox')
        special_layout = QVBoxLayout(self.special_top_box)
        special_layout.setContentsMargins(14, 10, 14, 10)
        special_layout.setSpacing(4)
        self.special_top_title = QLabel('Ⅱ형 특화')
        self.special_top_title.setObjectName('LoadoutOptionGroupTitle')
        self.special_top_desc = QLabel('-')
        self.special_top_desc.setObjectName('Muted')
        self.special_top_desc.setWordWrap(False)
        self.special_top_total = QLabel('-')
        self.special_top_total.setObjectName('LoadoutSpecialTopTotal')
        special_layout.addWidget(self.special_top_title)
        special_layout.addWidget(self.special_top_desc)
        special_layout.addWidget(self.special_top_total)
        layout.addWidget(self.special_top_box, 2)
        layout.addWidget(self._build_scan_panel(compact=True), 1)
        return frame

    def _build_scan_panel(self, compact: bool = False) -> QFrame:
        scan_panel = QFrame()
        scan_panel.setObjectName('LoadoutScannerPanel')
        scan_panel.setMinimumWidth(310)
        scan_panel.setMaximumWidth(380)
        scan_root = QVBoxLayout(scan_panel)
        scan_root.setContentsMargins(12, 10, 12, 10)
        scan_root.setSpacing(8)
        scan_title = QLabel('가방 스캔 / 추천')
        scan_title.setObjectName('SectionTitle')
        scan_root.addWidget(scan_title)
        scan_buttons = QHBoxLayout()
        scan_buttons.setSpacing(6)
        self.auto_scan_btn = QPushButton('가방 자동 스캔')
        self.auto_scan_btn.setObjectName('PrimaryButton')
        self.auto_scan_btn.clicked.connect(self.open_scan_dialog)
        self.recommend_btn = QPushButton('추천 장착')
        self.recommend_btn.clicked.connect(self.apply_recommended_loadout)
        self.final_stats_btn = QPushButton('최종 스펙')
        self.final_stats_btn.clicked.connect(self.open_final_stats_dialog)
        scan_buttons.addWidget(self.auto_scan_btn)
        scan_buttons.addWidget(self.recommend_btn)
        scan_buttons.addWidget(self.final_stats_btn)
        scan_root.addLayout(scan_buttons)
        self.scan_status_label = QLabel('스캔 저장: 카트리지 {0}개 / 드라이브 {1}개'.format(len(self.cartridge_bag_items), len(self.drive_bag_items)))
        self.scan_status_label.setObjectName('Muted')
        self.scan_status_label.setWordWrap(True)
        scan_root.addWidget(self.scan_status_label)
        return scan_panel

    def _build_left_panel(self) -> QWidget:
        panel = QWidget()
        panel.setObjectName('TransparentPanel')
        panel.setFixedWidth(LOADOUT_SIDE_PANEL_WIDTH)
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.cartridge_card = QFrame()
        self.cartridge_card.setObjectName('LoadoutSubPanel')
        self.cartridge_card.setFixedWidth(LOADOUT_SIDE_PANEL_WIDTH)
        p_root = QVBoxLayout(self.cartridge_card)
        p_root.setContentsMargins(12, 12, 12, 12)
        p_root.setSpacing(8)
        head = QHBoxLayout()
        p_title = QLabel('카트리지 설정')
        p_title.setObjectName('SectionTitle')
        self.promotion_count_label = QLabel('-')
        self.promotion_count_label.setObjectName('LoadoutMiniBadge')
        head.addWidget(p_title, 1)
        head.addWidget(self.promotion_count_label)
        p_root.addLayout(head)
        self.cartridge_select_btn = QPushButton('카트리지 선택')
        self.cartridge_select_btn.setObjectName('LoadoutPlacementButton')
        self.cartridge_select_btn.clicked.connect(self.open_cartridge_picker)
        p_root.addWidget(self.cartridge_select_btn)
        self.cartridge_tabs = QTabWidget()
        self.cartridge_tabs.setObjectName('LoadoutTabs')
        p_root.addWidget(self.cartridge_tabs, 1)
        self.cartridge_tabs.addTab(self._build_cartridge_custom_tab(), '커스텀')
        self.cartridge_tabs.addTab(self._build_cartridge_bag_tab(), '가방')
        self.promotion_effects = QLabel('-')
        self.promotion_effects.setObjectName('Muted')
        self.promotion_effects.setWordWrap(True)
        p_root.addWidget(self.promotion_effects)
        layout.addWidget(self.cartridge_card, 1)
        return panel

    def _build_cartridge_custom_tab(self) -> QWidget:
        page = QWidget()
        page.setObjectName('TransparentPanel')
        root = QVBoxLayout(page)
        root.setContentsMargins(0, 6, 0, 0)
        root.setSpacing(10)

        main_group = QFrame()
        main_group.setObjectName('LoadoutOptionGroupPrimary')
        main_layout = QVBoxLayout(main_group)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(6)
        main_title = QLabel('주옵션 1개')
        main_title.setObjectName('LoadoutOptionGroupTitle')
        main_layout.addWidget(main_title)
        self.cartridge_main_combo = QComboBox()
        self.cartridge_main_combo.currentIndexChanged.connect(self.on_cartridge_main_changed)
        main_layout.addWidget(self.cartridge_main_combo)
        root.addWidget(main_group)

        sub_group = QFrame()
        sub_group.setObjectName('LoadoutOptionGroupSecondary')
        sub_layout = QVBoxLayout(sub_group)
        sub_layout.setContentsMargins(10, 10, 10, 10)
        sub_layout.setSpacing(7)
        sub_head = QHBoxLayout()
        sub_title = QLabel('부옵션 4개')
        sub_title.setObjectName('LoadoutOptionGroupTitle')
        sub_help = QLabel('카트리지는 부옵션을 4개만 설정합니다.')
        sub_help.setObjectName('Muted')
        sub_head.addWidget(sub_title)
        sub_head.addStretch(1)
        sub_head.addWidget(sub_help)
        sub_layout.addLayout(sub_head)
        self.cartridge_sub_combos: list[QComboBox] = []
        for i in range(4):
            row = QHBoxLayout()
            label = QLabel(f'부옵션 {i + 1}')
            label.setObjectName('LoadoutOptionIndex')
            combo = QComboBox()
            combo.currentIndexChanged.connect(partial(self.on_cartridge_sub_changed, i))
            self.cartridge_sub_combos.append(combo)
            row.addWidget(label)
            row.addWidget(combo, 1)
            sub_layout.addLayout(row)
        root.addWidget(sub_group)

        req_holder = QWidget()
        req_holder.setVisible(False)
        self.req_row = QHBoxLayout(req_holder)
        self.req_row.setContentsMargins(0, 0, 0, 0)
        self.req_row.setSpacing(8)
        root.addWidget(req_holder)
        root.addStretch(1)
        return page

    def _build_cartridge_bag_tab(self) -> QWidget:
        page = QWidget()
        page.setObjectName('TransparentPanel')
        root = QVBoxLayout(page)
        root.setContentsMargins(0, 6, 0, 0)
        root.setSpacing(8)

        self.cartridge_bag_quality = QComboBox()
        self.cartridge_bag_quality.addItems(['전체', 'S급', 'A급', 'B급'])
        self.cartridge_bag_quality.currentIndexChanged.connect(self.rebuild_cartridge_bag_list)
        root.addWidget(self.cartridge_bag_quality)

        self.cartridge_bag_main = QComboBox()
        self.cartridge_bag_main.addItem('주옵 전체', '')
        for item in CARTRIDGE_MAIN_OPTIONS:
            self.cartridge_bag_main.addItem(format_option(item['id'], 'S급'), item['id'])
        self.cartridge_bag_main.currentIndexChanged.connect(self.rebuild_cartridge_bag_list)
        root.addWidget(self.cartridge_bag_main)

        sub_title = QLabel('부옵션 필터 최대 4개')
        sub_title.setObjectName('LoadoutOptionGroupTitle')
        root.addWidget(sub_title)
        self.cartridge_bag_sub_filters: list[QComboBox] = []
        for i in range(4):
            combo = QComboBox()
            combo.addItem(f'부옵 {i + 1} 전체', '')
            for item in CARTRIDGE_SUB_OPTIONS:
                combo.addItem(format_option(item['id'], 'S급', {'kind': 'cartridge_sub'}), item['id'])
            combo.currentIndexChanged.connect(self.rebuild_cartridge_bag_list)
            self.cartridge_bag_sub_filters.append(combo)
            root.addWidget(combo)

        match_row = QHBoxLayout()
        self.cartridge_match_group = QButtonGroup(self)
        self.cartridge_match_group.setExclusive(True)
        for count, label in [(0, '전체'), (1, '1개 일치'), (2, '2개'), (3, '3개'), (4, '4개')]:
            btn = QPushButton(label)
            btn.setObjectName('LoadoutFilterButton')
            btn.setCheckable(True)
            btn.setProperty('match_count', count)
            if count == 0:
                btn.setChecked(True)
            self.cartridge_match_group.addButton(btn)
            btn.clicked.connect(self.rebuild_cartridge_bag_list)
            match_row.addWidget(btn)
        root.addLayout(match_row)

        self.cartridge_bag_list = QListWidget()
        self.cartridge_bag_list.setFixedWidth(LOADOUT_SIDE_PANEL_WIDTH - 42)
        self.configure_bag_grid(self.cartridge_bag_list)
        self.cartridge_bag_list.itemClicked.connect(self.on_cartridge_bag_selected)
        root.addWidget(self.cartridge_bag_list, 1)
        return page

    def _build_center_panel(self) -> QVBoxLayout:
        center = QVBoxLayout()
        center.setSpacing(10)
        self.device = DeviceBoard()
        self.device.cell_clicked.connect(self.on_slot_clicked)
        center.addWidget(self.device, 0, Qt.AlignHCenter | Qt.AlignTop)

        placement_bar = QFrame()
        placement_bar.setObjectName('LoadoutPlacementBar')
        placement_bar.setFixedHeight(56)
        bar_layout = QHBoxLayout(placement_bar)
        bar_layout.setContentsMargins(14, 10, 14, 10)
        bar_layout.setSpacing(10)
        self.placement_message = QLabel('준비 완료')
        self.placement_message.setObjectName('Muted')
        self.placement_message.setWordWrap(True)
        self.placed_modules_button = QPushButton('장착 모듈 0개 보기')
        self.placed_modules_button.setObjectName('LoadoutPlacementButton')
        self.placed_modules_button.clicked.connect(self.open_placed_modules_dialog)
        bar_layout.addWidget(self.placement_message, 1)
        bar_layout.addWidget(self.placed_modules_button)
        center.addWidget(placement_bar)
        center.addStretch(1)
        return center

    def _build_right_panel(self) -> QWidget:
        panel = QWidget()
        panel.setObjectName('TransparentPanel')
        panel.setFixedWidth(LOADOUT_SIDE_PANEL_WIDTH)
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        picker = QFrame()
        picker.setObjectName('LoadoutPicker')
        picker.setFixedWidth(LOADOUT_SIDE_PANEL_WIDTH)
        p_root = QVBoxLayout(picker)
        p_root.setContentsMargins(12, 12, 12, 12)
        p_root.setSpacing(8)
        top = QHBoxLayout()
        title = QLabel('드라이브 모듈')
        title.setObjectName('SectionTitle')
        top.addWidget(title)
        top.addStretch(1)
        self.module_count_label = QLabel('-')
        self.module_count_label.setObjectName('LoadoutMiniBadge')
        top.addWidget(self.module_count_label)
        p_root.addLayout(top)

        self.module_tabs = QTabWidget()
        self.module_tabs.setObjectName('LoadoutTabs')
        p_root.addWidget(self.module_tabs, 1)
        self.module_tabs.addTab(self._build_module_custom_tab(), '커스텀')
        self.module_tabs.addTab(self._build_module_bag_tab(), '가방')
        layout.addWidget(picker, 1)

        # 하단 계산 결과 요약 패널은 최종 스펙 플로팅 창으로 대체합니다.
        self.summary_rows: dict[str, QLabel] = {}
        self.attribute_summary = None
        return panel

    def _build_module_custom_tab(self) -> QWidget:
        page = QWidget()
        page.setObjectName('TransparentPanel')
        root = QVBoxLayout(page)
        root.setContentsMargins(0, 6, 0, 0)
        root.setSpacing(10)
        filter_row = QHBoxLayout()
        self.filter_group = QButtonGroup(self)
        self.filter_group.setExclusive(True)
        for label in QUALITY_FILTERS:
            btn = QPushButton(label)
            btn.setObjectName('LoadoutFilterButton')
            btn.setCheckable(True)
            if label == self.module_quality_filter:
                btn.setChecked(True)
            self.filter_group.addButton(btn)
            filter_row.addWidget(btn)
            btn.clicked.connect(partial(self.on_filter_changed, label))
        root.addLayout(filter_row)

        main_group = QFrame()
        main_group.setObjectName('LoadoutOptionGroupPrimary')
        main_layout = QVBoxLayout(main_group)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(6)
        main_title = QLabel('고정 주옵션')
        main_title.setObjectName('LoadoutOptionGroupTitle')
        main_layout.addWidget(main_title)
        self.drive_fixed_main = QLabel('-')
        self.drive_fixed_main.setObjectName('LoadoutMainOptionValue')
        self.drive_fixed_main.setWordWrap(True)
        main_layout.addWidget(self.drive_fixed_main)
        root.addWidget(main_group)

        sub_group = QFrame()
        sub_group.setObjectName('LoadoutOptionGroupSecondary')
        sub_layout = QVBoxLayout(sub_group)
        sub_layout.setContentsMargins(10, 10, 10, 10)
        sub_layout.setSpacing(7)
        sub_title = QLabel('커스텀 부옵션 4개')
        sub_title.setObjectName('LoadoutOptionGroupTitle')
        sub_layout.addWidget(sub_title)
        self.drive_sub_combos: list[QComboBox] = []
        for i in range(4):
            row = QHBoxLayout()
            label = QLabel(f'부옵션 {i + 1}')
            label.setObjectName('LoadoutOptionIndex')
            combo = QComboBox()
            combo.currentIndexChanged.connect(partial(self.on_drive_sub_changed, i))
            self.drive_sub_combos.append(combo)
            row.addWidget(label)
            row.addWidget(combo, 1)
            sub_layout.addLayout(row)
        root.addWidget(sub_group)

        self.module_scroll = QScrollArea()
        self.module_scroll.setObjectName('LoadoutModuleScroll')
        self.module_scroll.setFrameShape(QFrame.NoFrame)
        self.module_scroll.setStyleSheet(
            'QScrollArea#LoadoutModuleScroll { background: #151d2f; border: none; }'
            'QScrollArea#LoadoutModuleScroll > QWidget { background: #151d2f; }'
        )
        self.module_scroll.setWidgetResizable(True)
        self.module_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.module_scroll.setMinimumHeight(220)
        self.module_scroll.viewport().setObjectName('LoadoutModuleScrollViewport')
        self.module_content = QWidget()
        self.module_content.setObjectName('TransparentPanel')
        self.module_layout = QVBoxLayout(self.module_content)
        self.module_layout.setContentsMargins(0, 0, 0, 0)
        self.module_layout.setSpacing(8)
        self.module_scroll.setWidget(self.module_content)
        root.addWidget(self.module_scroll, 1)
        return page

    def _build_module_bag_tab(self) -> QWidget:
        page = QWidget()
        page.setObjectName('TransparentPanel')
        root = QVBoxLayout(page)
        root.setContentsMargins(0, 6, 0, 0)
        root.setSpacing(8)
        self.drive_bag_quality = QComboBox()
        self.drive_bag_quality.addItems(['전체', 'S급', 'A급', 'B급'])
        self.drive_bag_quality.currentIndexChanged.connect(self.rebuild_drive_bag_list)
        self.drive_bag_geometry = QComboBox()
        self.drive_bag_geometry.addItem('모양 전체', '')
        for key, label in GEOMETRY_LABELS.items():
            if key != 'Core':
                self.drive_bag_geometry.addItem(label, key)
        self.drive_bag_geometry.currentIndexChanged.connect(self.rebuild_drive_bag_list)
        self.drive_bag_main = QComboBox()
        self.drive_bag_main.addItem('주옵 전체', '')
        for opt in ['AtkAdd', 'HPMaxAdd']:
            self.drive_bag_main.addItem(format_option(opt, 'S급', {'kind': 'drive_main', 'grid_count': 2}), opt)
        self.drive_bag_main.currentIndexChanged.connect(self.rebuild_drive_bag_list)
        self.drive_bag_sub = QComboBox()
        self.drive_bag_sub.addItem('부옵 전체', '')
        for item in DRIVE_SUB_OPTIONS:
            self.drive_bag_sub.addItem(format_option(item['id'], 'S급', {'kind': 'drive_sub', 'grid_count': 2}), item['id'])
        self.drive_bag_sub.currentIndexChanged.connect(self.rebuild_drive_bag_list)
        for widget in (self.drive_bag_quality, self.drive_bag_geometry, self.drive_bag_main, self.drive_bag_sub):
            root.addWidget(widget)
        self.drive_bag_list = QListWidget()
        self.drive_bag_list.setFixedWidth(LOADOUT_SIDE_PANEL_WIDTH - 42)
        self.configure_bag_grid(self.drive_bag_list)
        self.drive_bag_list.itemClicked.connect(self.on_drive_bag_selected)
        root.addWidget(self.drive_bag_list, 1)
        return page

    def configure_bag_grid(self, widget: QListWidget):
        widget.setViewMode(QListWidget.IconMode)
        widget.setResizeMode(QListWidget.Adjust)
        widget.setMovement(QListWidget.Static)
        widget.setWrapping(True)
        widget.setUniformItemSizes(True)
        widget.setIconSize(BAG_GRID_ICON_SIZE)
        widget.setGridSize(BAG_GRID_ITEM_SIZE)
        widget.setSpacing(0)
        widget.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        widget.setObjectName('LoadoutBagGrid')
        widget.viewport().setObjectName('LoadoutBagGridViewport')
        widget.setWordWrap(True)

    # ------------------------------------------------------------------ data helpers
    def _build_cartridge_bag_items(self) -> list[dict[str, Any]]:
        items = []
        main_ids = [it['id'] for it in CARTRIDGE_MAIN_OPTIONS] or [DEFAULT_CARTRIDGE_ATTRIBUTES['main']]
        sub_ids = [it['id'] for it in CARTRIDGE_SUB_OPTIONS] or list(DEFAULT_CARTRIDGE_ATTRIBUTES['subs'])
        for idx, base in enumerate(CARTRIDGES):
            items.append({
                'bag_id': f'cartridge-{idx}',
                'base_id': base['id'],
                'quality': base.get('quality', 'S급'),
                'main': main_ids[idx % len(main_ids)],
                'subs': [sub_ids[(idx + j) % len(sub_ids)] for j in range(4)],
                'order': idx,
            })
        return items

    def _build_drive_bag_items(self) -> list[dict[str, Any]]:
        items = []
        sub_ids = [it['id'] for it in DRIVE_SUB_OPTIONS] or list(DEFAULT_DRIVE_ATTRIBUTES['subs'])
        for idx, base in enumerate(DRIVE_MODULES):
            grid_count = geometry_cell_count(base.get('geometry'))
            mains = [stat['id'] for stat in get_drive_main_stats(base, grid_count)]
            items.append({
                'bag_id': f'drive-{idx}',
                'base_id': base['id'],
                'quality': base.get('quality', 'S급'),
                'geometry': base.get('geometry'),
                'mains': mains,
                'subs': [sub_ids[(idx + j) % len(sub_ids)] for j in range(4)],
                'order': idx,
            })
        return items

    # ------------------------------------------------------------------ helpers
    def character(self) -> dict[str, Any]:
        return self.characters_by_id.get(str(self.current_character_id), CHARACTERS[0])

    def ark(self) -> dict[str, Any] | None:
        return self.arks_by_id.get(self.current_ark_id)

    def cartridge(self) -> dict[str, Any] | None:
        return self.cartridges_by_id.get(self.current_cartridge_id)

    def module(self) -> dict[str, Any] | None:
        return self.modules_by_id.get(self.current_module_id)

    def cartridge_attrs(self) -> dict[str, Any]:
        return self.cartridge_attr_selections.get(self.current_cartridge_id, DEFAULT_CARTRIDGE_ATTRIBUTES.copy())

    def drive_attrs(self) -> dict[str, Any]:
        return self.drive_attr_selections.get(self.current_module_id, DEFAULT_DRIVE_ATTRIBUTES.copy())

    def character_name(self, character_id: str | int | None = None) -> str:
        cid = str(character_id or self.current_character_id)
        return self.characters_by_id.get(cid, {}).get('name', cid)

    def cartridge_bag_entry(self, bag_id: str | None) -> dict[str, Any] | None:
        return next((it for it in self.cartridge_bag_items if it.get('bag_id') == bag_id), None)

    def drive_bag_entry(self, bag_id: str | None) -> dict[str, Any] | None:
        return next((it for it in self.drive_bag_items if it.get('bag_id') == bag_id), None)

    def save_character_loadout(self, character_id: str | None = None):
        cid = str(character_id or self.current_character_id)
        self.character_loadouts[cid] = {
            'ark_id': self.current_ark_id,
            'cartridge_id': self.current_cartridge_id,
            'cartridge_bag_id': self.current_cartridge_bag_id,
            'drive_bag_id': self.current_drive_bag_id,
            'placements': deepcopy(self.placements),
            'cartridge_attrs': deepcopy(self.cartridge_attr_selections),
            'drive_attrs': deepcopy(self.drive_attr_selections),
        }

    def load_character_loadout(self, character_id: str):
        state = self.character_loadouts.get(str(character_id))
        if state:
            self.current_ark_id = state.get('ark_id') or (ARCS[0]['id'] if ARCS else '')
            self.current_cartridge_id = state.get('cartridge_id') or self.current_cartridge_id
            self.current_cartridge_bag_id = state.get('cartridge_bag_id', '')
            self.current_drive_bag_id = state.get('drive_bag_id', '')
            self.placements = deepcopy(state.get('placements', []))
            self.cartridge_attr_selections = deepcopy(state.get('cartridge_attrs', {}))
            self.drive_attr_selections = deepcopy(state.get('drive_attrs', {}))
        else:
            preferred = preferred_cartridge(self.character())
            self.current_cartridge_id = preferred['id'] if preferred else self.current_cartridge_id
            self.current_cartridge_bag_id = ''
            self.current_drive_bag_id = ''
            self.placements = []
            owner_count = slot_meta_for_character(self.current_character_id).get('owner_grid_count', 3)
            module = preferred_module(owner_count, self.module_quality_filter if self.module_quality_filter != '전체' else 'S급')
            if module:
                self.current_module_id = module['id']
        self.placement_counter = max(self.placement_counter, len(self.placements) + 1)

    def rebuild_inventory_usage(self):
        usage: dict[str, dict[str, Any]] = {}

        def mark(bag_id: str | None, kind: str, cid: str, placement_id: str = ''):
            if not bag_id:
                return
            usage[str(bag_id)] = {
                'kind': kind,
                'character_id': str(cid),
                'character_name': self.character_name(cid),
                'placement_id': placement_id,
            }

        for cid, state in self.character_loadouts.items():
            if str(cid) == str(self.current_character_id):
                continue
            mark(state.get('cartridge_bag_id'), 'cartridge', cid)
            for placement in state.get('placements', []):
                mark(placement.get('bag_id'), 'drive', cid, placement.get('id', ''))
        mark(self.current_cartridge_bag_id, 'cartridge', self.current_character_id)
        for placement in self.placements:
            mark(placement.get('bag_id'), 'drive', self.current_character_id, placement.get('id', ''))
        self.inventory_usage = usage

    def usage_for(self, bag_id: str | None) -> dict[str, Any] | None:
        if not bag_id:
            return None
        return self.inventory_usage.get(str(bag_id))

    def remove_bag_assignment(self, bag_id: str):
        if not bag_id:
            return
        if self.current_cartridge_bag_id == bag_id:
            self.current_cartridge_bag_id = ''
        self.placements = [item for item in self.placements if item.get('bag_id') != bag_id]
        for state in self.character_loadouts.values():
            if state.get('cartridge_bag_id') == bag_id:
                state['cartridge_bag_id'] = ''
            state['placements'] = [item for item in state.get('placements', []) if item.get('bag_id') != bag_id]
        self.rebuild_inventory_usage()

    def confirm_reassign_item(self, usage: dict[str, Any], item_label: str) -> bool:
        owner = usage.get('character_name') or usage.get('character_id') or '-'
        message = (
            f"이미 {owner}에게 장착된 {item_label}입니다.\n"
            f"이쪽에 다시 장착하면 기존 장착 위치에서는 해제됩니다.\n\n"
            f"다시 장착하시겠습니까?"
        )
        return QMessageBox.question(
            self,
            '중복 장착 확인',
            message,
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        ) == QMessageBox.Yes

    def sort_inventory_items(self, items: list[dict[str, Any]]) -> list[dict[str, Any]]:
        return sorted(items, key=lambda it: (1 if self.usage_for(it.get('bag_id')) else 0, int(it.get('order', 999999))))


    def occupied_slots(self) -> dict[tuple[int, int], str]:
        occupied: dict[tuple[int, int], str] = {}
        for placement in self.placements:
            for cell in placement.get('cells', []):
                occupied[cell] = placement['id']
        return occupied

    def occupied_placement_at(self, row: int, col: int) -> dict[str, Any] | None:
        placement_id = self.occupied_slots().get((row, col))
        if not placement_id:
            return None
        return next((it for it in self.placements if it['id'] == placement_id), None)

    def sync_combo(self, combo: QComboBox, value: str):
        index = combo.findData(value)
        if index >= 0 and combo.currentIndex() != index:
            combo.blockSignals(True)
            combo.setCurrentIndex(index)
            combo.blockSignals(False)

    def set_message(self, text: str):
        self.placement_message.setText(text)
        self.device.message.setText(text)

    def fill_option_combo(self, combo: QComboBox, options: list[dict[str, Any]], quality: str, selected_id: str, context: dict[str, Any] | None = None):
        combo.blockSignals(True)
        combo.clear()
        for option in options:
            option_id = option['id']
            combo.addItem(format_option(option_id, quality, context), option_id)
        index = combo.findData(selected_id)
        combo.setCurrentIndex(max(0, index))
        combo.blockSignals(False)

    # ------------------------------------------------------------------ selection popups
    def open_character_picker(self):
        dialog = SelectionDialog(
            '캐릭터 선택',
            CHARACTERS,
            id_key='id',
            name_key='name',
            image_getter=character_avatar_path,
            meta_getter=lambda item: ELEMENT_LABELS.get(item.get('element') or item.get('elementId'), '-'),
            parent=self,
        )
        dialog.set_current_id(int(self.current_character_id) if str(self.current_character_id).isdigit() else self.current_character_id)
        if dialog.exec() == QDialog.Accepted and dialog.selected_id is not None:
            next_id = str(dialog.selected_id)
            if next_id != self.current_character_id:
                old_id = self.current_character_id
                self.save_character_loadout(old_id)
                self.current_character_id = next_id
                self.load_character_loadout(next_id)
                self.set_message('캐릭터 변경: 저장된 장착 상태를 불러왔습니다.')
                self.refresh_all()

    def open_ark_picker(self):
        recommended_ids = ARK_RECOMMENDATIONS.get(self.character().get('name', ''), ())
        dialog = SelectionDialog(
            '아크 선택',
            ARCS,
            image_getter=lambda item: module_image_path(item, prefer_icon=True),
            meta_getter=lambda item: item.get('quality', ''),
            quality_filter=True,
            recommended_ids=recommended_ids,
            parent=self,
        )
        dialog.set_current_id(self.current_ark_id)
        if dialog.exec() == QDialog.Accepted and dialog.selected_id is not None:
            self.current_ark_id = dialog.selected_id
            self.refresh_all()

    def open_cartridge_picker(self):
        dialog = SelectionDialog(
            '카트리지 선택',
            CARTRIDGES,
            image_getter=module_image_path,
            meta_getter=lambda item: item.get('quality', ''),
            quality_filter=True,
            parent=self,
        )
        dialog.set_current_id(self.current_cartridge_id)
        if dialog.exec() == QDialog.Accepted and dialog.selected_id is not None:
            next_id = dialog.selected_id
            if next_id != self.current_cartridge_id:
                self.current_cartridge_id = next_id
                self.current_cartridge_bag_id = ''
                self.set_message('카트리지 변경: 설정 패널에서 선택한 카트리지를 적용했습니다.')
                self.refresh_all()

    # ------------------------------------------------------------------ events
    def on_character_changed(self):
        if self._refreshing:
            return
        self.load_character_loadout(self.current_character_id)
        self.set_message('캐릭터 변경: 저장된 장착 상태를 불러왔습니다.')
        self.refresh_all()

    def on_cartridge_main_changed(self):
        if self._refreshing or not self.current_cartridge_id:
            return
        attrs = self.cartridge_attrs().copy()
        attrs['main'] = self.cartridge_main_combo.currentData()
        self.cartridge_attr_selections[self.current_cartridge_id] = attrs
        self.refresh_all()

    def on_cartridge_sub_changed(self, index: int):
        if self._refreshing or not self.current_cartridge_id:
            return
        attrs = self.cartridge_attrs().copy()
        subs = list(attrs.get('subs', DEFAULT_CARTRIDGE_ATTRIBUTES['subs']))
        while len(subs) < 4:
            subs.append(DEFAULT_CARTRIDGE_ATTRIBUTES['subs'][len(subs)])
        subs[index] = self.cartridge_sub_combos[index].currentData()
        attrs['subs'] = subs
        self.cartridge_attr_selections[self.current_cartridge_id] = attrs
        self.refresh_all()

    def on_drive_sub_changed(self, index: int):
        if self._refreshing or not self.current_module_id:
            return
        attrs = self.drive_attrs().copy()
        subs = list(attrs.get('subs', DEFAULT_DRIVE_ATTRIBUTES['subs']))
        while len(subs) < 4:
            subs.append(DEFAULT_DRIVE_ATTRIBUTES['subs'][len(subs)])
        subs[index] = self.drive_sub_combos[index].currentData()
        attrs['subs'] = subs
        self.drive_attr_selections[self.current_module_id] = attrs
        self.refresh_all()

    def on_filter_changed(self, label: str):
        self.module_quality_filter = label
        modules = self.filtered_modules()
        if modules and self.current_module_id not in {item['id'] for item in modules}:
            self.current_module_id = modules[0]['id']
        self.refresh_all()

    def on_module_selected(self, module_id: str):
        self.current_module_id = module_id
        self.current_drive_bag_id = ''
        module = self.module()
        if module:
            self.set_message(f"{GEOMETRY_LABELS.get(module.get('geometry'), module.get('geometry'))} 선택")
        self.refresh_all()

    def on_slot_clicked(self, row: int, col: int):
        occupied = self.occupied_placement_at(row, col)
        if occupied:
            self.placements = [item for item in self.placements if item['id'] != occupied['id']]
            self.set_message('모듈 해제')
            self.refresh_all()
            return
        module = self.module()
        drive_entry = self.drive_bag_entry(self.current_drive_bag_id) if self.current_drive_bag_id else None
        if drive_entry:
            module = self.modules_by_id.get(drive_entry['base_id']) or module
        if not module:
            self.set_message('선택된 드라이브 모듈이 없습니다.')
            return
        if drive_entry:
            usage = self.usage_for(drive_entry['bag_id'])
            if usage:
                if not self.confirm_reassign_item(usage, '드라이브 모듈'):
                    self.set_message('중복 장착 취소')
                    return
                self.remove_bag_assignment(drive_entry['bag_id'])
        slot_layout = trim_slot_matrix(slot_rows_for_character(self.current_character_id))
        placement = resolve_module_placement(module.get('geometry'), (row, col), slot_layout, self.occupied_slots())
        if not placement.get('is_valid'):
            self.set_message('배치 불가')
            return
        grid_count = geometry_cell_count(module.get('geometry'))
        subs = list(self.drive_attrs().get('subs', DEFAULT_DRIVE_ATTRIBUTES['subs']))
        bag_id = ''
        bag_entry = None
        if drive_entry:
            bag_id = drive_entry['bag_id']
            bag_entry = deepcopy(drive_entry)
            subs = list(drive_entry.get('subs') or DEFAULT_DRIVE_ATTRIBUTES['subs'])[:4]
        self.placement_counter += 1
        self.placements.append({
            'id': f"{module['id']}-{self.placement_counter}",
            'module': module,
            'bag_id': bag_id,
            'bag_entry': bag_entry,
            'character_id': self.current_character_id,
            'origin': placement.get('origin'),
            'cells': placement.get('cells', []),
            'attributes': {
                'main': get_drive_main_stats(module, grid_count),
                'subs': subs,
            },
        })
        self.set_message('모듈 장착')
        self.refresh_all()

    def remove_last_placement(self):
        if self.placements:
            self.placements.pop()
            self.set_message('마지막 모듈 해제')
            self.refresh_all()

    def clear_placements(self):
        self.placements.clear()
        self.set_message('전체 해제')
        self.refresh_all()

    def on_cartridge_bag_selected(self, item: QListWidgetItem):
        bag_id = item.data(Qt.UserRole)
        entry = self.cartridge_bag_entry(bag_id)
        if not entry:
            return
        usage = self.usage_for(bag_id)
        if usage and usage.get('character_id') != self.current_character_id:
            if not self.confirm_reassign_item(usage, '카트리지'):
                self.set_message('중복 장착 취소')
                return
            self.remove_bag_assignment(bag_id)
        self.current_cartridge_bag_id = bag_id
        self.current_cartridge_id = entry['base_id']
        self.cartridge_attr_selections[self.current_cartridge_id] = {'main': entry['main'], 'subs': list(entry['subs'])[:4]}
        self.set_message('가방 카트리지 적용')
        self.refresh_all()

    def on_drive_bag_selected(self, item: QListWidgetItem):
        bag_id = item.data(Qt.UserRole)
        entry = self.drive_bag_entry(bag_id)
        if not entry:
            return
        self.current_drive_bag_id = bag_id
        self.current_module_id = entry['base_id']
        self.drive_attr_selections[self.current_module_id] = {'main': [], 'subs': list(entry['subs'])[:4]}
        usage = self.usage_for(bag_id)
        if usage:
            self.set_message(f"사용 중 드라이브 선택: {usage.get('character_name', '-')}에게 장착됨")
        else:
            self.set_message('가방 드라이브 선택')
        self.refresh_all()

    def open_placed_modules_dialog(self):
        dialog = QDialog(self)
        dialog.setWindowTitle('장착 모듈')
        dialog.resize(560, 620)
        root = QVBoxLayout(dialog)
        root.setContentsMargins(16, 16, 16, 16)
        root.setSpacing(12)
        title = QLabel('장착 모듈')
        title.setObjectName('SectionTitle')
        root.addWidget(title)
        help_text = QLabel('해제는 메인 보드에서 해당 모듈 칸을 클릭하면 됩니다.')
        help_text.setObjectName('Muted')
        help_text.setWordWrap(True)
        root.addWidget(help_text)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        body = QWidget()
        body.setObjectName('TransparentPanel')
        body_layout = QVBoxLayout(body)
        body_layout.setContentsMargins(0, 0, 0, 0)
        body_layout.setSpacing(10)
        if not self.placements:
            empty = QLabel('아직 장착된 모듈이 없습니다.')
            empty.setObjectName('Muted')
            body_layout.addWidget(empty)
        for idx, placement in enumerate(self.placements, start=1):
            module = placement['module']
            color = MODULE_QUALITY_COLORS.get(module.get('quality'), MODULE_QUALITY_COLORS['B급'])
            card = QFrame()
            card.setObjectName('LoadoutPlacedDialogItem')
            card.setStyleSheet(
                f"QFrame#LoadoutPlacedDialogItem {{background: #111827; border: 1px solid {color[0]}; border-radius: 14px;}}"
                f"QLabel#LoadoutPlacedDialogIndex {{background: {color[0]}; color: #101827; border-radius: 11px; padding: 5px 9px; font-weight: 900; min-width: 28px;}}"
            )
            row = QHBoxLayout(card)
            row.setContentsMargins(12, 12, 12, 12)
            row.setSpacing(12)
            idx_label = QLabel(str(idx))
            idx_label.setObjectName('LoadoutPlacedDialogIndex')
            idx_label.setAlignment(Qt.AlignCenter)
            row.addWidget(idx_label)
            icon = ImageLabel(52, 'LoadoutItemImage')
            icon.set_path(module_image_path(module))
            row.addWidget(icon)
            text_box = QVBoxLayout()
            name = QLabel(normalize_name(module.get('name')))
            name.setObjectName('LoadoutItemName')
            name.setWordWrap(True)
            meta = QLabel(f"{module.get('quality')} · {GEOMETRY_LABELS.get(module.get('geometry'), module.get('geometry'))} · {len(placement.get('cells', []))}칸")
            meta.setObjectName('Muted')
            cells = QLabel('좌표: ' + ', '.join(f"{r+1}-{c+1}" for r, c in placement.get('cells', [])))
            cells.setObjectName('Muted')
            attrs = []
            for item in placement.get('attributes', {}).get('main', []):
                attrs.append(format_option(item['id'], module.get('quality'), {'kind': 'drive_main', 'grid_count': len(placement.get('cells', []))}))
            for item in placement.get('attributes', {}).get('subs', []):
                attrs.append(format_option(item, module.get('quality'), {'kind': 'drive_sub', 'grid_count': len(placement.get('cells', []))}))
            attr_label = QLabel(' / '.join(attrs[:6]) if attrs else '-')
            attr_label.setObjectName('Muted')
            attr_label.setWordWrap(True)
            text_box.addWidget(name)
            text_box.addWidget(meta)
            text_box.addWidget(cells)
            text_box.addWidget(attr_label)
            row.addLayout(text_box, 1)
            body_layout.addWidget(card)
        body_layout.addStretch(1)
        scroll.setWidget(body)
        root.addWidget(scroll, 1)
        close_row = QHBoxLayout()
        close_row.addStretch(1)
        close_btn = QPushButton('닫기')
        close_btn.setObjectName('PrimaryButton')
        close_btn.clicked.connect(dialog.accept)
        close_row.addWidget(close_btn)
        root.addLayout(close_row)
        dialog.exec()


    # ------------------------------------------------------------------ scanner / recommendation / final stats
    def set_scan_status(self, message: str):
        # Update the sidebar scan status label without recursively calling this method.
        label = getattr(self, 'scan_status_label', None)
        if label is not None:
            label.setText(message)
        try:
            self.scan_status_changed.emit(message)
        except Exception:
            pass

    def update_scan_status(self):
        scanned_c = sum(1 for item in self.cartridge_bag_items if item.get('scanned'))
        scanned_d = sum(1 for item in self.drive_bag_items if item.get('scanned'))
        self.set_scan_status(
            f'스캔 저장: 카트리지 {len(self.cartridge_bag_items)}개({scanned_c}개 스캔) / '
            f'드라이브 {len(self.drive_bag_items)}개({scanned_d}개 스캔) · 사용 중 {len(self.inventory_usage)}개'
        )

    def open_scan_dialog(self):
        count, ok = QInputDialog.getInt(
            self,
            '가방 자동 스캔',
            '보유 콘솔 개수를 입력하세요.',
            28,
            1,
            2000,
            1,
        )
        if not ok:
            return
        self.run_real_inventory_scan(count)

    def run_real_inventory_scan(self, count: int, dialog: QDialog | None = None):
        if getattr(self, 'scan_worker', None) and self.scan_worker.isRunning():
            QMessageBox.information(self, '스캔 진행 중', '이미 가방 스캔이 진행 중입니다.')
            return
        try:
            from app.scanner.inventory_scan import InventoryScanRunner  # noqa: F401
        except Exception as exc:
            QMessageBox.critical(self, '스캔 백엔드 오류', f'스캔 모듈을 불러오지 못했습니다.\n{exc}')
            return

        self.set_scan_status('스캔 준비 중... HTGame.exe 창을 찾고 컨트롤러 입력 인식 여부를 확인합니다.')
        for btn_name in ('auto_scan_btn',):
            btn = getattr(self, btn_name, None)
            if btn:
                btn.setEnabled(False)
        self.scan_worker = InventoryScanWorker(count, self._scan_debug_dir())
        self.scan_worker.progress.connect(self.on_scan_progress)
        self.scan_worker.completed.connect(self.on_scan_completed)
        self.scan_worker.failed.connect(self.on_scan_failed)
        self.scan_worker.finished.connect(self.on_scan_finished)
        self.scan_worker.start()

    def on_scan_progress(self, index: int, message: str):
        self.set_scan_status(message)

    def on_scan_completed(self, result: dict[str, Any]):
        self.ingest_real_scan_results(result)
        self._keep_scan_debug_text_only()
        self.set_scan_status(
            f"스캔 완료: 카트리지 {len(result.get('cartridges', []))}개 / "
            f"드라이브 {len(result.get('drives', []))}개 / 실패 {len(result.get('errors', []))}개 / "
            f"검토 {len(result.get('review', []))}개"
        )

    def on_scan_failed(self, message: str):
        QMessageBox.critical(
            self,
            '스캔 실패',
            '실제 스캔을 실행하지 못했습니다.\n\n'
            f'{message}\n\n'
            '확인할 것:\n'
            '1. setup.bat 실행\n'
            '2. ViGEmBus_1.22.0_x64_x86_arm64.exe 설치 또는 vgamepad 설치 중 드라이버 설치 완료\n'
            '3. 게임 가방 > 콘솔 탭 열기\n'
            '4. 첫 번째 콘솔 선택 상태로 시작',
        )
        self.update_scan_status()

    def on_scan_finished(self):
        for btn_name in ('auto_scan_btn',):
            btn = getattr(self, btn_name, None)
            if btn:
                btn.setEnabled(True)

    def _scan_debug_dir(self):
        from pathlib import Path
        import os
        base = Path(os.environ.get('APPDATA', str(Path.home()))) / 'NTE Tool' / 'scan_debug'
        base.mkdir(parents=True, exist_ok=True)
        return base

    def _keep_scan_debug_text_only(self):
        debug_dir = self._scan_debug_dir()
        for path in debug_dir.rglob('*'):
            if path.is_file() and path.suffix.lower() != '.txt':
                try:
                    path.unlink()
                except OSError:
                    pass

    def ingest_real_scan_results(self, result: dict[str, Any]):
        # A re-scan replaces prior scanner data instead of appending the same
        # inventory again.  Non-scanned entries remain untouched.
        self.cartridge_bag_items = [item for item in self.cartridge_bag_items if not item.get('scanned')]
        self.drive_bag_items = [item for item in self.drive_bag_items if not item.get('scanned')]
        self.current_cartridge_bag_id = ''
        self.current_drive_bag_id = ''
        c_start = len(self.cartridge_bag_items)
        d_start = len(self.drive_bag_items)
        for i, entry in enumerate(result.get('cartridges', [])):
            base = self.cartridges_by_id.get(entry.get('base_id'))
            if not base:
                continue
            quality = entry.get('quality') or base.get('quality', 'S급')
            subs = list(entry.get('subs') or [])[:4]
            while len(subs) < 4:
                subs.append(DEFAULT_CARTRIDGE_ATTRIBUTES['subs'][len(subs)])
            self.cartridge_bag_items.append({
                'bag_id': f"scan-cartridge-{c_start + i}",
                'base_id': base['id'],
                'quality': quality,
                'main': entry.get('main') or DEFAULT_CARTRIDGE_ATTRIBUTES['main'],
                'subs': subs,
                'scanned': True,
                'order': c_start + i,
                'raw_text': entry.get('raw_text', ''),
                'confidence': entry.get('confidence', 0),
            })
        for i, entry in enumerate(result.get('drives', [])):
            base = self.modules_by_id.get(entry.get('base_id'))
            if not base:
                continue
            geometry = entry.get('geometry') or base.get('geometry')
            grid_count = geometry_cell_count(geometry)
            subs = list(entry.get('subs') or [])[:4]
            while len(subs) < 4:
                subs.append(DEFAULT_DRIVE_ATTRIBUTES['subs'][len(subs)])
            self.drive_bag_items.append({
                'bag_id': f"scan-drive-{d_start + i}",
                'base_id': base['id'],
                'quality': entry.get('quality') or base.get('quality', 'S급'),
                'geometry': geometry,
                'mains': list(entry.get('mains') or [stat['id'] for stat in get_drive_main_stats(base, grid_count)]),
                'subs': subs,
                'scanned': True,
                'order': d_start + i,
                'raw_text': entry.get('raw_text', ''),
                'confidence': entry.get('confidence', 0),
            })
        self.rebuild_cartridge_bag_list()
        self.rebuild_drive_bag_list()
        self.update_scan_status()
        self.set_message('실제 스캔 결과 저장 완료 (이전 스캔 결과 교체)')

    def ingest_scan_test_results(self, count: int):
        sub_ids_c = [it['id'] for it in CARTRIDGE_SUB_OPTIONS]
        sub_ids_d = [it['id'] for it in DRIVE_SUB_OPTIONS]
        main_ids = [it['id'] for it in CARTRIDGE_MAIN_OPTIONS]
        c_start = len(self.cartridge_bag_items)
        d_start = len(self.drive_bag_items)
        for i in range(count):
            if i % 5 == 0 and CARTRIDGES:
                base = CARTRIDGES[(c_start + i) % len(CARTRIDGES)]
                self.cartridge_bag_items.append({
                    'bag_id': f'scan-cartridge-{c_start + i}',
                    'base_id': base['id'],
                    'quality': base.get('quality', 'S급'),
                    'main': main_ids[i % len(main_ids)],
                    'subs': [sub_ids_c[(i + j) % len(sub_ids_c)] for j in range(4)],
                    'scanned': True,
                    'order': c_start + i,
                })
            elif DRIVE_MODULES:
                base = DRIVE_MODULES[(d_start + i) % len(DRIVE_MODULES)]
                grid_count = geometry_cell_count(base.get('geometry'))
                self.drive_bag_items.append({
                    'bag_id': f'scan-drive-{d_start + i}',
                    'base_id': base['id'],
                    'quality': base.get('quality', 'S급'),
                    'geometry': base.get('geometry'),
                    'mains': [stat['id'] for stat in get_drive_main_stats(base, grid_count)],
                    'subs': [sub_ids_d[(i + j) % len(sub_ids_d)] for j in range(4)],
                    'scanned': True,
                    'order': d_start + i,
                })
        self.rebuild_cartridge_bag_list()
        self.rebuild_drive_bag_list()
        self.update_scan_status()
        self.set_message(f'스캔 결과 테스트 저장: {count}개')
        QMessageBox.information(self, '저장 완료', f'스캔 결과 테스트 데이터 {count}개를 가방에 저장했습니다.')

    def apply_recommended_loadout(self):
        owner_count = int(slot_meta_for_character(self.current_character_id).get('owner_grid_count', 3))
        self.rebuild_inventory_usage()
        unused_cartridges = [it for it in self.cartridge_bag_items if not self.usage_for(it['bag_id']) or self.usage_for(it['bag_id']).get('character_id') == self.current_character_id]
        if unused_cartridges:
            entry = next((it for it in unused_cartridges if it.get('quality') == 'S급'), unused_cartridges[0])
            self.current_cartridge_bag_id = entry['bag_id']
            self.current_cartridge_id = entry['base_id']
            self.cartridge_attr_selections[self.current_cartridge_id] = {'main': entry['main'], 'subs': list(entry['subs'])[:4]}
        self.placements.clear()
        slot_layout = trim_slot_matrix(slot_rows_for_character(self.current_character_id))
        candidates = sorted(
            [it for it in self.drive_bag_items if not self.usage_for(it['bag_id']) or self.usage_for(it['bag_id']).get('character_id') == self.current_character_id],
            key=lambda it: (
                0 if geometry_cell_count(it.get('geometry')) == owner_count else 1,
                {'S급': 0, 'A급': 1, 'B급': 2}.get(it.get('quality'), 9),
                -geometry_cell_count(it.get('geometry')),
            )
        )
        placed = 0
        for entry in candidates:
            if placed >= 12:
                break
            if self._try_place_drive_entry(entry, slot_layout):
                placed += 1
        self.set_message(f'추천 장착 완료: {placed}개 배치')
        self.refresh_all()

    def _try_place_drive_entry(self, entry: dict[str, Any], slot_layout: dict[str, Any]) -> bool:
        module = self.modules_by_id.get(entry['base_id'])
        if not module:
            return False
        for r, row in enumerate(slot_layout['rows']):
            for c, value in enumerate(row):
                if value == -1:
                    continue
                placement = resolve_module_placement(module.get('geometry'), (r, c), slot_layout, self.occupied_slots())
                if not placement.get('is_valid'):
                    continue
                grid_count = geometry_cell_count(module.get('geometry'))
                self.placement_counter += 1
                self.placements.append({
                    'id': f"{module['id']}-auto-{self.placement_counter}",
                    'module': module,
                    'bag_id': entry.get('bag_id', ''),
                    'bag_entry': deepcopy(entry),
                    'character_id': self.current_character_id,
                    'origin': placement.get('origin'),
                    'cells': placement.get('cells', []),
                    'attributes': {
                        'main': get_drive_main_stats(module, grid_count),
                        'subs': list(entry.get('subs') or DEFAULT_DRIVE_ATTRIBUTES['subs'])[:4],
                    },
                })
                return True
        return False

    def open_final_stats_dialog(self):
        dialog = QDialog(self)
        dialog.setWindowTitle('최종 스펙')
        dialog.resize(760, 760)
        root = QVBoxLayout(dialog)
        root.setContentsMargins(16, 16, 16, 16)
        root.setSpacing(12)
        title = QLabel('최종 스펙')
        title.setObjectName('SectionTitle')
        root.addWidget(title)
        desc = QLabel('Everness Database 빌드 플래너 방식에 맞춰 캐릭터 Lv.80 / 아크 Lv.80 / 카트리지 / 드라이브 / 특화 효과를 합산합니다. 피해 n%는 통용 피해 증강으로 표시합니다.')
        desc.setObjectName('Muted')
        desc.setWordWrap(True)
        root.addWidget(desc)
        text = QTextEdit()
        text.setReadOnly(True)
        text.setObjectName('LoadoutTextSummary')
        text.setPlainText('\n'.join(self._final_stat_lines()))
        root.addWidget(text, 1)
        close_row = QHBoxLayout()
        close_row.addStretch(1)
        close = QPushButton('닫기')
        close.setObjectName('PrimaryButton')
        close.clicked.connect(dialog.accept)
        close_row.addWidget(close)
        root.addLayout(close_row)
        dialog.exec()

    def _final_stat_lines(self) -> list[str]:
        ch = self.character()
        ark = self.ark()
        cartridge = self.cartridge()
        progress = self.promotion_progress()
        lines = [
            f"캐릭터: {ch.get('name', '-') if ch else '-'}",
            f"아크: {normalize_name(ark.get('name')) if ark else '-'}",
            f"카트리지: {normalize_name(cartridge.get('name')) if cartridge else '-'}",
            f"드라이브 장착: {len(self.placements)}개",
            '',
        ]
        pending = []
        if ch and ch.get('sourcePending'):
            pending.append(f"캐릭터 수치 확인 필요: {ch.get('sourceUrl', '')}")
        if ark and ark.get('sourcePending'):
            pending.append(f"아크 수치 확인 필요: {ark.get('sourceUrl', '')}")
        if pending:
            lines.append('[데이터 확인 필요]')
            lines.extend(pending)
            lines.append('')
        lines.extend(build_final_stat_lines(
            ch,
            ark,
            cartridge,
            self.cartridge_attrs(),
            self.placements,
            progress.get('active_effects', []),
        ))
        if progress.get('active_effects'):
            lines.append('')
            lines.append('[활성 진급 효과 원문]')
            lines.extend(effect.get('description') or effect.get('title') or '-' for effect in progress['active_effects'])
        return lines

    # ------------------------------------------------------------------ refresh
    def filtered_modules(self) -> list[dict[str, Any]]:
        if self.module_quality_filter == '전체':
            return DRIVE_MODULES
        return [item for item in DRIVE_MODULES if item.get('quality') == self.module_quality_filter]

    def filtered_cartridge_bag_items(self) -> list[dict[str, Any]]:
        quality = self.cartridge_bag_quality.currentText() if hasattr(self, 'cartridge_bag_quality') else '전체'
        main_id = self.cartridge_bag_main.currentData() if hasattr(self, 'cartridge_bag_main') else ''
        selected_subs = []
        if hasattr(self, 'cartridge_bag_sub_filters'):
            selected_subs = [combo.currentData() for combo in self.cartridge_bag_sub_filters if combo.currentData()]
        selected_button = self.cartridge_match_group.checkedButton() if hasattr(self, 'cartridge_match_group') else None
        min_match = int(selected_button.property('match_count') or 0) if selected_button else 0
        items = self.cartridge_bag_items
        if quality != '전체':
            items = [it for it in items if it['quality'] == quality]
        if main_id:
            items = [it for it in items if it['main'] == main_id]
        if selected_subs:
            def matches(entry):
                return sum(1 for sub in selected_subs if sub in entry['subs'])
            if min_match > 0:
                items = [it for it in items if matches(it) >= min_match]
            else:
                items = [it for it in items if matches(it) > 0]
        return self.sort_inventory_items(items)

    def filtered_drive_bag_items(self) -> list[dict[str, Any]]:
        quality = self.drive_bag_quality.currentText() if hasattr(self, 'drive_bag_quality') else '전체'
        geometry = self.drive_bag_geometry.currentData() if hasattr(self, 'drive_bag_geometry') else ''
        main_id = self.drive_bag_main.currentData() if hasattr(self, 'drive_bag_main') else ''
        sub_id = self.drive_bag_sub.currentData() if hasattr(self, 'drive_bag_sub') else ''
        items = self.drive_bag_items
        if quality != '전체':
            items = [it for it in items if it['quality'] == quality]
        if geometry:
            items = [it for it in items if it['geometry'] == geometry]
        if main_id:
            items = [it for it in items if main_id in it.get('mains', [])]
        if sub_id:
            items = [it for it in items if sub_id in it['subs']]
        return self.sort_inventory_items(items)

    def promotion_progress(self) -> dict[str, Any]:
        cartridge = self.cartridge()
        promotion = cartridge.get('promotion') or cartridge.get('set', {}).get('promotion') if cartridge else None
        return build_promotion_progress(promotion, self.placements)

    def refresh_all(self):
        self._refreshing = True
        try:
            self.refresh_selector_tiles()
            self.refresh_ark_detail()
            self.refresh_cartridge_panel()
            self.refresh_module_panel()
            self.refresh_board_and_summary()
            self.rebuild_inventory_usage()
            self.rebuild_cartridge_bag_list()
            self.rebuild_drive_bag_list()
            self.update_scan_status()
        finally:
            self._refreshing = False

    def refresh_selector_tiles(self):
        ch = self.character()
        ark = self.ark()
        self.character_tile.set_content(
            character_avatar_path(ch),
            ch.get('name', '-'),
            ELEMENT_LABELS.get(ch.get('element') or ch.get('elementId'), '-')
        )
        self.ark_tile.set_content(
            module_image_path(ark, prefer_icon=True),
            normalize_name(ark.get('name')) if ark else '-',
            ark.get('quality', '') if ark else ''
        )

    def refresh_ark_detail(self):
        ark = self.ark()
        if not ark:
            return
        effect = ark.get('effect') or ark.get('description') or ''
        self.top_ark_effect.setText(text_cut(effect, 130))

    def refresh_cartridge_panel(self):
        cartridge = self.cartridge()
        if not cartridge:
            if hasattr(self, 'cartridge_select_btn'):
                self.cartridge_select_btn.setText('카트리지 선택')
            return
        if hasattr(self, 'cartridge_select_btn'):
            self.cartridge_select_btn.setText(f"카트리지: {normalize_name(cartridge.get('name'))}")
            self.cartridge_select_btn.setToolTip(
                f"{normalize_name(cartridge.get('name'))}\n{cartridge.get('quality', '')}\n클릭하여 카트리지 변경"
            )
        attrs = self.cartridge_attrs()
        self.fill_option_combo(self.cartridge_main_combo, CARTRIDGE_MAIN_OPTIONS, cartridge.get('quality'), attrs.get('main'))
        for i, combo in enumerate(self.cartridge_sub_combos):
            current = (attrs.get('subs') or DEFAULT_CARTRIDGE_ATTRIBUTES['subs'])[i]
            self.fill_option_combo(combo, CARTRIDGE_SUB_OPTIONS, cartridge.get('quality'), current, {'kind': 'cartridge_sub'})

        while self.req_row.count():
            item = self.req_row.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()
        progress = self.promotion_progress()
        self.promotion_count_label.setText(f"{progress['matched_count']} / {progress['total_count']}" if progress['total_count'] else '-')
        for req in progress['requirement_status']:
            label = QLabel(GEOMETRY_LABELS.get(req['geometry'], req['geometry']))
            label.setObjectName('LoadoutRequirementBadgeActive' if req['active'] else 'LoadoutRequirementBadge')
            label.setAlignment(Qt.AlignCenter)
            self.req_row.addWidget(label)
        effects = progress['active_effects']
        if effects:
            self.promotion_effects.setText('\n'.join(effect.get('description') or effect.get('title') or '' for effect in effects))
        else:
            raw_effects = (cartridge.get('promotion') or {}).get('effects', [])
            self.promotion_effects.setText(text_cut(raw_effects[0].get('description', '') if raw_effects else '요구 드라이브 모듈을 장착하면 보너스가 활성화됩니다.', 180))

    def refresh_module_panel(self):
        module = self.module()
        if not module:
            return
        grid_count = geometry_cell_count(module.get('geometry'))
        main_stats = get_drive_main_stats(module, grid_count)
        self.drive_fixed_main.setText(' / '.join(
            format_option(stat['id'], module.get('quality'), {'kind': 'drive_main', 'grid_count': grid_count})
            for stat in main_stats
        ))
        drive_attrs = self.drive_attrs()
        for i, combo in enumerate(self.drive_sub_combos):
            current = (drive_attrs.get('subs') or DEFAULT_DRIVE_ATTRIBUTES['subs'])[i]
            self.fill_option_combo(combo, DRIVE_SUB_OPTIONS, module.get('quality'), current, {'kind': 'drive_sub', 'grid_count': grid_count})
        self.rebuild_module_list()

    def rebuild_module_list(self):
        while self.module_layout.count():
            item = self.module_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()
        self.module_items.clear()
        modules = self.filtered_modules()
        self.module_count_label.setText(f'{len(modules)}개')
        for module in modules:
            item = ModuleListItem(module)
            item.clicked.connect(self.on_module_selected)
            item.set_active(module['id'] == self.current_module_id)
            self.module_items[module['id']] = item
            self.module_layout.addWidget(item)
        self.module_layout.addStretch(1)

    def rebuild_cartridge_bag_list(self):
        if not hasattr(self, 'cartridge_bag_list'):
            return
        self.cartridge_bag_list.blockSignals(True)
        self.cartridge_bag_list.clear()
        for entry in self.filtered_cartridge_bag_items():
            base = self.cartridges_by_id.get(entry['base_id'])
            if not base:
                continue
            usage = self.usage_for(entry['bag_id'])
            suffix = f"\n사용 중: {usage.get('character_name')}" if usage else ''
            text = f"{normalize_name(base.get('name'))}\n{entry['quality']}{suffix}"
            item = QListWidgetItem(text)
            item.setSizeHint(BAG_GRID_ITEM_SIZE)
            item.setTextAlignment(Qt.AlignCenter)
            item.setData(Qt.UserRole, entry['bag_id'])
            sub_text = option_lines(entry['subs'], entry['quality'], {'kind': 'cartridge_sub'})
            tooltip = (
                f"{normalize_name(base.get('name'))}\n"
                f"등급: {entry['quality']}\n"
                f"주옵션: {format_option(entry['main'], entry['quality'])}\n"
                f"부옵션:\n{sub_text}"
            )
            if usage:
                tooltip += f"\n\n사용 중: {usage.get('character_name')}"
                item.setForeground(QBrush(QColor('#7f8ca8')))
            item.setToolTip(tooltip)
            pixmap = QPixmap(str(module_image_path(base)))
            if not pixmap.isNull():
                if usage:
                    pixmap = QPixmap.fromImage(pixmap.toImage().convertToFormat(QImage.Format_Grayscale8))
                item.setIcon(QIcon(pixmap))
            self.cartridge_bag_list.addItem(item)
        self.cartridge_bag_list.blockSignals(False)

    def rebuild_drive_bag_list(self):
        if not hasattr(self, 'drive_bag_list'):
            return
        self.drive_bag_list.blockSignals(True)
        self.drive_bag_list.clear()
        for entry in self.filtered_drive_bag_items():
            base = self.modules_by_id.get(entry['base_id'])
            if not base:
                continue
            usage = self.usage_for(entry['bag_id'])
            suffix = f"\n사용 중: {usage.get('character_name')}" if usage else ''
            text = f"{GEOMETRY_LABELS.get(entry['geometry'], entry['geometry'])}\n{entry['quality']}{suffix}"
            item = QListWidgetItem(text)
            item.setSizeHint(BAG_GRID_ITEM_SIZE)
            item.setTextAlignment(Qt.AlignCenter)
            item.setData(Qt.UserRole, entry['bag_id'])
            grid_count = geometry_cell_count(entry['geometry'])
            mains = '\n'.join(format_option(main, entry['quality'], {'kind': 'drive_main', 'grid_count': grid_count}) for main in entry.get('mains', []))
            sub_text = option_lines(entry['subs'], entry['quality'], {'kind': 'drive_sub', 'grid_count': grid_count})
            tooltip = (
                f"{normalize_name(base.get('name'))}\n"
                f"등급: {entry['quality']}\n"
                f"모양: {GEOMETRY_LABELS.get(entry['geometry'], entry['geometry'])}\n"
                f"고정 주옵션:\n{mains}\n"
                f"부옵션:\n{sub_text}"
            )
            if usage:
                tooltip += f"\n\n사용 중: {usage.get('character_name')}"
                item.setForeground(QBrush(QColor('#7f8ca8')))
            item.setToolTip(tooltip)
            pixmap = QPixmap(str(module_image_path(base)))
            if not pixmap.isNull():
                if usage:
                    pixmap = QPixmap.fromImage(pixmap.toImage().convertToFormat(QImage.Format_Grayscale8))
                item.setIcon(QIcon(pixmap))
            self.drive_bag_list.addItem(item)
        self.drive_bag_list.blockSignals(False)

    def refresh_board_and_summary(self):
        meta = slot_meta_for_character(self.current_character_id)
        owner_grid_count = int(meta.get('owner_grid_count', 3))
        matching_count = sum(1 for placement in self.placements if geometry_cell_count(placement['module'].get('geometry')) == owner_grid_count)
        effect = SLOT_EFFECTS.get(meta.get('slot_id'), {'label': '특화', 'value': 0})
        effect_value = matching_count * effect.get('value', 0)
        progress = self.promotion_progress()
        self.device.set_core(self.cartridge(), progress)
        self.device.draw(self.current_character_id, self.placements)

        layout = trim_slot_matrix(slot_rows_for_character(self.current_character_id))
        placed_cells = len(self.occupied_slots())
        active_count = layout['active_count']
        self.special_top_title.setText(f'{roman_grid(owner_grid_count)}형 특화')
        self.special_top_desc.setText(
            f"{roman_grid(owner_grid_count)}형 1개당 {effect.get('label')} +{format_percent(effect.get('value', 0))}"
        )
        self.special_top_total.setText(f"현재 {matching_count}개 적용 · +{format_percent(effect_value)}")

        self.placed_modules_button.setText(f"장착 모듈 {len(self.placements)}개 보기")
        self.placed_modules_button.setEnabled(bool(self.placements))
        # v0.6.13: 하단 계산 결과 요약 패널은 삭제되었으므로,
        # summary_rows가 존재할 때만 갱신합니다. 최종 스펙은 플로팅 창에서 확인합니다.
        if getattr(self, 'summary_rows', None):
            if '점유 슬롯' in self.summary_rows:
                self.summary_rows['점유 슬롯'].setText(f'{placed_cells} / {active_count}')
            if '세트 효과' in self.summary_rows:
                self.summary_rows['세트 효과'].setText(f"{progress['matched_count']} / {progress['total_count']}" if progress['total_count'] else '-')
            if '슬롯 보너스' in self.summary_rows:
                self.summary_rows['슬롯 보너스'].setText(f"+{format_percent(effect_value)}")
            if '미배치 칸' in self.summary_rows:
                self.summary_rows['미배치 칸'].setText(f'{max(active_count - placed_cells, 0)}칸')
        # v0.6.13: attribute_summary 패널도 삭제되었으므로 남아 있을 때만 갱신합니다.
        if getattr(self, 'attribute_summary', None) is not None:
            self.attribute_summary.setPlainText('\n'.join(aggregate_attribute_lines(self.cartridge(), self.cartridge_attrs(), self.placements)))
