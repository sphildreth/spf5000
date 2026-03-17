#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
# shellcheck source=./pi-common.sh
source "${SCRIPT_DIR}/pi-common.sh"

RUNTIME_USER=""
CONFIG_PATH="${PI_DEFAULT_CONFIG_PATH}"
DATA_DIR="${PI_DEFAULT_DATA_DIR}"
CACHE_DIR="${PI_DEFAULT_CACHE_DIR}"
SERVICE_NAME="${PI_DEFAULT_SERVICE_NAME}"
PURGE=false

SERVICE_FILE=""
AUTOSTART_FILE=""
AUTOSTART_LAUNCHER_FILE=""
AUTOSTART_LABWC_FILE=""

usage() {
  cat <<EOF
Usage: sudo ./scripts/uninstall-pi.sh [options]

Remove the operational SPF5000 appliance wiring from a Raspberry Pi without
deleting user data by default.

Options:
  --user <username>       Runtime user that owns the Chromium autostart entry
  --config-path <path>    Runtime config path to preserve or purge (default: ${PI_DEFAULT_CONFIG_PATH})
  --data-dir <path>       Runtime data directory to preserve or purge (default: ${PI_DEFAULT_DATA_DIR})
  --cache-dir <path>      Runtime cache directory to preserve or purge (default: ${PI_DEFAULT_CACHE_DIR})
  --service-name <name>   Systemd service name to remove (default: ${PI_DEFAULT_SERVICE_NAME})
  --purge                 Also remove the config, data, and cache directories
  --help                  Show this help text
EOF
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
      --data-dir)
        DATA_DIR="$2"
        shift 2
        ;;
      --cache-dir)
        CACHE_DIR="$2"
        shift 2
        ;;
      --service-name)
        SERVICE_NAME="$2"
        shift 2
        ;;
      --purge)
        PURGE=true
        shift
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

preflight() {
  require_root
  require_command systemctl

  SERVICE_FILE="/etc/systemd/system/${SERVICE_NAME}.service"
  if [[ -z "${RUNTIME_USER}" ]]; then
    RUNTIME_USER="$(infer_service_value "${SERVICE_FILE}" "User" || true)"
  fi

  if [[ -n "${RUNTIME_USER}" ]]; then
    AUTOSTART_FILE="$(kiosk_desktop_path "${RUNTIME_USER}" "${SERVICE_NAME}")"
    AUTOSTART_LAUNCHER_FILE="$(kiosk_launcher_path "${RUNTIME_USER}" "${SERVICE_NAME}")"
    AUTOSTART_LABWC_FILE="$(kiosk_labwc_autostart_path "${RUNTIME_USER}")"
  fi
}

print_uninstall_summary() {
  cat <<EOF
Uninstall summary
  Service file : ${SERVICE_FILE}
  Autostart    : ${AUTOSTART_FILE:-<skipped; no user supplied or inferred>}
  labwc start  : ${AUTOSTART_LABWC_FILE:-<skipped; no user supplied or inferred>}
  Config path  : ${CONFIG_PATH}
  Data dir     : ${DATA_DIR}
  Cache dir    : ${CACHE_DIR}
  Purge data   : ${PURGE}
EOF
}

remove_service() {
  if systemctl list-unit-files "${SERVICE_NAME}.service" --no-legend >/dev/null 2>&1; then
    log "Stopping ${SERVICE_NAME}.service if it is running."
    systemctl stop "${SERVICE_NAME}.service" || true
    log "Disabling ${SERVICE_NAME}.service if it is enabled."
    systemctl disable "${SERVICE_NAME}.service" || true
  fi

  if [[ -f "${SERVICE_FILE}" ]]; then
    log "Removing ${SERVICE_FILE}."
    rm -f "${SERVICE_FILE}"
  else
    log "Service file ${SERVICE_FILE} is already absent."
  fi

  log "Reloading systemd state."
  systemctl daemon-reload
  systemctl reset-failed "${SERVICE_NAME}.service" >/dev/null 2>&1 || true
}

remove_autostart() {
  if [[ -z "${AUTOSTART_FILE}" ]]; then
    warn "No runtime user was supplied or inferred, so the Chromium autostart entry was not removed."
    return
  fi

  if [[ -f "${AUTOSTART_FILE}" ]]; then
    log "Removing ${AUTOSTART_FILE}."
    rm -f "${AUTOSTART_FILE}"
  else
    log "Autostart entry ${AUTOSTART_FILE} is already absent."
  fi

  if [[ -f "${AUTOSTART_LAUNCHER_FILE}" ]]; then
    log "Removing ${AUTOSTART_LAUNCHER_FILE}."
    rm -f "${AUTOSTART_LAUNCHER_FILE}"
  else
    log "Autostart launcher ${AUTOSTART_LAUNCHER_FILE} is already absent."
  fi

  if [[ -f "${AUTOSTART_LABWC_FILE}" ]]; then
    if grep -Fq "${PI_KIOSK_LABWC_BLOCK_START}" "${AUTOSTART_LABWC_FILE}" 2>/dev/null; then
      log "Removing the managed labwc autostart block from ${AUTOSTART_LABWC_FILE}."
      remove_managed_text_block "${AUTOSTART_LABWC_FILE}" "${PI_KIOSK_LABWC_BLOCK_START}" "${PI_KIOSK_LABWC_BLOCK_END}"
    else
      log "Managed labwc autostart block is already absent from ${AUTOSTART_LABWC_FILE}."
    fi
  else
    log "labwc autostart file ${AUTOSTART_LABWC_FILE} is already absent."
  fi
}

purge_runtime_data() {
  [[ "${PURGE}" == true ]] || return

  log "Purging runtime config, data, and cache directories."
  safe_remove_path "${CONFIG_PATH}"
  safe_remove_path "${DATA_DIR}"
  safe_remove_path "${CACHE_DIR}"
}

print_final_summary() {
  if [[ "${PURGE}" == true ]]; then
    cat <<EOF

SPF5000 appliance wiring was removed, including the runtime config, data, and cache paths.

The repository checkout under /opt or another app root was intentionally left in place.
EOF
    return
  fi

  cat <<EOF

SPF5000 appliance wiring was removed.

Preserved
  - ${CONFIG_PATH}
  - ${DATA_DIR}
  - ${CACHE_DIR}

Use --purge if you also want to remove those runtime paths.
EOF
}

main() {
  parse_args "$@"
  preflight
  print_uninstall_summary
  remove_service
  remove_autostart
  purge_runtime_data
  print_final_summary
}

main "$@"
