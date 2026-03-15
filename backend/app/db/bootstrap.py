from __future__ import annotations

import logging
from datetime import datetime, timezone

from PIL import Image

from app.core.config import settings
from app.db.connection import get_connection, is_null_connection

LOGGER = logging.getLogger(__name__)

DEFAULT_SOURCE_ID = "default-local-files"
DEFAULT_COLLECTION_ID = "default-collection"
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
}

SCHEMA_STATEMENTS = [
    """
    create table if not exists settings (
        key text primary key,
        value text not null,
        updated_at text not null
    )
    """,
    """
    create table if not exists sources (
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
    """
    create table if not exists collections (
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
    """
    create table if not exists assets (
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
    """
    create table if not exists asset_variants (
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
    """
    create table if not exists collection_assets (
        collection_id text not null,
        asset_id text not null,
        sort_order integer not null default 0,
        added_at text not null,
        primary key (collection_id, asset_id)
    )
    """,
    """
    create table if not exists import_jobs (
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
    """
    create table if not exists display_profiles (
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
    "create index if not exists idx_assets_source_id on assets (source_id)",
    "create index if not exists idx_assets_imported_at on assets (imported_at)",
    "create index if not exists idx_collection_assets_asset_id on collection_assets (asset_id)",
    "create index if not exists idx_asset_variants_asset_kind on asset_variants (asset_id, kind)",
    "create index if not exists idx_import_jobs_source_id on import_jobs (source_id)",
]


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
        settings.storage_dir,
        settings.originals_dir,
        settings.display_variants_dir,
        settings.thumbnails_dir,
        settings.staging_dir,
        settings.import_staging_dir,
        settings.sources_root_dir,
        settings.local_import_dir,
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

        for statement in SCHEMA_STATEMENTS:
            conn.execute(statement)

        _ensure_column(
            conn,
            "display_profiles",
            "idle_message",
            "text not null default 'Add photos from the admin UI to begin playback.'",
        )
        _ensure_column(conn, "display_profiles", "refresh_interval_seconds", "integer not null default 60")

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
