from __future__ import annotations

from datetime import datetime, timezone

from services.sqlite_store import SQLiteStore


class AuditService:
    def __init__(self, store: SQLiteStore, app_name: str = "File Mover Portal") -> None:
        self.store = store
        self.app_name = self._clean(app_name, 256)

    @staticmethod
    def _clean(value, maximum: int = 2048) -> str:
        text = str(value).replace("\r", " ").replace("\n", " ").replace("\x00", "")
        return text[:maximum]

    def record(self, action: str, username: str, details: str, remote_addr=None) -> None:
        entry = (
            self.app_name,
            datetime.now(timezone.utc).isoformat(),
            self._clean(username, 256),
            self._clean(action, 64),
            self._clean(details),
            self._clean(remote_addr or "", 64),
        )
        with self.store.transaction(immediate=True) as connection:
            connection.execute(
                """INSERT INTO audit_events
                   (application, timestamp, username, action, details, remote_addr)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                entry,
            )

    def read_recent(self, limit: int = 200, username: str | None = None):
        safe_limit = max(1, int(limit))
        with self.store.connect() as connection:
            if username is None:
                rows = connection.execute(
                    """SELECT timestamp, username, action, details, remote_addr
                       FROM audit_events ORDER BY id DESC LIMIT ?""",
                    (safe_limit,),
                ).fetchall()
            else:
                rows = connection.execute(
                    """SELECT timestamp, username, action, details, remote_addr
                       FROM audit_events WHERE username = ? ORDER BY id DESC LIMIT ?""",
                    (username, safe_limit),
                ).fetchall()
        return [
            {key: self._clean(row[key]) for key in ("timestamp", "username", "action", "details", "remote_addr")}
            for row in rows
        ]
