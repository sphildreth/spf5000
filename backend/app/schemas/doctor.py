from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class HealthSeverity(str, Enum):
    OK = "ok"
    WARNING = "warning"
    ERROR = "error"
    INFO = "info"


class HealthCheck(BaseModel):
    id: str
    title: str
    severity: HealthSeverity
    summary: str
    details: str | None = None
    remediation: str | None = None

    model_config = {"use_enum_values": True}


class HealthCheckGroup(BaseModel):
    id: str
    title: str
    status: HealthSeverity
    checks: list[HealthCheck] = Field(default_factory=list)

    model_config = {"use_enum_values": True}


class DoctorResponse(BaseModel):
    overall_status: HealthSeverity
    checked_at: str
    groups: list[HealthCheckGroup] = Field(default_factory=list)
    summary: str

    model_config = {"use_enum_values": True}

    @classmethod
    def from_groups(cls, groups: list[HealthCheckGroup]) -> "DoctorResponse":
        overall = cls._compute_overall_status(groups)
        summary = cls._compute_summary(groups, overall)
        return cls(
            overall_status=overall,
            checked_at=datetime.now(timezone.utc).isoformat(),
            groups=groups,
            summary=summary,
        )

    @staticmethod
    def _compute_overall_status(groups: list[HealthCheckGroup]) -> HealthSeverity:
        has_error = any(
            check.severity == HealthSeverity.ERROR
            for group in groups
            for check in group.checks
        )
        if has_error:
            return HealthSeverity.ERROR

        has_warning = any(
            check.severity == HealthSeverity.WARNING
            for group in groups
            for check in group.checks
        )
        if has_warning:
            return HealthSeverity.WARNING

        return HealthSeverity.OK

    @staticmethod
    def _compute_summary(
        groups: list[HealthCheckGroup], overall: HealthSeverity
    ) -> str:
        total_checks = sum(len(group.checks) for group in groups)
        errors = sum(
            1
            for group in groups
            for check in group.checks
            if check.severity == HealthSeverity.ERROR
        )
        warnings = sum(
            1
            for group in groups
            for check in group.checks
            if check.severity == HealthSeverity.WARNING
        )

        if overall == HealthSeverity.OK:
            return f"All {total_checks} checks passed."
        if overall == HealthSeverity.ERROR:
            return f"{errors} error(s), {warnings} warning(s) found."
        return f"{warnings} warning(s) found, {total_checks - errors - warnings} checks passed."
