from __future__ import annotations

from pathlib import Path
from typing import Any

from app.loadout_data import DRIVE_MODULES, module_image_path


class ShapeTemplateMatcher:
    def __init__(self):
        self.templates: list[tuple[str, str, Any]] = []
        self._load_templates()

    def _prep(self, img, size: int = 72, *, detail_badge: bool = False):
        import cv2  # type: ignore
        import numpy as np  # type: ignore
        if not isinstance(img, np.ndarray):
            arr = np.array(img.convert('RGB'))
        else:
            arr = img
        h, w = arr.shape[:2]
        if w > 0 and h > 0:
            if detail_badge:
                # In the game detail panel crop, the actual module icon sits in
                # the upper half of the big circular badge.  The old center crop
                # mostly captured the badge background and missed the shape.
                arr = arr[0:int(h * 0.56), int(w * 0.10):int(w * 0.90)]
            else:
                # Template assets have a white background.  Crop to the non-white
                # foreground so template matching focuses on the block shape.
                if arr.ndim == 3:
                    bg_mask = (arr[:, :, 0] > 245) & (arr[:, :, 1] > 245) & (arr[:, :, 2] > 245)
                    fg = ~bg_mask
                    ys, xs = np.where(fg)
                    if len(xs) and len(ys):
                        pad = 4
                        x1, x2 = max(0, xs.min() - pad), min(w, xs.max() + pad + 1)
                        y1, y2 = max(0, ys.min() - pad), min(h, ys.max() + pad + 1)
                        arr = arr[y1:y2, x1:x2]
        gray = cv2.cvtColor(arr, cv2.COLOR_RGB2GRAY) if arr.ndim == 3 else arr
        gray = cv2.resize(gray, (size, size))
        gray = cv2.equalizeHist(gray)
        edge = cv2.Canny(gray, 30, 90)
        return gray, edge

    def _load_templates(self):
        try:
            import cv2  # type: ignore
        except Exception:
            return
        seen = set()
        for module in DRIVE_MODULES:
            geometry = module.get('geometry')
            quality = module.get('quality')
            key = (geometry, quality)
            if key in seen:
                continue
            seen.add(key)
            path = module_image_path(module)
            if not path or not Path(path).exists():
                continue
            img = cv2.imread(str(path), cv2.IMREAD_COLOR)
            if img is None:
                continue
            img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
            gray, edge = self._prep(img, detail_badge=False)
            self.templates.append((geometry, quality, (gray, edge)))

    def match(self, image) -> tuple[str, str, float]:
        if not self.templates:
            return '', '', 0.0
        try:
            import cv2  # type: ignore
        except Exception:
            return '', '', 0.0
        gray, edge = self._prep(image, detail_badge=True)
        best = ('', '', -1.0)
        for geometry, quality, tmpl_pair in self.templates:
            tmpl_gray, tmpl_edge = tmpl_pair
            score_gray = float(cv2.matchTemplate(gray, tmpl_gray, cv2.TM_CCOEFF_NORMED)[0][0])
            score_edge = float(cv2.matchTemplate(edge, tmpl_edge, cv2.TM_CCOEFF_NORMED)[0][0])
            score = max(score_gray, score_edge)
            if score > best[2]:
                best = (geometry, quality, score)
        if best[2] < 0.45:
            return '', '', best[2]
        return best
