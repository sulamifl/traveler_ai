"""Тесты для модели групповой сессии."""

from __future__ import annotations

import pytest

from translator.net.session import Session, SessionError


def _make_session() -> Session:
    s = Session(session_id="demo")
    s.add_participant("alice", "Alice", language="ru", role="speaker")
    s.add_participant("bob", "Bob", language="en")
    s.add_participant("carol", "Carol", language="de")
    return s


def test_add_and_remove():
    s = _make_session()
    assert set(s.participants) == {"alice", "bob", "carol"}
    assert s.speaker_id == "alice"

    s.remove_participant("bob")
    assert "bob" not in s.participants

    s.remove_participant("alice")
    assert s.speaker_id is None


def test_add_duplicate_raises():
    s = _make_session()
    with pytest.raises(SessionError):
        s.add_participant("bob", "Bob2", language="fr")


def test_add_empty_raises():
    s = Session(session_id="x")
    with pytest.raises(SessionError):
        s.add_participant("", "X", language="en")
    with pytest.raises(SessionError):
        s.add_participant("a", "A", language="")


def test_set_speaker():
    s = _make_session()
    s.set_speaker("bob")
    assert s.speaker_id == "bob"
    assert s.participants["bob"].role == "speaker"
    assert s.participants["alice"].role == "listener"


def test_route_excludes_author_and_same_lang():
    s = _make_session()
    routes = s.route("Привет", source_lang="ru", author_id="alice")
    # alice — автор, пропускаем; bob(en) и carol(de) — переводим
    assert sorted(routes) == [("bob", "en"), ("carol", "de")]


def test_route_skips_same_language():
    s = Session(session_id="x")
    s.add_participant("a", "A", language="ru", role="speaker")
    s.add_participant("b", "B", language="ru")
    s.add_participant("c", "C", language="en")
    routes = s.route("Привет", source_lang="ru", author_id="a")
    assert routes == [("c", "en")]


def test_route_empty_text_raises():
    s = _make_session()
    with pytest.raises(SessionError):
        s.route("   ", source_lang="ru")


def test_route_question_to_speaker():
    s = _make_session()
    routes = s.route_question("How are you?", source_lang="en", author_id="bob")
    assert routes == [("alice", "ru")]


def test_route_question_no_speaker_raises():
    s = Session(session_id="x")
    s.add_participant("bob", "Bob", language="en")
    with pytest.raises(SessionError):
        s.route_question("Hi", source_lang="en", author_id="bob")


def test_route_question_from_speaker_returns_empty():
    s = _make_session()
    routes = s.route_question("Привет", source_lang="ru", author_id="alice")
    assert routes == []
