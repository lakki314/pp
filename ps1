# =========================================================
# Middleware JVM Restart Portal - Full .env Sample
# Replace placeholder values before deploying.
# Do not commit real tokens/passwords/private keys to Git.
# =========================================================


# =========================================================
# Flask / runtime
# =========================================================
FLASK_HOST=0.0.0.0
FLASK_PORT=5000
FLASK_DEBUG=false

# Generate a real value with:
# python3 -c "import secrets; print(secrets.token_hex(32))"
APP_SECRET_KEY=change-this-long-random-secret

# true when users access the portal through HTTPS
SESSION_COOKIE_SECURE=true

# Public URL users use to access the portal. Used for SAML callback URL creation.
PORTAL_PUBLIC_URL=https://middleware-jvm-restart.example.com


# =========================================================
# Authentication mode
# local       = local testing only, any non-empty username/password
# ldap        = Flask username/password login + LDAP group check
# saml_header = SAML/front-door login + LDAP group check
# =========================================================
AUTH_MODE=saml_header


# =========================================================
# SAML front-door/header mode
# SAML authenticates the user before Flask.
# Flask receives the authenticated UID in SAML_USER_HEADER.
# =========================================================
SAML_ENABLED=true
SAML_LOGIN_URL=https://sso.example.com/saml/login
SAML_LOGOUT_URL=https://sso.example.com/saml/logout
SAML_REDIRECT_PARAM=redirect

# Header sent by SAML gateway/proxy to Flask.
# This value should contain UID, not email, unless LDAP_USER_FILTER is changed.
SAML_USER_HEADER=X-Remote-User
SAML_DISPLAY_NAME_HEADER=X-Remote-Display-Name
SAML_EMAIL_HEADER=X-Remote-Email

# Your requested SAML mapping
SAML_ID_MAP=local_realm
SAML_UNIQUE_ID_ATTRIBUTE=UID
SAML_PRINCIPAL_NAME_ATTRIBUTE=UID

# Optional cert paths for future direct Python SAML SP mode.
# Current header mode normally validates certs at the SAML gateway/proxy layer.
SAML_IDP_CERT_FILE=./certs/saml/idp-signing.crt
SAML_SP_CERT_FILE=./certs/saml/sp-signing.crt
SAML_SP_KEY_FILE=./certs/saml/sp-signing.key


# =========================================================
# LDAP SSL authorization
# Flask checks LDAP group membership after SAML authentication.
# =========================================================
LDAP_ENABLED=true
LDAP_SERVER_URI=ldaps://ldap.example.com:636
LDAP_REQUIRE_SSL=true

# Optional custom CA file for LDAPS if the LDAP server CA is not in OS trust.
LDAP_CA_CERT_FILE=./certs/ldap/ldap-ca.pem

LDAP_BIND_DN=CN=svc_ldap,OU=Service Accounts,DC=example,DC=com
LDAP_BIND_PASSWORD=replace-with-ldap-service-password
LDAP_USER_BASE_DN=OU=Users,DC=example,DC=com

# UID mapping. SAML_USER_HEADER value should match this uid value.
LDAP_USER_FILTER=(uid={username})
LDAP_UID_ATTRIBUTE=uid
LDAP_DISPLAY_NAME_ATTRIBUTE=cn

# Access group allowed to use the portal
LDAP_REQUIRED_GROUP_DN=CN=middleware-jvm-restart-users,OU=Groups,DC=example,DC=com
LDAP_GROUP_MEMBER_ATTRIBUTE=member


# =========================================================
# Non-prod Ansible Automation Controller / AWX
# Used for UNIT, INTG, PERF, QUAL, and other non-production environments.
# =========================================================
CONTROLLER_API_BASE=https://nonprod-controller.example.com/api/controller/v2
CONTROLLER_TOKEN=replace-with-nonprod-controller-oauth-token
CONTROLLER_VERIFY_SSL=true
CONTROLLER_CA_BUNDLE=./certs/controller/nonprod-controller-ca.pem
JOB_TEMPLATE_ID=123


# =========================================================
# Prod Ansible Automation Controller / AWX
# Used for TRAINING and PRODUCTION environments.
# =========================================================
PROD_CONTROLLER_API_BASE=https://prod-controller.example.com/api/controller/v2
PROD_CONTROLLER_TOKEN=replace-with-prod-controller-oauth-token
PROD_CONTROLLER_VERIFY_SSL=true
PROD_CONTROLLER_CA_BUNDLE=./certs/controller/prod-controller-ca.pem
PROD_JOB_TEMPLATE_ID=456

# HTTP timeout in seconds for Controller/API calls
HTTP_TIMEOUT=30


# =========================================================
# Job launch payload behavior
# =========================================================
AUTO_LIMIT_FROM_JVMS=false
PAYLOAD_VAR_NAME=jvm_restart
RITM_NUMBER=RITMTEST
PORTAL_REQUESTED_BY=middleware-portal


# =========================================================
# Production environment visibility
# false = hide TRAINING and PRODUCTION from the portal
# true  = show TRAINING and PRODUCTION in the environment dropdown
# =========================================================
PROD_ENVIRONMENTS_ENABLED=false


# =========================================================
# JVM inventory source
# excel = read data/jvm_inventory.xlsx
# api   = call JVM_RESOURCE_URL?env=<env>
# json  = legacy local data/jvms.json fallback
# =========================================================
JVM_SOURCE_MODE=excel
JVM_INVENTORY_FILE=./data/jvm_inventory.xlsx

# Non-prod JVM resource API, used only when JVM_SOURCE_MODE=api
JVM_RESOURCE_URL=https://nonprod-inventory-resource.example.com/api/jvms
JVM_RESOURCE_TOKEN=
JVM_RESOURCE_VERIFY_SSL=true

# Prod JVM resource API, used for TRAINING/PRODUCTION when JVM_SOURCE_MODE=api
PROD_JVM_RESOURCE_URL=https://prod-inventory-resource.example.com/api/jvms
PROD_JVM_RESOURCE_TOKEN=
PROD_JVM_RESOURCE_VERIFY_SSL=true


# =========================================================
# Job history
# =========================================================
HISTORY_DB_PATH=./history.sqlite3
HISTORY_LIMIT=50


# =========================================================
# Gunicorn runtime values used by scripts/start_with_vendor.sh
# These can also be exported in the shell before starting.
# =========================================================
GUNICORN_BIND=127.0.0.1:5000
GUNICORN_WORKERS=3
GUNICORN_LOG_LEVEL=info
GUNICORN_ACCESS_LOG=./logs/gunicorn_access.log
GUNICORN_ERROR_LOG=./logs/gunicorn_error.log
