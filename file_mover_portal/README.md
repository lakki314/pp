# Secure File Mover Portal

A small internal support utility built with Flask and Python 3.9 or Python 3.11. It allows an authenticated user to search and select ZIP files from a fixed source directory, move them to a fixed target directory on the same filesystem, verify the result, follow live progress, and receive an Excel report by email.

The application intentionally does not include a system-health page or public health-check endpoint.

### Sortable file tables

The Move Files and Verify Files tables support server-side sorting across the complete matching result set. Click **ZIP file name**, **Size**, or **Last modified** to toggle ascending and descending order. Search, page size, pagination, directory selection, and the configured context root are preserved.


## Features

- LDAP/Active Directory authentication over certificate-validated LDAPS.
- Optional LDAP-group authorization.
- ZIP-only source listing and backend validation.
- Server-side filename search.
- Pagination with a default of 20 rows and configurable page sizes.
- Selection persistence across search, pagination, and page-size changes.
- Move confirmation dialog.
- Actual per-file move progress and batch completion summary.
- Read-only verification of source and target directories.
- Same-filesystem moves without copying file contents.
- Existing target files are never overwritten.
- SQLite-backed audit records, batch state, file-level results, and login-rate-limit data.
- Excel batch report generation and authenticated report download.
- Optional email delivery of the Excel report to the logged-in user.
- Secure session cookies, CSRF protection, security headers, and login throttling.
- Gunicorn start, stop, restart, and status scripts.
- AIX-compatible operational scripts; an optional Linux systemd example is isolated under `examples/linux/`.

## Supported runtime

- Python 3.9.23 or Python 3.11.13
- Linux or another Unix-like operating system
- Source and target directories on the same mounted filesystem
- Gunicorn for production execution

The shell scripts use Bash and standard Unix process signals.

## Project structure

```text
file_mover_portal/
├── app.py
├── config.py
├── requirements.txt
├── .env.example
├── .python-version
├── backups/
├── scripts/
│   ├── start.sh
│   ├── stop.sh
│   ├── restart.sh
│   └── status.sh
├── services/
│   ├── audit_service.py
│   ├── batch_service.py
│   ├── email_service.py
│   ├── excel_service.py
│   ├── file_service.py
│   ├── ldap_service.py
│   └── rate_limit_service.py
├── templates/
│   ├── _pagination.html
│   ├── base.html
│   ├── history.html
│   ├── index.html
│   ├── login.html
│   └── verify.html
└── static/
    ├── app.js
    └── styles.css
```


### Application display name

Set the portal name once in `.env`:

```dotenv
APP_NAME=File Mover Portal
```

After restarting the application, this value is used in the browser title, navigation header, login and page titles, email subjects, Excel report headings, and new audit records. Existing audit entries and previously generated reports are not rewritten. `MAIL_FROM_NAME` remains independently configurable; when it is omitted, it defaults to `APP_NAME`.

## Application workflow

1. The user signs in with corporate LDAP credentials.
2. The portal lists ZIP files from the configured source directory.
3. The user searches, pages through results, and selects files.
4. Selections are retained in browser session storage while the tab remains open.
5. The user confirms the move.
6. The backend creates a unique batch and processes files individually.
7. The page displays the current file, completed count, moved count, failed count, and elapsed time.
8. On completion, the backend generates an Excel report, optionally emails it, and writes one compact audit database entry.
9. The user can verify the source and target directories from the read-only Verify Files page.

## Filesystem behavior

The source and target directories must be on the same filesystem. The application verifies this during startup.

A move uses a hard-link-and-unlink operation:

1. Create the target hard link with exclusive semantics.
2. Remove the source directory entry.

This avoids copying ZIP contents and refuses to overwrite an existing target filename. Every file is revalidated immediately before movement.

The service account needs:

- read and directory traversal access to the source;
- create and delete permission in the source;
- create permission in the target;
- write permission for logs, batch state, and generated reports.

## Installation

### 1. Extract and position the project

Example production location:

```bash
sudo mkdir -p /opt/file_mover_portal
sudo unzip file_mover_portal.zip -d /opt
sudo chown -R filemover:filemover /opt/file_mover_portal
```

Adjust the extraction command if the archive already contains the `file_mover_portal` directory.

### 2. Create required directories

```bash
sudo mkdir -p /data/file-mover/incoming
sudo mkdir -p /data/file-mover/processed
sudo mkdir -p /var/log/file-mover
sudo mkdir -p /var/lib/file-mover/batches
sudo mkdir -p reports

sudo chown -R filemover:filemover \
  /data/file-mover \
  /var/log/file-mover \
  /var/lib/file-mover
```

Confirm source and target are on the same filesystem:

```bash
df -P /data/file-mover/incoming /data/file-mover/processed
```

The filesystem/device shown for both paths must be the same.

### 3. Create the Python environment

```bash
cd /opt/file_mover_portal
python3.10 -m venv .venv
. .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
python -m compileall app.py config.py services
```

### 4. Configure `.env`

```bash
cp .env.example .env
chmod 600 .env
```

Generate a secret key:

```bash
python3.10 -c "import secrets; print(secrets.token_urlsafe(48))"
```

Set the output as `SECRET_KEY`.

## Important `.env` settings

### Core paths

```dotenv
SECRET_KEY=replace-with-a-random-secret-of-at-least-32-characters

SOURCE_DIR=/data/file-mover/incoming
DESTINATION_DIR=/data/file-mover/processed
ALLOWED_EXTENSIONS=zip

DATABASE_PATH=data/file_mover.db
SQLITE_BUSY_TIMEOUT_MS=10000
REPORT_DIR=reports
```

Do not place batch state or reports inside the Flask static directory.

### File and page limits

```dotenv
MAX_FILES_PER_MOVE=200
MAX_FILE_SIZE_BYTES=10737418240
MAX_FILENAME_LENGTH=255

DEFAULT_FILES_PER_PAGE=20
PAGE_SIZE_OPTIONS=20,50,100,200
MAX_FILES_PER_PAGE=200
```

The browser limit is only a user-interface convenience. The backend always enforces `MAX_FILES_PER_MOVE`.

### Session and proxy settings

```dotenv
SESSION_COOKIE_SECURE=true
SESSION_TIMEOUT_MINUTES=30
TRUSTED_PROXY_COUNT=1
```

Set `SESSION_COOKIE_SECURE=false` only for temporary HTTP testing. Production access should use HTTPS.

Set `TRUSTED_PROXY_COUNT` to the exact number of trusted reverse proxies in front of Gunicorn. Use `0` when Gunicorn is accessed directly during local testing.

### LDAP search-and-bind example

```dotenv
LDAP_SERVER=ldaps://ldap.example.com:636
LDAP_USE_SSL=true
LDAP_CA_CERT_FILE=certs/company-root-ca.pem
LDAP_CONNECT_TIMEOUT=10

LDAP_BIND_DN=CN=svc_filemover,OU=Service Accounts,DC=example,DC=com
LDAP_BIND_PASSWORD=retrieve-from-secret-manager
LDAP_BASE_DN=DC=example,DC=com
LDAP_USER_FILTER=(sAMAccountName={username})
LDAP_GROUPS_REQUIRED=CN=FileMoverUsers,OU=Groups,DC=example,DC=com;CN=MiddlewareSupport,OU=Groups,DC=example,DC=com
LDAP_GROUP_MATCH_MODE=ANY
LDAP_NESTED_GROUPS_ENABLED=false
LDAP_GROUP_ATTRIBUTE=memberOf
LDAP_EMAIL_ATTRIBUTE=mail
LDAP_DISPLAY_NAME_ATTRIBUTE=cn

`LDAP_DISPLAY_NAME_ATTRIBUTE` controls the LDAP attribute shown in the portal after login. The default is `cn`; the login username remains the internal batch and audit owner.
```

`LDAP_GROUPS_REQUIRED` accepts one or more full group DNs separated by semicolons. Do not use commas as separators because commas are part of an LDAP DN. `LDAP_GROUP_MATCH_MODE=ANY` allows a user who belongs to at least one listed group; `ALL` requires membership in every listed group.

For Microsoft Active Directory nested groups, set `LDAP_NESTED_GROUPS_ENABLED=true`. This uses the AD recursive matching rule `1.2.840.113556.1.4.1941`. Leave it `false` for non-AD LDAP servers or when only direct `memberOf` values should be accepted.

The previous `LDAP_REQUIRED_GROUP_DN` and `LDAP_GROUP_REQUIRED` single-group names remain supported as fallbacks, but new deployments should use `LDAP_GROUPS_REQUIRED`.

The LDAP service password should be supplied through CyberArk, Vault, or another approved secret-management mechanism where possible.

### LDAP simple-bind example

```dotenv
LDAP_USER_DN_TEMPLATE=CN={username},OU=Users,DC=example,DC=com
```

Use the email template only when the username-to-email mapping is controlled and predictable.

### Local development authentication

```dotenv
```

Never use development authentication in production.

### Email settings

```dotenv
MAIL_ENABLED=true
SMTP_HOST=smtp.example.com
SMTP_PORT=25
SMTP_TIMEOUT_SECONDS=20


MAIL_FROM_ADDRESS=file-mover@example.com
MAIL_FROM_NAME=File Mover Portal
```

The portal uses an unauthenticated internal SMTP relay on the configured host and port. TLS and SMTP authentication are not used.

## Start and stop scripts

Scripts are located under `scripts/` and are intended to run as the application service account.

Set permissions once after installation:

```bash
chmod 750 scripts/*.sh
```

### Start

```bash
cd /opt/file_mover_portal
./scripts/start.sh
```

The script:

- verifies that `.env` exists;
- verifies that Gunicorn exists in `.venv`;
- creates `run/` and `logs/` when needed;
- refuses to start a duplicate process;
- removes a stale PID file;
- starts Gunicorn in daemon mode;
- records the master PID in `run/file-mover.pid`;
- writes Gunicorn access and error logs under `logs/`.

### Status

```bash
./scripts/status.sh
```

Exit codes:

- `0`: running;
- `1`: stale or invalid process state;
- `3`: stopped and no PID file exists.

### Stop

```bash
./scripts/stop.sh
```

The script sends `SIGTERM` and waits up to 30 seconds for a graceful shutdown. If the process remains active, it sends `SIGKILL` and removes the PID file.

Override the timeout when necessary:

```bash
STOP_TIMEOUT=60 ./scripts/stop.sh
```

### Restart

```bash
./scripts/restart.sh
```

### Runtime configuration

Production Gunicorn settings are read from `.env` by `scripts/start.sh`:

```dotenv
APP_HOST=10.20.30.40
APP_PORT=8000
TRUSTED_PROXY_IPS=10.20.30.25
TRUSTED_PROXY_COUNT=1
GUNICORN_WORKERS=3
GUNICORN_THREADS=4
GUNICORN_TIMEOUT=120
LOG_DIR=logs
ACCESS_LOG=logs/gunicorn-access.log
ERROR_LOG=logs/gunicorn-error.log
```

`APP_DIR`, `VENV_DIR`, `RUN_DIR`, and `PID_FILE` may still be supplied as shell environment overrides when invoking the operational scripts.

## Linux-only systemd example

A sample systemd definition is isolated under `examples/linux/`. It is not used on AIX. Linux administrators must review its user, paths, and security controls before installation.

## Reverse proxy

Because IBM HTTP Server is on a separate host, bind Gunicorn to the Python server internal IP and expose the application only through the trusted reverse proxy.

The reverse proxy should:

- terminate HTTPS;
- forward the original host and protocol headers;
- apply organization-standard TLS configuration;
- limit request body size;
- restrict access to the intended network;
- avoid caching authenticated pages.

The default standalone script binds to:

```text
127.0.0.1:5000
```

## Move progress endpoints

The browser uses authenticated and CSRF-protected backend endpoints:

- `POST /api/move/start` — creates the server-side batch.
- `POST /api/move/file` — processes one validated ZIP file.
- `POST /api/move/complete` — finalizes the batch, generates Excel, sends email, and writes the audit summary.

These endpoints are not intended as an unauthenticated public API.

## Selection behavior

Selections are stored in browser `sessionStorage`, scoped to the authenticated user. They remain selected when the user:

- searches;
- changes result pages;
- changes page size.

Selections are cleared when:

- the batch completes;
- the user clicks Clear Selection;
- the browser tab is closed.

Before moving, the backend independently validates every submitted filename and does not trust browser storage.

## Verify Files page

The Verify Files page is read-only and includes:

- Source view: ZIP files still waiting to be moved.
- Target view: ZIP files already present in the target.
- Independent search and pagination.

It does not move, delete, rename, or download files.

## Audit logging

The portal stores audit events in the SQLite database configured by `DATABASE_PATH`.

For a move operation, the application writes one compact batch summary instead of one line per file. The detailed file results are retained in the Excel report.

Example conceptually:

```json
{
  "timestamp": "2026-07-17T21:30:00+00:00",
  "username": "user1",
  "action": "MOVE_BATCH",
  "details": "batch_id=MOVE-...; requested=100; moved=99; failed=1; email=SENT",
  "remote_addr": "10.10.1.25"
}
```

Audit history is retained in SQLite. Back up the database and export or forward audit events according to enterprise retention and compliance policy.

## Excel reports

The completion workbook includes:

- batch ID;
- user and email;
- start and completion times;
- requested, moved, and failed totals;
- filename, size, result, and failure reason.

The workbook is generated without temporary public files. Formula-like text is escaped, and automatic URL/formula conversion is disabled to reduce spreadsheet-injection risk.

Generated reports are downloadable only by an authenticated user through the application route.

## Failure behavior

A single file failure does not stop the rest of the batch. Typical failures include:

- source file no longer exists;
- target filename already exists;
- permission denied;
- invalid filename;
- symbolic link rejected;
- non-ZIP file rejected.

The completion page and Excel report show successful and failed counts and failure reasons.

If email fails after files have moved, the file move is not rolled back. The completion page and audit record show the email failure, and the user can still download the Excel report.

## Security controls

The application includes:

- mandatory strong secret-key validation;
- secure, HttpOnly, SameSite session cookies;
- configurable session expiration;
- CSRF protection for state-changing requests;
- LDAPS requirement and LDAP certificate validation;
- login-attempt throttling;
- LDAP-group authorization;
- filename length and character validation;
- path traversal and absolute-path rejection;
- symbolic-link rejection;
- ZIP extension enforcement;
- source and target containment validation;
- destination overwrite protection;
- request and batch-size limits;
- audit log sanitization;
- Content Security Policy and related security headers;
- debug mode disabled in normal execution.

Protect `.env`, the SQLite database, reports, PID files, and Gunicorn logs from unauthorized access.

## Performance guidance

For approximately 100–1,000 or several thousand files:

- `os.scandir()` minimizes metadata calls;
- search and pagination run on the server;
- only the current page is rendered;
- the portal does not cache directory listings, so verification remains current;
- same-filesystem movement avoids content copying;
- Gunicorn uses multiple workers and threads.

Default standalone settings:

```text
Workers: 3
Threads per worker: 4
Timeout: 120 seconds
```

Avoid running multiple move processes for the same source/target pair unless operational requirements have been tested. Concurrent requests are safely revalidated, but high concurrency may still create confusing user outcomes when two users select the same files.

## Operational checks

Because the portal intentionally has no health-check endpoint, use operating-system and application checks:

```bash
./scripts/status.sh
ps -ef | grep '[g]unicorn.*app:app'
tail -f logs/gunicorn-error.log
sqlite3 data/file_mover.db "SELECT timestamp,username,action,details FROM audit_events ORDER BY id DESC LIMIT 20;"
```

You can also verify the listening socket with an approved system utility, for example:

```bash
ss -ltn | grep 5000
```

Use the equivalent command available on your operating system.

## Troubleshooting

### Application does not start

Review:

```bash
cat logs/gunicorn-error.log
```

Common causes:

- `.env` missing;
- weak or missing `SECRET_KEY`;
- virtual environment not created;
- requirements not installed;
- source or target missing;
- source and target on different filesystems;
- state, report, or log directory not writable;
- invalid LDAP or SMTP configuration.

### Login fails

Confirm:

- LDAPS hostname and port;
- CA certificate path;
- service-bind credentials;
- base DN and user filter;
- required group DN;
- user `mail` attribute when email delivery is enabled.

Detailed LDAP exceptions are intentionally not shown to the browser. Review secured server logs.

### File appears in the source after move

Use Refresh on the Verify Files page. If it remains:

- review the batch result;
- inspect the Excel report;
- confirm target collision or permission failure;
- review the audit and Gunicorn error logs.

### Report email is not received

Check:

- SMTP host and port;
- TLS mode;
- CA trust;
- sender permission;
- authenticated relay credentials;
- LDAP email value;
- spam/quarantine controls.

The report remains available from the completion page even when email delivery fails.

## Upgrade procedure

1. Stop the application.
2. Back up `.env` and any locally customized service files.
3. Extract the new project version.
4. Restore `.env` without replacing the new `.env.example`.
5. Activate the Python 3.9 or Python 3.11 virtual environment.
6. Reinstall pinned requirements.
7. Run Python compilation checks.
8. Confirm permissions.
9. Start the application and review logs.

Example:

```bash
./scripts/stop.sh
cp .env /tmp/file-mover.env.backup
. .venv/bin/activate
pip install -r requirements.txt
python -m compileall app.py config.py services
./scripts/start.sh
./scripts/status.sh
```

## Scope

This project is intentionally a small support utility. It does not require a database, Redis, Celery, or a JavaScript framework for the current same-filesystem use case. Add a persistent job store or background queue only if actual usage demonstrates long-running moves, multi-instance deployment, or high concurrent volume.

## Security hardening in this release

This release includes a focused security review of authentication, filesystem movement, batch state, email, logging, browser sessions, and operating-system scripts.

### Authentication and authorization

- LDAP connections require `ldaps://` and validate the LDAP server certificate.
- LDAP referrals are disabled to avoid following an unexpected directory referral.
- User input is escaped for both LDAP filters and DN-template substitution.
- The required LDAP group is enforced in both search-bind and simple-bind configurations. Simple bind no longer bypasses group authorization.
- Login throttling is stored on disk and shared by all Gunicorn workers instead of being held in one worker's memory.
- Login throttle keys are SHA-256 hashes, so usernames and client addresses are not used as filenames.
- The browser session contains only the username. The user's email address is resolved server-side when a move starts and is not exposed in the signed session cookie.

### Session and browser controls

- Production sessions use a `__Host-` cookie, `Secure`, `HttpOnly`, and `SameSite=Lax`.
- CSRF validation is required for form and JSON-changing requests.
- Responses use a restrictive Content Security Policy, frame protection, MIME sniffing protection, no-referrer policy, HSTS over HTTPS, cross-origin isolation headers, and no-store caching.
- The secret key must be at least 32 characters and cannot use the sample value.

### File movement

- Only ZIP filenames are accepted.
- Absolute paths, traversal, separators, control characters, overlong names, directories, and symbolic links are rejected.
- Source and target must be different, non-nested directories on the same filesystem.
- Existing target files are never overwritten.
- The target inode is compared with the validated source inode before the source name is removed, reducing path-swap race risk.
- Each file is revalidated immediately before movement.
- Batch size and individual file size are limited by configuration.
- Each user is limited to a small configurable number of active batches.

### Batch state, reports, and logs

- Batch updates use operating-system file locks shared across Gunicorn workers.
- Batch completion is claimed atomically, preventing duplicate completion and duplicate report emails.
- State and report writes use private temporary files, `fsync`, atomic replacement, and mode `0600`.
- Runtime directories use mode `0700` and reject symbolic-link directories.
- Old state, locks, reports, and rate-limit files are removed according to `BATCH_RETENTION_HOURS`.
- History and Excel history exports are restricted to the currently authenticated user's records.
- Audit logs escape newline and NUL characters and are read with bounded memory.

### SMTP

- SMTP is configured for an internal anonymous relay without TLS or authentication. Protect relay access at the network layer.
- SMTP and CA certificates are validated.
- Sender and recipient addresses are validated, including CR/LF rejection.
- SMTP credentials should be supplied by CyberArk, Vault, systemd credentials, or another secret manager instead of source control.

### Process scripts and systemd

- Start scripts use `umask 077` and private runtime/log directories.
- Startup refuses a `.env` file accessible by group or other users.
- Stop and status scripts verify that a PID belongs to the Gunicorn `app:app` process before sending a signal.
- Gunicorn request-line/header limits, graceful timeout, and short keep-alive are configured.
- The systemd example adds filesystem, kernel, privilege, device, namespace, and writable-path restrictions.

## New runtime configuration

```dotenv
BATCH_RETENTION_HOURS=168
MAX_ACTIVE_BATCHES_PER_USER=3
```

Create the runtime locations as the service account:

```bash
sudo install -d -m 0700 -o filemover -g filemover /var/lib/file-mover/batches
sudo install -d -m 0700 -o filemover -g filemover reports
sudo install -d -m 0700 -o filemover -g filemover /var/lib/file-mover/rate-limits
sudo install -d -m 0700 -o filemover -g filemover /var/log/file-mover
sudo chmod 0600 /opt/file_mover_portal/.env
```

## Dependency security maintenance

The pinned versions in this release are compatible with Python 3.9 and Python 3.11:

```text
Flask==3.1.3
Flask-WTF==1.2.2
ldap3==2.9.1
python-dotenv==1.2.2
gunicorn==26.0.0
XlsxWriter==3.2.9
```

Before each production deployment, run from a network-enabled build environment:

```bash
python3.11 -m pip install --upgrade pip pip-audit
pip-audit -r requirements.txt
```

Also run your organization's SAST and container or host vulnerability scanner. Dependency scanning is a recurring release activity, not a one-time guarantee.


# AIX offline deployment

This release includes an AIX-oriented `vendor/` directory. It contains platform-neutral Python wheels, the MarkupSafe source archive, and bundled `pip`, `setuptools`, and `wheel` bootstrap packages. Do not populate this directory with ordinary Windows wheels: Windows binary wheels cannot run on AIX.

## Supported interpreters

The same dependency lock supports:

- Python 3.9.23
- Python 3.11.13

The installer searches in this order:

```text
/opt/freeware/bin/python3.11
/opt/freeware/bin/python3.9
python3.11 from PATH
python3.9 from PATH
```

To select a specific interpreter:

```bash
PYTHON_BIN=/opt/freeware/bin/python3.9 ./scripts/install_offline_aix.sh
```

IBM commonly provides AIX Toolbox software under `/opt/freeware`. Keep the Python interpreter and its supporting AIX Toolbox libraries from the same packaging source; mixing base AIX Python libraries with AIX Toolbox libraries can produce loader and ABI problems.

## Rebuild the vendor directory on Windows

Run PowerShell from the extracted project directory on an Internet-connected Windows workstation:

```powershell
Set-ExecutionPolicy -Scope Process Bypass
.\scripts\download_vendor_aix.ps1
```

To choose Windows Python explicitly:

```powershell
.\scripts\download_vendor_aix.ps1 -PythonCommand "py -3.11"
```

The script:

1. Deletes and recreates `vendor/`.
2. Downloads only `py3-none-any` or equivalent platform-neutral wheels.
3. Downloads MarkupSafe as a source archive because PyPI does not publish an AIX wheel.
4. Downloads platform-neutral `pip`, `setuptools`, and `wheel` bootstrap wheels.
5. Generates `vendor/SHA256SUMS`.

Copy the complete project directory to AIX. Do not copy only the `vendor/` directory because the lock file and installation scripts are also required.

## Install on AIX without system pip

The AIX installer does not depend on `ensurepip` and does not require `pip` to already be installed globally.

```bash
cd /opt/file_mover_portal
chmod 750 scripts/*.sh
./scripts/install_offline_aix.sh
```

It performs the following operations:

1. Selects Python 3.11 or 3.9.
2. Creates `.venv` with `--without-pip`.
3. Loads `pip` directly from the bundled wheel.
4. Installs `pip`, `setuptools`, and `wheel` into the virtual environment.
5. Installs the locked application dependencies using only `vendor/`.
6. Runs `pip check` and import tests.

No Internet connection is used during the AIX installation.

## MarkupSafe on AIX

MarkupSafe is the only dependency in this application bundle that normally includes an optional C extension. The included source distribution first tries to compile the speedup. If an AIX compiler is unavailable or compilation fails, MarkupSafe retries automatically as a plain-Python build. The portal works without the optional speedup.

The installation requires `setuptools>=77`, which is already included in `vendor/`.

## Start and stop on AIX

After creating `.env` and setting it to mode `600`:

```bash
chmod 600 .env
./scripts/start.sh
./scripts/status.sh
./scripts/stop.sh
```

The scripts require Bash. On AIX Toolbox installations it is commonly available as `/opt/freeware/bin/bash`. When `/usr/bin/env bash` cannot find it, add `/opt/freeware/bin` to `PATH` before running the scripts:

```bash
export PATH=/opt/freeware/bin:$PATH
```

## AIX verification commands

```bash
/opt/freeware/bin/python3.11 -V
./.venv/bin/python -V
./.venv/bin/python -m pip check
./.venv/bin/gunicorn --version
./scripts/status.sh
```

## Important AIX limitations

- Do not use `manylinux`, Windows, macOS, x86, or ARM binary wheels on AIX/POWER.
- Keep all source and target filesystems mounted consistently for the service account.
- Gunicorn is Unix-oriented and is supported conceptually on AIX, but test worker/process behavior under your exact AIX maintenance level.
- The included service file is a systemd unit and is not usable on AIX. Use the supplied shell scripts or integrate them with your enterprise AIX process supervisor.
- If the Python `venv` module itself is missing, install the matching AIX Toolbox Python package that supplies it; copying a virtual environment from Windows or Linux will not work.


## SQLite persistence

The portal stores operational information in one SQLite database:

- audit events;
- batch headers;
- selected filenames and per-file results;
- batch completion and email status;
- login-rate-limit attempts.

Configure it with:

```dotenv
DATABASE_PATH=data/file_mover.db
SQLITE_BUSY_TIMEOUT_MS=10000
```

Python 3.9 and Python 3.11 include the `sqlite3` module, so no additional pip package or AIX wheel is required. The installer verifies that `sqlite3` imports successfully. Place the database on a local AIX filesystem rather than NFS. The database directory is set to mode `0700` and the database file to `0600`. Excel reports remain in `REPORT_DIR` because they are downloadable binary artifacts.

Back up the database while the portal is stopped, or use SQLite's online backup command. Do not copy an actively written database file without a consistent backup procedure.

### Migrating an earlier file-backed deployment

Stop the portal and run the one-time importer before starting the SQLite version:

```bash
.venv/bin/python scripts/migrate_legacy_storage.py \
  --database data/file_mover.db \
  --audit-file /var/log/file-mover/audit.jsonl \
  --batch-dir /var/lib/file-mover/batches
```

The importer skips batch IDs already present in SQLite. Keep a backup of the legacy files until the imported history has been verified.


## Remote IBM HTTP Server deployment

Set `APP_HOST` to the Python server internal IP and `APP_PORT` to the backend port. Set `TRUSTED_PROXY_IPS` to the exact IBM HTTP Server source IP (or comma-separated trusted proxy IPs). Firewall the backend port so only those proxy hosts can connect. `TRUSTED_PROXY_COUNT=1` is appropriate for one IHS proxy hop.

## Retention, log rotation, and database recovery

- Completed batch database rows expire using `BATCH_RETENTION_HOURS`.
- Excel reports expire independently using `REPORT_RETENTION_DAYS`.
- `scripts/rotate_logs.py` copy-truncates logs above `LOG_MAX_BYTES`, keeps `LOG_BACKUP_COUNT`, and removes archives older than `LOG_RETENTION_DAYS`. It runs before portal startup and may also be scheduled from cron.
- Create an online SQLite backup with `.venv/bin/python scripts/backup_db.py`.
- Stop the portal, then restore with `.venv/bin/python scripts/restore_db.py backups/<file>.db --force`. The restore utility validates integrity and preserves a pre-restore safety copy.


## Configurable context root

Set the public URL prefix in `.env`:

```properties
APPLICATION_ROOT=/filemover
PREFERRED_URL_SCHEME=https
```

The portal will then serve all pages, static assets, API endpoints, redirects,
report downloads, and session cookies below `/filemover`. Use `APPLICATION_ROOT=/`
for a root deployment. Do not add a trailing slash.

Example public URLs:

```text
https://portal.example.com/filemover/
https://portal.example.com/filemover/login
https://portal.example.com/filemover/move-files
```

IBM HTTP Server must preserve the `/filemover` prefix when proxying to Gunicorn.
The application itself strips the prefix internally and uses `SCRIPT_NAME` so
Flask `url_for()` generates correct context-root-aware links.
