# Demo Script

Target length: under 3 minutes for Devpost.

Reference: [OpenAI Devpost rules](https://openai.devpost.com/rules).

## Flow

1. Install Retriever from the repo-local marketplace, select **Try it now**, then select **Start my job search**.
2. Show Retriever beginning the career-coach intake and creating a user-created `USER.md` only after the user supplies their information.
3. Show the SQLite-backed company and target state.
4. Run a retrieval pass against company career pages with Chrome.
5. Show new matching jobs or a deterministic fixture if live results are not stable.
6. Show prompt-injection warning behavior with the scanner.
7. Ask to see found jobs and show that Retriever automatically starts or reuses the loopback-only interactive dashboard.
8. Point out its total-job, shown-job, and archived-job counts; download the archived-job CSV.
9. Archive one job with its confirmation-gated button, show that later reports hide it, then stop the local dashboard.
10. Show the fresh-start path: preview `reset jobs`, confirm it, then show that profile, companies, and targets remain while job findings are cleared.

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
python3 plugins/retriever/scripts/retriever.py --state-dir /private/tmp/retriever-demo report --format html --ranked --output /private/tmp/retriever-demo/reports/jobs.html
```

Reset only the demo job findings:

```bash
python3 plugins/retriever/scripts/retriever.py --state-dir /private/tmp/retriever-demo reset jobs
python3 plugins/retriever/scripts/retriever.py --state-dir /private/tmp/retriever-demo reset jobs --confirm-delete
python3 plugins/retriever/scripts/retriever.py --state-dir /private/tmp/retriever-demo status
```
