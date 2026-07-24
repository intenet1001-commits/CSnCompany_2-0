---
name: csn-sync
description: Keep the CSnCompany_2-0 marketplace in sync across Claude Code and Codex, using GitHub (intenet1001-commits/CSnCompany_2-0) as the single source of truth. There is one git repo — the Claude Code clone at ~/.claude/plugins/marketplaces/CSnCompany_2-0 — and Codex references that same folder as a source_type="local" marketplace (per ~/.codex/config.toml), rebuilding its own version-keyed cache from it. So "sync Claude ↔ Codex" is just git pull/push of that one repo, then each tool refreshes its view. Unlike a single-plugin marketplace, CSnCompany ships ~14 plugins, so version bumps and cache mirroring loop over all of them, and each plugin needs a .codex-plugin/plugin.json (regenerated from its .claude-plugin twin). Note: named csn-sync (not cs-sync) to avoid colliding with the pre-existing global cs-sync skill for the separate cs_plugins marketplace. Trigger: "/csn-sync", "동기화", "싱크 맞춰줘", "sync the marketplace", "pull the latest CSnCompany", "push my CS changes", "codex랑 클로드 맞춰줘", or any request to reconcile this marketplace between the two tools or with GitHub.
risk: safe
---

# csn-sync

One repo, two tools, GitHub as the hub. This skill wraps a deterministic git helper so an
update made in **either** Claude Code or Codex propagates to the other through GitHub. It is the
CSnCompany_2-0 analogue of nhdesign4-sync, adapted for a **multi-plugin** marketplace.

## The architecture (why this is simple)

- **One git repo only**: `~/.claude/plugins/marketplaces/CSnCompany_2-0` (remote
  `github.com/intenet1001-commits/CSnCompany_2-0`, branch `main`).
- **Codex points at that same folder.** `~/.codex/config.toml` registers it as
  `source_type = "local"`, `source = "/Users/gwanli/.claude/plugins/marketplaces/CSnCompany_2-0"`,
  and keeps a *derived*, version-keyed cache at
  `~/.codex/plugins/cache/CSnCompany_2-0/<plugin-name>/<version>/`.

So there is no disk-level Claude↔Codex divergence to reconcile — only **local repo vs GitHub**.
Sync = `git pull` / `git push` of the one repo, then each tool refreshes its own view.

## Two CSnCompany-specific wrinkles

1. **~14 plugins, not one.** Claude Code reads `.claude-plugin/*`; Codex reads `.codex-plugin/*`.
   Every plugin therefore needs a `.codex-plugin/plugin.json`. `scripts/build-codex-manifests.sh`
   regenerates each one as a faithful projection of its `.claude-plugin/plugin.json` (adds the
   Codex `interface` block + a `skills` path when a `skills/` dir exists). Run on every push, so
   the two tools never drift. Three marketplace entries (`cs-ceo`, `goal`, `cs-partnership`) share
   the `cs-ceo-v15` folder — in Codex they ride inside the single `cs-ceo` plugin.

2. **Codex caches BY VERSION.** Codex will not rebuild a plugin's cache while its `version` is
   unchanged — restarting doesn't help. So `push`/`auto` **bump the patch version of every plugin**
   (in both manifests) as the cache-bust key, then mirror each plugin's source into
   `~/.codex/plugins/cache/CSnCompany_2-0/<name>/<version>/` so the new versions are on disk for
   Codex immediately. Claude Code reads bodies live and only needs `/reload-plugins` when plugins
   or skills are added/removed. The mirror is best-effort and no-ops if Codex hasn't ingested this
   marketplace yet.

## How to run it

The helper is `scripts/sync.sh` next to this file (`${CLAUDE_PLUGIN_ROOT}/skills/csn-sync/scripts`
in Claude Code; the script self-locates the repo if that variable isn't set, e.g. under Codex).

```bash
bash "<this-skill-dir>/scripts/sync.sh" <mode> [commit-message]
```

### Modes

| Mode | What it does |
|------|--------------|
| `status` (default) | Read-only. `git fetch`, then report ahead / behind / uncommitted and recommend the next mode. **Start here.** |
| `pull` | Fast-forward pull from GitHub. Refuses on uncommitted changes or divergence (use `auto`). Then mirrors the Codex cache. |
| `push [msg]` | Regenerate codex manifests, bump every plugin's version, stage all, commit, push. Refuses if the remote is ahead. |
| `auto [msg]` | The "just make it right" mode: commit local changes, rebase onto the remote if behind, then push. Stops on a rebase conflict. |

### Regenerating Codex manifests on their own

```bash
bash "<this-skill-dir>/scripts/build-codex-manifests.sh"          # write/refresh all
bash "<this-skill-dir>/scripts/build-codex-manifests.sh" --check  # dry-run, exit 1 on drift
```

## Decision flow

1. **Always run `status` first** and read the state out loud to the user.
2. Then:
   - `=> in sync` → nothing to do.
   - `=> BEHIND` → run `pull`.
   - `=> LOCAL CHANGES` → run `push` (offer a clear commit message describing what changed).
   - `=> DIVERGED` → run `auto`. On a rebase conflict, resolve in the repo, then
     `git rebase --continue && git push`.
3. After any `pull`/`push`/`auto`, remind the user to refresh the consuming tool (the script also
   prints this): **Claude Code** `/reload-plugins` when plugins/skills were added/removed;
   **Codex** just start a fresh session — the bumped-version cache was already mirrored.

## Guardrails

- **Never force-push.** If the remote is ahead, reconcile with `auto` (rebase), never `push -f`.
- The script touches two things only: the one real git repo (commit/push/pull), and — best-effort
  on `pull`/`push`/`auto` — Codex's versioned cache dirs, which it *populates* with an exact copy of
  each plugin's source. It never deletes other version dirs and never edits Codex's config.
- `push`/`auto` commit **all** working-tree changes and bump **every** plugin's version. Before
  pushing, glance at `git -C <repo> status` and confirm the pending changes are ones the user
  intends to publish (a version-only bump on unrelated plugins is expected and harmless).
- This skill is repo/tool plumbing only. It does not touch any CS plugin's runtime behavior.
