#!/usr/bin/env python3
"""routing_sync — marketplace.json을 라우팅 메타데이터의 단일 출처로 유지 (R9).

  routing_sync.py check   → plugins/CLAUDE.md 라우팅 규칙이 marketplace.json에
                            없는 플러그인을 가리키면 ok=false로 보고 (drift 탐지)
  routing_sync.py write   → plugins/CLAUDE.md의 AUTO-PLUGIN-INVENTORY 블록을
                            marketplace.json에서 재생성

cs-end Phase 4 / version-up STEP 4 직후 `check`를 실행하고, drift가 보고되면
`write`로 인벤토리를 재생성한 뒤 수동 라우팅 규칙을 정리한다.
"""
import json
import re
import sys
from pathlib import Path

MARKETPLACE = Path(__file__).resolve().parents[2]  # .../plugins/shared/scripts → repo root? no: plugins/
REPO = MARKETPLACE.parent
MJ = REPO / ".claude-plugin" / "marketplace.json"
CLAUDE_MD = MARKETPLACE / "CLAUDE.md"
BEGIN = "<!-- AUTO-PLUGIN-INVENTORY:BEGIN (routing_sync.py write 로 재생성 — 직접 편집 금지) -->"
END = "<!-- AUTO-PLUGIN-INVENTORY:END -->"

# 라우팅 규칙에 등장하지만 이 마켓플레이스 소속이 아닌 외부 스킬 (drift 오탐 방지)
EXTERNAL_TARGETS = {
    "cs-sync", "office-hours", "investigate", "ship", "review",
    "plan-eng-review", "checkpoint", "smart-run",
}


def plugins() -> list[dict]:
    return json.loads(MJ.read_text(encoding="utf-8")).get("plugins", [])


def inventory_block() -> str:
    rows = ["| 플러그인 | 디렉토리 | 설명 |", "|---|---|---|"]
    for p in plugins():
        desc = p.get("description", "").split(" — ")[0].split(". ")[0][:90]
        rows.append(f"| {p['name']} | `{p.get('source', '')}` | {desc} |")
    return "\n".join([BEGIN, "", *rows, "", END])


def cmd_write() -> dict:
    text = CLAUDE_MD.read_text(encoding="utf-8")
    block = inventory_block()
    if BEGIN in text and END in text:
        new = re.sub(re.escape(BEGIN) + r".*?" + re.escape(END), block, text, flags=re.DOTALL)
    else:
        new = text.rstrip() + "\n\n## 플러그인 인벤토리 (자동 생성)\n\n" + block + "\n"
    CLAUDE_MD.write_text(new, encoding="utf-8")
    return {"ok": True, "plugins": len(plugins()), "file": str(CLAUDE_MD)}


def cmd_check() -> dict:
    """CLAUDE.md 라우팅 규칙의 'invoke X' 대상이 실제로 존재하는지 검증."""
    text = CLAUDE_MD.read_text(encoding="utf-8")
    targets = set(re.findall(r"invoke ([\w-]+)", text))
    known = {p["name"] for p in plugins()} | EXTERNAL_TARGETS
    unknown = sorted(t for t in targets if t not in known)
    missing_dirs = [
        p["name"] for p in plugins()
        if p.get("source") and not (REPO / p["source"].lstrip("./")).is_dir()
    ]
    ok = not unknown and not missing_dirs
    return {
        "ok": ok,
        "unknown_routing_targets": unknown,
        "marketplace_entries_missing_dir": missing_dirs,
    }


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "check"
    result = cmd_write() if cmd == "write" else cmd_check()
    print(json.dumps(result, ensure_ascii=False, indent=2))
    sys.exit(0 if result.get("ok") else 1)
