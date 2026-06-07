#!/usr/bin/env bash
# CS pre-pass bootstrap runner
# Tries: python3 → uv run → uv install → guided error
# Usage: bash run_prepass.sh <subcommand> [args...]

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PREPASS="$SCRIPT_DIR/scripts/pre_pass.py"

_run_with_python() {
  local py="$1"; shift
  "$py" "$PREPASS" "$@"
}

_try_uv_run() {
  uv run --quiet --no-project python "$PREPASS" "$@" 2>/dev/null
}

_install_uv() {
  echo '⚙️  uv not found — installing Python runtime manager (uv)...' >&2
  if command -v brew &>/dev/null; then
    brew install uv >&2
  else
    curl -LsSf https://astral.sh/uv/install.sh | sh >&2
    # Reload PATH after install
    export PATH="$HOME/.local/bin:$HOME/.cargo/bin:$PATH"
    # Source env if available
    [[ -f "$HOME/.local/bin/env" ]] && source "$HOME/.local/bin/env" 2>/dev/null || true
    [[ -f "$HOME/.cargo/env" ]]     && source "$HOME/.cargo/env" 2>/dev/null || true
  fi
  echo '✅  uv installed.' >&2
}

_no_python_error() {
  cat >&2 <<'EOF'

❌  Python not available and uv install failed.

Please install Python (recommended: via uv):
  curl -LsSf https://astral.sh/uv/install.sh | sh
  uv python install 3.12

Or via Homebrew:
  brew install python

Then retry your CS command.
EOF
  echo '{"error":"python_unavailable"}'
  exit 1
}

# ── main dispatch ─────────────────────────────────────────────────────────────

# 1. python3 in PATH?
if command -v python3 &>/dev/null; then
  _run_with_python python3 "$@"
  exit $?
fi

# 2. uv already in PATH?
if command -v uv &>/dev/null; then
  _try_uv_run "$@"
  exit $?
fi

# 3. Try auto-installing uv
_install_uv

if command -v uv &>/dev/null; then
  # Ensure Python is available under uv
  uv python install --quiet 2>/dev/null || true
  _try_uv_run "$@"
  exit $?
fi

_no_python_error
