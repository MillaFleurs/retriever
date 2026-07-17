# Demo Script

Target length: under 3 minutes for Devpost.

Reference: [OpenAI Devpost rules](https://openai.devpost.com/rules).

## Flow

1. Install Retriever from the repo-local marketplace.
2. Run `$retriever-onboard` and show a user-created `USER.md`.
3. Show the SQLite-backed company and target state.
4. Run a retrieval pass against company career pages with Chrome.
5. Show new matching jobs or a deterministic fixture if live results are not stable.
6. Show prompt-injection warning behavior with the scanner.
7. Export Markdown and CSV reports.
8. Archive a job or category and show that reports hide it.

## Deterministic Fallback

If live network or hiring results are not stable during judging, use the CLI to insert a fixture job:

```bash
python3 plugins/retriever/scripts/retriever.py --state-dir /private/tmp/retriever-demo profile write --json examples/demo/profile.json
python3 plugins/retriever/scripts/retriever.py --state-dir /private/tmp/retriever-demo job upsert \
  --company "Example AI Labs" \
  --title "Technical Program Manager, AI Infrastructure" \
  --location "San Francisco, CA" \
  --source-url "https://example.com/careers" \
  --url "https://example.com/careers/technical-program-manager" \
  --observed-text "Example fixture for demo only."
python3 plugins/retriever/scripts/retriever.py --state-dir /private/tmp/retriever-demo report --format markdown --ranked
```
