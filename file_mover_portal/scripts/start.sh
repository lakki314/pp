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
BIND_ADDRESS="${BIND_ADDRESS:-127.0.0.1:5000}"
GUNICORN_WORKERS="${GUNICORN_WORKERS:-3}"
GUNICORN_THREADS="${GUNICORN_THREADS:-4}"
GUNICORN_TIMEOUT="${GUNICORN_TIMEOUT:-120}"

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

if pid="$(read_portal_pid 2>/dev/null)"; then
  if is_portal_process "$pid"; then
    echo "File Mover Portal is already running with PID $pid."
    exit 0
  fi
  echo "ERROR: PID file points to a process that is not this portal. Refusing to overwrite it." >&2
  exit 1
fi
rm -f "$PID_FILE"

cd "$APP_DIR"
"${VENV_DIR}/bin/gunicorn" \
  --daemon --pid "$PID_FILE" \
  --workers "$GUNICORN_WORKERS" --threads "$GUNICORN_THREADS" \
  --timeout "$GUNICORN_TIMEOUT" --graceful-timeout 30 --keep-alive 2 \
  --limit-request-line 4094 --limit-request-fields 50 --limit-request-field_size 8190 \
  --bind "$BIND_ADDRESS" --access-logfile "$ACCESS_LOG" --error-logfile "$ERROR_LOG" \
  --capture-output --forwarded-allow-ips="127.0.0.1" "app:app"

sleep 1
if pid="$(read_portal_pid 2>/dev/null)" && is_portal_process "$pid"; then
  echo "File Mover Portal started successfully with PID $pid on $BIND_ADDRESS."
  exit 0
fi
echo "ERROR: File Mover Portal did not start. Review $ERROR_LOG." >&2
exit 1
