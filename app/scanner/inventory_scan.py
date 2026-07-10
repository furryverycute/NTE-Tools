from __future__ import annotations

import json
import os
import shutil
import subprocess
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

from app.scanner.scan_plan import ScanStep, build_console_scan_plan
@dataclass(frozen=True)
class CapturedFrame:
    step: ScanStep
    detail_path: Path


def _split_regions_from_detail(detail_img):
    from app.scanner.window_capture import (
        DETAIL_ICON_INNER_REL,
        DETAIL_MAIN_INNER_REL,
        DETAIL_MAIN_TEXT_INNER_REL,
        DETAIL_SUB_INNER_REL,
        DETAIL_SUB_TEXT_INNER_REL,
        DETAIL_TITLE_INNER_REL,
        crop_inner_region,
    )
    return {
        'title': crop_inner_region(detail_img, DETAIL_TITLE_INNER_REL),
        'main': crop_inner_region(detail_img, DETAIL_MAIN_INNER_REL),
        'main_text': crop_inner_region(detail_img, DETAIL_MAIN_TEXT_INNER_REL),
        'sub': crop_inner_region(detail_img, DETAIL_SUB_INNER_REL),
        'sub_text': crop_inner_region(detail_img, DETAIL_SUB_TEXT_INNER_REL),
    }, crop_inner_region(detail_img, DETAIL_ICON_INNER_REL)


def _fast_save_png(image, path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        image.save(path, optimize=False, compress_level=1)
    except TypeError:
        image.save(path)


class InventoryScanRunner:
    """Windows-only game inventory scanner.

    v29 separates capture and OCR:
    - Phase 1: quickly navigate the bag and save every detail-panel image.
    - Phase 2: run OCR on the captured images in background worker threads.
    """

    def __init__(
        self,
        total_count: int,
        *,
        debug_dir: str | Path | None = None,
        progress_callback: Callable[[int, str], None] | None = None,
        save_debug: bool = False,
        progress_interval: int = 5,
        settle_after_move: float = 0.075,
        ocr_workers: int | None = None,
    ):
        self.total_count = int(total_count)
        self.steps = build_console_scan_plan(total_count)
        self.progress_callback = progress_callback
        self.save_debug = bool(save_debug)
        self.progress_interval = max(1, int(progress_interval))
        self.settle_after_move = max(0.0, float(settle_after_move))
        self.debug_dir = Path(debug_dir) if debug_dir else Path.cwd() / 'scan_debug'
        self.debug_dir.mkdir(parents=True, exist_ok=True)
        self._log_path = self.debug_dir / 'scan_session.log'
        env_workers = os.environ.get('NTE_OCR_WORKERS', '').strip()
        if ocr_workers is None and env_workers:
            try:
                ocr_workers = int(env_workers)
            except ValueError:
                ocr_workers = None
        self.ocr_workers = max(1, min(4, int(ocr_workers or 1)))
        self._thread_local = threading.local()
        self.capture_errors: list[dict[str, Any]] = []
        self._setup_scan_backends()

    def _setup_scan_backends(self):
        from app.scanner.gamepad_controller import VirtualGamepadController
        from app.scanner.window_capture import WindowCapture
        self.capture = WindowCapture()
        self.gamepad = VirtualGamepadController()

    def _worker_backends(self):
        ctx = self._thread_local
        if not hasattr(ctx, 'ocr'):
            from app.scanner.ocr_backend import EquipmentTextParser, KoreanOcrEngine
            from app.scanner.shape_matcher import ShapeTemplateMatcher
            ctx.ocr = KoreanOcrEngine()
            ctx.parser = EquipmentTextParser()
            ctx.shape_matcher = ShapeTemplateMatcher()
        return ctx.ocr, ctx.parser, ctx.shape_matcher

    def emit(self, index: int, message: str):
        if self.progress_callback:
            self.progress_callback(index, message)
        self.log(f'[{index}] {message}')

    def log(self, message: str):
        try:
            from datetime import datetime
            self.debug_dir.mkdir(parents=True, exist_ok=True)
            with self._log_path.open('a', encoding='utf-8') as fp:
                fp.write(f'{datetime.now().isoformat(timespec="seconds")} {message}\n')
        except Exception:
            pass

    def close(self):
        try:
            self.gamepad.close()
        except Exception:
            pass
        try:
            self.capture.close()
        except Exception:
            pass

    def run(self) -> dict[str, list[dict[str, Any]]]:
        results: dict[str, list[dict[str, Any]]] = {'cartridges': [], 'drives': [], 'errors': [], 'review': []}
        captured: list[CapturedFrame] = []
        try:
            self.emit(0, 'HTGame.exe 창 확인 중...')
            activated = False
            try:
                activated = bool(self.capture.activate_game_window())
            except Exception:
                activated = False
            if not activated:
                self.log('HTGame.exe 창을 전면 활성화하지 못했습니다. 감지된 캡처 영역으로 계속 시도합니다.')

            self.emit(0, '컨트롤러 입력 인식 대기 중...')
            accepted = self.gamepad.wait_until_game_accepts_input(
                self.capture,
                total_count=self.total_count,
                timeout=22.0,
                progress_callback=self.emit,
                log_callback=self.log,
            )
            if not accepted:
                raise RuntimeError(
                    'ViGEmBus 가상 패드는 생성됐지만 HTGame.exe가 컨트롤러 입력에 반응하지 않습니다. '
                    '게임 창을 활성화하고, 콘솔 탭 첫 번째 아이템이 선택된 상태인지 확인하세요. scan_debug/scan_session.log의 [input_probe] 점수를 확인하세요.'
                )

            captured = self.capture_all_items()
            results['errors'].extend(self.capture_errors)
        finally:
            # Game control is no longer needed after image capture.  Release the
            # virtual pad before OCR so the game is not held by the scanner.
            self.close()

        if not captured:
            return results

        self.emit(0, f'드라이브 불러오는 중... 0% (0/{len(captured)}개)')
        ocr_results = self.ocr_captured_items(captured, results)
        for step_index, parsed in sorted(ocr_results, key=lambda it: it[0]):
            entry = parsed.to_bag_entry(step_index)
            if self.needs_review(parsed):
                results['review'].append({
                    'index': step_index,
                    'name': parsed.name,
                    'type': parsed.item_type,
                    'confidence': parsed.confidence,
                    'reason': 'low_confidence_or_incomplete',
                    'detail_path': entry.get('detail_path', ''),
                    'entry': entry,
                })
                continue
            if parsed.item_type == 'drive':
                results['drives'].append(entry)
            else:
                results['cartridges'].append(entry)
        return results

    def capture_all_items(self) -> list[CapturedFrame]:
        captured: list[CapturedFrame] = []
        self.emit(0, f'이미지 스캔 중... 0% (0/{self.total_count}개)')
        previous_step: ScanStep | None = None
        manifest: list[dict[str, Any]] = []
        for step in self.steps:
            if previous_step is not None:
                try:
                    self.gamepad.move_to_step(previous_step, step)
                except AttributeError:
                    self.gamepad.move_between((previous_step.row, previous_step.col), (step.row, step.col))
            previous_step = step
            if self.settle_after_move:
                time.sleep(self.settle_after_move)
            try:
                detail_img = self.capture.capture_detail_panel()
                detail_path = self.debug_dir / f'detail_{step.index:04d}.png'
                _fast_save_png(detail_img, detail_path)
                captured.append(CapturedFrame(step, detail_path))
                manifest.append({'index': step.index, 'row': step.row, 'col': step.col, 'detail': str(detail_path)})
            except Exception as exc:
                self.log(f'[capture_failed] #{step.index}: {exc.__class__.__name__}: {exc}')
                self.capture_errors.append({
                    'index': step.index,
                    'row': step.row,
                    'col': step.col,
                    'reason': f'{exc.__class__.__name__}: {exc}',
                    'detail_path': '',
                })
            if step.index == 1 or step.index % max(1, self.progress_interval) == 0 or step.index == self.total_count:
                percent = int(step.index * 100 / max(1, self.total_count))
                self.emit(step.index, f'이미지 스캔 중... {percent}% ({step.index}/{self.total_count}개)')
        try:
            (self.debug_dir / 'capture_manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding='utf-8')
        except Exception:
            pass
        self.emit(self.total_count, f'이미지 스캔 완료. OCR 처리 준비 중... ({len(captured)}/{self.total_count}개)')
        return captured

    def ocr_captured_items(self, captured: list[CapturedFrame], results: dict[str, list[dict[str, Any]]]):
        parsed_items: list[tuple[int, Any]] = []
        total = len(captured)
        workers = max(1, min(self.ocr_workers, total))
        self.log(f'[ocr] start total={total} workers={workers}')
        completed = 0
        with ThreadPoolExecutor(max_workers=workers, thread_name_prefix='nte-ocr') as executor:
            futures = {executor.submit(self.process_captured_item, frame): frame for frame in captured}
            for future in as_completed(futures):
                frame = futures[future]
                completed += 1
                try:
                    parsed = future.result()
                    if parsed:
                        parsed.detail_path = str(frame.detail_path)
                        parsed_items.append((frame.step.index, parsed))
                    else:
                        results['errors'].append({
                            'index': frame.step.index,
                            'row': frame.step.row,
                            'col': frame.step.col,
                            'reason': 'parse_failed',
                            'detail_path': str(frame.detail_path),
                        })
                except Exception as exc:
                    self.log(f'[ocr_failed] #{frame.step.index}: {exc.__class__.__name__}: {exc}')
                    results['errors'].append({
                        'index': frame.step.index,
                        'row': frame.step.row,
                        'col': frame.step.col,
                        'reason': f'{exc.__class__.__name__}: {exc}',
                        'detail_path': str(frame.detail_path),
                    })
                if completed == 1 or completed % max(1, self.progress_interval) == 0 or completed == total:
                    percent = int(completed * 100 / max(1, total))
                    self.emit(completed, f'드라이브 불러오는 중... {percent}% ({completed}/{total}개)')
        return parsed_items

    def process_captured_item(self, frame: CapturedFrame):
        from PIL import Image  # type: ignore
        ocr, parser, shape_matcher = self._worker_backends()
        with Image.open(frame.detail_path) as img:
            detail_img = img.convert('RGB')
        regions, icon_img = _split_regions_from_detail(detail_img)
        region_texts = ocr.read_regions(regions)
        geometry_hint, quality_hint, shape_score = shape_matcher.match(icon_img)
        parsed = parser.parse_structured(region_texts, geometry_hint=geometry_hint, quality_hint=quality_hint)
        # Full detail OCR is very slow and noisy.  Keep it opt-in for debugging.
        if not parsed and os.environ.get('NTE_OCR_FULL_FALLBACK', '0').strip().lower() in {'1', 'true', 'yes', 'on'}:
            try:
                full_text = ocr.read_text(detail_img, mode='text')
                region_texts['full'] = full_text
                parsed = parser.parse_structured(region_texts, geometry_hint=geometry_hint, quality_hint=quality_hint)
            except Exception as exc:
                self.log(f'[ocr_fallback] #{frame.step.index}: {exc.__class__.__name__}: {exc}')
        if parsed:
            parsed.confidence = max(parsed.confidence, min(0.98, 0.60 + max(shape_score, 0) * 0.30))
        self.save_ocr_debug(frame, parsed, region_texts, icon_img, regions, geometry_hint, quality_hint, shape_score)
        return parsed

    def save_ocr_debug(self, frame: CapturedFrame, parsed, region_texts, icon_img, regions, geometry_hint, quality_hint, shape_score):
        try:
            idx = frame.step.index
            debug_text = parsed.raw_text if parsed else '\n'.join(f'[{k}]\n{v}' for k, v in region_texts.items())
            debug_text += f'\n\n[shape_match] geometry={geometry_hint} quality={quality_hint} score={shape_score}'
            if parsed:
                debug_text += f'\n[parsed] type={parsed.item_type} name={parsed.name} quality={parsed.quality} confidence={parsed.confidence}'
            (self.debug_dir / f'ocr_{idx:04d}.txt').write_text(debug_text, encoding='utf-8')
            # Region PNGs are useful for tuning but writing every crop for every
            # item creates a lot of disk I/O.  Save only the first few by default.
            full_debug = os.environ.get('NTE_SCAN_DEBUG_IMAGES', '0').strip().lower() in {'1', 'true', 'yes', 'on'}
            if full_debug or idx <= 3 or parsed is None:
                _fast_save_png(icon_img, self.debug_dir / f'icon_{idx:04d}.png')
                for region_name, region_img in regions.items():
                    _fast_save_png(region_img, self.debug_dir / f'{region_name}_{idx:04d}.png')
        except Exception as exc:
            self.log(f'[debug_save_failed] #{frame.step.index}: {exc.__class__.__name__}: {exc}')

    @staticmethod
    def needs_review(parsed) -> bool:
        subs = list(parsed.subs or [])
        if parsed.confidence < 0.72:
            return True
        if parsed.item_type == 'drive':
            if not parsed.geometry or len(subs) < 4 or not (parsed.mains or []):
                return True
        else:
            if not parsed.base_id or not parsed.main or len(subs) < 4:
                return True
        return False
