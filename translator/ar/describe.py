"""Описание/перевод распознанного текста на кадре.

Модуль связывает OCR-блоки с переводчиком: склеивает текст, переводит
его на язык пользователя и возвращает результат с привязкой к bbox
первого блока (для overlay).

Не зависит от камеры и конкретного OCR/переводчика — работает через
протоколы `OCR`-подобного интерфейса и `Translator`.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Optional, Protocol, Sequence

from ..translate.base import Translator
from .ocr import OCRBlock

logger = logging.getLogger(__name__)


class _Recognizer(Protocol):
    def recognize(self, frame) -> list[OCRBlock]:  # noqa: ANN001
        ...


class DescribeError(RuntimeError):
    """Ошибка описания/перевода объекта."""


@dataclass(frozen=True)
class DescribedBlock:
    """Перевод одного OCR-блока с привязкой к его bbox."""

    original_text: str
    translated_text: str
    bbox: tuple[int, int, int, int]
    confidence: float


@dataclass(frozen=True)
class DescribeResult:
    """Результат описания кадра."""

    blocks: list[DescribedBlock]
    source_lang: Optional[str]
    target_lang: str

    @property
    def combined_original(self) -> str:
        return " ".join(b.original_text for b in self.blocks)

    @property
    def combined_translated(self) -> str:
        return " ".join(b.translated_text for b in self.blocks)


class ObjectDescriber:
    """Распознаёт текст на кадре и переводит его на язык пользователя.

    Пример:
        describer = ObjectDescriber(ocr=OCR(lang="eng"), translator=tr)
        result = describer.describe(frame, target_lang="ru", source_lang="en")
        for b in result.blocks:
            print(b.bbox, b.original_text, "->", b.translated_text)
    """

    def __init__(
        self,
        ocr: _Recognizer,
        translator: Translator,
        min_confidence: float = 0.0,
    ) -> None:
        if not (0.0 <= min_confidence <= 100.0):
            raise ValueError("min_confidence должен быть в диапазоне [0, 100]")
        self.ocr = ocr
        self.translator = translator
        self.min_confidence = min_confidence

    def describe(
        self,
        frame,  # noqa: ANN001
        target_lang: str,
        source_lang: Optional[str] = None,
    ) -> DescribeResult:
        if not target_lang:
            raise ValueError("Не указан целевой язык")
        if frame is None:
            raise DescribeError("Пустой кадр")

        blocks: Sequence[OCRBlock] = self.ocr.recognize(frame)
        blocks = [b for b in blocks if b.confidence >= self.min_confidence]
        if not blocks:
            logger.info("Описание: на кадре не найдено текста")
            return DescribeResult(blocks=[], source_lang=source_lang, target_lang=target_lang)

        described: list[DescribedBlock] = []
        for block in blocks:
            try:
                translation = self.translator.translate(
                    block.text,
                    target_lang=target_lang,
                    source_lang=source_lang,
                )
            except Exception as exc:  # noqa: BLE001
                raise DescribeError(
                    f"Ошибка перевода блока {block.text!r}: {exc}"
                ) from exc
            described.append(
                DescribedBlock(
                    original_text=block.text,
                    translated_text=translation.text,
                    bbox=block.bbox,
                    confidence=block.confidence,
                )
            )

        logger.info(
            "Описание: блоков=%s, %s -> %s",
            len(described),
            source_lang or "auto",
            target_lang,
        )
        return DescribeResult(
            blocks=described,
            source_lang=source_lang,
            target_lang=target_lang,
        )
