"""Интерфейсы для модуля перевода.

Все реализации переводчика возвращают `TranslationResult`,
чтобы пайплайн не зависел от конкретного провайдера.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, runtime_checkable


@dataclass(frozen=True)
class TranslationResult:
    """Результат перевода."""

    text: str
    source_lang: str | None = None
    target_lang: str | None = None


@runtime_checkable
class Translator(Protocol):
    """Протокол любого движка перевода."""

    def translate(
        self,
        text: str,
        target_lang: str,
        source_lang: str | None = None,
    ) -> TranslationResult:
        """Перевести текст на `target_lang`."""
        ...
