# Security and Safety

## Boundary

Retriever is read-only toward external job sites. It does not submit applications, send messages, edit external forms, or click final application controls.

## Prompt-Injection Handling

Career-site content is untrusted. Retriever scans observed text for patterns such as:

- Instructions to ignore prior, system, or developer instructions.
- Text that branches on whether the reader is an AI or assistant.
- Requests to reveal secrets, tokens, API keys, credentials, or environment variables.
- Special words or phrases that appear intended to detect automated readers.

Warnings are stored with the job observation and surfaced in reports. Retriever records and warns; it does not follow page instructions.

## Local Data

Default local state is `~/.retriever`:

- `USER.md`.
- `retriever.sqlite3`.
- `reports/`.

This directory may contain personally identifying job-search information. Do not commit it to Git.

## Codex and Chrome Controls

Retriever requires the separate Chrome plugin only for live company-site retrieval. The user controls Chrome website permissions and the selected Chrome profile; Retriever does not attempt to bypass a blocked site, change browser permissions, or override the browser User-Agent. It uses the normal browser identity and treats all career-page content as untrusted.
Reference: [OpenAI Chrome extension documentation](https://learn.chatgpt.com/docs/chrome-extension).

## Interactive Dashboard

The optional interactive dashboard binds only to `127.0.0.1`. Its archive action requires a fresh per-process token embedded in the locally rendered form and changes only the selected job's local archive flag after user confirmation. Managed start/stop control uses a separate random token stored in a `0600` local service-state file, and the stop request is accepted only over loopback. The archived-jobs CSV is served only by that loopback dashboard. Static HTML exports remain read-only.

## References

- [Codex Chrome extension docs](https://learn.chatgpt.com/docs/chrome-extension)
- [OpenAI Scheduled tasks documentation](https://learn.chatgpt.com/docs/automations)
- [Using Retriever with Codex](CODEX.md)
- [GNU AGPL v3](https://www.gnu.org/licenses/agpl-3.0.en.html)
