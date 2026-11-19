"""Единая настройка логирования для CLI и сервера."""

from __future__ import annotations

import logging

_DEFAULT_FORMAT = "%(asctime)s %(levelname)s %(name)s: %(message)s"


def setup_logging(level: str = "INFO", fmt: str = _DEFAULT_FORMAT) -> None:
    """Настроить корневой логгер.

    Идемпотентно: повторный вызов не добавляет дублирующих хендлеров.
    """
    numeric = getattr(logging, level.upper(), None)
    if not isinstance(numeric, int):
        raise ValueError(f"Неизвестный уровень логирования: {level!r}")

    root = logging.getLogger()
    root.setLevel(numeric)

    # Убираем ранее установленные нами хендлеры, чтобы не дублировать вывод
    for handler in list(root.handlers):
        if getattr(handler, "_translator_handler", False):
            root.removeHandler(handler)

    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter(fmt))
    handler._translator_handler = True  # type: ignore[attr-defined]
    root.addHandler(handler)
