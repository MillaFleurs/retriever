"""Report writers for Retriever."""

from __future__ import annotations

import csv
import io
from collections.abc import Iterable

from .db import now_utc


REPORT_COLUMNS = [
    "id",
    "company",
    "title",
    "location",
    "fit_score",
    "fit_reasons",
    "work_mode",
    "function",
    "url",
    "source_url",
    "first_seen_at",
    "last_seen_at",
    "prompt_injection_warning",
]


def _cell(value: object) -> str:
    return str(value or "").replace("\n", " ").strip()


def jobs_to_csv(rows: Iterable[object]) -> str:
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=REPORT_COLUMNS)
    writer.writeheader()
    for row in rows:
        writer.writerow(
            {
                "id": row["id"],
                "company": row["company_name"],
                "title": row["title"],
                "location": row["location"],
                "fit_score": row["fit_score"] if "fit_score" in row.keys() else "",
                "fit_reasons": row["fit_reasons"] if "fit_reasons" in row.keys() else "",
                "work_mode": row["work_mode"],
                "function": row["function"],
                "url": row["url"],
                "source_url": row["source_url"],
                "first_seen_at": row["first_seen_at"],
                "last_seen_at": row["last_seen_at"],
                "prompt_injection_warning": row["prompt_injection_warning"],
            }
        )
    return output.getvalue()


def _escape_markdown_table(value: object) -> str:
    return _cell(value).replace("|", "\\|")


def _has_key(row: object, key: str) -> bool:
    if isinstance(row, dict):
        return key in row
    return key in row.keys()


def jobs_to_markdown(
    rows: list[object],
    *,
    heading: str = "Retriever Job Report",
    total_count: int | None = None,
    ranked: bool = False,
) -> str:
    lines = [
        f"# {heading}",
        "",
        f"Generated: {now_utc()}",
        "",
    ]
    if not rows:
        lines.extend(["No active jobs matched the current filters.", ""])
        return "\n".join(lines)

    if total_count is not None and total_count != len(rows):
        lines.extend(
            [
                f"Showing {len(rows)} of {total_count} visible jobs.",
                "Run the report without a limit or export CSV to see the entire database.",
                "",
            ]
        )
    elif total_count is not None:
        lines.extend([f"Showing all {total_count} visible jobs.", ""])
    if ranked:
        lines.extend(["Ranked by active role, industry, and location targets.", ""])

    lines.extend(
        [
            "| ID | Company | Title | Location | Fit | Link | First Seen | Warning |",
            "| --- | --- | --- | --- | --- | --- | --- | --- |",
        ]
    )
    for row in rows:
        link = row["url"] or row["source_url"]
        warning = "Yes" if row["prompt_injection_warning"] else ""
        fit = ""
        if _has_key(row, "fit_score") and row["fit_score"] != "":
            fit = f"{row['fit_score']} {row['fit_reasons']}".strip()
        lines.append(
            "| {id} | {company} | {title} | {location} | {fit} | {link} | {first_seen} | {warning} |".format(
                id=row["id"],
                company=_escape_markdown_table(row["company_name"]),
                title=_escape_markdown_table(row["title"]),
                location=_escape_markdown_table(row["location"]),
                fit=_escape_markdown_table(fit),
                link=_escape_markdown_table(link),
                first_seen=_escape_markdown_table(row["first_seen_at"]),
                warning=warning,
            )
        )

    warned = [row for row in rows if row["prompt_injection_warning"]]
    if warned:
        lines.extend(["", "## Prompt-Injection Warnings", ""])
        for row in warned:
            lines.append(f"- Job {row['id']} ({row['company_name']} - {row['title']}): {row['prompt_injection_warning']}")

    lines.append("")
    return "\n".join(lines)
