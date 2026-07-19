# Configurable context root changes

The portal now reads `APPLICATION_ROOT` from `.env`.

Example:

```properties
APPLICATION_ROOT=/filemover
PREFERRED_URL_SCHEME=https
```

Changed files:

- `config.py` — validates and normalizes the configured context root; scopes the session cookie correctly.
- `app.py` — mounts the application beneath the context root using WSGI `SCRIPT_NAME` and rejects paths outside it.
- `.env.example` — includes context-root settings.
- `README.md` — documents root and prefixed deployments.

All existing templates already use Flask `url_for()`, so page links, static assets,
form actions, APIs, redirects, pagination, and report downloads automatically include
the configured context root.
