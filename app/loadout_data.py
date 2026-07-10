from __future__ import annotations

import json
import os
import re
import urllib.request
from functools import lru_cache
from pathlib import Path
from typing import Any

from app.paths import asset_path
from app.data import CHARACTER_ORDER, SLOT_LAYOUTS, SLOT_META, ELEMENT_LABELS

ARCHIVE_FILE = asset_path('datamine', 'archive-data.json')
MANUAL_PATCH_FILE = asset_path('datamine', 'everness_manual_patch.json')

QUALITY_CLASS = {
    'S급': 'orange',
    'A급': 'purple',
    'B급': 'blue',
}
QUALITY_ORDER = {'S급': 0, 'A급': 1, 'B급': 2}
RARITY_QUALITY = {5: 'S급', 4: 'A급', 3: 'B급'}

GEOMETRY_LABELS = {
    'Core': '카트리지',
    'Hen2': '가로 2',
    'Shu2': '세로 2',
    'Hen3': '가로 3',
    'Shu3': '세로 3',
    'ZhiJiao1': 'ㄴ 3',
    'ZhiJiao2': 'ㄱ 3',
    'ZhiJiao3': '┐ 3',
    'ZhiJiao4': '┘ 3',
    'Hen4': '가로 4',
    'Shu4': '세로 4',
    'Z3': 'Z 4',
    'Z4': 'S 4',
}

GEOMETRY_SHAPES = {
    'Hen2': ['11'],
    'Shu2': ['1', '1'],
    'Hen3': ['111'],
    'Shu3': ['1', '1', '1'],
    'ZhiJiao1': ['10', '11'],
    'ZhiJiao2': ['11', '10'],
    'ZhiJiao3': ['11', '01'],
    'ZhiJiao4': ['01', '11'],
    'Hen4': ['1111'],
    'Shu4': ['1', '1', '1', '1'],
    'Z3': ['011', '110'],
    'Z4': ['01', '11', '10'],
}

SLOT_EFFECTS = {
    'EquipmentSlots_Female': {'label': '공격력', 'value': 0.10},
    'EquipmentSlots_Mint': {'label': '치명 확률', 'value': 0.075},
    'EquipmentSlots_Sagiri': {'label': '주속성 이능력 피해', 'value': 0.09},
    'EquipmentSlots_Nanally': {'label': '치명 확률', 'value': 0.06},
    'EquipmentSlots_Adler': {'label': '방어력', 'value': 0.12},
    'EquipmentSlots_Fadia': {'label': 'HP', 'value': 0.06},
    'EquipmentSlots_lacrimosa': {'label': '암속성 이능력 피해', 'value': 0.10},
    'EquipmentSlots_skia': {'label': '공격력', 'value': 0.10},
    'EquipmentSlots_Jin': {'label': '빛속성 이능력 피해', 'value': 0.10},
    'EquipmentSlots_Hathor': {'label': '공격력', 'value': 0.10},
    'EquipmentSlots_Haniel': {'label': '공격력', 'value': 0.10},
    'EquipmentSlots_Cang': {'label': '치명 확률', 'value': 0.075},
    'EquipmentSlots_kuhara': {'label': '치명 확률', 'value': 0.06},
    'EquipmentSlots_edgar': {'label': 'HP', 'value': 0.10},
    'EquipmentSlots_daffodill': {'label': '암속성 이능력 피해', 'value': 0.10},
    'EquipmentSlots_chiichan': {'label': '빛속성 이능력 피해', 'value': 0.10},
    'EquipmentSlots_mitsuki': {'label': '공격력', 'value': 0.10},
}

ATTRIBUTE_LABELS = {
    'HPMaxBase': 'HP',
    'HPMaxAdd': 'HP',
    'HPMaxUp': 'HP',
    'AtkBase': '공격력',
    'AtkAdd': '공격력',
    'AtkUp': '공격력',
    'DefBase': '방어력',
    'DefAdd': '방어력',
    'DefUp': '방어력',
    'Crit': '치명 확률',
    'CritBase': '치명 확률',
    'CritDamage': '치명 피해',
    'CritDamageBase': '치명 피해',
    'HealUp': '치료 효율',
    'MagBase': '사이클 강도',
    'UnbalIntensityBase': '붕괴 강도',
    'DamageUpGeneralBase': '피해',
    'DamageUpGeneral': '피해',
    'DamageUpCosmos': '빛속성 이능력 피해',
    'DamageUpCosmosBase': '빛속성 이능력 피해',
    'DamageUpNature': '령속성 이능력 피해',
    'DamageUpNatureBase': '령속성 이능력 피해',
    'DamageUpIncantation': '주속성 이능력 피해',
    'DamageUpIncantationBase': '주속성 이능력 피해',
    'DamageUpChaos': '암속성 이능력 피해',
    'DamageUpChaosBase': '암속성 이능력 피해',
    'DamageUpPsyche': '혼속성 이능력 피해',
    'DamageUpPsycheBase': '혼속성 이능력 피해',
    'DamageUpLakshana': '상속성 이능력 피해',
    'DamageUpLakshanaBase': '상속성 이능력 피해',
    'DamageUpPsychicallyBase': '정신 피해',
}
PERCENT_ATTRIBUTE_IDS = {
    'AtkUp', 'DefUp', 'HPMaxUp', 'HealUp', 'Crit', 'CritBase',
    'CritDamage', 'CritDamageBase', 'DamageUpCosmos', 'DamageUpCosmosBase',
    'DamageUpNature', 'DamageUpNatureBase', 'DamageUpIncantation', 'DamageUpIncantationBase',
    'DamageUpChaos', 'DamageUpChaosBase', 'DamageUpPsyche', 'DamageUpPsycheBase',
    'DamageUpLakshana', 'DamageUpLakshanaBase', 'DamageUpPsychicallyBase',
    'DamageUpGeneralBase', 'DamageUpGeneral',
}
SUB_OPTION_IDS = [
    'AtkAdd', 'DefAdd', 'CritDamageBase', 'CritBase', 'AtkUp',
    'HPMaxAdd', 'HPMaxUp', 'DefUp', 'DamageUpGeneralBase',
    'MagBase', 'UnbalIntensityBase',
]

CARTRIDGE_SUB_VALUE_TEXT_BY_QUALITY = {
    'AtkAdd': {'B급': '48', 'A급': '64', 'S급': '80'},
    'HPMaxAdd': {'B급': '600', 'A급': '800', 'S급': '1000'},
    'DefAdd': {'B급': '48', 'A급': '64', 'S급': '80'},
    'AtkUp': {'B급': '7.50%', 'A급': '10.00%', 'S급': '12.50%'},
    'HPMaxUp': {'B급': '7.50%', 'A급': '10.00%', 'S급': '12.50%'},
    'DefUp': {'B급': '10.50%', 'A급': '14.00%', 'S급': '17.50%'},
    'CritDamageBase': {'B급': '12.00%', 'A급': '16.00%', 'S급': '20.00%'},
    'CritBase': {'B급': '6.00%', 'A급': '8.00%', 'S급': '10.00%'},
    'DamageUpGeneralBase': {'B급': '6.00%', 'A급': '8.00%', 'S급': '10.00%'},
    'MagBase': {'B급': '36', 'A급': '48', 'S급': '60'},
    'UnbalIntensityBase': {'B급': '36', 'A급': '48', 'S급': '60'},
}
QUALITY_VALUE_MULTIPLIER = {'B급': 0.6, 'A급': 0.8, 'S급': 1.0}
DRIVE_GRID_VALUE_MULTIPLIER = {2: 1.0, 3: 1.5, 4: 2.0}
S_GRADE_TYPE_II_DRIVE_SUB_VALUES = {
    'AtkAdd': 16,
    'HPMaxAdd': 200,
    'DefAdd': 16,
    'AtkUp': 0.025,
    'HPMaxUp': 0.025,
    'DefUp': 0.035,
    'CritDamageBase': 0.04,
    'CritBase': 0.02,
    'DamageUpGeneralBase': 0.02,
    'MagBase': 12,
    'UnbalIntensityBase': 12,
}

CARTRIDGE_MAIN_OPTIONS = [
    {'id': 'AtkUp', 'values': {'B급': 0.225, 'A급': 0.3, 'S급': 0.375}},
    {'id': 'HPMaxUp', 'values': {'B급': 0.225, 'A급': 0.3, 'S급': 0.375}},
    {'id': 'DefUp', 'values': {'B급': 0.315, 'A급': 0.42, 'S급': 0.525}},
    {'id': 'CritBase', 'values': {'B급': 0.18, 'A급': 0.24, 'S급': 0.3}},
    {'id': 'CritDamageBase', 'values': {'B급': 0.36, 'A급': 0.48, 'S급': 0.6}},
    {'id': 'HealUp', 'values': {'B급': 0.207, 'A급': 0.276, 'S급': 0.345}},
    {'id': 'MagBase', 'values': {'B급': 108, 'A급': 144, 'S급': 180}},
    {'id': 'UnbalIntensityBase', 'values': {'B급': 108, 'A급': 144, 'S급': 180}},
    {'id': 'DamageUpCosmosBase', 'values': {'B급': 0.225, 'A급': 0.3, 'S급': 0.375}},
    {'id': 'DamageUpNatureBase', 'values': {'B급': 0.225, 'A급': 0.3, 'S급': 0.375}},
    {'id': 'DamageUpIncantationBase', 'values': {'B급': 0.225, 'A급': 0.3, 'S급': 0.375}},
    {'id': 'DamageUpChaosBase', 'values': {'B급': 0.225, 'A급': 0.3, 'S급': 0.375}},
    {'id': 'DamageUpPsycheBase', 'values': {'B급': 0.225, 'A급': 0.3, 'S급': 0.375}},
    {'id': 'DamageUpLakshanaBase', 'values': {'B급': 0.225, 'A급': 0.3, 'S급': 0.375}},
    {'id': 'DamageUpPsychicallyBase', 'values': {'B급': 0.225, 'A급': 0.3, 'S급': 0.375}},
]
CARTRIDGE_SUB_OPTIONS = [{'id': option_id} for option_id in SUB_OPTION_IDS]
DRIVE_SUB_OPTIONS = [{'id': option_id} for option_id in SUB_OPTION_IDS]
DRIVE_FIXED_MAIN_OPTIONS = ['AtkAdd', 'HPMaxAdd']
DRIVE_MAIN_ATTRIBUTE_VALUES = {
    2: {
        'AtkAdd': {'B급': 25, 'A급': 34, 'S급': 42},
        'HPMaxAdd': {'B급': 336, 'A급': 448, 'S급': 560},
    },
    3: {
        'AtkAdd': {'B급': 38, 'A급': 50, 'S급': 63},
        'HPMaxAdd': {'B급': 504, 'A급': 672, 'S급': 840},
    },
    4: {
        'AtkAdd': {'B급': 50, 'A급': 67, 'S급': 84},
        'HPMaxAdd': {'B급': 672, 'A급': 896, 'S급': 1120},
    },
}

DEFAULT_CARTRIDGE_ATTRIBUTES = {
    'main': CARTRIDGE_MAIN_OPTIONS[0]['id'],
    'subs': [option['id'] for option in CARTRIDGE_SUB_OPTIONS[:4]],
}
DEFAULT_DRIVE_ATTRIBUTES = {
    'subs': [option['id'] for option in DRIVE_SUB_OPTIONS[:4]],
}


def roman_grid(grid_count: int) -> str:
    return {2: 'Ⅱ', 3: 'Ⅲ', 4: 'Ⅳ'}.get(int(grid_count or 0), str(grid_count))


def normalize_name(name: str | None) -> str:
    return re.sub(r'^[「]|[」]$', '', name or '')


def quality_class(quality: str | None) -> str:
    return QUALITY_CLASS.get(quality or '', 'blue')


def quality_from_rarity(rarity: int | str | None) -> str:
    try:
        return RARITY_QUALITY.get(int(rarity), 'B급')
    except Exception:
        return 'B급'


def format_percent(value: float | int) -> str:
    percent = float(value) * 100
    if abs(percent - round(percent)) < 1e-9:
        return f'{round(percent)}%'
    return f'{percent:.1f}%'


def get_attribute_label(attribute_id: str) -> str:
    return ATTRIBUTE_LABELS.get(attribute_id, attribute_id)


def format_attribute_value(attribute_id: str, value: Any) -> str:
    if value is None:
        return ''
    if attribute_id in PERCENT_ATTRIBUTE_IDS:
        percent = float(value) * 100
        return f'{percent:.0f}%' if abs(percent - round(percent)) < 1e-9 else f'{percent:.1f}%'
    return str(int(value)) if isinstance(value, (int, float)) and float(value).is_integer() else str(value)


def drive_sub_value_text(attribute_id: str, grid_count: int, quality: str) -> str:
    base = S_GRADE_TYPE_II_DRIVE_SUB_VALUES.get(attribute_id)
    if base is None:
        return ''
    value = base * DRIVE_GRID_VALUE_MULTIPLIER.get(int(grid_count or 2), 1) * QUALITY_VALUE_MULTIPLIER.get(quality, 1)
    if attribute_id in PERCENT_ATTRIBUTE_IDS:
        return f'{value * 100:.2f}%'
    return str(round(value))


def format_option(option_id: str, quality: str, context: dict[str, Any] | None = None) -> str:
    context = context or {}
    value_text = ''
    if context.get('kind') == 'cartridge_sub':
        value_text = CARTRIDGE_SUB_VALUE_TEXT_BY_QUALITY.get(option_id, {}).get(quality, '')
    elif context.get('kind') == 'drive_sub':
        value_text = drive_sub_value_text(option_id, int(context.get('grid_count') or 2), quality)
    elif context.get('kind') == 'drive_main':
        value = DRIVE_MAIN_ATTRIBUTE_VALUES.get(int(context.get('grid_count') or 2), {}).get(option_id, {}).get(quality)
        value_text = format_attribute_value(option_id, value)
    else:
        option = next((it for it in CARTRIDGE_MAIN_OPTIONS if it['id'] == option_id), None)
        if option:
            value_text = format_attribute_value(option_id, option.get('values', {}).get(quality))
    return f'{get_attribute_label(option_id)}{f" +{value_text}" if value_text else ""}'


def get_shape_rows(geometry: str) -> list[str]:
    return GEOMETRY_SHAPES.get(geometry, ['1'])


def get_shape_cells(geometry: str) -> list[tuple[int, int]]:
    cells: list[tuple[int, int]] = []
    for row_i, row in enumerate(get_shape_rows(geometry)):
        for col_i, ch in enumerate(row):
            if ch == '1':
                cells.append((row_i, col_i))
    return cells


def geometry_cell_count(geometry: str) -> int:
    return len(get_shape_cells(geometry))



def _app_cache_dir() -> Path:
    base = Path(os.environ.get('APPDATA') or Path.home()) / 'NTE Tool' / 'asset_cache'
    base.mkdir(parents=True, exist_ok=True)
    return base


def _download_cached_asset(url: str | None, filename: str | None = None) -> Path | None:
    if not url:
        return None
    safe_name = filename or str(url).rstrip('/').split('/')[-1]
    if not safe_name:
        return None
    target = _app_cache_dir() / safe_name
    if target.exists() and target.stat().st_size > 0:
        return target
    try:
        req = urllib.request.Request(str(url), headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=8) as response:
            target.write_bytes(response.read())
        return target if target.exists() and target.stat().st_size > 0 else None
    except Exception:
        return None


def load_manual_patch() -> dict[str, Any]:
    try:
        if MANUAL_PATCH_FILE.exists():
            with open(MANUAL_PATCH_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
    except Exception:
        pass
    return {'characters': [], 'arks': [], 'cafeEmployees': []}


def _merge_by_id(base_items: list[dict[str, Any]], patch_items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    existing = {str(item.get('id')) for item in base_items}
    merged = list(base_items)
    for item in patch_items or []:
        if str(item.get('id')) not in existing:
            merged.append(dict(item))
            existing.add(str(item.get('id')))
    return merged


def apply_manual_patch(archive: dict[str, Any]) -> dict[str, Any]:
    patch = load_manual_patch()
    archive = dict(archive)
    archive['characters'] = _merge_by_id(list(archive.get('characters') or []), list(patch.get('characters') or []))
    archive['arks'] = _merge_by_id(list(archive.get('arks') or []), list(patch.get('arks') or []))
    return archive

def module_image_path(item: dict[str, Any] | None, prefer_icon: bool = False) -> Path | None:
    if not item:
        return None
    rel = item.get('icon') if prefer_icon and item.get('icon') else item.get('image') or item.get('icon')
    if rel:
        local = asset_path(*str(rel).lstrip('/').split('/'))
        if local.exists():
            return local
    remote = item.get('remoteIcon') if prefer_icon and item.get('remoteIcon') else item.get('remoteImage') or item.get('remoteIcon')
    cached = _download_cached_asset(remote, f"{item.get('id', 'remote')}-icon.webp" if prefer_icon else f"{item.get('id', 'remote')}.webp")
    if cached:
        return cached
    if rel:
        return asset_path(*str(rel).lstrip('/').split('/'))
    return None


def character_avatar_path(character: dict[str, Any] | None) -> Path | None:
    if not character:
        return None
    local = asset_path('datamine', 'characters', f"{character.get('id')}-avatar.webp")
    if local.exists():
        return local
    cached = _download_cached_asset(character.get('remoteImage'), f"{character.get('id')}-avatar.webp")
    return cached or local


@lru_cache(maxsize=1)
def load_archive() -> dict[str, Any]:
    with open(ARCHIVE_FILE, 'r', encoding='utf-8') as f:
        return json.load(f)


def _sort_quality_name(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return sorted(items, key=lambda item: (QUALITY_ORDER.get(item.get('quality', ''), 9), normalize_name(item.get('name'))))


_archive = apply_manual_patch(load_archive())
_BASE_ORDER = list(CHARACTER_ORDER)
_by_char_id = {str(item.get('id')): item for item in _archive.get('characters', [])}
CHARACTERS = [_by_char_id[cid] for cid in _BASE_ORDER if cid in _by_char_id]
CHARACTERS.extend(item for cid, item in _by_char_id.items() if cid not in _BASE_ORDER)
ARCS = _sort_quality_name([dict(item) for item in _archive.get('arks', [])])
CARTRIDGES = _sort_quality_name([dict(item) for item in _archive.get('cartridges', [])])
DRIVE_MODULES = _sort_quality_name([dict(item) for item in _archive.get('consoles', [])])

# User-maintained recommendations.  Characters absent from this table have no
# confirmed recommendation and deliberately keep the normal archive ordering.
ARK_RECOMMENDATION_NAMES = {
    '제로': ('휴일', '잊힌 자'),
    '나나리': ('준비, 준비', '오라오라!'),
    '구원': ('현실 도피처', '잊힌 자'),
    '백장': ('동백꽃 모임', '때는 온다'),
    '다포딜': ('암흑 청춘의 망상', '빛나는 나날'),
    '파디아': ('영원한 왈츠', '입에 쓴 약이 몸에 좋다'),
    '하토르': ('염혼의 질주', '발도'),
    '사키리': ('착한 강아지의 여행', '말하기 어려운 마음'),
    '치즈': ('생각하는 고양이', '화려한 조명 속 광란의 파티'),
    '민트': ('정화 개시', '빛나는 나날'),
    '아들러': ('물망산', '봄을 심는 바보'),
    '하니엘': ('폭발 현장', '시간 도둑'),
    '스키아': ('머리 조심', '화려한 조명 속 광란의 파티'),
    '에드가': ('뒤틀린 도시의 부름', '영감 배틀로얄'),
    '우미츠키': ('「은하의 찰나」', '오라오라!'),
    '호토리': ('시간 밖으로의 행진', '잊힌 자'),
    '라크리모사': ('「마지막 장미」', '빛나는 나날'),
    '카오스': ('만인의 갈망', '때는 온다'),
    '신쿠': ('홍염의 신기루', '때는 온다'),
}
_ark_id_by_name = {normalize_name(item.get('name')): item['id'] for item in ARCS}
ARK_RECOMMENDATIONS = {
    character: tuple(
        _ark_id_by_name[normalize_name(name)]
        for name in names
        if normalize_name(name) in _ark_id_by_name
    )
    for character, names in ARK_RECOMMENDATION_NAMES.items()
}

# Keep a fast index for selections.
CHARACTER_BY_ID = {str(item['id']): item for item in CHARACTERS}
ARK_BY_ID = {item['id']: item for item in ARCS}
CARTRIDGE_BY_ID = {item['id']: item for item in CARTRIDGES}
DRIVE_MODULE_BY_ID = {item['id']: item for item in DRIVE_MODULES}


def default_character() -> dict[str, Any]:
    return CHARACTERS[0]


def preferred_cartridge(character: dict[str, Any]) -> dict[str, Any] | None:
    element = character.get('element') or ''
    return (
        next((item for item in CARTRIDGES if item.get('id') == f'{element}_orange'), None)
        or next((item for item in CARTRIDGES if str(item.get('id', '')).startswith(f'{element}_')), None)
        or (CARTRIDGES[0] if CARTRIDGES else None)
    )


def preferred_module(owner_grid_count: int, quality: str = 'S급') -> dict[str, Any] | None:
    prefix = f'cell{owner_grid_count}_'
    return (
        next((item for item in DRIVE_MODULES if str(item.get('id', '')).startswith(prefix) and item.get('quality') == quality), None)
        or next((item for item in DRIVE_MODULES if str(item.get('id', '')).startswith(prefix)), None)
        or (DRIVE_MODULES[0] if DRIVE_MODULES else None)
    )


def slot_rows_for_character(character_id: str | int) -> list[str]:
    return SLOT_LAYOUTS.get(int(character_id), SLOT_LAYOUTS['default'])


def slot_meta_for_character(character_id: str | int) -> dict[str, Any]:
    return SLOT_META.get(int(character_id), SLOT_META['default'])


def trim_slot_matrix(rows: list[str]) -> dict[str, Any]:
    matrix = [[int(v) for v in row.split(',')] for row in rows]
    active = [(r, c) for r, row in enumerate(matrix) for c, cell in enumerate(row) if cell != -1]
    if not active:
        return {'rows': [], 'active_set': set(), 'active_count': 0, 'row_count': 0, 'col_count': 0}
    min_r, max_r = min(r for r, _ in active), max(r for r, _ in active)
    min_c, max_c = min(c for _, c in active), max(c for _, c in active)
    trimmed = [row[min_c:max_c + 1] for row in matrix[min_r:max_r + 1]]
    active_set = {(r, c) for r, row in enumerate(trimmed) for c, cell in enumerate(row) if cell != -1}
    return {
        'rows': trimmed,
        'active_set': active_set,
        'active_count': len(active_set),
        'row_count': len(trimmed),
        'col_count': len(trimmed[0]) if trimmed else 0,
    }


def resolve_module_placement(geometry: str, target: tuple[int, int], slot_layout: dict[str, Any], occupied: dict[tuple[int, int], str]) -> dict[str, Any]:
    shape_cells = get_shape_cells(geometry)
    candidates = []
    active_set = slot_layout['active_set']
    for anchor_r, anchor_c in shape_cells:
        origin = (target[0] - anchor_r, target[1] - anchor_c)
        cells = [(origin[0] + r, origin[1] + c) for r, c in shape_cells]
        is_valid = all(cell in active_set and cell not in occupied for cell in cells)
        score = 0
        for cell in cells:
            r, c = cell
            if not (0 <= r < slot_layout['row_count'] and 0 <= c < slot_layout['col_count']):
                continue
            if cell not in active_set:
                score += 1
            elif cell in occupied:
                score += 2
            else:
                score += 4
        candidates.append({'origin': origin, 'cells': cells, 'is_valid': is_valid, 'score': score})
    valid = next((candidate for candidate in candidates if candidate['is_valid']), None)
    if valid:
        return valid
    return max(candidates, key=lambda c: c['score']) if candidates else {'origin': target, 'cells': [], 'is_valid': False, 'score': 0}


def get_drive_main_stats(module: dict[str, Any], grid_count: int) -> list[dict[str, Any]]:
    return [
        {'id': attribute_id, 'value': DRIVE_MAIN_ATTRIBUTE_VALUES.get(grid_count, {}).get(attribute_id, {}).get(module.get('quality'))}
        for attribute_id in DRIVE_FIXED_MAIN_OPTIONS
    ]


def build_promotion_progress(promotion: dict[str, Any] | None, placements: list[dict[str, Any]]) -> dict[str, Any]:
    requirements = list((promotion or {}).get('requirements') or [])
    required_counts: dict[str, int] = {}
    for geometry in requirements:
        required_counts[geometry] = required_counts.get(geometry, 0) + 1
    used_counts: dict[str, int] = {}
    matched_ids: set[str] = set()
    for placement in placements:
        geometry = placement.get('module', {}).get('geometry')
        required_count = required_counts.get(geometry, 0)
        used_count = used_counts.get(geometry, 0)
        if used_count >= required_count:
            continue
        used_counts[geometry] = used_count + 1
        matched_ids.add(placement['id'])
    matched_count = sum(used_counts.values())
    requirement_status = []
    for index, geometry in enumerate(requirements):
        previous_same_count = requirements[:index].count(geometry)
        requirement_status.append({
            'geometry': geometry,
            'active': previous_same_count < used_counts.get(geometry, 0),
        })
    return {
        'requirements': requirements,
        'requirement_status': requirement_status,
        'matched_ids': matched_ids,
        'matched_count': matched_count,
        'total_count': len(requirements),
        'active_effects': [effect for effect in (promotion or {}).get('effects', []) if int(effect.get('condition', 0)) <= matched_count],
    }


def aggregate_attribute_lines(cartridge: dict[str, Any] | None, cartridge_attrs: dict[str, Any], placements: list[dict[str, Any]]) -> list[str]:
    lines: list[str] = []
    if cartridge:
        quality = cartridge.get('quality', 'S급')
        lines.append('카트리지 주옵: ' + format_option(cartridge_attrs.get('main', DEFAULT_CARTRIDGE_ATTRIBUTES['main']), quality))
        subs = cartridge_attrs.get('subs', DEFAULT_CARTRIDGE_ATTRIBUTES['subs'])
        if subs:
            lines.append('카트리지 부옵: ' + ' / '.join(format_option(item, quality, {'kind': 'cartridge_sub'}) for item in subs))
    if placements:
        main_counts: dict[str, float] = {}
        sub_counts: dict[str, int] = {}
        for placement in placements:
            module = placement.get('module', {})
            grid_count = geometry_cell_count(module.get('geometry', ''))
            quality = module.get('quality', 'S급')
            for stat in get_drive_main_stats(module, grid_count):
                if stat.get('value') is not None:
                    main_counts[stat['id']] = main_counts.get(stat['id'], 0) + stat['value']
            for sub in placement.get('attributes', {}).get('subs', []):
                sub_counts[sub] = sub_counts.get(sub, 0) + 1
        if main_counts:
            lines.append('드라이브 주옵 합계: ' + ' / '.join(
                f'{get_attribute_label(k)} +{format_attribute_value(k, v)}' for k, v in main_counts.items()
            ))
        if sub_counts:
            lines.append('드라이브 부옵 수: ' + ' / '.join(f'{get_attribute_label(k)}×{v}' for k, v in sub_counts.items()))
    return lines or ['아직 장착된 드라이브 모듈이 없습니다.']


# ---------------------------------------------------------------------------
# Final stat calculator
#
# Builder-compatible display target:
# - Basic stats use base flat + additive flat + percent bonuses.
# - Percentage options are stored as decimal ratios internally.
# - DamageUpGeneral is displayed as "통용 피해 증강".
# - Missing stat categories are still shown as 0 so the final spec dialog always
#   matches the full builder stat list.

FINAL_BASIC_STATS = [
    ('HPMax', 'HP'),
    ('Atk', '공격력'),
    ('Def', '방어력'),
    ('Stamina', '체력'),
]

FINAL_ENHANCED_STATS = [
    ('Crit', '치명 확률'),
    ('CritDamage', '치명 피해'),
    ('ChargeGetEfficiency', '에너지 충전 효율'),
    ('Mag', '사이클 강도'),
    ('UnbalIntensity', '붕괴 강도'),
    ('HealUp', '치료 보너스'),
    ('HealReceiveUp', '받는 치료 보너스'),
    ('DamageUpGeneral', '통용 피해 증강'),
    ('DamageUpCosmos', '빛속성 이능력 피해 증강'),
    ('DamageUpNature', '령속성 이능력 피해 증강'),
    ('DamageUpIncantation', '주속성 이능력 피해 증강'),
    ('DamageUpChaos', '암속성 이능력 피해 증강'),
    ('DamageUpPsyche', '혼속성 이능력 피해 증강'),
    ('DamageUpLakshana', '상속성 이능력 피해 증강'),
    ('DamageUpPsychically', '정신 피해 증강'),
    ('DamageResCosmos', '빛속성 이능력 피해 저항'),
    ('DamageResNature', '령속성 이능력 피해 저항'),
    ('DamageResIncantation', '주속성 이능력 피해 저항'),
    ('DamageResChaos', '암속성 이능력 피해 저항'),
    ('DamageResPsyche', '혼속성 이능력 피해 저항'),
    ('DamageResLakshana', '상속성 이능력 피해 저항'),
    ('DamageResPsychically', '정신 피해 저항'),
]

FINAL_ID_MAP = {
    'HPMaxBase': 'HPMaxBase',
    'HPMaxAdd': 'HPMaxFlat',
    'HPMaxUp': 'HPMaxPercent',
    'AtkBase': 'AtkBase',
    'AtkAdd': 'AtkFlat',
    'AtkUp': 'AtkPercent',
    'DefBase': 'DefBase',
    'DefAdd': 'DefFlat',
    'DefUp': 'DefPercent',
    'StaminaBase': 'StaminaBase',
    'StaminaAdd': 'StaminaFlat',
    'StaminaUp': 'StaminaPercent',
    'Crit': 'Crit',
    'CritBase': 'Crit',
    'CritDamage': 'CritDamage',
    'CritDamageBase': 'CritDamage',
    'ChargeGetEfficiency': 'ChargeGetEfficiency',
    'ChargeGetEfficiencyBase': 'ChargeGetEfficiency',
    'MagBase': 'Mag',
    'Mag': 'Mag',
    'UnbalIntensityBase': 'UnbalIntensity',
    'UnbalIntensity': 'UnbalIntensity',
    'HealUp': 'HealUp',
    'HealUpBase': 'HealUp',
    'HealReceiveUp': 'HealReceiveUp',
    'HealReceiveUpBase': 'HealReceiveUp',
    'DamageUpGeneral': 'DamageUpGeneral',
    'DamageUpGeneralBase': 'DamageUpGeneral',
    'DamageUpCosmos': 'DamageUpCosmos',
    'DamageUpCosmosBase': 'DamageUpCosmos',
    'DamageUpNature': 'DamageUpNature',
    'DamageUpNatureBase': 'DamageUpNature',
    'DamageUpIncantation': 'DamageUpIncantation',
    'DamageUpIncantationBase': 'DamageUpIncantation',
    'DamageUpChaos': 'DamageUpChaos',
    'DamageUpChaosBase': 'DamageUpChaos',
    'DamageUpPsyche': 'DamageUpPsyche',
    'DamageUpPsycheBase': 'DamageUpPsyche',
    'DamageUpLakshana': 'DamageUpLakshana',
    'DamageUpLakshanaBase': 'DamageUpLakshana',
    'DamageUpPsychically': 'DamageUpPsychically',
    'DamageUpPsychicallyBase': 'DamageUpPsychically',
    'DamageResCosmos': 'DamageResCosmos',
    'DamageResCosmosBase': 'DamageResCosmos',
    'DamageResNature': 'DamageResNature',
    'DamageResNatureBase': 'DamageResNature',
    'DamageResIncantation': 'DamageResIncantation',
    'DamageResIncantationBase': 'DamageResIncantation',
    'DamageResChaos': 'DamageResChaos',
    'DamageResChaosBase': 'DamageResChaos',
    'DamageResPsyche': 'DamageResPsyche',
    'DamageResPsycheBase': 'DamageResPsyche',
    'DamageResLakshana': 'DamageResLakshana',
    'DamageResLakshanaBase': 'DamageResLakshana',
    'DamageResPsychically': 'DamageResPsychically',
    'DamageResPsychicallyBase': 'DamageResPsychically',
}

TEXT_STAT_MAP = {
    'HP': 'HPMaxPercent',
    '공격력': 'AtkPercent',
    '방어력': 'DefPercent',
    '치명 확률': 'Crit',
    '치명 피해': 'CritDamage',
    '에너지 충전 효율': 'ChargeGetEfficiency',
    '사이클 강도': 'Mag',
    '붕괴 강도': 'UnbalIntensity',
    '치료 보너스': 'HealUp',
    '치료 효율': 'HealUp',
    '받는 치료 보너스': 'HealReceiveUp',
    '통용 피해 증강': 'DamageUpGeneral',
    '피해': 'DamageUpGeneral',
    '빛속성 이능력 피해': 'DamageUpCosmos',
    '령속성 이능력 피해': 'DamageUpNature',
    '주속성 이능력 피해': 'DamageUpIncantation',
    '암속성 이능력 피해': 'DamageUpChaos',
    '혼속성 이능력 피해': 'DamageUpPsyche',
    '상속성 이능력 피해': 'DamageUpLakshana',
    '정신 피해': 'DamageUpPsychically',
    '빛속성 이능력 피해 저항': 'DamageResCosmos',
    '령속성 이능력 피해 저항': 'DamageResNature',
    '주속성 이능력 피해 저항': 'DamageResIncantation',
    '암속성 이능력 피해 저항': 'DamageResChaos',
    '혼속성 이능력 피해 저항': 'DamageResPsyche',
    '상속성 이능력 피해 저항': 'DamageResLakshana',
    '정신 피해 저항': 'DamageResPsychically',
}


def _parse_stat_number(value: Any) -> float:
    if value is None:
        return 0.0
    text = str(value).strip().replace(',', '')
    if not text:
        return 0.0
    is_percent = '%' in text
    text = text.replace('%', '')
    try:
        number = float(text)
    except Exception:
        return 0.0
    return number / 100.0 if is_percent else number


def _last_main_stat_value(stat: dict[str, Any]) -> float:
    values = list(stat.get('values') or [])
    if not values:
        return 0.0
    return _parse_stat_number(values[-1])


def _new_final_totals() -> dict[str, Any]:
    return {
        'basic': {key: {'base': 0.0, 'flat': 0.0, 'percent': 0.0, 'total': 0.0} for key, _ in FINAL_BASIC_STATS},
        'enhanced': {key: 0.0 for key, _ in FINAL_ENHANCED_STATS},
        'sources': [],
    }


def _add_final_value(totals: dict[str, Any], mapped_id: str | None, value: float, source: str = ''):
    if not mapped_id or value is None:
        return
    basic = totals['basic']
    enhanced = totals['enhanced']
    if mapped_id.endswith('Base'):
        key = mapped_id[:-4]
        if key in basic:
            basic[key]['base'] += value
            return
    if mapped_id.endswith('Flat'):
        key = mapped_id[:-4]
        if key in basic:
            basic[key]['flat'] += value
            return
    if mapped_id.endswith('Percent'):
        key = mapped_id[:-7]
        if key in basic:
            basic[key]['percent'] += value
            return
    if mapped_id in enhanced:
        enhanced[mapped_id] += value
        return


def _add_stat_id_value(totals: dict[str, Any], stat_id: str | None, value: float, source: str = ''):
    _add_final_value(totals, FINAL_ID_MAP.get(stat_id or ''), value, source)


def _option_value(option_id: str, quality: str, context: dict[str, Any] | None = None) -> float:
    context = context or {}
    if context.get('kind') == 'cartridge_sub':
        raw = CARTRIDGE_SUB_VALUE_TEXT_BY_QUALITY.get(option_id, {}).get(quality)
        return _parse_stat_number(raw)
    if context.get('kind') == 'drive_sub':
        raw = drive_sub_value_text(option_id, int(context.get('grid_count') or 2), quality)
        return _parse_stat_number(raw)
    if context.get('kind') == 'drive_main':
        return float(DRIVE_MAIN_ATTRIBUTE_VALUES.get(int(context.get('grid_count') or 2), {}).get(option_id, {}).get(quality) or 0)
    option = next((it for it in CARTRIDGE_MAIN_OPTIONS if it['id'] == option_id), None)
    if option:
        return float(option.get('values', {}).get(quality) or 0)
    return 0.0


def _add_item_main_stats(totals: dict[str, Any], item: dict[str, Any] | None):
    if not item:
        return
    for stat in item.get('mainStats', {}).get('stats', []) or []:
        _add_stat_id_value(totals, stat.get('id'), _last_main_stat_value(stat), 'mainStats')


def _add_cartridge_stats(totals: dict[str, Any], cartridge: dict[str, Any] | None, cartridge_attrs: dict[str, Any]):
    if not cartridge:
        return
    quality = cartridge.get('quality') or 'S급'
    main_id = cartridge_attrs.get('main') or DEFAULT_CARTRIDGE_ATTRIBUTES['main']
    _add_stat_id_value(totals, main_id, _option_value(main_id, quality), 'cartridge main')
    for sub_id in list(cartridge_attrs.get('subs') or DEFAULT_CARTRIDGE_ATTRIBUTES['subs'])[:4]:
        _add_stat_id_value(totals, sub_id, _option_value(sub_id, quality, {'kind': 'cartridge_sub'}), 'cartridge sub')


def _add_drive_stats(totals: dict[str, Any], placements: list[dict[str, Any]]):
    for placement in placements or []:
        module = placement.get('module') or {}
        quality = module.get('quality') or 'S급'
        grid_count = geometry_cell_count(module.get('geometry') or '')
        for stat in get_drive_main_stats(module, grid_count):
            _add_stat_id_value(totals, stat.get('id'), float(stat.get('value') or 0), 'drive main')
        for sub_id in list(placement.get('attributes', {}).get('subs') or [])[:4]:
            _add_stat_id_value(totals, sub_id, _option_value(sub_id, quality, {'kind': 'drive_sub', 'grid_count': grid_count}), 'drive sub')


def _add_slot_special(totals: dict[str, Any], character_id: str | int, placements: list[dict[str, Any]]):
    meta = slot_meta_for_character(character_id)
    owner_grid_count = int(meta.get('owner_grid_count', 3))
    matching_count = sum(1 for placement in placements or [] if geometry_cell_count(placement.get('module', {}).get('geometry')) == owner_grid_count)
    effect = SLOT_EFFECTS.get(meta.get('slot_id'))
    if not effect:
        return
    label = effect.get('label') or ''
    value = matching_count * float(effect.get('value') or 0)
    _add_final_value(totals, TEXT_STAT_MAP.get(label), value, 'slot special')


def _add_active_promotion_effects(totals: dict[str, Any], active_effects: list[dict[str, Any]]):
    # Only parse simple visible stat fragments. Conditional text may include the
    # same fragment; it is still displayed in a separate note in the dialog.
    for effect in active_effects or []:
        text = (effect.get('description') or '')
        for label, mapped in sorted(TEXT_STAT_MAP.items(), key=lambda it: len(it[0]), reverse=True):
            if label in ('HP', '공격력', '방어력'):
                continue
            pattern = re.escape(label) + r'\s*\+\s*([0-9]+(?:\.[0-9]+)?)\s*%'
            for match in re.finditer(pattern, text):
                _add_final_value(totals, mapped, float(match.group(1)) / 100.0, 'promotion')


def calculate_final_stats(
    character: dict[str, Any] | None,
    ark: dict[str, Any] | None,
    cartridge: dict[str, Any] | None,
    cartridge_attrs: dict[str, Any],
    placements: list[dict[str, Any]],
    active_effects: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    totals = _new_final_totals()
    _add_item_main_stats(totals, character)
    _add_item_main_stats(totals, ark)
    _add_cartridge_stats(totals, cartridge, cartridge_attrs)
    _add_drive_stats(totals, placements)
    if character:
        _add_slot_special(totals, character.get('id'), placements)
    _add_active_promotion_effects(totals, active_effects or [])

    for key, row in totals['basic'].items():
        # Everness builder-style additive formula:
        # final = (character base + arc base) * (1 + percent bonuses) + flat bonuses
        row['total'] = row['base'] * (1.0 + row['percent']) + row['flat']
    return totals


def _fmt_flat(value: float) -> str:
    if abs(value) < 1e-9:
        value = 0.0
    if abs(value - round(value)) < 1e-9:
        return f'{int(round(value)):,}'
    return f'{value:,.1f}'


def _fmt_ratio(value: float) -> str:
    if abs(value) < 1e-9:
        value = 0.0
    percent = value * 100.0
    if abs(percent - round(percent)) < 1e-9:
        return f'{int(round(percent))}%'
    return f'{percent:.1f}%'


def build_final_stat_lines(
    character: dict[str, Any] | None,
    ark: dict[str, Any] | None,
    cartridge: dict[str, Any] | None,
    cartridge_attrs: dict[str, Any],
    placements: list[dict[str, Any]],
    active_effects: list[dict[str, Any]] | None = None,
) -> list[str]:
    totals = calculate_final_stats(character, ark, cartridge, cartridge_attrs, placements, active_effects)
    lines: list[str] = []
    lines.append('[기본 속성]')
    for key, label in FINAL_BASIC_STATS:
        row = totals['basic'][key]
        if key in ('HPMax', 'Atk', 'Def'):
            details = []
            if row['base']:
                details.append(f"기초 {_fmt_flat(row['base'])}")
            if row['percent']:
                details.append(f"%보너스 {_fmt_ratio(row['percent'])}")
            if row['flat']:
                details.append(f"고정 +{_fmt_flat(row['flat'])}")
            suffix = f" ({' / '.join(details)})" if details else ''
            lines.append(f'{label}: {_fmt_flat(row["total"])}{suffix}')
        else:
            lines.append(f'{label}: {_fmt_flat(row["total"])}')
    lines.append('')
    lines.append('[강화 속성]')
    for key, label in FINAL_ENHANCED_STATS:
        lines.append(f'{label}: {_fmt_ratio(totals["enhanced"].get(key, 0.0))}')
    return lines
