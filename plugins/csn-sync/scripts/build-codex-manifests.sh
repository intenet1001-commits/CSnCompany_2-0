#!/usr/bin/env bash
# build-codex-manifests.sh — derive a .codex-plugin/plugin.json for every physical
# plugin dir referenced by CSnCompany_2-0's marketplace.json.
#
# Why: Codex consumes a marketplace like any other, but each plugin must carry its own
# .codex-plugin/plugin.json (verified against the OpenAI-bundled browser/latex plugins and
# the nhdesign4 plugin). Claude Code reads .claude-plugin/*; Codex reads .codex-plugin/*.
# This script keeps the Codex manifest a faithful, regenerable projection of the Claude one,
# so csn-sync can re-run it on every push and the two tools never drift.
#
# It is idempotent: re-running overwrites each .codex-plugin/plugin.json from source.
#
# Usage:
#   build-codex-manifests.sh            # generate/refresh all manifests
#   build-codex-manifests.sh --check    # report what would change, write nothing (exit 1 if drift)

set -uo pipefail

command -v jq >/dev/null 2>&1 || { echo "ERROR: jq is required" >&2; exit 1; }

CHECK=0
[ "${1:-}" = "--check" ] && CHECK=1

# --- Resolve repo root (the dir holding .claude-plugin/marketplace.json) -------
resolve_repo() {
  local here d top
  here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
  d="$here"
  while [ "$d" != "/" ]; do
    [ -f "$d/.claude-plugin/marketplace.json" ] && { printf '%s\n' "$d"; return 0; }
    d="$(dirname "$d")"
  done
  top="$HOME/.claude/plugins/marketplaces/CSnCompany_2-0"
  [ -f "$top/.claude-plugin/marketplace.json" ] && { printf '%s\n' "$top"; return 0; }
  return 1
}

REPO="$(resolve_repo)" || { echo "ERROR: could not locate CSnCompany_2-0 repo root" >&2; exit 1; }
MP="$REPO/.claude-plugin/marketplace.json"
echo "repo: $REPO"

# Title-case a plugin name for the Codex display name; keep all-caps tokens (CS) intact.
display_name() {
  printf '%s' "$1" | tr -- '-_' '  ' \
    | awk '{for(i=1;i<=NF;i++){ if($i ~ /^[A-Z]+$/){printf (i>1?" ":"") $i} else {printf (i>1?" ":"") toupper(substr($i,1,1)) substr($i,2)} } print ""}'
}

CHANGED=0
declare -a SEEN=()

# Iterate marketplace entries; dedupe by source dir (cs-ceo-v15 is shared by 3 entries).
while IFS=$'\t' read -r m_name m_source m_desc; do
  src="${m_source#./}"
  dir="$REPO/$src"
  [ -d "$dir" ] || { echo "skip (missing dir): $m_source"; continue; }

  skip=0
  for s in "${SEEN[@]:-}"; do [ "$s" = "$dir" ] && skip=1 && break; done
  [ "$skip" = 1 ] && continue
  SEEN+=("$dir")

  claude="$dir/.claude-plugin/plugin.json"

  if [ -f "$claude" ]; then
    name=$(jq -r '.name // empty' "$claude")
    version=$(jq -r '.version // empty' "$claude")
    desc=$(jq -r '.description // empty' "$claude")
    author=$(jq -c '.author // {"name":"intenet1001-commits","url":"https://github.com/intenet1001-commits"}' "$claude")
    keywords=$(jq -c '.keywords // []' "$claude")
  else
    name=""; version=""; desc=""; author=""; keywords="[]"
  fi
  [ -z "$name" ] && name="$m_name"
  [ -z "$desc" ] && desc="$m_desc"
  [ -z "$author" ] && author='{"name":"intenet1001-commits","url":"https://github.com/intenet1001-commits"}'
  if [ -z "$version" ]; then
    [ -f "$dir/VERSION" ] && version="$(tr -d ' \n' < "$dir/VERSION")"
    [ -z "$version" ] && version="1.0.0"
  fi

  disp="$(display_name "$name")"
  short=$(printf '%s' "$desc" | sed -E 's/^[^A-Za-z0-9가-힣]+//' | cut -c1-110)

  manifest=$(jq -n \
    --arg name "$name" \
    --arg version "$version" \
    --arg desc "$desc" \
    --argjson author "$author" \
    --argjson keywords "$keywords" \
    --arg disp "$disp" \
    --arg short "$short" \
    '{
      name: $name,
      version: $version,
      description: $desc,
      author: $author,
      repository: "https://github.com/intenet1001-commits/CSnCompany_2-0",
      license: "MIT",
      keywords: $keywords,
      interface: {
        displayName: $disp,
        shortDescription: $short,
        longDescription: $desc,
        developerName: "intenet1001-commits",
        category: "Engineering",
        capabilities: ["Interactive","Read","Write"],
        websiteURL: "https://github.com/intenet1001-commits/CSnCompany_2-0",
        defaultPrompt: [],
        brandColor: "#0F766E"
      }
    }')

  if [ -d "$dir/skills" ]; then
    manifest=$(printf '%s' "$manifest" | jq '. + {skills: "./skills/"}')
  fi

  out="$dir/.codex-plugin/plugin.json"
  new="$(printf '%s\n' "$manifest")"
  if [ -f "$out" ] && diff -q <(printf '%s\n' "$new") "$out" >/dev/null 2>&1; then
    echo "unchanged: $name ($version)  [$src]"
    continue
  fi

  CHANGED=$((CHANGED + 1))
  if [ "$CHECK" = 1 ]; then
    echo "would write: $name ($version)  [$src]"
  else
    mkdir -p "$dir/.codex-plugin"
    printf '%s\n' "$new" > "$out"
    echo "wrote: $name ($version)  [$src]"
  fi
done < <(jq -r '.plugins[] | [.name, .source, (.description // "")] | @tsv' "$MP")

echo "---"
if [ "$CHECK" = 1 ]; then
  echo "$CHANGED manifest(s) would change."
  [ "$CHANGED" -gt 0 ] && exit 1 || exit 0
else
  echo "$CHANGED manifest(s) written."
fi
