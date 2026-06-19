import os
import sys
from pathlib import Path

APP_DIR = Path(__file__).resolve().parent
VENDOR_DIR = APP_DIR / "vendor" / "site-packages"

os.chdir(APP_DIR)
sys.path.insert(0, str(APP_DIR))
if VENDOR_DIR.exists():
    sys.path.insert(0, str(VENDOR_DIR))

from app import app as application  # noqa: E402
