from __future__ import annotations

import logging
from datetime import datetime, timezone

from PIL import Image

from app.core.config import settings
from app.db.connection import get_connection, is_null_connection

LOGGER = logging.getLogger(__name__)

DEFAULT_SOURCE_ID = "default-local-files"
DEFAULT_COLLECTION_ID = "default-collection"
GOOGLE_PHOTOS_SOURCE_ID = "google-photos-source"
GOOGLE_PHOTOS_COLLECTION_ID = "google-photos-collection"
DEFAULT_DISPLAY_PROFILE_ID = "default-display-profile"
DEFAULT_SETTINGS = {
    "frame_name": "SPF5000",
    "display_variant_width": str(settings.display_max_width),
    "display_variant_height": str(settings.display_max_height),
    "thumbnail_max_size": str(settings.thumbnail_max_size),
    "slideshow_interval_seconds": "30",
    "transition_mode": "slide",
    "transition_duration_ms": "700",
    "fit_mode": "contain",
    "shuffle_enabled": "1",
    "selected_collection_id": DEFAULT_COLLECTION_ID,
    "active_display_profile_id": DEFAULT_DISPLAY_PROFILE_ID,
    # Sleep schedule defaults — display is off by default; 22:00 → 08:00 is a sensible preset.
    "sleep_schedule_enabled": "0",
    "sleep_start_local_time": "22:00",
    "sleep_end_local_time": "08:00",
}

TABLE_STATEMENTS = {
    "settings": """
        create table settings (
            key text primary key,
            value text not null,
            updated_at text not null
        )
    """,
    "admin_users": """
        create table admin_users (
            id text primary key,
            username text not null unique,
            password_hash text not null,
            enabled integer not null default 1,
            created_at text not null,
            updated_at text not null,
            last_login_at text
        )
    """,
    "system_state": """
        create table system_state (
            key text primary key,
            value text not null,
            updated_at text not null
        )
    """,
    "sources": """
        create table sources (
            id text primary key,
            name text not null,
            provider_type text not null,
            import_path text not null,
            enabled integer not null default 1,
            created_at text not null,
            updated_at text not null,
            last_scan_at text,
            last_import_at text
        )
    """,
    "collections": """
        create table collections (
            id text primary key,
            name text not null,
            description text not null,
            source_id text,
            is_default integer not null default 0,
            is_active integer not null default 1,
            created_at text not null,
            updated_at text not null
        )
    """,
    "assets": """
        create table assets (
            id text primary key,
            source_id text not null,
            checksum_sha256 text not null unique,
            filename text not null,
            original_filename text not null,
            original_extension text not null,
            mime_type text not null,
            width integer not null,
            height integer not null,
            size_bytes integer not null,
            imported_from_path text not null,
            local_original_path text not null,
            metadata_json text not null default '{}',
            created_at text not null,
            updated_at text not null,
            imported_at text not null,
            is_active integer not null default 1
        )
    """,
    "asset_variants": """
        create table asset_variants (
            id text primary key,
            asset_id text not null,
            kind text not null,
            local_path text not null,
            mime_type text not null,
            width integer not null,
            height integer not null,
            size_bytes integer not null,
            created_at text not null,
            unique(asset_id, kind)
        )
    """,
    "collection_assets": """
        create table collection_assets (
            collection_id text not null,
            asset_id text not null,
            sort_order integer not null default 0,
            added_at text not null,
            primary key (collection_id, asset_id)
        )
    """,
    "import_jobs": """
        create table import_jobs (
            id text primary key,
            job_type text not null,
            status text not null,
            source_id text,
            collection_id text,
            import_path text not null,
            discovered_count integer not null default 0,
            imported_count integer not null default 0,
            duplicate_count integer not null default 0,
            skipped_count integer not null default 0,
            error_count integer not null default 0,
            sample_filenames text not null default '[]',
            message text not null default '',
            started_at text not null,
            completed_at text
        )
    """,
    "display_profiles": """
        create table display_profiles (
            id text primary key,
            name text not null,
            selected_collection_id text,
            slideshow_interval_seconds integer not null,
            transition_mode text not null,
            transition_duration_ms integer not null,
            fit_mode text not null,
            shuffle_enabled integer not null,
            idle_message text not null default '',
            refresh_interval_seconds integer not null default 60,
            is_default integer not null default 0,
            created_at text not null,
            updated_at text not null
        )
    """,
    "provider_auth_flows": """
        create table provider_auth_flows (
            id text primary key,
            provider_name text not null,
            status text not null,
            request_id text not null,
            device_display_name text not null,
            device_code text not null,
            user_code text not null,
            verification_uri text not null,
            verification_uri_complete text,
            interval_seconds integer not null,
            expires_at text not null,
            last_polled_at text,
            next_poll_at text,
            error_message text not null default '',
            created_at text not null,
            updated_at text not null,
            completed_at text
        )
    """,
    "provider_accounts": """
        create table provider_accounts (
            id text primary key,
            provider_name text not null unique,
            connection_state text not null,
            account_subject text,
            account_email text,
            account_display_name text,
            account_picture_url text,
            access_token text,
            refresh_token text,
            scope text not null default '',
            access_token_expires_at text,
            request_id text,
            device_id text,
            device_display_name text,
            settings_uri text,
            media_sources_set integer not null default 0,
            device_poll_interval_seconds integer not null default 30,
            device_created_at text,
            last_device_poll_at text,
            connected_at text,
            disconnected_at text,
            last_sync_requested_at text,
            last_completed_sync_at text,
            current_error text not null default '',
            created_at text not null,
            updated_at text not null
        )
    """,
    "provider_media_sources": """
        create table provider_media_sources (
            id text primary key,
            provider_name text not null,
            media_source_id text not null,
            display_name text not null,
            is_selected integer not null default 1,
            last_seen_at text not null,
            created_at text not null,
            updated_at text not null,
            unique(provider_name, media_source_id)
        )
    """,
    "provider_sync_runs": """
        create table provider_sync_runs (
            id text primary key,
            provider_name text not null,
            trigger text not null,
            status text not null,
            message text not null default '',
            error_message text not null default '',
            warning_messages_json text not null default '[]',
            discovered_count integer not null default 0,
            imported_count integer not null default 0,
            duplicate_count integer not null default 0,
            skipped_count integer not null default 0,
            error_count integer not null default 0,
            started_at text not null,
            completed_at text
        )
    """,
    "provider_assets": """
        create table provider_assets (
            id text primary key,
            provider_name text not null,
            remote_media_id text not null,
            local_asset_id text,
            mime_type text not null,
            width integer not null default 0,
            height integer not null default 0,
            create_time text,
            imported_from_path text not null,
            remote_base_url text not null default '',
            cached_original_path text,
            checksum_sha256 text,
            metadata_json text not null default '{}',
            first_synced_at text not null,
            last_synced_at text not null,
            last_seen_at text not null,
            is_active integer not null default 1,
            unique(provider_name, remote_media_id)
        )
    """,
    "provider_asset_media_sources": """
        create table provider_asset_media_sources (
            provider_asset_id text not null,
            media_source_id text not null,
            added_at text not null,
            primary key (provider_asset_id, media_source_id)
        )
    """,
}

INDEX_STATEMENTS = {
    "idx_assets_source_id": "create index idx_assets_source_id on assets (source_id)",
    "idx_assets_imported_at": "create index idx_assets_imported_at on assets (imported_at)",
    "idx_collection_assets_asset_id": "create index idx_collection_assets_asset_id on collection_assets (asset_id)",
    "idx_asset_variants_asset_kind": "create index idx_asset_variants_asset_kind on asset_variants (asset_id, kind)",
    "idx_import_jobs_source_id": "create index idx_import_jobs_source_id on import_jobs (source_id)",
    "idx_provider_auth_flows_provider_status": "create index idx_provider_auth_flows_provider_status on provider_auth_flows (provider_name, status)",
    "idx_provider_media_sources_provider": "create index idx_provider_media_sources_provider on provider_media_sources (provider_name)",
    "idx_provider_sync_runs_provider_started": "create index idx_provider_sync_runs_provider_started on provider_sync_runs (provider_name, started_at)",
    "idx_provider_assets_provider_media_id": "create index idx_provider_assets_provider_media_id on provider_assets (provider_name, remote_media_id)",
}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _existing_columns(conn, table_name: str) -> set[str]:
    columns = conn.get_table_columns(table_name)
    return {str(column["name"]) for column in columns}


def _ensure_column(conn, table_name: str, column_name: str, definition: str) -> None:
    if column_name in _existing_columns(conn, table_name):
        return
    conn.execute(f"alter table {table_name} add column {column_name} {definition}")


def initialize_storage() -> None:
    directories = [
        settings.data_dir,
        settings.cache_dir,
        settings.log_dir,
        settings.database_path.parent,
        settings.storage_dir,
        settings.originals_dir,
        settings.display_variants_dir,
        settings.thumbnails_dir,
        settings.staging_dir,
        settings.import_staging_dir,
        settings.sources_root_dir,
        settings.local_import_dir,
        settings.google_photos_source_dir,
        settings.google_photos_import_dir,
        settings.google_photos_download_staging_dir,
        settings.fallback_assets_dir,
    ]
    for directory in directories:
        directory.mkdir(parents=True, exist_ok=True)

    fallback_file = settings.fallback_assets_dir / "empty-display.jpg"
    if not fallback_file.exists():
        image = Image.new("RGB", (settings.display_max_width, settings.display_max_height), color=(0, 0, 0))
        image.save(fallback_file, format="JPEG", quality=settings.jpeg_quality)


def bootstrap_database() -> None:
    with get_connection() as conn:
        if is_null_connection(conn):
            LOGGER.warning("DecentDB unavailable; running with NullConnection fallback")
            return

        existing_tables = set(conn.list_tables())
        for table_name, statement in TABLE_STATEMENTS.items():
            if table_name not in existing_tables:
                conn.execute(statement)

        existing_indexes = {str(index["name"]) for index in conn.list_indexes()}
        for index_name, statement in INDEX_STATEMENTS.items():
            if index_name not in existing_indexes:
                conn.execute(statement)

        _ensure_column(
            conn,
            "display_profiles",
            "idle_message",
            "text not null default 'Add photos from the admin UI to begin playback.'",
        )
        _ensure_column(conn, "display_profiles", "refresh_interval_seconds", "integer not null default 60")
        _ensure_column(conn, "admin_users", "last_login_at", "text")
        _ensure_column(conn, "provider_auth_flows", "verification_uri_complete", "text")
        _ensure_column(conn, "provider_auth_flows", "last_polled_at", "text")
        _ensure_column(conn, "provider_auth_flows", "next_poll_at", "text")
        _ensure_column(conn, "provider_accounts", "last_sync_requested_at", "text")
        _ensure_column(conn, "provider_accounts", "last_completed_sync_at", "text")
        _ensure_column(conn, "provider_assets", "cached_original_path", "text")
        _ensure_column(conn, "provider_assets", "checksum_sha256", "text")

        now = utc_now()
        for key, value in DEFAULT_SETTINGS.items():
            cursor = conn.execute("select value from settings where key = ?", (key,))
            if cursor.fetchone() is None:
                conn.execute(
                    "insert into settings (key, value, updated_at) values (?, ?, ?)",
                    (key, value, now),
                )

        if conn.execute("select id from sources where id = ?", (DEFAULT_SOURCE_ID,)).fetchone() is None:
            conn.execute(
                """
                insert into sources (
                    id, name, provider_type, import_path, enabled, created_at, updated_at, last_scan_at, last_import_at
                ) values (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    DEFAULT_SOURCE_ID,
                    "Local Files",
                    "local_files",
                    str(settings.local_import_dir),
                    1,
                    now,
                    now,
                    None,
                    None,
                ),
            )

        if conn.execute("select id from collections where id = ?", (DEFAULT_COLLECTION_ID,)).fetchone() is None:
            conn.execute(
                """
                insert into collections (
                    id, name, description, source_id, is_default, is_active, created_at, updated_at
                ) values (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    DEFAULT_COLLECTION_ID,
                    "All Photos",
                    "Default collection for locally managed photos.",
                    DEFAULT_SOURCE_ID,
                    1,
                    1,
                    now,
                    now,
                ),
            )

        if conn.execute("select id from sources where id = ?", (GOOGLE_PHOTOS_SOURCE_ID,)).fetchone() is None:
            conn.execute(
                """
                insert into sources (
                    id, name, provider_type, import_path, enabled, created_at, updated_at, last_scan_at, last_import_at
                ) values (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    GOOGLE_PHOTOS_SOURCE_ID,
                    settings.google_photos_provider_display_name,
                    "google_photos",
                    str(settings.google_photos_import_dir),
                    1,
                    now,
                    now,
                    None,
                    None,
                ),
            )

        if conn.execute("select id from collections where id = ?", (GOOGLE_PHOTOS_COLLECTION_ID,)).fetchone() is None:
            conn.execute(
                """
                insert into collections (
                    id, name, description, source_id, is_default, is_active, created_at, updated_at
                ) values (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    GOOGLE_PHOTOS_COLLECTION_ID,
                    settings.google_photos_provider_display_name,
                    "Offline-cached media synced from Google Photos Ambient selections.",
                    GOOGLE_PHOTOS_SOURCE_ID,
                    0,
                    1,
                    now,
                    now,
                ),
            )

        if conn.execute("select id from display_profiles where id = ?", (DEFAULT_DISPLAY_PROFILE_ID,)).fetchone() is None:
            conn.execute(
                """
                insert into display_profiles (
                    id, name, selected_collection_id, slideshow_interval_seconds, transition_mode,
                    transition_duration_ms, fit_mode, shuffle_enabled, idle_message, refresh_interval_seconds,
                    is_default, created_at, updated_at
                ) values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    DEFAULT_DISPLAY_PROFILE_ID,
                    "Default Display",
                    DEFAULT_COLLECTION_ID,
                    int(DEFAULT_SETTINGS["slideshow_interval_seconds"]),
                    DEFAULT_SETTINGS["transition_mode"],
                    int(DEFAULT_SETTINGS["transition_duration_ms"]),
                    DEFAULT_SETTINGS["fit_mode"],
                    int(DEFAULT_SETTINGS["shuffle_enabled"]),
                    "Add photos from the admin UI to begin playback.",
                    60,
                    1,
                    now,
                    now,
                ),
            )


def initialize_runtime() -> None:
    initialize_storage()
    bootstrap_database()
