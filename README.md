# Middleware JVM Restart Portal

A Flask + HTML/CSS/JavaScript portal for launching an Ansible Automation Controller / AWX job template to restart selected JVMs.

## Current recommended deployment

Because `mod_wsgi` is not installed, use this deployment model:

```text
Apache HTTPD serves static UI content.
Gunicorn runs Flask backend on 127.0.0.1:5000.
Apache reverse-proxies /login, /logout, /api/*, /health, and /static/* to Gunicorn.
SAML authentication can be handled by your SSO/front-door layer, and Flask then checks LDAP group authorization before allowing portal access. LDAP username/password mode is still available.
Python modules are bundled in vendor/site-packages, so the target server does not need pip install.
```

## Project layout

```text
middleware_jvm_restart_portal/
├── app.py
├── wsgi.py                              # optional mod_wsgi entry point
├── requirements.txt
├── .env.example
├── README.md
├── apache/
│   ├── middleware-jvm-restart-proxy.conf # recommended when mod_wsgi is not installed
│   └── middleware-jvm-restart.conf       # optional mod_wsgi example
├── systemd/
│   └── middleware-jvm-restart.service    # Gunicorn backend service example
├── data/
│   ├── jvm_inventory.xlsx
│   └── jvms.json
├── static/
│   ├── css/style.css
│   └── js/app.js
├── templates/
│   ├── index.html
│   └── login.html
├── ui/
│   ├── index.html
│   ├── css/style.css
│   └── js/app.js
├── vendor/
│   └── site-packages/
└── scripts/
    ├── run_with_vendor.sh
    └── build_vendor_bundle.sh
```

Use `ui/` for Apache static content.

Flask uses `templates/` and `static/` for the login page and backend-served assets.

## Runtime flow

```text
User opens https://middleware-jvm-restart.example.com/
        |
        v
Apache serves /opt/middleware-jvm-restart/ui/index.html
        |
        v
JavaScript calls /api/session
        |
        v
Apache proxies /api/session to Gunicorn on 127.0.0.1:5000
        |
        v
If not logged in, UI redirects to /login
        |
        v
Apache proxies /login to Flask
        |
        v
If AUTH_MODE=saml_header, Flask redirects to SAML login and reads the authenticated user header on callback
        |
        v
Flask checks LDAP group membership and creates a session cookie
        |
        v
User returns to Apache static UI
        |
        v
Static UI calls protected Flask APIs under /api/*
```

## No-pip / bundled modules mode

This ZIP includes Python dependencies under:

```text
vendor/site-packages
```

`app.py` and `wsgi.py` automatically add this folder to `sys.path` before importing Flask, requests, ldap3, openpyxl, and other packages.

The vendored dependency folder was prepared for:

```text
Python 3.11.x on Linux x86_64 / manylinux-compatible systems
```

Your target Python version is expected to be:

```text
Python 3.11.13
```

No target-server pip install is required.

If your target server is not Python 3.11.x on Linux x86_64, rebuild the vendor folder on a matching build server that has pip/internal PyPI access:

```bash
cd middleware_jvm_restart_portal
./scripts/build_vendor_bundle.sh
```

Then zip the project and move it to the locked-down server.


## Build offline vendor folder from Windows

If you have pip only on your local Windows machine, use this script:

```text
scripts/build_offline_vendor_windows.ps1
```

Run from PowerShell on Windows:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\build_offline_vendor_windows.ps1
```

The script uses the `python` command by default and does not call `py`. If Python is installed but not on PATH, pass the full Python path:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\build_offline_vendor_windows.ps1 -PythonExe "C:\Path\To\python.exe"
```

The script downloads Python 3.11 Linux x86_64 compatible wheels and extracts them into:

```text
vendor\site-packages
```

It also creates:

```text
offline_vendor_py311_linux_x86_64.zip
```

Copy the generated `vendor` folder to the server under:

```text
/opt/middleware-jvm-restart/app/vendor/site-packages
```

This is useful when the Linux server cannot run `pip install`.

## Install OS packages

For the recommended Apache reverse-proxy setup, you need Apache, SSL support, Python 3.11, and Apache proxy modules.

Example RHEL/Linux package names vary by environment, but usually you need:

```bash
sudo yum install -y httpd mod_ssl python3
```

Check whether the proxy modules are already available:

```bash
httpd -M | egrep -i "proxy|proxy_http|rewrite"
```

Expected modules:

```text
proxy_module
proxy_http_module
```

`rewrite_module` is useful but not required for the sample proxy config.

If proxy modules are not loaded, ask the webserver team to enable/install:

```text
mod_proxy
mod_proxy_http
```

You do **not** need `mod_wsgi` for the recommended proxy setup.

## Install application files

Target layout:

```text
/opt/middleware-jvm-restart/
├── app/
└── ui/
```

Copy files:

```bash
sudo mkdir -p /opt/middleware-jvm-restart/app
sudo mkdir -p /opt/middleware-jvm-restart/ui

sudo cp -r app.py wsgi.py requirements.txt .env.example data templates static scripts vendor logs /opt/middleware-jvm-restart/app/
sudo cp -r ui/* /opt/middleware-jvm-restart/ui/
```

No pip install is needed on the target server.

## Configure `.env`

```bash
sudo cp /opt/middleware-jvm-restart/app/.env.example /opt/middleware-jvm-restart/app/.env
sudo vi /opt/middleware-jvm-restart/app/.env
```

Minimum values for SAML/front-door authentication with LDAP authorization and separate non-prod/prod Controller configs:

```bash
PORTAL_PUBLIC_URL=https://middleware-jvm-restart.example.com
APP_SECRET_KEY=change-this-long-random-value
SESSION_COOKIE_SECURE=true

AUTH_MODE=saml_header
SAML_ENABLED=true
SAML_LOGIN_URL=https://sso.example.com/saml/login
SAML_LOGOUT_URL=https://sso.example.com/saml/logout
SAML_REDIRECT_PARAM=redirect
SAML_USER_HEADER=X-Remote-User
SAML_DISPLAY_NAME_HEADER=X-Remote-Display-Name

LDAP_ENABLED=true
LDAP_SERVER_URI=ldaps://ldap.example.com:636
LDAP_BIND_DN=CN=svc_ldap,OU=Service Accounts,DC=example,DC=com
LDAP_BIND_PASSWORD=<service-account-password>
LDAP_USER_BASE_DN=OU=Users,DC=example,DC=com
LDAP_USER_FILTER=(sAMAccountName={username})
LDAP_REQUIRED_GROUP_DN=CN=middleware-jvm-restart-users,OU=Groups,DC=example,DC=com
LDAP_GROUP_MEMBER_ATTRIBUTE=member
LDAP_DISPLAY_NAME_ATTRIBUTE=cn

# Non-prod Controller, used for UNIT/INTG/PERF/QUAL
CONTROLLER_API_BASE=https://nonprod-controller.example.com/api/controller/v2
CONTROLLER_TOKEN=<nonprod-controller-oauth-token>
CONTROLLER_VERIFY_SSL=true
JOB_TEMPLATE_ID=123

# Prod Controller, used for TRAINING/PRODUCTION
PROD_CONTROLLER_API_BASE=https://prod-controller.example.com/api/controller/v2
PROD_CONTROLLER_TOKEN=<prod-controller-oauth-token>
PROD_CONTROLLER_VERIFY_SSL=true
PROD_JOB_TEMPLATE_ID=456

JVM_SOURCE_MODE=excel
JVM_INVENTORY_FILE=./data/jvm_inventory.xlsx

PAYLOAD_VAR_NAME=jvm_restart
RITM_NUMBER=RITMTEST
AUTO_LIMIT_FROM_JVMS=false
PROD_ENVIRONMENTS_ENABLED=false

HISTORY_DB_PATH=./history.sqlite3
HISTORY_LIMIT=50
```

For local HTTP-only testing, use:

```bash
AUTH_MODE=local
LDAP_ENABLED=false
SAML_ENABLED=false
SESSION_COOKIE_SECURE=false
```

## SAML plus LDAP authorization mode

This portal supports SAML in header/front-door mode. The application does not parse raw SAML XML assertions. Your enterprise SSO layer, Apache module, reverse proxy, or gateway performs SAML authentication first and passes the authenticated user to Flask in a configured header such as `X-Remote-User` or `REMOTE_USER`.

Then Flask performs the LDAP lookup and validates the user is a member of `LDAP_REQUIRED_GROUP_DN`. If the LDAP group check passes, Flask creates the portal session.

Important variables:

```bash
AUTH_MODE=saml_header
SAML_ENABLED=true
SAML_LOGIN_URL=https://sso.example.com/saml/login
SAML_LOGOUT_URL=https://sso.example.com/saml/logout
SAML_REDIRECT_PARAM=redirect
SAML_USER_HEADER=X-Remote-User
PORTAL_PUBLIC_URL=https://middleware-jvm-restart.example.com
LDAP_REQUIRED_GROUP_DN=CN=middleware-jvm-restart-users,OU=Groups,DC=example,DC=com
```

If your SSO product expects a different redirect parameter, change `SAML_REDIRECT_PARAM`. Common values are `redirect`, `RelayState`, or `returnTo`.

## Separate non-prod and prod Controller configs

The portal routes restart launches based on the selected environment:

```text
UNIT / INTG / PERF / QUAL -> non-prod Controller config
TRAINING / PRODUCTION     -> prod Controller config
```

Do not mix production/training JVMs and non-production JVMs in the same restart request. The portal rejects mixed requests because they belong to different Controller profiles.

Non-prod variables:

```bash
CONTROLLER_API_BASE=https://nonprod-controller.example.com/api/controller/v2
CONTROLLER_TOKEN=<nonprod-controller-oauth-token>
JOB_TEMPLATE_ID=123
```

Prod variables:

```bash
PROD_CONTROLLER_API_BASE=https://prod-controller.example.com/api/controller/v2
PROD_CONTROLLER_TOKEN=<prod-controller-oauth-token>
PROD_JOB_TEMPLATE_ID=456
```


### Disable SSO/SAML

To disable SSO, do not only set `SAML_ENABLED=false`. Also set `AUTH_MODE` to the mode you want:

```bash
# LDAP username/password login
AUTH_MODE=ldap
SAML_ENABLED=false
LDAP_ENABLED=true
```

For local testing:

```bash
AUTH_MODE=local
SAML_ENABLED=false
LDAP_ENABLED=false
SESSION_COOKIE_SECURE=false
```

After changing `.env`, restart the portal and clear the browser session by opening `/logout` once.


### Disable all login/authentication for local testing

`LDAP_ENABLED=false` only disables LDAP validation. It does not bypass the login page by itself. To remove the login page completely for local testing, use:

```bash
AUTH_REQUIRED=false
AUTH_MODE=local
SAML_ENABLED=false
LDAP_ENABLED=false
SESSION_COOKIE_SECURE=false
AUTH_DISABLED_USERNAME=local-dev-user
AUTH_DISABLED_DISPLAY_NAME=Local Development User
```

Restart the portal after changing `.env`.

## Gunicorn backend without systemd

For your setup, where you do not have `systemd` and you run the application as a non-root user, use the included start/stop scripts.

Run these commands as the application owner, not root. Example application user: `appuser`.

```bash
cd /opt/middleware-jvm-restart/app
./scripts/start_with_vendor.sh
```

This starts Gunicorn in the background on localhost:

```text
127.0.0.1:5000
```

The scripts create and use this log directory automatically:

```text
/opt/middleware-jvm-restart/app/logs
```

Generated backend logs:

```text
logs/gunicorn_access.log
logs/gunicorn_error.log
logs/middleware-jvm-restart.out
logs/middleware-jvm-restart.pid
```

Check status:

```bash
cat logs/middleware-jvm-restart.pid
ps -ef | grep gunicorn | grep -v grep
```

Tail logs:

```bash
tail -f logs/gunicorn_error.log
tail -f logs/gunicorn_access.log
```

Stop the backend:

```bash
cd /opt/middleware-jvm-restart/app
./scripts/stop_with_vendor.sh
```

Restart the backend:

```bash
cd /opt/middleware-jvm-restart/app
./scripts/stop_with_vendor.sh
./scripts/start_with_vendor.sh
```

The default bind address is `127.0.0.1:5000`. To override it:

```bash
GUNICORN_BIND=127.0.0.1:5050 ./scripts/start_with_vendor.sh
```

If you change the port, update the Apache `ProxyPass` entries to match.

Test locally on the webserver:

```bash
curl http://127.0.0.1:5000/health
```

Expected:

```json
{"service":"middleware-jvm-restart","status":"ok"}
```

## Optional systemd service

If you later get access to systemd, a sample service is still included:

```text
systemd/middleware-jvm-restart.service
```

For now, use the no-systemd scripts above.

## Apache reverse-proxy configuration

Use this included file:

```text
apache/middleware-jvm-restart-proxy.conf
```

Copy it:

```bash
sudo cp apache/middleware-jvm-restart-proxy.conf /etc/httpd/conf.d/middleware-jvm-restart.conf
sudo vi /etc/httpd/conf.d/middleware-jvm-restart.conf
```

Apache does **not** handle LDAP. Do not add Apache LDAP directives such as:

```apache
AuthType Basic
AuthBasicProvider ldap
Require ldap-group ...
```

Core proxy config:

```apache
<VirtualHost *:443>
    ServerName middleware-jvm-restart.example.com

    SSLEngine on
    SSLCertificateFile /etc/pki/tls/certs/middleware-jvm-restart.crt
    SSLCertificateKeyFile /etc/pki/tls/private/middleware-jvm-restart.key

    ErrorLog logs/middleware-jvm-restart_error.log
    CustomLog logs/middleware-jvm-restart_access.log combined

    DocumentRoot /opt/middleware-jvm-restart/ui
    DirectoryIndex index.html

    <Directory "/opt/middleware-jvm-restart/ui">
        Options -Indexes +FollowSymLinks
        AllowOverride None
        Require all granted
    </Directory>

    ProxyPreserveHost On
    ProxyRequests Off

    ProxyPass        /login  http://127.0.0.1:5000/login
    ProxyPassReverse /login  http://127.0.0.1:5000/login

    ProxyPass        /logout http://127.0.0.1:5000/logout
    ProxyPassReverse /logout http://127.0.0.1:5000/logout

    ProxyPass        /api/   http://127.0.0.1:5000/api/
    ProxyPassReverse /api/   http://127.0.0.1:5000/api/

    ProxyPass        /health http://127.0.0.1:5000/health
    ProxyPassReverse /health http://127.0.0.1:5000/health

    ProxyPass        /static/ http://127.0.0.1:5000/static/
    ProxyPassReverse /static/ http://127.0.0.1:5000/static/
</VirtualHost>
```

Validate and restart Apache:

```bash
sudo apachectl configtest
sudo systemctl restart httpd
sudo systemctl status httpd
```

## Permissions

```bash
# Example: app backend runs as appuser; Apache only needs to read ui/
sudo chown -R appuser:appuser /opt/middleware-jvm-restart/app
sudo chmod -R 750 /opt/middleware-jvm-restart/app
sudo chmod 640 /opt/middleware-jvm-restart/app/.env

sudo chown -R apache:apache /opt/middleware-jvm-restart/ui
sudo chmod -R 755 /opt/middleware-jvm-restart/ui

# appuser must be able to write logs and SQLite history
sudo chmod 750 /opt/middleware-jvm-restart/app/logs
sudo chmod 750 /opt/middleware-jvm-restart/app/data
```

Make sure the application user can read:

```text
/opt/middleware-jvm-restart/app/data/jvm_inventory.xlsx
```

Make sure the application user can write:

```text
/opt/middleware-jvm-restart/app/data/history.sqlite3
```

## Test URLs

Open the portal:

```text
https://middleware-jvm-restart.example.com/
```

Health check through Apache:

```bash
curl -k https://middleware-jvm-restart.example.com/health
```

Session check before login:

```bash
curl -k https://middleware-jvm-restart.example.com/api/session
```

Expected before login:

```json
{"error":"Authentication required"}
```

After browser login through `/login`, the static UI should be able to call:

```text
/api/session
/api/environments
/api/jvms?env=UNIT
/api/restart
/api/history
/api/active-jobs
```

## Excel inventory format

The default source is:

```bash
JVM_SOURCE_MODE=excel
JVM_INVENTORY_FILE=./data/jvm_inventory.xlsx
```

Required columns:

```text
ENVIRONMENT | JVM_NAME | UNIX_HOST
```

Example rows:

```text
ENVIRONMENT | JVM_NAME       | UNIX_HOST
UNIT        | test_jvm       | test_hostname
INTG        | claims_server1 | intg-host01.example.com
TRAINING    | training_jvm1  | training-host01.example.com
PRODUCTION  | prod_jvm1      | prod-host01.example.com
```

The dropdown displays:

```text
JVM_NAME | UNIX_HOST | ENVIRONMENT
```

## Production environment visibility

`TRAINING` and `PRODUCTION` remain separate values.

When this is false:

```bash
PROD_ENVIRONMENTS_ENABLED=false
```

`TRAINING` and `PRODUCTION` are hidden from the dropdown and blocked from `/api/jvms`.

When this is true:

```bash
PROD_ENVIRONMENTS_ENABLED=true
```

Both are visible as separate dropdown values.

## Launch payload

Example payload sent to Controller:

```json
{
  "extra_vars": {
    "jvm_restart": {
      "ritm_number": "RITMTEST",
      "env": {
        "UNIT": {
          "hosts": {
            "test_hostname": "test_jvm"
          }
        }
      }
    }
  }
}
```

When `TRAINING` and `PRODUCTION` are enabled and selected, they remain separate:

```yaml
jvm_restart:
  ritm_number: RITMTEST
  env:
    TRAINING:
      hosts:
        training-host01.example.com: training_jvm1
    PRODUCTION:
      hosts:
        prod-host01.example.com: prod_jvm1
```

## Optional standalone mode without Apache

You can run the portal without Apache:

```bash
cd /opt/middleware-jvm-restart/app
./scripts/run_with_vendor.sh
```

Then access:

```text
http://server-name:5000
```

This starts Gunicorn directly and serves the Flask app from port `5000`.

## Optional mod_wsgi mode

A mod_wsgi sample remains available:

```text
apache/middleware-jvm-restart.conf
```

Use it only if `mod_wsgi` is installed and compiled for Python 3.11.

The recommended setup for your current server is the reverse-proxy setup because `mod_wsgi` is not installed.
