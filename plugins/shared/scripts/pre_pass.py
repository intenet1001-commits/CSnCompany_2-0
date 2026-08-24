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
  learn-append [FLAGS...]     → append a structured learning candidate to the BTW store
  learn-update-status [...]   → atomically mark a queued learning pending/promoted/rejected
  version-check <plugin_dir>  → assert VERSION == Claude/Codex manifests == SKILL frontmatter
  index-check [exp_dir]       → cs-experiencing 학습 INDEX ↔ 본문 정합성 검증 (commit gate)
"""

from __future__ import annotations  # 지원 런타임에서 annotation 평가를 지연한다.

import datetime
import hashlib
import json
import math
import os
import re
import subprocess
import sys
import tempfile
import time
import uuid
from contextlib import contextmanager
from pathlib import Path
from typing import Optional, Tuple

try:
    import fcntl
except ImportError:  # Windows fallback uses an exclusive lock marker below.
    fcntl = None

HOME = Path.home()
MARKETPLACE = HOME / ".claude/plugins/marketplaces/CSnCompany_2-0"
BASE = MARKETPLACE / "plugins"
REPO_ROOT = Path(__file__).resolve().parents[3]
SOURCE_PLUGINS = REPO_ROOT / "plugins"
MAX_LEARNING_QUEUE_BYTES = 4 * 1024 * 1024
MAX_PENDING_LEARNINGS = 500
MAX_LEARNING_ENTRY_BYTES = 16 * 1024
SESSION_DIGEST_PENDING_LIMIT = 20
MAX_SESSION_DIGEST_SCAN_FILES = 256
MAX_SESSION_DIGEST_SCAN_BYTES = 4 * 1024 * 1024
MAX_SESSION_DIGEST_SKILL_ENTRIES = 200
MAX_SESSION_DIGEST_TITLE_BYTES = 240
MAX_SESSION_DIGEST_TEXT_BYTES = 512
MAX_SESSION_DIGEST_PROVENANCE_BYTES = 128
MAX_SESSION_DIGEST_OUTPUT_BYTES = 128 * 1024
LEARNING_FIELD_BYTE_LIMITS = {
    "plugin": 256,
    "lesson": 6_000,
    "evidence": 6_000,
    "tier": 32,
    "source-run-id": 1_024,
    "source-range": 1_024,
    "memory-id": 512,
    "candidate-key": 64,
}


def _strip_control_chars(value: str) -> str:
    return "".join(
        char
        for char in value
        if char in "\n\t" or (ord(char) >= 32 and ord(char) != 127)
    )


def _redact_secrets(value: str) -> tuple[str, list[str]]:
    patterns = [
        ("private-key", re.compile(r"-----BEGIN [^-\n]*PRIVATE KEY-----.*?-----END [^-\n]*PRIVATE KEY-----", re.I | re.S)),
        ("openai-key", re.compile(r"\bsk-[A-Za-z0-9_-]{20,}\b")),
        ("github-token", re.compile(r"\b(?:gh[pousr]_[A-Za-z0-9]{36,}|github_pat_[A-Za-z0-9_]{20,})\b")),
        ("gitlab-token", re.compile(r"\bglpat-[A-Za-z0-9_-]{20,}\b")),
        ("slack-token", re.compile(r"\bxox[baprs]-[A-Za-z0-9-]{16,}\b", re.I)),
        ("slack-webhook", re.compile(r"https://hooks\.slack\.com/services/T[A-Z0-9]{8,}/B[A-Z0-9]{8,}/[A-Za-z0-9_-]{20,}", re.I)),
        ("stripe-key", re.compile(r"\b(?:(?:sk|rk)_(?:live|test)_|whsec_)[A-Za-z0-9]{16,}\b")),
        ("google-api-key", re.compile(r"\bAIza[0-9A-Za-z_-]{35}\b")),
        ("google-oauth-token", re.compile(r"\bya29\.[A-Za-z0-9_-]{20,}\b")),
        ("npm-token", re.compile(r"\bnpm_[A-Za-z0-9]{30,}\b")),
        ("pypi-token", re.compile(r"\bpypi-[A-Za-z0-9_-]{20,}\b")),
        ("huggingface-token", re.compile(r"\bhf_[A-Za-z0-9]{30,}\b")),
        ("sendgrid-token", re.compile(r"\bSG\.[A-Za-z0-9_-]{16,}\.[A-Za-z0-9_-]{16,}\b")),
        ("aws-key", re.compile(r"\b(?:AKIA|ASIA)[0-9A-Z]{16}\b")),
        ("jwt", re.compile(r"\beyJ[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\b")),
        (
            "credential-assignment",
            re.compile(
                r"(?im)\b(?:api[_-]?key|access[_-]?token|auth[_-]?token|password|secret|token)\s*[:=]\s*[\"']?([^\s\"']{16,})"
            ),
        ),
    ]
    clean = _strip_control_chars(value)
    found: list[str] = []
    for name, pattern in patterns:
        if pattern.search(clean):
            found.append(name)
            clean = pattern.sub("[REDACTED]", clean)
    high_entropy = re.compile(
        r"(?<![A-Za-z0-9_+=-])[A-Za-z0-9_+=-]{32,256}(?![A-Za-z0-9_+=-])"
    )
    credential_context = re.compile(
        r"(?i)(?:authorization\s*:\s*bearer|bearer|api[_-]?key|access[_-]?token|auth[_-]?token|password|secret|token|credential)"
    )
    public_context = re.compile(
        r"(?i)(?:integrity|checksum|digest|sha(?:1|224|256|384|512)|public[_ -]?key|ssh-(?:rsa|ed25519))"
    )

    def redact_high_entropy(match: re.Match[str]) -> str:
        token = match.group(0).rstrip("=")
        if re.fullmatch(r"[0-9a-fA-F]+", token):
            return match.group(0)
        if re.fullmatch(r"[0-9a-fA-F]{8}-[0-9a-fA-F-]{27,}", token):
            return match.group(0)
        context = clean[max(0, match.start() - 48):min(len(clean), match.end() + 48)]
        if public_context.search(context) or not credential_context.search(context):
            return match.group(0)
        classes = sum((
            any(char.islower() for char in token),
            any(char.isupper() for char in token),
            any(char.isdigit() for char in token),
            any(char in "_+=-" for char in token),
        ))
        if classes < 3 or len(set(token)) < 12:
            return match.group(0)
        frequencies = {
            char: token.count(char) / len(token)
            for char in set(token)
        }
        entropy = -sum(part * math.log2(part) for part in frequencies.values())
        if entropy < 4.0:
            return match.group(0)
        found.append("high-entropy-token")
        return "[REDACTED]"

    clean = high_entropy.sub(redact_high_entropy, clean)
    return clean, sorted(set(found))


# ── low-level helpers ─────────────────────────────────────────────────────────

def _marketplace_plugins() -> list[dict]:
    """marketplace.json이 플러그인 이름/경로/설명의 단일 출처 (R9)."""
    mj = MARKETPLACE / ".claude-plugin" / "marketplace.json"
    try:
        return json.loads(mj.read_text(encoding="utf-8")).get("plugins", [])
    except Exception:
        return []


def _atomic_write_json(path: Path, value: object) -> None:
    """같은 디렉토리의 0600 임시 파일을 fsync한 뒤 원자적으로 교체한다."""
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(
        dir=str(path.parent),
        prefix=f".{path.name}.",
        suffix=".tmp",
    )
    try:
        if hasattr(os, "fchmod"):
            os.fchmod(fd, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8") as tmp:
            json.dump(value, tmp, ensure_ascii=False, indent=2)
            tmp.write("\n")
            tmp.flush()
            os.fsync(tmp.fileno())
        os.replace(tmp_name, path)
        try:
            os.chmod(path, 0o600)
        except OSError:
            pass
    except BaseException:
        try:
            os.unlink(tmp_name)
        except OSError:
            pass
        raise


@contextmanager
def _queue_lock(path: Path):
    """BTW 큐별 advisory lock — 모든 read/modify/write 구간을 직렬화한다."""
    path.parent.mkdir(parents=True, exist_ok=True)
    lock_path = path.with_name(f".{path.name}.lock")
    if fcntl is not None:
        fd = os.open(str(lock_path), os.O_CREAT | os.O_RDWR, 0o600)
        try:
            if hasattr(os, "fchmod"):
                os.fchmod(fd, 0o600)
            fcntl.flock(fd, fcntl.LOCK_EX)
            yield
        finally:
            try:
                fcntl.flock(fd, fcntl.LOCK_UN)
            finally:
                os.close(fd)
        return

    marker = lock_path.with_suffix(lock_path.suffix + ".exclusive")
    deadline = time.time() + 10.0
    marker_fd = None
    while marker_fd is None:
        try:
            marker_fd = os.open(
                str(marker),
                os.O_CREAT | os.O_EXCL | os.O_WRONLY,
                0o600,
            )
        except FileExistsError:
            try:
                if time.time() - marker.stat().st_mtime > 1800:
                    marker.unlink()
                    continue
            except FileNotFoundError:
                continue
            if time.time() >= deadline:
                raise TimeoutError(f"BTW queue lock is busy: {marker}")
            time.sleep(0.05)
    try:
        yield
    finally:
        os.close(marker_fd)
        try:
            marker.unlink()
        except FileNotFoundError:
            pass


def _read_learning_queue(path: Path, *, missing_ok: bool) -> list:
    """큐를 읽되 손상된 JSON/비배열을 빈 큐로 덮어쓰지 않는다."""
    if not path.is_file():
        if missing_ok:
            return []
        raise FileNotFoundError(f"BTW store not found: {path}")
    if path.stat().st_size > MAX_LEARNING_QUEUE_BYTES:
        raise ValueError(
            f"BTW store exceeds the {MAX_LEARNING_QUEUE_BYTES}-byte limit"
        )
    try:
        items = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as exc:
        raise ValueError(f"BTW store read failure: {exc}") from exc
    if not isinstance(items, list):
        raise ValueError("BTW store must contain a JSON array")
    return items


def _json_bytes(value: object) -> int:
    return len(
        (json.dumps(value, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
    )


def _truncate_utf8(value: object, maximum_bytes: int) -> str:
    if not isinstance(value, str):
        return ""
    encoded = value.encode("utf-8")
    if len(encoded) <= maximum_bytes:
        return value
    return encoded[:maximum_bytes].decode("utf-8", errors="ignore")


def _bounded_digest_text(value: object) -> str:
    return _truncate_utf8(value, MAX_SESSION_DIGEST_TEXT_BYTES)


def _bounded_digest_provenance(value: object) -> dict:
    if not isinstance(value, dict):
        return {}
    bounded: dict[str, str] = {}
    for key in ("source_run_id", "memory_id", "source_range", "candidate_key"):
        raw = value.get(key)
        if isinstance(raw, str) and raw:
            bounded[key] = _truncate_utf8(raw, MAX_SESSION_DIGEST_PROVENANCE_BYTES)
    return bounded


def _write_learning_queue(path: Path, items: list) -> None:
    size = _json_bytes(items)
    if size > MAX_LEARNING_QUEUE_BYTES:
        raise ValueError(
            f"BTW store would exceed the {MAX_LEARNING_QUEUE_BYTES}-byte limit"
        )
    _atomic_write_json(path, items)


def _canonical_entry_hash(item: dict) -> str:
    """ID/status와 무관한 canonical content hash."""
    payload = {key: value for key, value in item.items() if key not in {"id", "status"}}
    encoded = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _unique_id(base: str, used: set[str]) -> str:
    candidate = base
    suffix = 2
    while candidate in used:
        candidate = f"{base}-{suffix}"
        suffix += 1
    return candidate


def _normalize_learning_queue(items: list) -> bool:
    """Legacy pending-patch와 누락/중복 ID를 결정론적으로 정규화한다."""
    changed = False
    used: set[str] = set()
    for item in items:
        if not isinstance(item, dict):
            continue

        legacy_pending = "status" not in item and item.get("type") == "pending-patch"
        if legacy_pending:
            # 기존 임의 ID가 있어도 본문에서 계산한 안정 ID로 이관한다.
            base_id = f"btw-legacy-{_canonical_entry_hash(item)[:24]}"
            normalized_id = _unique_id(base_id, used)
            if item.get("id") != normalized_id:
                item["id"] = normalized_id
                changed = True
            item["status"] = "pending"
            changed = True
        else:
            item_id = item.get("id")
            if not isinstance(item_id, str) or not item_id or item_id in used:
                base_id = f"btw-repaired-{_canonical_entry_hash(item)[:24]}"
                normalized_id = _unique_id(base_id, used)
                if item_id != normalized_id:
                    item["id"] = normalized_id
                    changed = True

        item_id = item.get("id")
        if isinstance(item_id, str) and item_id:
            used.add(item_id)
    return changed


def _provenance_tuple(item: dict) -> Optional[Tuple[str, str, str]]:
    provenance = item.get("provenance")
    if not isinstance(provenance, dict):
        return None
    values = (
        provenance.get("source_run_id"),
        provenance.get("memory_id"),
        provenance.get("source_range"),
    )
    if not all(isinstance(value, str) and value for value in values):
        return None
    return values


def _provenance_candidate_key(item: dict) -> Optional[str]:
    provenance = item.get("provenance")
    if not isinstance(provenance, dict):
        return None
    value = provenance.get("candidate_key")
    return value if isinstance(value, str) and value else None


def _is_pending_learning(item: object) -> bool:
    """Canonical pending 또는 status 키가 없는 legacy pending-patch."""
    if not isinstance(item, dict):
        return False
    return item.get("status") == "pending" or (
        "status" not in item and item.get("type") == "pending-patch"
    )


# 도메인 short-key 별칭 (게이트/버전업에서 쓰는 축약명만 등록)
DOMAIN_ALIASES = {
    "CS-test": "test", "CS-plan": "plan", "CS-codebase-review": "review",
    "cs-design": "design", "cs-ceo": "ceo", "cs-clarify": "clarify",
    "cs-ship": "ship", "cs-smart-run": "smart-run", "cs-experiencing": "experiencing",
    "cs-end": "cs-end",
}


def _marketplace_domains() -> list[tuple]:
    """[(plugin_name, source_path, alias)] — 별칭 등록된 도메인만."""
    out = []
    for p in _marketplace_plugins():
        alias = DOMAIN_ALIASES.get(p.get("name", ""))
        if alias:
            out.append((p["name"], p.get("source", ""), alias))
    return out


def latest_plugin(prefix: str) -> str:
    def vnum(p: Path) -> int:
        m = re.search(r"v(\d+)$", p.name)
        return int(m.group(1)) if m else 0
    # 숫자 정렬 필수: 사전순이면 v9 > v26 으로 잘못 정렬됨
    dirs = sorted(BASE.glob(f"{prefix}v*"), key=vnum)
    if not dirs:
        # prefix without trailing dash (e.g. "cs-smart-run")
        exact = BASE / prefix
        return str(exact) if exact.is_dir() else ""
    return str(dirs[-1])


_SKIP_DIRS = {".bak", "node_modules", ".git", "__pycache__", ".cache", ".DS_Store"}


def find_skill(name: str) -> str:
    """Search known locations for <name>/SKILL.md, skipping unsafe dirs."""
    roots = [
        SOURCE_PLUGINS,
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


_CPO = HOME / ".claude/plugins/marketplaces/claude-plugins-official"


def _find_official_plugin(name: str) -> str:
    """claude-plugins-official 마켓플레이스에서 플러그인 디렉토리 탐색.
    plugins/ 와 external_plugins/ 둘 다 확인. fallback으로 일반 캐시도 탐색.
    """
    for subdir in ("plugins", "external_plugins"):
        candidate = _CPO / subdir / name
        if candidate.is_dir():
            return str(candidate)
    for root in [HOME / ".claude/plugins/marketplaces", HOME / ".claude/plugins/cache"]:
        if not root.is_dir():
            continue
        if (root / name).is_dir():
            return str(root / name)
        for sub in root.iterdir():
            if sub.is_dir() and (sub / name).is_dir():
                return str(sub / name)
    return ""


def _find_mcp_server(name: str) -> bool:
    """~/.claude/settings.json의 mcpServers에서 name 키(대소문자 무관) 검색."""
    for sf in [HOME / ".claude/settings.json", HOME / ".claude/settings.local.json"]:
        if not sf.is_file():
            continue
        try:
            data = json.loads(sf.read_text(encoding="utf-8"))
            servers = data.get("mcpServers", {})
            if any(k.lower() == name.lower() for k in servers):
                return True
        except Exception:
            pass
    return False


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
        "ceo":          latest_plugin("cs-ceo-"),
        "ship":         latest_plugin("cs-ship-"),   # /cs-company SHIP phase (PIPELINE-PROTOCOL)
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

    # ── official plugin health (claude-plugins-official) ──────────────────────
    serena_path     = _find_official_plugin("serena")
    playwright_path = _find_official_plugin("playwright")
    hookify_path    = _find_official_plugin("hookify")
    serena_installed     = bool(serena_path)     or _find_mcp_server("serena")
    playwright_installed = bool(playwright_path) or _find_mcp_server("playwright")

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
        # 라우팅이 메모리를 소비하도록 세션 다이제스트를 동봉 (R7)
        "session_digest": _compact_digest(plugins.get("experiencing", "")),
        "official_plugins": {
            "serena": {
                "installed": serena_installed,
                "path": serena_path,
                "install_cmd": "/plugin install serena@claude-plugins-official",
                "description": "코드 인텔리전스 — 심볼 검색, 정의 탐색, 참조 분석",
            },
            "playwright": {
                "installed": playwright_installed,
                "path": playwright_path,
                "install_cmd": "/plugin install playwright@claude-plugins-official",
                "description": "브라우저 자동화 — 웹 테스트, 스크린샷, 네트워크 분석",
            },
            "hookify": {
                "installed": bool(hookify_path),
                "path": hookify_path,
                "install_cmd": "/plugin install hookify@claude-plugins-official",
                "description": "훅 생성 (Anthropic 공식) — 동작 차단, 패턴 방지",
            },
        },
    }


def _compact_digest(experiencing_dir: str) -> dict:
    """ceo-preflight에 동봉하는 경량 다이제스트 — 전체 본문 없이 인덱스/카운트만."""
    skill = f"{experiencing_dir}/skills/experiencing/SKILL.md" if experiencing_dir else ""
    try:
        d = cmd_session_digest(["--skill", skill] if skill else [])
        return {
            "btw_count":     d.get("btw_count", 0),
            "btw_pending":   d.get("btw_pending", [])[:5],
            "domains_used":  d.get("domains_used", []),
            "knowhow_count": len(d.get("skill_snapshot", [])),
            "stale_count":   len(d.get("stale_entries", [])),
        }
    except Exception as e:
        return {"error": str(e)[:120]}


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
    skill_scan_files = 0
    skill_scan_bytes = 0
    skill_snapshot_has_more = False
    skill_quarantined = 0
    truncation_reasons: set[str] = set()
    source = Path(skill_path) if skill_path else None
    scan_files: list[Path] = []
    if source and source.is_file() and not source.is_symlink():
        scan_files.append(source)
        knowledge_dir = source.parent / "knowledge"
        if knowledge_dir.is_dir() and not knowledge_dir.is_symlink():
            discovered: list[Path] = []
            try:
                with os.scandir(knowledge_dir) as iterator:
                    for entry in iterator:
                        if len(discovered) >= MAX_SESSION_DIGEST_SCAN_FILES:
                            skill_snapshot_has_more = True
                            truncation_reasons.add("skill-file-limit")
                            break
                        if (
                            entry.name.endswith(".md")
                            and entry.is_file(follow_symlinks=False)
                        ):
                            discovered.append(Path(entry.path))
            except OSError:
                truncation_reasons.add("skill-scan-error")
            scan_files.extend(sorted(discovered))
    elif source:
        truncation_reasons.add("skill-source-unsafe-or-missing")

    scan_files = scan_files[:MAX_SESSION_DIGEST_SCAN_FILES]
    header_re = re.compile(
        r"^### (\d+)\.\s+(.+?)\s+\((\d{4}-\d{2}-\d{2})\)",
        re.MULTILINE,
    )
    tier_re = re.compile(r"<!--\s*tier:\s*(principle|tactical)\s*-->")
    seen_n: set[int] = set()
    for path in scan_files:
        if len(skill_snapshot) >= MAX_SESSION_DIGEST_SKILL_ENTRIES:
            skill_snapshot_has_more = True
            truncation_reasons.add("skill-entry-limit")
            break
        remaining = MAX_SESSION_DIGEST_SCAN_BYTES - skill_scan_bytes
        if remaining <= 0:
            skill_snapshot_has_more = True
            truncation_reasons.add("skill-byte-limit")
            break
        try:
            if path.is_symlink():
                raise OSError("symlinked skill source")
            with path.open("rb") as handle:
                payload = handle.read(remaining + 1)
        except OSError:
            truncation_reasons.add("skill-scan-error")
            continue
        skill_scan_files += 1
        if len(payload) > remaining:
            payload = payload[:remaining]
            skill_snapshot_has_more = True
            truncation_reasons.add("skill-byte-limit")
        skill_scan_bytes += len(payload)
        text = payload.decode("utf-8", errors="ignore")
        for match in header_re.finditer(text):
            number = int(match.group(1))
            if number in seen_n:
                continue
            seen_n.add(number)
            if len(skill_snapshot) >= MAX_SESSION_DIGEST_SKILL_ENTRIES:
                skill_snapshot_has_more = True
                truncation_reasons.add("skill-entry-limit")
                break
            raw_title = match.group(2).strip()
            _, detectors = _redact_secrets(raw_title)
            if detectors:
                skill_quarantined += 1
                truncation_reasons.add("secret-quarantine")
                continue
            tier_match = tier_re.search(text[match.end():match.end() + 200])
            skill_snapshot.append({
                "n": number,
                "title": _truncate_utf8(raw_title, MAX_SESSION_DIGEST_TITLE_BYTES),
                "date": match.group(3),
                "tier": tier_match.group(1) if tier_match else "tactical",
            })
    skill_snapshot.sort(key=lambda entry: entry["n"])

    # ── 2. BTW pending items ──────────────────────────────────────────────────
    btw_pending: list[dict] = []
    btw_count = 0
    btw_quarantined = 0
    btw_quarantine_detectors: set[str] = set()
    btw_error = ""
    btw_path = Path(btw_file)
    if btw_path.is_file():
        try:
            with _queue_lock(btw_path):
                items = _read_learning_queue(btw_path, missing_ok=False)
                if _normalize_learning_queue(items):
                    _write_learning_queue(btw_path, items)
            for it in items:
                if not isinstance(it, dict):
                    continue
                if not _is_pending_learning(it):
                    continue
                btw_count += 1
                _, detectors = _redact_secrets(
                    json.dumps(it, ensure_ascii=False, sort_keys=True)
                )
                if detectors:
                    btw_quarantined += 1
                    btw_quarantine_detectors.update(detectors)
                    truncation_reasons.add("secret-quarantine")
                    continue
                if len(btw_pending) >= SESSION_DIGEST_PENDING_LIMIT:
                    truncation_reasons.add("pending-window-limit")
                    continue
                idea = it.get("idea") or it.get("learning") or it.get("change") or ""
                btw_pending.append({
                    "id": it.get("id"),
                    "idea": _bounded_digest_text(idea),
                    "date": it.get("date", ""),
                    "evidence": _bounded_digest_text(it.get("evidence", "")),
                    "tier": it.get("tier", "tactical"),
                    "provenance": _bounded_digest_provenance(
                        it.get("provenance", {})
                    ),
                })
        except (FileNotFoundError, ValueError, OSError):
            btw_error = "queue-unavailable-or-invalid"

    # ── 3. Domain usage (GRU Update Gate) — git diff heuristic ───────────────
    # 패턴은 marketplace.json에서 파생 (R9 단일 출처) — 하드코딩 테이블 금지
    DOMAIN_PATTERNS: dict[str, list[str]] = {}
    for name, src, alias in _marketplace_domains():
        dir_pattern = re.sub(r"-v\d+$", "-v", Path(src).name)
        DOMAIN_PATTERNS[alias] = [dir_pattern, f"/{name}/"]
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

    result = {
        "domains_used":    domains_used,
        "skill_snapshot":  skill_snapshot,
        "skill_snapshot_returned": len(skill_snapshot),
        "skill_snapshot_has_more": skill_snapshot_has_more,
        "skill_scan_files": skill_scan_files,
        "skill_scan_bytes": skill_scan_bytes,
        "skill_quarantined": skill_quarantined,
        "btw_pending":     btw_pending,
        "btw_count":       btw_count,
        "btw_returned":    len(btw_pending),
        "btw_has_more":    btw_count > len(btw_pending),
        "btw_quarantined": btw_quarantined,
        "btw_quarantine_detectors": sorted(btw_quarantine_detectors),
        "btw_error": btw_error,
        "stale_entries":   stale_entries,
        "stale_count":     len(stale_entries),
        "digest_truncated": bool(truncation_reasons),
        "truncation_reasons": sorted(truncation_reasons),
    }

    def rendered_size() -> int:
        return len((json.dumps(result, indent=2) + "\n").encode("utf-8"))

    while rendered_size() > MAX_SESSION_DIGEST_OUTPUT_BYTES:
        result["digest_truncated"] = True
        reasons = set(result["truncation_reasons"])
        reasons.add("output-byte-limit")
        result["truncation_reasons"] = sorted(reasons)
        if result["skill_snapshot"]:
            removed = result["skill_snapshot"].pop()
            result["stale_entries"] = [
                item for item in result["stale_entries"]
                if item["n"] != removed["n"]
            ]
            result["skill_snapshot_returned"] = len(result["skill_snapshot"])
            result["skill_snapshot_has_more"] = True
            result["stale_count"] = len(result["stale_entries"])
        elif result["btw_pending"]:
            result["btw_pending"].pop()
            result["btw_returned"] = len(result["btw_pending"])
            result["btw_has_more"] = True
        elif result["domains_used"]:
            result["domains_used"].pop()
        elif result["stale_entries"]:
            result["stale_entries"].pop()
            result["stale_count"] = len(result["stale_entries"])
        else:
            break
    return result


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
        SOURCE_PLUGINS,
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


def _plugin_root_from_path(start: Path) -> Optional[Path]:
    """Walk up from a skill/agent path to the nearest real plugin manifest."""
    current = start
    for _ in range(7):
        if (current / ".claude-plugin" / "plugin.json").exists():
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
            agent_names = {path.stem for path in agents_dir.glob("*.md")}
            hint = _SKILL_TO_AGENT_HINT.get(name, "")
            matching_agent = (
                (hint and hint in agent_names)
                or name in agent_names
                or name.replace("-", "_") in agent_names
            )
            if matching_agent:
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


def cmd_learn_append(argv: list) -> dict:
    """learn-append --plugin X --lesson "..." [--evidence "..."] [--tier tactical|principle]
    [--source-run-id ID] [--source-range RANGE] [--memory-id ID]
    [--candidate-key STABLE_ENTRY_VERSION_ID]

    어떤 플러그인이든 구조화된 학습 후보를 BTW 저장소에 추가한다 (R7).
    승격은 /cs-end Learning Gate가 담당 — 여기서는 캡처만.
    """
    fields = {
        "plugin": "",
        "lesson": "",
        "evidence": "",
        "tier": "tactical",
        "source-run-id": "",
        "source-range": "",
        "memory-id": "",
        "candidate-key": "",
    }
    btw_file = HOME / ".claude" / ".experiencing-btw.json"
    i = 0
    while i < len(argv):
        a = argv[i]
        for key in fields:
            if a == f"--{key}" and i + 1 < len(argv):
                i += 1
                fields[key] = argv[i]
            elif a.startswith(f"--{key}="):
                fields[key] = a[len(f"--{key}=") :]
        if a == "--btw-file" and i + 1 < len(argv):
            i += 1
            btw_file = Path(argv[i])
        elif a.startswith("--btw-file="):
            btw_file = Path(a[len("--btw-file=") :])
        i += 1
    if not fields["plugin"] or not fields["lesson"]:
        return {"error": "learn-append requires --plugin and --lesson"}
    for field, byte_limit in LEARNING_FIELD_BYTE_LIMITS.items():
        if len(fields[field].encode("utf-8")) > byte_limit:
            return {
                "error": (
                    f"learn-append --{field} exceeds its {byte_limit}-byte limit"
                )
            }
    _, secret_detectors = _redact_secrets("\n".join(fields.values()))
    if secret_detectors:
        return {
            "error": "learn-append rejected secret indicators",
            "detectors": secret_detectors,
        }
    provenance_values = (
        fields["source-run-id"].strip(),
        fields["memory-id"].strip(),
        fields["source-range"].strip(),
    )
    if fields["plugin"].startswith("project-memory:") and not all(provenance_values):
        return {
            "error": (
                "project-memory:* learn-append requires --source-run-id, "
                "--memory-id, and --source-range together"
            )
        }
    requested_candidate_key = fields["candidate-key"].strip()
    if requested_candidate_key and not re.fullmatch(
        r"memory-[0-9a-f]{24}", requested_candidate_key
    ):
        return {"error": "learn-append --candidate-key has an invalid format"}
    if not fields["evidence"]:
        # LOOP-PROTOCOL [a]: 근거 없는 학습은 tactical 상한
        fields["tier"] = "tactical"

    supplied_provenance = all(provenance_values)
    requested_provenance = (
        provenance_values if supplied_provenance else None
    )
    if requested_candidate_key and requested_provenance is None:
        return {"error": "learn-append --candidate-key requires complete provenance"}
    requested_idea = f"[{fields['plugin']}] {fields['lesson']}"
    try:
        with _queue_lock(btw_file):
            items = _read_learning_queue(btw_file, missing_ok=True)
            queue_changed = _normalize_learning_queue(items)

            if requested_candidate_key:
                existing = next(
                    (
                        item
                        for item in items
                        if isinstance(item, dict)
                        and _provenance_candidate_key(item) == requested_candidate_key
                    ),
                    None,
                )
                if existing is not None:
                    if _provenance_tuple(existing) != requested_provenance:
                        return {
                            "error": "learn-append --candidate-key provenance conflicts with an existing candidate"
                        }
                    if queue_changed:
                        _write_learning_queue(btw_file, items)
                    return {
                        "appended": existing,
                        "created": False,
                        "deduplicated": True,
                        "total_pending": sum(
                            1 for item in items if _is_pending_learning(item)
                        ),
                    }

            if requested_provenance is not None:
                existing = next(
                    (
                        item
                        for item in items
                        if isinstance(item, dict)
                        and _provenance_tuple(item) == requested_provenance
                        and item.get("idea") == requested_idea
                    ),
                    None,
                )
                if existing is not None:
                    if queue_changed:
                        _write_learning_queue(btw_file, items)
                    return {
                        "appended": existing,
                        "created": False,
                        "deduplicated": True,
                        "total_pending": sum(
                            1 for item in items if _is_pending_learning(item)
                        ),
                    }

            pending_count = sum(1 for item in items if _is_pending_learning(item))
            if pending_count >= MAX_PENDING_LEARNINGS:
                return {
                    "error": (
                        "learn-append pending queue reached its "
                        f"{MAX_PENDING_LEARNINGS}-item limit"
                    )
                }

            used_ids = {
                item["id"]
                for item in items
                if isinstance(item, dict)
                and isinstance(item.get("id"), str)
                and item["id"]
            }
            if requested_candidate_key:
                provenance_key = requested_candidate_key.encode("utf-8")
                base_id = f"btw-memory-{hashlib.sha256(provenance_key).hexdigest()[:24]}"
                entry_id = _unique_id(base_id, used_ids)
            elif requested_provenance is not None:
                provenance_key = "\0".join(
                    (*requested_provenance, requested_idea)
                ).encode("utf-8")
                base_id = f"btw-provenance-{hashlib.sha256(provenance_key).hexdigest()[:24]}"
                entry_id = _unique_id(base_id, used_ids)
            else:
                entry_id = f"btw-{datetime.date.today().isoformat()}-{uuid.uuid4().hex}"
                while entry_id in used_ids:
                    entry_id = f"btw-{datetime.date.today().isoformat()}-{uuid.uuid4().hex}"

            entry = {
                "id": entry_id,
                "idea": requested_idea,
                "evidence": fields["evidence"],
                "tier": fields["tier"],
                "provenance": {
                    "source_run_id": provenance_values[0],
                    "source_range": provenance_values[2],
                    "memory_id": provenance_values[1],
                    **(
                        {"candidate_key": requested_candidate_key}
                        if requested_candidate_key
                        else {}
                    ),
                },
                "date": datetime.date.today().isoformat(),
                "status": "pending",
            }
            if _json_bytes(entry) > MAX_LEARNING_ENTRY_BYTES:
                return {
                    "error": (
                        "learn-append entry exceeds its "
                        f"{MAX_LEARNING_ENTRY_BYTES}-byte limit"
                    )
                }
            items.append(entry)
            if _json_bytes(items) > MAX_LEARNING_QUEUE_BYTES:
                items.pop()
                return {
                    "error": (
                        "learn-append queue exceeds its "
                        f"{MAX_LEARNING_QUEUE_BYTES}-byte limit"
                    )
                }
            _write_learning_queue(btw_file, items)
    except (FileNotFoundError, ValueError, OSError) as exc:
        return {"error": str(exc)}

    return {
        "appended": entry,
        "created": True,
        "deduplicated": False,
        "total_pending": sum(1 for item in items if _is_pending_learning(item)),
    }


def cmd_learn_update_status(argv: list) -> dict:
    """learn-update-status --id ID --status promoted|pending|rejected [--note "..."].

    cs-end 없이 즉시 승격한 학습도 canonical 큐에서 원자적으로 상태를 바꿔
    다음 session-digest가 같은 항목을 다시 제안하지 않게 한다.
    """
    fields = {"id": "", "status": "", "note": ""}
    note_provided = False
    btw_file = HOME / ".claude" / ".experiencing-btw.json"
    i = 0
    while i < len(argv):
        a = argv[i]
        matched = False
        for key in fields:
            if a == f"--{key}" and i + 1 < len(argv):
                i += 1
                fields[key] = argv[i]
                note_provided = note_provided or key == "note"
                matched = True
                break
            if a.startswith(f"--{key}="):
                fields[key] = a[len(f"--{key}=") :]
                note_provided = note_provided or key == "note"
                matched = True
                break
        if not matched:
            if a == "--btw-file" and i + 1 < len(argv):
                i += 1
                btw_file = Path(argv[i])
            elif a.startswith("--btw-file="):
                btw_file = Path(a[len("--btw-file=") :])
        i += 1

    if not fields["id"] or not fields["status"]:
        return {"error": "learn-update-status requires --id and --status", "updated": False}
    allowed_statuses = {"pending", "promoted", "rejected"}
    if fields["status"] not in allowed_statuses:
        return {
            "error": "learn-update-status --status must be pending, promoted, or rejected",
            "updated": False,
        }
    try:
        with _queue_lock(btw_file):
            items = _read_learning_queue(btw_file, missing_ok=False)
            pre_normalization_matches = [
                item
                for item in items
                if isinstance(item, dict) and item.get("id") == fields["id"]
            ]
            queue_changed = _normalize_learning_queue(items)
            matches = [
                item
                for item in items
                if isinstance(item, dict) and item.get("id") == fields["id"]
            ]

            # Legacy statusless 항목은 정규화 중 ID가 바뀐다. 기존 ID가 정확히
            # 한 항목만 가리켰다면 같은 객체를 이어서 갱신한다.
            if len(matches) == 1:
                target = matches[0]
            elif not matches and len(pre_normalization_matches) == 1:
                target = pre_normalization_matches[0]
            else:
                if queue_changed:
                    _write_learning_queue(btw_file, items)
                if len(matches) > 1 or len(pre_normalization_matches) > 1:
                    return {
                        "error": f"learning id is not unique: {fields['id']}",
                        "updated": False,
                    }
                return {
                    "error": f"learning id not found: {fields['id']}",
                    "updated": False,
                }

            target["status"] = fields["status"]
            if note_provided:
                target["note"] = fields["note"]
            _write_learning_queue(btw_file, items)
    except (FileNotFoundError, ValueError, OSError) as exc:
        return {"error": str(exc), "updated": False}

    return {
        "updated": target,
        "updated_count": 1,
        "total_pending": sum(1 for item in items if _is_pending_learning(item)),
    }


def cmd_version_check(argv: list) -> dict:
    """version-check <plugin_dir> — VERSION == both manifests == SKILL frontmatter 단언 (R7).

    불일치 시 ok=false — version-up STEP 4b는 이 결과로 push를 중단해야 한다.
    """
    if not argv:
        return {"error": "version-check requires a plugin directory"}
    root = Path(argv[0]).expanduser()
    if not root.is_dir():
        return {"error": f"not a directory: {root}", "ok": False}

    sources: dict[str, str] = {}
    vf = root / "VERSION"
    if vf.is_file():
        sources["VERSION"] = vf.read_text(encoding="utf-8").strip()
    pj = root / ".claude-plugin" / "plugin.json"
    if pj.is_file():
        try:
            sources["plugin.json"] = str(json.loads(pj.read_text(encoding="utf-8")).get("version", ""))
        except Exception as e:
            return {"error": f"plugin.json parse failure: {e}", "ok": False}
    codex_pj = root / ".codex-plugin" / "plugin.json"
    if codex_pj.is_file():
        try:
            sources[".codex-plugin/plugin.json"] = str(
                json.loads(codex_pj.read_text(encoding="utf-8")).get("version", "")
            )
        except Exception as e:
            return {"error": f".codex-plugin/plugin.json parse failure: {e}", "ok": False}
    resolved_root = root.resolve()
    for ancestor in (resolved_root, *resolved_root.parents):
        marketplace_file = ancestor / ".claude-plugin" / "marketplace.json"
        if not marketplace_file.is_file():
            continue
        try:
            marketplace = json.loads(marketplace_file.read_text(encoding="utf-8"))
        except Exception as e:
            return {"error": f"marketplace.json parse failure: {e}", "ok": False}
        entries = marketplace.get("plugins", []) if isinstance(marketplace, dict) else []
        for entry in entries if isinstance(entries, list) else []:
            if not isinstance(entry, dict) or not entry.get("source"):
                continue
            entry_path = (ancestor / str(entry["source"]).lstrip("./")).resolve()
            if entry_path == resolved_root and "version" in entry:
                sources["marketplace.json"] = str(entry.get("version", ""))
                break
        if any(
            (ancestor / str(entry.get("source", "")).lstrip("./")).resolve()
            == resolved_root
            for entry in entries
            if isinstance(entry, dict) and entry.get("source")
        ):
            break
    fm_re = re.compile(r"^version:\s*[\"']?([\w.\-]+)[\"']?\s*$", re.MULTILINE)
    for sk in sorted(root.glob("skills/*/SKILL.md")):
        head = sk.read_text(encoding="utf-8")[:2000]
        m = fm_re.search(head)
        if m:
            sources[str(sk.relative_to(root))] = m.group(1)

    def norm(v: str) -> tuple:
        # "1" == "1.0.0": 숫자 튜플로 정규화 후 후행 0 제거
        parts = [int(x) for x in re.findall(r"\d+", v)] or [0]
        while len(parts) > 1 and parts[-1] == 0:
            parts.pop()
        return tuple(parts)

    values = {norm(v) for v in sources.values()}
    return {
        "plugin": root.name,
        "sources": sources,
        "ok": len(values) <= 1,
        "mismatch": sorted(set(sources.values())) if len(values) > 1 else [],
    }


def cmd_index_check(argv: list) -> dict:
    """index-check [experiencing_dir] — 학습 INDEX ↔ 본문 정합성 결정론 검증.

    LLM 체크리스트(반박 패스)가 3회 놓친 드리프트 클래스(#95-99 INDEX 누락,
    #100 위치 포인터 오염, 인라인 #12-16 번호 충돌)를 기계적으로 차단한다.

    검사 항목:
      C1  본문(### N.)이 있는데 INDEX 행이 없음
      C2  INDEX 행의 위치 포인터(인라인 / knowledge/*.md)에 실제 본문이 없음
      C3  본문 번호 전역 중복 (SKILL.md + knowledge/* 통틀어 번호는 유일)
      C4  INDEX 번호 중복
      C5  INDEX 번호 연속성 (1..max 공백 없음)
      C6  SKILL.md 인라인 본문 개수 ≤ INLINE_CAP (본문 오프로드 강제 게이트)

    ok=false면 학습 저장(STEP 2) 및 버전업 commit(STEP 4b)을 진행하지 않는다.
    """
    INLINE_CAP = 15
    root = Path(argv[0]).expanduser() if argv else Path(latest_plugin("cs-experiencing-"))
    skill = root / "skills" / "experiencing" / "SKILL.md"
    if not skill.is_file():
        return {"error": f"SKILL.md not found: {skill}", "ok": False}
    know_dir = skill.parent / "knowledge"

    body_re = re.compile(r"^### (\d+)\. ", re.MULTILINE)
    # INDEX 행: | N | 제목 | tier | 태그 | 위치 |  (제목/태그에 파이프 금지가 전제)
    row_re = re.compile(r"^\|\s*(\d+)\s*\|(?:[^|\n]*\|){3}\s*([^|\n]+?)\s*\|\s*$", re.MULTILINE)

    text = skill.read_text(encoding="utf-8")
    inline_bodies = [int(m.group(1)) for m in body_re.finditer(text)]
    knowledge_bodies: dict[str, list[int]] = {}
    if know_dir.is_dir():
        for kf in sorted(know_dir.glob("*.md")):
            nums = [int(m.group(1)) for m in body_re.finditer(kf.read_text(encoding="utf-8"))]
            if nums:
                knowledge_bodies[kf.name] = nums

    index_rows: dict[int, str] = {}
    dup_index: list[int] = []
    for m in row_re.finditer(text):
        num, loc = int(m.group(1)), m.group(2).strip()
        if num in index_rows:
            dup_index.append(num)
        index_rows[num] = loc

    violations: list[str] = []

    # C3 — 전역 번호 유일성
    all_bodies: list[tuple[int, str]] = [(n, "SKILL.md(인라인)") for n in inline_bodies]
    for fname, nums in knowledge_bodies.items():
        all_bodies += [(n, f"knowledge/{fname}") for n in nums]
    seen: dict[int, str] = {}
    for n, where in all_bodies:
        if n in seen:
            violations.append(f"C3 번호 중복: #{n} — {seen[n]} 와 {where} 양쪽에 본문 존재")
        else:
            seen[n] = where

    # C4 — INDEX 번호 중복
    for n in dup_index:
        violations.append(f"C4 INDEX 행 중복: #{n}")

    # C1 — 본문은 있는데 INDEX 행 없음
    for n, where in sorted(all_bodies):
        if n not in index_rows:
            violations.append(f"C1 INDEX 누락: #{n} 본문이 {where} 에 있으나 INDEX 행 없음")

    # C2 — INDEX 위치 포인터가 실제 본문 위치와 불일치
    inline_set = set(inline_bodies)
    for n in sorted(index_rows):
        loc = index_rows[n]
        if "인라인" in loc:
            if n not in inline_set:
                violations.append(f"C2 포인터 불일치: INDEX #{n} 위치='인라인'인데 SKILL.md에 본문 없음")
        elif loc.startswith("knowledge/"):
            fname = loc.split("/", 1)[1].strip()
            if n not in set(knowledge_bodies.get(fname, [])):
                violations.append(f"C2 포인터 불일치: INDEX #{n} 위치='{loc}'인데 해당 파일에 본문 없음")
        else:
            violations.append(f"C2 위치 형식 오류: INDEX #{n} 위치='{loc}' (인라인 또는 knowledge/<file>.md 만 허용)")

    # C5 — 연속성 (전역 유일 번호는 재사용하지 않으므로 1..max 공백은 유실 신호)
    if index_rows:
        missing = sorted(set(range(1, max(index_rows) + 1)) - set(index_rows))
        if missing:
            violations.append(f"C5 번호 공백: INDEX에 {missing} 없음 (1..{max(index_rows)})")

    # C6 — 인라인 본문 상한 (프로젝트-특화 본문의 knowledge/ 오프로드 강제)
    if len(inline_bodies) > INLINE_CAP:
        violations.append(
            f"C6 인라인 상한 초과: SKILL.md 인라인 본문 {len(inline_bodies)}건 > {INLINE_CAP}건 "
            f"— 프로젝트-특화 본문을 knowledge/<topic>.md 로 이동하라"
        )

    return {
        "plugin": root.name,
        "checked": {
            "index_rows": len(index_rows),
            "inline_bodies": len(inline_bodies),
            "inline_cap": INLINE_CAP,
            "knowledge_files": {k: len(v) for k, v in knowledge_bodies.items()},
        },
        "ok": not violations,
        "violations": violations,
    }


def cmd_plugin_versions() -> dict:
    # marketplace.json 파생 (R9) — 등록된 source 디렉토리를 우선 신뢰하고,
    # 존재하지 않으면 latest_plugin() 디렉토리 스캔으로 폴백
    out: dict[str, str] = {}
    for name, src, _alias in _marketplace_domains():
        p = MARKETPLACE / src.lstrip("./") if src else None
        if p and p.is_dir():
            out[name] = str(p)
        else:
            prefix = re.sub(r"v\d+$", "", Path(src or name).name)
            out[name] = latest_plugin(prefix)
    return out


# ── dispatch ──────────────────────────────────────────────────────────────────

COMMANDS = {
    "ceo-preflight":   lambda rest: cmd_ceo_preflight(),
    "end-preflight":   lambda rest: cmd_end_preflight(rest),
    "git-status":      lambda rest: cmd_git_status(rest),
    "resolve-partner": lambda rest: cmd_resolve_partner(rest),
    "plugin-versions": lambda rest: cmd_plugin_versions(),
    "session-digest":  lambda rest: cmd_session_digest(rest),
    "learn-append":    lambda rest: cmd_learn_append(rest),
    "learn-update-status": lambda rest: cmd_learn_update_status(rest),
    "version-check":   lambda rest: cmd_version_check(rest),
    "index-check":     lambda rest: cmd_index_check(rest),
}


def main() -> None:
    argv = sys.argv[1:]
    if not argv or argv[0] not in COMMANDS:
        available = ", ".join(COMMANDS)
        print(json.dumps({"error": f"unknown subcommand. available: {available}"}))
        sys.exit(1)

    result = COMMANDS[argv[0]](argv[1:])
    print(json.dumps(result, indent=2))
    if isinstance(result, dict) and (
        bool(result.get("error"))
        or result.get("updated") is False
        or result.get("ok") is False
    ):
        sys.exit(1)


if __name__ == "__main__":
    main()
