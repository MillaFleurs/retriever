# Devpost Checklist

Reference: [OpenAI Devpost rules](https://openai.devpost.com/rules).

## Positioning

- Track: Apps for Your Life.
- User problem: company career pages often expose roles before aggregator sites surface them.
- User: job seekers who need early intelligence at target companies.
- Core demo: Codex plugin behaves like a career coach, builds `USER.md`, uses Chrome to inspect company sites, records jobs locally, and exports reports.

## Required Evidence

- README with install and test instructions.
- Public CI that runs the local Retriever test suite on pushes and pull requests.
- Demo video under the Devpost limit.
- Repository URL when ready for public or shared judging.
- Explanation of how Codex was used.
- Clear note that Retriever does not submit applications.

## v1.1 Final Verification

- Reinstall from the marketplace, select **Try it now**, then select **Start my job search**.
- With no profile, verify Retriever begins career-coach intake without creating a retrieval run.
- Complete onboarding and verify Retriever calculates a first-search estimate from the active-company count at roughly three minutes per company, then waits for explicit permission before it opens Chrome.
- Approve the first search, then run one end-to-end Chrome retrieval and export a report.
- Ask for found jobs, verify Retriever starts or reuses the loopback-only interactive dashboard, and show its total/shown/archived counts plus the archived-job CSV download.
- Archive one visible job, show that it disappears from the next report, then stop the managed dashboard.
- Verify an unconfigured scheduled run skips cleanly without opening Chrome or recording an error run.
- Verify Retriever uninstall removes only Retriever-owned schedules after confirmation.
- XLSX or DOCX report exports remain a post-hackathon enhancement; CSV, Markdown, and HTML are the v1.1 report formats.
