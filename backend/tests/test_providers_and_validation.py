"""Tests for provider and backup validation edge cases."""

from __future__ import annotations

import io
import json
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

import pytest
from PIL import Image

from app.core.config import settings
from app.providers.local_files import LocalFilesProvider


def test_local_files_health_check_returns_correct_info(tmp_path: Path) -> None:
    """health_check returns ok=False for non-existent paths."""
    provider = LocalFilesProvider()
    result = provider.health_check("/nonexistent/path")
    assert result["ok"] is False
    assert result["provider"] == "local_files"


def test_local_files_health_check_exists_directory(tmp_path: Path) -> None:
    """health_check returns ok=True for existing directories."""
    provider = LocalFilesProvider()
    test_dir = tmp_path / "existing"
    test_dir.mkdir()
    result = provider.health_check(str(test_dir))
    assert result["ok"] is True


def test_local_files_scan_restricted_to_sources_root(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """scan_directory rejects paths outside sources_root_dir."""
    sources_root = tmp_path / "sources"
    sources_root.mkdir()
    monkeypatch.setattr(settings, "data_dir", tmp_path)

    outside_dir = tmp_path / "outside"
    outside_dir.mkdir()
    (outside_dir / "secret.jpg").touch()

    provider = LocalFilesProvider()
    result = provider.scan_directory(str(outside_dir))
    assert result.discovered == []
    assert result.ignored_count == 0


def test_local_files_scan_with_depth_limit(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """scan_directory respects depth limit."""
    import app.providers.local_files as lf

    monkeypatch.setattr(lf, "_MAX_SCAN_DEPTH", 2)
    monkeypatch.setattr(settings, "data_dir", tmp_path)

    scan_root = tmp_path / "sources" / "scan"
    scan_root.mkdir(parents=True, exist_ok=True)

    _write_jpeg(scan_root / "level1.jpg", (10, 10, 10))
    level1 = scan_root / "level1"
    level1.mkdir()
    _write_jpeg(level1 / "level2.jpg", (10, 10, 10))
    level2 = level1 / "level2"
    level2.mkdir()
    _write_jpeg(level2 / "level3.jpg", (10, 10, 10))

    provider = LocalFilesProvider()
    result = provider.scan_directory(str(scan_root))

    paths = {Path(p.path).name for p in result.discovered}
    assert "level1.jpg" in paths
    assert "level2.jpg" in paths
    assert "level3.jpg" not in paths


def test_local_files_scan_with_file_count_limit(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """scan_directory respects file count limit."""
    import app.providers.local_files as lf

    monkeypatch.setattr(lf, "_MAX_FILES_PER_SCAN", 3)
    monkeypatch.setattr(settings, "data_dir", tmp_path)

    scan_root = tmp_path / "sources" / "scan"
    scan_root.mkdir(parents=True, exist_ok=True)

    for i in range(5):
        _write_jpeg(scan_root / f"image{i}.jpg", (10, 10, 10))

    provider = LocalFilesProvider()
    result = provider.scan_directory(str(scan_root))

    assert len(result.discovered) == 3


def test_backup_archive_empty_rejected(tmp_path: Path) -> None:
    """Empty ZIP archive is rejected."""
    from app.services.backup_service import BackupService

    service = BackupService()

    buffer = io.BytesIO()
    with ZipFile(buffer, "w") as zf:
        pass
    buffer.seek(0)

    with pytest.raises(ValueError, match="empty"):
        service._read_database_backup_bytes(buffer)


def test_backup_archive_invalid_member_path_rejected(tmp_path: Path) -> None:
    """Absolute path in archive member is rejected."""
    from app.services.backup_service import BackupService

    service = BackupService()

    buffer = io.BytesIO()
    with ZipFile(buffer, "w", compression=ZIP_DEFLATED) as zf:
        zf.writestr("/absolute/path.txt", "evil")
        zf.writestr(
            "backup-manifest.json",
            json.dumps({"type": "database-backup", "database_filename": "spf5000.ddb"}),
        )
    buffer.seek(0)

    with pytest.raises(ValueError, match="invalid member path"):
        service._read_database_backup_bytes(buffer)


def test_backup_archive_traversal_path_rejected(tmp_path: Path) -> None:
    """Path traversal (..) in archive member is rejected."""
    from app.services.backup_service import BackupService

    service = BackupService()

    buffer = io.BytesIO()
    with ZipFile(buffer, "w", compression=ZIP_DEFLATED) as zf:
        zf.writestr("../traverse.txt", "evil")
        zf.writestr(
            "backup-manifest.json",
            json.dumps({"type": "database-backup", "database_filename": "spf5000.ddb"}),
        )
    buffer.seek(0)

    with pytest.raises(ValueError, match="invalid member path"):
        service._read_database_backup_bytes(buffer)


def test_backup_archive_duplicate_member_rejected(tmp_path: Path) -> None:
    """Duplicate archive members are rejected."""
    import warnings

    from app.services.backup_service import BackupService

    service = BackupService()

    buffer = io.BytesIO()
    with warnings.catch_warnings():
        warnings.filterwarnings(
            "ignore", message="Duplicate name", category=UserWarning
        )
        with ZipFile(buffer, "w", compression=ZIP_DEFLATED) as zf:
            zf.writestr("spf5000.ddb", b"data")
            zf.writestr("spf5000.ddb", b"data")
            zf.writestr(
                "backup-manifest.json",
                json.dumps(
                    {"type": "database-backup", "database_filename": "spf5000.ddb"}
                ),
            )
    buffer.seek(0)

    with pytest.raises(ValueError, match="duplicate"):
        service._read_database_backup_bytes(buffer)


def test_backup_archive_invalid_manifest_type_rejected(tmp_path: Path) -> None:
    """Wrong manifest type is rejected."""
    from app.services.backup_service import BackupService

    service = BackupService()

    buffer = io.BytesIO()
    with ZipFile(buffer, "w", compression=ZIP_DEFLATED) as zf:
        zf.writestr("spf5000.ddb", settings.database_path.read_bytes())
        zf.writestr(
            "backup-manifest.json",
            json.dumps(
                {
                    "type": "not-a-backup",
                    "database_filename": "spf5000.ddb",
                }
            ),
        )
    buffer.seek(0)

    with pytest.raises(ValueError, match="database-backup"):
        service._read_database_backup_bytes(buffer)


def test_backup_archive_wrong_database_filename_rejected(tmp_path: Path) -> None:
    """Wrong database filename in manifest is rejected."""
    from app.services.backup_service import BackupService

    service = BackupService()

    buffer = io.BytesIO()
    with ZipFile(buffer, "w", compression=ZIP_DEFLATED) as zf:
        zf.writestr("spf5000.ddb", settings.database_path.read_bytes())
        zf.writestr(
            "backup-manifest.json",
            json.dumps(
                {
                    "type": "database-backup",
                    "database_filename": "wrong.ddb",
                }
            ),
        )
    buffer.seek(0)

    with pytest.raises(ValueError, match="unexpected database filename"):
        service._read_database_backup_bytes(buffer)


def test_backup_archive_missing_manifest_rejected(tmp_path: Path) -> None:
    """Missing manifest is rejected."""
    from app.services.backup_service import BackupService

    service = BackupService()

    buffer = io.BytesIO()
    with ZipFile(buffer, "w", compression=ZIP_DEFLATED) as zf:
        zf.writestr("spf5000.ddb", settings.database_path.read_bytes())
    buffer.seek(0)

    with pytest.raises(ValueError, match="must include backup-manifest.json"):
        service._read_database_backup_bytes(buffer)


def test_backup_archive_manifest_must_be_object(tmp_path: Path) -> None:
    """Manifest that is not a JSON object is rejected."""
    from app.services.backup_service import BackupService

    service = BackupService()

    buffer = io.BytesIO()
    with ZipFile(buffer, "w", compression=ZIP_DEFLATED) as zf:
        zf.writestr("spf5000.ddb", settings.database_path.read_bytes())
        zf.writestr("backup-manifest.json", "not json")
    buffer.seek(0)

    with pytest.raises(ValueError, match="valid UTF-8 JSON"):
        service._read_database_backup_bytes(buffer)


def test_backup_archive_manifest_utf8_required(tmp_path: Path) -> None:
    """Manifest must be valid UTF-8."""
    from app.services.backup_service import BackupService

    service = BackupService()

    buffer = io.BytesIO()
    with ZipFile(buffer, "w", compression=ZIP_DEFLATED) as zf:
        zf.writestr("spf5000.ddb", settings.database_path.read_bytes())
        zf.writestr("backup-manifest.json", b"\xff\xfe invalid utf-8")
    buffer.seek(0)

    with pytest.raises(ValueError, match="UTF-8 JSON"):
        service._read_database_backup_bytes(buffer)


def _write_jpeg(path: Path, color: tuple[int, int, int]) -> None:
    buf = io.BytesIO()
    Image.new("RGB", (10, 10), color=color).save(buf, format="JPEG")
    path.write_bytes(buf.getvalue())
