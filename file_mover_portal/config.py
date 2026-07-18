from __future__ import annotations

import os
import secrets
from datetime import timedelta
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(override=False)


def env_bool(name: str, default: bool = False) -> bool:
    return os.getenv(name, str(default)).strip().lower() in {"1", "true", "yes", "on"}


class Config:
    APP_NAME = os.getenv("APP_NAME", "File Mover Portal").strip() or "File Mover Portal"

    SECRET_KEY = os.getenv("SECRET_KEY", "")
    if not SECRET_KEY or SECRET_KEY == "change-this-in-production" or len(SECRET_KEY) < 32:
        if env_bool("FLASK_DEBUG", False):
            SECRET_KEY = secrets.token_hex(32)
        else:
            raise RuntimeError("SECRET_KEY must be set to a random value of at least 32 characters")

    SOURCE_DIR = os.getenv("SOURCE_DIR", "/tmp/file-mover/source")
    DESTINATION_DIR = os.getenv("DESTINATION_DIR", "/tmp/file-mover/destination")
    ALLOWED_EXTENSIONS = {
        item.strip().lower().lstrip(".")
        for item in os.getenv("ALLOWED_EXTENSIONS", "zip").split(",")
        if item.strip()
    }
    MAX_FILE_SIZE_BYTES = int(os.getenv("MAX_FILE_SIZE_BYTES", str(5 * 1024 * 1024 * 1024)))
    MAX_FILES_PER_MOVE = int(os.getenv("MAX_FILES_PER_MOVE", "200"))
    DEFAULT_FILES_PER_PAGE = int(os.getenv("DEFAULT_FILES_PER_PAGE", "20"))
    PAGE_SIZE_OPTIONS = tuple(int(v) for v in os.getenv("PAGE_SIZE_OPTIONS", "20,50,100,200").split(",") if v.strip().isdigit())
    MAX_FILES_PER_PAGE = min(int(os.getenv("MAX_FILES_PER_PAGE", "200")), 500)
    MAX_FILENAME_LENGTH = int(os.getenv("MAX_FILENAME_LENGTH", "255"))

    DATABASE_PATH = os.getenv("DATABASE_PATH", str(Path(__file__).resolve().parent / "runtime" / "file_mover.db"))
    SQLITE_BUSY_TIMEOUT_MS = min(max(int(os.getenv("SQLITE_BUSY_TIMEOUT_MS", "10000")), 1000), 60000)
    REPORT_DIR = os.getenv("REPORT_DIR", str(Path(__file__).resolve().parent / "runtime" / "reports"))
    BATCH_RETENTION_HOURS = min(max(int(os.getenv("BATCH_RETENTION_HOURS", "168")), 1), 2160)
    MAX_ACTIVE_BATCHES_PER_USER = min(max(int(os.getenv("MAX_ACTIVE_BATCHES_PER_USER", "3")), 1), 20)

    HISTORY_LIMIT = min(int(os.getenv("HISTORY_LIMIT", "200")), 1000)
    EXCEL_EXPORT_LIMIT = min(int(os.getenv("EXCEL_EXPORT_LIMIT", "5000")), 10000)

    LDAP_ENABLED = env_bool("LDAP_ENABLED", True)
    LDAP_SERVER = os.getenv("LDAP_SERVER", "ldaps://ldap.example.com:636")
    LDAP_USE_SSL = env_bool("LDAP_USE_SSL", True)
    LDAP_CA_CERT_FILE = os.getenv("LDAP_CA_CERT_FILE", "")
    LDAP_CONNECT_TIMEOUT = int(os.getenv("LDAP_CONNECT_TIMEOUT", "10"))
    LDAP_USER_DN_TEMPLATE = os.getenv("LDAP_USER_DN_TEMPLATE", "")
    LDAP_BIND_DN = os.getenv("LDAP_BIND_DN", "")
    LDAP_BIND_PASSWORD = os.getenv("LDAP_BIND_PASSWORD", "")
    LDAP_BASE_DN = os.getenv("LDAP_BASE_DN", "")
    LDAP_USER_FILTER = os.getenv("LDAP_USER_FILTER", "(sAMAccountName={username})")
    # Multiple group DNs use a semicolon delimiter because LDAP DNs contain commas.
    # LDAP_REQUIRED_GROUP_DN and LDAP_GROUP_REQUIRED remain supported for compatibility.
    _LDAP_GROUPS_RAW = (
        os.getenv("LDAP_GROUPS_REQUIRED", "").strip()
        or os.getenv("LDAP_REQUIRED_GROUP_DN", "").strip()
        or os.getenv("LDAP_GROUP_REQUIRED", "").strip()
    )
    LDAP_GROUPS_REQUIRED = tuple(
        group.strip() for group in _LDAP_GROUPS_RAW.split(";") if group.strip()
    )
    LDAP_GROUP_MATCH_MODE = os.getenv("LDAP_GROUP_MATCH_MODE", "ANY").strip().upper()
    LDAP_NESTED_GROUPS_ENABLED = env_bool("LDAP_NESTED_GROUPS_ENABLED", False)
    LDAP_GROUP_ATTRIBUTE = os.getenv("LDAP_GROUP_ATTRIBUTE", "memberOf").strip() or "memberOf"

    LDAP_EMAIL_ATTRIBUTE = os.getenv("LDAP_EMAIL_ATTRIBUTE", "mail")
    LDAP_EMAIL_TEMPLATE = os.getenv("LDAP_EMAIL_TEMPLATE", "")

    MAIL_ENABLED = env_bool("MAIL_ENABLED", True)
    SMTP_HOST = os.getenv("SMTP_HOST", "")
    SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
    SMTP_USERNAME = os.getenv("SMTP_USERNAME", "")
    SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")
    SMTP_USE_STARTTLS = env_bool("SMTP_USE_STARTTLS", True)
    SMTP_USE_SSL = env_bool("SMTP_USE_SSL", False)
    SMTP_TIMEOUT_SECONDS = int(os.getenv("SMTP_TIMEOUT_SECONDS", "20"))
    SMTP_CA_CERT_FILE = os.getenv("SMTP_CA_CERT_FILE", "")
    MAIL_FROM_ADDRESS = os.getenv("MAIL_FROM_ADDRESS", "")
    MAIL_FROM_NAME = os.getenv("MAIL_FROM_NAME", APP_NAME).strip() or APP_NAME
    DEV_EMAIL = os.getenv("DEV_EMAIL", "")

    DEV_USERNAME = os.getenv("DEV_USERNAME", "")
    DEV_PASSWORD = os.getenv("DEV_PASSWORD", "")

    SESSION_COOKIE_SECURE = env_bool("SESSION_COOKIE_SECURE", True)
    SESSION_COOKIE_NAME = "__Host-file_mover_session" if SESSION_COOKIE_SECURE else "file_mover_session"
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    PERMANENT_SESSION_LIFETIME = timedelta(minutes=int(os.getenv("SESSION_TIMEOUT_MINUTES", "30")))
    SESSION_REFRESH_EACH_REQUEST = True
    MAX_CONTENT_LENGTH = 256 * 1024
    WTF_CSRF_TIME_LIMIT = 3600
    WTF_CSRF_SSL_STRICT = True

    LOGIN_MAX_ATTEMPTS = int(os.getenv("LOGIN_MAX_ATTEMPTS", "5"))
    LOGIN_WINDOW_SECONDS = int(os.getenv("LOGIN_WINDOW_SECONDS", "300"))
    TRUSTED_PROXY_COUNT = min(max(int(os.getenv("TRUSTED_PROXY_COUNT", "0")), 0), 5)

    if MAX_FILES_PER_MOVE < 1 or MAX_FILES_PER_MOVE > 1000:
        raise RuntimeError("MAX_FILES_PER_MOVE must be between 1 and 1000")
    if MAX_FILE_SIZE_BYTES < 1:
        raise RuntimeError("MAX_FILE_SIZE_BYTES must be positive")
    if DEFAULT_FILES_PER_PAGE not in PAGE_SIZE_OPTIONS:
        raise RuntimeError("DEFAULT_FILES_PER_PAGE must be included in PAGE_SIZE_OPTIONS")
    if ALLOWED_EXTENSIONS != {"zip"}:
        raise RuntimeError("This utility is restricted to ZIP files; ALLOWED_EXTENSIONS must be zip")
    if LDAP_GROUP_MATCH_MODE not in {"ANY", "ALL"}:
        raise RuntimeError("LDAP_GROUP_MATCH_MODE must be ANY or ALL")
