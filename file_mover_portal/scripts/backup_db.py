#!/usr/bin/env python3
"""Create a transactionally consistent online SQLite backup."""
from __future__ import annotations
import argparse
import os
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
parser.add_argument("--output-dir", default=str(resolve(cfg.get("BACKUP_DIR", "backups"), "backups")))
args = parser.parse_args()
source = resolve(cfg.get("DATABASE_PATH", "data/file_mover.db"), "data/file_mover.db")
if not source.is_file() or source.is_symlink():
    raise SystemExit(f"Database does not exist or is unsafe: {source}")
outdir = Path(args.output_dir).expanduser().resolve()
outdir.mkdir(parents=True, exist_ok=True, mode=0o700)
os.chmod(outdir, 0o700)
stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
target = outdir / f"file_mover_{stamp}.db"
with sqlite3.connect(str(source)) as src, sqlite3.connect(str(target)) as dst:
    src.backup(dst)
    row = dst.execute("PRAGMA integrity_check").fetchone()
    if not row or row[0] != "ok":
        raise RuntimeError("Backup integrity check failed")
os.chmod(target, 0o600)
print(target)
