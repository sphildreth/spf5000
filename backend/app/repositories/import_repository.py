from __future__ import annotations

from app.db.connection import get_connection, is_null_connection
from app.models.import_job import ImportJob
from app.repositories.base import json_dumps, json_loads, row_to_dict, utc_now


class ImportRepository:
    def create_job(self, job: ImportJob) -> ImportJob:
        with get_connection() as conn:
            if is_null_connection(conn):
                return job
            conn.execute(
                """
                insert into import_jobs (
                    id, job_type, status, source_id, collection_id, import_path, discovered_count,
                    imported_count, duplicate_count, skipped_count, error_count, sample_filenames,
                    message, started_at, completed_at
                ) values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    job.id,
                    job.job_type,
                    job.status,
                    job.source_id,
                    job.collection_id,
                    job.import_path,
                    job.discovered_count,
                    job.imported_count,
                    job.duplicate_count,
                    job.skipped_count,
                    job.error_count,
                    json_dumps(job.sample_filenames),
                    job.message,
                    job.started_at,
                    job.completed_at,
                ),
            )
        return self.get_job(job.id) or job

    def update_job(self, job: ImportJob) -> ImportJob:
        with get_connection() as conn:
            if is_null_connection(conn):
                return job
            completed_at = job.completed_at or utc_now()
            conn.execute(
                """
                update import_jobs
                set status = ?, discovered_count = ?, imported_count = ?, duplicate_count = ?, skipped_count = ?,
                    error_count = ?, sample_filenames = ?, message = ?, completed_at = ?
                where id = ?
                """,
                (
                    job.status,
                    job.discovered_count,
                    job.imported_count,
                    job.duplicate_count,
                    job.skipped_count,
                    job.error_count,
                    json_dumps(job.sample_filenames),
                    job.message,
                    completed_at,
                    job.id,
                ),
            )
        job.completed_at = completed_at
        return self.get_job(job.id) or job

    def get_job(self, job_id: str) -> ImportJob | None:
        with get_connection() as conn:
            if is_null_connection(conn):
                return None
            cursor = conn.execute("select * from import_jobs where id = ?", (job_id,))
            row = row_to_dict(cursor, cursor.fetchone())
            return None if row is None else self._to_model(row)

    def get_latest_job(self) -> ImportJob | None:
        with get_connection() as conn:
            if is_null_connection(conn):
                return None
            cursor = conn.execute("select * from import_jobs order by started_at desc, id desc limit 1")
            row = row_to_dict(cursor, cursor.fetchone())
            return None if row is None else self._to_model(row)

    def count_jobs(self) -> int:
        with get_connection() as conn:
            if is_null_connection(conn):
                return 0
            cursor = conn.execute("select count(*) from import_jobs")
            return int(cursor.fetchone()[0])

    @staticmethod
    def _to_model(row: dict[str, object]) -> ImportJob:
        return ImportJob(
            id=str(row["id"]),
            job_type=str(row["job_type"]),
            status=str(row["status"]),
            source_id=None if row["source_id"] is None else str(row["source_id"]),
            collection_id=None if row["collection_id"] is None else str(row["collection_id"]),
            import_path=str(row["import_path"]),
            discovered_count=int(row["discovered_count"]),
            imported_count=int(row["imported_count"]),
            duplicate_count=int(row["duplicate_count"]),
            skipped_count=int(row["skipped_count"]),
            error_count=int(row["error_count"]),
            sample_filenames=json_loads(str(row["sample_filenames"]), []),
            message=str(row["message"]),
            started_at=str(row["started_at"]),
            completed_at=None if row["completed_at"] is None else str(row["completed_at"]),
        )
