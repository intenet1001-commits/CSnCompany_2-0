#!/usr/bin/env bash
# CSnCompany Python Bootstrap v1.0
# Source this in any SKILL.md or agent that wants Python-accelerated analysis.
# Usage:
#   source "$BASE/shared/_bootstrap.sh"
#   csn_run "extract_summary.py" "$PROJECT_ROOT"   → JSON or {"fallback":true}

# CSN_SHARED_DIR를 외부에서 설정하면 그 경로 사용, 아니면 자동 감지
if [ -n "$CSN_SHARED_DIR" ]; then
  SHARED_DIR="$CSN_SHARED_DIR"
else
  _src="${BASH_SOURCE[0]:-$0}"
  _src_dir="$(cd "$(dirname "$_src")" 2>/dev/null && pwd)"
  # 감지된 디렉토리에 scripts/가 없으면 마켓플레이스에서 재탐색
  if [ ! -d "$_src_dir/scripts" ]; then
    _src_dir=$(find "$HOME/.claude/plugins/marketplaces" -path "*/shared/scripts" -maxdepth 6 2>/dev/null | head -1 | xargs dirname 2>/dev/null)
  fi
  SHARED_DIR="${_src_dir:-$HOME/.claude/plugins/marketplaces/CSnCompany_2-0/plugins/shared}"
fi
CSN_USE_PYTHON=false
CSN_PYTHON_CMD=""

_csn_ensure_python() {
  # uv 우선 (Python 자체도 설치 가능)
  if command -v uv &>/dev/null; then
    CSN_USE_UV=true
    CSN_USE_PYTHON=true
    return 0
  fi

  # python3 fallback
  if command -v python3 &>/dev/null; then
    CSN_USE_UV=false
    CSN_USE_PYTHON=true
    return 0
  fi

  # 안내 후 fallback
  CSN_USE_PYTHON=false
  >&2 echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
  >&2 echo " ⚡ Python 미설치 — 분석 품질/속도 향상을 위해 uv 설치를 권장합니다"
  >&2 echo ""
  >&2 echo "  Mac/Linux : curl -LsSf https://astral.sh/uv/install.sh | sh"
  >&2 echo "  Homebrew  : brew install uv"
  >&2 echo "  Windows   : winget install astral-sh.uv"
  >&2 echo ""
  >&2 echo "  설치 후 재실행하면 LLM 토큰 사용이 크게 줄어듭니다."
  >&2 echo "  지금은 LLM 직접 분석 방식으로 계속 진행합니다."
  >&2 echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
  return 1
}

# Run a Python script from shared/scripts/
# Returns JSON string. On failure returns {"fallback":true}
csn_run() {
  local script="$1"; shift
  local script_path="$SHARED_DIR/scripts/$script"

  if [ "$CSN_USE_PYTHON" != "true" ]; then
    echo '{"fallback":true,"reason":"no_python"}'
    return 1
  fi

  if [ ! -f "$script_path" ]; then
    echo '{"fallback":true,"reason":"script_not_found"}'
    return 1
  fi

  local result
  if [ "$CSN_USE_UV" = "true" ]; then
    result=$(uv run --quiet --no-project "$script_path" "$@" 2>/dev/null)
  else
    result=$(python3 "$script_path" "$@" 2>/dev/null)
  fi
  local exit_code=$?

  if [ $exit_code -ne 0 ] || [ -z "$result" ]; then
    echo '{"fallback":true,"reason":"script_error"}'
    return 1
  fi

  echo "$result"
}

# Init on source
_csn_ensure_python
