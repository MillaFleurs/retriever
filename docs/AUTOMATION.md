# Automation

Retriever recurring runs should be configured through Codex automations after the user chooses a cadence.

## Schedule Prompt

Use this prompt body for a daily job-search automation:

```text
Use $retriever-retrieve to check active companies in ~/.retriever for jobs matching the active USER.md profile. Then use $retriever-report to report jobs first seen since the previous scheduled run or since yesterday, whichever is available. Show counts, top ranked matches if there are many results, offer the full database/CSV, ask whether preferences need updates, and do not submit applications or contact employers.
```

## Guardrails

- Confirm the cadence and timezone before creating an automation.
- For "every morning at 9:00", use a daily wall-clock schedule in the user's local timezone.
- If the automation tool rejects a schedule representation, retry with that tool's supported daily wall-clock format while preserving the requested cadence.
- Tell the user that local scheduled retrieval depends on Codex, Chrome, and the machine/session being available.
