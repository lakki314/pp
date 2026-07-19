# Security Review Summary

## Fixed findings

| Severity | Finding | Resolution |
|---|---|---|
| High | Required LDAP group was not enforced in simple-bind mode | Group membership is now resolved and enforced with the LDAP service account after credential validation. Multiple groups, ANY/ALL matching, and optional Active Directory nested-group checks are supported. |
| High | Batch state locking worked only within one Python worker | Replaced thread-only locking with `fcntl` locks shared across Gunicorn workers. |
| Medium | Login throttling was worker-local and could be bypassed across workers | Added filesystem-backed shared throttling with hashed keys and private files. |
| Medium | Repeated completion calls could produce duplicate email/report processing | Added atomic completion claiming and idempotent completed responses. |
| Medium | Stop script trusted any PID in the PID file | It now verifies the process command belongs to Gunicorn running `app:app`. |
| Medium | SMTP could be configured without transport encryption | Mail-enabled startup now requires SSL or STARTTLS. |
| Medium | User email was stored in Flask's client-visible signed session | Session now stores only the username; email is looked up server-side per batch. |
| Medium | Batch and report files had no retention cleanup | Added configurable expiry cleanup and private directory/file modes. |
| Low | Audit history reader loaded the complete active log into memory | Replaced with bounded `deque` reading. |
| Low | Audit/history exposed all users to every authenticated user | History and exports are now filtered to the current user. |
| Low | LDAP DN-template substitution was not escaped | Added RDN escaping. |
| Low | Additional browser isolation and cache headers were absent | Added COOP, CORP, Pragma, and stronger no-store headers. |

## Deployment assumptions

- Source and target directories are controlled by trusted operating-system accounts.
- TLS is terminated by a correctly configured reverse proxy.
- `TRUSTED_PROXY_COUNT` exactly matches the trusted proxy chain and is `0` otherwise.
- The service runs as a dedicated non-login account.
- `.env`, runtime files, reports, and logs are not placed under a web document root.
- LDAP and SMTP CA files are genuine organization trust anchors.

## Verification performed

- Python source compilation succeeded.
- Shell scripts passed Bash syntax checking.
- Dependencies installed successfully in an isolated environment.
- Flask application creation and `/login` smoke test succeeded.
- Static search found no debug mode, disabled certificate verification, unsafe template marking, dynamic code execution, or shell subprocess usage.

An online advisory lookup with `pip-audit` was attempted but could not complete because the vulnerability service was unreachable from the execution environment. Run the documented `pip-audit` command in the organization's network-enabled build pipeline.
