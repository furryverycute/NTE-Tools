from __future__ import annotations

import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass
class CaptureRegion:
    left: int
    top: int
    width: int
    height: int

    def as_mss(self) -> dict[str, int]:
        return {'left': self.left, 'top': self.top, 'width': self.width, 'height': self.height}


def crop_inner_region(image, rel: tuple[float, float, float, float]):
    x1, y1, x2, y2 = rel
    w, h = image.size
    left = max(0, int(w * x1))
    top = max(0, int(h * y1))
    right = min(w, int(w * x2))
    bottom = min(h, int(h * y2))
    if right <= left or bottom <= top:
        return image
    return image.crop((left, top, right, bottom))


DETAIL_PANEL_REL = (0.695, 0.150, 0.970, 0.895)
DRIVE_ICON_REL = (0.715, 0.245, 0.815, 0.420)  # legacy direct screen crop; v26 uses detail-inner crop
# Inventory/grid area used only for input-response probing.
# The detail panel may not visibly change for same-looking items or delayed UI updates,
# so we also compare the left console list/grid highlight area.
INPUT_PROBE_REL = (0.045, 0.120, 0.690, 0.895)
# OCR crop regions inside the right detail panel.
# Keep title away from the big circular icon/ring text; OCRing the icon area was
# causing garbage such as 'RNESS' and broken roman-type strings.
DETAIL_TITLE_INNER_REL = (0.160, 0.035, 0.965, 0.235)
# The game separates 주속성 and 부속성 in the white card.  Cropping these bands
# separately greatly reduces level/value noise.
DETAIL_MAIN_INNER_REL = (0.035, 0.380, 0.725, 0.530)
DETAIL_SUB_INNER_REL = (0.035, 0.495, 0.725, 0.812)
# Narrow text-only versions used as a second OCR pass when the left icons confuse OCR.
DETAIL_MAIN_TEXT_INNER_REL = (0.045, 0.385, 0.700, 0.530)
DETAIL_SUB_TEXT_INNER_REL = (0.045, 0.500, 0.700, 0.812)
# Central module glyph inside the detail panel.  This avoids the title/level text
# and keeps the actual module icon centered for shape matching.
DETAIL_ICON_INNER_REL = (0.055, 0.200, 0.270, 0.330)


class WindowCapture:
    def __init__(self, title_keywords: list[str] | None = None, process_names: list[str] | None = None):
        self.title_keywords = title_keywords or ['Neverness', 'Everness', 'NTE', '이환', 'HTGame']
        self.process_names = [name.lower() for name in (process_names or ['HTGame.exe'])]
        self.hwnd = None
        self.window_rect = self._find_window_rect()
        self._sct = None

    def close(self):
        if self._sct is not None:
            try:
                self._sct.close()
            except Exception:
                pass
            self._sct = None

    def _process_name_for_hwnd(self, hwnd) -> str:
        try:
            import win32api  # type: ignore
            import win32con  # type: ignore
            import win32process  # type: ignore
        except Exception:
            return ''
        try:
            _, pid = win32process.GetWindowThreadProcessId(hwnd)
            handle = win32api.OpenProcess(
                win32con.PROCESS_QUERY_INFORMATION | win32con.PROCESS_VM_READ,
                False,
                pid,
            )
            try:
                path = win32process.GetModuleFileNameEx(handle, 0)
            finally:
                win32api.CloseHandle(handle)
            return Path(path).name.lower()
        except Exception:
            return ''

    def _client_rect_for_hwnd(self, hwnd):
        try:
            import win32gui  # type: ignore
            left, top, right, bottom = win32gui.GetClientRect(hwnd)
            x, y = win32gui.ClientToScreen(hwnd, (left, top))
            x2, y2 = win32gui.ClientToScreen(hwnd, (right, bottom))
            if x2 > x and y2 > y:
                return (x, y, x2 - x, y2 - y)
        except Exception:
            return None
        return None

    def _find_window_rect(self) -> tuple[int, int, int, int] | None:
        try:
            import win32gui  # type: ignore
        except Exception:
            return None
        matches: list[tuple[int, int, int, int, int, int]] = []
        keywords = [kw.lower() for kw in self.title_keywords]

        def enum_cb(hwnd, _):
            if not win32gui.IsWindowVisible(hwnd):
                return
            title = win32gui.GetWindowText(hwnd) or ''
            proc = self._process_name_for_hwnd(hwnd)
            title_match = bool(title and any(kw in title.lower() for kw in keywords))
            proc_match = bool(proc and proc in self.process_names)
            if not title_match and not proc_match:
                return
            rect = self._client_rect_for_hwnd(hwnd)
            if rect:
                priority = 0 if proc_match else 1
                matches.append((priority, hwnd, rect[0], rect[1], rect[2], rect[3]))

        try:
            win32gui.EnumWindows(enum_cb, None)
        except Exception:
            pass
        if matches:
            matches.sort(key=lambda it: (it[0], -(it[4] * it[5])))
            _, hwnd, x, y, w, h = matches[0]
            self.hwnd = hwnd
            return (x, y, w, h)
        try:
            hwnd = win32gui.GetForegroundWindow()
            rect = self._client_rect_for_hwnd(hwnd)
            if rect:
                self.hwnd = hwnd
                return rect
        except Exception:
            return None
        return None

    def refresh_window(self) -> tuple[int, int, int, int] | None:
        self.window_rect = self._find_window_rect()
        return self.window_rect

    def activate_game_window(self) -> bool:
        """Bring HTGame.exe/NTE window to foreground before scanning."""
        self.refresh_window()
        if not self.hwnd:
            return False
        try:
            import win32con  # type: ignore
            import win32gui  # type: ignore
            try:
                win32gui.ShowWindow(self.hwnd, win32con.SW_RESTORE)
            except Exception:
                pass
            try:
                win32gui.SetForegroundWindow(self.hwnd)
            except Exception:
                # Windows may deny focus stealing. Click-free fallback still keeps
                # the captured rect from the detected HTGame.exe window.
                pass
            time.sleep(0.45)
            self.refresh_window()
            return True
        except Exception:
            return False

    def _mss(self):
        import mss  # type: ignore
        if self._sct is None:
            self._sct = mss.mss()
        return self._sct

    def _monitor_rect(self) -> tuple[int, int, int, int]:
        sct = self._mss()
        mon = sct.monitors[1]
        return mon['left'], mon['top'], mon['width'], mon['height']

    def base_rect(self) -> tuple[int, int, int, int]:
        if self.window_rect is None:
            self.refresh_window()
        return self.window_rect or self._monitor_rect()

    def region_from_relative(self, rel: tuple[float, float, float, float]) -> CaptureRegion:
        x, y, w, h = self.base_rect()
        x1, y1, x2, y2 = rel
        return CaptureRegion(
            int(x + w * x1),
            int(y + h * y1),
            max(1, int(w * (x2 - x1))),
            max(1, int(h * (y2 - y1))),
        )

    def capture_region(self, region: CaptureRegion, save_path: str | Path | None = None):
        from PIL import Image  # type: ignore
        sct = self._mss()
        shot = sct.grab(region.as_mss())
        image = Image.frombytes('RGB', shot.size, shot.rgb)
        if save_path:
            Path(save_path).parent.mkdir(parents=True, exist_ok=True)
            image.save(save_path)
        return image

    def capture_detail_panel(self, save_path: str | Path | None = None):
        time.sleep(0.03)
        return self.capture_region(self.region_from_relative(DETAIL_PANEL_REL), save_path)

    def capture_drive_icon(self, save_path: str | Path | None = None):
        # Legacy direct screen crop kept for compatibility.  The scanner now
        # normally uses crop_drive_icon_from_detail(detail_img), because it is
        # more stable across window sizes and avoids drifting into title text.
        return self.capture_region(self.region_from_relative(DRIVE_ICON_REL), save_path)

    def crop_drive_icon_from_detail(self, detail_image, save_path: str | Path | None = None):
        image = crop_inner_region(detail_image, DETAIL_ICON_INNER_REL)
        if save_path:
            Path(save_path).parent.mkdir(parents=True, exist_ok=True)
            image.save(save_path)
        return image

    def capture_input_probe_region(self, save_path: str | Path | None = None):
        # Used for controller input readiness detection. This area intentionally
        # excludes most of the right detail panel and focuses on the item grid,
        # where selection-border movement is visible even when the detail text is
        # similar or updates slowly.
        return self.capture_region(self.region_from_relative(INPUT_PROBE_REL), save_path)

    def split_detail_ocr_regions(self, detail_image):
        return {
            'title': crop_inner_region(detail_image, DETAIL_TITLE_INNER_REL),
            'main': crop_inner_region(detail_image, DETAIL_MAIN_INNER_REL),
            'main_text': crop_inner_region(detail_image, DETAIL_MAIN_TEXT_INNER_REL),
            'sub': crop_inner_region(detail_image, DETAIL_SUB_INNER_REL),
            'sub_text': crop_inner_region(detail_image, DETAIL_SUB_TEXT_INNER_REL),
            # Full-panel OCR is intentionally skipped during normal scanning because
            # it is slow and noisy. It is saved as an image in debug mode instead.
        }
