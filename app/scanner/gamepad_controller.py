from __future__ import annotations

import time
from dataclasses import dataclass


@dataclass
class ImageDiffScore:
    mean: float = 0.0
    rms: float = 0.0
    changed_ratio: float = 0.0

    @property
    def passed(self) -> bool:
        return (
            self.mean >= 0.0045
            or self.rms >= 0.020
            or self.changed_ratio >= 0.0025
        )

    def short(self) -> str:
        return f'mean={self.mean:.4f}, rms={self.rms:.4f}, changed={self.changed_ratio:.4f}'


def _image_difference_score(img_a, img_b) -> ImageDiffScore:
    """Return a cheap difference score between two PIL images."""
    try:
        from PIL import ImageChops, ImageStat  # type: ignore
        a = img_a.resize((192, 108)).convert('L')
        b = img_b.resize((192, 108)).convert('L')
        diff = ImageChops.difference(a, b)
        stat = ImageStat.Stat(diff)
        mean = float(stat.mean[0]) / 255.0
        rms = float(stat.rms[0]) / 255.0
        changed = diff.point(lambda p: 255 if p > 18 else 0)
        changed_stat = ImageStat.Stat(changed)
        changed_ratio = float(changed_stat.mean[0]) / 255.0
        return ImageDiffScore(mean=mean, rms=rms, changed_ratio=changed_ratio)
    except Exception:
        return ImageDiffScore()


class VirtualGamepadController:
    def __init__(self, press_seconds: float = 0.070, settle_seconds: float = 0.145):
        try:
            import vgamepad as vg  # type: ignore
        except Exception as exc:
            raise RuntimeError('vgamepad를 불러올 수 없습니다. setup.bat를 실행하고 ViGEmBus 설치를 완료하세요.') from exc
        self.vg = vg
        try:
            self.pad = vg.VX360Gamepad()
        except Exception as exc:
            try:
                from app.scanner.runtime_setup import ensure_controller_installer, launch_controller_installer

                installer = ensure_controller_installer(download=True)
                if installer:
                    launch_controller_installer(installer)
            except Exception:
                pass
            raise RuntimeError('ViGEmBus 가상 패드를 만들 수 없습니다. ViGEmBus 설치 창을 열었으면 설치를 완료한 뒤 다시 스캔하세요.') from exc
        self.press_seconds = press_seconds
        self.settle_seconds = settle_seconds
        self.pad.reset()
        self.pad.update()
        time.sleep(0.8)

    def close(self):
        try:
            self.pad.reset()
            self.pad.update()
        except Exception:
            pass

    def tap(self, button, *, settle: float | None = None, hold: float | None = None):
        self.pad.press_button(button=button)
        self.pad.update()
        time.sleep(self.press_seconds if hold is None else max(0.01, hold))
        self.pad.release_button(button=button)
        self.pad.update()
        time.sleep(self.settle_seconds if settle is None else max(0.0, settle))

    def right(self, n: int = 1, *, settle: float | None = None):
        for _ in range(max(0, n)):
            self.tap(self.vg.XUSB_BUTTON.XUSB_GAMEPAD_DPAD_RIGHT, settle=settle)

    def left(self, n: int = 1, *, settle: float | None = None):
        for _ in range(max(0, n)):
            self.tap(self.vg.XUSB_BUTTON.XUSB_GAMEPAD_DPAD_LEFT, settle=settle)

    def down(self, n: int = 1, *, settle: float | None = None):
        # Row changes are where the game UI most often drops input. Keep these a
        # little longer than left/right so the S-turn after the 7th item is not missed.
        for _ in range(max(0, n)):
            self.tap(self.vg.XUSB_BUTTON.XUSB_GAMEPAD_DPAD_DOWN, settle=settle, hold=max(self.press_seconds, 0.095))

    def up(self, n: int = 1, *, settle: float | None = None):
        for _ in range(max(0, n)):
            self.tap(self.vg.XUSB_BUTTON.XUSB_GAMEPAD_DPAD_UP, settle=settle, hold=max(self.press_seconds, 0.095))

    def _probe_after_right(self, capture, wait_seconds: float) -> tuple[ImageDiffScore, ImageDiffScore, str]:
        before_detail = capture.capture_detail_panel()
        try:
            before_probe = capture.capture_input_probe_region()
        except Exception:
            before_probe = before_detail
        self.right(1, settle=0.0)
        time.sleep(max(0.0, wait_seconds))
        after_detail = capture.capture_detail_panel()
        try:
            after_probe = capture.capture_input_probe_region()
        except Exception:
            after_probe = after_detail
        detail_score = _image_difference_score(before_detail, after_detail)
        probe_score = _image_difference_score(before_probe, after_probe)
        reason = f'detail({detail_score.short()}), probe({probe_score.short()})'
        return detail_score, probe_score, reason

    def wait_until_game_accepts_input(
        self,
        capture,
        *,
        total_count: int = 0,
        timeout: float = 18.0,
        progress_callback=None,
        log_callback=None,
    ) -> bool:
        if total_count <= 1:
            time.sleep(1.2)
            return True
        start = time.time()
        attempt = 0
        wait_pattern = (0.35, 0.65, 0.95)
        last_reason = ''
        while time.time() - start < timeout:
            attempt += 1
            if progress_callback and (attempt == 1 or attempt % 2 == 0):
                progress_callback(0, f'컨트롤러 입력 인식 확인 중... {attempt}')
            try:
                detail_score = ImageDiffScore()
                probe_score = ImageDiffScore()
                reason = ''
                for wait_seconds in wait_pattern:
                    detail_score, probe_score, reason = self._probe_after_right(capture, wait_seconds)
                    try:
                        self.left(1, settle=0.45)
                    except Exception:
                        pass
                    last_reason = f'attempt={attempt}, wait={wait_seconds:.2f}, {reason}'
                    if log_callback:
                        log_callback(f'[input_probe] {last_reason}')
                    if detail_score.passed or probe_score.passed:
                        time.sleep(0.55)
                        if progress_callback:
                            progress_callback(0, '컨트롤러 입력 반응 감지 완료')
                        return True
                    time.sleep(0.25)
            except Exception as exc:
                last_reason = f'attempt={attempt}, error={exc.__class__.__name__}: {exc}'
                if log_callback:
                    log_callback(f'[input_probe] {last_reason}')
            try:
                self.pad.reset()
                self.pad.update()
            except Exception:
                pass
            time.sleep(0.75)
        if log_callback:
            log_callback(f'[input_probe] timeout. last={last_reason}')
        return False

    def move_between(self, current: tuple[int, int], target: tuple[int, int]):
        cr, cc = current
        tr, tc = target
        if tr > cr:
            self.down(tr - cr)
        elif tr < cr:
            self.up(cr - tr)
        if tc > cc:
            self.right(tc - cc)
        elif tc < cc:
            self.left(cc - tc)

    def move_to_step(self, current_step, target_step):
        """Move from one planned grid item to the next planned grid item.

        The old implementation always pressed DOWN before horizontal movement
        when changing rows. That fails for partial/tail-safe rows: after the 7th
        item, DOWN from column 6 can be ignored when the next row only has a few
        items starting from column 0. For safe LTR tail rows, move horizontally
        on the current complete row first, then press DOWN.
        """
        cr, cc = current_step.row, current_step.col
        tr, tc = target_step.row, target_step.col
        if tr == cr:
            if tc > cc:
                self.right(tc - cc)
            elif tc < cc:
                self.left(cc - tc)
            return

        if tr > cr and tc < cc and getattr(target_step, 'tail_safe', False):
            # Partial-row safe mode: return to the left edge before moving down.
            self.left(cc - tc, settle=0.075)
            self.down(tr - cr, settle=0.22)
            return

        if tr > cr and tc > cc and getattr(target_step, 'tail_safe', False):
            self.right(tc - cc, settle=0.075)
            self.down(tr - cr, settle=0.22)
            return

        # Normal snake transition: e.g. row0 col6 -> row1 col6.
        if tr > cr:
            self.down(tr - cr, settle=0.22)
        elif tr < cr:
            self.up(cr - tr, settle=0.22)
        if tc > cc:
            self.right(tc - cc)
        elif tc < cc:
            self.left(cc - tc)
