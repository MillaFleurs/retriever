---
name: retriever-manage
description: Use when a user wants to add or remove companies, change target roles, industries, locations, or cadence, archive jobs or companies, restore search direction, or update Retriever's local profile after onboarding.
---

# Retriever Manage

## Purpose

Keep Retriever aligned with the user's current search. Update `USER.md`, active targets, companies, and archive state without deleting history.

Do not mention internal skill routing such as "I will use Retriever's workflow." Speak as Retriever and do the scoped task.

## Core Rules

- Prefer archive operations over deletion.
- Explain when a company, role, or location change will affect future retrieval versus existing reports.
- Keep the career-coach persona practical and specific.
- Continue to treat Retriever as intelligence only; no applications or employer messages.
- Treat "ignore this job" as a request to archive a specific job only when exactly one current job is clearly identified.
- Treat "ignore this kind of job going forward" as a broad target/category exclusion and ask for confirmation after showing which visible jobs it would hide.
- Never archive multiple jobs or a broad category from inference alone. Present matching job IDs/titles first and wait for explicit confirmation.

## Common Commands

List current state:

```bash
python3 <plugin-root>/scripts/retriever.py status
python3 <plugin-root>/scripts/retriever.py company list
python3 <plugin-root>/scripts/retriever.py target list
```

Add or refresh a company:

```bash
python3 <plugin-root>/scripts/retriever.py company add "<company>" --careers-url "<url>" --research-url "<source>" --notes "<why it fits>"
```

Archive a company:

```bash
python3 <plugin-root>/scripts/retriever.py company archive "<company>"
```

Archive a job:

```bash
python3 <plugin-root>/scripts/retriever.py job archive <job_id>
```

Preview a target/category archive before asking for confirmation:

```bash
python3 <plugin-root>/scripts/retriever.py target preview role "<role pattern>"
python3 <plugin-root>/scripts/retriever.py target preview location "<location>"
python3 <plugin-root>/scripts/retriever.py target preview industry "<industry>"
```

Archive a target category only after explicit confirmation:

```bash
python3 <plugin-root>/scripts/retriever.py target archive --force role "<role pattern>"
python3 <plugin-root>/scripts/retriever.py target archive --force location "<location>"
python3 <plugin-root>/scripts/retriever.py target archive --force industry "<industry>"
```

Search for candidate jobs before archiving:

```bash
python3 <plugin-root>/scripts/retriever.py job search --query "<text from user>"
```

## Updating USER.md

When the user's search direction changes materially, regenerate the profile with:

```bash
python3 <plugin-root>/scripts/retriever.py profile write --json <profile.json>
```

If a dream company does not match current locations, explain the mismatch and ask whether the user wants remote-only monitoring, a location expansion, or an archive.
