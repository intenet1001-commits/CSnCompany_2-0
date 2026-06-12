#!/usr/bin/env bash
# _bootstrap.sh의 SHARED_DIR 감지/CSN_SHARED_DIR override를 그대로 재사용한다 (R7)
_AR_DIR="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")" && pwd)"
source "$_AR_DIR/_bootstrap.sh"
REGISTRY_PY="$SHARED_DIR/artifact_registry.py"
[ -f "$REGISTRY_PY" ] || REGISTRY_PY="$_AR_DIR/artifact_registry.py"
cs_find_artifact()  { python3 "$REGISTRY_PY" find "$1" "${2:-}"; }
cs_artifact_meta()  { python3 "$REGISTRY_PY" find-meta "$1" "${2:-}"; }  # path+age_days+fresh|stale+gate state
cs_record_verdict() { python3 "$REGISTRY_PY" verdict "$@"; }             # <type> <PASS|FAIL|WARNINGS|BLOCKED> <round> [items...]
cs_list_artifacts() { python3 "$REGISTRY_PY" list "${1:-}"; }
cs_pipeline_state() { python3 "$REGISTRY_PY" state "${1:-}"; }
