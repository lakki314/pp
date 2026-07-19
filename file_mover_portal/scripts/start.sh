#!/usr/bin/env bash
set -euo pipefail
umask 077
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=common.sh
source "${SCRIPT_DIR}/common.sh"

VENV_DIR="${VENV_DIR:-${APP_DIR}/.venv}"
LOG_DIR="${LOG_DIR:-${APP_DIR}/logs}"
ACCESS_LOG="${ACCESS_LOG:-${LOG_DIR}/gunicorn-access.log}"
ERROR_LOG="${ERROR_LOG:-${LOG_DIR}/gunicorn-error.log}"
GUNICORN_WORKERS="${GUNICORN_WORKERS:-3}"
GUNICORN_THREADS="${GUNICORN_THREADS:-4}"

mkdir -p "$RUN_DIR" "$LOG_DIR"
chmod 700 "$RUN_DIR" "$LOG_DIR"

if [[ ! -f "${APP_DIR}/.env" ]]; then
  echo "ERROR: ${APP_DIR}/.env does not exist." >&2
  exit 1
fi
if [[ ! -x "${VENV_DIR}/bin/python" ]]; then
  echo "ERROR: Python virtual environment was not found at ${VENV_DIR}." >&2
  exit 1
fi
ENV_MODE="$("${VENV_DIR}/bin/python" -c 'import os,sys; print(format(os.stat(sys.argv[1]).st_mode & 0o777, "03o"))' "${APP_DIR}/.env")"
if [[ "$ENV_MODE" != "600" ]]; then
  echo "ERROR: ${APP_DIR}/.env has mode ${ENV_MODE}; set it to 600." >&2
  exit 1
fi
if [[ ! -x "${VENV_DIR}/bin/gunicorn" ]]; then
  echo "ERROR: Gunicorn was not found at ${VENV_DIR}/bin/gunicorn." >&2
  exit 1
fi

# Read production runtime values through python-dotenv rather than sourcing .env as shell code.
env_value() {
  "${VENV_DIR}/bin/python" - "$1" "$2" <<'PY'
import sys
from dotenv import dotenv_values
values = dotenv_values(".env")
value = values.get(sys.argv[1])
print(sys.argv[2] if value is None or str(value).strip() == "" else str(value).strip())
PY
}

cd "$APP_DIR"
APP_HOST="$(env_value APP_HOST 127.0.0.1)"
APP_PORT="$(env_value APP_PORT 5000)"
BIND_ADDRESS="${APP_HOST}:${APP_PORT}"
FORWARDED_ALLOW_IPS="$(env_value TRUSTED_PROXY_IPS '')"
GUNICORN_WORKERS="$(env_value GUNICORN_WORKERS 3)"
GUNICORN_THREADS="$(env_value GUNICORN_THREADS 4)"
GUNICORN_TIMEOUT="$(env_value GUNICORN_TIMEOUT 120)"
LOG_DIR="$(env_value LOG_DIR "$LOG_DIR")"
ACCESS_LOG="$(env_value ACCESS_LOG "$ACCESS_LOG")"
ERROR_LOG="$(env_value ERROR_LOG "$ERROR_LOG")"
mkdir -p "$LOG_DIR" "$(dirname "$ACCESS_LOG")" "$(dirname "$ERROR_LOG")"
chmod 700 "$LOG_DIR" "$(dirname "$ACCESS_LOG")" "$(dirname "$ERROR_LOG")"

if [[ -z "$FORWARDED_ALLOW_IPS" ]]; then
  echo "ERROR: TRUSTED_PROXY_IPS must contain the IBM HTTP Server IP address." >&2
  exit 1
fi

if pid="$(read_portal_pid 2>/dev/null)"; then
  if is_portal_process "$pid"; then
    echo "File Mover Portal is already running with PID $pid."
    exit 0
  fi
  echo "ERROR: PID file points to a process that is not this portal. Refusing to overwrite it." >&2
  exit 1
fi
rm -f "$PID_FILE"

# Rotate and prune logs before starting Gunicorn. This is also safe to schedule separately.
"${VENV_DIR}/bin/python" "${APP_DIR}/scripts/rotate_logs.py"

"${VENV_DIR}/bin/gunicorn" \
  --daemon --pid "$PID_FILE" \
  --workers "$GUNICORN_WORKERS" --threads "$GUNICORN_THREADS" \
  --timeout "$GUNICORN_TIMEOUT" --graceful-timeout 30 --keep-alive 2 \
  --limit-request-line 4094 --limit-request-fields 50 --limit-request-field_size 8190 \
  --bind "$BIND_ADDRESS" --access-logfile "$ACCESS_LOG" --error-logfile "$ERROR_LOG" \
  --capture-output --forwarded-allow-ips="$FORWARDED_ALLOW_IPS" "app:app"

sleep 1
if pid="$(read_portal_pid 2>/dev/null)" && is_portal_process "$pid"; then
  echo "File Mover Portal started successfully with PID $pid on $BIND_ADDRESS."
  exit 0
fi
echo "ERROR: File Mover Portal did not start. Review $ERROR_LOG." >&2
exit 1
