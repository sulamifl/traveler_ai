"""Модуль перевода текста."""

from .base import TranslationResult, Translator
from .deepseek import DeepSeekTranslator, TranslationError

__all__ = [
    "TranslationResult",
    "Translator",
    "DeepSeekTranslator",
    "TranslationError",
]
