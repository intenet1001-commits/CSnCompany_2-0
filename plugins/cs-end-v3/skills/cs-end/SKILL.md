---
name: cs-end
description: Close a CSnCompany session, persist validated learnings, and delegate configured project-memory storage to the AgentsToZ owner. Use when the user invokes `/cs-end`, asks to close/wrap up the session, or requests the same closing workflow from Codex.
---

# CS session closing adapter

`../../commands/cs-end.md` is the canonical workflow shared by Claude Code and Codex. Read it fully at
invocation time and execute its current phases in order; do not maintain a second copy of the protocol in
this skill.

## Surface translation

- On Claude Code, a canonical `Task()` means the matching Claude subagent call.
- On Codex, use the current native subagent/fan-out primitive with the same isolated role and input. If
  that surface cannot spawn subagents, run the analysis roles sequentially and state the degraded mode;
  never fabricate parallel-agent results.
- Shell/Python checks in the canonical workflow use the same repository paths and output contracts on
  both surfaces. Run plugin Python only via `uv run --quiet --no-project python`.
- Preserve the Phase 1.5 AgentsToZ owner handoff exactly. Project memory is written only by the
  project-local `remember-session` adapter; cs-end must not create a global memory fallback.

## Completion rule

Do not report success until the canonical workflow's durable learning writes, project-memory owner
handoff (when configured), validation gates, and compact handoff have each either succeeded or been
reported with their explicit non-blocking failure status.
