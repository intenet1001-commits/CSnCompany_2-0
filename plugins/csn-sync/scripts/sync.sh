#!/usr/bin/env bash
# csn-sync — keep the CSnCompany_2-0 marketplace in sync across Claude Code and Codex.
#
# Architecture (modeled on nhdesign4-sync, adapted for a MULTI-plugin marketplace):
#   - There is exactly ONE git repo: the Claude Code marketplace clone
#     (~/.claude/plugins/marketplaces/CSnCompany_2-0, remote github.com/intenet1001-commits/CSnCompany_2-0).
#   - Codex references that SAME folder as a source_type="local" marketplace
#     (see ~/.codex/config.toml [marketplaces.CSnCompany_2-0]) and keeps a derived cache at
#     ~/.codex/plugins/cache/CSnCompany_2-0/<plugin-name>/<version>/ that it rebuilds itself.
#   - Therefore "sync Claude <-> Codex" == "git pull/push that one repo with GitHub",
#     then let each tool refresh its own view.
#
# Two things make CSnCompany different from nhdesign4 and are handled below:
#   1. It ships ~14 plugins, not one. Version bumps + cache mirroring loop over ALL of them.
#   2. Codex needs a .codex-plugin/plugin.json per plugin. build-codex-manifests.sh regenerates
#      those from each .claude-plugin/plugin.json so the two tools never drift.
#
# Usage:
#   sync.sh status        # (default) read-only: show ahead/behind + dirty state
#   sync.sh pull          # fast-forward pull from GitHub (refuses if uncommitted changes)
#   sync.sh push [msg]    # regen codex manifests, bump versions, stage all, commit, push
#   sync.sh auto [msg]    # commit local changes, reconcile with GitHub (rebase), push

set -uo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MODE="${1:-status}"
COMMIT_MSG="${2:-}"

say()  { printf '%s\n' "$*"; }
err()  { printf 'ERROR: %s\n' "$*" >&2; }

# --- Resolve the git repo (never the Codex cache copy) ------------------------
resolve_repo() {
  local candidates=("$HOME/.claude/plugins/marketplaces/CSnCompany_2-0")
  local codex_cfg="$HOME/.codex/config.toml"
  if [ -f "$codex_cfg" ]; then
    local p
    p=$(grep -A3 '\[marketplaces.CSnCompany_2-0\]' "$codex_cfg" 2>/dev/null \
        | grep -E '^\s*source\s*=' | head -1 | sed -E 's/^[^"]*"([^"]*)".*/\1/')
    [ -n "${p:-}" ] && candidates=("$p" "${candidates[@]}")
  fi
  local top
  top=$(git -C "$HERE" rev-parse --show-toplevel 2>/dev/null || true)
  [ -n "$top" ] && candidates=("$top" "${candidates[@]}")

  local c
  for c in "${candidates[@]}"; do
    if [ -d "$c/.git" ] \
       && git -C "$c" remote get-url origin 2>/dev/null | grep -q 'CSnCompany_2-0'; then
      printf '%s\n' "$c"; return 0
    fi
  done
  return 1
}

REPO=$(resolve_repo) || { err "could not locate the CSnCompany_2-0 git repo"; exit 1; }
MP="$REPO/.claude-plugin/marketplace.json"
say "repo: $REPO"

BRANCH=$(git -C "$REPO" symbolic-ref --short HEAD 2>/dev/null || echo main)

# List every unique physical plugin dir referenced by marketplace.json (absolute paths).
plugin_dirs() {
  jq -r '.plugins[].source' "$MP" | sed 's#^\./##' | sort -u | while read -r s; do
    [ -d "$REPO/$s" ] && printf '%s\n' "$REPO/$s"
  done
}

# --- Gather state -------------------------------------------------------------
git -C "$REPO" fetch origin --quiet 2>/dev/null || { err "git fetch failed (offline?)"; exit 1; }

UPSTREAM=$(git -C "$REPO" rev-parse --abbrev-ref --symbolic-full-name '@{u}' 2>/dev/null || true)
if [ -z "$UPSTREAM" ]; then
  err "branch '$BRANCH' has no upstream; run: git -C \"$REPO\" push -u origin $BRANCH"
  exit 1
fi

DIRTY=0
[ -n "$(git -C "$REPO" status --porcelain)" ] && DIRTY=1
read -r BEHIND AHEAD < <(git -C "$REPO" rev-list --left-right --count "$UPSTREAM"...HEAD 2>/dev/null || echo "0 0")

report_state() {
  say "branch: $BRANCH  ->  $UPSTREAM"
  say "ahead:  $AHEAD   behind: $BEHIND   uncommitted: $([ "$DIRTY" = 1 ] && echo yes || echo no)"
}

# Regenerate every .codex-plugin/plugin.json from its .claude-plugin twin (Codex/Claude parity).
regen_manifests() {
  if [ -x "$HERE/build-codex-manifests.sh" ] || [ -f "$HERE/build-codex-manifests.sh" ]; then
    bash "$HERE/build-codex-manifests.sh" || say "warn: manifest regen reported an issue"
  fi
}

# Codex caches each plugin BY VERSION and will NOT rebuild while the version is unchanged.
# Bump the patch level of EVERY plugin (both .codex-plugin and .claude-plugin) as the cache-bust.
bump_all_versions() {
  local dir cfile afile cur major minor patch new
  while read -r dir; do
    cfile="$dir/.codex-plugin/plugin.json"
    afile="$dir/.claude-plugin/plugin.json"
    [ -f "$cfile" ] || continue
    cur=$(jq -r '.version // empty' "$cfile" 2>/dev/null)
    printf '%s' "$cur" | grep -qE '^[0-9]+\.[0-9]+\.[0-9]+$' || continue
    IFS=. read -r major minor patch <<<"$cur"
    new="$major.$minor.$((patch + 1))"
    jq --arg v "$new" '.version=$v' "$cfile" > "$cfile.tmp" && mv "$cfile.tmp" "$cfile"
    if [ -f "$afile" ]; then
      jq --arg v "$new" '.version=$v' "$afile" > "$afile.tmp" && mv "$afile.tmp" "$afile"
    fi
    say "  bumped $(basename "$dir"): $cur -> $new"
  done < <(plugin_dirs)
}

# Best-effort: build Codex's versioned cache directly from source for EACH plugin, so updated
# skills/commands are on disk for Codex immediately. Keyed by the codex manifest's own name.
mirror_codex_cache() {
  local cache_root="$HOME/.codex/plugins/cache/CSnCompany_2-0"
  [ -d "$cache_root" ] || { say "codex cache: none yet (Codex hasn't ingested this marketplace) — skipping"; return 0; }
  local dir name ver target n=0
  while read -r dir; do
    local cfile="$dir/.codex-plugin/plugin.json"
    [ -f "$cfile" ] || continue
    name=$(jq -r '.name // empty' "$cfile"); ver=$(jq -r '.version // empty' "$cfile")
    [ -n "$name" ] && [ -n "$ver" ] || continue
    target="$cache_root/$name/$ver"
    mkdir -p "$target"
    if command -v rsync >/dev/null 2>&1; then
      rsync -a --delete --exclude '.DS_Store' --exclude '.git' "$dir/" "$target/" 2>/dev/null
    else
      rm -rf "${target:?}/"* 2>/dev/null; cp -R "$dir/." "$target/" 2>/dev/null
    fi
    n=$((n + 1))
  done < <(plugin_dirs)
  say "codex cache: mirrored $n plugin(s) -> $cache_root/<name>/<version>"
}

commit_all() {
  regen_manifests                    # keep codex manifests in step BEFORE bumping/staging
  bump_all_versions
  git -C "$REPO" add -A
  local msg="$COMMIT_MSG"
  [ -z "$msg" ] && msg="csn-sync: local changes $(git -C "$REPO" diff --cached --name-only | tr '\n' ' ' | cut -c1-120)"
  git -C "$REPO" commit -m "$msg" >/dev/null && say "committed: $msg"
}

refresh_hint() {
  say ""
  say "Next: each tool refreshes its own view of the marketplace —"
  say "  - Claude Code: /reload-plugins (or /plugin, or restart). Skill/command bodies are read live;"
  say "    a reload is only needed when plugins/skills are added/removed."
  say "  - Codex: the bumped-version cache was mirrored above, so the files are already on disk."
  say "    Start a new Codex session (or refresh plugins) to pick up the new versions."
}

# --- Modes --------------------------------------------------------------------
case "$MODE" in
  status)
    report_state
    if   [ "$AHEAD" -gt 0 ] && [ "$BEHIND" -gt 0 ]; then say "=> DIVERGED — run: sync.sh auto"
    elif [ "$BEHIND" -gt 0 ]; then say "=> BEHIND — run: sync.sh pull"
    elif [ "$AHEAD"  -gt 0 ] || [ "$DIRTY" = 1 ]; then say "=> LOCAL CHANGES — run: sync.sh push"
    else say "=> in sync"; fi
    ;;

  pull)
    if [ "$DIRTY" = 1 ]; then err "uncommitted changes present; commit or use 'auto' before pulling"; report_state; exit 1; fi
    if [ "$AHEAD" -gt 0 ] && [ "$BEHIND" -gt 0 ]; then err "branch has diverged; use 'auto' (rebase) instead of 'pull'"; exit 1; fi
    if [ "$BEHIND" -eq 0 ]; then say "already up to date"; mirror_codex_cache; exit 0; fi
    git -C "$REPO" merge --ff-only "$UPSTREAM" && say "pulled $BEHIND commit(s)"
    mirror_codex_cache
    refresh_hint
    ;;

  push)
    [ "$DIRTY" = 1 ] && commit_all
    if [ "$BEHIND" -gt 0 ]; then err "remote is ahead by $BEHIND; use 'auto' to rebase then push"; exit 1; fi
    git -C "$REPO" push origin "$BRANCH" && say "pushed to $UPSTREAM"
    mirror_codex_cache
    refresh_hint
    ;;

  auto)
    [ "$DIRTY" = 1 ] && commit_all
    read -r BEHIND AHEAD < <(git -C "$REPO" rev-list --left-right --count "$UPSTREAM"...HEAD 2>/dev/null || echo "0 0")
    if [ "$BEHIND" -gt 0 ]; then
      say "reconciling with remote (rebase)..."
      if ! git -C "$REPO" pull --rebase origin "$BRANCH"; then
        err "rebase hit conflicts — resolve in $REPO, then: git rebase --continue && git push"; exit 1
      fi
    fi
    read -r BEHIND AHEAD < <(git -C "$REPO" rev-list --left-right --count "$UPSTREAM"...HEAD 2>/dev/null || echo "0 0")
    [ "$AHEAD" -gt 0 ] && { git -C "$REPO" push origin "$BRANCH" && say "pushed to $UPSTREAM"; }
    mirror_codex_cache
    say "done — in sync"
    refresh_hint
    ;;

  *)
    err "unknown mode '$MODE' (use: status | pull | push [msg] | auto [msg])"; exit 1
    ;;
esac
