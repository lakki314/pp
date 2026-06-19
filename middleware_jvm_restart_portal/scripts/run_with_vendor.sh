#!/usr/bin/env bash
set -euo pipefail

APP_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$APP_DIR"

export PYTHONPATH="$APP_DIR/vendor/site-packages:$APP_DIR:${PYTHONPATH:-}"

if [ ! -d "$APP_DIR/vendor/site-packages" ]; then
  echo "Missing vendor/site-packages. Build the vendor bundle on a machine with pip first." >&2
  exit 1
fi

LOG_DIR="${LOG_DIR:-$APP_DIR/logs}"
mkdir -p "$LOG_DIR"

ACCESS_LOG="${GUNICORN_ACCESS_LOG:-$LOG_DIR/gunicorn_access.log}"
ERROR_LOG="${GUNICORN_ERROR_LOG:-$LOG_DIR/gunicorn_error.log}"
LOG_LEVEL="${GUNICORN_LOG_LEVEL:-info}"
WORKERS="${GUNICORN_WORKERS:-3}"
BIND_ADDR="${GUNICORN_BIND:-127.0.0.1:5000}"

exec python3 -m gunicorn \
  -w "$WORKERS" \
  -b "$BIND_ADDR" \
  --access-logfile "$ACCESS_LOG" \
  --error-logfile "$ERROR_LOG" \
  --capture-output \
  --log-level "$LOG_LEVEL" \
  app:app
