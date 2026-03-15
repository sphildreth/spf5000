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
  fi

  load_runtime_config
}

health_host() {
  if [[ "${HOST}" == "0.0.0.0" ]]; then
    printf '%s\n' "127.0.0.1"
    return
  fi

  printf '%s\n' "${HOST}"
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
  local health_json=""
  local bootstrapped_state=""
  local bootstrapped_value=""

  printf '\n== HTTP health ==\n'

  if ! command -v curl >/dev/null 2>&1; then
    return
  fi

  local_host="$(health_host)"
  health_url="http://${local_host}:${PORT}/api/health"
  session_url="http://${local_host}:${PORT}/api/auth/session"

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
}

check_browser_runtime() {
  local chromium_binary=""
  local default_target=""
  local throttled=""
  local lan_ip=""

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

  if command -v vcgencmd >/dev/null 2>&1; then
    throttled="$(vcgencmd get_throttled 2>/dev/null || true)"
    if [[ -n "${throttled}" && "${throttled}" != "throttled=0x0" ]]; then
      warn_check "vcgencmd reported throttling or undervoltage: ${throttled}."
    elif [[ -n "${throttled}" ]]; then
      pass_check "vcgencmd reports no throttling or undervoltage."
    fi
  fi

  warn_check "Desktop autologin and X11 blanking settings are not fully verified automatically; keep Raspberry Pi OS Desktop autologin enabled and screen blanking disabled."

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
  check_browser_runtime
  print_summary
}

main "$@"
