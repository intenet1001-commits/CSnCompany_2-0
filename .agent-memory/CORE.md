# Project Core Memory

**Project**: CSnCompany_2-0
**Created**: 2026-07-26
**Last Updated**: 2026-08-15

> Curated long-term memory for this project. Keep durable decisions and repeated
> lessons here; do not store secrets, credentials, environment values, raw chat logs,
> temporary status, or speculative claims.

## Project Identity

- CSnCompany_2-0 is a Claude Code plugin marketplace bundling 13 plugins that act as specialist AI "teammates" (CEO, PM, Architect, Designer, two Design Reference plugins, QA Engineer, Code Reviewer, DevOps, Team Lead, Knowledge Keeper, Memory Trainer, Language Coach), invoked via slash commands (e.g. `/cs-ceo`, `/CS-test`).
- Also registered for Codex (via `.codex/`), not just Claude Code.
- Design reference plugins: `cs-design-sample1` (CS Archive tokens — warm paper `#F4EFE3` + deep teal accent by default, near-black + cyan dark toggle, single `--cs-accent` token re-skins everything) and `cs-design-sample2` (dark editorial/terminal style — near-black navy `#05070d` background, cyan accent, grid-overlay + glow decor); both use IBM Plex Mono + Noto Serif KR.
- Installation is via the Claude Code plugin marketplace (`/plugin marketplace add intenet1001-commits/CSnCompany_2-0`), with plugins installed à la carte (`/plugin install <name>@CSnCompany_2-0`); `uv` is an optional dependency that reduces code-analysis token usage.
- Scheduled/automated work for the author's projects lives in **claude.ai cloud routines**, not in local `cron`/`launchd` — this repo has no local scheduled jobs. Routines are inspected via the remote-trigger API and viewed at `https://claude.ai/code/routines/<trigger_id>`.

## Key Decisions

- 2026-07-24: Renamed the `cs-sync` plugin to `csn-sync` to avoid a naming collision with a global skill (commit 8784d7e).
- Every multi-agent plugin uses the lead-agent pattern: the main conversation spawns one lead agent, which orchestrates N specialist workers internally so worker output never pollutes the main context — only the synthesized report returns.
- Code-analysis plugins (e.g. CS-codebase-review) run an optional Python pre-pass (`plugins/shared/`, using `uv` or `python3`) to extract structural data (file structure, import graph) into compact JSON before agents run, cutting input tokens by 70%+. Falls back gracefully to direct file reads if uv/python3 unavailable.
- Repo hygiene: superseded/duplicate plugin versions and duplicate files are moved (not deleted) into dated archive folders — `archive/legacy-plugins/<date>/` and `archive/duplicate-files/<date>/` — preserving history while keeping `plugins/` limited to active versions (e.g. 2026-07-26 archived cs-ceo-v14, cs-design-v19, cs-end-v1, cs-end-v2, and duplicate `VERSION 2` files).
- 2026-07-26: Replaced the old `cs-core-memory` plugin with `cs-memory`, which condenses its commands into three slim ones (`learn` / `upgrade` / `status`); upgrading users must uninstall `cs-core-memory` before installing `cs-memory`.
- 2026-07-30: Added `cs-design-sample2` (dark editorial/terminal design guide) and replaced `cs-design-sample1`'s prior design language with CS Archive tokens (paper/dark toggle), bringing the marketplace to 13 plugins total.
- 2026-08-02: Plugin renames must propagate to every internal identifier, not just the directory — `cs-smart-run` v1.1.1 fixed leftover `smart-run` values in both the Claude (`.claude-plugin/plugin.json`) and Codex (`.codex-plugin/plugin.json`) manifests, plus the `/smart-run` trigger phrases and invocation examples in `skills/smart-run/SKILL.md`.
- Skill directory names may keep the pre-rename name after a plugin rename (`cs-smart-run/skills/smart-run/`); the user-facing trigger phrases and manifest `name` are what must match the new plugin name.

## Strategic Patterns

### AgentsToZ is the sole project-memory writer
<!-- memory-entry-id:e2f17372967a1b9cf292bdf0 -->

- Since `memory-agent-version:11`, `.agent-memory` is authoritative. CSnCompany may read it but must not modify it outside the project-local remember-session adapter, and its learning state stores only IDs, hashes, timestamps, root provenance, and dispositions—not titles, bodies, section names, or excerpts.
- Remember-session uses Pull (when automatic backup is enabled) → local edit → `mark-remembered` journal → Push. A remote failure never rolls back the local save. `/cs-end` delegates to the same adapter. Split memory uses a generated index plus bounded notes; edit notes, never the index.
- Keep the generated project-memory block synchronized in `CLAUDE.md` and `AGENTS.md`. Claude/Codex activity hooks remain token-free and record only activity time and agent, never prompt text.

### cs-memory 2.1 learns changes through bounded deterministic state
<!-- memory-entry-id:6608fc2728a3dd412f93217b -->

- Stable identity is `memoryId + entryId`; a version adds the content hash and accepted/contested boundary. Title/section/note moves and mtime-only changes do not relearn. Initial automatic collection is an `observed` baseline; a later filled stable placeholder is a `filled` change.
- Collection is model-free and read-only, with explicit bounded recall/learning. Duplicate IDs, unsafe paths, unstable or oversized sources, and credential indicators are blocked without retaining source text. State/queue writes are locked, atomic, size-validated, and parent-identity guarded; known duplicate roots remain blocked until all are revalidated.
- The optional six-hour scheduler executes a stable user-state copy and calls no model. `cs-ceo` recalls bounded project memory before decomposition and learns only actionable pending items; Claude and Codex cache resolvers are both executable paths.
- CLAUDE.md enforces skill-first routing: when a user request matches an available skill, invoke it via the Skill tool as the first action rather than answering ad-hoc, unless the request is a single-fact check answerable in 1-3 direct tool calls. Routing rules are maintained as an explicit trigger→skill table (including Korean trigger phrases such as "플랜실행", "디자인 리뷰", "장기기억 학습").
- Recurring workflow: `cs-experiencing` learnings are committed incrementally with version bumps (e.g. v8.2.7 → v9.0.3 across 2026-07-19 to 2026-07-22), each commit capturing a discrete number of learned items/addenda.
- `csn-sync`'s `sync.sh` treats `git fetch` failure as non-fatal: on failure it warns and reports repo state against the last cached upstream ref instead of aborting, so offline status checks still work.
- `csn-sync`'s `sync.sh` includes an `archive_stale_codex_cache` step (run after pull/push/auto sync) that moves non-current plugin versions out of Codex's live cache (`~/.codex/plugins/cache/CSnCompany_2-0`) into a dated archive (`~/.codex/plugins/archive/CSnCompany_2-0/<date>/`), keeping the live cache limited to active versions while old ones stay recoverable.
- `csn-sync`'s skill scripts are located relative to the plugin root (`../../scripts/` from `SKILL.md`, or `${CLAUDE_PLUGIN_ROOT}/scripts/` when the runtime exposes that variable) so they self-locate the real marketplace repo even when invoked from a Codex cache copy.
- Plugin version bumps are applied consistently across four places: `VERSION`, `CHANGELOG.md` (dated entry), `.claude-plugin/plugin.json`, and `.codex-plugin/plugin.json` — and, where the skill declares its own `version:` frontmatter, that file too (`cs-smart-run` 1.1.1 aligned `SKILL.md` frontmatter with `VERSION`, which had drifted at 1.0.0).
- Every plugin ships parallel Claude and Codex manifests (`.claude-plugin/plugin.json` and `.codex-plugin/plugin.json`) that must stay in sync; edits to one require the same edit to the other.
- CHANGELOG entries are written per plugin with a dated `## <version> — <YYYY-MM-DD>` heading listing the concrete files changed.
- Diagnosing "did my scheduled job run?": check local `crontab -l` / LaunchAgents first to rule out a local job, then query the cloud routines. The routine API exposes schedule, `last_fired_at`, and `next_run_at` — enough to confirm a routine *fired*, but not what it produced; the run's output must be read from the routine's claude.ai page or wherever the routine posts (e.g. a Slack webhook), which may be unreachable from the CLI session.

## Recurring Issues

- Renaming a plugin leaves stale identifiers behind. Root cause: the name appears in the directory, both manifests, the skill's `description` trigger phrases, and its usage examples — renaming the directory alone leaves the rest inconsistent. Seen with `cs-sync` → `csn-sync` (2026-07-24) and `smart-run` → `cs-smart-run` (fixed 2026-08-02). Reliable workaround: grep the whole plugin directory for the old name after any rename.
- Skill frontmatter `version:` can drift from the plugin's `VERSION` file, since they are edited independently (`cs-smart-run` SKILL.md sat at 1.0.0 while VERSION was 1.1.0). Check both when bumping.
- Duplicate command wrappers have been shipped by mistake and needed removal after the fact (2026-07-26, commit 5076a27, `cs-memory`). Root cause: adding commands in more than one place during a plugin restructure.
- `VERSION` files have been written without a trailing newline (`cs-smart-run` 1.1.0); write them with one.
- Cloud routines silently fail to run when their schedule is malformed or mis-specified — a routine whose prompt says "매주 일요일마다 점검" can carry an **empty** `cron_expression` (and a `0001-01-01` `next_run_at`), so it never fires, and another can sit on `0 3 1 1 *` (once a year on Jan 1) when a frequent schedule was intended. Root cause: the natural-language intent in the prompt is not validated against the stored cron expression. Verify `cron_expression` and `next_run_at` after creating or editing a routine — observed 2026-08-06 on `freeparking` and `앱 자동 수정 에이전트`.

## Active Constraints

- Do not store secrets, credentials, environment values, raw chat logs, temporary status, or speculative claims in core memory.
- `.agent-memory/config.json` and its project-relative `sourcePath` should be read before substantial work when historical decisions may matter.
- Plugin names must not collide with globally available skill names (the reason for the `cs-sync` → `csn-sync` rename); the `cs-`/`CS-` prefix convention serves this purpose.
- The `cs-experiencing` learnings push is author-only; other users consume the versioned learnings rather than pushing to them.
- Cloud-routine schedules and their effects are outward-facing; changing or manually triggering a routine is confirmed with the user rather than done unilaterally during a status check.

## Contested Entries

<!-- Keep contradictory evidence visible until the user explicitly resolves it. -->
