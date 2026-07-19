"""SQLite storage for Retriever."""

from __future__ import annotations

import hashlib
import json
import shutil
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit

from . import schedule
from .injection import InjectionWarning


DEFAULT_STATE_DIR = Path.home() / ".retriever"
TARGET_KINDS = {"role", "industry", "location", "company", "cadence"}
REQUIRED_TARGET_KINDS = ("role", "location", "cadence")
REQUIRED_TABLES = {"companies", "jobs", "targets", "retrieval_runs", "observations"}
STATE_ARTIFACT_NAMES = (
    "USER.md",
    "retriever.sqlite3",
    "retriever.sqlite3-shm",
    "retriever.sqlite3-wal",
    "reports",
    "dashboard-service.json",
    "dashboard-service.log",
    "runtime.json",
    "prior-installs",
)
RUNTIME_STATE_FILENAME = "runtime.json"
PRIOR_INSTALLS_DIRECTORY = "prior-installs"


def now_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def resolve_state_dir(state_dir: str | Path | None = None) -> Path:
    """Resolve Retriever's state location without creating files or directories."""
    return Path(state_dir).expanduser() if state_dir else DEFAULT_STATE_DIR


def ensure_state_dir(state_dir: str | Path | None = None) -> Path:
    path = resolve_state_dir(state_dir)
    path.mkdir(parents=True, exist_ok=True)
    (path / "reports").mkdir(exist_ok=True)
    return path


def db_path(state_dir: str | Path | None = None) -> Path:
    return ensure_state_dir(state_dir) / "retriever.sqlite3"


def user_md_path(state_dir: str | Path | None = None) -> Path:
    return ensure_state_dir(state_dir) / "USER.md"


def state_paths(state_dir: str | Path | None = None) -> tuple[Path, Path, Path]:
    """Return state, database, and profile paths without mutating local state."""
    state = resolve_state_dir(state_dir)
    return state, state / "retriever.sqlite3", state / "USER.md"


def runtime_state_path(state_dir: str | Path | None = None) -> Path:
    """Return the small, non-profile marker for the runtime that saved state."""
    return resolve_state_dir(state_dir) / RUNTIME_STATE_FILENAME


def read_runtime_identity(state_dir: str | Path | None = None) -> str:
    """Read a saved runtime identity without creating or trusting state."""
    path = runtime_state_path(state_dir)
    if not path.is_file() or path.is_symlink():
        return ""
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError, TypeError):
        return ""
    value = payload.get("runtime_identity") if isinstance(payload, dict) else ""
    return value if isinstance(value, str) else ""


def write_runtime_identity(state_dir: str | Path | None, runtime_identity: str) -> Path:
    """Atomically persist the runtime identity after a successful profile write."""
    if not runtime_identity.strip():
        raise ValueError("runtime identity is required")
    path = ensure_state_dir(state_dir) / RUNTIME_STATE_FILENAME
    temporary = path.with_suffix(".json.tmp")
    temporary.write_text(
        dump_json({"runtime_identity": runtime_identity.strip(), "updated_at": now_utc()}) + "\n",
        encoding="utf-8",
    )
    temporary.replace(path)
    return path


def state_reset_preview(state_dir: str | Path | None = None) -> dict[str, object]:
    """List only known Retriever artifacts that a clean-state reset can remove.

    A reset must not recursively delete an arbitrary caller-supplied directory.
    Unknown entries are reported and preserved, while the absence of the known
    profile, database, reports, and dashboard metadata still returns Retriever
    to fresh-onboarding state.
    """
    state = resolve_state_dir(state_dir)
    result: dict[str, object] = {
        "state_dir": str(state),
        "state_directory_exists": state.is_dir(),
        "known_artifacts": [],
        "preserved_unmanaged_entries": [],
    }
    if not state.exists():
        return result
    if state.is_symlink():
        result["state_directory_error"] = "Retriever state path must not be a symbolic link"
        return result
    if not state.is_dir():
        result["state_directory_error"] = "Retriever state path exists but is not a directory"
        return result

    default_state = DEFAULT_STATE_DIR.expanduser()
    database = state / "retriever.sqlite3"
    profile = state / "USER.md"
    has_profile_marker = False
    if profile.is_file():
        try:
            has_profile_marker = "# Retriever User Profile" in profile.read_text(encoding="utf-8")
        except OSError:
            pass
    has_known_retriever_artifact = any(
        (state / name).exists() or (state / name).is_symlink() for name in STATE_ARTIFACT_NAMES
    )
    if state != default_state and not database.is_file() and not has_profile_marker and not has_known_retriever_artifact:
        result["state_directory_error"] = (
            "custom state reset requires a Retriever database or a marked Retriever USER.md profile"
        )
        return result

    for name in STATE_ARTIFACT_NAMES:
        candidate = state / name
        if candidate.is_symlink():
            artifact_type = "symlink"
        elif candidate.is_dir():
            artifact_type = "directory"
        elif candidate.exists():
            artifact_type = "file"
        else:
            continue
        result["known_artifacts"].append({"path": str(candidate), "type": artifact_type})

    known_names = set(STATE_ARTIFACT_NAMES)
    result["preserved_unmanaged_entries"] = sorted(
        str(child) for child in state.iterdir() if child.name not in known_names
    )
    return result


def reinstall_prepare_preview(state_dir: str | Path | None = None) -> dict[str, object]:
    """Preview only active Retriever artifacts that a reinstall will quarantine.

    Prior-install backups are intentionally retained.  They are not live
    Retriever state and must never be read for a fresh onboarding.
    """
    preview = state_reset_preview(state_dir)
    if preview.get("state_directory_error"):
        return preview
    active = [
        artifact
        for artifact in preview["known_artifacts"]
        if Path(str(artifact["path"])).name != PRIOR_INSTALLS_DIRECTORY
    ]
    prior = [
        artifact
        for artifact in preview["known_artifacts"]
        if Path(str(artifact["path"])).name == PRIOR_INSTALLS_DIRECTORY
    ]
    return {
        "state_dir": preview["state_dir"],
        "state_directory_exists": preview["state_directory_exists"],
        "active_retriever_artifacts": active,
        "preserved_prior_install_backups": prior,
        "preserved_unmanaged_entries": preview["preserved_unmanaged_entries"],
    }


def reset_state_artifacts(state_dir: str | Path | None = None) -> dict[str, object]:
    """Delete only the known Retriever state artifacts described by the preview."""
    preview = state_reset_preview(state_dir)
    if preview.get("state_directory_error"):
        raise ValueError(str(preview["state_directory_error"]))

    deleted: list[dict[str, str]] = []
    for artifact in preview["known_artifacts"]:
        path = Path(artifact["path"])
        artifact_type = str(artifact["type"])
        if artifact_type == "directory":
            shutil.rmtree(path)
        else:
            path.unlink(missing_ok=True)
        deleted.append({"path": str(path), "type": artifact_type})

    return {
        "state_dir": preview["state_dir"],
        "deleted_artifacts": deleted,
        "preserved_unmanaged_entries": preview["preserved_unmanaged_entries"],
        "fresh_onboarding": True,
    }


def quarantine_active_state_for_reinstall(state_dir: str | Path | None = None) -> dict[str, object]:
    """Move active Retriever state aside so a reinstall cannot reuse it.

    This is deliberately a rename, not a delete.  The retained files remain
    local and are unavailable to the new profile; a later explicit full reset
    can remove the ``prior-installs`` directory after preview and confirmation.
    """
    preview = reinstall_prepare_preview(state_dir)
    if preview.get("state_directory_error"):
        raise ValueError(str(preview["state_directory_error"]))

    active = list(preview["active_retriever_artifacts"])
    if not active:
        return {
            "state_dir": preview["state_dir"],
            "quarantined_artifacts": [],
            "prior_install_backup": "",
            "preserved_unmanaged_entries": preview["preserved_unmanaged_entries"],
            "fresh_onboarding": True,
        }

    state = resolve_state_dir(state_dir)
    retained_root = state / PRIOR_INSTALLS_DIRECTORY
    if retained_root.is_symlink():
        raise ValueError("Retriever prior-install backup path must not be a symbolic link")
    if retained_root.exists() and not retained_root.is_dir():
        raise ValueError("Retriever prior-install backup path must be a directory")
    timestamp = now_utc().replace(":", "-")
    backup = retained_root / timestamp
    suffix = 1
    while backup.exists():
        suffix += 1
        backup = retained_root / f"{timestamp}-{suffix}"
    backup.mkdir(parents=True, mode=0o700)

    moved: list[dict[str, str]] = []
    for artifact in active:
        path = Path(str(artifact["path"]))
        destination = backup / path.name
        path.replace(destination)
        moved.append({"from": str(path), "to": str(destination), "type": str(artifact["type"])})

    return {
        "state_dir": str(state),
        "quarantined_artifacts": moved,
        "prior_install_backup": str(backup),
        "preserved_unmanaged_entries": preview["preserved_unmanaged_entries"],
        "fresh_onboarding": True,
    }


def _readonly_connection(database: Path) -> sqlite3.Connection:
    return sqlite3.connect(database.resolve().as_uri() + "?mode=ro", uri=True)


def setup_status(
    state_dir: str | Path | None = None,
    *,
    expected_runtime_identity: str | None = None,
) -> dict[str, object]:
    """Inspect whether local state is safe and complete enough for retrieval.

    This check intentionally never creates ``~/.retriever``, SQLite files, or a
    retrieval run. It is the guard used before onboarding and scheduled scans.
    """
    state, database, user_md = state_paths(state_dir)
    result: dict[str, object] = {
        "state_dir": str(state),
        "state_directory_exists": state.is_dir(),
        "database": str(database),
        "database_exists": database.is_file(),
        "database_integrity": "missing",
        "database_integrity_detail": "",
        "user_md": str(user_md),
        "user_md_exists": user_md.is_file(),
        "user_md_integrity": "missing",
        "active_companies": 0,
        "active_jobs": 0,
        "visible_jobs": 0,
        "active_targets": 0,
        "active_target_counts": {kind: 0 for kind in TARGET_KINDS},
        "cadence_integrity": "missing",
        "cadence_plan": None,
        "latest_run": None,
        "runtime_identity_status": "not_checked",
        "stored_runtime_identity": "",
        "requires_reinstall_cleanup": False,
    }

    if user_md.is_file():
        try:
            profile_text = user_md.read_text(encoding="utf-8")
        except OSError as exc:
            result["user_md_integrity"] = "unreadable"
            result["user_md_error"] = str(exc)
        else:
            result["user_md_integrity"] = "ok" if "# Retriever User Profile" in profile_text else "invalid"

    if database.is_file():
        conn: sqlite3.Connection | None = None
        try:
            conn = _readonly_connection(database)
            conn.row_factory = sqlite3.Row
            quick_check = conn.execute("PRAGMA quick_check").fetchone()[0]
            foreign_key_errors = list(conn.execute("PRAGMA foreign_key_check"))
            table_names = {row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type = 'table'")}
            missing_tables = sorted(REQUIRED_TABLES - table_names)
            schema_version = conn.execute("PRAGMA user_version").fetchone()[0]

            if quick_check != "ok":
                result["database_integrity"] = "invalid"
                result["database_integrity_detail"] = str(quick_check)
            elif foreign_key_errors:
                result["database_integrity"] = "invalid"
                result["database_integrity_detail"] = "foreign key check failed"
            elif missing_tables or schema_version < 1:
                result["database_integrity"] = "invalid"
                result["database_integrity_detail"] = (
                    f"missing tables: {', '.join(missing_tables)}" if missing_tables else "unsupported schema version"
                )
            else:
                target_counts = {
                    kind: conn.execute(
                        "SELECT COUNT(*) FROM targets WHERE archived = 0 AND kind = ?", (kind,)
                    ).fetchone()[0]
                    for kind in TARGET_KINDS
                }
                result.update(
                    {
                        "database_integrity": "ok",
                        "active_companies": conn.execute(
                            "SELECT COUNT(*) FROM companies WHERE archived = 0"
                        ).fetchone()[0],
                        "active_jobs": conn.execute(
                            """
                            SELECT COUNT(*)
                            FROM jobs j
                            JOIN companies c ON c.id = j.company_id
                            WHERE j.archived = 0 AND c.archived = 0
                            """
                        ).fetchone()[0],
                        "visible_jobs": len(visible_jobs(conn)),
                        "active_targets": sum(target_counts.values()),
                        "active_target_counts": target_counts,
                        "latest_run": (
                            dict(row)
                            if (row := conn.execute("SELECT * FROM retrieval_runs ORDER BY id DESC LIMIT 1").fetchone())
                            else None
                        ),
                    }
                )
                cadence_rows = list(
                    conn.execute(
                        "SELECT value FROM targets WHERE archived = 0 AND kind = 'cadence' ORDER BY updated_at DESC, id DESC"
                    )
                )
                if len(cadence_rows) == 1:
                    try:
                        result["cadence_plan"] = schedule.plan(cadence_rows[0]["value"])
                    except ValueError as exc:
                        result["cadence_integrity"] = "invalid"
                        result["cadence_error"] = str(exc)
                    else:
                        if result["cadence_plan"]["requires_local_timezone_confirmation"]:
                            result["cadence_integrity"] = "needs_local_timezone_confirmation"
                            result["cadence_error"] = (
                                "the saved cadence names a timezone; confirm the desired Codex machine local time "
                                "before updating its scheduled task"
                            )
                        else:
                            result["cadence_integrity"] = "ok"
                elif cadence_rows:
                    result["cadence_integrity"] = "ambiguous"
                    result["cadence_error"] = "multiple active cadence targets"
        except (OSError, sqlite3.Error) as exc:
            result["database_integrity"] = "unreadable"
            result["database_integrity_detail"] = str(exc)
        finally:
            if conn is not None:
                conn.close()

    missing_setup: list[str] = []
    if result["user_md_integrity"] != "ok":
        missing_setup.append("valid USER.md profile")
    if result["database_integrity"] != "ok":
        missing_setup.append("valid Retriever database")
    active_target_counts = result["active_target_counts"]
    assert isinstance(active_target_counts, dict)
    for kind in ("role", "location"):
        if active_target_counts.get(kind, 0) == 0:
            missing_setup.append(f"active {kind} target")
    if active_target_counts.get("cadence", 0) == 0:
        missing_setup.append("active cadence target")
    elif result["cadence_integrity"] in {"invalid", "ambiguous"}:
        missing_setup.append("one valid active cadence target")
    if result["active_companies"] == 0:
        missing_setup.append("active company")

    has_live_profile = (
        result["user_md_integrity"] == "ok"
        or result["active_companies"] > 0
        or result["active_targets"] > 0
        or result["active_jobs"] > 0
    )
    if expected_runtime_identity is not None:
        stored_identity = read_runtime_identity(state)
        result["stored_runtime_identity"] = stored_identity
        if not has_live_profile:
            result["runtime_identity_status"] = "not_applicable"
        elif not stored_identity:
            result["runtime_identity_status"] = "missing"
            result["requires_reinstall_cleanup"] = True
        elif stored_identity == expected_runtime_identity:
            result["runtime_identity_status"] = "current"
        else:
            result["runtime_identity_status"] = "changed"
            result["requires_reinstall_cleanup"] = True
        if result["requires_reinstall_cleanup"]:
            missing_setup.append("fresh onboarding required before using retained Retriever state")

    result["missing_setup"] = missing_setup
    result["fresh_onboarding"] = (
        result["database_integrity"] in {"missing", "ok"}
        and
        result["user_md_integrity"] == "missing"
        and result["active_companies"] == 0
        and result["active_targets"] == 0
        and result["active_jobs"] == 0
    )
    result["ready_for_retrieval"] = not missing_setup
    return result


def connect(state_dir: str | Path | None = None) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path(state_dir))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    migrate(conn)
    return conn


def migrate(conn: sqlite3.Connection) -> None:
    version = conn.execute("PRAGMA user_version").fetchone()[0]
    if version >= 1:
        return

    conn.executescript(
        """
        CREATE TABLE companies (
          id INTEGER PRIMARY KEY,
          name TEXT NOT NULL COLLATE NOCASE UNIQUE,
          website_url TEXT NOT NULL DEFAULT '',
          careers_url TEXT NOT NULL DEFAULT '',
          research_url TEXT NOT NULL DEFAULT '',
          notes TEXT NOT NULL DEFAULT '',
          created_at TEXT NOT NULL,
          updated_at TEXT NOT NULL,
          archived INTEGER NOT NULL DEFAULT 0 CHECK (archived IN (0, 1))
        );

        CREATE TABLE jobs (
          id INTEGER PRIMARY KEY,
          company_id INTEGER NOT NULL,
          source_key TEXT NOT NULL,
          external_id TEXT NOT NULL DEFAULT '',
          title TEXT NOT NULL,
          location TEXT NOT NULL DEFAULT '',
          work_mode TEXT NOT NULL DEFAULT '',
          function TEXT NOT NULL DEFAULT '',
          url TEXT NOT NULL DEFAULT '',
          source_url TEXT NOT NULL,
          description TEXT NOT NULL DEFAULT '',
          prompt_injection_warning TEXT NOT NULL DEFAULT '',
          first_seen_at TEXT NOT NULL,
          last_seen_at TEXT NOT NULL,
          posted_at TEXT NOT NULL DEFAULT '',
          archived INTEGER NOT NULL DEFAULT 0 CHECK (archived IN (0, 1)),
          FOREIGN KEY (company_id) REFERENCES companies(id) ON DELETE CASCADE,
          UNIQUE (company_id, source_key)
        );

        CREATE TABLE targets (
          id INTEGER PRIMARY KEY,
          kind TEXT NOT NULL,
          value TEXT NOT NULL,
          created_at TEXT NOT NULL,
          updated_at TEXT NOT NULL,
          archived INTEGER NOT NULL DEFAULT 0 CHECK (archived IN (0, 1)),
          UNIQUE (kind, value)
        );

        CREATE TABLE retrieval_runs (
          id INTEGER PRIMARY KEY,
          started_at TEXT NOT NULL,
          completed_at TEXT NOT NULL DEFAULT '',
          status TEXT NOT NULL DEFAULT 'running',
          new_job_count INTEGER NOT NULL DEFAULT 0,
          error_count INTEGER NOT NULL DEFAULT 0,
          notes TEXT NOT NULL DEFAULT '',
          archived INTEGER NOT NULL DEFAULT 0 CHECK (archived IN (0, 1))
        );

        CREATE TABLE observations (
          id INTEGER PRIMARY KEY,
          run_id INTEGER,
          job_id INTEGER,
          seen_at TEXT NOT NULL,
          source_url TEXT NOT NULL,
          raw_excerpt TEXT NOT NULL DEFAULT '',
          prompt_injection_warning TEXT NOT NULL DEFAULT '',
          is_new INTEGER NOT NULL DEFAULT 0 CHECK (is_new IN (0, 1)),
          archived INTEGER NOT NULL DEFAULT 0 CHECK (archived IN (0, 1)),
          FOREIGN KEY (run_id) REFERENCES retrieval_runs(id) ON DELETE CASCADE,
          FOREIGN KEY (job_id) REFERENCES jobs(id) ON DELETE CASCADE
        );

        CREATE INDEX idx_jobs_company_id ON jobs(company_id);
        CREATE INDEX idx_jobs_first_seen_at ON jobs(first_seen_at);
        CREATE INDEX idx_jobs_archived ON jobs(archived);
        CREATE INDEX idx_companies_archived ON companies(archived);

        PRAGMA user_version = 1;
        """
    )
    conn.commit()


@dataclass(frozen=True)
class JobInput:
    company: str
    title: str
    source_url: str
    location: str = ""
    work_mode: str = ""
    function: str = ""
    url: str = ""
    external_id: str = ""
    description: str = ""
    posted_at: str = ""


def canonical_url(url: str) -> str:
    if not url:
        return ""
    parsed = urlsplit(url.strip())
    path = parsed.path.rstrip("/") or parsed.path
    return urlunsplit((parsed.scheme.lower(), parsed.netloc.lower(), path, "", ""))


def source_key(job: JobInput) -> str:
    if job.external_id.strip():
        return "external:" + job.external_id.strip().lower()
    if job.url.strip():
        return "url:" + canonical_url(job.url)
    basis = "\n".join(
        [
            job.company.strip().lower(),
            job.title.strip().lower(),
            job.location.strip().lower(),
            canonical_url(job.source_url),
        ]
    )
    return "hash:" + hashlib.sha256(basis.encode("utf-8")).hexdigest()


def add_company(
    conn: sqlite3.Connection,
    name: str,
    *,
    website_url: str = "",
    careers_url: str = "",
    research_url: str = "",
    notes: str = "",
) -> sqlite3.Row:
    if not name.strip():
        raise ValueError("company name is required")
    timestamp = now_utc()
    conn.execute(
        """
        INSERT INTO companies (name, website_url, careers_url, research_url, notes, created_at, updated_at, archived)
        VALUES (?, ?, ?, ?, ?, ?, ?, 0)
        ON CONFLICT(name) DO UPDATE SET
          website_url = COALESCE(NULLIF(excluded.website_url, ''), companies.website_url),
          careers_url = COALESCE(NULLIF(excluded.careers_url, ''), companies.careers_url),
          research_url = COALESCE(NULLIF(excluded.research_url, ''), companies.research_url),
          notes = COALESCE(NULLIF(excluded.notes, ''), companies.notes),
          updated_at = excluded.updated_at,
          archived = 0
        """,
        (name.strip(), website_url.strip(), careers_url.strip(), research_url.strip(), notes.strip(), timestamp, timestamp),
    )
    conn.commit()
    return conn.execute("SELECT * FROM companies WHERE name = ?", (name.strip(),)).fetchone()


def list_companies(conn: sqlite3.Connection, *, active_only: bool = True) -> list[sqlite3.Row]:
    clause = "WHERE archived = 0" if active_only else ""
    return list(conn.execute(f"SELECT * FROM companies {clause} ORDER BY name"))


def add_target(conn: sqlite3.Connection, kind: str, value: str) -> sqlite3.Row:
    if kind not in TARGET_KINDS:
        raise ValueError(f"unsupported target kind: {kind}")
    if not value.strip():
        raise ValueError("target value is required")
    timestamp = now_utc()
    conn.execute(
        """
        INSERT INTO targets (kind, value, created_at, updated_at, archived)
        VALUES (?, ?, ?, ?, 0)
        ON CONFLICT(kind, value) DO UPDATE SET updated_at = excluded.updated_at, archived = 0
        """,
        (kind, value.strip(), timestamp, timestamp),
    )
    conn.commit()
    return conn.execute("SELECT * FROM targets WHERE kind = ? AND value = ?", (kind, value.strip())).fetchone()


def replace_active_target(conn: sqlite3.Connection, kind: str, value: str) -> sqlite3.Row:
    """Keep exactly one active value for a singleton target such as cadence."""
    if kind not in TARGET_KINDS:
        raise ValueError(f"unsupported target kind: {kind}")
    if not value.strip():
        raise ValueError("target value is required")
    timestamp = now_utc()
    with conn:
        conn.execute(
            "UPDATE targets SET archived = 1, updated_at = ? WHERE kind = ? AND archived = 0 AND value <> ?",
            (timestamp, kind, value.strip()),
        )
        conn.execute(
            """
            INSERT INTO targets (kind, value, created_at, updated_at, archived)
            VALUES (?, ?, ?, ?, 0)
            ON CONFLICT(kind, value) DO UPDATE SET updated_at = excluded.updated_at, archived = 0
            """,
            (kind, value.strip(), timestamp, timestamp),
        )
    return conn.execute("SELECT * FROM targets WHERE kind = ? AND value = ?", (kind, value.strip())).fetchone()


def list_targets(conn: sqlite3.Connection, *, active_only: bool = True) -> list[sqlite3.Row]:
    clause = "WHERE archived = 0" if active_only else ""
    return list(conn.execute(f"SELECT * FROM targets {clause} ORDER BY kind, value"))


def archive_target(conn: sqlite3.Connection, kind: str, value: str) -> int:
    if kind not in TARGET_KINDS:
        raise ValueError(f"unsupported target kind: {kind}")
    if not value.strip():
        raise ValueError("target value is required")
    timestamp = now_utc()
    conn.execute(
        """
        INSERT INTO targets (kind, value, created_at, updated_at, archived)
        VALUES (?, ?, ?, ?, 1)
        ON CONFLICT(kind, value) DO UPDATE SET updated_at = excluded.updated_at, archived = 1
        """,
        (kind, value.strip(), timestamp, timestamp),
    )
    conn.commit()
    return 1


def create_run(conn: sqlite3.Connection, notes: str = "") -> sqlite3.Row:
    timestamp = now_utc()
    cur = conn.execute(
        "INSERT INTO retrieval_runs (started_at, notes) VALUES (?, ?)",
        (timestamp, notes.strip()),
    )
    conn.commit()
    return conn.execute("SELECT * FROM retrieval_runs WHERE id = ?", (cur.lastrowid,)).fetchone()


def finish_run(conn: sqlite3.Connection, run_id: int, *, status: str = "completed", error_count: int = 0) -> sqlite3.Row:
    timestamp = now_utc()
    new_job_count = conn.execute(
        """
        SELECT COALESCE(SUM(is_new), 0)
        FROM observations o
        WHERE o.run_id = ?
        """,
        (run_id,),
    ).fetchone()[0]
    conn.execute(
        """
        UPDATE retrieval_runs
        SET completed_at = ?, status = ?, new_job_count = ?, error_count = ?
        WHERE id = ?
        """,
        (timestamp, status, new_job_count, error_count, run_id),
    )
    conn.commit()
    return conn.execute("SELECT * FROM retrieval_runs WHERE id = ?", (run_id,)).fetchone()


def upsert_job(
    conn: sqlite3.Connection,
    job: JobInput,
    *,
    run_id: int | None = None,
    warnings: list[InjectionWarning] | None = None,
    raw_excerpt: str = "",
) -> tuple[sqlite3.Row, bool]:
    if not job.title.strip():
        raise ValueError("job title is required")
    if not job.source_url.strip():
        raise ValueError("source URL is required")

    company = add_company(conn, job.company)
    key = source_key(job)
    timestamp = now_utc()
    warning_text = " | ".join(f"{warning.reason} Evidence: {warning.snippet}" for warning in (warnings or []))

    existing = conn.execute(
        "SELECT * FROM jobs WHERE company_id = ? AND source_key = ?",
        (company["id"], key),
    ).fetchone()

    inserted = existing is None
    if inserted:
        cur = conn.execute(
            """
            INSERT INTO jobs (
              company_id, source_key, external_id, title, location, work_mode, function, url,
              source_url, description, prompt_injection_warning, first_seen_at, last_seen_at, posted_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                company["id"],
                key,
                job.external_id.strip(),
                job.title.strip(),
                job.location.strip(),
                job.work_mode.strip(),
                job.function.strip(),
                job.url.strip(),
                job.source_url.strip(),
                job.description.strip(),
                warning_text,
                timestamp,
                timestamp,
                job.posted_at.strip(),
            ),
        )
        job_id = cur.lastrowid
    else:
        job_id = existing["id"]
        conn.execute(
            """
            UPDATE jobs
            SET title = ?, location = ?, work_mode = ?, function = ?, url = ?,
                source_url = ?, description = ?, prompt_injection_warning = ?,
                last_seen_at = ?, posted_at = ?
            WHERE id = ?
            """,
            (
                job.title.strip(),
                job.location.strip(),
                job.work_mode.strip(),
                job.function.strip(),
                job.url.strip(),
                job.source_url.strip(),
                job.description.strip(),
                warning_text,
                timestamp,
                job.posted_at.strip(),
                job_id,
            ),
        )

    conn.execute(
        """
        INSERT INTO observations (run_id, job_id, seen_at, source_url, raw_excerpt, prompt_injection_warning, is_new)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (run_id, job_id, timestamp, job.source_url.strip(), raw_excerpt.strip()[:4000], warning_text, 1 if inserted else 0),
    )
    conn.commit()
    return conn.execute("SELECT * FROM jobs WHERE id = ?", (job_id,)).fetchone(), inserted


def visible_jobs(
    conn: sqlite3.Connection,
    *,
    since: str = "",
    company: str = "",
) -> list[sqlite3.Row]:
    clauses = ["j.archived = 0", "c.archived = 0"]
    values: list[str] = []
    if since:
        clauses.append("j.first_seen_at >= ?")
        values.append(since)
    if company:
        clauses.append("c.name = ?")
        values.append(company)

    return list(
        conn.execute(
            f"""
            SELECT j.*, c.name AS company_name, c.careers_url AS company_careers_url
            FROM jobs j
            JOIN companies c ON c.id = j.company_id
            WHERE {' AND '.join(clauses)}
              AND NOT EXISTS (
                SELECT 1
                FROM targets t
                WHERE t.archived = 1
                  AND (
                    (t.kind = 'role' AND lower(j.title || ' ' || j.function) LIKE '%' || lower(t.value) || '%')
                    OR (t.kind = 'industry' AND lower(j.description || ' ' || c.notes) LIKE '%' || lower(t.value) || '%')
                    OR (t.kind = 'location' AND lower(j.location) LIKE '%' || lower(t.value) || '%')
                  )
              )
            ORDER BY j.first_seen_at DESC, c.name, j.title
            """,
            values,
        )
    )


def job_counts(conn: sqlite3.Connection) -> dict[str, int]:
    """Return dashboard counts across all locally stored job records."""
    return {
        "total_jobs": conn.execute("SELECT COUNT(*) FROM jobs").fetchone()[0],
        "directly_archived_jobs": conn.execute("SELECT COUNT(*) FROM jobs WHERE archived = 1").fetchone()[0],
    }


def directly_archived_jobs(conn: sqlite3.Connection) -> list[sqlite3.Row]:
    """Return jobs explicitly archived by the user, including archived-company records."""
    return list(
        conn.execute(
            """
            SELECT j.*, c.name AS company_name, c.careers_url AS company_careers_url
            FROM jobs j
            JOIN companies c ON c.id = j.company_id
            WHERE j.archived = 1
            ORDER BY j.first_seen_at DESC, c.name, j.title
            """
        )
    )


def _target_values(conn: sqlite3.Connection, kind: str) -> list[str]:
    return [
        row["value"]
        for row in conn.execute(
            "SELECT value FROM targets WHERE kind = ? AND archived = 0 ORDER BY value",
            (kind,),
        )
    ]


def _contains(haystack: str, needle: str) -> bool:
    return needle.strip().lower() in haystack.lower()


def rank_jobs(conn: sqlite3.Connection, rows: list[sqlite3.Row]) -> list[dict[str, object]]:
    role_targets = _target_values(conn, "role")
    industry_targets = _target_values(conn, "industry")
    location_targets = _target_values(conn, "location")
    ranked: list[dict[str, object]] = []

    for row in rows:
        record = dict(row)
        title_function = f"{record.get('title', '')} {record.get('function', '')}"
        searchable = " ".join(str(record.get(key, "")) for key in ("title", "function", "description", "company_name"))
        location = str(record.get("location", ""))
        score = 0
        reasons: list[str] = []

        for target in role_targets:
            if _contains(title_function, target):
                score += 50
                reasons.append(f"role: {target}")
        for target in industry_targets:
            if _contains(searchable, target):
                score += 20
                reasons.append(f"industry: {target}")
        for target in location_targets:
            if _contains(location, target) or (target.lower() == "remote" and _contains(location, "remote")):
                score += 20
                reasons.append(f"location: {target}")
        if _contains(title_function, "program manager"):
            score += 10
            reasons.append("title contains Program Manager")

        record["fit_score"] = score
        record["fit_reasons"] = "; ".join(dict.fromkeys(reasons))
        ranked.append(record)

    return sorted(
        ranked,
        key=lambda item: (-int(item["fit_score"]), str(item["company_name"]).lower(), str(item["title"]).lower()),
    )


def find_jobs(conn: sqlite3.Connection, query: str, *, active_only: bool = True) -> list[sqlite3.Row]:
    clauses = [
        "(lower(j.title) LIKE ? OR lower(j.function) LIKE ? OR lower(j.location) LIKE ? OR lower(c.name) LIKE ?)"
    ]
    values = [f"%{query.strip().lower()}%"] * 4
    if active_only:
        clauses.extend(["j.archived = 0", "c.archived = 0"])
    return list(
        conn.execute(
            f"""
            SELECT j.*, c.name AS company_name
            FROM jobs j
            JOIN companies c ON c.id = j.company_id
            WHERE {' AND '.join(clauses)}
            ORDER BY c.name, j.title
            """,
            values,
        )
    )


def preview_target_archive(conn: sqlite3.Connection, kind: str, value: str) -> list[sqlite3.Row]:
    if kind not in {"role", "industry", "location"}:
        return []
    return list(
        conn.execute(
            """
            SELECT j.*, c.name AS company_name
            FROM jobs j
            JOIN companies c ON c.id = j.company_id
            WHERE j.archived = 0
              AND c.archived = 0
              AND (
                (? = 'role' AND lower(j.title || ' ' || j.function) LIKE '%' || lower(?) || '%')
                OR (? = 'industry' AND lower(j.description || ' ' || c.notes) LIKE '%' || lower(?) || '%')
                OR (? = 'location' AND lower(j.location) LIKE '%' || lower(?) || '%')
              )
            ORDER BY c.name, j.title
            """,
            (kind, value, kind, value, kind, value),
        )
    )


def archive_company(conn: sqlite3.Connection, name: str) -> int:
    cur = conn.execute(
        "UPDATE companies SET archived = 1, updated_at = ? WHERE name = ?",
        (now_utc(), name.strip()),
    )
    conn.commit()
    return cur.rowcount


def archive_job(conn: sqlite3.Connection, job_id: int) -> int:
    cur = conn.execute("UPDATE jobs SET archived = 1 WHERE id = ?", (job_id,))
    conn.commit()
    return cur.rowcount


def job_reset_counts(conn: sqlite3.Connection) -> dict[str, int]:
    """Count the rows a job-findings reset would delete or preserve."""
    return {
        "jobs": conn.execute("SELECT COUNT(*) FROM jobs").fetchone()[0],
        "observations": conn.execute("SELECT COUNT(*) FROM observations").fetchone()[0],
        "retrieval_runs": conn.execute("SELECT COUNT(*) FROM retrieval_runs").fetchone()[0],
        "companies": conn.execute("SELECT COUNT(*) FROM companies").fetchone()[0],
        "targets": conn.execute("SELECT COUNT(*) FROM targets").fetchone()[0],
    }


def reset_jobs(conn: sqlite3.Connection) -> dict[str, int]:
    """Delete job findings and run history while preserving profile targets and companies."""
    before = job_reset_counts(conn)
    with conn:
        conn.execute("DELETE FROM observations")
        conn.execute("DELETE FROM jobs")
        conn.execute("DELETE FROM retrieval_runs")

    return {
        "deleted_jobs": before["jobs"],
        "deleted_observations": before["observations"],
        "deleted_retrieval_runs": before["retrieval_runs"],
        "preserved_companies": before["companies"],
        "preserved_targets": before["targets"],
    }


def status(conn: sqlite3.Connection, state_dir: str | Path | None = None) -> dict[str, object]:
    active_companies = conn.execute("SELECT COUNT(*) FROM companies WHERE archived = 0").fetchone()[0]
    stored_active_jobs = conn.execute(
        """
        SELECT COUNT(*)
        FROM jobs j
        JOIN companies c ON c.id = j.company_id
        WHERE j.archived = 0 AND c.archived = 0
        """
    ).fetchone()[0]
    active_targets = conn.execute("SELECT COUNT(*) FROM targets WHERE archived = 0").fetchone()[0]
    latest_run = conn.execute("SELECT * FROM retrieval_runs ORDER BY id DESC LIMIT 1").fetchone()
    return {
        "state_dir": str(ensure_state_dir(state_dir)),
        "database": str(db_path(state_dir)),
        "user_md": str(user_md_path(state_dir)),
        "active_companies": active_companies,
        "active_jobs": stored_active_jobs,
        "visible_jobs": len(visible_jobs(conn)),
        "active_targets": active_targets,
        "latest_run": dict(latest_run) if latest_run else None,
    }


def dump_json(payload: object) -> str:
    return json.dumps(payload, indent=2, sort_keys=True)
