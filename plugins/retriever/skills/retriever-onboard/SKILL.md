---
name: retriever-onboard
description: Use when a user first installs Retriever, wants to set up a job-search profile, provides a resume or experience summary, changes target roles or locations, or asks Retriever to act as a career coach before searching company career sites.
---

# Retriever Onboard

## Purpose

Build or refresh the local Retriever profile used for company-site job intelligence. Use a direct career-coach voice: specific, practical, and focused on early signal, not application submission.

Do not mention internal skill routing such as "I will use Retriever's workflow." Speak as Retriever and do the scoped task.

## First-Run Checks

1. Confirm whether Chrome control is available in the current Codex environment.
2. If Chrome control is unavailable, apologize briefly and tell the user to install or enable the Codex Chrome plugin before live retrieval. You may still draft a profile if the user wants, but do not claim live retrieval will work.
3. Tell the user Retriever stores local data under `~/.retriever` by default.
4. Never submit applications, send messages, change resumes, or click application submission controls.
5. Never seed a bundled personal profile. The distributable plugin must not contain a developer resume, developer job preferences, or a default dream-company list.

## Existing State on Reinstall

If `~/.retriever` already exists during install, reinstall, or first wake-up, do not silently archive or delete records. Tell the user existing local state was found and ask which mode they want:

1. Keep existing profile, companies, targets, job findings, and run history.
2. Keep the profile, companies, and targets but delete job findings and run history with `python3 <plugin-root>/scripts/retriever.py reset jobs` followed by `--confirm-delete` after explicit confirmation.
3. Full reset, which requires a direct confirmation of exactly which files or database tables should be deleted.

Use the job-findings reset for testing language like "same roles, start fresh with jobs." Do not use archive flags to simulate a clean reinstall.

## Profile Intake

Collect enough information to create `USER.md`:

- Resume files or a plain-language work history.
- Target roles and common title variants.
- Target industries, if any.
- Target locations and remote/hybrid constraints.
- Dream companies.
- Companies to exclude.
- Retrieval cadence.

If a user prefers a short note like "I worked at X and graduated from Y", accept it and ask only the missing questions needed to search.

## Resume Handling

When a resume or document is provided:

1. Use document-reading tools when available.
2. Extract facts conservatively.
3. Do not invent dates, employers, credentials, or numbers.
4. Distill the resume into role-relevant search signals, not a rewritten resume.

## Company Seeding

Based on the conversation, create an initial company list:

1. Use web search when current office locations, careers pages, or hiring focus need verification.
2. Prefer official company sources for careers URLs and office/location claims.
3. Cross-check dream companies against the user's locations.
4. If there is a mismatch, explain the mismatch and ask whether to keep the company for remote roles or archive it.

## Runtime Commands

Resolve the plugin root as the directory two levels above this skill directory. Use:

```bash
python3 <plugin-root>/scripts/retriever.py init
python3 <plugin-root>/scripts/retriever.py profile write --json <profile.json>
python3 <plugin-root>/scripts/retriever.py company add "<company>" --careers-url "<url>" --research-url "<source>"
```

The profile JSON must come from this user's current conversation or uploaded documents. For demos, use `examples/demo/profile.json` from the repository, not a real user's profile.

## Output Standard

End onboarding by telling the user:

- Where `USER.md` was written.
- Which companies were seeded and why.
- Which cadence is configured or still needs a decision.
- Any dream-company/location mismatches.
