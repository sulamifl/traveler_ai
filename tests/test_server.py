"""Тесты WebSocket-сервера через TestClient. Без реальной сети."""

from __future__ import annotations

from fastapi.testclient import TestClient

from translator.net.server import create_app
from translator.translate.base import TranslationResult


class _FakeTranslator:
    def translate(self, text, target_lang, source_lang=None):
        return TranslationResult(
            text=f"[{target_lang}] {text}",
            source_lang=source_lang,
            target_lang=target_lang,
        )


def _client() -> TestClient:
    app = create_app(translator_factory=lambda: _FakeTranslator())
    return TestClient(app)


def test_join_and_speak_routes_to_listener():
    client = _client()
    with client.websocket_connect("/ws/demo") as alice_ws:
        alice_ws.send_json(
            {"type": "join", "participant_id": "alice", "name": "Alice",
             "language": "ru", "role": "speaker"}
        )
        assert alice_ws.receive_json()["type"] == "joined"

        with client.websocket_connect("/ws/demo") as bob_ws:
            bob_ws.send_json(
                {"type": "join", "participant_id": "bob", "name": "Bob",
                 "language": "en"}
            )
            assert bob_ws.receive_json()["type"] == "joined"

            alice_ws.send_json(
                {"type": "speak", "participant_id": "alice",
                 "text": "Привет", "source_lang": "ru"}
            )
            msg = bob_ws.receive_json()
            assert msg["type"] == "translation"
            assert msg["to"] == "bob"
            assert msg["target_lang"] == "en"
            assert msg["text"] == "[en] Привет"


def test_question_routes_to_speaker():
    client = _client()
    with client.websocket_connect("/ws/q") as alice_ws:
        alice_ws.send_json(
            {"type": "join", "participant_id": "alice", "name": "Alice",
             "language": "ru", "role": "speaker"}
        )
        alice_ws.receive_json()

        with client.websocket_connect("/ws/q") as bob_ws:
            bob_ws.send_json(
                {"type": "join", "participant_id": "bob", "name": "Bob",
                 "language": "en"}
            )
            bob_ws.receive_json()

            bob_ws.send_json(
                {"type": "question", "participant_id": "bob",
                 "text": "How are you?", "source_lang": "en"}
            )
            msg = alice_ws.receive_json()
            assert msg["type"] == "translation"
            assert msg["to"] == "alice"
            assert msg["target_lang"] == "ru"
            assert msg["text"] == "[ru] How are you?"


def test_unknown_type_returns_error():
    client = _client()
    with client.websocket_connect("/ws/e") as ws:
        ws.send_json({"type": "bogus"})
        msg = ws.receive_json()
        assert msg["type"] == "error"


def test_history_records_author_and_time(tmp_path):
    from translator.history.store import HistoryStore

    db_path = tmp_path / "history.db"

    def history_factory() -> HistoryStore:
        return HistoryStore(db_path)

    app = create_app(
        translator_factory=lambda: _FakeTranslator(),
        history_factory=history_factory,
    )
    client = TestClient(app)

    with client.websocket_connect("/ws/s1") as ws:
        ws.send_json(
            {"type": "join", "participant_id": "alice", "name": "Alice",
             "language": "ru", "role": "speaker"}
        )
        ws.receive_json()
        ws.send_json(
            {"type": "join", "participant_id": "bob", "name": "Bob",
             "language": "en"}
        )
        ws.receive_json()
        ws.send_json(
            {"type": "speak", "participant_id": "alice",
             "text": "Привет", "source_lang": "ru"}
        )
        # bob получит перевод
        ws.receive_json()

    resp = client.get("/sessions/s1/history")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["entries"]) == 1
    entry = data["entries"][0]
    assert entry["author"] == "Alice"
    assert entry["original_text"] == "Привет"
    assert entry["translated_text"] == "[en] Привет"
    assert entry["source_lang"] == "ru"
    assert entry["target_lang"] == "en"
    assert entry["created_at"]


def test_index_page_served():
    client = _client()
    resp = client.get("/")
    assert resp.status_code == 200
    assert "text/html" in resp.headers["content-type"]
    assert "Translator AR" in resp.text


def test_static_index_available():
    client = _client()
    resp = client.get("/static/index.html")
    assert resp.status_code == 200
    assert "WebSocket" in resp.text


def test_join_duplicate_returns_error():
    client = _client()
    with client.websocket_connect("/ws/d") as ws:
        ws.send_json(
            {"type": "join", "participant_id": "a", "name": "A", "language": "ru"}
        )
        ws.receive_json()
        ws.send_json(
            {"type": "join", "participant_id": "a", "name": "A", "language": "ru"}
        )
        msg = ws.receive_json()
        assert msg["type"] == "error"
