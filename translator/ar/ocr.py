"""Распознавание текста на кадре через Tesseract (pytesseract).

Модуль не зависит от камеры и перевода — только OCR. `pytesseract`
импортируется лениво, чтобы тесты и CLI без AR работали без него.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Optional

logger = logging.getLogger(__name__)

DEFAULT_LANG = "eng"
DEFAULT_MIN_CONFIDENCE = 40.0


class OCRError(RuntimeError):
    """Ошибка распознавания текста."""


@dataclass(frozen=True)
class OCRBlock:
    """Один распознанный фрагмент текста."""

    text: str
    confidence: float
    left: int
    top: int
    width: int
    height: int

    @property
    def bbox(self) -> tuple[int, int, int, int]:
        """(x, y, w, h) — удобно для overlay."""
        return (self.left, self.top, self.width, self.height)


class OCR:
    """Обёртка над `pytesseract.image_to_data`.

    Пример:
        ocr = OCR(lang="eng")
        blocks = ocr.recognize(frame)   # frame — numpy.ndarray (BGR)
        for b in blocks:
            print(b.text, b.bbox, b.confidence)
    """

    def __init__(
        self,
        lang: str = DEFAULT_LANG,
        min_confidence: float = DEFAULT_MIN_CONFIDENCE,
        tesseract_cmd: Optional[str] = None,
    ) -> None:
        if not lang:
            raise ValueError("lang не может быть пустым")
        if not (0.0 <= min_confidence <= 100.0):
            raise ValueError("min_confidence должен быть в диапазоне [0, 100]")
        self.lang = lang
        self.min_confidence = min_confidence
        self.tesseract_cmd = tesseract_cmd

    def _ensure_pytesseract(self) -> Any:
        try:
            import pytesseract  # локальный импорт: тесты могут мокать
        except ImportError as exc:  # pragma: no cover
            raise OCRError(
                "pytesseract не установлен. Установите: pip install pytesseract Pillow"
            ) from exc
        if self.tesseract_cmd:
            pytesseract.pytesseract.tesseract_cmd = self.tesseract_cmd
        return pytesseract

    def recognize(self, frame: Any) -> list[OCRBlock]:
        """Распознать текст на кадре (numpy.ndarray в BGR или RGB)."""
        if frame is None:
            raise OCRError("Пустой кадр")

        pytesseract = self._ensure_pytesseract()

        try:
            data = pytesseract.image_to_data(
                frame,
                lang=self.lang,
                output_type=pytesseract.Output.DICT,
            )
        except Exception as exc:  # noqa: BLE001
            raise OCRError(f"Ошибка OCR: {exc}") from exc

        blocks: list[OCRBlock] = []
        n = len(data.get("text", []))
        for i in range(n):
            text = (data["text"][i] or "").strip()
            if not text:
                continue
            try:
                conf = float(data["conf"][i])
            except (TypeError, ValueError):
                continue
            if conf < self.min_confidence:
                continue
            blocks.append(
                OCRBlock(
                    text=text,
                    confidence=conf,
                    left=int(data["left"][i]),
                    top=int(data["top"][i]),
                    width=int(data["width"][i]),
                    height=int(data["height"][i]),
                )
            )

        logger.info(
            "OCR: lang=%s, найдено блоков=%s (min_conf=%.1f)",
            self.lang,
            len(blocks),
            self.min_confidence,
        )
        return blocks
