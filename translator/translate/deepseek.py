"""Перевод через DeepSeek Chat Completions API.

Использует `httpx`. Ключ берётся из аргумента `api_key` или из
переменной окружения `DEEPSEEK_API_KEY`.
"""

from __future__ import annotations

import logging
import os
from typing import Any, Optional

import httpx

from .base import TranslationResult

logger = logging.getLogger(__name__)

DEFAULT_BASE_URL = "https://api.deepseek.com"
DEFAULT_MODEL = "deepseek-chat"
DEFAULT_TIMEOUT = 30.0

_SYSTEM_PROMPT = (
    "Ты — профессиональный переводчик. Переводи текст точно, сохраняя смысл, "
    "тон и стиль. Возвращай ТОЛЬКО перевод, без пояснений и кавычек."
)


class TranslationError(RuntimeError):
    """Ошибка при обращении к API перевода."""


class DeepSeekTranslator:
    """Переводчик на базе DeepSeek Chat API.

    Пример:
        tr = DeepSeekTranslator(api_key="sk-...")
        res = tr.translate("Привет", target_lang="en")
        print(res.text)  # "Hello"
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: str = DEFAULT_BASE_URL,
        model: str = DEFAULT_MODEL,
        timeout: float = DEFAULT_TIMEOUT,
        client: Optional[httpx.Client] = None,
    ) -> None:
        self.api_key = api_key or os.environ.get("DEEPSEEK_API_KEY")
        if not self.api_key:
            raise TranslationError(
                "Не задан API-ключ DeepSeek. Передайте api_key или "
                "установите переменную окружения DEEPSEEK_API_KEY."
            )
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout = timeout
        self._client = client

    def _get_client(self) -> httpx.Client:
        if self._client is None:
            self._client = httpx.Client(timeout=self.timeout)
        return self._client

    def translate(
        self,
        text: str,
        target_lang: str,
        source_lang: str | None = None,
    ) -> TranslationResult:
        if not text or not text.strip():
            raise ValueError("Пустой текст для перевода")
        if not target_lang:
            raise ValueError("Не указан целевой язык")

        user_prompt = self._build_prompt(text, target_lang, source_lang)
        payload: dict[str, Any] = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": _SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": 0.2,
            "stream": False,
        }
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        client = self._get_client()
        try:
            response = client.post(
                f"{self.base_url}/chat/completions",
                json=payload,
                headers=headers,
            )
        except httpx.HTTPError as exc:
            raise TranslationError(f"Сетевая ошибка при переводе: {exc}") from exc

        if response.status_code >= 400:
            raise TranslationError(
                f"DeepSeek вернул {response.status_code}: {response.text[:200]}"
            )

        try:
            data = response.json()
            translated = data["choices"][0]["message"]["content"].strip()
        except (KeyError, IndexError, ValueError) as exc:
            raise TranslationError(
                f"Неожиданный ответ DeepSeek: {response.text[:200]}"
            ) from exc

        logger.info(
            "Перевод выполнен: %s -> %s (%s символов)",
            source_lang or "auto",
            target_lang,
            len(translated),
        )
        return TranslationResult(
            text=translated,
            source_lang=source_lang,
            target_lang=target_lang,
        )

    @staticmethod
    def _build_prompt(text: str, target_lang: str, source_lang: str | None) -> str:
        src = source_lang or "auto"
        return (
            f"Переведи следующий текст с языка '{src}' на язык '{target_lang}'.\n"
            f"Текст:\n{text}"
        )
