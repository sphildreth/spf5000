#!/usr/bin/env bash
set -euo pipefail

PI_SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PI_REPO_ROOT="$(cd "${PI_SCRIPT_DIR}/.." && pwd)"

PI_DEFAULT_APP_ROOT="/opt/spf5000"
PI_DEFAULT_DATA_DIR="/var/lib/spf5000"
PI_DEFAULT_CACHE_DIR="/var/cache/spf5000"
PI_DEFAULT_CONFIG_PATH="${PI_DEFAULT_DATA_DIR}/spf5000.toml"
PI_DEFAULT_SERVICE_NAME="spf5000"
PI_DEFAULT_HOST="0.0.0.0"
PI_DEFAULT_PORT="8000"
PI_DEFAULT_KIOSK_DELAY_SECONDS="8"
PI_KIOSK_LABWC_BLOCK_START="# >>> SPF5000 managed kiosk >>>"
PI_KIOSK_LABWC_BLOCK_END="# <<< SPF5000 managed kiosk <<<"

log() {
  printf '[INFO] %s\n' "$*"
}

warn() {
  printf '[WARN] %s\n' "$*" >&2
}

fail() {
  printf '[ERROR] %s\n' "$*" >&2
  exit 1
}

require_command() {
  local command_name="$1"
  command -v "${command_name}" >/dev/null 2>&1 || fail "Required command not found: ${command_name}"
}

require_root() {
  [[ "${EUID}" -eq 0 ]] || fail "This script must run as root. Re-run it with sudo."
}

resolve_user_home() {
  local user_name="$1"
  local home_dir

  home_dir="$(getent passwd "${user_name}" | cut -d: -f6)"
  [[ -n "${home_dir}" ]] || fail "Unable to determine the home directory for user ${user_name}."
  printf '%s\n' "${home_dir}"
}

resolve_user_group() {
  local user_name="$1"
  id -gn "${user_name}"
}

run_as_user_shell() {
  local user_name="$1"
  local shell_command="$2"
  local home_dir

  home_dir="$(resolve_user_home "${user_name}")"

  if command -v runuser >/dev/null 2>&1; then
    runuser -u "${user_name}" -- env HOME="${home_dir}" USER="${user_name}" LOGNAME="${user_name}" bash -lc "${shell_command}"
    return
  fi

  su - "${user_name}" -c "${shell_command}"
}

render_template() {
  local template_path="$1"
  local output_path="$2"
  shift 2

  python3 - "${template_path}" "${output_path}" "$@" <<'PY'
from pathlib import Path
import sys

template_path = Path(sys.argv[1])
output_path = Path(sys.argv[2])
replacements: dict[str, str] = {}

for item in sys.argv[3:]:
    key, value = item.split("=", 1)
    replacements[key] = value

text = template_path.read_text(encoding="utf-8")
for key, value in replacements.items():
    text = text.replace(f"__{key}__", value)

output_path.parent.mkdir(parents=True, exist_ok=True)
output_path.write_text(text, encoding="utf-8")
PY
}

require_spf5000_checkout() {
  local app_root="$1"

  [[ -d "${app_root}" ]] || fail "Expected an SPF5000 checkout at ${app_root}, but the directory does not exist."
  [[ -f "${app_root}/backend/requirements.txt" ]] || fail "Missing ${app_root}/backend/requirements.txt. The installer does not clone the repository for you."
  [[ -f "${app_root}/backend/app/__main__.py" ]] || fail "Missing ${app_root}/backend/app/__main__.py. ${app_root} does not look like an SPF5000 checkout."
  [[ -f "${app_root}/frontend/package.json" ]] || fail "Missing ${app_root}/frontend/package.json. ${app_root} does not look like an SPF5000 checkout."
  [[ -f "${app_root}/deploy/systemd/spf5000.service.template" ]] || fail "Missing ${app_root}/deploy/systemd/spf5000.service.template."
  [[ -f "${app_root}/deploy/autostart/spf5000-kiosk.desktop.template" ]] || fail "Missing ${app_root}/deploy/autostart/spf5000-kiosk.desktop.template."
  [[ -f "${app_root}/deploy/autostart/spf5000-kiosk-launch.sh.template" ]] || fail "Missing ${app_root}/deploy/autostart/spf5000-kiosk-launch.sh.template."
}

infer_service_value() {
  local service_file="$1"
  local key_name="$2"

  [[ -f "${service_file}" ]] || return 1

  python3 - "${service_file}" "${key_name}" <<'PY'
from pathlib import Path
import sys

service_file = Path(sys.argv[1])
key_name = sys.argv[2]

for line in service_file.read_text(encoding="utf-8").splitlines():
    if line.startswith(f"{key_name}="):
        print(line.split("=", 1)[1].strip())
        raise SystemExit(0)

raise SystemExit(1)
PY
}

toml_get_value() {
  local config_path="$1"
  local dotted_key="$2"

  python3 - "${config_path}" "${dotted_key}" <<'PY'
from pathlib import Path
import sys
import tomllib

config_path = Path(sys.argv[1])
dotted_key = sys.argv[2]

if not config_path.exists():
    raise SystemExit(2)

with config_path.open("rb") as handle:
    data = tomllib.load(handle)

current = data
for part in dotted_key.split("."):
    if not isinstance(current, dict) or part not in current:
        raise SystemExit(3)
    current = current[part]

if isinstance(current, bool):
    print("true" if current else "false")
else:
    print(current)
PY
}

detect_chromium_binary() {
  if command -v chromium-browser >/dev/null 2>&1; then
    printf '%s\n' "chromium-browser"
    return 0
  fi

  if command -v chromium >/dev/null 2>&1; then
    printf '%s\n' "chromium"
    return 0
  fi

  return 1
}

apt_package_has_install_candidate() {
  local package_name="$1"
  local candidate=""

  candidate="$(apt-cache policy "${package_name}" 2>/dev/null | awk '/Candidate:/ {print $2; exit}')"
  [[ -n "${candidate}" && "${candidate}" != "(none)" ]]
}

detect_chromium_package() {
  if apt_package_has_install_candidate chromium-browser; then
    printf '%s\n' "chromium-browser"
    return 0
  fi

  if apt_package_has_install_candidate chromium; then
    printf '%s\n' "chromium"
    return 0
  fi

  return 1
}

kiosk_desktop_path() {
  local user_name="$1"
  local service_name="${2:-${PI_DEFAULT_SERVICE_NAME}}"

  printf '%s/.config/autostart/%s-kiosk.desktop\n' "$(resolve_user_home "${user_name}")" "${service_name}"
}

kiosk_launcher_path() {
  local user_name="$1"
  local service_name="${2:-${PI_DEFAULT_SERVICE_NAME}}"

  printf '%s/.config/autostart/%s-kiosk-launch.sh\n' "$(resolve_user_home "${user_name}")" "${service_name}"
}

kiosk_labwc_autostart_path() {
  local user_name="$1"

  printf '%s/.config/labwc/autostart\n' "$(resolve_user_home "${user_name}")"
}

upsert_managed_text_block() {
  local target_path="$1"
  local start_marker="$2"
  local end_marker="$3"
  local block_content="$4"

  python3 - "${target_path}" "${start_marker}" "${end_marker}" "${block_content}" <<'PY'
from pathlib import Path
import sys

target_path = Path(sys.argv[1])
start_marker = sys.argv[2]
end_marker = sys.argv[3]
block_content = sys.argv[4]

text = target_path.read_text(encoding="utf-8") if target_path.exists() else ""
lines = text.splitlines()
result: list[str] = []

i = 0
while i < len(lines):
    if lines[i] == start_marker:
        i += 1
        while i < len(lines) and lines[i] != end_marker:
            i += 1
        if i < len(lines) and lines[i] == end_marker:
            i += 1
        continue
    result.append(lines[i])
    i += 1

while result and result[-1] == "":
    result.pop()

if result:
    result.append("")

result.extend([start_marker, *block_content.splitlines(), end_marker])
target_path.parent.mkdir(parents=True, exist_ok=True)
target_path.write_text("\n".join(result) + "\n", encoding="utf-8")
PY
}

remove_managed_text_block() {
  local target_path="$1"
  local start_marker="$2"
  local end_marker="$3"

  python3 - "${target_path}" "${start_marker}" "${end_marker}" <<'PY'
from pathlib import Path
import sys

target_path = Path(sys.argv[1])
start_marker = sys.argv[2]
end_marker = sys.argv[3]

if not target_path.exists():
    raise SystemExit(0)

lines = target_path.read_text(encoding="utf-8").splitlines()
result: list[str] = []

i = 0
while i < len(lines):
    if lines[i] == start_marker:
        i += 1
        while i < len(lines) and lines[i] != end_marker:
            i += 1
        if i < len(lines) and lines[i] == end_marker:
            i += 1
        continue
    result.append(lines[i])
    i += 1

while result and result[-1] == "":
    result.pop()

if result:
    target_path.write_text("\n".join(result) + "\n", encoding="utf-8")
else:
    target_path.unlink(missing_ok=True)
PY
}

safe_remove_path() {
  local target_path="$1"

  [[ -n "${target_path}" ]] || fail "Refusing to remove an empty path."
  [[ "${target_path}" != "/" ]] || fail "Refusing to remove /."
  [[ "${target_path}" != "/var" ]] || fail "Refusing to remove /var."
  [[ "${target_path}" != "/var/lib" ]] || fail "Refusing to remove /var/lib."
  [[ "${target_path}" != "/var/cache" ]] || fail "Refusing to remove /var/cache."

  if [[ -e "${target_path}" ]]; then
    rm -rf "${target_path}"
  fi
}
