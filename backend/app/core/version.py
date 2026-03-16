from __future__ import annotations

import re
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[2]
REPO_ROOT = BACKEND_DIR.parent
VERSION_FILE = REPO_ROOT / "VERSION"
_SEMVER_RE = re.compile(
    r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)"
    r"(?:-[0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*)?"
    r"(?:\+[0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*)?$"
)


def load_app_version() -> str:
    version = VERSION_FILE.read_text(encoding="utf-8").strip()
    if not version:
        raise RuntimeError(f"{VERSION_FILE} is empty.")
    if _SEMVER_RE.fullmatch(version) is None:
        raise RuntimeError(f"{VERSION_FILE} does not contain a valid semantic version: {version!r}")
    return version


APP_VERSION = load_app_version()
