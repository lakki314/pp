#!/usr/bin/env python3
"""Restore a validated SQLite backup while the portal is stopped."""
from __future__ import annotations
import argparse
import os
import shutil
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from dotenv import dotenv_values

ROOT = Path(__file__).resolve().parent.parent
cfg = dotenv_values(ROOT / ".env")

def resolve(value: str, default: str) -> Path:
    path = Path(str(value or default)).expanduser()
    return path if path.is_absolute() else (ROOT / path).resolve()

parser = argparse.ArgumentParser()
parser.add_argument("backup", type=Path)
parser.add_argument("--force", action="store_true", help="Required confirmation flag")
args = parser.parse_args()
if not args.force:
    raise SystemExit("Refusing restore without --force")
pid_file = ROOT / "run" / "file-mover.pid"
if pid_file.exists():
    try:
        pid = int(pid_file.read_text().strip())
        os.kill(pid, 0)
    except ProcessLookupError:
        pass
    except (ValueError, PermissionError, OSError):
        raise SystemExit("Unable to verify portal status; remove stale PID only after validation")
    else:
        raise SystemExit("Portal is running. Stop it before restoring the database")
backup = args.backup.expanduser().resolve()
if not backup.is_file() or backup.is_symlink():
    raise SystemExit(f"Backup does not exist or is unsafe: {backup}")
with sqlite3.connect(f"file:{backup}?mode=ro", uri=True) as check:
    row = check.execute("PRAGMA integrity_check").fetchone()
    if not row or row[0] != "ok":
        raise SystemExit("Backup integrity check failed")
target = resolve(cfg.get("DATABASE_PATH", "data/file_mover.db"), "data/file_mover.db")
target.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
if target.exists():
    safety = target.with_name(target.name + ".pre_restore_" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ"))
    shutil.copy2(target, safety)
    os.chmod(safety, 0o600)
temp = target.with_suffix(target.suffix + ".restore.tmp")
shutil.copyfile(backup, temp)
os.chmod(temp, 0o600)
os.replace(temp, target)
print(target)
