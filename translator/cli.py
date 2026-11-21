"""CLI-точка входа: запись → STT → перевод → TTS.

Пример:
    python -m translator.cli --target en --duration 5 --tts-out out.mp3
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

from .config import Config
from .history.store import HistoryStore
from .logging_setup import setup_logging
from .pipeline import TranslationPipeline
from .stt.groq_stt import GroqTranscriber
from .translate.deepseek import DeepSeekTranslator
from .tts.edge_tts import EdgeTTSSynthesizer


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="translator",
        description="Синхронный переводчик: запись → STT → перевод → TTS",
    )
    p.add_argument("--target", required=True, help="Целевой язык (например, en)")
    p.add_argument("--source", default=None, help="Исходный язык (по умолчанию авто)")
    p.add_argument("--audio", required=True, help="Путь к аудиофайлу для распознавания")
    p.add_argument("--tts-out", default=None, help="Куда сохранить озвучку (mp3)")
    p.add_argument("--model", default=None, help="Модель Groq Whisper (по умолчанию из env)")
    p.add_argument("--author", default="user", help="Автор реплики для истории")
    p.add_argument("--history", default=None, help="Путь к SQLite истории (по умолчанию из env)")
    p.add_argument("--no-history", action="store_true", help="Не писать в историю")
    p.add_argument("-v", "--verbose", action="store_true")
    return p


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    cfg = Config.from_env()
    setup_logging("DEBUG" if args.verbose else cfg.log_level)

    audio_path = Path(args.audio)
    if not audio_path.exists():
        print(f"Файл не найден: {audio_path}", file=sys.stderr)
        return 1

    stt = GroqTranscriber(
        api_key=cfg.groq_api_key,
        model=args.model or cfg.groq_model,
        base_url=cfg.groq_base_url,
        timeout=cfg.groq_timeout,
    )
    translator = DeepSeekTranslator(
        api_key=cfg.deepseek_api_key,
        base_url=cfg.deepseek_base_url,
        model=cfg.deepseek_model,
        timeout=cfg.deepseek_timeout,
    )
    tts = (
        EdgeTTSSynthesizer(rate=cfg.tts_rate, volume=cfg.tts_volume)
        if args.tts_out
        else None
    )

    pipeline = TranslationPipeline(stt=stt, translator=translator, tts=tts)
    result = pipeline.run(
        audio_path,
        target_lang=args.target,
        source_lang=args.source,
        tts_output=args.tts_out,
    )

    print(f"\nОригинал: {result.transcription.text}")
    print(f"Перевод:  {result.translation.text}")
    if result.synthesis:
        print(f"Аудио:    {result.synthesis.audio_path}")

    if not args.no_history:
        history_path = args.history or cfg.history_db_path
        with HistoryStore(history_path) as store:
            store.add(
                author=args.author,
                original_text=result.transcription.text,
                translated_text=result.translation.text,
                source_lang=result.transcription.language or args.source,
                target_lang=args.target,
            )
        print(f"История:  {Path(history_path).resolve()}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
