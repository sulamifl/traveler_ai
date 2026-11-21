"""Тесты WebSocket-сервера через TestClient. Без реальной сети."""

from __future__ import annotations

import pytest
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


def test_history_filtered_by_session(tmp_path):
    from translator.history.store import HistoryStore

    db_path = tmp_path / "history.db"

    def history_factory() -> HistoryStore:
        return HistoryStore(db_path)

    app = create_app(
        translator_factory=lambda: _FakeTranslator(),
        history_factory=history_factory,
    )
    client = TestClient(app)

    def _speak(session_id: str, text: str) -> None:
        with client.websocket_connect(f"/ws/{session_id}") as ws:
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
                 "text": text, "source_lang": "ru"}
            )
            ws.receive_json()

    _speak("s1", "Привет")
    _speak("s2", "Пока")

    r1 = client.get("/sessions/s1/history").json()
    r2 = client.get("/sessions/s2/history").json()

    assert len(r1["entries"]) == 1
    assert r1["entries"][0]["original_text"] == "Привет"
    assert r1["entries"][0]["session_id"] == "s1"

    assert len(r2["entries"]) == 1
    assert r2["entries"][0]["original_text"] == "Пока"
    assert r2["entries"][0]["session_id"] == "s2"


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


def test_ar_page_served():
    client = _client()
    resp = client.get("/ar")
    assert resp.status_code == 200
    assert "text/html" in resp.headers["content-type"]
    assert "AR-режим" in resp.text


def test_ar_frame_returns_blocks():
    import io

    import numpy as np
    from PIL import Image

    from translator.ar.describe import DescribedBlock, DescribeResult

    class _FakeDescriber:
        def describe(self, frame, target_lang, source_lang=None):
            return DescribeResult(
                blocks=[
                    DescribedBlock(
                        original_text="Hello",
                        translated_text="Привет",
                        bbox=(1, 2, 3, 4),
                        confidence=90.0,
                    )
                ],
                source_lang=source_lang,
                target_lang=target_lang,
            )

    app = create_app(
        translator_factory=lambda: _FakeTranslator(),
        describer_factory=lambda: _FakeDescriber(),
    )
    client = TestClient(app)

    img = Image.fromarray(np.zeros((10, 10, 3), dtype=np.uint8))
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    buf.seek(0)

    resp = client.post(
        "/ar/frame",
        files={"file": ("frame.jpg", buf, "image/jpeg")},
        data={"target_lang": "ru", "source_lang": "eng"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["target_lang"] == "ru"
    assert len(data["blocks"]) == 1
    assert data["blocks"][0]["translated_text"] == "Привет"
    assert data["blocks"][0]["bbox"] == [1, 2, 3, 4]


def test_stt_endpoint_returns_text():
    from translator.stt.base import TranscriptionResult, TranscriptionSegment

    class _FakeSTT:
        def transcribe(self, audio_path, language=None):
            return TranscriptionResult(
                text="Привет мир",
                language=language or "ru",
                segments=[TranscriptionSegment(start=0.0, end=1.0, text="Привет мир")],
            )

    app = create_app(
        translator_factory=lambda: _FakeTranslator(),
        stt_factory=lambda: _FakeSTT(),
    )
    client = TestClient(app)

    resp = client.post(
        "/stt",
        files={"file": ("speech.webm", b"\x00\x01\x02", "audio/webm")},
        data={"language": "ru"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["text"] == "Привет мир"
    assert data["language"] == "ru"
    assert len(data["segments"]) == 1


def test_groq_transcriber_returns_result(tmp_path):
    from translator.stt.groq_stt import GroqTranscriber

    class _FakeResponse:
        text = "Привет мир"
        language = "ru"
        segments = [
            {"start": 0.0, "end": 1.0, "text": "Привет мир"},
        ]

    class _FakeAudio:
        def __init__(self):
            self.calls = []

        def transcriptions(self):
            return self

        def create(self, **kwargs):
            self.calls.append(kwargs)
            return _FakeResponse()

    class _FakeClient:
        def __init__(self):
            self.audio = _FakeAudio()

    audio_file = tmp_path / "speech.webm"
    audio_file.write_bytes(b"\x00\x01\x02")

    client = _FakeClient()
    stt = GroqTranscriber(api_key="test", client=client)
    result = stt.transcribe(audio_file, language="ru")

    assert result.text == "Привет мир"
    assert result.language == "ru"
    assert len(result.segments) == 1
    assert result.segments[0].text == "Привет мир"


def test_groq_transcriber_missing_file_raises(tmp_path):
    from translator.stt.groq_stt import GroqSTTError, GroqTranscriber

    stt = GroqTranscriber(api_key="test", client=object())
    with pytest.raises(GroqSTTError):
        stt.transcribe(tmp_path / "missing.webm")


def test_groq_transcriber_requires_api_key(tmp_path):
    from translator.stt.groq_stt import GroqSTTError, GroqTranscriber

    # Конструктор не падает без ключа — приложение должно стартовать.
    stt = GroqTranscriber()
    audio_file = tmp_path / "speech.webm"
    audio_file.write_bytes(b"\x00\x01\x02")
    with pytest.raises(GroqSTTError):
        stt.transcribe(audio_file)


def test_stt_endpoint_without_factory_returns_503():
    client = _client()
    resp = client.post(
        "/stt",
        files={"file": ("speech.webm", b"\x00", "audio/webm")},
    )
    assert resp.status_code == 503


def test_ar_frame_without_describer_returns_503():
    client = _client()
    import io

    import numpy as np
    from PIL import Image

    img = Image.fromarray(np.zeros((4, 4, 3), dtype=np.uint8))
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    buf.seek(0)

    resp = client.post(
        "/ar/frame",
        files={"file": ("frame.jpg", buf, "image/jpeg")},
        data={"target_lang": "ru"},
    )
    assert resp.status_code == 503


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
