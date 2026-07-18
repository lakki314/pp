from __future__ import annotations

import os
import re
import time
from datetime import datetime, timezone
from pathlib import Path

import sqlite3

from services.sqlite_store import SQLiteStore


_BATCH_RE = re.compile(r"^MOVE-[0-9]{8}-[A-F0-9]{10}$")
_FINAL_STATUSES = {"SUCCESS", "FAILED", "PARTIAL_SUCCESS"}


class BatchStateError(Exception):
    pass


class BatchService:
    """SQLite-backed batch state with transactional cross-process coordination."""

    def __init__(self, store: SQLiteStore, report_dir: Path, retention_hours: int = 168) -> None:
        self.store = store
        self.report_dir = report_dir.expanduser().resolve()
        self.retention_seconds = max(1, int(retention_hours)) * 3600
        self.report_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
        if self.report_dir.is_symlink():
            raise RuntimeError("Report directory must not be a symbolic link")
        os.chmod(self.report_dir, 0o700)

    def _validate_id(self, batch_id: str) -> str:
        if not _BATCH_RE.fullmatch(batch_id):
            raise BatchStateError("Invalid batch identifier")
        return batch_id

    def report_path(self, batch_id: str) -> Path:
        return self.report_dir / f"file_move_report_{self._validate_id(batch_id)}.xlsx"

    @staticmethod
    def _state_from_connection(connection, batch_id: str) -> dict | None:
        batch = connection.execute(
            """SELECT batch_id, username, recipient, started_at, completed_at, status, email_status
               FROM batches WHERE batch_id = ?""",
            (batch_id,),
        ).fetchone()
        if batch is None:
            return None
        files = connection.execute(
            """SELECT filename, status, message FROM batch_files
               WHERE batch_id = ? ORDER BY position""",
            (batch_id,),
        ).fetchall()
        return {
            "batch_id": batch["batch_id"],
            "username": batch["username"],
            "recipient": batch["recipient"],
            "started_at": batch["started_at"],
            "completed_at": batch["completed_at"],
            "filenames": [row["filename"] for row in files],
            "results": [
                {"filename": row["filename"], "status": row["status"], "message": row["message"] or ""}
                for row in files if row["status"] is not None
            ],
            "status": batch["status"],
            "email_status": batch["email_status"],
        }

    @staticmethod
    def _assert_owner(state: dict | None, username: str) -> dict:
        if state is None:
            raise BatchStateError("Batch state is unavailable")
        if state.get("username") != username:
            raise BatchStateError("Batch does not belong to this user")
        return state

    def active_count(self, username: str) -> int:
        with self.store.connect() as connection:
            row = connection.execute(
                """SELECT COUNT(*) AS count FROM batches
                   WHERE username = ? AND status IN ('IN_PROGRESS', 'FINALIZING')""",
                (username,),
            ).fetchone()
        return int(row["count"])

    def create(self, *, batch_id: str, username: str, recipient: str, filenames: list[str]) -> dict:
        validated_id = self._validate_id(batch_id)
        now_iso = datetime.now(timezone.utc).isoformat()
        now_epoch = time.time()
        try:
            with self.store.transaction(immediate=True) as connection:
                connection.execute(
                    """INSERT INTO batches
                       (batch_id, username, recipient, started_at, completed_at, status,
                        email_status, created_epoch, updated_epoch)
                       VALUES (?, ?, ?, ?, '', 'IN_PROGRESS', 'PENDING', ?, ?)""",
                    (validated_id, username, recipient, now_iso, now_epoch, now_epoch),
                )
                connection.executemany(
                    """INSERT INTO batch_files (batch_id, position, filename, status, message)
                       VALUES (?, ?, ?, NULL, NULL)""",
                    [(validated_id, position, filename) for position, filename in enumerate(filenames)],
                )
                state = self._state_from_connection(connection, validated_id)
        except sqlite3.IntegrityError as exc:
            raise BatchStateError("Batch identifier already exists or contains duplicate files") from exc
        return self._assert_owner(state, username)

    def load(self, batch_id: str, username: str) -> dict:
        validated_id = self._validate_id(batch_id)
        with self.store.connect() as connection:
            state = self._state_from_connection(connection, validated_id)
        return self._assert_owner(state, username)

    def append_result(self, batch_id: str, username: str, result: dict) -> dict:
        validated_id = self._validate_id(batch_id)
        filename = str(result.get("filename", ""))
        with self.store.transaction(immediate=True) as connection:
            state = self._assert_owner(self._state_from_connection(connection, validated_id), username)
            if state.get("status") != "IN_PROGRESS":
                raise BatchStateError("Batch is no longer active")
            row = connection.execute(
                "SELECT status FROM batch_files WHERE batch_id = ? AND filename = ?",
                (validated_id, filename),
            ).fetchone()
            if row is None:
                raise BatchStateError("File is not part of this batch")
            if row["status"] is not None:
                raise BatchStateError("File was already processed")
            connection.execute(
                """UPDATE batch_files SET status = ?, message = ?
                   WHERE batch_id = ? AND filename = ?""",
                (str(result.get("status", "FAILED")), str(result.get("message", "")), validated_id, filename),
            )
            connection.execute(
                "UPDATE batches SET updated_epoch = ? WHERE batch_id = ?",
                (time.time(), validated_id),
            )
            state = self._state_from_connection(connection, validated_id)
        return self._assert_owner(state, username)

    def claim_completion(self, batch_id: str, username: str) -> dict:
        validated_id = self._validate_id(batch_id)
        with self.store.transaction(immediate=True) as connection:
            state = self._assert_owner(self._state_from_connection(connection, validated_id), username)
            if state.get("status") in _FINAL_STATUSES:
                return state
            if state.get("status") == "FINALIZING":
                raise BatchStateError("Batch completion is already in progress")
            pending = connection.execute(
                "SELECT COUNT(*) AS count FROM batch_files WHERE batch_id = ? AND status IS NULL",
                (validated_id,),
            ).fetchone()["count"]
            if int(pending) != 0:
                raise BatchStateError("Not all files have been processed")
            connection.execute(
                "UPDATE batches SET status = 'FINALIZING', updated_epoch = ? WHERE batch_id = ?",
                (time.time(), validated_id),
            )
            state = self._state_from_connection(connection, validated_id)
        return self._assert_owner(state, username)

    def complete(self, batch_id: str, username: str, email_status: str) -> dict:
        validated_id = self._validate_id(batch_id)
        with self.store.transaction(immediate=True) as connection:
            state = self._assert_owner(self._state_from_connection(connection, validated_id), username)
            if state.get("status") in _FINAL_STATUSES:
                return state
            if state.get("status") != "FINALIZING":
                raise BatchStateError("Batch is not ready to complete")
            moved = sum(1 for item in state["results"] if item.get("status") == "MOVED")
            failed = len(state["results"]) - moved
            final_status = "SUCCESS" if failed == 0 else ("FAILED" if moved == 0 else "PARTIAL_SUCCESS")
            completed_at = datetime.now(timezone.utc).isoformat()
            connection.execute(
                """UPDATE batches SET completed_at = ?, status = ?, email_status = ?, updated_epoch = ?
                   WHERE batch_id = ?""",
                (completed_at, final_status, email_status, time.time(), validated_id),
            )
            state = self._state_from_connection(connection, validated_id)
        return self._assert_owner(state, username)

    def save_report(self, batch_id: str, content: bytes) -> Path:
        path = self.report_path(batch_id)
        temp = path.with_suffix(f".tmp.{os.getpid()}")
        fd = os.open(temp, os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0), 0o600)
        try:
            with os.fdopen(fd, "wb") as handle:
                handle.write(content)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temp, path)
            os.chmod(path, 0o600)
        finally:
            try:
                temp.unlink()
            except FileNotFoundError:
                pass
        return path

    def cleanup_expired(self) -> int:
        cutoff = time.time() - self.retention_seconds
        with self.store.transaction(immediate=True) as connection:
            expired_ids = [
                row["batch_id"] for row in connection.execute(
                    """SELECT batch_id FROM batches
                       WHERE updated_epoch < ? AND status NOT IN ('IN_PROGRESS', 'FINALIZING')""",
                    (cutoff,),
                ).fetchall()
            ]
            if expired_ids:
                connection.executemany("DELETE FROM batches WHERE batch_id = ?", [(value,) for value in expired_ids])
        removed = len(expired_ids)
        for batch_id in expired_ids:
            try:
                self.report_path(batch_id).unlink()
                removed += 1
            except FileNotFoundError:
                pass
            except OSError:
                continue
        return removed
