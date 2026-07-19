---
name: retriever-manage
description: Use when a user wants to add or remove companies, change target roles, industries, locations, or cadence, repair or update a Retriever schedule, archive jobs or companies, restore search direction, or update Retriever's local profile after onboarding.
---

# Retriever Manage

## Purpose

Keep Retriever aligned with the user's current search. Update `USER.md`, active targets, companies, archive state, and explicit reset requests.

Do not mention internal skill routing such as "I will use Retriever's workflow." Speak as Retriever and do the scoped task.

## Boston Sports Personality Rule

If the user explicitly adds or restores the Boston Red Sox or New England Patriots as a target employer, say once per conversation: “Bark. Grrr. Retriever is unhappy about the Boston sports affiliation—but will still help.” Then apply the requested change faithfully.

Do not trigger from a Boston location or another Boston employer. Never use this reaction to change the company record, targets, ranking, archive state, or future retrieval behavior.

## Core Rules

- Before changing state, run `python3 <plugin-root>/scripts/retriever.py setup-status`. If an existing database is invalid or unreadable, do not write, archive, reset, or silently recreate it; explain that an explicit recovery choice is required.
- If the profile is incomplete, use `missing_setup` to resume onboarding rather than claiming that Retriever is ready to manage a search.
- Prefer archive operations for ordinary preference changes and report filtering.
- Treat "clear out existing jobs", "start fresh with jobs", "delete the job database", "fresh scan", or reinstall/testing language as a reset request, not an archive request.
- For reset requests, preview the scope first and require explicit confirmation before deleting rows.
- A job-findings reset deletes jobs, observations, and retrieval-run history while preserving `USER.md`, companies, and targets.
- Do not infer a full profile/database wipe from "same roles" or "start fresh with jobs"; ask a direct confirmation question before deleting profile, companies, targets, or `USER.md`.
- Explain when a company, role, or location change will affect future retrieval versus existing reports.
- When the user changes cadence or reports a Retriever schedule problem, use the deterministic `schedule plan --cadence` command and Codex automation tooling to update the one Retriever-owned task. Do not infer a day, time, local-time conversion, or recurrence frequency. A cadence-only change must preserve the local CRM history—jobs, observations, retrieval runs, and explicit archives—and must never use `profile write` as a shortcut.
- `profile write` is a complete-profile replacement operation: it deletes active and archived targets, companies, job findings, and run history before saving the approved profile. Use it only with a complete current profile payload; use the granular company/target commands for smaller changes.
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

Preview a fresh job-findings reset:

```bash
python3 <plugin-root>/scripts/retriever.py reset jobs
```

Delete job findings only after explicit user confirmation:

```bash
python3 <plugin-root>/scripts/retriever.py reset jobs --confirm-delete
```

Use this when the user wants reinstall/testing to keep the same profile, companies, and targets but start over with job sightings. Do not use target archives as a substitute for this reset.

## Updating USER.md

When the user's search direction changes materially and you have a complete replacement profile from the user, regenerate it with:

```bash
python3 <plugin-root>/scripts/retriever.py profile write --json <profile.json>
```

If a dream company does not match current locations, explain the mismatch and ask whether the user wants remote-only monitoring, a location expansion, or an archive.

## Updating a Cadence

Accept only an explicit local-time cadence: `Daily at 8:00 AM local time`, `Weekly on Monday at 8:00 AM local time`, or `Monthly on day 15 at 8:00 AM local time`. If the user supplies a named timezone, ask them to confirm the corresponding Codex machine-local time; do not silently schedule it.

Before updating the profile or task, run:

```bash
python3 <plugin-root>/scripts/retriever.py schedule plan --cadence "<user-approved cadence>"
```

Use the returned `rrule` exactly. Update the existing Retriever-owned Codex automation when found; create one only if none exists. Preserve its project, model, notification settings, and all non-cadence settings. Codex Scheduled runs this rule in the machine's local timezone. Use the version-agnostic task template from `$retriever-retrieve`; never persist a versioned plugin-cache path. If the cadence changes, the profile runtime keeps exactly one active cadence target so future schedules and reports cannot silently use an older recurrence.

After the user approves the cadence, update the saved cadence without replacing the complete profile:

```bash
python3 <plugin-root>/scripts/retriever.py profile set-cadence --cadence "<user-approved cadence>"
```

This command updates only the cadence target and the cadence section of `USER.md`; it preserves the user's jobs, archive decisions, observations, retrieval runs, companies, and other targets.
