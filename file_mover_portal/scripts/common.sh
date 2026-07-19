#!/usr/bin/env bash
set -euo pipefail

APP_DIR="${APP_DIR:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"
RUN_DIR="${RUN_DIR:-${APP_DIR}/run}"
PID_FILE="${PID_FILE:-${RUN_DIR}/file-mover.pid}"

read_portal_pid() {
  [[ -f "$PID_FILE" ]] || return 1
  local pid
  pid="$(cat "$PID_FILE" 2>/dev/null || true)"
  [[ "$pid" =~ ^[0-9]+$ ]] || return 1
  printf '%s' "$pid"
}

is_portal_process() {
  local pid="$1"
  kill -0 "$pid" 2>/dev/null || return 1
  local args=""
  if [[ -r "/proc/${pid}/cmdline" ]]; then
    args="$(tr '\0' ' ' < "/proc/${pid}/cmdline" 2>/dev/null || true)"
  else
    args="$(ps -p "$pid" -o args= 2>/dev/null || true)"
  fi
  [[ "$args" == *gunicorn* && "$args" == *"app:app"* ]]
}
