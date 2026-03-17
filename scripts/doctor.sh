#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
# shellcheck source=./pi-common.sh
source "${SCRIPT_DIR}/pi-common.sh"

SERVICE_NAME="${PI_DEFAULT_SERVICE_NAME}"
CONFIG_PATH="${PI_DEFAULT_CONFIG_PATH}"
RUNTIME_USER=""

SERVICE_FILE=""
DATA_DIR="${PI_DEFAULT_DATA_DIR}"
CACHE_DIR="${PI_DEFAULT_CACHE_DIR}"
LOG_DIR="${PI_DEFAULT_CACHE_DIR}/logs"
DATABASE_PATH="${PI_DEFAULT_DATA_DIR}/spf5000.ddb"
HOST="${PI_DEFAULT_HOST}"
PORT="${PI_DEFAULT_PORT}"
AUTOSTART_FILE=""
AUTOSTART_LAUNCHER_FILE=""
AUTOSTART_LABWC_FILE=""
KIOSK_LOG_FILE=""

PASS_COUNT=0
WARN_COUNT=0
FAIL_COUNT=0

usage() {
  cat <<EOF
Usage: ./scripts/doctor.sh [options]

Check the readiness of the Pi appliance setup and print a pass/warn/fail report.

Options:
  --user <username>       Runtime user to use for autostart and writeability checks
  --config-path <path>    Runtime config path to inspect (default: ${PI_DEFAULT_CONFIG_PATH})
  --service-name <name>   Systemd service name to inspect (default: ${PI_DEFAULT_SERVICE_NAME})
  --help                  Show this help text
EOF
}

pass_check() {
  PASS_COUNT=$((PASS_COUNT + 1))
  printf '[PASS] %s\n' "$*"
}

warn_check() {
  WARN_COUNT=$((WARN_COUNT + 1))
  printf '[WARN] %s\n' "$*"
}

fail_check() {
  FAIL_COUNT=$((FAIL_COUNT + 1))
  printf '[FAIL] %s\n' "$*"
}

parse_args() {
  while [[ $# -gt 0 ]]; do
    case "$1" in
      --user)
        RUNTIME_USER="$2"
        shift 2
        ;;
      --config-path)
        CONFIG_PATH="$2"
        shift 2
        ;;
      --service-name)
        SERVICE_NAME="$2"
        shift 2
        ;;
      --help|-h)
        usage
        exit 0
        ;;
      *)
        fail "Unknown option: $1"
        ;;
    esac
  done
}

load_runtime_config() {
  if [[ ! -f "${CONFIG_PATH}" ]]; then
    return
  fi

  DATA_DIR="$(toml_get_value "${CONFIG_PATH}" "paths.data_dir" 2>/dev/null || printf '%s' "${DATA_DIR}")"
  CACHE_DIR="$(toml_get_value "${CONFIG_PATH}" "paths.cache_dir" 2>/dev/null || printf '%s' "${CACHE_DIR}")"
  LOG_DIR="$(toml_get_value "${CONFIG_PATH}" "paths.log_dir" 2>/dev/null || printf '%s' "${LOG_DIR}")"
  DATABASE_PATH="$(toml_get_value "${CONFIG_PATH}" "paths.database_path" 2>/dev/null || printf '%s' "${DATABASE_PATH}")"
  HOST="$(toml_get_value "${CONFIG_PATH}" "server.host" 2>/dev/null || printf '%s' "${HOST}")"
  PORT="$(toml_get_value "${CONFIG_PATH}" "server.port" 2>/dev/null || printf '%s' "${PORT}")"
}

preflight() {
  SERVICE_FILE="/etc/systemd/system/${SERVICE_NAME}.service"

  if [[ -z "${RUNTIME_USER}" ]]; then
    RUNTIME_USER="$(infer_service_value "${SERVICE_FILE}" "User" || true)"
  fi

  if [[ -n "${RUNTIME_USER}" ]]; then
    AUTOSTART_FILE="$(kiosk_desktop_path "${RUNTIME_USER}" "${SERVICE_NAME}")"
    AUTOSTART_LAUNCHER_FILE="$(kiosk_launcher_path "${RUNTIME_USER}" "${SERVICE_NAME}")"
    AUTOSTART_LABWC_FILE="$(kiosk_labwc_autostart_path "${RUNTIME_USER}")"
  fi

  load_runtime_config
  KIOSK_LOG_FILE="${LOG_DIR}/${SERVICE_NAME}-kiosk-launcher.log"
}

health_host() {
  if [[ "${HOST}" == "0.0.0.0" ]]; then
    printf '%s\n' "127.0.0.1"
    return
  fi

  printf '%s\n' "${HOST}"
}

select_runtime_session_id() {
  local user_name="$1"

  python3 - "${user_name}" <<'PY'
import subprocess
import sys

user_name = sys.argv[1]

try:
    sessions_output = subprocess.check_output(
        ["loginctl", "list-sessions", "--no-legend"],
        text=True,
        stderr=subprocess.DEVNULL,
    )
except Exception:
    raise SystemExit(1)

best_session_id = None
best_score = None

for line in sessions_output.splitlines():
    parts = line.split()
    if len(parts) < 3 or parts[2] != user_name:
        continue

    session_id = parts[0]
    try:
        details_output = subprocess.check_output(
            [
                "loginctl",
                "show-session",
                session_id,
                "-p",
                "Type",
                "-p",
                "Desktop",
                "-p",
                "State",
                "-p",
                "Active",
                "-p",
                "Remote",
                "-p",
                "Class",
                "-p",
                "Seat",
                "--value",
            ],
            text=True,
            stderr=subprocess.DEVNULL,
        )
        detail_values = [value.strip() for value in details_output.splitlines()]
        while len(detail_values) < 7:
            detail_values.append("")
        session_type, desktop, state, active, remote, session_class, seat = detail_values[:7]
    except Exception:
        session_type = ""
        desktop = ""
        state = ""
        active = ""
        remote = ""
        session_class = ""
        seat = ""

    score = 0
    if session_type in {"wayland", "x11"}:
        score += 100
    if active == "yes":
        score += 20
    if state == "active":
        score += 10
    if remote == "no":
        score += 5
    if seat:
        score += 3
    if desktop:
        score += 2
    if session_class == "user":
        score += 1

    if best_score is None or score > best_score:
        best_score = score
        best_session_id = session_id

if best_session_id:
    print(best_session_id)
    raise SystemExit(0)

raise SystemExit(1)
PY
}

check_environment() {
  printf '\n== Environment ==\n'

  if [[ "$(uname -s)" == "Linux" ]]; then
    pass_check "Running on Linux."
  else
    fail_check "Not running on Linux."
  fi

  if [[ -r /proc/device-tree/model ]]; then
    local model
    model="$(tr -d '\0' </proc/device-tree/model)"
    if [[ "${model}" == *"Raspberry Pi"* ]]; then
      pass_check "Detected Raspberry Pi hardware: ${model}."
    else
      warn_check "Detected non-Pi hardware model: ${model}."
    fi
  else
    warn_check "Could not read /proc/device-tree/model to confirm Raspberry Pi hardware."
  fi

  if command -v systemctl >/dev/null 2>&1; then
    pass_check "systemctl is available."
  else
    fail_check "systemctl is not available."
  fi

  if command -v curl >/dev/null 2>&1; then
    pass_check "curl is available."
  else
    fail_check "curl is not available."
  fi
}

check_service() {
  printf '\n== Backend service ==\n'

  if [[ -f "${SERVICE_FILE}" ]]; then
    pass_check "Service file exists at ${SERVICE_FILE}."
  else
    fail_check "Service file is missing: ${SERVICE_FILE}."
  fi

  if command -v systemctl >/dev/null 2>&1; then
    if systemctl is-enabled --quiet "${SERVICE_NAME}.service" 2>/dev/null; then
      pass_check "${SERVICE_NAME}.service is enabled."
    else
      fail_check "${SERVICE_NAME}.service is not enabled."
    fi

    if systemctl is-active --quiet "${SERVICE_NAME}.service" 2>/dev/null; then
      pass_check "${SERVICE_NAME}.service is active."
    else
      fail_check "${SERVICE_NAME}.service is not active."
    fi

    if [[ -f "${SERVICE_FILE}" && -z "${RUNTIME_USER}" ]]; then
      warn_check "Could not infer the service User= value from ${SERVICE_FILE}."
    elif [[ -n "${RUNTIME_USER}" ]]; then
      pass_check "Service runtime user is ${RUNTIME_USER}."
    fi
  fi
}

check_config_and_paths() {
  printf '\n== Runtime config and storage ==\n'

  if [[ -f "${CONFIG_PATH}" ]]; then
    pass_check "Config file exists at ${CONFIG_PATH}."
  else
    fail_check "Config file is missing: ${CONFIG_PATH}."
  fi

  if [[ -d "${DATA_DIR}" ]]; then
    pass_check "Data directory exists: ${DATA_DIR}."
  else
    fail_check "Data directory is missing: ${DATA_DIR}."
  fi

  if [[ -d "${CACHE_DIR}" ]]; then
    pass_check "Cache directory exists: ${CACHE_DIR}."
  else
    fail_check "Cache directory is missing: ${CACHE_DIR}."
  fi

  if [[ -d "${LOG_DIR}" ]]; then
    pass_check "Log directory exists: ${LOG_DIR}."
  else
    warn_check "Log directory is missing: ${LOG_DIR}."
  fi

  if [[ -f "${DATABASE_PATH}" ]]; then
    pass_check "Database file exists: ${DATABASE_PATH}."
  else
    warn_check "Database file is missing: ${DATABASE_PATH}. A brand-new install may not have created it yet."
  fi

  check_user_writeability "${DATA_DIR}" "data directory"
  check_user_writeability "${CACHE_DIR}" "cache directory"
  check_user_writeability "$(dirname "${CONFIG_PATH}")" "config directory"

  if [[ "${HOST}" == "127.0.0.1" || "${HOST}" == "localhost" ]]; then
    warn_check "Backend host is ${HOST}; the admin UI will not be reachable from another device on the LAN."
  else
    pass_check "Backend bind host ${HOST} supports LAN access."
  fi
}

check_user_writeability() {
  local target_path="$1"
  local label="$2"

  if [[ ! -e "${target_path}" ]]; then
    return
  fi

  if [[ -z "${RUNTIME_USER}" ]]; then
    warn_check "Runtime user is unknown; could not verify write access for the ${label}."
    return
  fi

  if [[ "$(id -un)" == "${RUNTIME_USER}" ]]; then
    if [[ -w "${target_path}" ]]; then
      pass_check "Runtime user ${RUNTIME_USER} can write the ${label} (${target_path})."
    else
      fail_check "Runtime user ${RUNTIME_USER} cannot write the ${label} (${target_path})."
    fi
    return
  fi

  if [[ "${EUID}" -eq 0 ]]; then
    if run_as_user_shell "${RUNTIME_USER}" "[[ -w '${target_path}' ]]"; then
      pass_check "Runtime user ${RUNTIME_USER} can write the ${label} (${target_path})."
    else
      fail_check "Runtime user ${RUNTIME_USER} cannot write the ${label} (${target_path})."
    fi
    return
  fi

  if [[ "$(stat -c '%U' "${target_path}" 2>/dev/null || true)" == "${RUNTIME_USER}" ]]; then
    warn_check "The ${label} is owned by ${RUNTIME_USER}, but write access could not be verified without root."
  else
    fail_check "The ${label} is not owned by ${RUNTIME_USER}, and write access could not be verified."
  fi
}

check_http_endpoints() {
  local local_host=""
  local health_url=""
  local session_url=""
  local display_url=""
  local health_json=""
  local bootstrapped_state=""
  local bootstrapped_value=""
  local display_headers_file=""
  local display_body_file=""
  local display_status=""
  local display_content_type=""

  printf '\n== HTTP health ==\n'

  if ! command -v curl >/dev/null 2>&1; then
    return
  fi

  local_host="$(health_host)"
  health_url="http://${local_host}:${PORT}/api/health"
  session_url="http://${local_host}:${PORT}/api/auth/session"
  display_url="http://${local_host}:${PORT}/display"

  health_json="$(curl --silent --show-error --max-time 5 "${health_url}" 2>/dev/null || true)"
  if [[ -n "${health_json}" ]]; then
    if python3 - "${health_json}" <<'PY' >/dev/null 2>&1
import json
import sys

payload = json.loads(sys.argv[1])
raise SystemExit(0 if payload.get("ok") is True else 1)
PY
    then
      pass_check "Health endpoint responded successfully at ${health_url}."
    else
      fail_check "Health endpoint responded, but did not report ok=true."
    fi
  else
    fail_check "Health endpoint did not respond at ${health_url}."
  fi

  bootstrapped_state="$(curl --silent --show-error --max-time 5 "${session_url}" 2>/dev/null || true)"
  if [[ -n "${bootstrapped_state}" ]]; then
    bootstrapped_value="$(python3 - "${bootstrapped_state}" <<'PY'
import json
import sys

payload = json.loads(sys.argv[1])
bootstrapped = payload.get("bootstrapped")
if bootstrapped is True:
    print("true")
    raise SystemExit(0)
if bootstrapped is False:
    print("false")
    raise SystemExit(0)
raise SystemExit(1)
PY
)" || true

    if [[ "${bootstrapped_value}" == "true" ]]; then
        pass_check "Auth/session endpoint reports the device is bootstrapped."
    elif [[ "${bootstrapped_value}" == "false" ]]; then
        warn_check "Auth/session endpoint reports the device is not bootstrapped yet."
    else
      warn_check "Could not parse the auth/session response from ${session_url}."
    fi
  else
    warn_check "Auth/session endpoint did not respond at ${session_url}."
  fi

  display_headers_file="$(mktemp)"
  display_body_file="$(mktemp)"
  trap 'rm -f "${display_headers_file}" "${display_body_file}"' RETURN

  if curl --silent --show-error --location --max-time 5 --dump-header "${display_headers_file}" --output "${display_body_file}" "${display_url}" >/dev/null 2>&1; then
    display_status="$(awk 'toupper($1) ~ /^HTTP\// {code=$2} END {print code}' "${display_headers_file}")"
    display_content_type="$(awk 'BEGIN {IGNORECASE=1} /^content-type:/ {sub(/\r$/, "", $0); sub(/^[^:]*:[[:space:]]*/, "", $0); value=$0} END {print value}' "${display_headers_file}")"

    if [[ "${display_status}" == "200" ]] && [[ "${display_content_type}" == text/html* ]]; then
      if grep --quiet '"detail"[[:space:]]*:[[:space:]]*"Not Found"' "${display_body_file}"; then
        fail_check "Display route ${display_url} returned an error payload instead of the frontend shell."
      elif grep --quiet --ignore-case '<html' "${display_body_file}" || grep --quiet 'id="root"' "${display_body_file}"; then
        pass_check "Display route served the frontend shell successfully at ${display_url}."
      else
        warn_check "Display route responded with HTML at ${display_url}, but the body did not look like the built frontend shell."
      fi
    else
      fail_check "Display route did not serve the frontend shell at ${display_url} (status=${display_status:-unknown}, content-type=${display_content_type:-unknown})."
    fi
  else
    fail_check "Display route did not respond at ${display_url}."
  fi

  rm -f "${display_headers_file}" "${display_body_file}"
  trap - RETURN
}

check_display_runtime_state() {
  local local_host=""
  local playlist_url=""
  local playlist_json=""
  local playlist_info=()
  local item_count="0"
  local collection_label=""
  local first_item_url=""
  local first_asset_url=""
  local sleep_state=""
  local sleep_start=""
  local sleep_end=""
  local sleep_timezone=""
  local sleep_error=""
  local playlist_body_file=""
  local playlist_info_output=""
  local asset_headers_file=""
  local asset_body_file=""
  local asset_status=""
  local asset_content_type=""
  local asset_size=""

  printf '\n== Display state ==\n'

  if ! command -v curl >/dev/null 2>&1; then
    return
  fi

  local_host="$(health_host)"
  playlist_url="http://${local_host}:${PORT}/api/display/playlist"

  playlist_json="$(curl --silent --show-error --max-time 5 "${playlist_url}" 2>/dev/null || true)"
  if [[ -z "${playlist_json}" ]]; then
    fail_check "Display playlist endpoint did not respond at ${playlist_url}."
    return
  fi

  playlist_body_file="$(mktemp)"
  trap 'rm -f "${playlist_body_file}"' RETURN
  printf '%s' "${playlist_json}" > "${playlist_body_file}"

  if ! playlist_info_output="$(python3 - "${playlist_body_file}" <<'PY'
import json
import sys
from datetime import datetime
from zoneinfo import ZoneInfo

with open(sys.argv[1], "r", encoding="utf-8") as handle:
    payload = json.load(handle)
items = payload.get("items")
if not isinstance(items, list):
    items = []

collection_label = payload.get("collection_name") or payload.get("collection_id") or ""
first_item_url = ""
if items and isinstance(items[0], dict):
    first_item_url = str(items[0].get("display_url") or "")

sleep = payload.get("sleep_schedule")
sleep_state = "disabled"
sleep_start = ""
sleep_end = ""
timezone_label = "device-local timezone"
sleep_error = ""

if isinstance(sleep, dict):
    sleep_start = str(sleep.get("sleep_start_local_time") or "")
    sleep_end = str(sleep.get("sleep_end_local_time") or "")
    configured_timezone = str(sleep.get("display_timezone") or "")
    if configured_timezone:
        timezone_label = configured_timezone

    if bool(sleep.get("sleep_schedule_enabled")):
        try:
            if configured_timezone:
                now = datetime.now(ZoneInfo(configured_timezone))
            else:
                now = datetime.now().astimezone()
                timezone_label = getattr(now.tzinfo, "key", None) or now.tzname() or timezone_label

            start_hour, start_minute = [int(value) for value in sleep_start.split(":", 1)]
            end_hour, end_minute = [int(value) for value in sleep_end.split(":", 1)]
            start_total = start_hour * 60 + start_minute
            end_total = end_hour * 60 + end_minute
            current_total = now.hour * 60 + now.minute

            if start_total == end_total:
                sleep_state = "invalid"
            elif start_total < end_total:
                sleep_state = "active" if start_total <= current_total < end_total else "inactive"
            else:
                sleep_state = "active" if current_total >= start_total or current_total < end_total else "inactive"
        except Exception as exc:
            sleep_state = "unknown"
            sleep_error = str(exc)

print(len(items))
print(collection_label)
print(first_item_url)
print(sleep_state)
print(sleep_start)
print(sleep_end)
print(timezone_label)
print(sleep_error)
PY
  )"; then
    rm -f "${playlist_body_file}"
    trap - RETURN
    fail_check "Display playlist endpoint ${playlist_url} returned invalid JSON."
    return
  fi

  mapfile -t playlist_info <<< "${playlist_info_output}"

  rm -f "${playlist_body_file}"
  trap - RETURN

  item_count="${playlist_info[0]:-0}"
  collection_label="${playlist_info[1]:-}"
  first_item_url="${playlist_info[2]:-}"
  sleep_state="${playlist_info[3]:-disabled}"
  sleep_start="${playlist_info[4]:-}"
  sleep_end="${playlist_info[5]:-}"
  sleep_timezone="${playlist_info[6]:-device-local timezone}"
  sleep_error="${playlist_info[7]:-}"

  if [[ "${item_count}" =~ ^[0-9]+$ ]] && (( item_count > 0 )); then
    if [[ -n "${collection_label}" ]]; then
      pass_check "Display playlist endpoint returned ${item_count} item(s) from ${collection_label}."
    else
      pass_check "Display playlist endpoint returned ${item_count} item(s)."
    fi
  else
    warn_check "Display playlist endpoint returned no items; /display will stay idle until photos are imported."
  fi

  case "${sleep_state}" in
    disabled)
      pass_check "Display sleep schedule is disabled."
      ;;
    inactive)
      pass_check "Display sleep schedule is enabled but inactive right now (${sleep_start} -> ${sleep_end}, ${sleep_timezone})."
      ;;
    active)
      warn_check "Display sleep schedule is active right now (${sleep_start} -> ${sleep_end}, ${sleep_timezone}); /display is expected to render a black sleep screen."
      ;;
    invalid)
      warn_check "Display sleep schedule is enabled but invalid (${sleep_start} -> ${sleep_end}); identical start and end times should be corrected in the admin UI."
      ;;
    unknown)
      warn_check "Could not evaluate the display sleep schedule (${sleep_start} -> ${sleep_end}, ${sleep_timezone}): ${sleep_error:-unknown error}."
      ;;
    *)
      warn_check "Display sleep schedule returned an unrecognized state: ${sleep_state}."
      ;;
  esac

  if ! [[ "${item_count}" =~ ^[0-9]+$ ]] || (( item_count == 0 )); then
    return
  fi

  if [[ -z "${first_item_url}" ]]; then
    warn_check "Display playlist has items, but the first item did not include a display asset URL."
    return
  fi

  if [[ "${first_item_url}" == http://* || "${first_item_url}" == https://* ]]; then
    first_asset_url="${first_item_url}"
  else
    first_asset_url="http://${local_host}:${PORT}${first_item_url}"
  fi

  asset_headers_file="$(mktemp)"
  asset_body_file="$(mktemp)"
  trap 'rm -f "${asset_headers_file}" "${asset_body_file}"' RETURN

  if curl --silent --show-error --location --max-time 10 --dump-header "${asset_headers_file}" --output "${asset_body_file}" "${first_asset_url}" >/dev/null 2>&1; then
    asset_status="$(awk 'toupper($1) ~ /^HTTP\// {code=$2} END {print code}' "${asset_headers_file}")"
    asset_content_type="$(awk 'BEGIN {IGNORECASE=1} /^content-type:/ {sub(/\r$/, "", $0); sub(/^[^:]*:[[:space:]]*/, "", $0); value=$0} END {print value}' "${asset_headers_file}")"
    asset_size="$(wc -c < "${asset_body_file}" | tr -d '[:space:]')"

    if [[ "${asset_status}" == "200" ]] && [[ "${asset_content_type}" == image/* ]] && [[ "${asset_size}" =~ ^[0-9]+$ ]] && (( asset_size > 0 )); then
      pass_check "First display asset responded successfully at ${first_asset_url}."
    else
      fail_check "First display asset did not serve a valid image at ${first_asset_url} (status=${asset_status:-unknown}, content-type=${asset_content_type:-unknown}, bytes=${asset_size:-0})."
    fi
  else
    fail_check "First display asset did not respond at ${first_asset_url}."
  fi

  rm -f "${asset_headers_file}" "${asset_body_file}"
  trap - RETURN
}

check_browser_runtime() {
  local chromium_binary=""
  local default_target=""
  local throttled=""
  local lan_ip=""
  local autostart_exec_line=""
  local launcher_body=""
  local autostart_has_unclutter="false"
  local autostart_has_wayland_flag="false"
  local session_id=""
  local session_type=""
  local session_desktop=""
  local session_state=""
  local session_active=""
  local session_remote=""
  local labwc_autostart_body=""
  local expected_display_url=""
  local chromium_process=""
  local boot_epoch=""
  local log_mtime=""

  printf '\n== Browser kiosk runtime ==\n'

  chromium_binary="$(detect_chromium_binary || true)"
  if [[ -n "${chromium_binary}" ]]; then
    pass_check "Chromium binary is available as ${chromium_binary}."
  else
    fail_check "Chromium binary was not found on PATH."
  fi

  if [[ -n "${AUTOSTART_FILE}" ]]; then
    if [[ -f "${AUTOSTART_FILE}" ]]; then
      pass_check "Chromium autostart entry exists at ${AUTOSTART_FILE}."

      if command -v desktop-file-validate >/dev/null 2>&1; then
        if desktop-file-validate "${AUTOSTART_FILE}" >/dev/null 2>&1; then
          pass_check "Chromium autostart entry is a valid desktop file."
        else
          fail_check "Chromium autostart entry is not a valid desktop file: ${AUTOSTART_FILE}."
        fi
      fi

      autostart_exec_line="$(grep '^Exec=' "${AUTOSTART_FILE}" 2>/dev/null || true)"

      if [[ -n "${AUTOSTART_LAUNCHER_FILE}" && -f "${AUTOSTART_LAUNCHER_FILE}" ]]; then
        pass_check "Chromium autostart launcher exists at ${AUTOSTART_LAUNCHER_FILE}."
        launcher_body="$(cat "${AUTOSTART_LAUNCHER_FILE}" 2>/dev/null || true)"
      elif [[ -n "${AUTOSTART_LAUNCHER_FILE}" ]]; then
        fail_check "Chromium autostart launcher is missing: ${AUTOSTART_LAUNCHER_FILE}."
      fi

      if [[ -n "${AUTOSTART_LABWC_FILE}" && -f "${AUTOSTART_LABWC_FILE}" ]]; then
        labwc_autostart_body="$(cat "${AUTOSTART_LABWC_FILE}" 2>/dev/null || true)"
      fi

      if [[ "${autostart_exec_line}" == *"kiosk-launch.sh"* ]]; then
        pass_check "Chromium autostart entry delegates to the managed launcher script."
      else
        warn_check "Chromium autostart entry does not appear to call the managed launcher script."
      fi

      if [[ "${launcher_body}" == *"/usr/bin/unclutter"* ]]; then
        autostart_has_unclutter="true"
      fi

      if [[ "${launcher_body}" == *"--ozone-platform-hint=auto"* ]] || [[ "${launcher_body}" == *"--ozone-platform=wayland"* ]]; then
        autostart_has_wayland_flag="true"
      fi

      if [[ "${launcher_body}" == *"--password-store=basic"* ]]; then
        pass_check "Chromium autostart entry avoids desktop keyring prompts with --password-store=basic."
      else
        warn_check "Chromium autostart entry does not set --password-store=basic; Chromium may prompt for a new keyring password."
      fi
    else
      fail_check "Chromium autostart entry is missing: ${AUTOSTART_FILE}."
    fi
  else
    warn_check "Runtime user is unknown, so the Chromium autostart location could not be checked."
  fi

  if command -v systemctl >/dev/null 2>&1; then
    default_target="$(systemctl get-default 2>/dev/null || true)"
    if [[ "${default_target}" == "graphical.target" ]]; then
      pass_check "Default systemd target is graphical.target."
    elif [[ -n "${default_target}" ]]; then
      warn_check "Default systemd target is ${default_target}; the Pi appliance expects a graphical desktop session."
    else
      warn_check "Could not determine the default systemd target."
    fi
  fi

  if command -v loginctl >/dev/null 2>&1 && [[ -n "${RUNTIME_USER}" ]]; then
    session_id="$(select_runtime_session_id "${RUNTIME_USER}" || true)"
    if [[ -n "${session_id}" ]]; then
      session_type="$(loginctl show-session "${session_id}" -p Type --value 2>/dev/null || true)"
      session_desktop="$(loginctl show-session "${session_id}" -p Desktop --value 2>/dev/null || true)"
      session_state="$(loginctl show-session "${session_id}" -p State --value 2>/dev/null || true)"
      session_active="$(loginctl show-session "${session_id}" -p Active --value 2>/dev/null || true)"
      session_remote="$(loginctl show-session "${session_id}" -p Remote --value 2>/dev/null || true)"
      if [[ "${session_active}" == "yes" && "${session_remote}" != "yes" ]]; then
        pass_check "Desktop session ${session_id} for ${RUNTIME_USER} is active and local${session_state:+ (state=${session_state})}."
      elif [[ "${session_remote}" == "yes" ]]; then
        warn_check "The best matching session for ${RUNTIME_USER} is remote${session_state:+ (state=${session_state})}; Chromium kiosk must run in a local desktop session on the Pi."
      else
        warn_check "Desktop session ${session_id} for ${RUNTIME_USER} is present but not active/local (active=${session_active:-unknown}, remote=${session_remote:-unknown}${session_state:+, state=${session_state}})."
      fi
      if [[ "${session_type}" == "x11" ]]; then
        pass_check "Desktop session for ${RUNTIME_USER} is X11${session_desktop:+ (${session_desktop})}."
        if [[ "${autostart_has_unclutter}" == "true" ]]; then
          pass_check "Chromium autostart entry includes unclutter for X11 cursor hiding."
        else
          warn_check "Chromium autostart entry does not appear to launch unclutter; the mouse cursor may remain visible on X11."
        fi
      elif [[ "${session_type}" == "wayland" ]]; then
        pass_check "Desktop session for ${RUNTIME_USER} is Wayland${session_desktop:+ (${session_desktop})}."
        if [[ "${session_desktop}" == *"labwc"* ]]; then
          if [[ -f "${AUTOSTART_LABWC_FILE}" ]]; then
            pass_check "labwc autostart file exists at ${AUTOSTART_LABWC_FILE}."
            if [[ "${labwc_autostart_body}" == *"${AUTOSTART_LAUNCHER_FILE}"* ]]; then
              pass_check "labwc autostart file includes the managed kiosk launcher."
            else
              warn_check "labwc autostart file ${AUTOSTART_LABWC_FILE} does not reference the managed kiosk launcher."
            fi
          else
            warn_check "labwc Wayland session detected, but ${AUTOSTART_LABWC_FILE} is missing. The desktop entry under ~/.config/autostart may not launch Chromium on labwc."
          fi
        fi
        if [[ "${autostart_has_wayland_flag}" == "true" ]]; then
          pass_check "Chromium autostart entry requests native Wayland mode for Wayland sessions."
        else
          warn_check "Chromium autostart entry does not request native Wayland mode; Chromium may fall back to Xwayland and leave the cursor visible."
        fi
      elif [[ -n "${session_type}" ]]; then
        warn_check "Desktop session for ${RUNTIME_USER} reports Type=${session_type}${session_desktop:+ (${session_desktop})}. The kiosk launcher is validated for X11 and Wayland sessions."
      else
        warn_check "Could not determine the desktop session type for ${RUNTIME_USER}."
      fi
    else
      warn_check "Could not find an active desktop session for ${RUNTIME_USER}; session backend was not checked."
    fi
  elif [[ -n "${AUTOSTART_FILE}" && -f "${AUTOSTART_FILE}" ]]; then
    if [[ "${autostart_has_wayland_flag}" == "true" ]]; then
      pass_check "Chromium autostart entry includes a Wayland selector for Wayland sessions."
    else
      warn_check "Chromium autostart entry does not request native Wayland mode; Chromium may fall back to Xwayland on Wayland desktops."
    fi

    if [[ "${autostart_has_unclutter}" == "true" ]]; then
      pass_check "Chromium autostart entry includes unclutter for X11 cursor hiding."
    else
      warn_check "Chromium autostart entry does not appear to launch unclutter; the mouse cursor may remain visible on X11."
    fi
  fi

  expected_display_url="http://$(health_host):${PORT}/display"
  if command -v ps >/dev/null 2>&1 && [[ -n "${RUNTIME_USER}" ]]; then
    chromium_process="$(ps -ww -u "${RUNTIME_USER}" -o pid=,args= 2>/dev/null | awk -v display_url="${expected_display_url}" 'index($0, "--kiosk") && index($0, display_url) && tolower($0) ~ /chromium/ { print; exit }' || true)"
    if [[ -n "${chromium_process}" ]]; then
      pass_check "Chromium kiosk process is running for ${RUNTIME_USER}: ${chromium_process}."
    elif [[ -n "${session_id}" ]]; then
      fail_check "Chromium kiosk process is not running for ${RUNTIME_USER} even though a desktop session is active."
    else
      warn_check "Chromium kiosk process could not be verified because no active desktop session was found for ${RUNTIME_USER}."
    fi
  fi

  if [[ -n "${KIOSK_LOG_FILE}" ]]; then
    if [[ -f "${KIOSK_LOG_FILE}" ]]; then
      pass_check "Kiosk launcher log exists at ${KIOSK_LOG_FILE}."
      if [[ -r /proc/stat ]]; then
        boot_epoch="$(awk '/^btime / {print $2; exit}' /proc/stat 2>/dev/null || true)"
      fi
      log_mtime="$(stat -c '%Y' "${KIOSK_LOG_FILE}" 2>/dev/null || true)"
      if [[ -n "${boot_epoch}" && -n "${log_mtime}" ]]; then
        if (( log_mtime >= boot_epoch )); then
          pass_check "Kiosk launcher log has been updated since the current boot."
        else
          warn_check "Kiosk launcher log predates the current boot; the kiosk launcher may not have run after the last reboot."
        fi
      fi
      if grep -Fq 'Executing ' "${KIOSK_LOG_FILE}" 2>/dev/null; then
        pass_check "Kiosk launcher log recorded a Chromium launch command."
      elif [[ -n "${session_id}" ]]; then
        warn_check "Kiosk launcher log exists but does not yet show a Chromium launch command."
      fi
      if grep -Fq 'Another kiosk instance already holds' "${KIOSK_LOG_FILE}" 2>/dev/null; then
        warn_check "Kiosk launcher log shows a duplicate-launch lockout; another kiosk instance may already be holding the kiosk lock."
      fi
    elif [[ -n "${session_id}" ]]; then
      warn_check "Kiosk launcher log is missing at ${KIOSK_LOG_FILE}; kiosk launch failures may be harder to diagnose."
    fi
  fi

  if command -v vcgencmd >/dev/null 2>&1; then
    throttled="$(vcgencmd get_throttled 2>/dev/null || true)"
    if [[ -n "${throttled}" && "${throttled}" != "throttled=0x0" ]]; then
      warn_check "vcgencmd reported throttling or undervoltage: ${throttled}."
    elif [[ -n "${throttled}" ]]; then
      pass_check "vcgencmd reports no throttling or undervoltage."
    fi
  fi

  warn_check "Desktop autologin and blanking settings are not fully verified automatically; keep Raspberry Pi OS Desktop autologin enabled and screen blanking disabled. On Wayland/labwc, confirm the managed ~/.config/labwc/autostart entry still launches Chromium after reboots."

  lan_ip="$(hostname -I 2>/dev/null | awk '{print $1}')"
  if [[ "${HOST}" == "127.0.0.1" || "${HOST}" == "localhost" ]]; then
    warn_check "Admin hint: backend is loopback-only. Change the configured host if you want LAN admin access."
  elif [[ -n "${lan_ip}" ]]; then
    pass_check "Admin hint: http://${lan_ip}:${PORT}/"
  else
    warn_check "Admin hint: http://<pi-hostname-or-ip>:${PORT}/"
  fi
}

print_summary() {
  printf '\n== Summary ==\n'
  printf 'PASS: %s  WARN: %s  FAIL: %s\n' "${PASS_COUNT}" "${WARN_COUNT}" "${FAIL_COUNT}"

  if [[ "${FAIL_COUNT}" -gt 0 ]]; then
    printf 'Doctor found blocking issues.\n'
    exit 1
  fi

  if [[ "${WARN_COUNT}" -gt 0 ]]; then
    printf 'Doctor found warnings but no blocking failures.\n'
    exit 0
  fi

  printf 'Doctor found no issues.\n'
}

main() {
  parse_args "$@"
  preflight
  check_environment
  check_service
  check_config_and_paths
  check_http_endpoints
  check_display_runtime_state
  check_browser_runtime
  print_summary
}

main "$@"
