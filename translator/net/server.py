"""WebSocket-сервер группового перевода на FastAPI.

Протокол сообщений (JSON):
    {"type": "join", "participant_id": "...", "name": "...", "language": "ru", "role": "speaker"}
    {"type": "leave", "participant_id": "..."}
    {"type": "set_speaker", "participant_id": "..."}
    {"type": "speak", "participant_id": "...", "text": "...", "source_lang": "ru"}
    {"type": "question", "participant_id": "...", "text": "...", "source_lang": "en"}

Ответы:
    {"type": "translation", "to": "<participant_id>", "target_lang": "en",
     "original": "...", "text": "..."}
    {"type": "error", "message": "..."}
"""

from __future__ import annotations

import logging
from typing import Callable, Optional

from fastapi import FastAPI, WebSocket, WebSocketDisconnect

from ..history.store import HistoryStore
from ..translate.base import Translator
from .session import Session, SessionError

logger = logging.getLogger(__name__)

TranslatorFactory = Callable[[], Translator]
HistoryFactory = Callable[[], HistoryStore]


class SessionRegistry:
    """Хранилище сессий и активных WebSocket-подключений."""

    def __init__(self) -> None:
        self.sessions: dict[str, Session] = {}
        self.connections: dict[str, dict[str, WebSocket]] = {}

    def get_or_create(self, session_id: str) -> Session:
        if session_id not in self.sessions:
            self.sessions[session_id] = Session(session_id=session_id)
            self.connections[session_id] = {}
        return self.sessions[session_id]

    def register(self, session_id: str, participant_id: str, ws: WebSocket) -> None:
        self.connections.setdefault(session_id, {})[participant_id] = ws

    def unregister(self, session_id: str, participant_id: str) -> None:
        conns = self.connections.get(session_id)
        if conns:
            conns.pop(participant_id, None)

    async def send_to(self, session_id: str, participant_id: str, payload: dict) -> None:
        ws = self.connections.get(session_id, {}).get(participant_id)
        if ws is None:
            return
        try:
            await ws.send_json(payload)
        except Exception as exc:  # noqa: BLE001
            logger.warning("Не удалось отправить %s: %s", participant_id, exc)


def create_app(
    translator_factory: Optional[TranslatorFactory] = None,
    history_factory: Optional[HistoryFactory] = None,
) -> FastAPI:
    """Создать FastAPI-приложение.

    `translator_factory` позволяет подменить переводчик в тестах.
    `history_factory` — фабрика `HistoryStore`; если задана, все реплики
    и вопросы сохраняются с автором и временем.
    """
    app = FastAPI(title="Translator AR — Group mode")
    registry = SessionRegistry()
    app.state.registry = registry
    app.state.history_factory = history_factory

    def _get_translator() -> Translator:
        if translator_factory is None:
            raise RuntimeError("translator_factory не задан")
        return translator_factory()

    def _record_history(
        author: str,
        original_text: str,
        translated_text: str,
        source_lang: Optional[str],
        target_lang: str,
    ) -> None:
        if history_factory is None:
            return
        try:
            with history_factory() as store:
                store.add(
                    author=author,
                    original_text=original_text,
                    translated_text=translated_text,
                    source_lang=source_lang,
                    target_lang=target_lang,
                )
        except Exception as exc:  # noqa: BLE001
            logger.warning("Не удалось записать историю: %s", exc)

    @app.websocket("/ws/{session_id}")
    async def ws_endpoint(websocket: WebSocket, session_id: str) -> None:
        await websocket.accept()
        session = registry.get_or_create(session_id)
        participant_id: Optional[str] = None

        try:
            while True:
                msg = await websocket.receive_json()
                mtype = msg.get("type")

                try:
                    if mtype == "join":
                        pid = msg["participant_id"]
                        session.add_participant(
                            pid,
                            msg.get("name", pid),
                            language=msg["language"],
                            role=msg.get("role", "listener"),
                        )
                        registry.register(session_id, pid, websocket)
                        participant_id = pid
                        await websocket.send_json(
                            {"type": "joined", "participant_id": pid}
                        )

                    elif mtype == "leave":
                        pid = msg["participant_id"]
                        session.remove_participant(pid)
                        registry.unregister(session_id, pid)
                        await websocket.send_json({"type": "left", "participant_id": pid})

                    elif mtype == "set_speaker":
                        session.set_speaker(msg["participant_id"])
                        await websocket.send_json(
                            {"type": "speaker_set", "participant_id": msg["participant_id"]}
                        )

                    elif mtype in ("speak", "question"):
                        pid = msg["participant_id"]
                        text = msg["text"]
                        source_lang = msg["source_lang"]
                        if mtype == "speak":
                            routes = session.route(text, source_lang, author_id=pid)
                        else:
                            routes = session.route_question(
                                text, source_lang, author_id=pid
                            )
                        translator = _get_translator()
                        author_name = session.participants[pid].name
                        for target_id, target_lang in routes:
                            result = translator.translate(
                                text, target_lang=target_lang, source_lang=source_lang
                            )
                            _record_history(
                                author=author_name,
                                original_text=text,
                                translated_text=result.text,
                                source_lang=source_lang,
                                target_lang=target_lang,
                            )
                            await registry.send_to(
                                session_id,
                                target_id,
                                {
                                    "type": "translation",
                                    "to": target_id,
                                    "target_lang": target_lang,
                                    "original": text,
                                    "text": result.text,
                                },
                            )

                    else:
                        await websocket.send_json(
                            {"type": "error", "message": f"Неизвестный тип: {mtype}"}
                        )

                except (SessionError, KeyError, ValueError) as exc:
                    await websocket.send_json({"type": "error", "message": str(exc)})

        except WebSocketDisconnect:
            logger.info("WebSocket отключён: session=%s, participant=%s", session_id, participant_id)
            if participant_id:
                registry.unregister(session_id, participant_id)
                try:
                    session.remove_participant(participant_id)
                except SessionError:
                    pass

    @app.get("/sessions/{session_id}/history")
    def get_history(session_id: str, limit: int = 50) -> dict:
        """Последние записи истории сессии (сначала новые)."""
        if history_factory is None:
            return {"session_id": session_id, "entries": []}
        with history_factory() as store:
            entries = store.list_recent(limit=limit)
        return {
            "session_id": session_id,
            "entries": [
                {
                    "id": e.id,
                    "author": e.author,
                    "original_text": e.original_text,
                    "translated_text": e.translated_text,
                    "source_lang": e.source_lang,
                    "target_lang": e.target_lang,
                    "created_at": e.created_at,
                }
                for e in entries
            ],
        }

    return app
