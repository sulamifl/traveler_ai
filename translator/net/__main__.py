"""Точка входа сервера: `python -m translator.net`.

Собирает приложение из `Config`: DeepSeek-переводчик, OCR, ObjectDescriber,
HistoryStore. Запускает uvicorn.
"""

from __future__ import annotations

import logging
import sys

from ..ar.describe import ObjectDescriber
from ..ar.ocr import OCR
from ..config import Config
from ..history.store import HistoryStore
from ..logging_setup import setup_logging
from ..stt.whisper_stt import WhisperTranscriber
from ..translate.deepseek import DeepSeekTranslator
from .server import create_app

logger = logging.getLogger(__name__)


def build_app(cfg: Config | None = None):
    """Собрать FastAPI-приложение из конфига."""
    cfg = cfg or Config.from_env()

    def translator_factory() -> DeepSeekTranslator:
        return DeepSeekTranslator(
            api_key=cfg.deepseek_api_key,
            base_url=cfg.deepseek_base_url,
            model=cfg.deepseek_model,
            timeout=cfg.deepseek_timeout,
        )

    def history_factory() -> HistoryStore:
        return HistoryStore(cfg.history_db_path)

    def describer_factory() -> ObjectDescriber:
        def ocr_factory(source_lang: str) -> OCR:
            # source_lang приходит из формы как код Tesseract (eng/rus/...).
            # Если пусто — используем английский по умолчанию.
            return OCR(lang=source_lang or "eng")

        return ObjectDescriber(
            ocr_factory=ocr_factory,
            translator=translator_factory(),
        )

    _stt_singleton: dict[str, WhisperTranscriber] = {}

    def stt_factory() -> WhisperTranscriber:
        # Модель Whisper тяжёлая — держим один экземпляр на процесс.
        if "stt" not in _stt_singleton:
            _stt_singleton["stt"] = WhisperTranscriber(
                model_size=cfg.whisper_model,
                device=cfg.whisper_device,
                compute_type=cfg.whisper_compute_type,
            )
        return _stt_singleton["stt"]

    return create_app(
        translator_factory=translator_factory,
        history_factory=history_factory,
        describer_factory=describer_factory,
        stt_factory=stt_factory,
    )


def main(argv: list[str] | None = None) -> int:
    import argparse

    p = argparse.ArgumentParser(prog="translator.net", description="WebSocket-сервер переводчика")
    p.add_argument("--host", default="127.0.0.1")
    p.add_argument("--port", type=int, default=8000)
    p.add_argument("--reload", action="store_true")
    p.add_argument("-v", "--verbose", action="store_true")
    args = p.parse_args(argv)

    cfg = Config.from_env()
    setup_logging("DEBUG" if args.verbose else cfg.log_level)

    if args.reload:
        # reload требует строку импорта, а не объект
        import uvicorn

        uvicorn.run(
            "translator.net.__main__:build_app",
            factory=True,
            host=args.host,
            port=args.port,
            reload=True,
        )
        return 0

    import uvicorn

    uvicorn.run(build_app(cfg), host=args.host, port=args.port)
    return 0


if __name__ == "__main__":
    sys.exit(main())
