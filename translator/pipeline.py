"""Пайплайн: аудио → STT → перевод → TTS.

Связывает компоненты через протоколы, чтобы их можно было подменять
в тестах и в разных режимах (CLI, WebSocket, AR).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from .stt.base import Transcriber, TranscriptionResult
from .translate.base import TranslationResult, Translator
from .tts.base import SynthesisResult, Synthesizer

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class PipelineResult:
    """Результат полного прохода пайплайна."""

    transcription: TranscriptionResult
    translation: TranslationResult
    synthesis: Optional[SynthesisResult] = None


class TranslationPipeline:
    """Связка STT → перевод → (опционально) TTS.

    Пример:
        pipe = TranslationPipeline(stt, translator, tts)
        res = pipe.run("audio.wav", target_lang="en", tts_output="out.mp3")
        print(res.translation.text)
    """

    def __init__(
        self,
        stt: Transcriber,
        translator: Translator,
        tts: Optional[Synthesizer] = None,
    ) -> None:
        self.stt = stt
        self.translator = translator
        self.tts = tts

    def run(
        self,
        audio_path: str | Path,
        target_lang: str,
        source_lang: Optional[str] = None,
        tts_output: Optional[str | Path] = None,
    ) -> PipelineResult:
        transcription = self.stt.transcribe(audio_path, language=source_lang)
        if not transcription.text:
            raise RuntimeError("STT не распознал речь")

        translation = self.translator.translate(
            transcription.text,
            target_lang=target_lang,
            source_lang=source_lang or transcription.language,
        )

        synthesis: Optional[SynthesisResult] = None
        if self.tts is not None and tts_output is not None:
            synthesis = self.tts.synthesize(
                translation.text,
                tts_output,
                language=target_lang,
            )

        logger.info(
            "Пайплайн завершён: %s -> %s (%s символов)",
            transcription.language or source_lang or "auto",
            target_lang,
            len(translation.text),
        )
        return PipelineResult(
            transcription=transcription,
            translation=translation,
            synthesis=synthesis,
        )
