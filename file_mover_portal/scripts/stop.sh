#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=common.sh
source "${SCRIPT_DIR}/common.sh"
STOP_TIMEOUT="${STOP_TIMEOUT:-30}"

if ! pid="$(read_portal_pid 2>/dev/null)"; then
  echo "File Mover Portal is not running: valid PID file not found."
  rm -f "$PID_FILE"
  exit 0
fi
if ! is_portal_process "$pid"; then
  echo "ERROR: PID $pid does not belong to this portal. No signal was sent." >&2
  exit 1
fi

echo "Stopping File Mover Portal with PID $pid..."
kill -TERM "$pid"
for ((i=0; i<STOP_TIMEOUT; i++)); do
  if ! kill -0 "$pid" 2>/dev/null; then
    rm -f "$PID_FILE"
    echo "File Mover Portal stopped successfully."
    exit 0
  fi
  sleep 1
done

echo "WARNING: Graceful stop timed out; sending SIGKILL to verified portal PID." >&2
if is_portal_process "$pid"; then kill -KILL "$pid" 2>/dev/null || true; fi
rm -f "$PID_FILE"
