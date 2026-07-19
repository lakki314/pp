# Display name used across the UI, email subjects, Excel reports, and audit records
APP_NAME=File Mover Portal

SECRET_KEY=replace-with-at-least-32-random-characters
APP_HOST=127.0.0.1
APP_PORT=5000
FLASK_DEBUG=false

SOURCE_DIR=data/incoming
DESTINATION_DIR=data/processed
ALLOWED_EXTENSIONS=zip
MAX_FILE_SIZE_BYTES=5368709120
MAX_FILES_PER_MOVE=200
DEFAULT_FILES_PER_PAGE=20
PAGE_SIZE_OPTIONS=20,50,100,200
MAX_FILES_PER_PAGE=200
MAX_FILENAME_LENGTH=255

DATABASE_PATH=data/file_mover.db
SQLITE_BUSY_TIMEOUT_MS=10000
HISTORY_LIMIT=200
EXCEL_EXPORT_LIMIT=5000

LDAP_SERVER=ldaps://ldap.example.com:636
LDAP_USE_SSL=true
LDAP_CA_CERT_FILE=certs/company-root-ca.pem
LDAP_CONNECT_TIMEOUT=10
LDAP_USER_DN_TEMPLATE=
LDAP_BIND_DN=CN=svc_filemover,OU=Service Accounts,DC=example,DC=com
LDAP_BIND_PASSWORD=retrieve-from-secret-manager
LDAP_BASE_DN=DC=example,DC=com
LDAP_USER_FILTER=(sAMAccountName={username})
# Separate multiple group DNs with semicolons because DNs themselves contain commas.
LDAP_GROUPS_REQUIRED=CN=FileMoverUsers,OU=Groups,DC=example,DC=com;CN=MiddlewareSupport,OU=Groups,DC=example,DC=com
# ANY allows membership in at least one configured group; ALL requires every group.
LDAP_GROUP_MATCH_MODE=ANY
# Active Directory only: recursively recognizes membership through nested groups.
LDAP_NESTED_GROUPS_ENABLED=false
LDAP_GROUP_ATTRIBUTE=memberOf

# Secure cookies require HTTPS at the reverse proxy.
SESSION_COOKIE_SECURE=true
SESSION_TIMEOUT_MINUTES=30
LOGIN_MAX_ATTEMPTS=5
LOGIN_WINDOW_SECONDS=300
# Set only when running behind this many trusted proxies.
TRUSTED_PROXY_COUNT=1


# User email lookup. LDAP search mode reads this attribute.
LDAP_EMAIL_ATTRIBUTE=mail
LDAP_DISPLAY_NAME_ATTRIBUTE=cn

# Email delivery
MAIL_ENABLED=true
SMTP_HOST=smtp.example.com
SMTP_PORT=25
SMTP_TIMEOUT_SECONDS=20
MAIL_FROM_ADDRESS=file-mover@example.com
MAIL_FROM_NAME=File Mover Portal

# Runtime state and generated Excel reports under the project directory.
REPORT_DIR=reports
BATCH_RETENTION_HOURS=168
MAX_ACTIVE_BATCHES_PER_USER=3
