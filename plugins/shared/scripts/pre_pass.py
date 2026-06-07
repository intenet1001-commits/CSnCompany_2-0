#!/usr/bin/env python3
"""
CS-series Python pre-pass — file-system ops, git queries, path resolution.

Claude tokens are reserved for reasoning.  This script handles everything
that can be answered deterministically: plugin paths, partner skill paths,
git state, flag parsing.

Sub-commands
  ceo-preflight               → plugin + partner paths + context7 status
  end-preflight [FLAGS...]    → flag parsing + author check + initial git state
  git-status <dir>            → push status for one repo (run after git push)
  resolve-partner <name>      → dynamic SKILL.md path lookup
  plugin-versions             → latest dir for every CS plugin
  session-digest [FLAGS...]   → session pre-pass: domain usage, BTW pending, knowhow index, stale entries
"""

import datetime
import json
import os
import re
import subprocess
import sys
from pathlib import Path

HOME = Path.home()
MARKETPLACE = HOME / ".claude/plugins/marketplaces/CSnCompany_2-0"
BASE = MARKETPLACE / "plugins"


# ── low-level helpers ─────────────────────────────────────────────────────────

def latest_plugin(prefix: str) -> str:
    dirs = sorted(BASE.glob(f"{prefix}v*"), key=lambda p: p.name)
    if not dirs:
        # prefix without trailing dash (e.g. "cs-smart-run")
        exact = BASE / prefix
        return str(exact) if exact.is_dir() else ""
    return str(dirs[-1])


_SKIP_DIRS = {".bak", "node_modules", ".git", "__pycache__", ".cache", ".DS_Store"}


def find_skill(name: str) -> str:
    """Search known locations for <name>/SKILL.md, skipping unsafe dirs."""
    roots = [
        BASE,
        HOME / ".claude/plugins/marketplaces",
        HOME / ".claude/plugins/cache",
        HOME / ".claude/skills",
    ]
    for root in roots:
        root_str = str(root)
        if not os.path.isdir(root_str):
            continue
        for dirpath, dirnames, filenames in os.walk(root_str, onerror=lambda _: None):
            dirnames[:] = [d for d in dirnames if d not in _SKIP_DIRS]
            if os.path.basename(dirpath) == name and "SKILL.md" in filenames:
                return os.path.join(dirpath, "SKILL.md")
    return ""


def _git(repo: str, *args: str) -> str:
    try:
        return subprocess.check_output(
            ["git", "-C", repo, *args],
            stderr=subprocess.DEVNULL,
            text=True,
        ).strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return ""


def push_status(repo: str) -> dict:
    if not repo or not Path(repo).is_dir():
        return {"state": "na", "ahead": "0", "behind": "0", "branch": "", "remote": ""}
    ahead  = _git(repo, "rev-list", "--count", "@{u}..HEAD") or "0"
    behind = _git(repo, "rev-list", "--count", "HEAD..@{u}") or "0"
    branch = _git(repo, "branch", "--show-current")
    r_url  = _git(repo, "remote", "get-url", "origin")
    slug   = ""
    if r_url and "github.com" in r_url:
        slug = r_url.split("github.com")[-1].lstrip(":/")
        if slug.endswith(".git"):
            slug = slug[:-4]
    state = "pushed" if ahead == "0" else "unpushed"
    return {"state": state, "ahead": ahead, "behind": behind, "branch": branch, "remote": slug}


# ── sub-commands ──────────────────────────────────────────────────────────────

def cmd_ceo_preflight() -> dict:
    plugins = {
        "test":         latest_plugin("CS-test-"),
        "plan":         latest_plugin("CS-plan-"),
        "review":       latest_plugin("CS-codebase-review-"),
        "design":       latest_plugin("cs-design-"),
        "smartrun":     latest_plugin("cs-smart-run"),
        "clarify":      latest_plugin("cs-clarify-"),
        "experiencing": latest_plugin("cs-experiencing-"),
    }

    # superpowers
    sp_base = ""
    cache = HOME / ".claude/plugins/cache"
    if cache.is_dir():
        candidates = sorted(
            [p for p in cache.rglob("superpowers/*/skills") if p.is_dir()],
            key=lambda p: p.parent.name,
        )
        sp_base = str(candidates[-1]) if candidates else ""

    # omc (oh-my-claudecode) — exclude src/skills test-only dir
    omc_base = ""
    if cache.is_dir():
        candidates = sorted(
            [
                p for p in cache.rglob("oh-my-claudecode/*/skills")
                if p.is_dir() and "src/skills" not in str(p)
            ],
            key=lambda p: p.parent.name,
        )
        omc_base = str(candidates[-1]) if candidates else ""

    # omc agents — direct marketplace path (not cache)
    omc_marketplace = HOME / ".claude/plugins/marketplaces/omc"
    omc_agents: dict[str, str] = {}
    if (omc_marketplace / "agents").is_dir():
        for af in sorted((omc_marketplace / "agents").glob("*.md"))[:12]:
            omc_agents[af.stem] = str(af)

    # gstack
    gstack = ""
    for candidate in [
        HOME / ".claude/skills/gstack/SKILL.md",
        HOME / ".claude/plugins/marketplaces/gstack/skills/gstack/SKILL.md",
    ]:
        if candidate.exists():
            gstack = str(candidate)
            break
    if not gstack:
        gstack = find_skill("gstack")

    # context7
    c7 = str(HOME / ".claude/skills/context7-auto-research/SKILL.md")
    if not Path(c7).exists():
        c7 = find_skill("context7-auto-research")

    bkit = HOME / ".claude/plugins/marketplaces/bkit-marketplace"
    clarify_dir = plugins["clarify"]

    def sp(skill: str) -> str:
        return f"{sp_base}/{skill}/SKILL.md" if sp_base else ""

    def omc(skill: str) -> str:
        return f"{omc_base}/{skill}/SKILL.md" if omc_base else ""

    return {
        "plugins": plugins,
        "partners": {
            "superpowers": {
                "base":                 sp_base,
                "brainstorming":        sp("brainstorming"),
                "writing_plans":        sp("writing-plans"),
                "executing_plans":      sp("executing-plans"),
                "systematic_debugging": sp("systematic-debugging"),
                "dispatching_parallel": sp("dispatching-parallel-agents"),
            },
            "bkit": {
                "pdca": str(bkit / "skills/pdca/SKILL.md"),
                "qa":   str(bkit / "skills/qa-phase/SKILL.md"),
            },
            "omc": {
                "base":         omc_base,
                "deep_dive":    omc("deep-dive"),
                "autoresearch": omc("autoresearch"),
                "autopilot":    omc("autopilot"),
                "plugin_name":  "oh-my-claudecode",
                "agents":       omc_agents,
            },
            "gstack":  gstack,
            "clarify": f"{clarify_dir}/skills/cs-clarify/SKILL.md" if clarify_dir else "",
            "context7": c7,
        },
        "context7_installed": bool(c7 and Path(c7).exists()),
    }


def cmd_end_preflight(argv: list) -> dict:
    explicit_project = ""
    no_push = False
    no_compact = False
    learning_only = False
    no_decay_check = False
    explicit_domains = ""

    i = 0
    while i < len(argv):
        a = argv[i]
        if a.startswith("--project="):
            explicit_project = a[len("--project="):]
        elif a == "--project" and i + 1 < len(argv):
            i += 1
            explicit_project = argv[i]
        elif a == "--no-push":
            no_push = True
        elif a == "--no-compact":
            no_compact = True
        elif a == "--learning-only":
            learning_only = True
        elif a == "--no-decay-check":
            no_decay_check = True
        elif a.startswith("--domains="):
            explicit_domains = a[len("--domains="):]
        elif a == "--domains" and i + 1 < len(argv):
            i += 1
            explicit_domains = argv[i]
        i += 1

    marketplace_dir = str(MARKETPLACE)
    remote = _git(marketplace_dir, "remote", "get-url", "origin")
    auto_no_push = "intenet1001-commits" not in remote

    if not explicit_project:
        cwd_top = _git(os.getcwd(), "rev-parse", "--show-toplevel")
        if cwd_top and cwd_top != marketplace_dir:
            explicit_project = cwd_top

    return {
        "flags": {
            "explicit_project":  explicit_project,
            "no_push":           no_push or auto_no_push,
            "no_compact":        no_compact,
            "learning_only":     learning_only,
            "auto_no_push":      auto_no_push,
            "no_decay_check":    no_decay_check,
            "explicit_domains":  explicit_domains,
        },
        "git": {
            "marketplace": push_status(marketplace_dir),
            "project":     push_status(explicit_project) if explicit_project else {"state": "na"},
        },
        "paths": {
            "marketplace":  marketplace_dir,
            "project":      explicit_project,
            "project_name": Path(explicit_project).name if explicit_project else "",
        },
    }


def cmd_session_digest(argv: list) -> dict:
    """
    Session Pre-Pass Digest — LSTM Attention/KV-Cache pattern.

    Extracts a compact JSON digest shared by all Phase 1 agents, eliminating
    4x redundant full-history reads.

    Returns:
      domains_used    – CS domains active this session (git-diff heuristic)
      skill_snapshot  – knowhow index (number, title, date, tier) — NOT full body
      btw_pending     – list of pending BTW items
      btw_count       – total pending BTW count
      stale_entries   – knowhow entries flagged for decay review (Forget Gate)
    """
    skill_path = ""
    btw_file = str(HOME / ".claude" / ".experiencing-btw.json")

    i = 0
    while i < len(argv):
        a = argv[i]
        if a == "--skill" and i + 1 < len(argv):
            i += 1
            skill_path = argv[i]
        elif a.startswith("--skill="):
            skill_path = a[len("--skill="):]
        elif a == "--btw-file" and i + 1 < len(argv):
            i += 1
            btw_file = argv[i]
        elif a.startswith("--btw-file="):
            btw_file = a[len("--btw-file="):]
        i += 1

    # ── 1. Knowhow index (titles + dates only, no full body) ──────────────────
    skill_snapshot: list[dict] = []
    if skill_path and Path(skill_path).is_file():
        text = Path(skill_path).read_text(encoding="utf-8", errors="ignore")
        # Match: ### N. Title (YYYY-MM-DD)
        # Also capture optional <!-- tier: principle|tactical --> comment
        header_re = re.compile(
            r"^### (\d+)\.\s+(.+?)\s+\((\d{4}-\d{2}-\d{2})\)",
            re.MULTILINE,
        )
        tier_re = re.compile(r"<!--\s*tier:\s*(principle|tactical)\s*-->")
        entries = list(header_re.finditer(text))
        for m in entries:
            n, title, date_str = m.group(1), m.group(2).strip(), m.group(3)
            # Look for tier comment in the 3 lines after the header
            after = text[m.end():m.end() + 200]
            tier_match = tier_re.search(after)
            tier = tier_match.group(1) if tier_match else "tactical"  # default = tactical
            skill_snapshot.append({"n": int(n), "title": title, "date": date_str, "tier": tier})

    # ── 2. BTW pending items ──────────────────────────────────────────────────
    btw_pending: list[dict] = []
    if Path(btw_file).is_file():
        try:
            items = json.loads(Path(btw_file).read_text(encoding="utf-8"))
            if isinstance(items, list):
                btw_pending = [
                    {"id": it.get("id"), "idea": it.get("idea", ""), "date": it.get("date", "")}
                    for it in items
                    if isinstance(it, dict) and it.get("status") == "pending"
                ]
        except (json.JSONDecodeError, OSError):
            pass

    # ── 3. Domain usage (GRU Update Gate) — git diff heuristic ───────────────
    DOMAIN_PATTERNS: dict[str, list[str]] = {
        "test":   ["CS-test-v", "/CS-test/"],
        "plan":   ["CS-plan-v", "/CS-plan/"],
        "review": ["CS-codebase-review-v", "/CS-codebase-review/"],
        "design": ["cs-design-v", "/cs-design/"],
        "ceo":    ["cs-ceo-v", "/cs-ceo/"],
        "clarify":["cs-clarify-v", "/cs-clarify/"],
        "ship":   ["cs-ship-v", "/cs-ship/"],
    }
    marketplace_dir = str(MARKETPLACE)
    changed_files = _git(marketplace_dir, "diff", "--name-only", "HEAD~5..HEAD")
    domains_used = [
        domain
        for domain, patterns in DOMAIN_PATTERNS.items()
        if any(p in changed_files for p in patterns)
    ]
    # Always include cs-end itself if its files changed
    if "cs-end-v" in changed_files or "/cs-end/" in changed_files:
        if "cs-end" not in domains_used:
            domains_used.append("cs-end")

    # ── 4. Knowledge Decay check (Forget Gate) ────────────────────────────────
    TODAY = datetime.date.today()
    STALE_THRESHOLD_DAYS = 30
    DECAY_KEYWORDS = [
        "osascript", "window.open", "bun --watch", "clipboarditem",
        "v4", "v5", "config.toml", ".env", "api key",
        "bun.write", "bun.spawn", "osascript -e",
    ]
    stale_entries: list[dict] = []
    for entry in skill_snapshot:
        if entry["tier"] == "principle":
            continue
        try:
            entry_date = datetime.date.fromisoformat(entry["date"])
        except ValueError:
            continue
        age = (TODAY - entry_date).days
        if age < STALE_THRESHOLD_DAYS:
            continue
        title_lower = entry["title"].lower()
        if any(kw.lower() in title_lower for kw in DECAY_KEYWORDS):
            stale_entries.append({
                "n":    entry["n"],
                "title": entry["title"],
                "date":  entry["date"],
                "age_days": age,
            })

    return {
        "domains_used":    domains_used,
        "skill_snapshot":  skill_snapshot,
        "btw_pending":     btw_pending,
        "btw_count":       len(btw_pending),
        "stale_entries":   stale_entries,
        "stale_count":     len(stale_entries),
    }


def cmd_git_status(argv: list) -> dict:
    if not argv:
        return {"error": "git-status requires a directory argument"}
    return push_status(argv[0])


_SKILL_TO_AGENT_HINT: dict[str, str] = {
    "deep-dive":    "debugger",
    "autoresearch": "analyst",
    "autopilot":    "executor",
    "explore":      "explore",
    "brainstorm":   "architect",
    "analyze":      "analyst",
    "review":       "code-reviewer",
    "simplify":     "code-simplifier",
    "document":     "document-specialist",
    "design":       "designer",
    "debug":        "debugger",
    "execute":      "executor",
    "critique":     "critic",
}


def find_agent_file(name: str) -> str:
    """Search for agents/<name>.md in plugin marketplaces and cache."""
    roots = [
        HOME / ".claude/plugins/marketplaces",
        HOME / ".claude/plugins/cache",
    ]
    for root in roots:
        if not root.is_dir():
            continue
        for dirpath, dirnames, filenames in os.walk(str(root), onerror=lambda _: None):
            dirnames[:] = [d for d in dirnames if d not in _SKIP_DIRS]
            if os.path.basename(dirpath) == "agents" and f"{name}.md" in filenames:
                return os.path.join(dirpath, f"{name}.md")
    return ""


def _plugin_root_from_path(start: Path) -> Path | None:
    """Walk up from start to find a directory that has .claude-plugin/plugin.json or agents/."""
    current = start
    for _ in range(7):
        if (current / ".claude-plugin" / "plugin.json").exists() or (current / "agents").is_dir():
            return current
        current = current.parent
    return None


def _read_plugin_name(plugin_root: Path) -> str:
    pj = plugin_root / ".claude-plugin" / "plugin.json"
    if pj.exists():
        try:
            return json.loads(pj.read_text(encoding="utf-8")).get("name", "")
        except Exception:
            pass
    return ""


def _build_agent_result(name: str, skill_path: str, plugin_root: Path, plugin_name: str) -> dict:
    agents_dir = plugin_root / "agents"
    agent_files = sorted(agents_dir.glob("*.md"))
    agent_names = [f.stem for f in agent_files]
    hint = _SKILL_TO_AGENT_HINT.get(name, "")
    primary = (
        hint if hint and hint in agent_names
        else next((a for a in agent_names if a == name or a == name.replace("-", "_")), "")
        or (agent_names[0] if agent_names else "")
    )
    return {
        "name":        name,
        "found":       True,
        "type":        "AGENT",
        "path":        skill_path,
        "plugin_name": plugin_name,
        "invocation":  f"{plugin_name}:{primary}" if primary else "",
        "agents":      agent_names[:8],
    }


def find_partner_info(name: str) -> dict:
    """
    Find a partner and detect its invocation type.

    Returns:
      found        – bool
      type         – "AGENT" | "SKILL" | "PROTOCOL"
      path         – path to SKILL.md or agent .md (if found)
      plugin_name  – plugin name from .claude-plugin/plugin.json
      invocation   – "plugin_name:agent_name" or "plugin_name:skill_name"
      agents       – list of available agent names (AGENT type only)

    Type semantics:
      AGENT    → plugin has agents/ dir + plugin.json → Task(subagent_type=invocation)
      SKILL    → plugin has plugin.json but no agents/ → Skill(skill=invocation)
      PROTOCOL → only SKILL.md, no plugin.json → CEO reads and follows directly
    """
    # --- Primary: search by SKILL.md ----------------------------------------
    skill_path = find_skill(name)
    if skill_path:
        plugin_root = _plugin_root_from_path(Path(skill_path).parent)
        if plugin_root is None:
            # SKILL.md found but no plugin root (standalone skill) —
            # check if an agent file exists and prefer it when it has a proper plugin
            agent_file = find_agent_file(name)
            if agent_file:
                ar = _plugin_root_from_path(Path(agent_file).parent)
                if ar:
                    pn = _read_plugin_name(ar)
                    if pn:
                        return _build_agent_result(name, agent_file, ar, pn)
            return {"name": name, "found": True, "type": "PROTOCOL", "path": skill_path,
                    "plugin_name": "", "invocation": "", "agents": []}

        plugin_name = _read_plugin_name(plugin_root)
        agents_dir = plugin_root / "agents"

        if agents_dir.is_dir() and plugin_name:
            return _build_agent_result(name, skill_path, plugin_root, plugin_name)

        if plugin_name:
            skill_folder = Path(skill_path).parent.name
            return {"name": name, "found": True, "type": "SKILL", "path": skill_path,
                    "plugin_name": plugin_name, "invocation": f"{plugin_name}:{skill_folder}", "agents": []}

        return {"name": name, "found": True, "type": "PROTOCOL", "path": skill_path,
                "plugin_name": "", "invocation": "", "agents": []}

    # --- Fallback: search by agent file name (e.g. "executor", "analyst") ----
    agent_file = find_agent_file(name)
    if agent_file:
        plugin_root = _plugin_root_from_path(Path(agent_file).parent)
        if plugin_root:
            plugin_name = _read_plugin_name(plugin_root)
            if plugin_name:
                return _build_agent_result(name, agent_file, plugin_root, plugin_name)

    return {"name": name, "found": False, "type": "UNKNOWN", "path": "", "plugin_name": "", "invocation": "", "agents": []}


def cmd_resolve_partner(argv: list) -> dict:
    if not argv:
        return {"error": "resolve-partner requires a skill name"}
    return find_partner_info(argv[0])


def cmd_plugin_versions() -> dict:
    prefixes = [
        ("CS-test",             "CS-test-"),
        ("CS-plan",             "CS-plan-"),
        ("CS-codebase-review",  "CS-codebase-review-"),
        ("cs-design",           "cs-design-"),
        ("cs-smart-run",        "cs-smart-run"),
        ("cs-clarify",          "cs-clarify-"),
        ("cs-experiencing",     "cs-experiencing-"),
        ("cs-end",              "cs-end-"),
        ("cs-ceo",              "cs-ceo-"),
    ]
    return {name: latest_plugin(prefix) for name, prefix in prefixes}


# ── dispatch ──────────────────────────────────────────────────────────────────

COMMANDS = {
    "ceo-preflight":   lambda rest: cmd_ceo_preflight(),
    "end-preflight":   lambda rest: cmd_end_preflight(rest),
    "git-status":      lambda rest: cmd_git_status(rest),
    "resolve-partner": lambda rest: cmd_resolve_partner(rest),
    "plugin-versions": lambda rest: cmd_plugin_versions(),
    "session-digest":  lambda rest: cmd_session_digest(rest),
}


def main() -> None:
    argv = sys.argv[1:]
    if not argv or argv[0] not in COMMANDS:
        available = ", ".join(COMMANDS)
        print(json.dumps({"error": f"unknown subcommand. available: {available}"}))
        sys.exit(1)

    result = COMMANDS[argv[0]](argv[1:])
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
