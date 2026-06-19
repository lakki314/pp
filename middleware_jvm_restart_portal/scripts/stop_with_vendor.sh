#!/usr/bin/env bash
set -euo pipefail

APP_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$APP_DIR"

LOG_DIR="${LOG_DIR:-$APP_DIR/logs}"
PID_FILE="${PID_FILE:-$LOG_DIR/middleware-jvm-restart.pid}"

if [ ! -f "$PID_FILE" ]; then
  echo "No PID file found at $PID_FILE"
  exit 0
fi

pid="$(cat "$PID_FILE")"
if [ -z "$pid" ]; then
  rm -f "$PID_FILE"
  echo "Empty PID file removed"
  exit 0
fi

if kill -0 "$pid" 2>/dev/null; then
  kill "$pid"
  echo "Stopped Middleware JVM Restart PID $pid"
else
  echo "Process $pid is not running"
fi

rm -f "$PID_FILE"
