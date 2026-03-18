from __future__ import annotations

import shutil
import socket
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

from app.core.config import settings
from app.db.connection import (
    decentdb,
    get_connection,
    is_decentdb_available,
    is_null_connection,
)
from app.models.weather import WeatherProviderState
from app.repositories.admin_repository import AdminRepository
from app.repositories.asset_repository import AssetRepository
from app.repositories.collection_repository import CollectionRepository
from app.repositories.source_repository import SourceRepository
from app.repositories.weather_repository import WeatherRepository
from app.schemas.doctor import (
    DoctorResponse,
    HealthCheck,
    HealthCheckGroup,
    HealthSeverity,
)
from app.services.weather_service import WeatherService


def _get_package_version(package_name: str) -> str | None:
    try:
        from importlib.metadata import version

        return version(package_name)
    except Exception:
        return None


class ApplicationDoctorChecks:
    @staticmethod
    def run() -> list[HealthCheck]:
        checks: list[HealthCheck] = []

        checks.append(
            HealthCheck(
                id="app_reachable",
                title="Application Status",
                severity=HealthSeverity.OK,
                summary="SPF5000 backend is running and responsive.",
            )
        )

        checks.append(
            HealthCheck(
                id="app_version",
                title="Application Version",
                severity=HealthSeverity.INFO,
                summary=f"Running SPF5000 v{settings.app_version}.",
                details=f"Python {sys.version.split()[0]}.",
            )
        )

        checks.append(
            ApplicationDoctorChecks._check_dependencies(),
        )

        checks.append(
            HealthCheck(
                id="system_time",
                title="System Time",
                severity=HealthSeverity.OK,
                summary=f"System time: {datetime.now(UTC).strftime('%Y-%m-%d %H:%M:%S UTC')}.",
            )
        )

        hostname = socket.gethostname()
        checks.append(
            HealthCheck(
                id="hostname",
                title="Hostname",
                severity=HealthSeverity.INFO,
                summary=f"Hostname: {hostname}.",
            )
        )

        return checks

    @staticmethod
    def _check_dependencies() -> HealthCheck:
        deps = []
        missing = []

        dep_map = [
            ("decentdb", "DecentDB"),
            ("fastapi", "FastAPI"),
            ("uvicorn", "Uvicorn"),
        ]

        for pkg, label in dep_map:
            ver = _get_package_version(pkg)
            if ver:
                deps.append(f"{label} {ver}")
            else:
                missing.append(label)

        if missing:
            return HealthCheck(
                id="dependencies",
                title="Dependencies",
                severity=HealthSeverity.WARNING,
                summary=f"Installed: {', '.join(deps)}.",
                details=f"Could not determine versions for: {', '.join(missing)}.",
            )

        return HealthCheck(
            id="dependencies",
            title="Dependencies",
            severity=HealthSeverity.INFO,
            summary=f"{', '.join(deps)}.",
        )


class DatabaseDoctorChecks:
    @staticmethod
    def run() -> list[HealthCheck]:
        checks: list[HealthCheck] = []

        checks.append(
            DatabaseDoctorChecks._check_file_exists(),
        )
        checks.append(
            DatabaseDoctorChecks._check_connection(),
        )
        checks.append(
            DatabaseDoctorChecks._check_schema(),
        )

        return checks

    @staticmethod
    def _check_file_exists() -> HealthCheck:
        db_path = settings.database_path
        if db_path.exists():
            size_mb = db_path.stat().st_size / (1024 * 1024)
            return HealthCheck(
                id="database_file",
                title="Database File",
                severity=HealthSeverity.OK,
                summary=f"Database file exists at {db_path.name}.",
                details=f"Size: {size_mb:.2f} MB.",
            )
        return HealthCheck(
            id="database_file",
            title="Database File",
            severity=HealthSeverity.ERROR,
            summary="Database file not found.",
            details=f"Expected at: {db_path}",
            remediation="Check data directory configuration or restore from backup.",
        )

    @staticmethod
    def _check_connection() -> HealthCheck:
        if decentdb is None:
            return HealthCheck(
                id="database_connection",
                title="Database Connection",
                severity=HealthSeverity.ERROR,
                summary="DecentDB library not available.",
                remediation="Install DecentDB or use a database-enabled runtime.",
            )

        try:
            with get_connection() as conn:
                if is_null_connection(conn):
                    return HealthCheck(
                        id="database_connection",
                        title="Database Connection",
                        severity=HealthSeverity.ERROR,
                        summary="Cannot connect to DecentDB.",
                        remediation="Verify DecentDB is properly installed and the database file is accessible.",
                    )
                conn.execute("SELECT 1").fetchone()
            return HealthCheck(
                id="database_connection",
                title="Database Connection",
                severity=HealthSeverity.OK,
                summary="Database connection successful.",
            )
        except Exception as exc:
            return HealthCheck(
                id="database_connection",
                title="Database Connection",
                severity=HealthSeverity.ERROR,
                summary=f"Database query failed: {exc}",
                remediation="Check database integrity and permissions.",
            )

    @staticmethod
    def _check_schema() -> HealthCheck:
        required_tables = {"settings", "admin_users", "collections"}
        try:
            with get_connection() as conn:
                if is_null_connection(conn):
                    return HealthCheck(
                        id="database_schema",
                        title="Database Schema",
                        severity=HealthSeverity.ERROR,
                        summary="Cannot check schema - no database connection.",
                    )
                existing_tables = set(conn.list_tables())
        except Exception as exc:
            return HealthCheck(
                id="database_schema",
                title="Database Schema",
                severity=HealthSeverity.ERROR,
                summary=f"Failed to list tables: {exc}",
            )

        missing = required_tables - existing_tables
        if missing:
            return HealthCheck(
                id="database_schema",
                title="Database Schema",
                severity=HealthSeverity.ERROR,
                summary=f"Missing required tables: {', '.join(sorted(missing))}.",
                remediation="Run database migrations or restore from a known-good backup.",
            )

        return HealthCheck(
            id="database_schema",
            title="Database Schema",
            severity=HealthSeverity.OK,
            summary="All required tables present.",
            details=f"Found: {', '.join(sorted(existing_tables))}.",
        )


class StorageDoctorChecks:
    @staticmethod
    def run() -> list[HealthCheck]:
        checks: list[HealthCheck] = []

        paths_to_check = [
            ("data_dir", "Data Directory", settings.data_dir),
            ("cache_dir", "Cache Directory", settings.cache_dir),
            ("storage_dir", "Storage Directory", settings.storage_dir),
            ("originals_dir", "Originals Directory", settings.originals_dir),
            ("variants_dir", "Variants Directory", settings.variants_dir),
        ]

        for path_id, path_title, path in paths_to_check:
            checks.append(StorageDoctorChecks._check_path(path_id, path_title, path))

        disk = StorageDoctorChecks._check_disk_space()
        checks.append(disk)

        return checks

    @staticmethod
    def _check_path(path_id: str, path_title: str, path: Path) -> HealthCheck:
        if not path.exists():
            return HealthCheck(
                id=path_id,
                title=path_title,
                severity=HealthSeverity.WARNING,
                summary=f"Directory does not exist: {path.name}.",
                details=f"Full path: {path}",
                remediation="The directory will be created on first use.",
            )

        if not path.is_dir():
            return HealthCheck(
                id=path_id,
                title=path_title,
                severity=HealthSeverity.ERROR,
                summary=f"Path exists but is not a directory: {path}",
                remediation="Fix the path configuration or remove the conflicting file.",
            )

        if not _is_writable(path):
            return HealthCheck(
                id=path_id,
                title=path_title,
                severity=HealthSeverity.WARNING,
                summary=f"Directory may not be writable: {path.name}.",
                remediation="Check directory permissions.",
            )

        return HealthCheck(
            id=path_id,
            title=path_title,
            severity=HealthSeverity.OK,
            summary=f"Directory accessible: {path.name}.",
        )

    @staticmethod
    def _check_disk_space() -> HealthCheck:
        try:
            du = shutil.disk_usage(settings.data_dir)
            percent_used = (du.used / du.total) * 100

            if percent_used > 90:
                return HealthCheck(
                    id="disk_space",
                    title="Disk Space",
                    severity=HealthSeverity.ERROR,
                    summary=f"Disk is {percent_used:.1f}% full.",
                    details=f"Free: {du.free / (1024**3):.1f} GB / Total: {du.total / (1024**3):.1f} GB.",
                    remediation="Free up disk space to prevent data loss.",
                )
            if percent_used > 75:
                return HealthCheck(
                    id="disk_space",
                    title="Disk Space",
                    severity=HealthSeverity.WARNING,
                    summary=f"Disk is {percent_used:.1f}% full.",
                    details=f"Free: {du.free / (1024**3):.1f} GB.",
                    remediation="Consider freeing up disk space soon.",
                )

            return HealthCheck(
                id="disk_space",
                title="Disk Space",
                severity=HealthSeverity.OK,
                summary=f"Disk usage normal ({percent_used:.1f}% full).",
                details=f"Free: {du.free / (1024**3):.1f} GB.",
            )
        except OSError:
            return HealthCheck(
                id="disk_space",
                title="Disk Space",
                severity=HealthSeverity.WARNING,
                summary="Could not determine disk usage.",
                remediation="Check disk accessibility manually.",
            )


class AuthDoctorChecks:
    @staticmethod
    def run() -> list[HealthCheck]:
        checks: list[HealthCheck] = []
        admin_repo = AdminRepository()

        checks.append(AuthDoctorChecks._check_auth_available())
        checks.append(AuthDoctorChecks._check_admin_users(admin_repo))

        return checks

    @staticmethod
    def _check_auth_available() -> HealthCheck:
        try:
            admin_repo = AdminRepository()
            available = admin_repo.auth_available()
            if available:
                return HealthCheck(
                    id="auth_available",
                    title="Authentication System",
                    severity=HealthSeverity.OK,
                    summary="Authentication system is available.",
                )
            return HealthCheck(
                id="auth_available",
                title="Authentication System",
                severity=HealthSeverity.ERROR,
                summary="Authentication system is unavailable.",
                remediation="Check database connection and initialization.",
            )
        except Exception as exc:
            return HealthCheck(
                id="auth_available",
                title="Authentication System",
                severity=HealthSeverity.ERROR,
                summary=f"Authentication check failed: {exc}",
            )

    @staticmethod
    def _check_admin_users(admin_repo: AdminRepository) -> HealthCheck:
        try:
            count = admin_repo.count_enabled_admins()
            if count == 0:
                return HealthCheck(
                    id="admin_users",
                    title="Admin Users",
                    severity=HealthSeverity.WARNING,
                    summary="No admin users configured.",
                    remediation="Complete initial setup to create an admin account.",
                )
            return HealthCheck(
                id="admin_users",
                title="Admin Users",
                severity=HealthSeverity.OK,
                summary=f"{count} admin user(s) configured.",
            )
        except Exception as exc:
            return HealthCheck(
                id="admin_users",
                title="Admin Users",
                severity=HealthSeverity.ERROR,
                summary=f"Failed to check admin users: {exc}",
            )


class MediaDoctorChecks:
    @staticmethod
    def run() -> list[HealthCheck]:
        checks: list[HealthCheck] = []

        checks.append(MediaDoctorChecks._check_collections())
        checks.append(MediaDoctorChecks._check_assets())
        checks.append(MediaDoctorChecks._check_active_collection())

        return checks

    @staticmethod
    def _check_collections() -> HealthCheck:
        try:
            repo = CollectionRepository()
            collections = repo.list_collections()
            count = len(collections)

            if count == 0:
                return HealthCheck(
                    id="collections_exist",
                    title="Collections",
                    severity=HealthSeverity.WARNING,
                    summary="No collections exist.",
                    remediation="Create a collection from the Collections page.",
                )

            return HealthCheck(
                id="collections_exist",
                title="Collections",
                severity=HealthSeverity.OK,
                summary=f"{count} collection(s) configured.",
            )
        except Exception as exc:
            return HealthCheck(
                id="collections_exist",
                title="Collections",
                severity=HealthSeverity.ERROR,
                summary=f"Failed to check collections: {exc}",
            )

    @staticmethod
    def _check_assets() -> HealthCheck:
        try:
            repo = AssetRepository()
            count = repo.count_assets()

            if count == 0:
                return HealthCheck(
                    id="assets_exist",
                    title="Playable Assets",
                    severity=HealthSeverity.WARNING,
                    summary="No playable images found.",
                    remediation="Import images from Sources or add photos to a collection.",
                )

            return HealthCheck(
                id="assets_exist",
                title="Playable Assets",
                severity=HealthSeverity.OK,
                summary=f"{count} active image(s) available.",
            )
        except Exception as exc:
            return HealthCheck(
                id="assets_exist",
                title="Playable Assets",
                severity=HealthSeverity.ERROR,
                summary=f"Failed to check assets: {exc}",
            )

    @staticmethod
    def _check_active_collection() -> HealthCheck:
        try:
            from app.repositories.settings_repository import SettingsRepository

            repo = CollectionRepository()
            settings_repo = SettingsRepository()
            settings = settings_repo.get_settings()

            if not settings.selected_collection_id:
                return HealthCheck(
                    id="active_collection",
                    title="Active Collection",
                    severity=HealthSeverity.INFO,
                    summary="No specific collection selected; will use all active assets.",
                )

            collection = repo.get_collection(settings.selected_collection_id)
            if collection is None:
                return HealthCheck(
                    id="active_collection",
                    title="Active Collection",
                    severity=HealthSeverity.WARNING,
                    summary="Selected collection no longer exists.",
                    remediation="Select a valid collection in Display Settings.",
                )

            if not collection.is_active:
                return HealthCheck(
                    id="active_collection",
                    title="Active Collection",
                    severity=HealthSeverity.WARNING,
                    summary=f"Selected collection '{collection.name}' is inactive.",
                    remediation="Activate the collection in Collections Settings.",
                )

            return HealthCheck(
                id="active_collection",
                title="Active Collection",
                severity=HealthSeverity.OK,
                summary=f"Active collection: {collection.name}.",
            )
        except Exception as exc:
            return HealthCheck(
                id="active_collection",
                title="Active Collection",
                severity=HealthSeverity.WARNING,
                summary=f"Could not verify active collection: {exc}",
            )


class ProviderDoctorChecks:
    @staticmethod
    def run() -> list[HealthCheck]:
        checks: list[HealthCheck] = []

        try:
            source_repo = SourceRepository()
            sources = source_repo.list_sources()
        except Exception as exc:
            return [
                HealthCheck(
                    id="sources_overall",
                    title="Sources",
                    severity=HealthSeverity.ERROR,
                    summary=f"Failed to check sources: {exc}",
                )
            ]

        if not sources:
            checks.append(
                HealthCheck(
                    id="sources_overall",
                    title="Sources",
                    severity=HealthSeverity.WARNING,
                    summary="No sources configured.",
                    remediation="Add a source from the Sources page to enable image imports.",
                )
            )
        else:
            enabled_count = sum(1 for s in sources if s.enabled)
            checks.append(
                HealthCheck(
                    id="sources_overall",
                    title="Sources",
                    severity=HealthSeverity.OK
                    if enabled_count > 0
                    else HealthSeverity.WARNING,
                    summary=f"{len(sources)} source(s) total, {enabled_count} enabled.",
                )
            )

        for source in sources:
            checks.append(ProviderDoctorChecks._check_source(source))

        return checks

    @staticmethod
    def _check_source(source) -> HealthCheck:
        try:
            provider_type = source.provider_type
            health: dict = {}

            if provider_type == "local_files":
                from app.providers.local_files import LocalFilesProvider

                provider = LocalFilesProvider()
                health = provider.health_check(source.import_path or "")
            elif provider_type == "google_photos":
                from app.providers.google_photos import GooglePhotosProvider

                provider = GooglePhotosProvider()
                health = provider.health_check(source.import_path or "")

            is_healthy = health.get("ok", health.get("available", False))
            is_configured = health.get("configured", True)

            if not source.enabled:
                return HealthCheck(
                    id=f"source_{source.id}",
                    title=f"Source: {source.name}",
                    severity=HealthSeverity.INFO,
                    summary=f"Source is disabled.",
                )

            if not is_configured and provider_type == "google_photos":
                return HealthCheck(
                    id=f"source_{source.id}",
                    title=f"Source: {source.name}",
                    severity=HealthSeverity.WARNING,
                    summary="Google Photos source configured but not connected.",
                    remediation="Reconnect Google Photos from the Sources page.",
                )

            if not is_healthy:
                return HealthCheck(
                    id=f"source_{source.id}",
                    title=f"Source: {source.name}",
                    severity=HealthSeverity.WARNING,
                    summary=f"Source path not accessible: {source.import_path}.",
                    remediation="Verify the import path exists and is accessible.",
                )

            return HealthCheck(
                id=f"source_{source.id}",
                title=f"Source: {source.name}",
                severity=HealthSeverity.OK,
                summary=f"Source is healthy.",
                details=f"Type: {provider_type}, Path: {source.import_path}",
            )

        except Exception as exc:
            return HealthCheck(
                id=f"source_{source.id}",
                title=f"Source: {source.name}",
                severity=HealthSeverity.WARNING,
                summary=f"Health check failed: {exc}",
            )


class WeatherDoctorChecks:
    @staticmethod
    def run() -> list[HealthCheck]:
        checks: list[HealthCheck] = []

        try:
            weather_service = WeatherService()
            settings = weather_service.get_settings()
        except Exception as exc:
            return [
                HealthCheck(
                    id="weather_overall",
                    title="Weather",
                    severity=HealthSeverity.ERROR,
                    summary=f"Failed to check weather service: {exc}",
                )
            ]

        checks.append(WeatherDoctorChecks._check_weather_enabled(settings))
        checks.append(WeatherDoctorChecks._check_weather_location(settings))

        if settings.weather_enabled and settings.weather_location.is_configured:
            checks.append(WeatherDoctorChecks._check_weather_provider(weather_service))

        return checks

    @staticmethod
    def _check_weather_enabled(settings) -> HealthCheck:
        if not settings.weather_enabled:
            return HealthCheck(
                id="weather_enabled",
                title="Weather Feature",
                severity=HealthSeverity.INFO,
                summary="Weather feature is disabled.",
            )
        return HealthCheck(
            id="weather_enabled",
            title="Weather Feature",
            severity=HealthSeverity.OK,
            summary="Weather feature is enabled.",
        )

    @staticmethod
    def _check_weather_location(settings) -> HealthCheck:
        if not settings.weather_location.is_configured:
            return HealthCheck(
                id="weather_location",
                title="Weather Location",
                severity=HealthSeverity.WARNING,
                summary="Weather location not configured.",
                remediation="Set a location in Weather settings.",
            )
        return HealthCheck(
            id="weather_location",
            title="Weather Location",
            severity=HealthSeverity.OK,
            summary=f"Location: {settings.weather_location.label or 'coordinates'}.",
        )

    @staticmethod
    def _check_weather_provider(weather_service: WeatherService) -> HealthCheck:
        try:
            state = weather_service.get_provider_state()
        except Exception as exc:
            return HealthCheck(
                id="weather_provider",
                title="Weather Provider",
                severity=HealthSeverity.ERROR,
                summary=f"Failed to get provider state: {exc}",
            )

        checks: list[HealthCheck] = []

        checks.append(
            HealthCheck(
                id="weather_provider_status",
                title="Weather Provider",
                severity=HealthSeverity.OK
                if state.available
                else HealthSeverity.WARNING,
                summary=f"Provider '{state.provider_display_name}' is {state.status}.",
                details=f"Status: {state.status}",
            )
        )

        if state.current_error:
            checks.append(
                HealthCheck(
                    id="weather_last_error",
                    title="Weather Error",
                    severity=HealthSeverity.ERROR,
                    summary=f"Last error: {state.current_error}",
                    remediation="Check internet connectivity or provider credentials.",
                )
            )

        if state.last_successful_weather_refresh_at:
            stale_threshold = datetime.now(UTC) - timedelta(hours=1)
            try:
                last_refresh = datetime.fromisoformat(
                    state.last_successful_weather_refresh_at.replace("Z", "+00:00")
                )
                if last_refresh.tzinfo is None:
                    last_refresh = last_refresh.replace(tzinfo=UTC)
                if last_refresh < stale_threshold:
                    checks.append(
                        HealthCheck(
                            id="weather_stale",
                            title="Weather Data Freshness",
                            severity=HealthSeverity.WARNING,
                            summary="Weather data may be stale.",
                            details=f"Last successful refresh: {state.last_successful_weather_refresh_at}",
                            remediation="Check internet connectivity or trigger a manual refresh.",
                        )
                    )
                else:
                    checks.append(
                        HealthCheck(
                            id="weather_stale",
                            title="Weather Data Freshness",
                            severity=HealthSeverity.OK,
                            summary="Weather data is fresh.",
                            details=f"Last refresh: {state.last_successful_weather_refresh_at}",
                        )
                    )
            except (ValueError, TypeError):
                pass

        return (
            checks[0]
            if checks
            else HealthCheck(
                id="weather_provider",
                title="Weather Provider",
                severity=HealthSeverity.OK,
                summary="Weather provider is available.",
            )
        )


class DisplayDoctorChecks:
    @staticmethod
    def run() -> list[HealthCheck]:
        checks: list[HealthCheck] = []

        checks.append(DisplayDoctorChecks._check_display_config())
        checks.append(DisplayDoctorChecks._check_sleep_schedule())

        return checks

    @staticmethod
    def _check_display_config() -> HealthCheck:
        try:
            from app.repositories.settings_repository import SettingsRepository

            settings_repo = SettingsRepository()
            frame_settings = settings_repo.get_settings()

            if not frame_settings.selected_collection_id:
                return HealthCheck(
                    id="display_config",
                    title="Display Configuration",
                    severity=HealthSeverity.INFO,
                    summary="No specific collection selected for display.",
                    details="All active assets will be shown.",
                )

            return HealthCheck(
                id="display_config",
                title="Display Configuration",
                severity=HealthSeverity.OK,
                summary=f"Display configured (interval: {frame_settings.slideshow_interval_seconds}s).",
            )
        except Exception as exc:
            return HealthCheck(
                id="display_config",
                title="Display Configuration",
                severity=HealthSeverity.WARNING,
                summary=f"Could not verify display config: {exc}",
            )

    @staticmethod
    def _check_sleep_schedule() -> HealthCheck:
        try:
            from app.repositories.settings_repository import SettingsRepository

            settings_repo = SettingsRepository()
            schedule = settings_repo.get_sleep_schedule()

            if schedule.sleep_schedule_enabled:
                return HealthCheck(
                    id="sleep_schedule",
                    title="Sleep Schedule",
                    severity=HealthSeverity.INFO,
                    summary=(
                        "Sleep schedule enabled "
                        f"({schedule.sleep_start_local_time} - {schedule.sleep_end_local_time})."
                    ),
                )

            return HealthCheck(
                id="sleep_schedule",
                title="Sleep Schedule",
                severity=HealthSeverity.INFO,
                summary="Sleep schedule is disabled.",
            )
        except Exception as exc:
            return HealthCheck(
                id="sleep_schedule",
                title="Sleep Schedule",
                severity=HealthSeverity.INFO,
                summary="Could not verify sleep schedule.",
                details=str(exc),
            )


class BackupDoctorChecks:
    @staticmethod
    def run() -> list[HealthCheck]:
        checks: list[HealthCheck] = []

        checks.append(BackupDoctorChecks._check_export_path())

        return checks

    @staticmethod
    def _check_export_path() -> HealthCheck:
        export_dir = settings.staging_dir / "exports"
        try:
            export_dir.mkdir(parents=True, exist_ok=True)
            if _is_writable(export_dir):
                return HealthCheck(
                    id="backup_export",
                    title="Backup / Export",
                    severity=HealthSeverity.OK,
                    summary="Backup and export directories are accessible.",
                )
            return HealthCheck(
                id="backup_export",
                title="Backup / Export",
                severity=HealthSeverity.WARNING,
                summary="Export directory may not be writable.",
                remediation="Check directory permissions.",
            )
        except Exception as exc:
            return HealthCheck(
                id="backup_export",
                title="Backup / Export",
                severity=HealthSeverity.WARNING,
                summary=f"Could not verify export path: {exc}",
            )


def _is_writable(path: Path) -> bool:
    try:
        test_file = path / ".write_test"
        test_file.touch()
        test_file.unlink()
        return True
    except OSError:
        return False


class DoctorService:
    CHECKERS: list[type] = [
        ApplicationDoctorChecks,
        DatabaseDoctorChecks,
        StorageDoctorChecks,
        AuthDoctorChecks,
        MediaDoctorChecks,
        ProviderDoctorChecks,
        WeatherDoctorChecks,
        DisplayDoctorChecks,
        BackupDoctorChecks,
    ]

    GROUP_META: dict[type, tuple[str, str]] = {
        ApplicationDoctorChecks: ("application", "Application"),
        DatabaseDoctorChecks: ("database", "Database"),
        StorageDoctorChecks: ("storage", "Storage / Paths"),
        AuthDoctorChecks: ("auth", "Authentication"),
        MediaDoctorChecks: ("media", "Media / Collections"),
        ProviderDoctorChecks: ("providers", "Providers / Sources"),
        WeatherDoctorChecks: ("weather", "Weather / Alerts"),
        DisplayDoctorChecks: ("display", "Display Runtime"),
        BackupDoctorChecks: ("backup", "Backup / Export"),
    }

    def run_all_checks(self) -> DoctorResponse:
        groups: list[HealthCheckGroup] = []

        for checker_class in self.CHECKERS:
            group_id, group_title = self.GROUP_META[checker_class]
            try:
                checks = checker_class.run()
                if not isinstance(checks, list):
                    checks = [checks]
            except Exception as exc:
                checks = [
                    HealthCheck(
                        id="checker_error",
                        title="Check Error",
                        severity=HealthSeverity.ERROR,
                        summary=f"Checker failed: {exc}",
                    )
                ]

            group_status = self._compute_group_status(checks)
            groups.append(
                HealthCheckGroup(
                    id=group_id,
                    title=group_title,
                    status=group_status,
                    checks=list(checks),
                )
            )

        return DoctorResponse.from_groups(groups)

    @staticmethod
    def _compute_group_status(checks: list[HealthCheck]) -> HealthSeverity:
        if any(c.severity == HealthSeverity.ERROR for c in checks):
            return HealthSeverity.ERROR
        if any(c.severity == HealthSeverity.WARNING for c in checks):
            return HealthSeverity.WARNING
        if any(c.severity == HealthSeverity.INFO for c in checks):
            return HealthSeverity.INFO
        return HealthSeverity.OK
