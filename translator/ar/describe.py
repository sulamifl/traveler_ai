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
from typing import Callable, Optional, Protocol, Sequence

from ..translate.base import Translator
from .ocr import OCRBlock

logger = logging.getLogger(__name__)


class _Recognizer(Protocol):
    def recognize(self, frame) -> list[OCRBlock]:  # noqa: ANN001
        ...


RecognizerFactory = Callable[[str], _Recognizer]


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
        ocr: Optional[_Recognizer] = None,
        translator: Optional[Translator] = None,
        min_confidence: float = 0.0,
        ocr_factory: Optional[RecognizerFactory] = None,
    ) -> None:
        if not (0.0 <= min_confidence <= 100.0):
            raise ValueError("min_confidence должен быть в диапазоне [0, 100]")
        if ocr is None and ocr_factory is None:
            raise ValueError("Нужен либо ocr, либо ocr_factory")
        if translator is None:
            raise ValueError("translator обязателен")
        self.ocr = ocr
        self.ocr_factory = ocr_factory
        self.translator = translator
        self.min_confidence = min_confidence

    def _get_recognizer(self, source_lang: Optional[str]) -> _Recognizer:
        if self.ocr_factory is not None:
            return self.ocr_factory(source_lang or "")
        assert self.ocr is not None
        return self.ocr

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

        recognizer = self._get_recognizer(source_lang)
        blocks: Sequence[OCRBlock] = recognizer.recognize(frame)
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
