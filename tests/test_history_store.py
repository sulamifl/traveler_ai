"""Тесты для HistoryStore."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import pytest

from translator.history.store import HistoryStore


def test_add_and_list(tmp_path: Path):
    db = tmp_path / "h.db"
    with HistoryStore(db) as store:
        id1 = store.add(
            author="alice",
            original_text="Привет",
            translated_text="Hello",
            source_lang="ru",
            target_lang="en",
        )
        id2 = store.add(
            author="bob",
            original_text="Как дела?",
            translated_text="How are you?",
            source_lang="ru",
            target_lang="en",
        )
        assert id1 == 1
        assert id2 == 2

        entries = store.list_recent(limit=10)
        assert len(entries) == 2
        # сначала новые
        assert entries[0].author == "bob"
        assert entries[1].author == "alice"
        assert entries[0].translated_text == "How are you?"


def test_limit(tmp_path: Path):
    with HistoryStore(tmp_path / "h.db") as store:
        for i in range(5):
            store.add(
                author=f"u{i}",
                original_text=f"o{i}",
                translated_text=f"t{i}",
                target_lang="en",
            )
        assert len(store.list_recent(limit=3)) == 3
        assert len(store.list_recent(limit=0)) == 0


def test_validation(tmp_path: Path):
    with HistoryStore(tmp_path / "h.db") as store:
        with pytest.raises(ValueError):
            store.add(author="", original_text="x", translated_text="y", target_lang="en")
        with pytest.raises(ValueError):
            store.add(author="a", original_text="x", translated_text="y", target_lang="")


def test_created_at_override(tmp_path: Path):
    ts = datetime(2024, 1, 1, 12, 0, tzinfo=timezone.utc)
    with HistoryStore(tmp_path / "h.db") as store:
        store.add(
            author="a",
            original_text="x",
            translated_text="y",
            target_lang="en",
            created_at=ts,
        )
        entry = store.list_recent(1)[0]
        assert entry.created_at.startswith("2024-01-01T12:00")
