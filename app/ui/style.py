APP_QSS = """
* {
    font-family: "Malgun Gothic", "Noto Sans CJK KR", "Segoe UI", sans-serif;
    color: #e8eefc;
    font-size: 12px;
}
QMainWindow, QWidget#Root {
    background: #0d1220;
}
QFrame#Sidebar {
    background: #111827;
    border-right: 1px solid #24314d;
}
QFrame#HeaderCard, QFrame#Panel {
    background: #151d2f;
    border: 1px solid #263653;
    border-radius: 14px;
}
QFrame#AccentPanel {
    background: #17233a;
    border: 1px solid #3e63a8;
    border-radius: 14px;
}
QLabel#AppTitle {
    font-size: 22px;
    font-weight: 800;
    color: #ffffff;
}
QLabel#AppSubtitle {
    color: #8ea4d0;
    font-size: 11px;
}
QLabel#PageTitle {
    font-size: 24px;
    font-weight: 800;
    color: #ffffff;
}
QLabel#SectionTitle {
    font-size: 15px;
    font-weight: 700;
    color: #f4f7ff;
}
QLabel#Muted {
    color: #8ea4d0;
}
QLabel#Badge {
    background: #20304f;
    color: #b9ccff;
    border: 1px solid #3e63a8;
    border-radius: 10px;
    padding: 5px 10px;
}
QPushButton {
    background: #1a2540;
    border: 1px solid #314465;
    border-radius: 10px;
    padding: 9px 12px;
    color: #e8eefc;
}
QPushButton:hover {
    background: #243452;
    border-color: #5578bc;
}
QPushButton#PrimaryButton {
    background: #4f7cff;
    border: 1px solid #7ea0ff;
    color: #ffffff;
    font-weight: 700;
}
QPushButton#NavButton {
    text-align: left;
    padding: 12px 14px;
    border-radius: 12px;
    border: 1px solid transparent;
    background: transparent;
    color: #b7c5e8;
    font-size: 13px;
}
QPushButton#NavButton:checked {
    background: #243452;
    border-color: #4f7cff;
    color: white;
    font-weight: 700;
}
QComboBox, QSpinBox {
    background: #0f1728;
    border: 1px solid #314465;
    border-radius: 8px;
    padding: 7px 9px;
    min-height: 20px;
}
QComboBox {
    padding-right: 34px;
}
QComboBox::drop-down {
    subcontrol-origin: padding;
    subcontrol-position: top right;
    width: 26px;
    border-left: none;
}
QComboBox::down-arrow {
    width: 10px;
    height: 10px;
    margin-right: 8px;
}
QComboBox QAbstractItemView {
    background: #111827;
    border: 1px solid #314465;
    selection-background-color: #4f7cff;
}
QTableWidget {
    background: #0f1728;
    border: 1px solid #263653;
    border-radius: 10px;
    gridline-color: #263653;
    alternate-background-color: #121c31;
}
QHeaderView::section {
    background: #1a2540;
    color: #dbe7ff;
    border: none;
    border-bottom: 1px solid #314465;
    padding: 8px;
    font-weight: 700;
}
QScrollArea {
    border: none;
    background: transparent;
}
QLineEdit {
    background: #0f1728;
    border: 1px solid #314465;
    border-radius: 8px;
    padding: 8px 10px;
}
QCheckBox {
    color: #dbe7ff;
}
QProgressBar {
    background: #101827;
    border: 1px solid #2f4266;
    border-radius: 8px;
    height: 10px;
    text-align: center;
}
QProgressBar::chunk {
    background: #4f7cff;
    border-radius: 8px;
}
"""
APP_QSS += """
QListWidget {
    background: #0f1728;
    border: 1px solid #263653;
    border-radius: 10px;
    padding: 8px;
}
QListWidget::item {
    color: #dbe7ff;
    padding: 6px;
}
QListWidget::item:selected {
    background: #243452;
    color: #ffffff;
}
QTableCornerButton::section {
    background: #1a2540;
    border: none;
}
QScrollBar:vertical {
    background: #0f1728;
    width: 12px;
    margin: 0;
}
QScrollBar::handle:vertical {
    background: #314465;
    border-radius: 6px;
    min-height: 24px;
}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0;
}
QScrollBar:horizontal {
    background: #0f1728;
    height: 12px;
    margin: 0;
}
QScrollBar::handle:horizontal {
    background: #314465;
    border-radius: 6px;
    min-width: 24px;
}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
    width: 0;
}
"""

APP_QSS += """
/* Cafe optimizer layout - aligned with the desktop app theme */
QFrame#CafeTopBox {
    background: #151d2f;
    border: 1px solid #263653;
    border-radius: 14px;
    min-height: 78px;
}
QFrame#CafeTopBox:hover {
    border-color: #3e63a8;
}
QLabel#CafeTopTitle {
    font-size: 18px;
    font-weight: 800;
    color: #ffffff;
}
QLabel#CafeTopSub {
    font-size: 12px;
    font-weight: 700;
    color: #8ea4d0;
}
QLabel#CafeTopValue {
    font-size: 22px;
    font-weight: 800;
    color: #ffffff;
}
QLabel#CafeCaption {
    color: #8ea4d0;
    font-size: 11px;
}
QLabel#CafeSkillSummary {
    color: #dbe7ff;
    font-size: 12px;
    line-height: 1.35;
}
QFrame#CafeResultPanel {
    background: #151d2f;
    border: 1px solid #263653;
    border-radius: 14px;
}
QLabel#ResultPanelTitle {
    background: #17233a;
    border-bottom: 1px solid #263653;
    color: #ffffff;
    font-size: 18px;
    font-weight: 800;
    min-height: 46px;
    border-top-left-radius: 14px;
    border-top-right-radius: 14px;
}
QFrame#StoreResultCard {
    background: #111827;
    border-right: 1px solid #263653;
    border-radius: 0px;
}
QFrame#StoreResultCard:hover {
    background: #17233a;
}
QFrame#StoreResultCard[inactive="true"] {
    background: #0f1728;
}
QLabel#StoreTitle {
    color: #ffffff;
    font-size: 18px;
    font-weight: 800;
}
QLabel#MenuName {
    color: #ffffff;
    font-size: 14px;
    font-weight: 800;
}
QLabel#IncomeValue {
    color: #ffffff;
    font-size: 16px;
    font-weight: 800;
}
QLabel#TrendBadge {
    background: #20304f;
    border: 1px solid #3e63a8;
    border-radius: 10px;
    color: #b9ccff;
    padding: 4px 8px;
    font-size: 11px;
}
QFrame#ConditionRail {
    background: #17233a;
    border: 1px solid #263653;
    border-top-left-radius: 14px;
    border-bottom-left-radius: 14px;
    border-right: 0px;
}
QLabel#ConditionRailLabel {
    color: #ffffff;
    font-size: 17px;
    font-weight: 800;
}
QFrame#ConditionPanel {
    background: #151d2f;
    border: 1px solid #263653;
    border-top-right-radius: 14px;
    border-bottom-right-radius: 0px;
    border-bottom-left-radius: 0px;
}
QFrame#ConditionControlPanel {
    background: #151d2f;
    border: 1px solid #263653;
    border-top: 0px;
    border-radius: 0px;
}
QFrame#ConditionControlPanel:hover {
    background: #17233a;
}
QLabel#LargeSectionTitle {
    color: #ffffff;
    font-size: 18px;
    font-weight: 800;
}
QFrame#EmployeeMiniCard {
    background: #0f1728;
    border: 1px solid #314465;
    border-radius: 10px;
}
QFrame#EmployeeMiniCard:hover {
    border-color: #5578bc;
    background: #17233a;
}
QDoubleSpinBox {
    background: #0f1728;
    border: 1px solid #314465;
    border-radius: 8px;
    padding: 7px 9px;
    min-height: 20px;
}
QComboBox, QSpinBox, QDoubleSpinBox {
    selection-background-color: #4f7cff;
}

"""
APP_QSS += """
QLabel#EmployeeAvatar {
    background: #101827;
    border: 1px solid #314465;
    border-radius: 8px;
}
QLabel#SmallEmployeeAvatar {
    background: #101827;
    border: 1px solid #314465;
    border-radius: 6px;
    color: #8ea4d0;
    font-size: 10px;
}
QLabel#MenuThumb {
    background: #101827;
    border: 1px solid #314465;
    border-radius: 12px;
    padding: 3px;
    color: #8ea4d0;
}
QFrame#EmployeeMiniCard QSpinBox {
    min-width: 82px;
    padding-left: 6px;
    padding-right: 6px;
}
QFrame#EmployeeMiniCard QCheckBox {
    font-weight: 700;
}
"""
APP_QSS += """
/* Loadout page v0.3 layout based on the original React web app */
QLabel#LoadoutKicker {
    color: #7df4df;
    font-size: 11px;
    font-weight: 800;
    letter-spacing: 0.5px;
}
QLabel#LoadoutHeaderBadge {
    background: #18243b;
    color: #dbe7ff;
    border: 1px solid #314465;
    border-radius: 10px;
    padding: 7px 10px;
    font-weight: 800;
}
QFrame#LoadoutCharacterCard, QFrame#LoadoutSubPanel, QFrame#LoadoutPicker, QFrame#LoadoutEquippedStrip {
    background: #151d2f;
    border: 1px solid #263653;
    border-radius: 14px;
}
QFrame#LoadoutCharacterCard {
    border-color: rgba(255, 210, 94, 0.55);
    background: #17233a;
}
QLabel#LoadoutAvatar {
    background: #0f1728;
    border: 1px solid #314465;
    border-radius: 12px;
    color: #dbe7ff;
    font-size: 20px;
    font-weight: 900;
}
QLabel#LoadoutQuality {
    color: #ffd25e;
    font-size: 12px;
    font-weight: 900;
}
QLabel#LoadoutCharacterName {
    color: #ffffff;
    font-size: 21px;
    font-weight: 900;
}
QLabel#LoadoutItemName {
    color: #ffffff;
    font-weight: 800;
}
QLabel#LoadoutMiniBadge, QLabel#LoadoutRequirementBadge {
    background: #20304f;
    color: #cfe0ff;
    border: 1px solid #3e63a8;
    border-radius: 9px;
    padding: 5px 8px;
    font-weight: 800;
}
QLabel#LoadoutRequirementBadge {
    min-height: 24px;
    min-width: 54px;
}
QLabel#LoadoutSpecialTotal {
    color: #ffd25e;
    font-size: 18px;
    font-weight: 900;
}
QFrame#LoadoutDevice {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #ffd94d, stop:0.54 #f7b800, stop:1 #d99300);
    border: 1px solid rgba(255, 238, 120, 0.75);
    border-radius: 28px;
}
QFrame#LoadoutDeviceScreen {
    background: #111827;
    border: 1px solid rgba(255, 255, 255, 0.14);
    border-radius: 14px;
}
QFrame#LoadoutSlotCellEmpty {
    background: #080d18;
    border: 1px solid #18233a;
    border-radius: 8px;
}
QFrame#LoadoutSlotCellActive {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #273d6a, stop:1 #16233d);
    border: 1px solid #5b82d9;
    border-radius: 8px;
}
QFrame#LoadoutSlotCellFilled {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #ffcf68, stop:1 #d1782a);
    border: 1px solid #ffd25e;
    border-radius: 8px;
}
QFrame#LoadoutCartridgeDock {
    background: rgba(17, 24, 39, 0.38);
    border: 1px solid rgba(38, 54, 83, 0.45);
    border-radius: 16px;
}
QFrame#TinyIcon_orange, QFrame#TinyIcon_purple, QFrame#TinyIcon_blue {
    border-radius: 12px;
}
QFrame#TinyIcon_orange {
    background: #392417;
    border: 1px solid #ffae58;
}
QFrame#TinyIcon_purple {
    background: #271d3d;
    border: 1px solid #a78bfa;
}
QFrame#TinyIcon_blue {
    background: #15263d;
    border: 1px solid #63b3ed;
}
QLabel#TinyIconText {
    color: #ffffff;
    font-weight: 900;
    font-size: 11px;
}
QFrame#LoadoutAttributeEditor, QFrame#LoadoutModuleItem {
    background: #0f1728;
    border: 1px solid #263653;
    border-radius: 12px;
}
QFrame#LoadoutModuleItem:hover {
    border-color: #5578bc;
    background: #17233a;
}
QPushButton#LoadoutFilterButton {
    padding: 6px 8px;
    border-radius: 8px;
    background: #0f1728;
    border: 1px solid #314465;
    font-size: 11px;
}
QPushButton#LoadoutFilterButton:checked {
    background: #243452;
    border-color: #ffd25e;
    color: #ffffff;
    font-weight: 800;
}
QFrame#LoadoutFilterChipBox {
    background: #0f1728;
    border: 1px solid #263653;
    border-radius: 10px;
}
QPushButton#LoadoutFilterChip {
    background: #18243b;
    border: 1px solid #3e63a8;
    border-radius: 8px;
    color: #dbe7ff;
    padding: 6px 8px;
    text-align: left;
    font-size: 11px;
}
QPushButton#LoadoutFilterChip:hover {
    background: #243452;
    border-color: #ffd25e;
    color: #ffffff;
}
QLabel#LoadoutStripValue, QLabel#LoadoutSummaryValue {
    color: #ffffff;
    font-weight: 900;
}
"""
APP_QSS += """
/* Loadout interactive additions v0.4 */
QLabel#LoadoutImage, QLabel#LoadoutItemImage, QLabel#LoadoutSmallItemImage, QLabel#LoadoutCoreImage {
    background: #101827;
    border: 1px solid #314465;
    border-radius: 10px;
    color: #8ea4d0;
    font-weight: 800;
}
QLabel#LoadoutSmallItemImage {
    border-radius: 8px;
}
QLabel#LoadoutCoreImage {
    border: 1px solid #ffd25e;
    background: #17233a;
}
QLabel#LoadoutRequirementBadgeActive {
    background: #3b2e12;
    color: #fff5ce;
    border: 1px solid #ffd25e;
    border-radius: 9px;
    padding: 5px 8px;
    font-weight: 900;
    min-height: 24px;
    min-width: 54px;
}
QLabel#LoadoutPromotionEffectActive {
    background: rgba(79, 124, 255, 0.16);
    border: 1px solid #4f7cff;
    border-radius: 8px;
    color: #dbe7ff;
    padding: 7px 8px;
    font-weight: 800;
}
QLabel#LoadoutPromotionEffectInactive {
    background: #0f1728;
    border: 1px solid #263653;
    border-radius: 8px;
    color: #8ea4d0;
    padding: 7px 8px;
}
QFrame#LoadoutSlotCellMatched {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #7df4df, stop:1 #1d7b88);
    border: 1px solid #bafff5;
    border-radius: 8px;
}
QFrame#LoadoutModuleItem[active="true"] {
    background: #243452;
    border: 1px solid #ffd25e;
}
QTextEdit#LoadoutTextSummary {
    background: #0f1728;
    border: 1px solid #263653;
    border-radius: 10px;
    padding: 8px;
    color: #dbe7ff;
}
"""
APP_QSS += """
QWidget#TransparentPanel {
    background: transparent;
}
"""

APP_QSS += """
/* Loadout UI optimization v0.4.1 */
QFrame#LoadoutSelectorTile {
    background: #0f1728;
    border: 1px solid #314465;
    border-radius: 12px;
}
QFrame#LoadoutSelectorTile:hover {
    background: #17233a;
    border-color: #5578bc;
}
QLabel#LoadoutSelectorImage {
    background: #101827;
    border: 1px solid #314465;
    border-radius: 12px;
    color: #8ea4d0;
}
QTabWidget#LoadoutTabs::pane {
    border: 0;
    top: 0px;
}
QTabBar::tab {
    background: #0f1728;
    border: 1px solid #314465;
    border-bottom: 0;
    padding: 8px 14px;
    margin-right: 4px;
    border-top-left-radius: 8px;
    border-top-right-radius: 8px;
}
QTabBar::tab:selected {
    background: #243452;
    border-color: #ffd25e;
    color: #ffffff;
    font-weight: 800;
}
QFrame#LoadoutEquippedWrap {
    background: rgba(17, 24, 39, 0.42);
    border: 1px solid rgba(38, 54, 83, 0.45);
    border-radius: 14px;
}
QFrame#LoadoutEquippedBadge {
    background: #17233a;
    border: 1px solid #314465;
    border-radius: 12px;
}
QLabel#LoadoutPlacedIndex {
    background: #ffd25e;
    color: #101827;
    border-radius: 10px;
    padding: 4px 8px;
    font-weight: 900;
    min-width: 22px;
}
"""

APP_QSS += """
/* Main/sub option separation v0.4.2 */
QFrame#LoadoutOptionGroupPrimary {
    background: #17233a;
    border: 1px solid #5578bc;
    border-radius: 12px;
}
QFrame#LoadoutOptionGroupSecondary {
    background: #0f1728;
    border: 1px solid #314465;
    border-radius: 12px;
}
QLabel#LoadoutOptionGroupTitle {
    color: #ffffff;
    font-size: 13px;
    font-weight: 900;
}
QLabel#LoadoutOptionIndex {
    background: #20304f;
    color: #cfe0ff;
    border: 1px solid #3e63a8;
    border-radius: 8px;
    padding: 6px 8px;
    font-weight: 800;
    min-width: 62px;
}
QLabel#LoadoutMainOptionValue {
    background: #0f1728;
    border: 1px solid #314465;
    border-radius: 9px;
    color: #ffd25e;
    padding: 9px 10px;
    font-weight: 900;
}
"""

APP_QSS += """
/* Loadout layout optimization v0.4.3 */
QFrame#LoadoutTopStrip {
    background: #111827;
    border: 1px solid #263653;
    border-radius: 14px;
}
QFrame#LoadoutTopStrip QLabel#LoadoutHeaderBadge {
    min-height: 30px;
}
QFrame#LoadoutSelectorTile {
    min-width: 96px;
    max-width: 96px;
    min-height: 96px;
    max-height: 96px;
}
QLabel#LoadoutSelectorImage {
    border-color: #3e63a8;
}
QScrollArea QWidget#TransparentPanel {
    background: transparent;
}
"""

APP_QSS += """
/* Loadout layout v0.4.4 */
QFrame#LoadoutTopEffectBox {
    background: #151d2f;
    border: 1px solid #263653;
    border-radius: 14px;
}
QFrame#LoadoutPlacementBar {
    background: #151d2f;
    border: 1px solid #263653;
    border-radius: 14px;
}
QPushButton#LoadoutPlacementButton {
    background: #243452;
    border: 1px solid #4f7cff;
    border-radius: 10px;
    padding: 8px 12px;
    font-weight: 800;
}
QPushButton#LoadoutPlacementButton:disabled {
    background: #111827;
    border-color: #263653;
    color: #60708f;
}
QFrame#LoadoutPlacedDialogItem {
    background: #111827;
    border: 1px solid #314465;
    border-radius: 14px;
}
QLabel#LoadoutPlacedDialogIndex {
    background: #ffd25e;
    color: #101827;
    border-radius: 11px;
    padding: 5px 9px;
    font-weight: 900;
}
"""
APP_QSS += """
/* Loadout v14 bag grid and promotion icons */
QListWidget#LoadoutBagGrid {
    background: #0f1728;
    border: 1px solid #263653;
    border-radius: 12px;
    padding: 8px;
}
QListWidget#LoadoutBagGrid::item {
    background: #111827;
    border: 1px solid #263653;
    border-radius: 10px;
    color: #dbe7ff;
    padding: 6px;
    margin: 4px;
}
QListWidget#LoadoutBagGrid::item:hover {
    background: #17233a;
    border-color: #5578bc;
}
QListWidget#LoadoutBagGrid::item:selected {
    background: #243452;
    border-color: #ffd25e;
    color: #ffffff;
}
QLabel#PromotionReqIcon, QLabel#PromotionReqIconActive {
    background: #18243b;
    border: 1px solid #314465;
    border-radius: 7px;
    padding: 2px;
}
QLabel#PromotionReqIconActive {
    background: #3b2e12;
    border: 1px solid #ffd25e;
}
"""

APP_QSS += """
/* Loadout tuning v0.4.6 */
QFrame#LoadoutSpecialTopBox {
    background: #18243b;
    border: 1px solid #314465;
    border-radius: 12px;
}
QLabel#LoadoutSpecialTopTotal {
    color: #ffd25e;
    font-weight: 900;
}
QLabel#PromotionReqIcon {
    background: #101827;
    border: 1px solid #3a4254;
    border-radius: 7px;
    padding: 2px;
}
QLabel#PromotionReqIconActive {
    background: #3b2e12;
    border: 1px solid #ffd25e;
    border-radius: 7px;
    padding: 2px;
}
"""

APP_QSS += """
/* Loadout compact width tuning v0.4.7 */
QListWidget#LoadoutBagGrid {
    padding: 6px;
}
QListWidget#LoadoutBagGrid::item {
    padding: 4px;
    margin: 2px;
}
QFrame#LoadoutDevice {
    border-radius: 24px;
}
QFrame#LoadoutDeviceScreen {
    border-radius: 13px;
}
QFrame#LoadoutSlotCellEmpty, QFrame#LoadoutSlotCellActive, QFrame#LoadoutSlotCellFilled, QFrame#LoadoutSlotCellMatched {
    border-radius: 7px;
}
"""

APP_QSS += """
/* Loadout bag grid fixed-card tuning v0.4.8 */
QListWidget#LoadoutBagGrid {
    background: #0f1728;
    padding: 5px;
}
QListWidget#LoadoutBagGrid::item {
    padding: 3px;
    margin: 1px;
}
QWidget#LoadoutBagGridViewport {
    background: #0f1728;
}
QScrollArea#LoadoutModuleScroll, QWidget#LoadoutModuleScrollViewport {
    background: #151d2f;
    border: none;
}
"""


APP_QSS += """
/* Loadout panel */
QFrame#LoadoutScannerPanel {
    background: #151d2f;
    border: 1px solid #314465;
    border-radius: 14px;
}
QFrame#LoadoutScannerPanel QPushButton {
    padding: 8px 9px;
}
QTableWidget {
    background: #0f1728;
    border: 1px solid #263653;
    border-radius: 10px;
    gridline-color: #263653;
}
QTableWidget::item {
    padding: 4px;
}
"""

APP_QSS += """
/* Settings */
QFrame#SettingsCard {
    background: #151d2f;
    border: 1px solid #263653;
    border-radius: 14px;
}
QLabel#SettingsAssetText {
    background: #0f1728;
    border: 1px solid #263653;
    border-radius: 10px;
    color: #dbe7ff;
    padding: 10px;
}
"""
