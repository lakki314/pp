#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=common.sh
source "${SCRIPT_DIR}/common.sh"

if pid="$(read_portal_pid 2>/dev/null)" && is_portal_process "$pid"; then
  echo "File Mover Portal is running with PID $pid."
  exit 0
fi
if [[ -f "$PID_FILE" ]]; then
  echo "File Mover Portal is stopped or the PID file does not belong to this application."
  exit 1
fi
echo "File Mover Portal is stopped."
exit 3
