#!/usr/bin/env bash
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REGISTRY_PY="$SCRIPT_DIR/artifact_registry.py"
cs_find_artifact()  { python3 "$REGISTRY_PY" find "$1" "${2:-}"; }
cs_list_artifacts() { python3 "$REGISTRY_PY" list "${1:-}"; }
cs_pipeline_state() { python3 "$REGISTRY_PY" state "${1:-}"; }
