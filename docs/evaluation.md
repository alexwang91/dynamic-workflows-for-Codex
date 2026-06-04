# Evaluation Checklist

## Architecture

- Runtime state is stored in `.cdw/runs/<run-id>/state.json`.
- Worker results are structured and persisted before verification.
- Verification results are persisted before synthesis.
- Synthesis reads structured state, not chat transcript history.

## MVP Behavior

- `cdw plan` creates a durable run directory.
- `cdw review` fans out to security, tests, compatibility, and maintainability workers.
- `cdw debug` fans out to logs, tests, code-path, and timing investigators.
- Fake adapter mode works without OpenAI credentials.
- Live adapter mode fails clearly when optional dependencies are missing.
