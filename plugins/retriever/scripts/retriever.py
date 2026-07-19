#!/usr/bin/env python3
"""Command-line runtime for the Retriever Codex plugin."""

from __future__ import annotations

import argparse
import json
import secrets
import subprocess
import sys
from pathlib import Path

from retriever_core import dashboard, db, profile, reports
from retriever_core.db import JobInput
from retriever_core.injection import scan_text


def state_dir_from_args(args: argparse.Namespace) -> Path:
    return db.ensure_state_dir(args.state_dir)


def raw_state_dir_from_args(args: argparse.Namespace) -> Path:
    return db.resolve_state_dir(args.state_dir)


def _setup_required_response(state_dir: Path) -> dict[str, object]:
    return {
        "requires_onboarding": True,
        "message": (
            "Retriever is not configured for retrieval. Complete interactive onboarding before scanning career sites; "
            "no retrieval run was created."
        ),
        "setup": db.setup_status(state_dir),
    }


def cmd_init(args: argparse.Namespace) -> int:
    state_dir = raw_state_dir_from_args(args)
    setup = db.setup_status(state_dir)
    if setup["database_exists"] and setup["database_integrity"] != "ok":
        print(
            db.dump_json(
                {
                    "requires_repair": True,
                    "message": "Retriever found an unreadable or invalid database. Do not overwrite it automatically; ask the user whether to repair or reset local state.",
                    "setup": setup,
                }
            )
        )
        return 2
    state_dir = db.ensure_state_dir(state_dir)
    conn = db.connect(state_dir)
    print(db.dump_json(db.status(conn, state_dir)))
    return 0


def cmd_status(args: argparse.Namespace) -> int:
    print(db.dump_json(db.setup_status(raw_state_dir_from_args(args))))
    return 0


def cmd_setup_status(args: argparse.Namespace) -> int:
    print(db.dump_json(db.setup_status(raw_state_dir_from_args(args))))
    return 0


def cmd_profile_write(args: argparse.Namespace) -> int:
    state_dir = raw_state_dir_from_args(args)
    setup = db.setup_status(state_dir)
    if setup["database_exists"] and setup["database_integrity"] != "ok":
        print(
            db.dump_json(
                {
                    "requires_repair": True,
                    "message": "Retriever found an unreadable or invalid database. Do not overwrite it automatically; ask the user whether to repair or reset local state.",
                    "setup": setup,
                }
            )
        )
        return 2
    state_dir = db.ensure_state_dir(state_dir)
    conn = db.connect(state_dir)
    if args.json == "-":
        payload = json.load(sys.stdin)
    else:
        payload = profile.load_profile_json(args.json)
    path = profile.write_profile(conn, payload, state_dir=state_dir)
    print(db.dump_json({"user_md": str(path)}))
    return 0


def cmd_company_add(args: argparse.Namespace) -> int:
    conn = db.connect(state_dir_from_args(args))
    row = db.add_company(
        conn,
        args.name,
        website_url=args.website_url,
        careers_url=args.careers_url,
        research_url=args.research_url,
        notes=args.notes,
    )
    print(db.dump_json(dict(row)))
    return 0


def cmd_company_list(args: argparse.Namespace) -> int:
    conn = db.connect(state_dir_from_args(args))
    rows = [dict(row) for row in db.list_companies(conn, active_only=not args.all)]
    print(db.dump_json(rows))
    return 0


def cmd_company_archive(args: argparse.Namespace) -> int:
    conn = db.connect(state_dir_from_args(args))
    count = db.archive_company(conn, args.name)
    print(db.dump_json({"archived": count, "company": args.name}))
    return 0 if count else 1


def cmd_run_start(args: argparse.Namespace) -> int:
    state_dir = raw_state_dir_from_args(args)
    setup = db.setup_status(state_dir)
    if not setup["ready_for_retrieval"]:
        print(db.dump_json(_setup_required_response(state_dir)))
        return 2
    conn = db.connect(state_dir)
    row = db.create_run(conn, notes=args.notes)
    print(db.dump_json(dict(row)))
    return 0


def cmd_run_finish(args: argparse.Namespace) -> int:
    state_dir = raw_state_dir_from_args(args)
    setup = db.setup_status(state_dir)
    if setup["database_integrity"] != "ok":
        print(db.dump_json(_setup_required_response(state_dir)))
        return 2
    conn = db.connect(state_dir)
    row = db.finish_run(conn, args.run_id, status=args.status, error_count=args.error_count)
    if row is None:
        print(
            db.dump_json(
                {
                    "run_not_found": True,
                    "message": "Retriever could not finish that retrieval run because it does not exist in the current local database.",
                    "run_id": args.run_id,
                }
            )
        )
        return 1
    print(db.dump_json(dict(row)))
    return 0


def _read_optional_file(path: str) -> str:
    if not path:
        return ""
    return Path(path).expanduser().read_text(encoding="utf-8")


def cmd_job_upsert(args: argparse.Namespace) -> int:
    conn = db.connect(state_dir_from_args(args))
    observed_text = args.observed_text or _read_optional_file(args.observed_text_file)
    description = args.description or _read_optional_file(args.description_file)
    warnings = scan_text("\n".join([observed_text, description]))
    job, inserted = db.upsert_job(
        conn,
        JobInput(
            company=args.company,
            title=args.title,
            location=args.location,
            work_mode=args.work_mode,
            function=args.function,
            url=args.url,
            source_url=args.source_url,
            external_id=args.external_id,
            description=description,
            posted_at=args.posted_at,
        ),
        run_id=args.run_id,
        warnings=warnings,
        raw_excerpt=observed_text or description,
    )
    print(
        db.dump_json(
            {
                "job": dict(job),
                "new": inserted,
                "prompt_injection_warnings": [warning.as_dict() for warning in warnings],
            }
        )
    )
    return 0


def cmd_job_archive(args: argparse.Namespace) -> int:
    conn = db.connect(state_dir_from_args(args))
    count = db.archive_job(conn, args.job_id)
    print(db.dump_json({"archived": count, "job_id": args.job_id}))
    return 0 if count else 1


def cmd_job_search(args: argparse.Namespace) -> int:
    conn = db.connect(state_dir_from_args(args))
    rows = [dict(row) for row in db.find_jobs(conn, args.query, active_only=not args.all)]
    print(db.dump_json({"query": args.query, "matches": rows, "count": len(rows)}))
    return 0


def cmd_target_list(args: argparse.Namespace) -> int:
    conn = db.connect(state_dir_from_args(args))
    rows = [dict(row) for row in db.list_targets(conn, active_only=not args.all)]
    print(db.dump_json(rows))
    return 0


def cmd_target_archive(args: argparse.Namespace) -> int:
    conn = db.connect(state_dir_from_args(args))
    preview = [dict(row) for row in db.preview_target_archive(conn, args.kind, args.value)]
    if not args.force:
        print(
            db.dump_json(
                {
                    "requires_confirmation": True,
                    "message": "Target/category archive can hide multiple jobs. Show this preview to the user and rerun with --force only after explicit confirmation.",
                    "kind": args.kind,
                    "value": args.value,
                    "matching_visible_jobs": preview,
                    "matching_visible_job_count": len(preview),
                }
            )
        )
        return 2
    count = db.archive_target(conn, args.kind, args.value)
    print(
        db.dump_json(
            {
                "archived": count,
                "kind": args.kind,
                "value": args.value,
                "matching_visible_job_count_at_confirmation": len(preview),
            }
        )
    )
    return 0 if count else 1


def cmd_target_preview(args: argparse.Namespace) -> int:
    conn = db.connect(state_dir_from_args(args))
    preview = [dict(row) for row in db.preview_target_archive(conn, args.kind, args.value)]
    print(
        db.dump_json(
            {
                "kind": args.kind,
                "value": args.value,
                "matching_visible_jobs": preview,
                "matching_visible_job_count": len(preview),
            }
        )
    )
    return 0


def cmd_reset_jobs(args: argparse.Namespace) -> int:
    conn = db.connect(state_dir_from_args(args))
    counts = db.job_reset_counts(conn)
    if not args.confirm_delete:
        print(
            db.dump_json(
                {
                    "requires_confirmation": True,
                    "message": "This will permanently delete job findings, observations, and retrieval-run history while preserving USER.md, companies, and targets. Rerun with --confirm-delete only after the user explicitly chooses a fresh job-findings reset.",
                    "would_delete_jobs": counts["jobs"],
                    "would_delete_observations": counts["observations"],
                    "would_delete_retrieval_runs": counts["retrieval_runs"],
                    "would_preserve_companies": counts["companies"],
                    "would_preserve_targets": counts["targets"],
                }
            )
        )
        return 2

    print(db.dump_json(db.reset_jobs(conn)))
    return 0


def cmd_report(args: argparse.Namespace) -> int:
    state_dir = state_dir_from_args(args)
    conn = db.connect(state_dir)
    rows = db.visible_jobs(conn, since=args.since, company=args.company)
    if args.ranked:
        rows = db.rank_jobs(conn, rows)
    total_count = len(rows)
    if args.limit > 0:
        rows = rows[: args.limit]
    if args.format == "csv":
        content = reports.jobs_to_csv(rows)
    elif args.format == "html":
        content = reports.jobs_to_html(rows, total_count=total_count, ranked=args.ranked)
    else:
        content = reports.jobs_to_markdown(rows, total_count=total_count, ranked=args.ranked)

    if args.output:
        output = Path(args.output).expanduser()
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(content, encoding="utf-8")
        print(db.dump_json({"output": str(output), "jobs": len(rows)}))
    else:
        print(content)
    return 0


def cmd_dashboard_serve(args: argparse.Namespace) -> int:
    state_dir = raw_state_dir_from_args(args)
    setup = db.setup_status(state_dir)
    if setup["database_integrity"] != "ok":
        print(
            db.dump_json(
                {
                    "requires_valid_database": True,
                    "message": "Retriever needs a valid local database before it can start the interactive dashboard. No local state was created.",
                    "setup": setup,
                }
            )
        )
        return 2
    managed = bool(args.service_id)
    if managed != bool(args.control_token) or managed != bool(args.service_state):
        print(
            db.dump_json(
                {
                    "invalid_dashboard_service": True,
                    "message": "Managed dashboard serving requires matching internal service metadata.",
                }
            )
        )
        return 2
    if args.service_state:
        expected_state_path = dashboard.service_state_path(state_dir).resolve()
        supplied_state_path = Path(args.service_state).expanduser().resolve()
        if supplied_state_path != expected_state_path:
            print(
                db.dump_json(
                    {
                        "invalid_dashboard_service": True,
                        "message": "Managed dashboard metadata must remain inside the Retriever state directory.",
                    }
                )
            )
            return 2

    server = dashboard.create_dashboard_server(
        state_dir,
        port=args.port,
        ranked=args.ranked,
        service_id=args.service_id,
        control_token=args.control_token,
    )
    host, port = server.server_address[:2]
    if managed:
        dashboard.write_service_state(
            state_dir,
            service_id=args.service_id,
            control_token=args.control_token,
            port=port,
            ranked=args.ranked,
        )
    print(
        db.dump_json(
            {
                "dashboard_url": f"http://{host}:{port}/",
                "managed": managed,
                "message": "Interactive dashboard is local-only. Press Ctrl-C to stop it." if not managed else "Interactive dashboard is local-only and managed by Retriever.",
            }
        ),
        flush=True,
    )
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        return 0
    finally:
        server.server_close()
        if managed:
            dashboard.clear_service_state(state_dir, args.service_id)
    return 0


def cmd_dashboard_start(args: argparse.Namespace) -> int:
    state_dir = raw_state_dir_from_args(args)
    setup = db.setup_status(state_dir)
    if setup["database_integrity"] != "ok":
        print(
            db.dump_json(
                {
                    "requires_valid_database": True,
                    "message": "Retriever needs a valid local database before it can start the interactive dashboard. No local state was created.",
                    "setup": setup,
                }
            )
        )
        return 2

    existing = dashboard.active_service(state_dir)
    if existing is not None:
        print(
            db.dump_json(
                {
                    "started": False,
                    "dashboard_url": f"http://127.0.0.1:{existing['port']}/",
                    "ranked": existing["ranked"],
                    "message": "Retriever is reusing the active local dashboard.",
                }
            )
        )
        return 0

    service_id = secrets.token_urlsafe(18)
    control_token = secrets.token_urlsafe(32)
    service_state = dashboard.service_state_path(state_dir)
    service_log = state_dir / "dashboard-service.log"
    command = [
        sys.executable,
        str(Path(__file__).resolve()),
        "--state-dir",
        str(state_dir),
        "dashboard",
        "serve",
        "--port",
        str(args.port),
        "--service-state",
        str(service_state),
        "--service-id",
        service_id,
        "--control-token",
        control_token,
    ]
    if args.ranked:
        command.append("--ranked")
    with service_log.open("w", encoding="utf-8") as log_file:
        process = subprocess.Popen(
            command,
            stdin=subprocess.DEVNULL,
            stdout=log_file,
            stderr=subprocess.STDOUT,
            start_new_session=True,
        )
    active = dashboard.wait_for_active_service(state_dir, service_id)
    if active is None:
        if process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=2)
            except subprocess.TimeoutExpired:
                process.kill()
        print(
            db.dump_json(
                {
                    "started": False,
                    "dashboard_unavailable": True,
                    "message": "Retriever could not start the local dashboard service.",
                }
            )
        )
        return 1

    print(
        db.dump_json(
            {
                "started": True,
                "dashboard_url": f"http://127.0.0.1:{active['port']}/",
                "ranked": active["ranked"],
                "message": "Retriever started the local interactive dashboard.",
            }
        )
    )
    return 0


def cmd_dashboard_stop(args: argparse.Namespace) -> int:
    state_dir = raw_state_dir_from_args(args)
    active = dashboard.active_service(state_dir)
    if active is None:
        print(db.dump_json({"stopped": False, "message": "No managed Retriever dashboard is running."}))
        return 0
    if not dashboard.request_stop(active) or not dashboard.wait_for_stop(state_dir):
        print(db.dump_json({"stopped": False, "message": "Retriever could not stop the managed local dashboard."}))
        return 1
    print(db.dump_json({"stopped": True, "message": "Retriever stopped the managed local dashboard."}))
    return 0


def cmd_dashboard_status(args: argparse.Namespace) -> int:
    active = dashboard.active_service(raw_state_dir_from_args(args))
    if active is None:
        print(db.dump_json({"running": False}))
        return 0
    print(
        db.dump_json(
            {
                "running": True,
                "dashboard_url": f"http://127.0.0.1:{active['port']}/",
                "ranked": active["ranked"],
            }
        )
    )
    return 0


def cmd_scan_injection(args: argparse.Namespace) -> int:
    text = args.text or _read_optional_file(args.file)
    warnings = scan_text(text)
    print(db.dump_json({"warnings": [warning.as_dict() for warning in warnings]}))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Retriever local job-intelligence runtime.")
    parser.add_argument(
        "--state-dir",
        default=None,
        help="Override the local state directory. Defaults to ~/.retriever.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    init = sub.add_parser("init", help="Create the local state directory and SQLite database.")
    init.set_defaults(func=cmd_init)

    status = sub.add_parser("status", help="Show local Retriever setup state without creating it.")
    status.set_defaults(func=cmd_status)

    setup_status = sub.add_parser(
        "setup-status",
        help="Check local profile and database integrity before onboarding or retrieval without creating local state.",
    )
    setup_status.set_defaults(func=cmd_setup_status)

    profile_parser = sub.add_parser("profile", help="Create or update USER.md.")
    profile_sub = profile_parser.add_subparsers(dest="profile_command", required=True)
    profile_write = profile_sub.add_parser("write", help="Write USER.md from a JSON profile.")
    profile_write.add_argument("--json", required=True, help="Profile JSON path, or '-' for stdin.")
    profile_write.set_defaults(func=cmd_profile_write)

    company = sub.add_parser("company", help="Manage companies.")
    company_sub = company.add_subparsers(dest="company_command", required=True)
    company_add = company_sub.add_parser("add", help="Add or update a company.")
    company_add.add_argument("name")
    company_add.add_argument("--website-url", default="")
    company_add.add_argument("--careers-url", default="")
    company_add.add_argument("--research-url", default="")
    company_add.add_argument("--notes", default="")
    company_add.set_defaults(func=cmd_company_add)
    company_list = company_sub.add_parser("list", help="List companies.")
    company_list.add_argument("--all", action="store_true", help="Include archived companies.")
    company_list.set_defaults(func=cmd_company_list)
    company_archive = company_sub.add_parser("archive", help="Archive a company.")
    company_archive.add_argument("name")
    company_archive.set_defaults(func=cmd_company_archive)

    run = sub.add_parser("run", help="Track retrieval runs.")
    run_sub = run.add_subparsers(dest="run_command", required=True)
    run_start = run_sub.add_parser("start", help="Start a retrieval run.")
    run_start.add_argument("--notes", default="")
    run_start.set_defaults(func=cmd_run_start)
    run_finish = run_sub.add_parser("finish", help="Finish a retrieval run.")
    run_finish.add_argument("run_id", type=int)
    run_finish.add_argument("--status", default="completed")
    run_finish.add_argument("--error-count", type=int, default=0)
    run_finish.set_defaults(func=cmd_run_finish)

    job = sub.add_parser("job", help="Manage observed jobs.")
    job_sub = job.add_subparsers(dest="job_command", required=True)
    job_upsert = job_sub.add_parser("upsert", help="Create or update a job sighting.")
    job_upsert.add_argument("--company", required=True)
    job_upsert.add_argument("--title", required=True)
    job_upsert.add_argument("--source-url", required=True)
    job_upsert.add_argument("--location", default="")
    job_upsert.add_argument("--work-mode", default="")
    job_upsert.add_argument("--function", default="")
    job_upsert.add_argument("--url", default="")
    job_upsert.add_argument("--external-id", default="")
    job_upsert.add_argument("--description", default="")
    job_upsert.add_argument("--description-file", default="")
    job_upsert.add_argument("--observed-text", default="")
    job_upsert.add_argument("--observed-text-file", default="")
    job_upsert.add_argument("--posted-at", default="")
    job_upsert.add_argument("--run-id", type=int, default=None)
    job_upsert.set_defaults(func=cmd_job_upsert)
    job_archive = job_sub.add_parser("archive", help="Archive a job.")
    job_archive.add_argument("job_id", type=int)
    job_archive.set_defaults(func=cmd_job_archive)
    job_search = job_sub.add_parser("search", help="Preview jobs matching a text query before archiving.")
    job_search.add_argument("--query", required=True)
    job_search.add_argument("--all", action="store_true", help="Include archived jobs or archived-company jobs.")
    job_search.set_defaults(func=cmd_job_search)

    target = sub.add_parser("target", help="Manage target roles, industries, locations, and cadence.")
    target_sub = target.add_subparsers(dest="target_command", required=True)
    target_list = target_sub.add_parser("list", help="List targets.")
    target_list.add_argument("--all", action="store_true", help="Include archived targets.")
    target_list.set_defaults(func=cmd_target_list)
    target_archive = target_sub.add_parser("archive", help="Archive a target value.")
    target_archive.add_argument("--force", action="store_true", help="Required after explicit user confirmation.")
    target_archive.add_argument("kind", choices=["role", "industry", "location", "company", "cadence"])
    target_archive.add_argument("value")
    target_archive.set_defaults(func=cmd_target_archive)
    target_preview = target_sub.add_parser("preview", help="Preview jobs that a target/category archive would hide.")
    target_preview.add_argument("kind", choices=["role", "industry", "location"])
    target_preview.add_argument("value")
    target_preview.set_defaults(func=cmd_target_preview)

    reset = sub.add_parser("reset", help="Delete local Retriever data by explicit scope.")
    reset_sub = reset.add_subparsers(dest="reset_command", required=True)
    reset_jobs = reset_sub.add_parser(
        "jobs",
        help="Delete job findings and retrieval-run history while preserving USER.md, companies, and targets.",
    )
    reset_jobs.add_argument(
        "--confirm-delete",
        action="store_true",
        help="Required to permanently delete job findings after the preview has been shown to the user.",
    )
    reset_jobs.set_defaults(func=cmd_reset_jobs)

    report = sub.add_parser("report", help="Export visible jobs.")
    report.add_argument("--format", choices=["markdown", "csv", "html"], default="markdown")
    report.add_argument("--output", default="")
    report.add_argument("--since", default="")
    report.add_argument("--company", default="")
    report.add_argument("--ranked", action="store_true", help="Rank jobs by active role, industry, and location targets.")
    report.add_argument("--limit", type=int, default=0, help="Limit displayed rows. Default 0 shows all rows.")
    report.set_defaults(func=cmd_report)

    dashboard_parser = sub.add_parser("dashboard", help="Manage the interactive local job dashboard.")
    dashboard_sub = dashboard_parser.add_subparsers(dest="dashboard_command", required=True)
    dashboard_serve = dashboard_sub.add_parser("serve", help="Start a loopback-only dashboard with archive controls.")
    dashboard_serve.add_argument("--port", type=int, default=0, help="Local port; default 0 chooses an available port.")
    dashboard_serve.add_argument("--ranked", action="store_true", help="Rank visible jobs before rendering.")
    dashboard_serve.add_argument("--service-state", default="", help=argparse.SUPPRESS)
    dashboard_serve.add_argument("--service-id", default="", help=argparse.SUPPRESS)
    dashboard_serve.add_argument("--control-token", default="", help=argparse.SUPPRESS)
    dashboard_serve.set_defaults(func=cmd_dashboard_serve)
    dashboard_start = dashboard_sub.add_parser("start", help="Start or reuse the managed loopback dashboard.")
    dashboard_start.add_argument("--port", type=int, default=0, help="Local port; default 0 chooses an available port.")
    dashboard_start.add_argument("--ranked", action="store_true", help="Rank visible jobs before rendering.")
    dashboard_start.set_defaults(func=cmd_dashboard_start)
    dashboard_stop = dashboard_sub.add_parser("stop", help="Stop the managed loopback dashboard.")
    dashboard_stop.set_defaults(func=cmd_dashboard_stop)
    dashboard_status = dashboard_sub.add_parser("status", help="Show whether the managed local dashboard is running.")
    dashboard_status.set_defaults(func=cmd_dashboard_status)

    scan = sub.add_parser("scan-injection", help="Scan text for prompt-injection warnings.")
    scan.add_argument("--text", default="")
    scan.add_argument("--file", default="")
    scan.set_defaults(func=cmd_scan_injection)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
