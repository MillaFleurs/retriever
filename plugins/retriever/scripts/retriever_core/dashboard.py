"""Loopback-only interactive Retriever job dashboard."""

from __future__ import annotations

import hmac
import re
import secrets
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

from . import db, reports


ARCHIVE_PATH = re.compile(r"^/jobs/([1-9][0-9]*)/archive$")
MAX_FORM_BYTES = 4096


def create_dashboard_server(
    state_dir: str | Path,
    *,
    port: int = 0,
    ranked: bool = False,
) -> ThreadingHTTPServer:
    """Create a dashboard server bound exclusively to the local loopback interface."""
    resolved_state_dir = db.resolve_state_dir(state_dir)
    archive_token = secrets.token_urlsafe(32)

    class DashboardRequestHandler(BaseHTTPRequestHandler):
        def log_message(self, format: str, *args: object) -> None:
            """Keep job metadata out of the terminal log by default."""

        def _send_html(self, content: str, *, status: HTTPStatus = HTTPStatus.OK) -> None:
            encoded = content.encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(encoded)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(encoded)

        def _error(self, status: HTTPStatus, message: str) -> None:
            self._send_html(f"<!doctype html><title>Retriever Dashboard</title><p>{message}</p>", status=status)

        def _render(self, *, notice: str = "") -> str:
            conn = db.connect(resolved_state_dir)
            try:
                rows = db.visible_jobs(conn)
                if ranked:
                    rows = db.rank_jobs(conn, rows)
                return reports.jobs_to_html(
                    rows,
                    total_count=len(rows),
                    ranked=ranked,
                    interactive_archive=True,
                    archive_token=archive_token,
                    archive_notice=notice,
                )
            finally:
                conn.close()

        def do_GET(self) -> None:  # noqa: N802
            request = urlsplit(self.path)
            if request.path != "/":
                self._error(HTTPStatus.NOT_FOUND, "Not found.")
                return
            archived = parse_qs(request.query).get("archived", [""])[0]
            notice = f"Archived job {archived} locally." if archived.isdecimal() else ""
            self._send_html(self._render(notice=notice))

        def do_POST(self) -> None:  # noqa: N802
            match = ARCHIVE_PATH.fullmatch(urlsplit(self.path).path)
            if match is None:
                self._error(HTTPStatus.NOT_FOUND, "Not found.")
                return
            try:
                content_length = int(self.headers.get("Content-Length", "0"))
            except ValueError:
                self._error(HTTPStatus.BAD_REQUEST, "Invalid request.")
                return
            if content_length <= 0 or content_length > MAX_FORM_BYTES:
                self._error(HTTPStatus.BAD_REQUEST, "Invalid request.")
                return
            fields = parse_qs(self.rfile.read(content_length).decode("utf-8", errors="replace"))
            submitted_token = fields.get("token", [""])[0]
            if not hmac.compare_digest(submitted_token, archive_token):
                self._error(HTTPStatus.FORBIDDEN, "Archive confirmation is required.")
                return

            job_id = int(match.group(1))
            conn = db.connect(resolved_state_dir)
            try:
                archived = db.archive_job(conn, job_id)
            finally:
                conn.close()
            if not archived:
                self._error(HTTPStatus.NOT_FOUND, "That job is no longer available to archive.")
                return
            self.send_response(HTTPStatus.SEE_OTHER)
            self.send_header("Location", f"/?archived={job_id}")
            self.end_headers()

    server = ThreadingHTTPServer(("127.0.0.1", port), DashboardRequestHandler)
    server.daemon_threads = True
    server.retriever_archive_token = archive_token  # type: ignore[attr-defined]
    return server
