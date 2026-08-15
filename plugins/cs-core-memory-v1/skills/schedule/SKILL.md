---
name: schedule
description: Install or manage zero-token periodic AgentsToZ memory-change collection. Use when the user invokes `/cs-memory:schedule`, asks for scheduled/automatic long-term-memory learning, or wants folder/PC-wide memory polling.
---

# Schedule memory-change collection

Install a native scheduler that runs the deterministic collector. A scheduled tick reads file stamps,
fully parses only changed memories, and stores entry/version pointers; it never edits project memory and
never calls an LLM.

## Public interface

```text
/cs-memory:schedule status
/cs-memory:schedule install registry       # AgentsToZ project registry, every 6h
/cs-memory:schedule install folder /abs    # one bounded folder tree
/cs-memory:schedule install pc             # bounded user-home scan + registry
/cs-memory:schedule remove
```

With no arguments, run `status`. Do not install or remove a scheduler implicitly.

## Run

1. Locate `../learn/scripts/memory_learning_schedule.py` from this skill directory.
2. Use `uv run --quiet --no-project python <script>`; do not invoke project Python environments.
3. For `install`, run once with `--dry-run` and verify:
   - the learning script and state paths are absolute;
   - the interval is between 1 and 168 hours;
   - `folder` has one existing absolute root;
   - the generated command contains `collect --no-cwd --quiet`;
   - no shell string, credential, model command, or project-memory write is present.
4. If the dry run is valid, run the same command without `--dry-run`.
5. Run `status` and report the native definition path, loaded/enabled state, `scriptCurrent`,
   `definitionCurrent`, and `needsReinstall`.
   - Install copies the current deterministic collector to
     `~/.csncompany/bin/memory_learning.py`; native definitions must point to this stable path, not a
     versioned marketplace/cache directory.
   - If `needsReinstall=true`, explain that the plugin source or native definition drifted and offer to
     repeat the same `install <scope>` command. Do not reinstall implicitly during a status check.
6. `remove` deletes only this skill's exact launchd/systemd/Task Scheduler definition and its stable
   collector copy.

Optional interval syntax is `every <N>h`; pass it as `--interval-hours N`. Default to 6 hours. Reject
sub-hour polling: memory saves are session-scale events and faster polling only creates filesystem churn.

## Scope semantics

- `registry`: preferred. Reads projects already known to AgentsToZ.
- `folder`: bounded recursive discovery with dependency/cache/credential directories pruned.
- `pc`: user-home discovery plus registry, never `/`, external volumes, or unrestricted symlink traversal.

The scheduler stores state at `~/.csncompany/state/memory-learning.json`, shared by Claude and Codex.
Unchanged stamps skip note reads; an unchanged project still receives a full audit at least every seven
days so metadata stamps are not permanent proof of equality.

## Learning handoff

Periodic collection is deliberately model-free. `/cs-memory:learn` consumes at most five pending current
entry versions in one batch and queues at most one compact reusable lesson per entry version.
`/cs-memory:upgrade` merges those lessons into the smallest affected owner skill. This separation keeps
idle ticks at zero tokens and prevents an unattended memory document from gaining broad write authority.

Never install an unattended Claude/Codex command with bypassed permissions. Never fall back to writing
`~/.claude/core-memory` or to editing `.agent-memory` from this plugin.
