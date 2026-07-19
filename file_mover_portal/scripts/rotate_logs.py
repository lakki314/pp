#!/usr/bin/env python3
"""Copy-truncate and prune portal logs using project-relative configuration."""
from __future__ import annotations
import gzip
import os
import shutil
import time
from datetime import datetime, timezone
from pathlib import Path
from dotenv import dotenv_values

ROOT = Path(__file__).resolve().parent.parent
cfg = dotenv_values(ROOT / ".env")

def resolve(value: str, default: str) -> Path:
    path = Path(str(value or default)).expanduser()
    return path if path.is_absolute() else (ROOT / path).resolve()

log_dir = resolve(cfg.get("LOG_DIR", "logs"), "logs")
max_bytes = max(1024, int(cfg.get("LOG_MAX_BYTES", "10485760")))
backup_count = max(1, min(int(cfg.get("LOG_BACKUP_COUNT", "10")), 100))
retention_days = max(1, min(int(cfg.get("LOG_RETENTION_DAYS", "30")), 3650))
log_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
os.chmod(log_dir, 0o700)

now = time.time()
stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
for log in sorted(log_dir.glob("*.log")):
    try:
        if log.is_symlink() or not log.is_file() or log.stat().st_size < max_bytes:
            continue
        archive = log.with_name(f"{log.name}.{stamp}.gz")
        with log.open("rb") as source, gzip.open(str(archive), "wb") as target:
            shutil.copyfileobj(source, target)
        os.chmod(archive, 0o600)
        with log.open("r+b") as handle:
            handle.truncate(0)
    except (FileNotFoundError, OSError):
        continue

cutoff = now - retention_days * 86400
for archive in log_dir.glob("*.log.*.gz"):
    try:
        if archive.stat().st_mtime < cutoff:
            archive.unlink()
    except (FileNotFoundError, OSError):
        pass

for base in ("gunicorn-access.log", "gunicorn-error.log", "portal.log"):
    archives = sorted(log_dir.glob(base + ".*.gz"), key=lambda p: p.stat().st_mtime, reverse=True)
    for archive in archives[backup_count:]:
        try:
            archive.unlink()
        except (FileNotFoundError, OSError):
            pass
