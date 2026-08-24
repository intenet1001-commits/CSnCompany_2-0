#!/usr/bin/env python3
"""CS Series artifact registry"""
import json, os, sys
from pathlib import Path

MANIFEST = ".cs-artifacts/manifest.json"
DEFAULTS = {
    "CLARIFY.md":       ["CLARIFY.md", ".cs-artifacts/CLARIFY.md"],
    "PLAN.md":          ["PLAN.md", ".cs-artifacts/PLAN.md"],
    "DESIGN-REVIEW.md": ["DESIGN-REVIEW.md", ".cs-artifacts/DESIGN-REVIEW.md"],
    "SHIP-REPORT.md":   [".cs-artifacts/SHIP-REPORT.md", "SHIP-REPORT.md"],
    "REVIEW.md":        [".cs-artifacts/REVIEW.md", "REVIEW.md"],
    "IMPLEMENT-REPORT.md": [".cs-artifacts/IMPLEMENT-REPORT.md"],
    "TEST-REPORT.md":   ["tests/results/REPORT.md"],
}

def _load(root):
    p = Path(root) / MANIFEST
    return json.loads(p.read_text()) if p.exists() else {"artifacts": []}

def _save(root, m):
    p = Path(root) / MANIFEST
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(m, indent=2))

def register(atype, fpath, plugin, root=None):
    root = root or os.getcwd()
    m = _load(root)
    m["artifacts"] = [a for a in m["artifacts"] if a["type"] != atype]
    m["artifacts"].append({"type": atype, "path": str(fpath), "plugin": plugin})
    _save(root, m)

def find(atype, root=None):
    root = Path(root or os.getcwd())
    for e in reversed(_load(root)["artifacts"]):
        if e["type"] == atype:
            p = Path(e["path"]); p = p if p.is_absolute() else root / p
            if p.exists(): return str(p)
    for fb in DEFAULTS.get(atype, []):
        p = root / fb
        if p.exists(): return str(p)
    return None

def state(root=None):
    return {k: find(k, root) is not None for k in DEFAULTS}

STALE_DAYS = float(os.environ.get("CS_ARTIFACT_STALE_DAYS", "7"))

def find_meta(atype, root=None):
    """find + 신선도: GATE-LOOP/cs-ship가 오래된 스펙을 묵묵히 소비하지 않도록.

    파일이 없어도 registry에 verdict 기록이 있으면 게이트 상태는 복원한다
    (freshness="missing") — GATE-LOOP 라운드 추적이 파일 존재에 묶이지 않도록.
    """
    import time
    p = find(atype, root)
    entry = next((a for a in reversed(_load(Path(root or os.getcwd()))["artifacts"])
                  if a["type"] == atype), None)
    if not p and entry is None:
        return None
    if p:
        age_days = round((time.time() - Path(p).stat().st_mtime) / 86400, 1)
        freshness = "fresh" if age_days <= STALE_DAYS else "stale"
    else:
        age_days, freshness = None, "missing"
    entry = entry or {}
    return {
        "path": p,
        "age_days": age_days,
        "freshness": freshness,
        "verdict": entry.get("verdict"),
        "round": entry.get("round"),
        "blocking_items": entry.get("blocking_items", []),
    }

def record_verdict(atype, verdict, rnd, blocking_items, root=None):
    """GATE-LOOP 상태 기록: gate→fix→re-gate 라운드를 세션 간에 추적 가능하게."""
    root = root or os.getcwd()
    m = _load(root)
    for a in m["artifacts"]:
        if a["type"] == atype:
            a.update({"verdict": verdict, "round": int(rnd), "blocking_items": blocking_items})
            break
    else:
        m["artifacts"].append({"type": atype, "path": DEFAULTS.get(atype, [atype])[0],
                               "plugin": "unknown", "verdict": verdict,
                               "round": int(rnd), "blocking_items": blocking_items})
    _save(root, m)

if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "state"
    if cmd == "register":
        # register <type> <path> <plugin> [root] — ARTIFACT-CONTRACTS [2] 생산 등록
        if len(sys.argv) < 5:
            print("usage: register <type> <path> <plugin> [root]", file=sys.stderr)
            sys.exit(2)
        register(sys.argv[2], sys.argv[3], sys.argv[4],
                 sys.argv[5] if len(sys.argv) > 5 else None)
        print("ok")
    elif cmd == "find" and len(sys.argv) > 2:
        print(find(sys.argv[2], sys.argv[3] if len(sys.argv) > 3 else None) or "")
    elif cmd == "find-meta" and len(sys.argv) > 2:
        print(json.dumps(find_meta(sys.argv[2], sys.argv[3] if len(sys.argv) > 3 else None),
                         ensure_ascii=False))
    elif cmd == "verdict":
        # verdict <type> <PASS|FAIL|WARNINGS|BLOCKED> <round> [blocking_item ...]
        if len(sys.argv) < 5:
            print("usage: verdict <type> <PASS|FAIL|WARNINGS|BLOCKED> <round> [item ...]",
                  file=sys.stderr)
            sys.exit(2)
        record_verdict(sys.argv[2], sys.argv[3], sys.argv[4], sys.argv[5:])
        print("ok")
    elif cmd == "list":
        for a in _load(sys.argv[2] if len(sys.argv) > 2 else os.getcwd())["artifacts"]:
            extra = f" [{a['verdict']} r{a.get('round')}]" if a.get("verdict") else ""
            print(f"{a['type']} ({a['plugin']}) -> {a['path']}{extra}")
    elif cmd == "state":
        for k, v in state(sys.argv[2] if len(sys.argv) > 2 else None).items():
            print(f"{k}: {'done' if v else 'missing'}")
