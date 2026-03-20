from __future__ import annotations

from collections import deque
from datetime import datetime, timezone
from pathlib import Path

from app.core.config import settings
from app.core.logging import LOG_BACKUP_COUNT, LOG_FILENAME
from app.schemas.logs import LogFileInfo, LogViewerResponse

DEFAULT_LINE_LIMIT = 300
MAX_LINE_LIMIT = 1000


class LogService:
    def get_logs(
        self, *, selected_file: str | None = None, line_limit: int = DEFAULT_LINE_LIMIT
    ) -> LogViewerResponse:
        files = self.list_log_files()
        resolved_name = self._resolve_selected_file_name(selected_file, files)
        fetched_at = datetime.now(timezone.utc).isoformat()

        if resolved_name is None:
            return LogViewerResponse(
                files=files,
                selected_file=None,
                line_limit=line_limit,
                total_lines=0,
                truncated=False,
                lines=[],
                fetched_at=fetched_at,
            )

        log_path = self._resolve_allowed_log_path(resolved_name)
        total_lines, lines, truncated = self._read_trailing_lines(log_path, line_limit)

        return LogViewerResponse(
            files=files,
            selected_file=resolved_name,
            line_limit=line_limit,
            total_lines=total_lines,
            truncated=truncated,
            lines=lines,
            fetched_at=fetched_at,
        )

    def get_log_download_path(self, *, selected_file: str | None = None) -> Path:
        files = self.list_log_files()
        resolved_name = self._resolve_selected_file_name(selected_file, files)
        if resolved_name is None:
            raise FileNotFoundError("No managed log files are available.")
        return self._resolve_allowed_log_path(resolved_name)

    def list_log_files(self) -> list[LogFileInfo]:
        if not settings.log_dir.exists():
            return []

        files: list[LogFileInfo] = []
        for index, filename in enumerate(self._allowed_log_names()):
            path = settings.log_dir / filename
            if not path.is_file():
                continue

            stat = path.stat()
            files.append(
                LogFileInfo(
                    name=filename,
                    size_bytes=stat.st_size,
                    modified_at=datetime.fromtimestamp(
                        stat.st_mtime, tz=timezone.utc
                    ).isoformat(),
                    is_current=index == 0,
                )
            )

        return files

    @classmethod
    def _allowed_log_names(cls) -> list[str]:
        return [LOG_FILENAME] + [
            f"{LOG_FILENAME}.{index}" for index in range(1, LOG_BACKUP_COUNT + 1)
        ]

    @classmethod
    def _validate_allowed_log_name(cls, filename: str) -> None:
        if filename not in cls._allowed_log_names():
            raise ValueError("Requested log file is not managed by SPF5000.")

    def _resolve_selected_file_name(
        self, selected_file: str | None, files: list[LogFileInfo]
    ) -> str | None:
        available_names = {file.name for file in files}

        if selected_file is not None:
            self._validate_allowed_log_name(selected_file)
            if selected_file not in available_names:
                raise FileNotFoundError("Requested log file does not exist.")
            return selected_file

        if not files:
            return None

        current_log = next((file.name for file in files if file.is_current), None)
        return current_log or files[0].name

    def _resolve_allowed_log_path(self, filename: str) -> Path:
        self._validate_allowed_log_name(filename)

        log_dir = settings.log_dir.resolve()
        log_path = (settings.log_dir / filename).resolve(strict=True)
        if log_path.parent != log_dir:
            raise ValueError("Requested log file is outside the managed log directory.")

        return log_path

    @staticmethod
    def _read_trailing_lines(path: Path, line_limit: int) -> tuple[int, list[str], bool]:
        tail: deque[str] = deque(maxlen=line_limit)
        total_lines = 0

        with path.open("r", encoding="utf-8", errors="replace") as fh:
            for raw_line in fh:
                total_lines += 1
                tail.append(raw_line.rstrip("\r\n"))

        return total_lines, list(tail), total_lines > line_limit
