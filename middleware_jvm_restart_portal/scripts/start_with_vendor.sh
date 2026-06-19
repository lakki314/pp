#!/usr/bin/env bash
set -euo pipefail

APP_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$APP_DIR"

LOG_DIR="${LOG_DIR:-$APP_DIR/logs}"
PID_FILE="${PID_FILE:-$LOG_DIR/middleware-jvm-restart.pid}"
NOHUP_LOG="${NOHUP_LOG:-$LOG_DIR/middleware-jvm-restart.out}"
mkdir -p "$LOG_DIR"

if [ -f "$PID_FILE" ]; then
  old_pid="$(cat "$PID_FILE")"
  if [ -n "$old_pid" ] && kill -0 "$old_pid" 2>/dev/null; then
    echo "Middleware JVM Restart is already running with PID $old_pid"
    exit 0
  fi
  rm -f "$PID_FILE"
fi

nohup "$APP_DIR/scripts/run_with_vendor.sh" > "$NOHUP_LOG" 2>&1 &
echo $! > "$PID_FILE"
echo "Started Middleware JVM Restart with PID $(cat "$PID_FILE")"
echo "Logs: $LOG_DIR"
