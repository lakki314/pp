from __future__ import annotations

import os
import uuid
from datetime import datetime, timezone
from functools import wraps
from pathlib import Path

from flask import Flask, flash, jsonify, redirect, render_template, request, send_file, session, url_for
from flask_wtf.csrf import CSRFProtect
from werkzeug.middleware.proxy_fix import ProxyFix

from config import Config
from services.audit_service import AuditService
from services.batch_service import BatchService, BatchStateError
from services.file_service import FileMoveError, FileService
from services.excel_service import ExcelExportService
from services.email_service import EmailDeliveryError, EmailService
from services.ldap_service import LDAPAuthenticationError, LDAPService
from services.rate_limit_service import LoginRateLimiter
from services.sqlite_store import SQLiteStore


def create_app() -> Flask:
    app = Flask(__name__)
    app.config.from_object(Config)
    CSRFProtect(app)

    proxy_count = app.config["TRUSTED_PROXY_COUNT"]
    if proxy_count > 0:
        app.wsgi_app = ProxyFix(app.wsgi_app, x_for=proxy_count, x_proto=proxy_count, x_host=proxy_count)

    file_service = FileService(
        source_dir=Path(app.config["SOURCE_DIR"]),
        destination_dir=Path(app.config["DESTINATION_DIR"]),
        allowed_extensions=app.config["ALLOWED_EXTENSIONS"],
        max_file_size_bytes=app.config["MAX_FILE_SIZE_BYTES"],
        max_filename_length=app.config["MAX_FILENAME_LENGTH"],
    )
    sqlite_store = SQLiteStore(
        Path(app.config["DATABASE_PATH"]), app.config["SQLITE_BUSY_TIMEOUT_MS"]
    )
    audit_service = AuditService(sqlite_store, app.config["APP_NAME"])
    batch_service = BatchService(
        sqlite_store,
        Path(app.config["REPORT_DIR"]),
        app.config["BATCH_RETENTION_HOURS"],
        app.config["REPORT_RETENTION_DAYS"],
    )
    ldap_service = LDAPService(app.config)
    excel_service = ExcelExportService(app.config["APP_NAME"])
    email_service = EmailService(app.config)
    limiter = LoginRateLimiter(
        app.config["LOGIN_MAX_ATTEMPTS"],
        app.config["LOGIN_WINDOW_SECONDS"],
        sqlite_store,
    )
    batch_service.cleanup_expired()

    def current_user():
        return session.get("username")

    def current_display_name():
        return session.get("display_name") or current_user()

    @app.context_processor
    def inject_authenticated_identity():
        return {
            "username": current_user(),
            "display_name": current_display_name(),
        }

    def login_required(view):
        @wraps(view)
        def wrapped(*args, **kwargs):
            if not current_user():
                return redirect(url_for("login"))
            return view(*args, **kwargs)
        return wrapped

    def client_key(username: str) -> str:
        return f"{request.remote_addr or 'unknown'}:{username.casefold()}"

    @app.after_request
    def security_headers(response):
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; "
            "font-src 'self'; object-src 'none'; base-uri 'self'; form-action 'self'; frame-ancestors 'none'"
        )
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
        response.headers["Cache-Control"] = "no-store, max-age=0"
        response.headers["Pragma"] = "no-cache"
        response.headers["Cross-Origin-Opener-Policy"] = "same-origin"
        response.headers["Cross-Origin-Resource-Policy"] = "same-origin"
        if request.is_secure:
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        return response

    @app.route("/login", methods=["GET", "POST"])
    def login():
        if current_user():
            return redirect(url_for("index"))
        if request.method == "POST":
            username = request.form.get("username", "").strip()
            password = request.form.get("password", "")
            key = client_key(username)
            if limiter.is_blocked(key):
                audit_service.record("LOGIN_BLOCKED", username or "unknown", "Rate limit exceeded", request.remote_addr)
                flash("Too many failed attempts. Try again later.", "error")
                return render_template("login.html"), 429
            if not username or not password or len(username) > 256 or len(password) > 1024:
                limiter.record_failure(key)
                flash("Invalid username or password.", "error")
                return render_template("login.html"), 401
            try:
                identity = ldap_service.authenticate(username, password)
            except LDAPAuthenticationError:
                limiter.record_failure(key)
                audit_service.record("LOGIN_FAILED", username or "unknown", "Authentication rejected", request.remote_addr)
                flash("Invalid username or password.", "error")
                return render_template("login.html"), 401
            limiter.reset(key)
            session.clear()
            session.permanent = True
            session["username"] = username
            session["display_name"] = str(identity.get("display_name", username)).strip() or username
            audit_service.record("LOGIN_SUCCESS", username, "User authenticated", request.remote_addr)
            return redirect(url_for("index"))
        return render_template("login.html")

    @app.post("/logout")
    @login_required
    def logout():
        username = current_user() or "unknown"
        audit_service.record("LOGOUT", username, "User logged out", request.remote_addr)
        session.clear()
        return redirect(url_for("login"))

    def file_page(directory: str) -> tuple[dict, str, int]:
        search = request.args.get("q", "").strip()[:256]
        requested_size = request.args.get("per_page", app.config["DEFAULT_FILES_PER_PAGE"], type=int)
        allowed_sizes = app.config["PAGE_SIZE_OPTIONS"] or (20,)
        per_page = requested_size if requested_size in allowed_sizes else app.config["DEFAULT_FILES_PER_PAGE"]
        per_page = min(per_page, app.config["MAX_FILES_PER_PAGE"])
        page = request.args.get("page", 1, type=int)
        return file_service.list_files_page(directory, search, page, per_page), search, per_page

    @app.get("/")
    @login_required
    def index():
        pagination, search, per_page = file_page("source")
        return render_template(
            "index.html", files=pagination["items"], pagination=pagination, search=search,
            per_page=per_page, page_size_options=app.config["PAGE_SIZE_OPTIONS"],
            source_dir=str(file_service.source_dir), destination_dir=str(file_service.destination_dir),
            username=current_user(),
        )

    @app.get("/verify")
    @login_required
    def verify_files():
        directory = request.args.get("directory", "source")
        if directory not in {"source", "destination"}:
            directory = "source"
        pagination, search, per_page = file_page(directory)
        return render_template(
            "verify.html", files=pagination["items"], pagination=pagination, search=search,
            per_page=per_page, page_size_options=app.config["PAGE_SIZE_OPTIONS"], directory=directory,
            source_dir=str(file_service.source_dir), destination_dir=str(file_service.destination_dir),
            username=current_user(),
        )

    def _json_payload() -> dict:
        payload = request.get_json(silent=True)
        return payload if isinstance(payload, dict) else {}

    @app.post("/api/move/start")
    @login_required
    def api_move_start():
        payload = _json_payload()
        selected_files = payload.get("selected_files", [])
        if not isinstance(selected_files, list):
            return jsonify({"error": "Invalid file selection"}), 400
        selected_files = list(dict.fromkeys(str(name) for name in selected_files))
        if not selected_files:
            return jsonify({"error": "Select at least one ZIP file"}), 400
        if len(selected_files) > app.config["MAX_FILES_PER_MOVE"]:
            return jsonify({"error": "Too many files selected"}), 400
        # Validate names before creating the server-side batch. File existence is rechecked per move.
        for filename in selected_files:
            try:
                file_service.validate_filename(filename)
            except FileMoveError as exc:
                return jsonify({"error": f"Invalid selection: {exc}"}), 400

        username = current_user() or "unknown"
        if batch_service.active_count(username) >= app.config["MAX_ACTIVE_BATCHES_PER_USER"]:
            return jsonify({"error": "Too many active batches for this user"}), 429
        try:
            recipient = ldap_service.lookup_authorized_email(username).strip()
        except LDAPAuthenticationError:
            recipient = ""
        batch_id = f"MOVE-{datetime.now(timezone.utc).strftime('%Y%m%d')}-{uuid.uuid4().hex[:10].upper()}"
        state = batch_service.create(
            batch_id=batch_id, username=username, recipient=recipient, filenames=selected_files
        )
        audit_service.record(
            "MOVE_BATCH_STARTED", username,
            f"batch_id={batch_id}; requested={len(selected_files)}", request.remote_addr
        )
        return jsonify({
            "batch_id": batch_id,
            "started_at": state["started_at"],
            "total": len(selected_files),
        })

    @app.post("/api/move/file")
    @login_required
    def api_move_file():
        payload = _json_payload()
        batch_id = str(payload.get("batch_id", ""))
        filename = str(payload.get("filename", ""))
        username = current_user() or "unknown"
        try:
            state = batch_service.load(batch_id, username)
            if filename not in state.get("filenames", []):
                raise BatchStateError("File is not part of this batch")
            result = file_service.move_file(filename)
            item = {"filename": result["source_name"], "status": "MOVED", "message": "Moved successfully"}
        except FileMoveError as exc:
            item = {"filename": filename, "status": "FAILED", "message": str(exc)}
        except BatchStateError as exc:
            return jsonify({"error": str(exc)}), 400

        try:
            state = batch_service.append_result(batch_id, username, item)
        except BatchStateError as exc:
            return jsonify({"error": str(exc)}), 400
        completed = len(state["results"])
        moved = sum(1 for row in state["results"] if row["status"] == "MOVED")
        return jsonify({
            "result": item, "completed": completed, "moved": moved, "failed": completed - moved
        })

    @app.post("/api/move/complete")
    @login_required
    def api_move_complete():
        payload = _json_payload()
        batch_id = str(payload.get("batch_id", ""))
        username = current_user() or "unknown"
        try:
            state = batch_service.claim_completion(batch_id, username)
        except BatchStateError as exc:
            return jsonify({"error": str(exc)}), 409

        if state.get("status") in {"SUCCESS", "FAILED", "PARTIAL_SUCCESS"}:
            moved = sum(1 for item in state["results"] if item["status"] == "MOVED")
            failed = len(state["results"]) - moved
            return jsonify({
                "batch_id": batch_id, "status": state["status"], "requested": len(state["results"]),
                "moved": moved, "failed": failed, "email_status": state.get("email_status", "UNKNOWN"),
                "started_at": state["started_at"], "completed_at": state.get("completed_at", ""),
                "download_url": url_for("download_batch_report", batch_id=batch_id),
                "results": state["results"],
            })

        moved = sum(1 for item in state["results"] if item["status"] == "MOVED")
        failed = len(state["results"]) - moved
        email_status = "DISABLED"
        report = excel_service.build_move_report_workbook(
            batch_id=batch_id, username=username, recipient=state.get("recipient", ""),
            started_at=state["started_at"], completed_at=datetime.now(timezone.utc).isoformat(),
            source_directory=str(file_service.source_dir),
            destination_directory=str(file_service.destination_dir), results=state["results"],
        )
        batch_service.save_report(batch_id, report.getvalue())

        if app.config["MAIL_ENABLED"]:
            recipient = state.get("recipient", "")
            if not recipient:
                email_status = "FAILED_NO_ADDRESS"
            else:
                try:
                    email_service.send_move_report(
                        recipient=recipient, username=username, batch_id=batch_id,
                        moved_count=moved, failed_count=failed, workbook=report,
                    )
                    email_status = "SENT"
                except EmailDeliveryError:
                    email_status = "FAILED"

        try:
            state = batch_service.complete(batch_id, username, email_status)
        except BatchStateError as exc:
            return jsonify({"error": str(exc)}), 400
        audit_service.record(
            "MOVE_BATCH", username,
            f"batch_id={batch_id}; status={state['status']}; requested={len(state['results'])}; "
            f"moved={moved}; failed={failed}; email={email_status}", request.remote_addr
        )
        return jsonify({
            "batch_id": batch_id, "status": state["status"], "requested": len(state["results"]),
            "moved": moved, "failed": failed, "email_status": email_status,
            "started_at": state["started_at"], "completed_at": state["completed_at"],
            "download_url": url_for("download_batch_report", batch_id=batch_id),
            "results": state["results"],
        })

    @app.get("/reports/<batch_id>.xlsx")
    @login_required
    def download_batch_report(batch_id: str):
        username = current_user() or "unknown"
        try:
            batch_service.load(batch_id, username)
            path = batch_service.report_path(batch_id)
        except BatchStateError:
            return "Report not found", 404
        if not path.is_file():
            return "Report not found", 404
        return send_file(
            path, as_attachment=True, download_name=path.name,
            mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", max_age=0
        )

    @app.post("/move")
    @login_required
    def move_files():
        flash("JavaScript is required for live move progress.", "error")
        return redirect(url_for("index"))

    @app.get("/history")
    @login_required
    def history():
        return render_template("history.html", entries=audit_service.read_recent(app.config["HISTORY_LIMIT"], current_user()), username=current_user())

    @app.get("/history/export.xlsx")
    @login_required
    def export_history_excel():
        username = current_user() or "unknown"
        entries = audit_service.read_recent(app.config["EXCEL_EXPORT_LIMIT"], username)
        workbook = excel_service.build_audit_workbook(reversed(entries))
        audit_service.record("HISTORY_EXCEL_EXPORT", username, f"Exported {len(entries)} audit entries", request.remote_addr)
        return send_file(
            workbook,
            as_attachment=True,
            download_name="file_mover_audit_history.xlsx",
            mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            max_age=0,
        )

    @app.errorhandler(400)
    def bad_request(_error):
        flash("The request was invalid or expired.", "error")
        return redirect(url_for("index" if current_user() else "login"))

    @app.errorhandler(413)
    def request_too_large(_error):
        return "Request too large", 413

    return app


app = create_app()

if __name__ == "__main__":
    app.run(host=os.getenv("APP_HOST", "127.0.0.1"), port=int(os.getenv("APP_PORT", "5000")), debug=False)
