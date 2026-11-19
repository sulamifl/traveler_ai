"""Отрисовка результатов AR поверх кадра через OpenCV.

Модуль не зависит от камеры/OCR/перевода — только рисование. OpenCV
импортируется лениво, чтобы тесты и CLI без AR работали без него.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Optional, Sequence

from .describe import DescribedBlock

logger = logging.getLogger(__name__)

DEFAULT_BOX_COLOR = (0, 255, 0)      # BGR: зелёный
DEFAULT_TEXT_COLOR = (255, 255, 255)  # BGR: белый
DEFAULT_BG_COLOR = (0, 0, 0)          # BGR: чёрный
DEFAULT_THICKNESS = 2
DEFAULT_FONT_SCALE = 0.6
DEFAULT_FONT = 0  # cv2.FONT_HERSHEY_SIMPLEX


class OverlayError(RuntimeError):
    """Ошибка отрисовки overlay."""


@dataclass(frozen=True)
class OverlayStyle:
    """Стиль отрисовки."""

    box_color: tuple[int, int, int] = DEFAULT_BOX_COLOR
    text_color: tuple[int, int, int] = DEFAULT_TEXT_COLOR
    bg_color: tuple[int, int, int] = DEFAULT_BG_COLOR
    thickness: int = DEFAULT_THICKNESS
    font_scale: float = DEFAULT_FONT_SCALE
    font: int = DEFAULT_FONT


class OverlayRenderer:
    """Рисует рамки и перевод поверх кадра.

    Пример:
        renderer = OverlayRenderer()
        out = renderer.render(frame, result.blocks)
        cv2.imshow("AR", out)
    """

    def __init__(self, style: Optional[OverlayStyle] = None) -> None:
        self.style = style or OverlayStyle()

    def _ensure_cv2(self) -> Any:
        try:
            import cv2  # локальный импорт: тесты могут мокать
        except ImportError as exc:  # pragma: no cover
            raise OverlayError(
                "opencv-python не установлен. Установите: pip install opencv-python"
            ) from exc
        return cv2

    def render(
        self,
        frame: Any,
        blocks: Sequence[DescribedBlock],
        copy: bool = True,
    ) -> Any:
        """Нарисовать блоки на кадре. Возвращает новый кадр (или тот же при copy=False)."""
        if frame is None:
            raise OverlayError("Пустой кадр")

        cv2 = self._ensure_cv2()
        canvas = frame.copy() if copy else frame

        for block in blocks:
            x, y, w, h = block.bbox
            cv2.rectangle(
                canvas,
                (x, y),
                (x + w, y + h),
                self.style.box_color,
                self.style.thickness,
            )
            self._draw_label(cv2, canvas, block.translated_text, x, y, h)

        logger.info("Overlay: отрисовано блоков=%s", len(blocks))
        return canvas

    def _draw_label(
        self,
        cv2: Any,
        canvas: Any,
        text: str,
        x: int,
        y: int,
        box_height: int,
    ) -> None:
        if not text:
            return
        (tw, th), baseline = cv2.getTextSize(
            text, self.style.font, self.style.font_scale, self.style.thickness
        )
        # Подпись над рамкой; если места нет — под ней
        label_y = y - 4
        if label_y - th < 0:
            label_y = y + box_height + th + 4

        cv2.rectangle(
            canvas,
            (x, label_y - th - baseline),
            (x + tw, label_y + baseline),
            self.style.bg_color,
            -1,
        )
        cv2.putText(
            canvas,
            text,
            (x, label_y),
            self.style.font,
            self.style.font_scale,
            self.style.text_color,
            self.style.thickness,
            cv2.LINE_AA,
        )
