"""Модель групповой сессии перевода.

Сессия хранит участников, их роли и языки. Отвечает за маршрутизацию:
кому и на какой язык нужно перевести очередную реплику.

Модуль не зависит от сети — это чистая логика, которую использует
WebSocket-сервер и CLI.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Literal, Optional

logger = logging.getLogger(__name__)

Role = Literal["speaker", "listener"]


class SessionError(RuntimeError):
    """Ошибка работы с сессией."""


@dataclass
class Participant:
    """Участник сессии."""

    id: str
    name: str
    language: str
    role: Role = "listener"


@dataclass
class Session:
    """Групповая сессия перевода.

    Пример:
        s = Session(session_id="demo")
        s.add_participant("alice", "Alice", language="ru", role="speaker")
        s.add_participant("bob", "Bob", language="en")
        routes = s.route("Привет", source_lang="ru")
        # -> [("bob", "en")]
    """

    session_id: str
    participants: dict[str, Participant] = field(default_factory=dict)
    speaker_id: Optional[str] = None

    def add_participant(
        self,
        participant_id: str,
        name: str,
        language: str,
        role: Role = "listener",
    ) -> Participant:
        if not participant_id:
            raise SessionError("participant_id не может быть пустым")
        if not language:
            raise SessionError("language не может быть пустым")
        if participant_id in self.participants:
            raise SessionError(f"Участник уже существует: {participant_id}")

        p = Participant(id=participant_id, name=name, language=language, role=role)
        self.participants[participant_id] = p
        if role == "speaker":
            self.speaker_id = participant_id
        logger.info(
            "Сессия %s: добавлен %s (%s, %s)",
            self.session_id,
            participant_id,
            language,
            role,
        )
        return p

    def remove_participant(self, participant_id: str) -> None:
        if participant_id not in self.participants:
            raise SessionError(f"Участник не найден: {participant_id}")
        del self.participants[participant_id]
        if self.speaker_id == participant_id:
            self.speaker_id = None

    def set_speaker(self, participant_id: str) -> None:
        if participant_id not in self.participants:
            raise SessionError(f"Участник не найден: {participant_id}")
        for p in self.participants.values():
            p.role = "listener"
        self.participants[participant_id].role = "speaker"
        self.speaker_id = participant_id

    def route(
        self,
        text: str,
        source_lang: str,
        author_id: Optional[str] = None,
    ) -> list[tuple[str, str]]:
        """Кому переводить реплику говорящего.

        Возвращает список `(participant_id, target_lang)` для всех
        участников, кроме автора реплики. Если язык участника совпадает
        с исходным — пропускаем (перевод не нужен).
        """
        if not text or not text.strip():
            raise SessionError("Пустой текст реплики")

        routes: list[tuple[str, str]] = []
        for p in self.participants.values():
            if p.id == author_id:
                continue
            if p.language == source_lang:
                continue
            routes.append((p.id, p.language))
        return routes

    def route_question(
        self,
        text: str,
        source_lang: str,
        author_id: Optional[str] = None,
    ) -> list[tuple[str, str]]:
        """Вопрос из группы → перевод на язык основного говорящего.

        Если основной говорящий не задан — ошибка.
        """
        if not text or not text.strip():
            raise SessionError("Пустой текст вопроса")
        if self.speaker_id is None:
            raise SessionError("В сессии нет основного говорящего")

        speaker = self.participants[self.speaker_id]
        if speaker.id == author_id:
            return []
        if speaker.language == source_lang:
            return []
        return [(speaker.id, speaker.language)]
