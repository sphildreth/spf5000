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
DECENTDB_ROOT=""
DECENTDB_BINDINGS_PATH=""
DECENTDB_NATIVE_LIB=""

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
  - The installer expects a nearby DecentDB checkout so it can install the Python binding and build the native library.
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

  if [[ "${HOST}" == "0.0.0.0" ]]; then
    DISPLAY_HOST="127.0.0.1"
    HEALTH_HOST="127.0.0.1"
  else
    DISPLAY_HOST="${HOST}"
    HEALTH_HOST="${HOST}"
  fi
  DISPLAY_URL="http://${DISPLAY_HOST}:${PORT}/display"
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
    libpg-query-dev
    nim
    nodejs
    npm
    python3
    python3-pip
    python3-venv
    unclutter
    "${chromium_package}"
  )

  log "Installing required packages: ${packages[*]}"
  DEBIAN_FRONTEND=noninteractive apt-get install -y "${packages[@]}"
}

ensure_required_binaries() {
  require_command python3
  require_command curl
  require_command nim
  require_command nimble

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

find_decentdb_checkout() {
  local candidate_roots=(
    "${APP_ROOT}/../decentdb"
    "${APP_ROOT}/decentdb"
    "${PI_REPO_ROOT}/../decentdb"
  )
  local candidate_root=""

  for candidate_root in "${candidate_roots[@]}"; do
    if [[ -f "${candidate_root}/decentdb.nimble" && -f "${candidate_root}/bindings/python/pyproject.toml" ]]; then
      printf '%s\n' "${candidate_root}"
      return 0
    fi
  done

  return 1
}

ensure_decentdb_runtime() {
  local backend_dir="${APP_ROOT}/backend"
  local venv_python="${backend_dir}/.venv/bin/python"

  DECENTDB_ROOT="$(find_decentdb_checkout)" || fail "Could not find a DecentDB checkout. Clone DecentDB next to SPF5000 (for example: ${APP_ROOT}/../decentdb) and re-run this installer."
  DECENTDB_BINDINGS_PATH="${DECENTDB_ROOT}/bindings/python"
  DECENTDB_NATIVE_LIB="${DECENTDB_ROOT}/build/libc_api.so"

  if ! run_as_user_shell "${RUNTIME_USER}" "test -w '${DECENTDB_ROOT}'"; then
    fail "DecentDB checkout ${DECENTDB_ROOT} is not writable by ${RUNTIME_USER}. Fix ownership or permissions and re-run this installer."
  fi

  log "Installing DecentDB Python binding from ${DECENTDB_BINDINGS_PATH}."
  run_as_user_shell "${RUNTIME_USER}" "cd '${backend_dir}' && .venv/bin/python -m pip install -e '${DECENTDB_BINDINGS_PATH}'"

  log "Building DecentDB native library in ${DECENTDB_ROOT}."
  if ! run_as_user_shell "${RUNTIME_USER}" "cd '${DECENTDB_ROOT}' && nimble build_lib"; then
    fail "Failed to build DecentDB native library. Ensure nim, nimble, and libpg-query-dev are installed, then re-run this installer."
  fi

  [[ -f "${DECENTDB_NATIVE_LIB}" ]] || fail "DecentDB build completed without producing ${DECENTDB_NATIVE_LIB}."

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
  local chromium_binary=""
  local autostart_dir=""

  chromium_binary="$(detect_chromium_binary)" || fail "Chromium is not installed."
  autostart_dir="$(dirname "${AUTOSTART_FILE}")"

  log "Installing Chromium kiosk autostart entry."
  mkdir -p "${autostart_dir}"
  render_template \
    "${autostart_template}" \
    "${AUTOSTART_FILE}" \
    "KIOSK_DELAY_SECONDS=${PI_DEFAULT_KIOSK_DELAY_SECONDS}" \
    "CHROMIUM_BINARY=${chromium_binary}" \
    "DISPLAY_URL=${DISPLAY_URL}"

  chown -R "${RUNTIME_USER}:${RUNTIME_GROUP}" "${autostart_dir}"
  chmod 0644 "${AUTOSTART_FILE}"
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
  Display URL   : ${DISPLAY_URL}
  DecentDB lib  : ${DECENTDB_NATIVE_LIB}

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
  ensure_backend_venv
  ensure_decentdb_runtime
  build_frontend
  write_config_if_needed
  install_service_file
  install_autostart_file
  enable_service
  wait_for_health
  print_final_summary
}

main "$@"
