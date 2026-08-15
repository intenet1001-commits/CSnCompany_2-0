---
name: status
description: Show memory-change intake, periodic collector, pending lessons, and recent CS agent upgrade versions without modifying anything. Use when the user invokes `/cs-memory:status`, says "장기기억 상태", "학습 상태", "미처리 학습 후보", or asks whether scheduled memory learning or agent upgrades are pending.
---

# Show memory status

Perform read-only checks:

1. Run `../learn/scripts/memory_learning.py status` through `uv run --quiet --no-project python`.
2. Run `../learn/scripts/memory_learning_schedule.py status` read-only.
3. Count candidate statuses in `~/.claude/.experiencing-btw.json`; do not print complete lesson
   bodies unless requested.
4. Read versions for the latest `CS-test-v*`, `CS-plan-v*`, `CS-codebase-review-v*`,
   `cs-design-v*`, `cs-clarify-v*`, `cs-ceo-v*`, `cs-smart-run`, and `cs-experiencing-v*`.
5. Show:
   - configured memory count and last full scan per project;
   - observed-baseline/pending/queued/rejected/contested entry-version counts;
   - scheduler installed/enabled state and scope when available;
   - pending/promoted/rejected candidate counts;
   - domains changed by the most recent upgrade when that provenance exists;
   - actionable next command.

Recommend `/cs-memory:learn` only when pending entry versions exist. Recommend
`/cs-memory:upgrade` only when pending reusable candidates exist.

