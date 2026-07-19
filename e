###############################################################################
# Application
###############################################################################
APP_NAME=Middleware File Mover Portal
ENVIRONMENT=PROD
DEBUG=False
SECRET_KEY=<GENERATE_64_CHAR_SECRET>

###############################################################################
# Context Root
###############################################################################
# Deploy as:
# https://server/filemover
# Use "/" to deploy at the web server root.
APPLICATION_ROOT=/filemover

# Used when generating external URLs
PREFERRED_URL_SCHEME=https

###############################################################################
# Server
###############################################################################
APP_HOST=10.10.10.20
APP_PORT=8000

###############################################################################
# Gunicorn
###############################################################################
GUNICORN_WORKERS=4
GUNICORN_THREADS=4
GUNICORN_TIMEOUT=300

###############################################################################
# Reverse Proxy (IBM HTTP Server)
###############################################################################
TRUSTED_PROXY_IPS=10.10.10.15
TRUSTED_PROXY_COUNT=1

###############################################################################
# LDAP
###############################################################################
LDAP_SERVER=ldap.company.com
LDAP_PORT=636
LDAP_USE_SSL=True

LDAP_BIND_DN=cn=svc_filemover,ou=Service Accounts,dc=company,dc=com
LDAP_BIND_PASSWORD=<PASSWORD>

LDAP_BASE_DN=dc=company,dc=com
LDAP_USER_FILTER=(uid={username})

# Display name shown after login
LDAP_DISPLAY_NAME_ATTRIBUTE=cn

# Group authorization
LDAP_GROUP_BASE_DN=ou=Groups,dc=company,dc=com
LDAP_ALLOWED_GROUPS=MiddlewareAdmins,MiddlewareOperators
LDAP_GROUP_MATCH_MODE=ANY

###############################################################################
# SQLite
###############################################################################
DATABASE_PATH=data/file_mover.db

###############################################################################
# Directories
###############################################################################
SOURCE_DIRECTORY=/data/source
TARGET_DIRECTORY=/data/target

REPORT_DIRECTORY=reports
LOG_DIR=logs
BACKUP_DIR=backups
RUN_DIR=run

###############################################################################
# Reports / Cleanup
###############################################################################
REPORT_RETENTION_DAYS=30
BATCH_RETENTION_HOURS=72

###############################################################################
# Logging
###############################################################################
ACCESS_LOG=access.log
ERROR_LOG=error.log

LOG_MAX_BYTES=10485760
LOG_BACKUP_COUNT=10
LOG_RETENTION_DAYS=30

###############################################################################
# Upload Limits
###############################################################################
MAX_FILE_SIZE_BYTES=2147483648

###############################################################################
# SMTP Relay
###############################################################################
SMTP_HOST=smtp.company.com
SMTP_PORT=25

MAIL_FROM_NAME=Middleware File Mover
MAIL_FROM_ADDRESS=filemover@company.com

###############################################################################
# Session
###############################################################################
SESSION_TIMEOUT_MINUTES=30

SESSION_COOKIE_SECURE=True
SESSION_COOKIE_HTTPONLY=True
SESSION_COOKIE_SAMESITE=Lax

# Automatically determined by the application from APPLICATION_ROOT.
# Normally you do not need to change this.
# SESSION_COOKIE_PATH=/filemover

###############################################################################
# Branding
###############################################################################
COMPANY_NAME=Company Name
PORTAL_TITLE=Middleware File Mover Portal
FOOTER_TEXT=© Company Name
