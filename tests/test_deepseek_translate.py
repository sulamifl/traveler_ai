"""Тесты для DeepSeekTranslator. Не требуют сети и реального ключа."""

from __future__ import annotations

import httpx
import pytest

from translator.translate.base import Translator
from translator.translate.deepseek import DeepSeekTranslator, TranslationError


class _FakeResponse:
    def __init__(self, status_code: int, payload: dict | None = None, text: str = ""):
        self.status_code = status_code
        self._payload = payload
        self.text = text

    def json(self):
        if self._payload is None:
            raise ValueError("no json")
        return self._payload


class _FakeClient:
    def __init__(self, response: _FakeResponse | Exception):
        self._response = response
        self.calls: list[dict] = []

    def post(self, url, json=None, headers=None):
        self.calls.append({"url": url, "json": json, "headers": headers})
        if isinstance(self._response, Exception):
            raise self._response
        return self._response


def _ok_response(text: str = "Hello") -> _FakeResponse:
    return _FakeResponse(
        200,
        {
            "choices": [
                {"message": {"role": "assistant", "content": text}},
            ]
        },
    )


def test_translate_returns_result():
    client = _FakeClient(_ok_response("Hello"))
    tr = DeepSeekTranslator(api_key="sk-test", client=client)

    res = tr.translate("Привет", target_lang="en", source_lang="ru")

    assert res.text == "Hello"
    assert res.target_lang == "en"
    assert res.source_lang == "ru"
    assert client.calls[0]["url"].endswith("/chat/completions")
    assert client.calls[0]["headers"]["Authorization"] == "Bearer sk-test"
    assert client.calls[0]["json"]["model"] == "deepseek-chat"


def test_missing_api_key_raises(monkeypatch):
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    with pytest.raises(TranslationError):
        DeepSeekTranslator()


def test_empty_text_raises():
    tr = DeepSeekTranslator(api_key="sk-test", client=_FakeClient(_ok_response()))
    with pytest.raises(ValueError):
        tr.translate("   ", target_lang="en")


def test_http_error_status_raises():
    client = _FakeClient(_FakeResponse(401, text="unauthorized"))
    tr = DeepSeekTranslator(api_key="sk-test", client=client)
    with pytest.raises(TranslationError):
        tr.translate("Привет", target_lang="en")


def test_network_error_raises():
    client = _FakeClient(httpx.ConnectError("boom"))
    tr = DeepSeekTranslator(api_key="sk-test", client=client)
    with pytest.raises(TranslationError):
        tr.translate("Привет", target_lang="en")


def test_bad_payload_raises():
    client = _FakeClient(_FakeResponse(200, {"unexpected": True}))
    tr = DeepSeekTranslator(api_key="sk-test", client=client)
    with pytest.raises(TranslationError):
        tr.translate("Привет", target_lang="en")


def test_implements_protocol():
    tr = DeepSeekTranslator(api_key="sk-test", client=_FakeClient(_ok_response()))
    assert isinstance(tr, Translator)
