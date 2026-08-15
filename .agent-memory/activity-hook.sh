#!/bin/sh
# AGENTSTOZ_PROJECT_MEMORY_ACTIVITY
# Token-free activity marker. Prompt content from stdin is intentionally discarded.
cat >/dev/null 2>&1 || :
agent="${1:-unknown}"
case "$agent" in
  claude|codex) ;;
  *) agent="unknown" ;;
esac
hook_dir=$(CDPATH= cd -- "$(dirname -- "$0")" 2>/dev/null && pwd)
[ -n "$hook_dir" ] || exit 0
activity_path="$hook_dir/activity.json"
tmp_path="$activity_path.tmp-$$"
now=$(date -u "+%Y-%m-%dT%H:%M:%SZ")
printf '{"schemaVersion":1,"lastActivityAt":"%s","agent":"%s"}\n' "$now" "$agent" > "$tmp_path" 2>/dev/null || exit 0
mv -f "$tmp_path" "$activity_path" 2>/dev/null || :
exit 0
