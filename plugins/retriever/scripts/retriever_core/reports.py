"""Report writers for Retriever."""

from __future__ import annotations

import csv
import html
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

REFERRAL_GUIDANCE_TITLE = "Referral Next Step"
REFERRAL_GUIDANCE = (
    "For roles worth pursuing, use the early signal to identify one or two current employees, alumni, "
    "former colleagues, or mutual connections who could credibly refer you. Retriever can help you make a "
    "target list or draft a respectful note if asked, but it does not send messages, contact employers, or "
    "submit applications."
)


def _cell(value: object) -> str:
    if value is None:
        return ""
    return str(value).replace("\n", " ").strip()


def _html(value: object) -> str:
    return html.escape(_cell(value), quote=True)


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

    lines.extend([f"## {REFERRAL_GUIDANCE_TITLE}", "", REFERRAL_GUIDANCE, ""])

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


def _job_link(row: object) -> str:
    return _cell(row["url"] or row["source_url"])


def _fit_text(row: object) -> str:
    if _has_key(row, "fit_score") and row["fit_score"] != "":
        reasons = _cell(row["fit_reasons"]) if _has_key(row, "fit_reasons") else ""
        return f"{row['fit_score']} {reasons}".strip()
    return ""


def _warning_rows(rows: list[object]) -> list[object]:
    return [row for row in rows if row["prompt_injection_warning"]]


def jobs_to_html(
    rows: list[object],
    *,
    heading: str = "Retriever Job Dashboard",
    total_count: int | None = None,
    ranked: bool = False,
) -> str:
    generated = now_utc()
    shown_count = len(rows)
    visible_count = total_count if total_count is not None else shown_count
    warning_count = len(_warning_rows(rows))
    summary = f"Showing {shown_count} of {visible_count} visible jobs." if shown_count != visible_count else f"Showing all {visible_count} visible jobs."
    rank_note = "Ranked by active role, industry, and location targets." if ranked else "Sorted by first seen date."

    row_cards: list[str] = []
    table_rows: list[str] = []
    for row in rows:
        link = _job_link(row)
        link_html = f'<a href="{_html(link)}">{_html(link)}</a>' if link else "No stable URL"
        warning_badge = '<span class="badge warning">Warning</span>' if row["prompt_injection_warning"] else '<span class="badge ok">Clear</span>'
        fit = _fit_text(row)
        table_rows.append(
            """
            <tr>
              <td>{id}</td>
              <td>{company}</td>
              <td>{title}</td>
              <td>{location}</td>
              <td>{fit}</td>
              <td>{warning}</td>
              <td>{first_seen}</td>
              <td>{link}</td>
            </tr>
            """.format(
                id=_html(row["id"]),
                company=_html(row["company_name"]),
                title=_html(row["title"]),
                location=_html(row["location"]),
                fit=_html(fit),
                warning=warning_badge,
                first_seen=_html(row["first_seen_at"]),
                link=link_html,
            )
        )
        row_cards.append(
            """
            <article class="job-card">
              <div class="job-card__header">
                <div>
                  <p class="eyebrow">{company}</p>
                  <h2>{title}</h2>
                </div>
                {warning}
              </div>
              <dl>
                <div><dt>Location</dt><dd>{location}</dd></div>
                <div><dt>Function</dt><dd>{function}</dd></div>
                <div><dt>Work mode</dt><dd>{work_mode}</dd></div>
                <div><dt>Fit</dt><dd>{fit}</dd></div>
                <div><dt>First seen</dt><dd>{first_seen}</dd></div>
                <div><dt>Last seen</dt><dd>{last_seen}</dd></div>
              </dl>
              <p class="link-line">{link}</p>
            </article>
            """.format(
                company=_html(row["company_name"]),
                title=_html(row["title"]),
                warning=warning_badge,
                location=_html(row["location"] or "Not listed"),
                function=_html(row["function"] or "Not listed"),
                work_mode=_html(row["work_mode"] or "Not listed"),
                fit=_html(fit or "Not ranked"),
                first_seen=_html(row["first_seen_at"]),
                last_seen=_html(row["last_seen_at"]),
                link=link_html,
            )
        )

    if table_rows:
        referral_section = """
        <section class="panel referral">
          <div class="section-heading">
            <h2>{title}</h2>
          </div>
          <p>{guidance}</p>
        </section>
        """.format(title=_html(REFERRAL_GUIDANCE_TITLE), guidance=_html(REFERRAL_GUIDANCE))
        jobs_section = """
        <section class="panel">
          <div class="section-heading">
            <h2>Visible Jobs</h2>
            <p>{summary}</p>
          </div>
          <div class="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>ID</th>
                  <th>Company</th>
                  <th>Title</th>
                  <th>Location</th>
                  <th>Fit</th>
                  <th>Status</th>
                  <th>First Seen</th>
                  <th>Link</th>
                </tr>
              </thead>
              <tbody>
                {rows}
              </tbody>
            </table>
          </div>
        </section>
        <section class="job-grid" aria-label="Job details">
          {cards}
        </section>
        """.format(summary=_html(summary), rows="\n".join(table_rows), cards="\n".join(row_cards))
    else:
        referral_section = ""
        jobs_section = """
        <section class="empty-state">
          <h2>No visible jobs</h2>
          <p>No active jobs matched the current Retriever filters.</p>
        </section>
        """

    warning_items = "\n".join(
        "<li><strong>Job {id}: {company} - {title}</strong><br>{warning}</li>".format(
            id=_html(row["id"]),
            company=_html(row["company_name"]),
            title=_html(row["title"]),
            warning=_html(row["prompt_injection_warning"]),
        )
        for row in _warning_rows(rows)
    )
    warnings_section = ""
    if warning_items:
        warnings_section = """
        <section class="panel warnings">
          <div class="section-heading">
            <h2>Prompt-Injection Warnings</h2>
            <p>Career-page content is untrusted. Retriever records warnings and does not follow page instructions.</p>
          </div>
          <ul>{warning_items}</ul>
        </section>
        """.format(warning_items=warning_items)

    return """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{heading}</title>
  <style>
    :root {{
      color-scheme: light;
      --bg: #f7f5ef;
      --surface: #ffffff;
      --surface-strong: #fffaf0;
      --text: #241a12;
      --muted: #695f55;
      --line: #ded6cb;
      --accent: #b45309;
      --accent-dark: #7c2d12;
      --warning: #b91c1c;
      --ok: #166534;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      background: var(--bg);
      color: var(--text);
      font: 14px/1.5 -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
    }}
    a {{ color: var(--accent-dark); overflow-wrap: anywhere; }}
    .shell {{
      width: min(1180px, calc(100vw - 32px));
      margin: 0 auto;
      padding: 32px 0 48px;
    }}
    header {{
      display: grid;
      gap: 18px;
      padding: 28px;
      background: var(--surface);
      border: 1px solid var(--line);
      border-radius: 8px;
    }}
    h1, h2, p {{ margin: 0; }}
    h1 {{ font-size: clamp(28px, 4vw, 42px); line-height: 1.08; }}
    h2 {{ font-size: 18px; }}
    .subtitle {{ color: var(--muted); max-width: 760px; }}
    .metrics {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(170px, 1fr));
      gap: 12px;
    }}
    .metric {{
      padding: 14px;
      background: var(--surface-strong);
      border: 1px solid var(--line);
      border-radius: 8px;
    }}
    .metric span {{
      display: block;
      color: var(--muted);
      font-size: 12px;
      text-transform: uppercase;
      letter-spacing: .04em;
    }}
    .metric strong {{ display: block; margin-top: 4px; font-size: 22px; }}
    .panel, .empty-state {{
      margin-top: 18px;
      padding: 20px;
      background: var(--surface);
      border: 1px solid var(--line);
      border-radius: 8px;
    }}
    .section-heading {{
      display: flex;
      align-items: end;
      justify-content: space-between;
      gap: 16px;
      margin-bottom: 14px;
    }}
    .section-heading p, .empty-state p {{ color: var(--muted); }}
    .table-wrap {{ overflow-x: auto; }}
    table {{
      width: 100%;
      border-collapse: collapse;
      min-width: 920px;
    }}
    th, td {{
      padding: 11px 10px;
      border-bottom: 1px solid var(--line);
      text-align: left;
      vertical-align: top;
    }}
    th {{
      color: var(--muted);
      font-size: 12px;
      text-transform: uppercase;
      letter-spacing: .04em;
    }}
    .badge {{
      display: inline-flex;
      align-items: center;
      min-height: 24px;
      padding: 2px 8px;
      border-radius: 999px;
      border: 1px solid currentColor;
      font-size: 12px;
      font-weight: 600;
    }}
    .badge.warning {{ color: var(--warning); background: #fef2f2; }}
    .badge.ok {{ color: var(--ok); background: #f0fdf4; }}
    .job-grid {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
      gap: 14px;
      margin-top: 18px;
    }}
    .job-card {{
      padding: 18px;
      background: var(--surface);
      border: 1px solid var(--line);
      border-radius: 8px;
    }}
    .job-card__header {{
      display: flex;
      justify-content: space-between;
      gap: 14px;
      margin-bottom: 14px;
    }}
    .eyebrow {{
      color: var(--accent);
      font-size: 12px;
      font-weight: 700;
      text-transform: uppercase;
      letter-spacing: .05em;
    }}
    dl {{
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 10px 14px;
      margin: 0;
    }}
    dt {{
      color: var(--muted);
      font-size: 12px;
      text-transform: uppercase;
      letter-spacing: .04em;
    }}
    dd {{ margin: 2px 0 0; overflow-wrap: anywhere; }}
    .link-line {{ margin-top: 14px; }}
    .warnings ul {{ margin: 0; padding-left: 20px; }}
    .warnings li + li {{ margin-top: 10px; }}
    .referral p {{ color: var(--muted); max-width: 860px; }}
    @media (max-width: 680px) {{
      .shell {{ width: min(100vw - 20px, 1180px); padding-top: 10px; }}
      header, .panel, .empty-state, .job-card {{ padding: 14px; }}
      .section-heading {{ display: block; }}
      .section-heading p {{ margin-top: 4px; }}
      dl {{ grid-template-columns: 1fr; }}
    }}
  </style>
</head>
<body>
  <main class="shell">
    <header>
      <div>
        <h1>{heading}</h1>
        <p class="subtitle">Company-site job intelligence from Retriever. This dashboard is a static local report; it does not submit applications or contact employers.</p>
      </div>
      <section class="metrics" aria-label="Dashboard summary">
        <div class="metric"><span>Generated</span><strong>{generated}</strong></div>
        <div class="metric"><span>Visible jobs</span><strong>{visible_count}</strong></div>
        <div class="metric"><span>Shown here</span><strong>{shown_count}</strong></div>
        <div class="metric"><span>Warnings</span><strong>{warning_count}</strong></div>
      </section>
      <p class="subtitle">{rank_note}</p>
    </header>
    {referral_section}
    {jobs_section}
    {warnings_section}
  </main>
</body>
</html>
""".format(
        heading=_html(heading),
        generated=_html(generated),
        visible_count=_html(visible_count),
        shown_count=_html(shown_count),
        warning_count=_html(warning_count),
        rank_note=_html(rank_note),
        referral_section=referral_section,
        jobs_section=jobs_section,
        warnings_section=warnings_section,
    )
