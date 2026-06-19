#!/usr/bin/env bash
set -euo pipefail

APP_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$APP_DIR"

rm -rf vendor/site-packages
mkdir -p vendor/site-packages

python3 -m pip install --target vendor/site-packages -r requirements.txt --no-cache-dir

find vendor/site-packages -type d -name '__pycache__' -prune -exec rm -rf {} +
find vendor/site-packages -type f -name '*.pyc' -delete

echo "Vendor bundle created at $APP_DIR/vendor/site-packages"
