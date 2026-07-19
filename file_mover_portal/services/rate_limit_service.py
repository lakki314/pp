from __future__ import annotations

import hashlib
import time

from services.sqlite_store import SQLiteStore


class LoginRateLimiter:
    """SQLite-backed limiter shared by all Gunicorn workers on one host."""

    def __init__(self, max_attempts: int, window_seconds: int, store: SQLiteStore) -> None:
        self.max_attempts = max(1, int(max_attempts))
        self.window_seconds = max(30, int(window_seconds))
        self.store = store

    @staticmethod
    def _hash(key: str) -> str:
        return hashlib.sha256(key.encode("utf-8", errors="ignore")).hexdigest()

    def _prune(self, connection, key_hash: str, now: float) -> None:
        connection.execute(
            "DELETE FROM login_attempts WHERE key_hash = ? AND attempted_epoch < ?",
            (key_hash, now - self.window_seconds),
        )

    def is_blocked(self, key: str) -> bool:
        key_hash = self._hash(key)
        now = time.time()
        with self.store.transaction(immediate=True) as connection:
            self._prune(connection, key_hash, now)
            row = connection.execute(
                "SELECT COUNT(*) AS count FROM login_attempts WHERE key_hash = ?",
                (key_hash,),
            ).fetchone()
        return int(row["count"]) >= self.max_attempts

    def record_failure(self, key: str) -> None:
        key_hash = self._hash(key)
        now = time.time()
        with self.store.transaction(immediate=True) as connection:
            self._prune(connection, key_hash, now)
            connection.execute(
                "INSERT INTO login_attempts (key_hash, attempted_epoch) VALUES (?, ?)",
                (key_hash, now),
            )

    def clear(self, key: str) -> None:
        with self.store.transaction(immediate=True) as connection:
            connection.execute("DELETE FROM login_attempts WHERE key_hash = ?", (self._hash(key),))
