from __future__ import annotations

import json
import os
import re
import subprocess
import tempfile
from dataclasses import dataclass
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any

from app.scanner.tesseract_locator import locate_tesseract


POSTPROCESS_RULE_PATH = Path(__file__).with_name('ocr_postprocess_rules.json')
_POSTPROCESS_RULES_CACHE: dict[str, Any] | None = None


def load_postprocess_rules() -> dict[str, Any]:
    global _POSTPROCESS_RULES_CACHE
    if _POSTPROCESS_RULES_CACHE is not None:
        return _POSTPROCESS_RULES_CACHE
    try:
        with POSTPROCESS_RULE_PATH.open('r', encoding='utf-8') as fp:
            data = json.load(fp)
        if not isinstance(data, dict):
            data = {}
    except Exception:
        data = {}
    _POSTPROCESS_RULES_CACHE = data
    return data


def external_replacements() -> dict[str, str]:
    rules = load_postprocess_rules()
    replacements = rules.get('replacements') or {}
    return {str(k): str(v) for k, v in replacements.items()}

from app.loadout_data import (
    CARTRIDGES,
    CARTRIDGE_MAIN_OPTIONS,
    CARTRIDGE_SUB_OPTIONS,
    DRIVE_FIXED_MAIN_OPTIONS,
    DRIVE_MODULES,
    DRIVE_SUB_OPTIONS,
    GEOMETRY_LABELS,
    get_attribute_label,
    normalize_name,
)


QUALITY_ALIASES = {
    'S급': ['S급', 'S 급', 'S', 'SR', '橙'],
    'A급': ['A급', 'A 급', 'A', '紫'],
    'B급': ['B급', 'B 급', 'B', '蓝', '藍'],
}

GEOMETRY_ALIASES = {
    'Hen2': ['가로 2', '가로2', '横 2', '横2', '2칸 가로', 'II형', 'Ⅱ형'],
    'Shu2': ['세로 2', '세로2', '竖 2', '竖2', '2칸 세로', 'II형', 'Ⅱ형'],
    'Hen3': ['가로 3', '가로3', '横 3', '横3', '3칸 가로', 'III형', 'Ⅲ형'],
    'Shu3': ['세로 3', '세로3', '竖 3', '竖3', '3칸 세로', 'III형', 'Ⅲ형'],
    'ZhiJiao1': ['ㄴ 3', 'L 3', 'L형', 'ㄴ형'],
    'ZhiJiao2': ['ㄱ 3', 'ㄱ형'],
    'ZhiJiao3': ['┐ 3', '┐형'],
    'ZhiJiao4': ['┘ 3', '┘형'],
    'Hen4': ['가로 4', '가로4', '横 4', '横4', 'IV형', 'Ⅳ형'],
    'Shu4': ['세로 4', '세로4', '竖 4', '竖4', 'IV형', 'Ⅳ형'],
    'Z3': ['Z 4', 'Z형', 'Z 4칸'],
    'Z4': ['S 4', 'S형', 'S 4칸'],
}

TEXT_NORMALIZE_REPLACEMENTS = {
    '공격 력': '공격력',
    '공 격력': '공격력',
    '공격럭': '공격력',
    '공격려': '공격력',
    '공격러': '공격력',
    '방어 력': '방어력',
    '치명확률': '치명 확률',
    '치명확를': '치명 확률',
    '치명확출': '치명 확률',
    '치명 확출': '치명 확률',
    '치명확울': '치명 확률',
    '치명 확울': '치명 확률',
    '치명 확를': '치명 확률',
    '치명피해': '치명 피해',
    '이능럭': '이능력',
    '이능려': '이능력',
    '이능력피해': '이능력 피해',
    '붕괴강도': '붕괴 강도',
    '봉괴 강도': '붕괴 강도',
    '붕괴강 도': '붕괴 강도',
    '사이클강도': '사이클 강도',
    '치료효율': '치료 효율',
    '주 속성': '주속성',
    '부 속성': '부속성',
    '드라이브모듈': '드라이브 모듈',
    'HP ': 'HP ',
    'ㅐ': 'HP',
    '키': 'HP',
    '郭': '공격력',
    '곽': '공격력',
    '겅격력': '공격력',
    '태': '피해',
    '太': '피해',
    '피 해': '피해',
    '피해 증강': '피해',
    '품승': '붕괴',
    '품음': '붕괴',
    '카드리지': '카트리지',
    '잃어버린 빚': '잃어버린 빛',
    '잃어버린 빛_': '잃어버린 빛',
    '빗속성': '빛속성',
    '빛 속성': '빛속성',
    '령 속성': '령속성',
    '주 속성': '주속성',
    '암 속성': '암속성',
    '혼 속성': '혼속성',
    '상 속성': '상속성',
    '정 신': '정신',
    '봉괴': '붕괴',
    '공 격 력': '공격력',
    '방 어 력': '방어력',
    '방 어력': '방어력',
    '치 명 확 률': '치명 확률',
    '치 명 피 해': '치명 피해',
    '붕 괴 강 도': '붕괴 강도',
    '사 이 클 강 도': '사이클 강도',
    '||형': 'II형',
    '| |형': 'II형',
    '1] 드라이브': 'II형 드라이브',
    '1]드라이브': 'II형드라이브',
    'l] 드라이브': 'II형 드라이브',
    'l]드라이브': 'II형드라이브',
    '그겨려': '공격력',
    '공겨려': '공격력',
    'SAA+2.50%': '공격력+2.50%',
    'SAH+2.50%': '공격력+2.50%',
    'SAl+2.50%': '공격력+2.50%',
    '치명 피해+44.00%': '치명 피해+4.00%',
}

IGNORE_LINE_PATTERNS = [
    r'^\+?\d+(?:\.\d+)?%?$',
    r'^\d+$',
    r'^Lv\.?\s*\d+',
    r'^\+\s*20$'
    , r'^20$',
    r'^획득',
    r'^장착',
    r'^잠금',
    r'^분해',
]


def normalize_ocr_text(text: str) -> str:
    text = (text or '').replace('\r', '\n')
    text = text.replace('Ⅰ', 'I').replace('Ⅱ', 'II').replace('Ⅲ', 'III').replace('Ⅳ', 'IV')
    text = re.sub(r'[ \t]+', ' ', text)
    # Common OCR numeric noise in NTE's small option text.  EasyOCR often
    # reads the percent sign as 9 and the digit 0 as O/o.  Normalize these
    # before option-value based disambiguation.
    text = re.sub(r'(?<=\d)[oO](?=\d|\D|$)', '0', text)
    text = re.sub(r'(\d+[.,]\d{2})9(?=\D|$)', r'\1%', text)
    text = re.sub(r'(\d+[.,]\d)9(?=\D|$)', r'\1%', text)
    text = text.replace('509', '50%').replace('009', '00%')
    for src, dst in TEXT_NORMALIZE_REPLACEMENTS.items():
        text = text.replace(src, dst)
    for src, dst in external_replacements().items():
        text = text.replace(src, dst)
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    return '\n'.join(lines)


def strip_value_noise(text: str) -> str:
    text = normalize_ocr_text(text)
    text = re.sub(r'[+＋]?\s*\d+(?:[.,]\d+)?\s*%?', ' ', text)
    text = re.sub(r'[:：/|·•\-_=]+', ' ', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text


def should_ignore_line(line: str) -> bool:
    clean = line.strip()
    if not clean:
        return True
    compact = re.sub(r'\s+', '', clean)
    if compact in {'공', '성', '등', '_', '-', '+', 'U', 'V', 'UV', '(', ')', '=', '공격력', '방어력', 'HP', '피해', '치명확률', '치명피해', '붕괴강도', '사이클강도'}:
        return True
    if len(compact) <= 1 and not re.search(r'HP', compact, flags=re.I):
        return True
    # Crops may include the orange cartridge set/name footer.  It is not an
    # option line and was being mixed into sub-option OCR.
    if ('「' in clean and '」' in clean) or clean in {'카트리지', '드라이브 모듈', '주속성', '부속성'}:
        return True
    return any(re.search(pattern, clean, flags=re.I) for pattern in IGNORE_LINE_PATTERNS)


def _score(a: str, b: str) -> float:
    a = re.sub(r'\s+', '', (a or '').lower())
    b = re.sub(r'\s+', '', (b or '').lower())
    if not a or not b:
        return 0.0
    if a in b or b in a:
        return 0.95
    return SequenceMatcher(None, a, b).ratio()


@dataclass
class ParsedOcrItem:
    item_type: str
    quality: str
    name: str
    base_id: str
    geometry: str = ''
    main: str = ''
    mains: list[str] | None = None
    subs: list[str] | None = None
    raw_text: str = ''
    confidence: float = 0.0

    def to_bag_entry(self, index: int) -> dict[str, Any]:
        if self.item_type == 'drive':
            return {
                'bag_id': f'scan-drive-{index}',
                'base_id': self.base_id,
                'quality': self.quality,
                'geometry': self.geometry,
                'mains': list(self.mains or []),
                'subs': list(self.subs or [])[:4],
                'scanned': True,
                'order': index,
                'raw_text': self.raw_text,
                'confidence': self.confidence,
            }
        return {
            'bag_id': f'scan-cartridge-{index}',
            'base_id': self.base_id,
            'quality': self.quality,
            'main': self.main,
            'subs': list(self.subs or [])[:4],
            'scanned': True,
            'order': index,
            'raw_text': self.raw_text,
            'confidence': self.confidence,
        }


class KoreanOcrEngine:
    """Tesseract v5 OCR wrapper for the inventory scanner."""

    _shared_engine: dict[str, str] | None = None
    _shared_backend_name = ''

    def __init__(self):
        self.mode = os.environ.get('NTE_OCR_MODE', 'fast').strip().lower() or 'fast'
        if KoreanOcrEngine._shared_engine is None:
            location = locate_tesseract(verify=True)
            lang = 'kor+eng'
            psm = '6'
            oem = '1'
            KoreanOcrEngine._shared_engine = {
                'exe': location.exe,
                'lang': lang,
                'psm': psm,
                'oem': oem,
                'tessdata_dir': location.tessdata_dir,
            }
            KoreanOcrEngine._shared_backend_name = f'Tesseract({lang},psm{psm})'
        self.engine = KoreanOcrEngine._shared_engine
        self.backend_name = KoreanOcrEngine._shared_backend_name

    def preprocess(self, image: Any, *, mode: str = 'text', variant: str = 'balanced'):
        try:
            from PIL import ImageEnhance, ImageFilter, ImageOps  # type: ignore

            img = image.convert('RGB') if hasattr(image, 'convert') else image
            if not hasattr(img, 'size'):
                return image
            width, height = img.size
            scale = 3 if max(width, height) < 650 else 2
            if scale != 1:
                img = img.resize((int(width * scale), int(height * scale)))
            if mode == 'text':
                gray = ImageOps.autocontrast(img.convert('L'), cutoff=1)
                gray = ImageEnhance.Contrast(gray).enhance(1.90 if variant == 'fast' else 2.05)
                gray = ImageEnhance.Sharpness(gray).enhance(2.25)
                img = gray.convert('RGB')
            else:
                img = ImageOps.autocontrast(img)
                img = ImageEnhance.Sharpness(img).enhance(1.5)
            return img.filter(ImageFilter.SHARPEN)
        except Exception:
            return image


    def _read_tesseract_once(self, image_input) -> str:
        engine = self.engine
        exe = engine.get('exe') or 'tesseract'
        lang = engine.get('lang') or 'kor+eng'
        psm = str(engine.get('psm') or '6')
        oem = str(engine.get('oem') or '1')
        tessdata_dir = str(engine.get('tessdata_dir') or '')
        temp_path = None
        try:
            if isinstance(image_input, (str, bytes)):
                input_path = os.fsdecode(image_input)
            else:
                fd, temp_path = tempfile.mkstemp(prefix='nte_tess_', suffix='.png')
                os.close(fd)
                if hasattr(image_input, 'save'):
                    image_input.save(temp_path)
                else:
                    from PIL import Image  # type: ignore
                    import numpy as np  # type: ignore

                    Image.fromarray(np.asarray(image_input)).save(temp_path)
                input_path = temp_path
            cmd = [
                exe, input_path, 'stdout',
                '-l', lang,
                '--psm', psm,
                '--oem', oem,
                '-c', 'preserve_interword_spaces=1',
            ]
            if tessdata_dir:
                cmd.extend(['--tessdata-dir', tessdata_dir])
            proc = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8', errors='ignore', timeout=35)
            if proc.returncode not in (0, 1):
                raise RuntimeError((proc.stderr or '').strip() or f'tesseract exit {proc.returncode}')
            return normalize_ocr_text(proc.stdout or '')
        finally:
            if temp_path:
                try:
                    os.unlink(temp_path)
                except Exception:
                    pass

    def _quality_score_text(self, text: str) -> int:
        useful = ['공격력', '방어력', 'HP', '피해', '치명', '붕괴', '사이클', '치료', '가로', '세로', '드라이브', '카트리지']
        score = sum(3 for token in useful if token in text)
        score += sum(1 for _ in re.finditer(r'[가-힣]{2,}', text))
        score -= sum(2 for _ in re.finditer(r'[一-龥]{1,}', text))
        return score

    def read_text(self, image_path: str | bytes | Any, *, preprocess: bool = True, mode: str = 'text') -> str:
        if isinstance(image_path, (str, bytes)):
            image_obj = image_path
        elif preprocess:
            image_obj = self.preprocess(image_path, mode=mode, variant='balanced')
        else:
            image_obj = image_path
        return self._read_tesseract_once(image_obj)

    def _make_fast_composite(self, regions: dict[str, Any]):
        try:
            from PIL import Image  # type: ignore

            prepared = []
            for name in ('title', 'main_text', 'sub_text'):
                image = regions.get(name)
                if image is None:
                    continue
                processed = self.preprocess(image, mode='text', variant='fast')
                if hasattr(processed, 'convert'):
                    processed = processed.convert('RGB')
                prepared.append(processed)
            if not prepared:
                return None
            width = max(image.size[0] for image in prepared)
            gap = 24
            height = sum(image.size[1] for image in prepared) + gap * (len(prepared) - 1)
            canvas = Image.new('RGB', (width, height), (255, 255, 255))
            y = 0
            for image in prepared:
                canvas.paste(image, (0, y))
                y += image.size[1] + gap
            return canvas
        except Exception:
            return None

    def read_regions_fast(self, regions: dict[str, Any]) -> dict[str, str]:
        composite = self._make_fast_composite(regions)
        if composite is None:
            return {}
        text = normalize_ocr_text(self._read_tesseract_once(composite))
        return {
            'title': text,
            'main_text': text,
            'main': '',
            'sub_text': text,
            'sub': '',
            'full': text,
            '_ocr_backend': f'{self.backend_name}/tesseract-fast-1pass',
        }

    def read_regions_precise(self, regions: dict[str, Any]) -> dict[str, str]:
        texts: dict[str, str] = {}
        for name, image in regions.items():
            if image is None:
                continue
            if name in {'main_text', 'sub_text', 'main', 'sub'}:
                variants: list[str] = []
                for variant in ('fast', 'balanced'):
                    try:
                        text = self._read_tesseract_once(self.preprocess(image, mode='text', variant=variant))
                        if text and text not in variants:
                            variants.append(text)
                    except Exception:
                        pass
                texts[name] = normalize_ocr_text('\n'.join(variants))
            else:
                texts[name] = self.read_text(image, mode='text')
        texts['_ocr_backend'] = f'{self.backend_name}/tesseract-precise'
        return texts

    def read_regions(self, regions: dict[str, Any]) -> dict[str, str]:
        if self.mode != 'precise':
            fast = self.read_regions_fast(regions)
            if fast and self._quality_score_text('\n'.join(fast.values())) >= 1:
                return fast
        return self.read_regions_precise(regions)


class EquipmentTextParser:
    def __init__(self):
        self.cartridge_names = [(item['id'], normalize_name(item.get('name'))) for item in CARTRIDGES]
        self.drive_by_geometry_quality = {(item.get('geometry'), item.get('quality')): item for item in DRIVE_MODULES}
        self.drive_by_geometry = {}
        for item in DRIVE_MODULES:
            self.drive_by_geometry.setdefault(item.get('geometry'), item)
        self.sub_candidates = []
        for opt in list(CARTRIDGE_SUB_OPTIONS) + list(DRIVE_SUB_OPTIONS):
            option_id = opt['id']
            label = get_attribute_label(option_id)
            self.sub_candidates.append((option_id, label))
        self.cartridge_main_candidates = [(item['id'], get_attribute_label(item['id'])) for item in CARTRIDGE_MAIN_OPTIONS]
        self.drive_main_candidates = [(option_id, get_attribute_label(option_id)) for option_id in DRIVE_FIXED_MAIN_OPTIONS]
        self.all_main_candidates = self.cartridge_main_candidates + self.drive_main_candidates

    def parse(self, text: str, *, geometry_hint: str = '', quality_hint: str = '') -> ParsedOcrItem | None:
        # Backward-compatible whole-panel parser.
        return self.parse_structured({'full': text, 'title': text, 'main': text, 'sub': text}, geometry_hint=geometry_hint, quality_hint=quality_hint)

    def parse_structured(self, texts: dict[str, str], *, geometry_hint: str = '', quality_hint: str = '') -> ParsedOcrItem | None:
        normalized = {key: normalize_ocr_text(value or '') for key, value in texts.items()}
        full = normalize_ocr_text('\n'.join(value for key, value in normalized.items() if value and key != 'full'))
        if not full:
            return None
        title_text = normalized.get('title') or full
        main_text = normalize_ocr_text('\n'.join(filter(None, [normalized.get('main_text', ''), normalized.get('main', '')]))) or full
        sub_text = normalize_ocr_text('\n'.join(filter(None, [normalized.get('sub_text', ''), normalized.get('sub', '')]))) or full
        quality = quality_hint or self._detect_quality(full)
        item_type = self._detect_type(title_text + '\n' + full, geometry_hint)
        if item_type == 'drive':
            geometry = geometry_hint or self._detect_geometry(title_text + '\n' + full)
            base = self.drive_by_geometry_quality.get((geometry, quality)) or self.drive_by_geometry.get(geometry)
            if not base:
                # Last-resort fallback for cases where icon matching fails but
                # OCR clearly says this is a drive.  The game title only exposes
                # II/III/IV type, not exact shape; default to the horizontal
                # shape so the entry is not discarded.  The raw OCR remains in
                # debug output for later correction.
                type_text = re.sub(r'\s+', '', title_text + '\n' + full).upper()
                if any(token in type_text for token in ('II형', 'I형', '1형', 'L형', '2형', 'LE드라이브', 'LLE드라이브', 'LES드라이브', 'LIS드라이브', 'LIE드라이브')):
                    geometry = 'Hen2'
                elif any(token in type_text for token in ('III형', '3형')):
                    geometry = 'Hen3'
                elif any(token in type_text for token in ('IV형', '4형')):
                    geometry = 'Hen4'
                elif '드라이브' in type_text:
                    geometry = 'Hen2'
                base = self.drive_by_geometry_quality.get((geometry, quality)) or self.drive_by_geometry.get(geometry)
            if not base:
                return None
            # Drive main stats are fixed at Lv.20 in the database.  OCR is used
            # to distinguish drive/cartridge and sub-options, not to decide the
            # drive main stat pair/order.
            mains = list(DRIVE_FIXED_MAIN_OPTIONS)
            subs = self._detect_options(sub_text, self.sub_candidates, max_count=4)
            return ParsedOcrItem(
                item_type='drive', quality=quality, name=normalize_name(base.get('name')),
                base_id=base['id'], geometry=geometry, mains=mains, subs=subs,
                raw_text=self._format_raw_debug(normalized), confidence=0.78,
            )
        base_id, name, confidence = self._match_cartridge(title_text + '\n' + full)
        if not base_id:
            return None
        main = self._detect_cartridge_main(main_text) or self._detect_cartridge_main(full) or CARTRIDGE_MAIN_OPTIONS[0]['id']
        subs = self._detect_options(sub_text, self.sub_candidates, max_count=4)
        return ParsedOcrItem(
            item_type='cartridge', quality=quality, name=name, base_id=base_id,
            main=main, subs=subs, raw_text=self._format_raw_debug(normalized), confidence=confidence,
        )

    def _format_raw_debug(self, texts: dict[str, str]) -> str:
        parts = []
        for key in ('title', 'main_text', 'main', 'sub_text', 'sub', 'full'):
            value = texts.get(key)
            if value:
                parts.append(f'[{key}]\n{value}')
        return '\n\n'.join(parts)

    def _detect_quality(self, text: str) -> str:
        clean = text.upper()
        for quality, aliases in QUALITY_ALIASES.items():
            if any(alias.upper() in clean for alias in aliases):
                return quality
        return 'S급'

    def _detect_type(self, text: str, geometry_hint: str) -> str:
        upper = text.upper()
        if geometry_hint or '드라이브' in text or ' DRIVE' in upper:
            return 'drive'
        if '카트리지' in text or '진급' in text or '세트 효과' in text:
            return 'cartridge'
        return 'drive' if self._detect_geometry(text) else 'cartridge'

    def _detect_geometry(self, text: str) -> str:
        compact = re.sub(r'\s+', '', text)
        for geometry, aliases in GEOMETRY_ALIASES.items():
            if GEOMETRY_LABELS.get(geometry, '') and re.sub(r'\s+', '', GEOMETRY_LABELS[geometry]) in compact:
                return geometry
            for alias in aliases:
                if re.sub(r'\s+', '', alias) in compact:
                    return geometry
        # Title OCR sometimes captures only roman type. Use it only as a weak hint;
        # actual shape_matcher usually supplies exact geometry.
        upper = compact.upper()
        if 'III형' in upper or '3형' in upper:
            return 'Hen3'
        if 'IV형' in upper or '4형' in upper:
            return 'Hen4'
        if (
            'II형' in upper or '2형' in upper or 'I형' in upper or '1형' in upper
            or 'L형' in upper or 'LE드라이브' in upper or 'LLE드라이브' in upper
            or 'LES드라이브' in upper or 'LIS드라이브' in upper or 'LIE드라이브' in upper
        ):
            return 'Hen2'
        return ''

    def _option_lines(self, text: str) -> list[str]:
        lines: list[str] = []
        for raw in normalize_ocr_text(text).splitlines():
            raw = raw.strip()
            if not raw or should_ignore_line(raw):
                continue
            # OCR can merge two option rows. Split only after a value-looking token.
            parts = re.split(r'(?<=[%0-9])\s{2,}|[|｜]', raw)
            for part in parts:
                part = part.strip()
                if part and not should_ignore_line(part):
                    lines.append(part)
        return lines

    def _detect_options(self, text: str, candidates: list[tuple[str, str]], max_count: int = 4) -> list[str]:
        found: list[str] = []
        lines = self._option_lines(text)
        for line in lines:
            option_id = self._best_option_for_line(line, candidates)
            if option_id and option_id not in found:
                found.append(option_id)
            if len(found) >= max_count:
                break
        return found[:max_count]

    def _detect_main_options(self, text: str, *, drive: bool = False) -> list[str]:
        candidates = self.drive_main_candidates if drive else self.all_main_candidates
        return self._detect_options(text, candidates, max_count=4)

    def _detect_cartridge_main(self, text: str) -> str:
        options = self._detect_options(text, self.cartridge_main_candidates, max_count=1)
        return options[0] if options else ''

    def _best_option_for_line(self, line: str, candidates: list[tuple[str, str]]) -> str:
        original = normalize_ocr_text(line)
        candidate_ids = {cid for cid, _ in candidates}
        # First resolve ambiguous labels like 공격력/방어력/HP by whether the
        # OCR line contains a percent sign.  Without this, the candidate order
        # makes 방어력+17.50% become flat 방어력 instead of 방어력%.
        stat_hint = self._option_by_stat_value(original, candidate_ids)
        if stat_hint:
            return stat_hint
        # Apply high-confidence value+glyph rules before fuzzy label matching.
        # Tiny game text often turns '치명 피해+4.00%' into unreadable fragments,
        # but +4.00% is a distinctive S급 Ⅱ형 drive value.
        pre_hint = self._option_by_value_hint(original, candidate_ids, early=True)
        if pre_hint:
            return pre_hint
        clean = strip_value_noise(original)
        compact_line = re.sub(r'\s+', '', clean)
        best = ('', 0.0)
        for option_id, label in candidates:
            labels = self._label_aliases(label, option_id)
            for alias in labels:
                alias_compact = re.sub(r'\s+', '', alias)
                if alias_compact and alias_compact in compact_line:
                    return option_id
                score = max(_score(clean, alias), _score(compact_line, alias_compact))
                if score > best[1]:
                    best = (option_id, score)
        if best[1] >= 0.62:
            return best[0]
        # Value-pattern fallback for tiny drive text where Hangul is sometimes
        # unreadable.  Use only when the value is very characteristic or the OCR
        # line still contains a weak glyph hint.
        value_hint = self._option_by_value_hint(original, candidate_ids)
        return value_hint

    def _option_by_stat_value(self, line: str, candidate_ids: set[str]) -> str:
        compact = re.sub(r'\s+', '', normalize_ocr_text(line))
        low = compact.lower()
        has_percent = '%' in compact
        def allowed(opt: str) -> bool:
            return opt in candidate_ids
        if '공격력' in compact or '공격' in compact or '郭' in compact or '곽' in compact:
            if has_percent and allowed('AtkUp'):
                return 'AtkUp'
            if not has_percent and allowed('AtkAdd'):
                return 'AtkAdd'
        if '방어력' in compact or '방어' in compact:
            if has_percent and allowed('DefUp'):
                return 'DefUp'
            if not has_percent and allowed('DefAdd'):
                return 'DefAdd'
        if 'HP' in compact or '체력' in compact or '키' in compact or 'hp' in low:
            if has_percent and allowed('HPMaxUp'):
                return 'HPMaxUp'
            if not has_percent and allowed('HPMaxAdd'):
                return 'HPMaxAdd'
        return ''

    def _option_by_value_hint(self, line: str, candidate_ids: set[str], *, early: bool = False) -> str:
        compact = re.sub(r'\s+', '', normalize_ocr_text(line))
        low = compact.lower()
        def allowed(opt: str) -> bool:
            return opt in candidate_ids
        has_percent = '%' in compact
        if re.search(r'(?:4|44)[.,]0{1,2}%', compact) and allowed('CritDamageBase'):
            return 'CritDamageBase'
        if ('hp' in low or '키' in compact) and has_percent and allowed('HPMaxUp'):
            return 'HPMaxUp'
        if ('hp' in low or '키' in compact) and not has_percent and allowed('HPMaxAdd'):
            return 'HPMaxAdd'
        if ('공' in compact or '격' in compact or '郭' in compact or '곽' in compact) and has_percent and allowed('AtkUp'):
            return 'AtkUp'
        if ('공' in compact or '격' in compact or '郭' in compact or '곽' in compact) and not has_percent and allowed('AtkAdd'):
            return 'AtkAdd'
        if re.search(r'2[.,][45]0?%', compact):
            if ('hp' in low or '키' in compact) and allowed('HPMaxUp'):
                return 'HPMaxUp'
            if allowed('AtkUp'):
                return 'AtkUp'
        if re.search(r'2[.,]0{1,2}%', compact):
            if ('치' in compact) and allowed('CritBase'):
                return 'CritBase'
            if ('피' in compact or '태' in compact or '太' in compact) and allowed('DamageUpGeneralBase'):
                return 'DamageUpGeneralBase'
            if not early and allowed('DamageUpGeneralBase'):
                return 'DamageUpGeneralBase'
        if ('피' in compact or '태' in compact or '太' in compact) and allowed('DamageUpGeneralBase'):
            return 'DamageUpGeneralBase'
        if not early and re.search(r'\+?(12|18|24|36|48|60)$', compact) and allowed('UnbalIntensityBase'):
            return 'UnbalIntensityBase'
        return ''

    def _label_aliases(self, label: str, option_id: str) -> list[str]:
        aliases = {label}
        compact = re.sub(r'\s+', '', label)
        aliases.add(compact)
        if option_id in {'AtkAdd', 'AtkUp', 'AtkBase'}:
            aliases.update(['공격력', '공격', '격력', '郭', '곽'])
        if option_id in {'HPMaxAdd', 'HPMaxUp', 'HPMaxBase'}:
            aliases.update(['HP', '체력', '키'])
        if option_id in {'DefAdd', 'DefUp', 'DefBase'}:
            aliases.update(['방어력', '방어'])
        if option_id in {'Crit', 'CritBase'}:
            aliases.update(['치명 확률', '치확', '치명률'])
        if option_id in {'CritDamage', 'CritDamageBase'}:
            aliases.update(['치명 피해', '치피'])
        if option_id in {'DamageUpGeneralBase', 'DamageUpGeneral'}:
            aliases.update(['피해', '통용 피해', '통용 피해 증강', '태', '太'])
        if option_id in {'MagBase'}:
            aliases.update(['사이클 강도', '사이클'])
        if option_id in {'UnbalIntensityBase'}:
            aliases.update(['붕괴 강도', '붕괴'])
        if option_id in {'HealUp'}:
            aliases.update(['치료 효율', '치료'])
        elemental_aliases = {
            'DamageUpCosmosBase': ['빛속성', '빗속성', '빛속성 피해', '빛 이능력', '빛속성 이능력 피해', '빛속성 피해'],
            'DamageUpNatureBase': ['령속성', '령속성 피해', '령 이능력', '령속성 이능력 피해'],
            'DamageUpIncantationBase': ['주속성', '주속성 피해', '주 이능력', '주속성 이능력 피해'],
            'DamageUpChaosBase': ['암속성', '암속성 피해', '암 이능력', '암속성 이능력 피해'],
            'DamageUpPsycheBase': ['혼속성', '혼속성 피해', '혼 이능력', '혼속성 이능력 피해'],
            'DamageUpLakshanaBase': ['상속성', '상속성 피해', '상 이능력', '상속성 이능력 피해'],
            'DamageUpPsychicallyBase': ['정신 피해', '정신', '정신피해'],
        }
        aliases.update(elemental_aliases.get(option_id, []))
        # Attribute-specific damage aliases.
        if option_id.startswith('DamageUp') and option_id not in {'DamageUpGeneralBase', 'DamageUpGeneral'}:
            aliases.add(label.replace(' 이능력 피해', ' 피해'))
            aliases.add(label.replace(' 이능력 피해', ' 이능력 피해 증강'))
            aliases.add(label.replace(' 피해', ' 피해 증강'))
        return list(aliases)

    def _match_cartridge(self, text: str) -> tuple[str, str, float]:
        best = ('', '', 0.0)
        for base_id, name in self.cartridge_names:
            score = _score(text, name)
            for line in text.splitlines():
                score = max(score, _score(line, name))
            if score > best[2]:
                best = (base_id, name, score)
        if best[2] < 0.45:
            return ('', '', 0.0)
        return best
