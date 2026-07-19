"""Loopback-only interactive Retriever job dashboard and service controls."""

from __future__ import annotations

import hmac
import json
import os
import re
import secrets
import threading
import time
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib import error, request
from urllib.parse import parse_qs, urlencode, urlsplit

from . import db, reports


ARCHIVE_PATH = re.compile(r"^/jobs/([1-9][0-9]*)/archive$")
HEALTH_PATH = "/_health"
STOP_PATH = "/_stop"
ARCHIVED_CSV_PATH = "/archived.csv"
MAX_FORM_BYTES = 4096
SERVICE_STATE_FILENAME = "dashboard-service.json"


def service_state_path(state_dir: str | Path) -> Path:
    """Return the local service state path without creating it."""
    return db.resolve_state_dir(state_dir) / SERVICE_STATE_FILENAME


def _service_url(record: dict[str, object]) -> str:
    return f"http://127.0.0.1:{record['port']}/"


def load_service_state(state_dir: str | Path) -> dict[str, object] | None:
    """Read a syntactically valid local dashboard service record, if present."""
    path = service_state_path(state_dir)
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    if not isinstance(payload, dict):
        return None
    if not isinstance(payload.get("service_id"), str) or not isinstance(payload.get("control_token"), str):
        return None
    if not isinstance(payload.get("port"), int) or not 1 <= payload["port"] <= 65535:
        return None
    if not isinstance(payload.get("pid"), int) or payload["pid"] <= 0:
        return None
    if not isinstance(payload.get("ranked"), bool):
        return None
    return payload


def write_service_state(
    state_dir: str | Path,
    *,
    service_id: str,
    control_token: str,
    port: int,
    ranked: bool,
) -> dict[str, object]:
    """Atomically persist the control metadata for one loopback dashboard server."""
    path = service_state_path(state_dir)
    record: dict[str, object] = {
        "service_id": service_id,
        "control_token": control_token,
        "pid": os.getpid(),
        "port": port,
        "ranked": ranked,
    }
    temporary = path.with_name(f".{path.name}.tmp")
    temporary.write_text(json.dumps(record, sort_keys=True), encoding="utf-8")
    os.chmod(temporary, 0o600)
    temporary.replace(path)
    return record


def clear_service_state(state_dir: str | Path, service_id: str) -> None:
    """Remove state only when it still belongs to the stopping service."""
    path = service_state_path(state_dir)
    record = load_service_state(state_dir)
    if record is not None and record["service_id"] == service_id:
        try:
            path.unlink()
        except FileNotFoundError:
            pass


def _health_matches(record: dict[str, object], *, timeout_seconds: float) -> bool:
    try:
        with request.urlopen(f"{_service_url(record).rstrip('/')}{HEALTH_PATH}", timeout=timeout_seconds) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except (OSError, ValueError, error.URLError, json.JSONDecodeError):
        return False
    return payload.get("service_id") == record["service_id"]


def active_service(state_dir: str | Path, *, timeout_seconds: float = 0.5) -> dict[str, object] | None:
    """Return the active local service record, clearing stale metadata safely."""
    record = load_service_state(state_dir)
    if record is None:
        return None
    if not _health_matches(record, timeout_seconds=timeout_seconds):
        clear_service_state(state_dir, str(record["service_id"]))
        return None
    return record


def wait_for_active_service(
    state_dir: str | Path,
    service_id: str,
    *,
    timeout_seconds: float = 5.0,
) -> dict[str, object] | None:
    """Wait briefly for a newly spawned dashboard process to answer on loopback."""
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        record = load_service_state(state_dir)
        if record is not None and record["service_id"] == service_id and _health_matches(record, timeout_seconds=0.5):
            return record
        time.sleep(0.05)
    return None


def request_stop(record: dict[str, object], *, timeout_seconds: float = 2.0) -> bool:
    """Ask an active loopback service to stop through its authenticated control endpoint."""
    body = urlencode({"token": record["control_token"]}).encode("utf-8")
    stop_request = request.Request(
        f"{_service_url(record).rstrip('/')}{STOP_PATH}", data=body, method="POST"
    )
    try:
        with request.urlopen(stop_request, timeout=timeout_seconds) as response:
            return response.status == HTTPStatus.ACCEPTED
    except (OSError, error.URLError):
        return False


def wait_for_stop(state_dir: str | Path, *, timeout_seconds: float = 5.0) -> bool:
    """Wait for the managed service to clear its own control state."""
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        if active_service(state_dir) is None:
            return True
        time.sleep(0.05)
    return active_service(state_dir) is None


def create_dashboard_server(
    state_dir: str | Path,
    *,
    port: int = 0,
    ranked: bool = False,
    service_id: str = "",
    control_token: str = "",
) -> ThreadingHTTPServer:
    """Create a dashboard server bound exclusively to the local loopback interface."""
    if bool(service_id) != bool(control_token):
        raise ValueError("managed dashboard services require an id and control token")
    resolved_state_dir = db.resolve_state_dir(state_dir)
    archive_token = secrets.token_urlsafe(32)

    class DashboardRequestHandler(BaseHTTPRequestHandler):
        def log_message(self, format: str, *args: object) -> None:
            """Keep job metadata out of the terminal log by default."""

        def _send_bytes(
            self,
            content: bytes,
            *,
            content_type: str,
            status: HTTPStatus = HTTPStatus.OK,
            content_disposition: str = "",
        ) -> None:
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(content)))
            self.send_header("Cache-Control", "no-store")
            if content_disposition:
                self.send_header("Content-Disposition", content_disposition)
            self.end_headers()
            self.wfile.write(content)

        def _send_html(self, content: str, *, status: HTTPStatus = HTTPStatus.OK) -> None:
            self._send_bytes(content.encode("utf-8"), content_type="text/html; charset=utf-8", status=status)

        def _send_json(self, payload: dict[str, object], *, status: HTTPStatus = HTTPStatus.OK) -> None:
            self._send_bytes(
                json.dumps(payload).encode("utf-8"), content_type="application/json; charset=utf-8", status=status
            )

        def _error(self, status: HTTPStatus, message: str) -> None:
            self._send_html(f"<!doctype html><title>Retriever Dashboard</title><p>{message}</p>", status=status)

        def _form_fields(self) -> dict[str, list[str]] | None:
            try:
                content_length = int(self.headers.get("Content-Length", "0"))
            except ValueError:
                self._error(HTTPStatus.BAD_REQUEST, "Invalid request.")
                return None
            if content_length <= 0 or content_length > MAX_FORM_BYTES:
                self._error(HTTPStatus.BAD_REQUEST, "Invalid request.")
                return None
            return parse_qs(self.rfile.read(content_length).decode("utf-8", errors="replace"))

        def _render(self, *, notice: str = "") -> str:
            conn = db.connect(resolved_state_dir)
            try:
                rows = db.visible_jobs(conn)
                if ranked:
                    rows = db.rank_jobs(conn, rows)
                counts = db.job_counts(conn)
                return reports.jobs_to_html(
                    rows,
                    total_count=len(rows),
                    total_job_count=counts["total_jobs"],
                    archived_job_count=counts["directly_archived_jobs"],
                    ranked=ranked,
                    interactive_archive=True,
                    archive_token=archive_token,
                    archive_notice=notice,
                    archived_download_url=ARCHIVED_CSV_PATH,
                )
            finally:
                conn.close()

        def do_GET(self) -> None:  # noqa: N802
            parsed = urlsplit(self.path)
            if parsed.path == HEALTH_PATH:
                self._send_json({"service_id": service_id})
                return
            if parsed.path == ARCHIVED_CSV_PATH:
                conn = db.connect(resolved_state_dir)
                try:
                    content = reports.jobs_to_csv(db.directly_archived_jobs(conn)).encode("utf-8")
                finally:
                    conn.close()
                self._send_bytes(
                    content,
                    content_type="text/csv; charset=utf-8",
                    content_disposition='attachment; filename="retriever-archived-jobs.csv"',
                )
                return
            if parsed.path != "/":
                self._error(HTTPStatus.NOT_FOUND, "Not found.")
                return
            archived = parse_qs(parsed.query).get("archived", [""])[0]
            notice = f"Archived job {archived} locally." if archived.isdecimal() else ""
            self._send_html(self._render(notice=notice))

        def do_POST(self) -> None:  # noqa: N802
            parsed = urlsplit(self.path)
            fields = self._form_fields()
            if fields is None:
                return
            submitted_token = fields.get("token", [""])[0]
            if parsed.path == STOP_PATH:
                if not service_id or not hmac.compare_digest(submitted_token, control_token):
                    self._error(HTTPStatus.FORBIDDEN, "Dashboard stop confirmation is required.")
                    return
                self._send_json({"stopping": True}, status=HTTPStatus.ACCEPTED)
                threading.Thread(target=server.shutdown, daemon=True).start()
                return

            match = ARCHIVE_PATH.fullmatch(parsed.path)
            if match is None:
                self._error(HTTPStatus.NOT_FOUND, "Not found.")
                return
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
