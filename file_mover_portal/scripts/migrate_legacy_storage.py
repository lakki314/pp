#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from services.sqlite_store import SQLiteStore


def import_audit(store: SQLiteStore, audit_file: Path) -> int:
    if not audit_file.is_file():
        return 0
    rows = []
    with audit_file.open("r", encoding="utf-8", errors="replace") as handle:
        for line in handle:
            try:
                item = json.loads(line)
            except json.JSONDecodeError:
                continue
            rows.append((
                str(item.get("application", "File Mover Portal")),
                str(item.get("timestamp", "")), str(item.get("username", "")),
                str(item.get("action", "")), str(item.get("details", "")),
                str(item.get("remote_addr", "")),
            ))
    with store.transaction(immediate=True) as connection:
        connection.executemany(
            """INSERT INTO audit_events
               (application,timestamp,username,action,details,remote_addr)
               VALUES (?,?,?,?,?,?)""", rows)
    return len(rows)


def import_batches(store: SQLiteStore, batch_dir: Path) -> int:
    imported = 0
    if not batch_dir.is_dir():
        return imported
    for path in sorted(batch_dir.glob("MOVE-*.json")):
        try:
            state = json.loads(path.read_text(encoding="utf-8"))
            batch_id = str(state["batch_id"])
            started_at = str(state.get("started_at", ""))
            epoch = path.stat().st_mtime or time.time()
            with store.transaction(immediate=True) as connection:
                exists = connection.execute(
                    "SELECT 1 FROM batches WHERE batch_id = ?", (batch_id,)
                ).fetchone()
                if exists:
                    continue
                connection.execute(
                    """INSERT INTO batches
                       (batch_id,username,recipient,started_at,completed_at,status,email_status,created_epoch,updated_epoch)
                       VALUES (?,?,?,?,?,?,?,?,?)""",
                    (batch_id, str(state.get("username", "")), str(state.get("recipient", "")),
                     started_at, str(state.get("completed_at", "")), str(state.get("status", "IN_PROGRESS")),
                     str(state.get("email_status", "PENDING")), epoch, epoch),
                )
                results = {str(item.get("filename", "")): item for item in state.get("results", [])}
                connection.executemany(
                    """INSERT INTO batch_files (batch_id,position,filename,status,message)
                       VALUES (?,?,?,?,?)""",
                    [(batch_id, position, str(filename),
                      results.get(str(filename), {}).get("status"),
                      results.get(str(filename), {}).get("message"))
                     for position, filename in enumerate(state.get("filenames", []))],
                )
            imported += 1
        except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError) as exc:
            print(f"Skipping {path}: {exc}", file=sys.stderr)
    return imported


def main() -> int:
    parser = argparse.ArgumentParser(description="Import legacy JSON storage into SQLite")
    parser.add_argument("--database", required=True, type=Path)
    parser.add_argument("--audit-file", type=Path)
    parser.add_argument("--batch-dir", type=Path)
    args = parser.parse_args()
    store = SQLiteStore(args.database)
    audit_count = import_audit(store, args.audit_file) if args.audit_file else 0
    batch_count = import_batches(store, args.batch_dir) if args.batch_dir else 0
    print(f"Imported audit events: {audit_count}")
    print(f"Imported batches: {batch_count}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
