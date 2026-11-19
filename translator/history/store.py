"""Хранение истории реплик в SQLite.

Каждая запись содержит автора, оригинал, перевод, языки и время.
"""

from __future__ import annotations

import logging
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

_SCHEMA = """
CREATE TABLE IF NOT EXISTS history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    author TEXT NOT NULL,
    original_text TEXT NOT NULL,
    translated_text TEXT NOT NULL,
    source_lang TEXT,
    target_lang TEXT NOT NULL,
    created_at TEXT NOT NULL
);
"""


@dataclass(frozen=True)
class HistoryEntry:
    """Одна запись истории."""

    id: int
    author: str
    original_text: str
    translated_text: str
    source_lang: Optional[str]
    target_lang: str
    created_at: str


class HistoryStore:
    """Хранилище истории реплик.

    Пример:
        store = HistoryStore("history.db")
        store.add(author="alice", original_text="Привет",
                  translated_text="Hello", source_lang="ru", target_lang="en")
        for e in store.list_recent(limit=10):
            print(e.author, e.translated_text)
        store.close()
    """

    def __init__(self, db_path: str | Path = "history.db") -> None:
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(self.db_path))
        self._conn.row_factory = sqlite3.Row
        self._conn.execute(_SCHEMA)
        self._conn.commit()
        logger.info("История открыта: %s", self.db_path)

    def add(
        self,
        author: str,
        original_text: str,
        translated_text: str,
        target_lang: str,
        source_lang: Optional[str] = None,
        created_at: Optional[datetime] = None,
    ) -> int:
        """Добавить запись. Возвращает id."""
        if not author:
            raise ValueError("author не может быть пустым")
        if not target_lang:
            raise ValueError("target_lang не может быть пустым")

        ts = (created_at or datetime.now(timezone.utc)).isoformat()
        cur = self._conn.execute(
            "INSERT INTO history "
            "(author, original_text, translated_text, source_lang, target_lang, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (author, original_text, translated_text, source_lang, target_lang, ts),
        )
        self._conn.commit()
        return int(cur.lastrowid)

    def list_recent(self, limit: int = 50) -> list[HistoryEntry]:
        """Вернуть последние записи (сначала новые)."""
        if limit <= 0:
            return []
        rows = self._conn.execute(
            "SELECT id, author, original_text, translated_text, "
            "source_lang, target_lang, created_at "
            "FROM history ORDER BY id DESC LIMIT ?",
            (limit,),
        ).fetchall()
        return [
            HistoryEntry(
                id=row["id"],
                author=row["author"],
                original_text=row["original_text"],
                translated_text=row["translated_text"],
                source_lang=row["source_lang"],
                target_lang=row["target_lang"],
                created_at=row["created_at"],
            )
            for row in rows
        ]

    def close(self) -> None:
        self._conn.close()

    def __enter__(self) -> "HistoryStore":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:  # noqa: ANN001
        self.close()
