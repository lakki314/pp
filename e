# Display name used across the UI, email subjects, Excel reports, and audit records
APP_NAME=File Mover Portal

SECRET_KEY=replace-with-at-least-32-random-characters
APP_HOST=127.0.0.1
APP_PORT=5000
FLASK_DEBUG=false

SOURCE_DIR=/opt/company/file-mover/incoming
DESTINATION_DIR=/opt/company/file-mover/processed
ALLOWED_EXTENSIONS=zip
MAX_FILE_SIZE_BYTES=5368709120
MAX_FILES_PER_MOVE=200
DEFAULT_FILES_PER_PAGE=20
PAGE_SIZE_OPTIONS=20,50,100,200
MAX_FILES_PER_PAGE=200
MAX_FILENAME_LENGTH=255

DATABASE_PATH=/var/lib/file-mover/file_mover.db
SQLITE_BUSY_TIMEOUT_MS=10000
HISTORY_LIMIT=200
EXCEL_EXPORT_LIMIT=5000

LDAP_ENABLED=true
LDAP_SERVER=ldaps://ldap.example.com:636
LDAP_USE_SSL=true
LDAP_CA_CERT_FILE=/etc/pki/ca-trust/source/anchors/company-root-ca.pem
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

# Local development only when LDAP_ENABLED=false.
DEV_USERNAME=admin
DEV_PASSWORD=replace-with-at-least-12-characters

# User email lookup. LDAP search mode reads this attribute.
LDAP_EMAIL_ATTRIBUTE=mail
# Optional fallback for simple-bind environments, for example {username}@example.com
LDAP_EMAIL_TEMPLATE=
DEV_EMAIL=developer@example.com

# Email delivery
MAIL_ENABLED=true
SMTP_HOST=smtp.example.com
SMTP_PORT=587
SMTP_USERNAME=
SMTP_PASSWORD=
SMTP_USE_STARTTLS=true
SMTP_USE_SSL=false
SMTP_TIMEOUT_SECONDS=20
SMTP_CA_CERT_FILE=/etc/pki/ca-trust/source/anchors/company-root-ca.pem
MAIL_FROM_ADDRESS=file-mover@example.com
MAIL_FROM_NAME=File Mover Portal

# Runtime state and generated Excel reports. Keep outside the web document root.
REPORT_DIR=/var/lib/file-mover/reports
BATCH_RETENTION_HOURS=168
MAX_ACTIVE_BATCHES_PER_USER=3
