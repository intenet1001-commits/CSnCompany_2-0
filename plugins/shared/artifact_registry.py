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

if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "state"
    if cmd == "find" and len(sys.argv) > 2:
        print(find(sys.argv[2], sys.argv[3] if len(sys.argv) > 3 else None) or "")
    elif cmd == "list":
        for a in _load(sys.argv[2] if len(sys.argv) > 2 else os.getcwd())["artifacts"]:
            print(f"{a['type']} ({a['plugin']}) -> {a['path']}")
    elif cmd == "state":
        for k, v in state(sys.argv[2] if len(sys.argv) > 2 else None).items():
            print(f"{k}: {'done' if v else 'missing'}")
