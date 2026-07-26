---
name: status
description: Show project-memory learning cursors, pending experience candidates, and recent CS agent upgrade versions without modifying anything. Use when the user invokes `/cs-memory:status`, says "장기기억 상태", "학습 상태", "미처리 학습 후보", or asks whether memory learning or agent upgrades are pending.
---

# Show memory status

Perform read-only checks:

1. Run `scripts/long_term_memory_training.py status`.
2. Count candidate statuses in `~/.claude/.experiencing-btw.json`; do not print complete lesson
   bodies unless requested.
3. Read versions for the latest `CS-test-v*`, `CS-plan-v*`, `CS-codebase-review-v*`,
   `cs-design-v*`, `cs-clarify-v*`, `cs-ceo-v*`, `cs-smart-run`, and `cs-experiencing-v*`.
4. Show:
   - configured and successfully trained project counts;
   - last successful cursor time per project;
   - pending/promoted/rejected candidate counts;
   - domains changed by the most recent upgrade when that provenance exists;
   - actionable next command.

Recommend `/cs-memory:learn` only when project changes are unreviewed. Recommend
`/cs-memory:upgrade` only when pending reusable candidates exist.

