#!/usr/bin/env bash
set -euo pipefail
umask 077

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
APP_DIR="${APP_DIR:-$(cd "${SCRIPT_DIR}/.." && pwd)}"
VENDOR_DIR="${VENDOR_DIR:-${APP_DIR}/vendor}"
VENV_DIR="${VENV_DIR:-${APP_DIR}/.venv}"
PYTHON_BIN="${PYTHON_BIN:-}"

find_python() {
  if [[ -n "$PYTHON_BIN" ]]; then
    [[ -x "$PYTHON_BIN" ]] || { echo "ERROR: PYTHON_BIN is not executable: $PYTHON_BIN" >&2; exit 1; }
    printf '%s\n' "$PYTHON_BIN"
    return
  fi
  for candidate in /opt/freeware/bin/python3.11 /opt/freeware/bin/python3.9 python3.11 python3.9; do
    if command -v "$candidate" >/dev/null 2>&1; then
      command -v "$candidate"
      return
    fi
  done
  echo "ERROR: Python 3.11 or Python 3.9 was not found." >&2
  exit 1
}

PYTHON_BIN="$(find_python)"
PYTHON_VERSION="$($PYTHON_BIN -c 'import sys; print("%d.%d" % sys.version_info[:2])')"
case "$PYTHON_VERSION" in
  3.9|3.11) ;;
  *) echo "ERROR: Supported Python versions are 3.9 and 3.11; found $PYTHON_VERSION." >&2; exit 1 ;;
esac

[[ -d "$VENDOR_DIR" ]] || { echo "ERROR: Vendor directory not found: $VENDOR_DIR" >&2; exit 1; }
[[ -f "${APP_DIR}/requirements.lock.txt" ]] || { echo "ERROR: requirements.lock.txt not found." >&2; exit 1; }

PIP_WHEEL="$(find "$VENDOR_DIR" -type f -name 'pip-25.3-py3-none-any.whl' -print | head -1)"
SETUPTOOLS_WHEEL="$(find "$VENDOR_DIR" -type f -name 'setuptools-80.9.0-py3-none-any.whl' -print | head -1)"
WHEEL_WHEEL="$(find "$VENDOR_DIR" -type f -name 'wheel-0.45.1-py3-none-any.whl' -print | head -1)"
[[ -n "$PIP_WHEEL" && -n "$SETUPTOOLS_WHEEL" && -n "$WHEEL_WHEEL" ]] || {
  echo "ERROR: pip/setuptools/wheel bootstrap files are missing from vendor/." >&2
  exit 1
}

if [[ -e "$VENV_DIR" ]]; then
  echo "ERROR: $VENV_DIR already exists. Remove it only when you intend to rebuild the environment." >&2
  exit 1
fi

# --without-pip avoids dependency on ensurepip, which may be absent from AIX Python builds.
"$PYTHON_BIN" -m venv --without-pip "$VENV_DIR"

# Make pip available from its bundled wheel, then install pip into the virtual environment.
PYTHONPATH="$PIP_WHEEL" "$VENV_DIR/bin/python" -m pip install \
  --no-index --no-deps "$PIP_WHEEL"

"$VENV_DIR/bin/python" -m pip install --no-index --no-deps \
  "$SETUPTOOLS_WHEEL" "$WHEEL_WHEEL"

# MarkupSafe may attempt its optional C speedup first. On AIX without a compiler,
# its build automatically retries as a supported plain-Python installation.
"$VENV_DIR/bin/python" -m pip install \
  --no-index --find-links "$VENDOR_DIR" --no-build-isolation \
  --requirement "${APP_DIR}/requirements.lock.txt"

"$VENV_DIR/bin/python" -m pip check
"$VENV_DIR/bin/python" - <<'PY'
import flask, flask_wtf, ldap3, dotenv, gunicorn, xlsxwriter, sqlite3
print("Offline installation test passed.")
print("Python:", __import__("sys").version.split()[0])
print("Flask:", flask.__version__ if hasattr(flask, "__version__") else "installed")
PY

chmod -R go-rwx "$VENV_DIR"
echo "AIX offline environment created successfully at $VENV_DIR"
