from __future__ import annotations

import os
import stat
import threading
import unicodedata
from datetime import datetime, timezone
from pathlib import Path


class FileMoveError(Exception):
    pass


class FileService:
    def __init__(
        self,
        source_dir: Path,
        destination_dir: Path,
        allowed_extensions=None,
        max_file_size_bytes: int = 5 * 1024**3,
        max_filename_length: int = 255,
    ) -> None:
        self.source_dir = source_dir.expanduser().resolve()
        self.destination_dir = destination_dir.expanduser().resolve()
        self.allowed_extensions = allowed_extensions or {"zip"}
        self.max_file_size_bytes = max_file_size_bytes
        self.max_filename_length = max_filename_length
        self._move_lock = threading.Lock()

        if self.source_dir == self.destination_dir:
            raise RuntimeError("SOURCE_DIR and DESTINATION_DIR must be different")
        if self.source_dir in self.destination_dir.parents or self.destination_dir in self.source_dir.parents:
            raise RuntimeError("Source and destination directories must not contain one another")

        self.source_dir.mkdir(parents=True, exist_ok=True, mode=0o750)
        self.destination_dir.mkdir(parents=True, exist_ok=True, mode=0o750)
        if self.source_dir.is_symlink() or self.destination_dir.is_symlink():
            raise RuntimeError("Configured directories must not be symbolic links")

        # The project uses os.replace(), an atomic and efficient rename, so both
        # configured directories must be on the same filesystem.
        if self.source_dir.stat().st_dev != self.destination_dir.stat().st_dev:
            raise RuntimeError("SOURCE_DIR and DESTINATION_DIR must be on the same filesystem")

    def _validate_filename(self, filename: str) -> str:
        normalized = unicodedata.normalize("NFC", filename)
        if not normalized or len(normalized) > self.max_filename_length:
            raise FileMoveError("Invalid filename length")
        if normalized in {".", ".."} or Path(normalized).name != normalized or Path(normalized).is_absolute():
            raise FileMoveError("Invalid filename")
        if any(ord(char) < 32 or ord(char) == 127 for char in normalized):
            raise FileMoveError("Control characters are not allowed in filenames")
        return normalized

    def validate_filename(self, filename: str) -> str:
        return self._validate_filename(filename)

    def _is_allowed(self, path: Path) -> bool:
        return path.suffix.lower().lstrip(".") in self.allowed_extensions

    @staticmethod
    def _safe_page(value: int, default: int = 1) -> int:
        return value if value > 0 else default

    def list_files_page(
        self,
        directory: str = "source",
        search: str = "",
        page: int = 1,
        per_page: int = 20,
    ) -> dict:
        base_dir = self.source_dir if directory == "source" else self.destination_dir
        search_term = search.strip().casefold()
        rows = []

        # os.scandir avoids an extra stat call for many directory entries and is
        # appropriate for directories containing hundreds or thousands of files.
        with os.scandir(base_dir) as entries:
            for entry in entries:
                try:
                    if entry.is_symlink() or not entry.is_file(follow_symlinks=False):
                        continue
                    path = Path(entry.path)
                    if not self._is_allowed(path):
                        continue
                    if search_term and search_term not in entry.name.casefold():
                        continue
                    info = entry.stat(follow_symlinks=False)
                    rows.append(
                        {
                            "name": entry.name,
                            "size_bytes": info.st_size,
                            "size_display": self._format_size(info.st_size),
                            "modified": datetime.fromtimestamp(
                                info.st_mtime, tz=timezone.utc
                            ).astimezone().strftime("%Y-%m-%d %H:%M:%S %Z"),
                        }
                    )
                except (FileNotFoundError, PermissionError):
                    # Files may disappear between scandir and stat when another
                    # user moves them. Skip the stale entry safely.
                    continue

        rows.sort(key=lambda row: row["name"].casefold())
        total = len(rows)
        per_page = max(1, per_page)
        total_pages = max(1, (total + per_page - 1) // per_page)
        page = min(self._safe_page(page), total_pages)
        start = (page - 1) * per_page

        return {
            "items": rows[start : start + per_page],
            "page": page,
            "per_page": per_page,
            "total": total,
            "total_pages": total_pages,
            "has_previous": page > 1,
            "has_next": page < total_pages,
            "previous_page": page - 1,
            "next_page": page + 1,
            "start_item": start + 1 if total else 0,
            "end_item": min(start + per_page, total),
        }

    def move_file(self, filename: str):
        filename = self._validate_filename(filename)
        source = self.source_dir / filename
        destination = self.destination_dir / filename

        with self._move_lock:
            try:
                source_stat = os.stat(source, follow_symlinks=False)
            except FileNotFoundError as exc:
                raise FileMoveError("Source file no longer exists") from exc

            if not stat.S_ISREG(source_stat.st_mode):
                raise FileMoveError("Only regular files can be moved")
            if source_stat.st_size > self.max_file_size_bytes:
                raise FileMoveError("File exceeds the configured size limit")
            if not self._is_allowed(source):
                raise FileMoveError("Only ZIP files can be moved")
            if destination.exists() or destination.is_symlink():
                raise FileMoveError("A file with the same name already exists in the destination")

            try:
                # Create the target name atomically without overwriting an existing
                # file. Hard-link + unlink is efficient because both directories are
                # on the same filesystem and no file data is copied.
                os.link(source, destination, follow_symlinks=False)
                destination_stat = os.stat(destination, follow_symlinks=False)
                if (destination_stat.st_dev, destination_stat.st_ino) != (source_stat.st_dev, source_stat.st_ino):
                    os.unlink(destination)
                    raise FileMoveError("Source file changed during the move")
                try:
                    os.unlink(source)
                except OSError:
                    # Roll back the target link if removal of the source fails.
                    try:
                        os.unlink(destination)
                    except OSError:
                        pass
                    raise
            except FileExistsError as exc:
                raise FileMoveError("A file with the same name already exists in the destination") from exc
            except FileNotFoundError as exc:
                raise FileMoveError("Source file no longer exists") from exc
            except OSError as exc:
                raise FileMoveError("The operating system could not move the file") from exc

        return {"source_name": filename, "destination_name": filename}

    @staticmethod
    def _format_size(size: int) -> str:
        value = float(size)
        for unit in ("B", "KB", "MB", "GB", "TB"):
            if value < 1024 or unit == "TB":
                return f"{value:.1f} {unit}" if unit != "B" else f"{int(value)} B"
            value /= 1024
        return f"{size} B"
