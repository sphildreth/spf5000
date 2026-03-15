from __future__ import annotations

import socket
from pathlib import Path

from app.core.config import settings
from app.db.connection import is_decentdb_available
from app.repositories.asset_repository import AssetRepository
from app.repositories.collection_repository import CollectionRepository
from app.repositories.import_repository import ImportRepository
from app.repositories.source_repository import SourceRepository
from app.services.display_service import DisplayService


class SystemService:
    def __init__(
        self,
        source_repo: SourceRepository | None = None,
        collection_repo: CollectionRepository | None = None,
        asset_repo: AssetRepository | None = None,
        import_repo: ImportRepository | None = None,
        display_service: DisplayService | None = None,
    ) -> None:
        self.source_repo = source_repo or SourceRepository()
        self.collection_repo = collection_repo or CollectionRepository()
        self.asset_repo = asset_repo or AssetRepository()
        self.import_repo = import_repo or ImportRepository()
        self.display_service = display_service or DisplayService()

    def get_status(self) -> dict[str, object]:
        profile = self.display_service.get_config()
        collection = None
        if profile.selected_collection_id:
            collection = self.collection_repo.get_collection(profile.selected_collection_id)
        latest_job = self.import_repo.get_latest_job()
        source_count = len(self.source_repo.list_sources())
        collection_count = len(self.collection_repo.list_collections())
        asset_count = self.asset_repo.count_assets()
        warnings: list[str] = []

        if not is_decentdb_available():
            warnings.append("DecentDB is unavailable; NullConnection fallback is active.")
        if not settings.local_import_dir.exists():
            warnings.append("The default local import directory is missing.")
        if asset_count == 0:
            warnings.append("No assets have been imported yet.")

        status = "degraded" if not is_decentdb_available() or not settings.local_import_dir.exists() else "ready"

        return {
            "ok": True,
            "app": settings.app_name,
            "status": status,
            "version": settings.app_version,
            "hostname": socket.gethostname(),
            "asset_count": asset_count,
            "collection_count": collection_count,
            "source_count": source_count,
            "last_sync_at": None if latest_job is None else latest_job.completed_at,
            "warnings": warnings,
            "database": {
                "available": is_decentdb_available(),
                "path": str(settings.database_path),
                "mode": "decentdb" if is_decentdb_available() else "null",
            },
            "storage": {
                "data_dir": str(settings.data_dir),
                "originals_dir": str(settings.originals_dir),
                "display_variants_dir": str(settings.display_variants_dir),
                "thumbnails_dir": str(settings.thumbnails_dir),
                "local_import_dir": str(settings.local_import_dir),
                "fallback_asset_url": "/fallback/empty-display.jpg",
            },
            "counts": {
                "sources": source_count,
                "collections": collection_count,
                "assets": asset_count,
                "import_jobs": self.import_repo.count_jobs(),
            },
            "active_display_profile": {
                "id": profile.id,
                "name": profile.name,
                "selected_collection_id": profile.selected_collection_id,
                "shuffle_enabled": profile.shuffle_enabled,
            },
            "active_collection": None
            if collection is None
            else {
                "id": collection.id,
                "name": collection.name,
                "asset_count": collection.asset_count,
            },
            "latest_import_job": None
            if latest_job is None
            else {
                "id": latest_job.id,
                "status": latest_job.status,
                "imported_count": latest_job.imported_count,
                "duplicate_count": latest_job.duplicate_count,
                "error_count": latest_job.error_count,
                "message": latest_job.message,
                "completed_at": latest_job.completed_at,
            },
            "paths_exist": {
                "database_parent": Path(settings.database_path).parent.exists(),
                "local_import_dir": settings.local_import_dir.exists(),
                "storage_dir": settings.storage_dir.exists(),
            },
        }
