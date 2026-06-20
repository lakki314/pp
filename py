#!/usr/bin/env python3
"""
Pure Python start/stop manager for the Middleware JVM Restart Flask portal.

Usage from the project folder:
  python scripts/manage_portal.py start
  python scripts/manage_portal.py stop
  python scripts/manage_portal.py restart
  python scripts/manage_portal.py status

This is intended for local Windows/Python testing or simple non-systemd use.
For production Linux behind Apache, Gunicorn is still preferred.
"""

from __future__ import annotations

import argparse
import os
import signal
import subprocess
import sys
import time
from pathlib import Path
from typing import Optional


def app_dir_from_script() -> Path:
    script_path = Path(__file__).resolve()
    if script_path.parent.name == "scripts":
        return script_path.parent.parent
    return script_path.parent


APP_DIR = app_dir_from_script()
APP_FILE = APP_DIR / "app.py"
LOG_DIR = APP_DIR / "logs"
PID_FILE = LOG_DIR / "middleware-jvm-restart-python.pid"
LOG_FILE = LOG_DIR / "middleware-jvm-restart-python.log"


def read_pid() -> Optional[int]:
    if not PID_FILE.exists():
        return None
    try:
        return int(PID_FILE.read_text(encoding="utf-8").strip())
    except ValueError:
        return None


def is_process_running(pid: int) -> bool:
    if pid <= 0:
        return False

    if os.name == "nt":
        result = subprocess.run(
            ["tasklist", "/FI", f"PID eq {pid}", "/FO", "CSV", "/NH"],
            capture_output=True,
            text=True,
            check=False,
        )
        output = (result.stdout or "") + (result.stderr or "")
        return str(pid) in output and "No tasks" not in output

    try:
        os.kill(pid, 0)
        return True
    except ProcessLookupError:
        return False
    except PermissionError:
        return True


def status() -> int:
    pid = read_pid()
    if pid and is_process_running(pid):
        print(f"Middleware JVM Restart portal is running. PID: {pid}")
        print(f"Log file: {LOG_FILE}")
        return 0

    if pid and not is_process_running(pid):
        print(f"PID file exists but process is not running. Removing stale PID file: {PID_FILE}")
        PID_FILE.unlink(missing_ok=True)

    print("Middleware JVM Restart portal is stopped.")
    return 1


def start(host: str, port: str) -> int:
    if not APP_FILE.exists():
        print(f"ERROR: app.py not found: {APP_FILE}", file=sys.stderr)
        return 2

    LOG_DIR.mkdir(parents=True, exist_ok=True)

    existing_pid = read_pid()
    if existing_pid and is_process_running(existing_pid):
        print(f"Middleware JVM Restart portal is already running. PID: {existing_pid}")
        print(f"Open: http://{host if host != '0.0.0.0' else 'localhost'}:{port}")
        return 0

    if existing_pid:
        PID_FILE.unlink(missing_ok=True)

    env = os.environ.copy()
    env.setdefault("FLASK_HOST", host)
    env.setdefault("FLASK_PORT", port)
    env.setdefault("FLASK_DEBUG", "false")
    env.setdefault("PYTHONUNBUFFERED", "1")

    command = [sys.executable, str(APP_FILE)]
    log_handle = LOG_FILE.open("ab")

    print(f"Starting Middleware JVM Restart portal...")
    print(f"Command: {' '.join(command)}")
    print(f"Working directory: {APP_DIR}")
    print(f"Log file: {LOG_FILE}")

    if os.name == "nt":
        creation_flags = 0
        if hasattr(subprocess, "CREATE_NEW_PROCESS_GROUP"):
            creation_flags |= subprocess.CREATE_NEW_PROCESS_GROUP
        if hasattr(subprocess, "DETACHED_PROCESS"):
            creation_flags |= subprocess.DETACHED_PROCESS
        process = subprocess.Popen(
            command,
            cwd=str(APP_DIR),
            stdout=log_handle,
            stderr=subprocess.STDOUT,
            stdin=subprocess.DEVNULL,
            env=env,
            creationflags=creation_flags,
        )
    else:
        process = subprocess.Popen(
            command,
            cwd=str(APP_DIR),
            stdout=log_handle,
            stderr=subprocess.STDOUT,
            stdin=subprocess.DEVNULL,
            env=env,
            start_new_session=True,
        )

    PID_FILE.write_text(str(process.pid), encoding="utf-8")
    time.sleep(1)

    if is_process_running(process.pid):
        print(f"Started. PID: {process.pid}")
        print(f"Open: http://{host if host != '0.0.0.0' else 'localhost'}:{port}")
        return 0

    print("ERROR: Process did not stay running. Check the log file:")
    print(LOG_FILE)
    return 1


def stop() -> int:
    pid = read_pid()
    if not pid:
        print("Middleware JVM Restart portal is already stopped. No PID file found.")
        return 0

    if not is_process_running(pid):
        print(f"Process {pid} is not running. Removing stale PID file.")
        PID_FILE.unlink(missing_ok=True)
        return 0

    print(f"Stopping Middleware JVM Restart portal. PID: {pid}")

    if os.name == "nt":
        result = subprocess.run(["taskkill", "/PID", str(pid), "/T", "/F"], check=False)
        if result.returncode != 0:
            print(f"WARNING: taskkill returned code {result.returncode}")
    else:
        os.kill(pid, signal.SIGTERM)
        for _ in range(20):
            if not is_process_running(pid):
                break
            time.sleep(0.5)
        if is_process_running(pid):
            print("Process did not stop after SIGTERM. Sending SIGKILL.")
            os.kill(pid, signal.SIGKILL)

    PID_FILE.unlink(missing_ok=True)
    print("Stopped.")
    return 0


def restart(host: str, port: str) -> int:
    stop_code = stop()
    if stop_code != 0:
        return stop_code
    return start(host, port)


def main() -> int:
    parser = argparse.ArgumentParser(description="Start/stop Middleware JVM Restart Flask portal")
    parser.add_argument("action", choices=["start", "stop", "restart", "status"])
    parser.add_argument("--host", default=os.environ.get("FLASK_HOST", "0.0.0.0"))
    parser.add_argument("--port", default=os.environ.get("FLASK_PORT", "5000"))
    args = parser.parse_args()

    if args.action == "start":
        return start(args.host, str(args.port))
    if args.action == "stop":
        return stop()
    if args.action == "restart":
        return restart(args.host, str(args.port))
    return status()


if __name__ == "__main__":
    raise SystemExit(main())
