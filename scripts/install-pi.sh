#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
# shellcheck source=./pi-common.sh
source "${SCRIPT_DIR}/pi-common.sh"

RUNTIME_USER=""
APP_ROOT="${PI_DEFAULT_APP_ROOT}"
DATA_DIR="${PI_DEFAULT_DATA_DIR}"
CACHE_DIR="${PI_DEFAULT_CACHE_DIR}"
CONFIG_PATH="${PI_DEFAULT_CONFIG_PATH}"
SERVICE_NAME="${PI_DEFAULT_SERVICE_NAME}"
HOST="${PI_DEFAULT_HOST}"
PORT="${PI_DEFAULT_PORT}"
SKIP_APT=false
FORCE=false

RUNTIME_GROUP=""
RUNTIME_HOME=""
LOG_DIR=""
DATABASE_PATH=""
DISPLAY_HOST=""
DISPLAY_URL=""
HEALTH_HOST=""
SERVICE_FILE=""
AUTOSTART_FILE=""
AUTOSTART_LAUNCHER_FILE=""
AUTOSTART_LABWC_FILE=""
DECENTDB_RELEASE_TAG="${DECENTDB_RELEASE_TAG:-latest}"
DECENTDB_RELEASE_ASSET_NAME=""
DECENTDB_RELEASE_ASSET_URL=""
DECENTDB_SOURCE_ARCHIVE_URL=""
DECENTDB_VENDOR_DIR=""
DECENTDB_NATIVE_LIB=""
KIOSK_LOG_FILE=""
PREINSTALL_DATABASE_BACKUP=""

usage() {
  cat <<EOF
Usage: sudo ./scripts/install-pi.sh --user <username> [options]

Provision the Pi-specific SPF5000 appliance runtime around an existing repo checkout.

Options:
  --user <username>       Runtime user for the backend service and Chromium kiosk (required)
  --app-root <path>       SPF5000 checkout to operate on (default: ${PI_DEFAULT_APP_ROOT})
  --data-dir <path>       Runtime data directory (default: ${PI_DEFAULT_DATA_DIR})
  --cache-dir <path>      Runtime cache/log directory root (default: ${PI_DEFAULT_CACHE_DIR})
  --config-path <path>    Runtime config path (default: ${PI_DEFAULT_CONFIG_PATH})
  --host <host>           Backend bind host (default: ${PI_DEFAULT_HOST})
  --port <port>           Backend bind port (default: ${PI_DEFAULT_PORT})
  --skip-apt              Skip apt package installation and only validate required binaries
  --force                 Overwrite an existing generated config and continue on non-Pi hardware
  --help                  Show this help text

Notes:
  - The installer expects an existing SPF5000 checkout at --app-root.
  - A stable security.session_secret is generated only when a new config file is created.
  - The installer downloads the latest matching DecentDB native release plus the matching source archive for the Python binding.
  - Set DECENTDB_RELEASE_TAG=vX.Y.Z to override the default latest-release behavior.
EOF
}

parse_args() {
  while [[ $# -gt 0 ]]; do
    case "$1" in
      --user)
        RUNTIME_USER="$2"
        shift 2
        ;;
      --app-root)
        APP_ROOT="$2"
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
      --config-path)
        CONFIG_PATH="$2"
        shift 2
        ;;
      --host)
        HOST="$2"
        shift 2
        ;;
      --port)
        PORT="$2"
        shift 2
        ;;
      --skip-apt)
        SKIP_APT=true
        shift
        ;;
      --force)
        FORCE=true
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

  [[ -n "${RUNTIME_USER}" ]] || fail "The runtime user is required. Re-run with --user <username>."
}

preflight() {
  local os_id=""
  local os_like=""
  local model=""

  require_root
  require_command getent
  require_command id
  require_command python3
  require_command systemctl

  [[ "$(uname -s)" == "Linux" ]] || fail "This installer only supports Linux."

  if [[ -r /etc/os-release ]]; then
    # shellcheck disable=SC1091
    source /etc/os-release
    os_id="${ID:-}"
    os_like="${ID_LIKE:-}"
  fi

  if [[ "${os_id}" != "raspbian" && "${os_id}" != "debian" && "${os_like}" != *"debian"* ]]; then
    fail "This installer expects Raspberry Pi OS or another Debian-like system."
  fi

  if [[ -r /proc/device-tree/model ]]; then
    model="$(tr -d '\0' </proc/device-tree/model)"
    if [[ "${model}" != *"Raspberry Pi"* ]]; then
      if [[ "${FORCE}" == true ]]; then
        warn "Hardware model '${model}' is not a Raspberry Pi; continuing because --force was provided."
      else
        fail "Detected hardware '${model}', not a Raspberry Pi. Re-run with --force if you really want to continue."
      fi
    fi
  else
    warn "Could not confirm Raspberry Pi hardware from /proc/device-tree/model."
  fi

  id "${RUNTIME_USER}" >/dev/null 2>&1 || fail "User ${RUNTIME_USER} does not exist."
  RUNTIME_GROUP="$(resolve_user_group "${RUNTIME_USER}")"
  RUNTIME_HOME="$(resolve_user_home "${RUNTIME_USER}")"

  require_spf5000_checkout "${APP_ROOT}"

  [[ "${PORT}" =~ ^[0-9]+$ ]] || fail "Port must be numeric. Got: ${PORT}"

  if [[ "${SKIP_APT}" == false ]]; then
    require_command apt-get
    require_command apt-cache
  fi

  LOG_DIR="${CACHE_DIR}/logs"
  DATABASE_PATH="${DATA_DIR}/spf5000.ddb"
  SERVICE_FILE="/etc/systemd/system/${SERVICE_NAME}.service"
  AUTOSTART_FILE="$(kiosk_desktop_path "${RUNTIME_USER}" "${SERVICE_NAME}")"
  AUTOSTART_LAUNCHER_FILE="$(kiosk_launcher_path "${RUNTIME_USER}" "${SERVICE_NAME}")"
  AUTOSTART_LABWC_FILE="$(kiosk_labwc_autostart_path "${RUNTIME_USER}")"

  if [[ "${HOST}" == "0.0.0.0" ]]; then
    DISPLAY_HOST="127.0.0.1"
    HEALTH_HOST="127.0.0.1"
  else
    DISPLAY_HOST="${HOST}"
    HEALTH_HOST="${HOST}"
  fi
  DISPLAY_URL="http://${DISPLAY_HOST}:${PORT}/display"
  KIOSK_LOG_FILE="${LOG_DIR}/${SERVICE_NAME}-kiosk-launcher.log"
}

print_install_summary() {
  cat <<EOF
Install summary
  Runtime user : ${RUNTIME_USER}
  App root     : ${APP_ROOT}
  Data dir     : ${DATA_DIR}
  Cache dir    : ${CACHE_DIR}
  Config path  : ${CONFIG_PATH}
  Service file : ${SERVICE_FILE}
  Autostart    : ${AUTOSTART_FILE}
  Labwc start  : ${AUTOSTART_LABWC_FILE}
  Backend bind : ${HOST}:${PORT}
  Display URL  : ${DISPLAY_URL}
EOF
}

install_packages() {
  local chromium_package=""
  local packages=()

  if [[ "${SKIP_APT}" == true ]]; then
    log "Skipping apt package installation (--skip-apt)."
    return
  fi

  log "Updating apt package metadata."
  DEBIAN_FRONTEND=noninteractive apt-get update

  chromium_package="$(detect_chromium_package)" || fail "Unable to determine whether this Pi uses the chromium or chromium-browser package."

  packages=(
    build-essential
    ca-certificates
    curl
    nodejs
    npm
    python3
    python3-pip
    python3-venv
    unclutter-xfixes
    "${chromium_package}"
  )

  log "Installing required packages: ${packages[*]}"
  DEBIAN_FRONTEND=noninteractive apt-get install -y "${packages[@]}"
}

ensure_required_binaries() {
  require_command python3
  require_command curl
  require_command tar

  if ! detect_chromium_binary >/dev/null 2>&1; then
    fail "Chromium is not installed or not on PATH. Install it or omit --skip-apt."
  fi

  if ! command -v npm >/dev/null 2>&1; then
    if [[ -f "${APP_ROOT}/frontend/dist/index.html" ]]; then
      warn "npm is unavailable, but frontend/dist already exists. Reusing the existing frontend build."
    else
      fail "npm is not installed and ${APP_ROOT}/frontend/dist/index.html is missing."
    fi
  fi
}

ensure_directories() {
  log "Ensuring runtime directories exist."

  mkdir -p "${APP_ROOT}" "${DATA_DIR}" "${CACHE_DIR}" "${LOG_DIR}" "$(dirname "${CONFIG_PATH}")"

  log "Setting ownership for ${RUNTIME_USER}:${RUNTIME_GROUP}."
  chown -R "${RUNTIME_USER}:${RUNTIME_GROUP}" "${APP_ROOT}" "${DATA_DIR}" "${CACHE_DIR}"
}

resolve_configured_database_path() {
  local config_path="$1"

  python3 - "${config_path}" <<'PY'
from pathlib import Path
import sys
import tomllib

config_path = Path(sys.argv[1])

with config_path.open("rb") as handle:
    data = tomllib.load(handle)

database_path = data.get("paths", {}).get("database_path")
if not database_path:
    raise SystemExit(1)

path = Path(database_path).expanduser()
if not path.is_absolute():
    path = (config_path.parent / path).resolve()

print(path)
PY
}

resolve_database_backup_source_path() {
  local configured_database_path=""

  if [[ -f "${CONFIG_PATH}" && "${FORCE}" != true ]]; then
    if configured_database_path="$(resolve_configured_database_path "${CONFIG_PATH}" 2>/dev/null)"; then
      printf '%s\n' "${configured_database_path}"
      return 0
    fi
  fi

  printf '%s\n' "${DATABASE_PATH}"
}

stop_service_if_running() {
  if systemctl is-active --quiet "${SERVICE_NAME}.service"; then
    log "Stopping ${SERVICE_NAME}.service before refreshing install artifacts."
    systemctl stop "${SERVICE_NAME}.service"
  fi
}

backup_existing_database_if_present() {
  local database_backup_source=""
  local database_backup_dir=""
  local timestamp=""
  local archive_path=""
  local source_dir=""
  local source_name=""
  local archive_members=()

  database_backup_source="$(resolve_database_backup_source_path)"
  if [[ ! -f "${database_backup_source}" ]]; then
    log "No existing database file found at ${database_backup_source}; skipping pre-install database backup."
    return
  fi

  source_dir="$(dirname "${database_backup_source}")"
  source_name="$(basename "${database_backup_source}")"
  database_backup_dir="${source_dir}/installer-backups"
  timestamp="$(date -u +%Y%m%dT%H%M%SZ)"
  archive_path="${database_backup_dir}/spf5000-ddb-install-backup-${timestamp}.tar.gz"
  archive_members=("${source_name}")

  if [[ -f "${database_backup_source}-wal" ]]; then
    archive_members+=("${source_name}-wal")
  fi
  if [[ -f "${database_backup_source}-shm" ]]; then
    archive_members+=("${source_name}-shm")
  fi

  mkdir -p "${database_backup_dir}"
  log "Creating pre-install database backup at ${archive_path}."
  tar -czf "${archive_path}" -C "${source_dir}" "${archive_members[@]}"
  chown "${RUNTIME_USER}:${RUNTIME_GROUP}" "${database_backup_dir}" "${archive_path}"
  chmod 0750 "${database_backup_dir}"
  chmod 0640 "${archive_path}"
  PREINSTALL_DATABASE_BACKUP="${archive_path}"
}

ensure_backend_venv() {
  local backend_dir="${APP_ROOT}/backend"
  local venv_python="${backend_dir}/.venv/bin/python"

  if [[ ! -x "${venv_python}" ]]; then
    log "Creating backend virtual environment in ${backend_dir}/.venv."
    run_as_user_shell "${RUNTIME_USER}" "cd '${backend_dir}' && python3 -m venv .venv"
  else
    log "Reusing existing backend virtual environment."
  fi

  log "Upgrading pip in the backend virtual environment."
  run_as_user_shell "${RUNTIME_USER}" "cd '${backend_dir}' && .venv/bin/python -m pip install --upgrade pip"

  log "Installing backend dependencies."
  run_as_user_shell "${RUNTIME_USER}" "cd '${backend_dir}' && .venv/bin/python -m pip install -r requirements.txt"
}

decentdb_release_asset_suffix() {
  case "$(uname -m)" in
    aarch64|arm64)
      printf '%s\n' 'Linux-arm64.tar.gz'
      ;;
    x86_64|amd64)
      printf '%s\n' 'Linux-x64.tar.gz'
      ;;
    *)
      return 1
      ;;
  esac
}

resolve_decentdb_release() {
  local asset_suffix=""
  local release_info=()

  asset_suffix="$(decentdb_release_asset_suffix)" || fail "No supported prebuilt DecentDB release is available for architecture $(uname -m). Use a 64-bit Raspberry Pi OS image or install DecentDB manually from source."

  mapfile -t release_info < <(python3 - "${DECENTDB_RELEASE_TAG}" "${asset_suffix}" <<'PY'
import json
import sys
import urllib.parse
import urllib.request

requested_tag = sys.argv[1]
asset_suffix = sys.argv[2]

if requested_tag == "latest":
    api_url = "https://api.github.com/repos/sphildreth/decentdb/releases/latest"
else:
    api_url = "https://api.github.com/repos/sphildreth/decentdb/releases/tags/" + urllib.parse.quote(requested_tag, safe="")

request = urllib.request.Request(
    api_url,
    headers={
        "Accept": "application/vnd.github+json",
        "User-Agent": "spf5000-install-pi",
    },
)

with urllib.request.urlopen(request) as response:
    release = json.load(response)

tag_name = release["tag_name"]
asset_name = None
asset_url = None
for asset in release.get("assets", []):
    name = asset.get("name", "")
    if name.endswith(asset_suffix):
        asset_name = name
        asset_url = asset.get("browser_download_url")
        break

if not asset_name or not asset_url:
    raise SystemExit(f"Missing DecentDB release asset matching *{asset_suffix} for {tag_name}")

source_url = f"https://github.com/sphildreth/decentdb/archive/refs/tags/{tag_name}.tar.gz"

print(tag_name)
print(asset_name)
print(asset_url)
print(source_url)
PY
)

[[ "${#release_info[@]}" -eq 4 ]] || fail "Could not resolve DecentDB release metadata from GitHub."

DECENTDB_RELEASE_TAG="${release_info[0]}"
DECENTDB_RELEASE_ASSET_NAME="${release_info[1]}"
DECENTDB_RELEASE_ASSET_URL="${release_info[2]}"
DECENTDB_SOURCE_ARCHIVE_URL="${release_info[3]}"
}

download_and_extract_tarball() {
  local url="$1"
  local output_dir="$2"

  mkdir -p "${output_dir}"
  curl --fail --silent --show-error --location "${url}" | tar -xz -C "${output_dir}" --strip-components=1
}

find_decentdb_native_lib() {
  local search_dir="$1"
  local candidate=""

  for candidate in \
    "${search_dir}/libdecentdb.so" \
    "${search_dir}/libc_api.so"; do
    if [[ -f "${candidate}" ]]; then
      printf '%s\n' "${candidate}"
      return 0
    fi
  done

  return 1
}

ensure_decentdb_runtime() {
  local backend_dir="${APP_ROOT}/backend"
  local venv_python="${backend_dir}/.venv/bin/python"
  local native_extract_dir="${CACHE_DIR}/tmp/decentdb-native"
  local source_extract_dir="${CACHE_DIR}/tmp/decentdb-source"
  local extracted_native_lib=""

  resolve_decentdb_release

  DECENTDB_VENDOR_DIR="${APP_ROOT}/vendor/decentdb"

  log "Downloading DecentDB native release ${DECENTDB_RELEASE_ASSET_NAME}."
  rm -rf "${native_extract_dir}" "${source_extract_dir}" "${DECENTDB_VENDOR_DIR}"
  download_and_extract_tarball "${DECENTDB_RELEASE_ASSET_URL}" "${native_extract_dir}"

  extracted_native_lib="$(find_decentdb_native_lib "${native_extract_dir}")" || fail "Downloaded DecentDB release ${DECENTDB_RELEASE_ASSET_NAME}, but no Linux native library was found inside it."

  mkdir -p "${DECENTDB_VENDOR_DIR}"
  cp -a "${native_extract_dir}/." "${DECENTDB_VENDOR_DIR}/"
  chown -R "${RUNTIME_USER}:${RUNTIME_GROUP}" "${DECENTDB_VENDOR_DIR}"

  DECENTDB_NATIVE_LIB="$(find_decentdb_native_lib "${DECENTDB_VENDOR_DIR}")" || fail "Installed DecentDB release bundle, but could not locate the managed native library under ${DECENTDB_VENDOR_DIR}."

  log "Downloading DecentDB source archive ${DECENTDB_RELEASE_TAG} for the Python binding."
  download_and_extract_tarball "${DECENTDB_SOURCE_ARCHIVE_URL}" "${source_extract_dir}"
  chown -R "${RUNTIME_USER}:${RUNTIME_GROUP}" "${source_extract_dir}"

  [[ -f "${source_extract_dir}/bindings/python/pyproject.toml" ]] || fail "Downloaded DecentDB source archive ${DECENTDB_RELEASE_TAG}, but bindings/python/pyproject.toml was not found."

  log "Installing DecentDB Python binding from the ${DECENTDB_RELEASE_TAG} source archive."
  run_as_user_shell "${RUNTIME_USER}" "cd '${backend_dir}' && .venv/bin/python -m pip install --force-reinstall '${source_extract_dir}/bindings/python'"

  log "Validating DecentDB runtime with ${DECENTDB_NATIVE_LIB}."
  if ! env DECENTDB_NATIVE_LIB="${DECENTDB_NATIVE_LIB}" "${venv_python}" -c 'import decentdb; conn = decentdb.connect(":memory:"); conn.close()' >/dev/null 2>&1; then
    fail "DecentDB Python binding installed, but opening a database with ${DECENTDB_NATIVE_LIB} failed."
  fi
}

build_frontend() {
  local frontend_dir="${APP_ROOT}/frontend"

  if ! command -v npm >/dev/null 2>&1; then
    log "Skipping frontend build because npm is unavailable and an existing frontend/dist build was found."
    return
  fi

  log "Installing frontend dependencies."
  run_as_user_shell "${RUNTIME_USER}" "cd '${frontend_dir}' && npm install --package-lock=false"

  log "Building frontend/dist for production serving."
  run_as_user_shell "${RUNTIME_USER}" "cd '${frontend_dir}' && npm run build"
}

write_config_if_needed() {
  local session_secret=""

  if [[ -f "${CONFIG_PATH}" && "${FORCE}" != true ]]; then
    log "Preserving existing config at ${CONFIG_PATH}."
    return
  fi

  session_secret="$(python3 -c 'import secrets; print(secrets.token_hex(32))')"
  log "Writing runtime config to ${CONFIG_PATH}."

  cat >"${CONFIG_PATH}" <<EOF
# SPF5000 Pi runtime config generated by scripts/install-pi.sh
# Runtime/startup settings live here. Slideshow settings, bootstrap state, and admin
# account state are stored in DecentDB.

[server]
host = "${HOST}"
port = ${PORT}
debug = false

[logging]
level = "INFO"

[security]
session_secret = "${session_secret}"

[paths]
data_dir = "${DATA_DIR}"
cache_dir = "${CACHE_DIR}"
log_dir = "${LOG_DIR}"
database_path = "${DATABASE_PATH}"
EOF

  chown "${RUNTIME_USER}:${RUNTIME_GROUP}" "${CONFIG_PATH}"
  chmod 0640 "${CONFIG_PATH}"
}

install_empty_cursor() {
  local icons_dir="${RUNTIME_HOME}/.icons"
  local theme_dir="${icons_dir}/empty"
  local cursors_dir="${theme_dir}/cursors"

  log "Installing empty cursor theme to hide cursor on Wayland."
  mkdir -p "${cursors_dir}" "${icons_dir}/default"

  cat <<EOF >"${theme_dir}/index.theme"
[Icon Theme]
Name=Empty
Comment=Empty cursor theme
EOF

  python3 -c '
import struct
import sys

def write_xcursor(filename):
    with open(filename, "wb") as f:
        f.write(b"Xcur")
        f.write(struct.pack("<I", 16))
        f.write(struct.pack("<I", 0x10000))
        f.write(struct.pack("<I", 1))
        f.write(struct.pack("<I", 0xfffd0002))
        f.write(struct.pack("<I", 1))
        f.write(struct.pack("<I", 28))
        f.write(struct.pack("<I", 36))
        f.write(struct.pack("<I", 0xfffd0002))
        f.write(struct.pack("<I", 1))
        f.write(struct.pack("<I", 1))
        f.write(struct.pack("<IIII", 1, 1, 0, 0))
        f.write(struct.pack("<I", 0))
        f.write(struct.pack("<I", 0x00000000))

write_xcursor(sys.argv[1])
' "${cursors_dir}/left_ptr"

  # Link common cursor names
  for name in default pointer right_ptr crosshair x-cursor; do
    ln -sf left_ptr "${cursors_dir}/${name}"
  done

  # Make it the default for this user
  cat <<EOF >"${icons_dir}/default/index.theme"
[Icon Theme]
Inherits=empty
EOF

  chown -R "${RUNTIME_USER}:${RUNTIME_GROUP}" "${icons_dir}"

  # Configure labwc and wayfire to use the empty cursor
  local labwc_env="${RUNTIME_HOME}/.config/labwc/environment"
  local wayfire_ini="${RUNTIME_HOME}/.config/wayfire.ini"

  mkdir -p "$(dirname "${labwc_env}")" "$(dirname "${wayfire_ini}")"
  
  if [[ ! -f "${labwc_env}" ]] || ! grep -q "XCURSOR_THEME" "${labwc_env}"; then
    echo "XCURSOR_THEME=empty" >> "${labwc_env}"
  fi
  
  if [[ ! -f "${wayfire_ini}" ]] || ! grep -q "cursor_theme" "${wayfire_ini}"; then
    echo -e "\n[input]\ncursor_theme = empty" >> "${wayfire_ini}"
  fi

  chown -R "${RUNTIME_USER}:${RUNTIME_GROUP}" "${RUNTIME_HOME}/.config/labwc" "${RUNTIME_HOME}/.config/wayfire.ini" 2>/dev/null || true
}

install_service_file() {
  local service_template="${APP_ROOT}/deploy/systemd/spf5000.service.template"
  local python_bin="${APP_ROOT}/backend/.venv/bin/python"

  log "Installing systemd unit ${SERVICE_FILE}."
  render_template \
    "${service_template}" \
    "${SERVICE_FILE}" \
    "RUNTIME_USER=${RUNTIME_USER}" \
    "RUNTIME_GROUP=${RUNTIME_GROUP}" \
    "BACKEND_DIR=${APP_ROOT}/backend" \
    "CONFIG_PATH=${CONFIG_PATH}" \
    "PYTHON_BIN=${python_bin}" \
    "DECENTDB_NATIVE_LIB=${DECENTDB_NATIVE_LIB}"

  chmod 0644 "${SERVICE_FILE}"
}

install_autostart_file() {
  local autostart_template="${APP_ROOT}/deploy/autostart/spf5000-kiosk.desktop.template"
  local launcher_template="${APP_ROOT}/deploy/autostart/spf5000-kiosk-launch.sh.template"
  local chromium_binary=""
  local autostart_dir=""

  chromium_binary="$(detect_chromium_binary)" || fail "Chromium is not installed."
  autostart_dir="$(dirname "${AUTOSTART_FILE}")"

  log "Installing Chromium kiosk autostart entry."
  mkdir -p "${autostart_dir}"
  render_template \
    "${launcher_template}" \
    "${AUTOSTART_LAUNCHER_FILE}" \
    "KIOSK_DELAY_SECONDS=${PI_DEFAULT_KIOSK_DELAY_SECONDS}" \
    "CHROMIUM_BINARY=${chromium_binary}" \
    "DISPLAY_URL=${DISPLAY_URL}" \
    "KIOSK_LOG_PATH=${KIOSK_LOG_FILE}"
  render_template \
    "${autostart_template}" \
    "${AUTOSTART_FILE}" \
    "KIOSK_LAUNCHER=${AUTOSTART_LAUNCHER_FILE}"

  chown -R "${RUNTIME_USER}:${RUNTIME_GROUP}" "${autostart_dir}"
  chmod 0755 "${AUTOSTART_LAUNCHER_FILE}"
  chmod 0644 "${AUTOSTART_FILE}"
}

install_labwc_autostart_file() {
  local labwc_dir=""
  local labwc_block=""

  labwc_dir="$(dirname "${AUTOSTART_LABWC_FILE}")"

  log "Installing labwc autostart command for Wayland sessions."
  mkdir -p "${labwc_dir}"
  chown "${RUNTIME_USER}:${RUNTIME_GROUP}" "${labwc_dir}"

  labwc_block="$(cat <<EOF
/bin/sh "${AUTOSTART_LAUNCHER_FILE}" &
EOF
)"
  upsert_managed_text_block \
    "${AUTOSTART_LABWC_FILE}" \
    "${PI_KIOSK_LABWC_BLOCK_START}" \
    "${PI_KIOSK_LABWC_BLOCK_END}" \
    "${labwc_block}"

  chown "${RUNTIME_USER}:${RUNTIME_GROUP}" "${AUTOSTART_LABWC_FILE}"
  chmod 0644 "${AUTOSTART_LABWC_FILE}"
}

enable_service() {
  log "Reloading systemd and enabling ${SERVICE_NAME}.service."
  systemctl daemon-reload
  systemctl enable "${SERVICE_NAME}.service"

  if systemctl is-active --quiet "${SERVICE_NAME}.service"; then
    log "Restarting ${SERVICE_NAME}.service."
    systemctl restart "${SERVICE_NAME}.service"
  else
    log "Starting ${SERVICE_NAME}.service."
    systemctl start "${SERVICE_NAME}.service"
  fi
}

wait_for_health() {
  local health_url="http://${HEALTH_HOST}:${PORT}/api/health"
  local attempt=""

  log "Waiting for ${SERVICE_NAME}.service to report healthy at ${health_url}."
  for attempt in $(seq 1 20); do
    if curl --silent --show-error --fail --max-time 3 "${health_url}" >/dev/null 2>&1; then
      log "Backend health endpoint responded successfully."
      return
    fi
    sleep 1
  done

  warn "Backend health check did not succeed within the expected startup window."
  systemctl --no-pager --full status "${SERVICE_NAME}.service" || true
  fail "The service started, but the backend did not become healthy."
}

print_final_summary() {
  local lan_ip=""
  local admin_hint=""

  lan_ip="$(hostname -I 2>/dev/null | awk '{print $1}')"
  if [[ "${HOST}" == "127.0.0.1" || "${HOST}" == "localhost" ]]; then
    admin_hint="Backend is bound to ${HOST}; change --host to 0.0.0.0 if you want LAN admin access."
  elif [[ -n "${lan_ip}" ]]; then
    admin_hint="http://${lan_ip}:${PORT}/"
  else
    admin_hint="http://<pi-hostname-or-ip>:${PORT}/"
  fi

  cat <<EOF

SPF5000 Pi install complete.

What was configured
  Config path   : ${CONFIG_PATH}
  Service name  : ${SERVICE_NAME}.service
  Kiosk entry   : ${AUTOSTART_FILE}
  labwc entry   : ${AUTOSTART_LABWC_FILE}
  Display URL   : ${DISPLAY_URL}
  DB backup     : ${PREINSTALL_DATABASE_BACKUP:-not created}
  DecentDB tag  : ${DECENTDB_RELEASE_TAG}
  DecentDB lib  : ${DECENTDB_NATIVE_LIB}
  Kiosk log     : ${KIOSK_LOG_FILE}

Useful commands
  sudo systemctl status ${SERVICE_NAME}.service
  sudo journalctl -u ${SERVICE_NAME}.service -f
  sudo ${APP_ROOT}/scripts/doctor.sh --user ${RUNTIME_USER} --config-path ${CONFIG_PATH}

Admin UI
  ${admin_hint}

Still manual
  - Enable Raspberry Pi OS Desktop autologin (raspi-config -> System Options -> Boot / Auto Login -> Desktop Autologin).
  - Disable OS-level screen blanking if you want SPF5000 to control sleep/blackout behavior.
  - Import photos and complete /setup from another LAN device if this is a fresh install.
  - If the desktop session for ${RUNTIME_USER} was already logged in during this install, log out or reboot once so the refreshed Chromium autostart files can launch the kiosk browser.

Reminder
  Slideshow sleep scheduling is handled by SPF5000 application settings, not by this installer.
EOF
}

main() {
  parse_args "$@"
  preflight
  print_install_summary
  install_packages
  ensure_required_binaries
  ensure_directories
  stop_service_if_running
  backup_existing_database_if_present
  ensure_backend_venv
  ensure_decentdb_runtime
  build_frontend
  write_config_if_needed
  install_empty_cursor
  install_service_file
  install_autostart_file
  install_labwc_autostart_file
  enable_service
  wait_for_health
  print_final_summary
}

main "$@"
