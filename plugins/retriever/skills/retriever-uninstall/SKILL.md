---
name: retriever-uninstall
description: Use when a user wants to uninstall or remove Retriever, stop Retriever schedules, clean up local state, or perform a clean test reset.
---

# Retriever Uninstall

## Purpose

Safely stop Retriever-owned scheduled work before the user removes the plugin. Do not remove unrelated Codex automations or any local data without an explicit scope and confirmation.

## Scheduled Automation Cleanup

Codex does not provide Retriever with a documented uninstall lifecycle event. Therefore, when a user asks to uninstall Retriever, first use the Codex automation tooling to list automations and identify only entries whose identifier or name clearly belongs to Retriever, such as `retriever-daily-new-jobs` or `Retriever daily new jobs`.

Show the exact matching schedule names and cadence. Ask for confirmation before deleting them. After confirmation, delete every identified Retriever-owned automation through the Codex automation tool, then verify no Retriever-owned automation remains. Do not delete a schedule merely because it has a similar job-search topic.

## Local Data Cleanup

After schedules are removed, ask separately what should happen to `~/.retriever`:

1. Keep it for a later reinstall.
2. Reset job findings only, preserving `USER.md`, companies, and targets.
3. Delete all Retriever local data after the user confirms the exact directory and data types.

Default to keeping local data. Do not use archive flags as a substitute for a requested clean reset. Do not delete `~/.retriever` until the user explicitly chooses the full-data deletion option.

## Clean Test Reset

When the user says they are reinstalling, testing first-run onboarding, or asks to reset Retriever for a clean test, offer the full clean-reset path instead of asking them to manually delete `~/.retriever`:

1. Use Codex automation tooling to find only Retriever-owned schedules. Run the local preview command below; it never changes files.

   ```bash
   python3 <plugin-root>/scripts/retriever.py reset state
   ```

2. Show the exact Retriever schedule names, the exact known local artifacts that would be removed, and any unrecognized files that will be preserved. Explain that this creates a fresh onboarding state and does not remove unrelated Codex automations or unmanaged files.
3. Ask for one explicit confirmation covering both the displayed Retriever schedules and the displayed local artifacts. Do not infer that confirmation from “start over” alone.
4. After confirmation, delete the matching Retriever-owned schedules through Codex automation tooling. Then run:

   ```bash
   python3 <plugin-root>/scripts/retriever.py reset state --confirm-delete
   ```

5. Verify no Retriever-owned schedules remain, then run `setup-status`. It should report `fresh_onboarding: true`; start a new interactive onboarding conversation. Do not run a retrieval as part of reset.

The `reset state` runtime command is deliberately local-only. If a user runs it outside Retriever's interactive cleanup flow, it leaves schedules unchanged and says so; never claim a schedule was removed unless automation tooling confirmed it.

## Final Step

Tell the user they can now uninstall Retriever in the Codex Plugins UI. Explain that a later install followed by **Start my job search** will inspect any retained state and either continue setup or begin a fresh onboarding conversation.
