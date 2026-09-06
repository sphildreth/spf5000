from __future__ import annotations

import gc
import structlog
from pathlib import Path
from uuid import uuid4

from app.models.import_job import ImportJob
from app.providers.base import ProviderScanResult
from app.repositories.asset_repository import AssetRepository
from app.repositories.base import utc_now
from app.repositories.import_repository import ImportRepository
from app.repositories.settings_repository import SettingsRepository
from app.repositories.source_repository import SourceRepository
from app.core.memory import trim_process_heap
from app.services.asset_ingest_service import AssetIngestService
from app.services.source_service import SourceService

LOGGER = structlog.get_logger(__name__)


class ImportService:
    def __init__(
        self,
        asset_repo: AssetRepository | None = None,
        import_repo: ImportRepository | None = None,
        source_repo: SourceRepository | None = None,
        source_service: SourceService | None = None,
        settings_repo: SettingsRepository | None = None,
        ingest_service: AssetIngestService | None = None,
    ) -> None:
        self.asset_repo = asset_repo or AssetRepository()
        self.import_repo = import_repo or ImportRepository()
        self.source_repo = source_repo or SourceRepository()
        self.source_service = source_service or SourceService(repo=self.source_repo)
        self.settings_repo = settings_repo or SettingsRepository()
        self.ingest_service = ingest_service or AssetIngestService(
            asset_repo=self.asset_repo,
            settings_repo=self.settings_repo,
        )

    def scan_local_source(
        self, source_id: str, max_samples: int = 10
    ) -> tuple[ImportJob, ProviderScanResult]:
        source = self.source_service.get_source(source_id)
        if source is None:
            raise ValueError(f"Unknown source: {source_id}")
        if source.provider_type != "local_files":
            raise ValueError(
                f"Source {source_id} does not support local scan/import operations"
            )
        provider = self.source_service.get_provider(source.provider_type)
        scan_result = provider.scan_directory(
            source.import_path, sample_limit=max_samples
        )
        now = utc_now()
        job = ImportJob(
            id=f"scan-{uuid4().hex}",
            job_type="scan",
            status="completed",
            source_id=source.id,
            collection_id=None,
            import_path=scan_result.import_path,
            discovered_count=scan_result.discovered_count,
            imported_count=0,
            duplicate_count=0,
            skipped_count=scan_result.ignored_count,
            error_count=0,
            sample_filenames=[item.filename for item in scan_result.discovered],
            message=f"Scanned {scan_result.discovered_count} supported files",
            started_at=now,
            completed_at=now,
        )
        stored_job = self.import_repo.create_job(job)
        self.source_repo.touch_last_scan(source.id, now)
        return stored_job, scan_result

    def scan_directory(self, source_id: str, max_samples: int = 10) -> ProviderScanResult:
        """
        Scan a source directory and return discovered files.

        Used by auto-scan scheduler and watcher for automatic scanning.
        Does not create a job record - just returns the scan result.
        """
        source = self.source_service.get_source(source_id)
        if source is None:
            raise ValueError(f"Unknown source: {source_id}")
        if source.provider_type != "local_files":
            raise ValueError(
                f"Source {source_id} does not support local scan/import operations"
            )
        provider = self.source_service.get_provider(source.provider_type)
        scan_result = provider.scan_directory(
            source.import_path, sample_limit=max_samples
        )
        self.source_repo.touch_last_scan(source.id, utc_now())
        return scan_result

    def import_local_source(
        self, source_id: str, collection_id: str, max_samples: int = 10
    ) -> ImportJob:
        source = self.source_service.get_source(source_id)
        if source is None:
            raise ValueError(f"Unknown source: {source_id}")
        if source.provider_type != "local_files":
            raise ValueError(
                f"Source {source_id} does not support local scan/import operations"
            )
        provider = self.source_service.get_provider(source.provider_type)
        started_at = utc_now()
        job = ImportJob(
            id=f"import-{uuid4().hex}",
            job_type="import",
            status="running",
            source_id=source.id,
            collection_id=collection_id,
            import_path=str(Path(source.import_path).resolve()),
            discovered_count=0,
            imported_count=0,
            duplicate_count=0,
            skipped_count=0,
            error_count=0,
            sample_filenames=[],
            message="Import in progress",
            started_at=started_at,
            completed_at=None,
        )
        self.import_repo.create_job(job)

        walk_directory = getattr(provider, "walk_directory", None)
        if callable(walk_directory):
            walk = walk_directory(source.import_path, sample_limit=max_samples)
            candidates = walk
        else:
            walk = None
            candidates = provider.iter_directory(source.import_path)

        for candidate in candidates:
            job.discovered_count += 1
            if len(job.sample_filenames) < max_samples:
                job.sample_filenames.append(candidate.filename)
            try:
                ingest_result = self.ingest_service.ingest_file(
                    source_id=source.id,
                    collection_ids=[collection_id],
                    source_path=Path(candidate.path),
                    imported_from_path=str(Path(candidate.path)),
                )
                if ingest_result.created:
                    job.imported_count += 1
                    gc.collect()
                    trim_process_heap()
                else:
                    job.duplicate_count += 1
            except Exception as exc:  # pragma: no cover
                LOGGER.exception("import_file_failed", path=str(candidate.path))
                job.error_count += 1
                job.message = f"Import completed with {job.error_count} errors"
                LOGGER.error("import_job_error", error=str(exc))

        if walk is not None:
            job.skipped_count = walk.ignored_count

        job.status = "completed" if job.error_count == 0 else "completed_with_errors"
        job.message = f"Imported {job.imported_count} new assets, {job.duplicate_count} duplicates, {job.error_count} errors"
        job.completed_at = utc_now()
        self.source_repo.touch_last_scan(source.id, job.completed_at)
        self.source_repo.touch_last_import(source.id, job.completed_at)
        return self.import_repo.update_job(job)

    def get_latest_job(self) -> ImportJob | None:
        return self.import_repo.get_latest_job()
