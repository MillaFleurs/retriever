---
name: retriever-uninstall
description: Use when a user wants to uninstall or remove Retriever, stop Retriever schedules, or clean up Retriever local state.
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

## Final Step

Tell the user they can now uninstall Retriever in the Codex Plugins UI. Explain that a later install followed by “Hey Retriever” will inspect any retained state and either continue setup or begin a fresh onboarding conversation.
