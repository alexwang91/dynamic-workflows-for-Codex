# Codex Dynamic Workflows

External orchestration runtime that recreates Claude-style dynamic workflows for Codex.

The runtime generates typed workflow plans, executes specialist worker tasks through a swappable adapter, persists intermediate state under `.cdw/runs/`, verifies outputs before synthesis, and loops against explicit stop conditions.

MVP commands:

```bash
cdw plan "Review this branch"
cdw review "Review this branch with specialist agents"
cdw debug "This test fails 1 in 50 runs"
```
