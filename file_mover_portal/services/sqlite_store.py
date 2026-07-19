from __future__ import annotations

import os
import sqlite3
from contextlib import contextmanager
from pathlib import Path


class SQLiteStore:
    """Small SQLite connection factory shared by portal services."""

    def __init__(self, database_path: Path, busy_timeout_ms: int = 10000) -> None:
        self.database_path = database_path.expanduser().resolve()
        self.busy_timeout_ms = max(1000, int(busy_timeout_ms))
        self.database_path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        if self.database_path.parent.is_symlink():
            raise RuntimeError("SQLite database directory must not be a symbolic link")
        os.chmod(self.database_path.parent, 0o700)
        self.initialize()

    def connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(
            str(self.database_path),
            timeout=self.busy_timeout_ms / 1000.0,
            isolation_level=None,
        )
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute(f"PRAGMA busy_timeout = {self.busy_timeout_ms}")
        connection.execute("PRAGMA journal_mode = DELETE")
        connection.execute("PRAGMA synchronous = FULL")
        return connection

    @contextmanager
    def transaction(self, immediate: bool = False):
        connection = self.connect()
        try:
            connection.execute("BEGIN IMMEDIATE" if immediate else "BEGIN")
            yield connection
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    def initialize(self) -> None:
        with self.transaction(immediate=True) as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS audit_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    application TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    username TEXT NOT NULL,
                    action TEXT NOT NULL,
                    details TEXT NOT NULL,
                    remote_addr TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_audit_user_id
                    ON audit_events(username, id DESC);

                CREATE TABLE IF NOT EXISTS batches (
                    batch_id TEXT PRIMARY KEY,
                    username TEXT NOT NULL,
                    recipient TEXT NOT NULL,
                    started_at TEXT NOT NULL,
                    completed_at TEXT NOT NULL DEFAULT '',
                    status TEXT NOT NULL,
                    email_status TEXT NOT NULL,
                    created_epoch REAL NOT NULL,
                    updated_epoch REAL NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_batches_user_status
                    ON batches(username, status);
                CREATE INDEX IF NOT EXISTS idx_batches_updated
                    ON batches(updated_epoch);

                CREATE TABLE IF NOT EXISTS batch_files (
                    batch_id TEXT NOT NULL,
                    position INTEGER NOT NULL,
                    filename TEXT NOT NULL,
                    status TEXT,
                    message TEXT,
                    PRIMARY KEY (batch_id, filename),
                    UNIQUE (batch_id, position),
                    FOREIGN KEY (batch_id) REFERENCES batches(batch_id) ON DELETE CASCADE
                );
                CREATE INDEX IF NOT EXISTS idx_batch_files_batch_position
                    ON batch_files(batch_id, position);

                CREATE TABLE IF NOT EXISTS login_attempts (
                    key_hash TEXT NOT NULL,
                    attempted_epoch REAL NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_login_attempts_key_time
                    ON login_attempts(key_hash, attempted_epoch);
                """
            )
        try:
            os.chmod(self.database_path, 0o600)
        except OSError:
            pass
