#!/usr/bin/env python3
"""Discover project memories and build fail-safe incremental training runs.

The helper is intentionally deterministic. It does not call an LLM and it never edits a
project memory. `scan` records the exact source snapshot that an agent should review;
`commit` advances the cursor only after the agent has finished updating the memory and
handling any cs-experiencing candidates.
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import re
import stat
import subprocess
import sys
import tempfile
import threading
import time
import urllib.parse
import urllib.request
import uuid
from contextlib import contextmanager, nullcontext
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

try:
    import fcntl
except ImportError:  # Windows fallback uses an exclusive lock marker below.
    fcntl = None


STATE_SCHEMA = 1
RUN_SCHEMA = 1
PARSER_VERSION = 1
MAX_STATE_BYTES = 16 * 1024 * 1024
MAX_CONFIG_BYTES = 64 * 1024
MAX_MEMORY_BYTES = 1_000_000
MAX_DIFF_CHARS = 24_000
MAX_UNTRACKED_CHARS = 12_000
MAX_GIT_UNTRACKED_FILES = 5_000
MAX_GIT_UNTRACKED_HASH_BYTES = 256 * 1024 * 1024
MAX_GIT_DIGEST_BYTES = 256 * 1024 * 1024
MAX_GIT_STDERR_BYTES = 1024 * 1024
GIT_TIMEOUT_SECONDS = 30
MAX_LINKED_WORKTREES = 64
MAX_LINKED_EVIDENCE_CHARS = 24_000
MAX_FLAGGED_INDEX_FILES = 5_000
MAX_FLAGGED_INDEX_HASH_BYTES = 256 * 1024 * 1024
MAX_FLAGGED_INDEX_EVIDENCE = 100
MAX_NON_GIT_FILES = 5_000
MAX_NON_GIT_HASH_BYTES = 256 * 1024 * 1024
MAX_TEXT_EXCERPT_BYTES = 2_500

TRAINABLE_SECTIONS = {
    "Key Decisions",
    "Strategic Patterns",
    "Recurring Issues",
    "Active Constraints",
    "Contested Entries",
}

IGNORED_DIRS = {
    ".git",
    ".agent-memory",
    "node_modules",
    ".next",
    "dist",
    "build",
    "coverage",
    "target",
    ".turbo",
    ".cache",
    ".venv",
    "venv",
    "__pycache__",
}

IGNORED_EXACT_PREFIXES = (
    ".claude/skills/project-memory/",
    ".claude/skills/project-session-end/",
    ".claude/skills/remember-session/",
    ".claude/skills/learn/",
    ".agents/skills/project-memory/",
    ".agents/skills/project-session-end/",
    ".agents/skills/remember-session/",
    ".agents/skills/learn/",
)

SENSITIVE_FILENAMES = {
    ".env",
    ".env.local",
    ".env.production",
    "credentials.json",
    "service-account.json",
    "id_rsa",
    "id_ed25519",
}

TEXT_EXTENSIONS = {
    ".c",
    ".cc",
    ".cpp",
    ".css",
    ".go",
    ".h",
    ".html",
    ".java",
    ".js",
    ".json",
    ".jsx",
    ".kt",
    ".kts",
    ".md",
    ".mjs",
    ".php",
    ".plist",
    ".py",
    ".rb",
    ".rs",
    ".sh",
    ".sql",
    ".swift",
    ".toml",
    ".ts",
    ".tsx",
    ".txt",
    ".vue",
    ".xml",
    ".yaml",
    ".yml",
    ".zsh",
}

SECRET_PATTERNS: Sequence[Tuple[str, re.Pattern[str]]] = (
    (
        "private-key",
        re.compile(
            r"-----BEGIN [A-Z0-9 ]*PRIVATE KEY-----[\s\S]*?"
            r"(?:-----END [A-Z0-9 ]*PRIVATE KEY-----|$)",
            re.IGNORECASE,
        ),
    ),
    ("openai-key", re.compile(r"\bsk-[A-Za-z0-9_-]{20,}\b")),
    ("github-token", re.compile(r"\bgh[pousr]_[A-Za-z0-9]{20,}\b")),
    ("aws-access-key", re.compile(r"\bAKIA[0-9A-Z]{16}\b")),
    (
        "credential-assignment",
        re.compile(
            r"(?im)\b(api[_-]?key|access[_-]?token|auth[_-]?token|client[_-]?secret|"
            r"token|password|passwd)\b\s*[:=]\s*[\"']?[^\s\"']{8,}"
        ),
    ),
)


class TrainingError(RuntimeError):
    pass


class NoRedirectHandler(urllib.request.HTTPRedirectHandler):
    def redirect_request(
        self,
        req: Any,
        fp: Any,
        code: int,
        msg: str,
        headers: Any,
        newurl: str,
    ) -> None:
        return None


def utc_now() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat().replace("+00:00", "Z")


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_text(text: str) -> str:
    return sha256_bytes(text.encode("utf-8"))


def canonical_json(value: Any) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def path_is_within(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
        return True
    except ValueError:
        return False


def stable_read_bytes(path: Path, limit: int) -> bytes:
    """Read a regular file with one retry when it changes during the read."""
    for attempt in range(2):
        before = path.stat()
        if not stat.S_ISREG(before.st_mode):
            raise TrainingError("regular file required: %s" % path)
        if before.st_size > limit:
            raise TrainingError("file exceeds %d-byte limit: %s" % (limit, path))
        with path.open("rb") as handle:
            data = handle.read(limit + 1)
        after = path.stat()
        if len(data) > limit:
            raise TrainingError("file exceeds %d-byte limit: %s" % (limit, path))
        signature_before = (
            before.st_dev,
            before.st_ino,
            before.st_size,
            before.st_mtime_ns,
        )
        signature_after = (
            after.st_dev,
            after.st_ino,
            after.st_size,
            after.st_mtime_ns,
        )
        if signature_before == signature_after:
            return data
        if attempt == 0:
            continue
    raise TrainingError("file changed while being read: %s" % path)


def stable_read_prefix(path: Path, limit: int) -> bytes:
    """Read at most limit bytes without rejecting an otherwise safe large text file."""
    for attempt in range(2):
        before = path.stat()
        if not stat.S_ISREG(before.st_mode):
            raise TrainingError("regular file required: %s" % path)
        with path.open("rb") as handle:
            data = handle.read(limit)
        after = path.stat()
        signature_before = (
            before.st_dev,
            before.st_ino,
            before.st_size,
            before.st_mtime_ns,
        )
        signature_after = (
            after.st_dev,
            after.st_ino,
            after.st_size,
            after.st_mtime_ns,
        )
        if signature_before == signature_after:
            return data
        if attempt == 0:
            continue
    raise TrainingError("file changed while being read: %s" % path)


def decode_utf8(data: bytes, path: Path) -> str:
    try:
        return data.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise TrainingError("invalid UTF-8 in %s: %s" % (path, exc)) from exc


def load_json_file(path: Path, limit: int) -> Any:
    data = stable_read_bytes(path, limit)
    try:
        return json.loads(decode_utf8(data, path))
    except json.JSONDecodeError as exc:
        raise TrainingError("invalid JSON in %s: %s" % (path, exc)) from exc


def atomic_write_json(
    path: Path,
    value: Any,
    max_bytes: Optional[int] = None,
) -> None:
    payload = (
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    ).encode("utf-8")
    if max_bytes is not None and len(payload) > max_bytes:
        raise TrainingError(
            "JSON payload exceeds %d-byte safety limit (%d bytes): %s"
            % (max_bytes, len(payload), path)
        )
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(prefix=".%s." % path.name, dir=str(path.parent))
    tmp_path = Path(tmp_name)
    try:
        if hasattr(os, "fchmod"):
            os.fchmod(fd, 0o600)
        with os.fdopen(fd, "wb") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(str(tmp_path), str(path))
        try:
            dir_fd = os.open(str(path.parent), os.O_RDONLY)
            try:
                os.fsync(dir_fd)
            finally:
                os.close(dir_fd)
        except OSError:
            pass
    finally:
        if tmp_path.exists():
            tmp_path.unlink()


def atomic_write_bytes(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(prefix=".%s." % path.name, dir=str(path.parent))
    tmp_path = Path(tmp_name)
    try:
        if hasattr(os, "fchmod"):
            os.fchmod(fd, 0o600)
        with os.fdopen(fd, "wb") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(str(tmp_path), str(path))
    finally:
        if tmp_path.exists():
            tmp_path.unlink()


class FileLock:
    def __init__(self, target: Path, timeout_seconds: float = 10.0) -> None:
        self.path = Path(str(target) + ".lock")
        self.timeout_seconds = timeout_seconds
        self.fd: Optional[int] = None

    def __enter__(self) -> "FileLock":
        deadline = time.time() + self.timeout_seconds
        while True:
            try:
                self.path.parent.mkdir(parents=True, exist_ok=True)
                self.fd = os.open(
                    str(self.path),
                    os.O_CREAT | os.O_EXCL | os.O_WRONLY,
                    0o600,
                )
                os.write(self.fd, ("%d\n" % os.getpid()).encode("ascii"))
                return self
            except FileExistsError:
                try:
                    age = time.time() - self.path.stat().st_mtime
                    if age > 1800:
                        self.path.unlink()
                        continue
                except FileNotFoundError:
                    continue
                if time.time() >= deadline:
                    raise TrainingError("state lock is busy: %s" % self.path)
                time.sleep(0.1)

    def __exit__(self, exc_type: Any, exc: Any, traceback: Any) -> None:
        if self.fd is not None:
            os.close(self.fd)
        try:
            self.path.unlink()
        except FileNotFoundError:
            pass


@contextmanager
def learning_queue_lock(path: Path) -> Iterable[None]:
    """Match pre_pass._queue_lock so queue writers share one advisory lock."""
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
                raise TimeoutError("BTW queue lock is busy: %s" % marker)
            time.sleep(0.05)
    try:
        yield
    finally:
        os.close(marker_fd)
        try:
            marker.unlink()
        except FileNotFoundError:
            pass


def default_state_path() -> Path:
    override = os.environ.get("CSNCOMPANY_MEMORY_TRAINING_STATE")
    if override:
        return Path(override).expanduser()
    return Path.home() / ".claude" / "state" / "long-term-memory-training.json"


def default_ports_path() -> Path:
    if sys.platform == "win32":
        appdata = os.environ.get("APPDATA")
        base = Path(appdata) if appdata else Path.home() / "AppData" / "Roaming"
        return base / "com.portmanager.portmanager" / "ports.json"
    return (
        Path.home()
        / "Library"
        / "Application Support"
        / "com.portmanager.portmanager"
        / "ports.json"
    )


def empty_state() -> Dict[str, Any]:
    return {"schemaVersion": STATE_SCHEMA, "consumers": {}}


def load_state(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return empty_state()
    raw = load_json_file(path, MAX_STATE_BYTES)
    if not isinstance(raw, dict) or raw.get("schemaVersion") != STATE_SCHEMA:
        raise TrainingError(
            "unsupported or corrupt training state; rebaseline explicitly: %s" % path
        )
    if not isinstance(raw.get("consumers"), dict):
        raise TrainingError("invalid consumers map in training state: %s" % path)
    return raw


def consumer_projects(state: Dict[str, Any], consumer: str) -> Dict[str, Any]:
    consumers = state.setdefault("consumers", {})
    consumer_state = consumers.setdefault(consumer, {"projects": {}})
    projects = consumer_state.setdefault("projects", {})
    if not isinstance(projects, dict):
        raise TrainingError("invalid project cursor map for consumer %s" % consumer)
    return projects


def strip_control_chars(text: str) -> str:
    text = re.sub(r"\x1b\[[0-?]*[ -/]*[@-~]", "", text)
    return "".join(
        char
        for char in text
        if char in "\n\t" or ord(char) >= 32
    )


def redact_secrets(text: str) -> Tuple[str, List[str]]:
    detectors: List[str] = []
    clean = strip_control_chars(text)
    for label, pattern in SECRET_PATTERNS:
        if pattern.search(clean):
            detectors.append(label)
            clean = pattern.sub("[REDACTED:%s]" % label, clean)
    return clean, sorted(set(detectors))


def truncate_text(text: str, limit: int) -> Tuple[str, bool]:
    if len(text) <= limit:
        return text, False
    return text[:limit] + "\n[TRUNCATED]\n", True


def remove_html_comments(text: str) -> str:
    return re.sub(r"<!--[\s\S]*?-->", "", text)


def canonical_block(text: str) -> str:
    normalized = text.replace("\r\n", "\n").replace("\r", "\n").lstrip("\ufeff")
    normalized = remove_html_comments(normalized)
    lines = [line.rstrip() for line in normalized.split("\n")]
    while lines and not lines[0].strip():
        lines.pop(0)
    while lines and not lines[-1].strip():
        lines.pop()
    compact: List[str] = []
    blank = False
    for line in lines:
        if not line.strip():
            if not blank:
                compact.append("")
            blank = True
        else:
            compact.append(line)
            blank = False
    return ("\n".join(compact) + "\n") if compact else ""


def visible_structure_lines(lines: Sequence[str]) -> List[str]:
    visible: List[str] = []
    in_comment = False
    fence_char = ""
    fence_len = 0
    for raw in lines:
        line = raw
        if fence_char:
            close = re.match(r"^\s{0,3}(%s{%d,})\s*$" % (re.escape(fence_char), fence_len), line)
            visible.append("")
            if close:
                fence_char = ""
                fence_len = 0
            continue

        without_comments = ""
        cursor = 0
        while cursor < len(line):
            if in_comment:
                end = line.find("-->", cursor)
                if end < 0:
                    cursor = len(line)
                    break
                in_comment = False
                cursor = end + 3
            else:
                start = line.find("<!--", cursor)
                if start < 0:
                    without_comments += line[cursor:]
                    break
                without_comments += line[cursor:start]
                end = line.find("-->", start + 4)
                if end < 0:
                    in_comment = True
                    break
                cursor = end + 3

        fence = re.match(r"^\s{0,3}(`{3,}|~{3,})", without_comments)
        if fence:
            token = fence.group(1)
            fence_char = token[0]
            fence_len = len(token)
            visible.append("")
            continue
        visible.append(without_comments if not in_comment else "")
    return visible


def normalized_title(title: str) -> str:
    value = re.sub(r"\s*\(\d{4}-\d{2}-\d{2}\)\s*$", "", title.strip())
    value = re.sub(r"[`*_]+", "", value)
    return re.sub(r"\s+", " ", value).casefold()


def is_substantive(text: str) -> bool:
    plain = canonical_block(text)
    if not plain:
        return False
    lowered = plain.casefold()
    placeholders = (
        "append durable decisions",
        "promote approaches",
        "record repeated failure modes",
        "non-negotiable technical",
        "keep contradictory evidence",
        "to be confirmed during the first memory update",
        "patterns confirmed across 3+ sessions",
        "issues that have appeared in 2+ sessions",
        "architectural and strategic decisions with full rationale",
        "entries where new evidence contradicts an existing pattern",
        "no entries yet",
    )
    visible = re.sub(r"[\s*_`()>—-]+", " ", lowered).strip()
    if not visible:
        return False
    return not any(marker in lowered for marker in placeholders)


def make_block(
    section: str,
    kind: str,
    title: str,
    content_lines: Sequence[str],
    line_start: int,
    line_end: int,
    occurrence: int,
) -> Optional[Dict[str, Any]]:
    content = canonical_block("\n".join(content_lines))
    if not is_substantive(content):
        return None
    safe_section, _ = redact_secrets(section)
    safe_title, _ = redact_secrets(title.strip())
    identity = "%s\x00%s\x00%s" % (
        normalized_title(safe_section),
        kind,
        normalized_title(safe_title),
    )
    if occurrence > 1:
        identity += "\x00%d" % occurrence
    digest = sha256_text(
        "ltmt:block:v%d\x00%s\x00%s\x00%s"
        % (PARSER_VERSION, section, kind, content)
    )
    return {
        "key": sha256_text("ltmt:key:v1\x00" + identity),
        "hash": digest,
        "section": safe_section[:240],
        "kind": kind,
        "title": safe_title[:240],
        "lineStart": line_start,
        "lineEnd": line_end,
        "trainable": section in TRAINABLE_SECTIONS,
    }


def parse_flat_blocks(
    section: str,
    raw_lines: Sequence[str],
    visible_lines: Sequence[str],
    base_line: int,
    occurrence_counts: Dict[str, int],
) -> List[Dict[str, Any]]:
    blocks: List[Dict[str, Any]] = []
    starts: List[int] = []
    list_re = re.compile(r"^\s{0,3}(?:[-+*]|\d+[.)])\s+")
    for index, line in enumerate(visible_lines):
        if list_re.match(line):
            starts.append(index)

    occupied = [False] * len(raw_lines)
    for position, start in enumerate(starts):
        end = starts[position + 1] if position + 1 < len(starts) else len(raw_lines)
        for index in range(start, end):
            occupied[index] = True
        first = re.sub(r"^\s{0,3}(?:[-+*]|\d+[.)])\s+", "", visible_lines[start]).strip()
        title = re.sub(r"[`*_]+", "", first)[:160] or "%s item" % section
        identity = "%s|list|%s" % (section, normalized_title(title))
        occurrence_counts[identity] = occurrence_counts.get(identity, 0) + 1
        block = make_block(
            section,
            "list",
            title,
            raw_lines[start:end],
            base_line + start,
            base_line + end - 1,
            occurrence_counts[identity],
        )
        if block:
            blocks.append(block)

    paragraph_start: Optional[int] = None
    for index in range(len(raw_lines) + 1):
        is_boundary = (
            index == len(raw_lines)
            or occupied[index]
            or not visible_lines[index].strip()
        )
        if paragraph_start is not None and is_boundary:
            end = index
            paragraph = raw_lines[paragraph_start:end]
            title_source = next(
                (line.strip() for line in visible_lines[paragraph_start:end] if line.strip()),
                "%s paragraph" % section,
            )
            title = re.sub(r"[`*_#]+", "", title_source)[:160]
            identity = "%s|paragraph|%s" % (section, normalized_title(title))
            occurrence_counts[identity] = occurrence_counts.get(identity, 0) + 1
            block = make_block(
                section,
                "paragraph",
                title,
                paragraph,
                base_line + paragraph_start,
                base_line + end - 1,
                occurrence_counts[identity],
            )
            if block:
                blocks.append(block)
            paragraph_start = None
        if index < len(raw_lines) and not is_boundary and paragraph_start is None:
            paragraph_start = index
    return blocks


def parse_memory_blocks(text: str) -> Dict[str, Any]:
    normalized = text.replace("\r\n", "\n").replace("\r", "\n").lstrip("\ufeff")
    lines = normalized.split("\n")
    visible = visible_structure_lines(lines)
    h2_re = re.compile(r"^##\s+(.+?)\s*$")
    h3_re = re.compile(r"^###\s+(.+?)\s*$")
    h2_indices = [index for index, line in enumerate(visible) if h2_re.match(line)]
    warnings: List[str] = []
    if not h2_indices:
        return {
            "valid": False,
            "warnings": ["memory has no H2 sections"],
            "blocks": [],
            "documentHash": sha256_text(normalized),
        }

    blocks: List[Dict[str, Any]] = []
    occurrence_counts: Dict[str, int] = {}
    for section_position, h2_index in enumerate(h2_indices):
        section_end = (
            h2_indices[section_position + 1]
            if section_position + 1 < len(h2_indices)
            else len(lines)
        )
        section_match = h2_re.match(visible[h2_index])
        if not section_match:
            continue
        section = section_match.group(1).strip()
        h3_indices = [
            index
            for index in range(h2_index + 1, section_end)
            if h3_re.match(visible[index])
        ]
        prefix_end = h3_indices[0] if h3_indices else section_end
        if prefix_end > h2_index + 1:
            blocks.extend(
                parse_flat_blocks(
                    section,
                    lines[h2_index + 1 : prefix_end],
                    visible[h2_index + 1 : prefix_end],
                    h2_index + 2,
                    occurrence_counts,
                )
            )
        for position, h3_index in enumerate(h3_indices):
            end = (
                h3_indices[position + 1]
                if position + 1 < len(h3_indices)
                else section_end
            )
            match = h3_re.match(visible[h3_index])
            if not match:
                continue
            title = match.group(1).strip()
            identity = "%s|heading|%s" % (section, normalized_title(title))
            occurrence_counts[identity] = occurrence_counts.get(identity, 0) + 1
            block = make_block(
                section,
                "heading",
                title,
                lines[h3_index:end],
                h3_index + 1,
                end,
                occurrence_counts[identity],
            )
            if block:
                blocks.append(block)

    blocks.sort(key=lambda item: (item["lineStart"], item["key"]))
    if not blocks:
        warnings.append("memory contains no substantive blocks")
    return {
        "valid": True,
        "warnings": warnings,
        "blocks": blocks,
        "documentHash": sha256_text(normalized),
    }


def memory_delta(
    previous: Optional[Dict[str, Any]],
    current_blocks: Sequence[Dict[str, Any]],
) -> Dict[str, Any]:
    previous_blocks = previous.get("blocks", []) if previous else []
    previous_by_key = {
        block.get("key"): block
        for block in previous_blocks
        if isinstance(block, dict) and block.get("key")
    }
    current_by_key = {block["key"]: block for block in current_blocks}
    added: List[Dict[str, Any]] = []
    updated: List[Dict[str, Any]] = []
    removed: List[Dict[str, Any]] = []
    for key, block in current_by_key.items():
        old = previous_by_key.get(key)
        if old is None:
            if block.get("trainable"):
                added.append(block)
        elif old.get("hash") != block.get("hash"):
            if block.get("trainable"):
                updated.append(block)
    for key, old in previous_by_key.items():
        if key not in current_by_key and old.get("trainable"):
            removed.append(
                {
                    "key": key,
                    "hash": old.get("hash"),
                    "section": old.get("section"),
                    "kind": old.get("kind"),
                    "title": old.get("title"),
                }
            )
    return {
        "added": added,
        "updated": updated,
        "removed": removed,
        "candidateCount": len(added) + len(updated),
    }


def normalize_relative_path(value: str) -> str:
    normalized = value.replace("\\", "/")
    while normalized.startswith("./"):
        normalized = normalized[2:]
    return normalized.lstrip("/")


def path_is_ignored(relative_path: str, source_path: str) -> bool:
    normalized = normalize_relative_path(relative_path).rstrip("/")
    if not normalized:
        return True
    parts = normalized.split("/")
    if any(part in IGNORED_DIRS for part in parts):
        return True
    if normalized == normalize_relative_path(source_path).rstrip("/"):
        return True
    if any(normalized.startswith(prefix) for prefix in IGNORED_EXACT_PREFIXES):
        return True
    name = parts[-1].casefold()
    if name in SENSITIVE_FILENAMES or name.startswith(".env."):
        return True
    return False


def run_process(
    command: Sequence[str],
    cwd: Path,
    max_bytes: int = 8 * 1024 * 1024,
) -> Tuple[int, bytes, bytes]:
    try:
        completed = subprocess.run(
            list(command),
            cwd=str(cwd),
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=30,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return 127, b"", str(exc).encode("utf-8", "replace")
    stdout = completed.stdout[:max_bytes]
    stderr = completed.stderr[:1024 * 1024]
    return completed.returncode, stdout, stderr


def run_git_checked(
    cwd: Path,
    args: Sequence[str],
    max_bytes: int = 32 * 1024 * 1024,
) -> bytes:
    """Run a Git query while hard-capping both output pipes as they stream."""
    result = _run_bounded_process(
        ["git", *args],
        cwd,
        stdout_limit=max_bytes,
        stderr_limit=MAX_GIT_STDERR_BYTES,
        digest_stdout=False,
    )
    if result["returncode"] != 0:
        stderr = strip_control_chars(
            result["stderr"].decode("utf-8", "replace")
        ).strip()
        raise TrainingError(
            "git command failed (%d): git %s%s"
            % (
                result["returncode"],
                " ".join(args),
                (": " + stderr) if stderr else "",
            )
        )
    return result["stdout"]


def _run_bounded_process(
    command: Sequence[str],
    cwd: Path,
    *,
    stdout_limit: int,
    stderr_limit: int,
    digest_stdout: bool,
) -> Dict[str, Any]:
    """Drain two process pipes concurrently and kill on the first hard overflow."""
    if stdout_limit < 0 or stderr_limit < 0:
        raise TrainingError("process output limits must be non-negative")
    try:
        process = subprocess.Popen(
            list(command),
            cwd=str(cwd),
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            bufsize=0,
        )
    except OSError as exc:
        raise TrainingError(
            "process could not start: %s: %s" % (" ".join(command), exc)
        ) from exc

    if process.stdout is None or process.stderr is None:
        try:
            process.kill()
        except OSError:
            pass
        process.wait()
        raise TrainingError("process pipes were not created")

    results: Dict[str, Dict[str, Any]] = {}
    issues: List[Tuple[str, str]] = []
    issue_lock = threading.Lock()
    overflow = threading.Event()

    def record_issue(kind: str, detail: str) -> None:
        with issue_lock:
            if not issues:
                issues.append((kind, detail))
        overflow.set()
        try:
            process.kill()
        except OSError:
            pass

    def drain(
        name: str,
        stream: Any,
        hard_limit: int,
        *,
        keep_limit: int,
        hash_stream: bool,
    ) -> None:
        total = 0
        captured = bytearray()
        digest = hashlib.sha256() if hash_stream else None
        exceeded = False
        try:
            while True:
                chunk = stream.read(64 * 1024)
                if not chunk:
                    break
                previous_total = total
                total += len(chunk)
                if total > hard_limit:
                    if not exceeded:
                        exceeded = True
                        record_issue(
                            "overflow",
                            "%s output exceeds %d-byte safety limit"
                            % (name, hard_limit),
                        )
                    # Continue draining and discarding until EOF so teardown
                    # cannot deadlock on a pipe still held by the child.
                    continue
                if hash_stream:
                    assert digest is not None
                    digest.update(chunk)
                elif previous_total < keep_limit:
                    captured.extend(chunk[: keep_limit - previous_total])
        except OSError as exc:
            record_issue("read-error", "%s pipe read failed: %s" % (name, exc))
        finally:
            try:
                stream.close()
            except OSError:
                pass
            results[name] = {
                "total": total,
                "data": bytes(captured),
                "digest": digest.hexdigest() if digest is not None else None,
            }

    stdout_thread = threading.Thread(
        target=drain,
        args=("stdout", process.stdout, stdout_limit),
        kwargs={
            "keep_limit": 0 if digest_stdout else stdout_limit,
            "hash_stream": digest_stdout,
        },
        daemon=True,
    )
    stderr_thread = threading.Thread(
        target=drain,
        args=("stderr", process.stderr, stderr_limit),
        kwargs={"keep_limit": min(stderr_limit, 4096), "hash_stream": False},
        daemon=True,
    )
    stdout_thread.start()
    stderr_thread.start()

    timed_out = False
    try:
        process.wait(timeout=GIT_TIMEOUT_SECONDS)
    except subprocess.TimeoutExpired:
        timed_out = True
        try:
            process.kill()
        except OSError:
            pass
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired as exc:
            raise TrainingError(
                "process could not be terminated after timeout: %s"
                % " ".join(command)
            ) from exc

    stdout_thread.join(timeout=5)
    stderr_thread.join(timeout=5)
    if stdout_thread.is_alive() or stderr_thread.is_alive():
        raise TrainingError(
            "process output drain did not finish safely: %s" % " ".join(command)
        )
    if issues:
        raise TrainingError("%s: %s" % (issues[0][1], " ".join(command)))
    if timed_out:
        raise TrainingError("process timed out: %s" % " ".join(command))
    if "stdout" not in results or "stderr" not in results:
        raise TrainingError(
            "process output drain failed: %s" % " ".join(command)
        )
    return {
        "returncode": process.returncode,
        "stdout": results["stdout"]["data"],
        "stdoutDigest": results["stdout"]["digest"],
        "stdoutBytes": results["stdout"]["total"],
        "stderr": results["stderr"]["data"],
        "stderrBytes": results["stderr"]["total"],
    }


def git_digest_checked(
    cwd: Path,
    args: Sequence[str],
    max_bytes: Optional[int] = None,
) -> Tuple[str, int]:
    """Hash Git output incrementally while enforcing streaming pipe limits."""
    effective_limit = (
        MAX_GIT_DIGEST_BYTES if max_bytes is None else max_bytes
    )
    result = _run_bounded_process(
        ["git", *args],
        cwd,
        stdout_limit=effective_limit,
        stderr_limit=MAX_GIT_STDERR_BYTES,
        digest_stdout=True,
    )
    if result["returncode"] != 0:
        stderr = strip_control_chars(
            result["stderr"].decode("utf-8", "replace")
        ).strip()
        raise TrainingError(
            "git command failed (%d): git %s%s"
            % (
                result["returncode"],
                " ".join(args),
                (": " + stderr) if stderr else "",
            )
        )
    digest = result["stdoutDigest"]
    if not isinstance(digest, str):
        raise TrainingError("git digest output was not captured")
    return digest, result["stdoutBytes"]


def git_text_checked(
    cwd: Path,
    args: Sequence[str],
    max_bytes: int = 8 * 1024 * 1024,
) -> str:
    return run_git_checked(cwd, args, max_bytes=max_bytes).decode(
        "utf-8", "replace"
    ).strip()


def git_text(cwd: Path, args: Sequence[str], max_bytes: int = 8 * 1024 * 1024) -> str:
    code, stdout, _ = run_process(["git", *args], cwd, max_bytes=max_bytes)
    if code != 0:
        return ""
    return stdout.decode("utf-8", "replace").strip()


def git_bytes(cwd: Path, args: Sequence[str], max_bytes: int = 32 * 1024 * 1024) -> bytes:
    code, stdout, _ = run_process(["git", *args], cwd, max_bytes=max_bytes)
    return stdout if code == 0 else b""


def git_exclusions(source_path: str) -> List[str]:
    paths = [
        ".agent-memory",
        ".claude/skills/project-memory",
        ".claude/skills/project-session-end",
        ".claude/skills/remember-session",
        ".claude/skills/learn",
        ".agents/skills/project-memory",
        ".agents/skills/project-session-end",
        ".agents/skills/remember-session",
        ".agents/skills/learn",
        source_path.replace("\\", "/"),
    ]
    return [":(exclude,literal)%s" % path for path in paths if path]


def bounded_git_diff(
    root: Path,
    range_args: Sequence[str],
    source_path: str,
) -> Tuple[str, bool, List[str]]:
    args = [
        "diff",
        "--no-ext-diff",
        "--unified=1",
        "--relative",
        *range_args,
        "--",
        ".",
        *git_exclusions(source_path),
    ]
    raw = run_git_checked(root, args, max_bytes=32 * 1024 * 1024)
    text, detectors = redact_secrets(raw.decode("utf-8", "replace"))
    limited, truncated = truncate_text(text, MAX_DIFF_CHARS)
    return limited, truncated, detectors


def hash_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while True:
            chunk = handle.read(1024 * 1024)
            if not chunk:
                break
            digest.update(chunk)
    return digest.hexdigest()


def hash_file_bounded(path: Path, max_bytes: int) -> Tuple[str, int]:
    """Hash one file without hashing more than the caller's remaining budget."""
    digest = hashlib.sha256()
    total = 0
    with path.open("rb") as handle:
        before = os.fstat(handle.fileno())
        while True:
            allowed = max_bytes - total
            chunk = handle.read(min(1024 * 1024, allowed + 1))
            if not chunk:
                break
            if len(chunk) > allowed:
                raise TrainingError(
                    "file grew beyond the remaining hash budget: %s" % path
                )
            digest.update(chunk)
            total += len(chunk)
        after = os.fstat(handle.fileno())
    signature_before = (
        before.st_dev,
        before.st_ino,
        before.st_size,
        before.st_mtime_ns,
    )
    signature_after = (
        after.st_dev,
        after.st_ino,
        after.st_size,
        after.st_mtime_ns,
    )
    if signature_before != signature_after:
        raise TrainingError("file changed while being hashed: %s" % path)
    return digest.hexdigest(), total


def fingerprint_regular_file(
    path: Path,
    expected_stat: os.stat_result,
    max_bytes: int,
    excerpt_path: Path,
) -> Tuple[str, int, str, List[str]]:
    """Hash and sanitize an excerpt through one verified file descriptor.

    The caller may have reached ``path`` through a symlink.  Opening it only once,
    refusing a final-component symlink, and comparing the descriptor identity with
    the already validated target prevents a later alias swap from redirecting the
    excerpt read to a sensitive file.
    """
    flags = os.O_RDONLY
    if hasattr(os, "O_CLOEXEC"):
        flags |= os.O_CLOEXEC
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    fd = os.open(str(path), flags)
    digest = hashlib.sha256()
    total = 0
    prefix = bytearray()
    try:
        with os.fdopen(fd, "rb") as handle:
            before = os.fstat(handle.fileno())
            expected_identity = (
                expected_stat.st_dev,
                expected_stat.st_ino,
                expected_stat.st_size,
                expected_stat.st_mtime_ns,
            )
            opened_identity = (
                before.st_dev,
                before.st_ino,
                before.st_size,
                before.st_mtime_ns,
            )
            if not stat.S_ISREG(before.st_mode):
                raise TrainingError("regular file required: %s" % path)
            if opened_identity != expected_identity:
                raise TrainingError(
                    "file identity changed before it could be fingerprinted: %s"
                    % path
                )
            while True:
                allowed = max_bytes - total
                chunk = handle.read(min(1024 * 1024, allowed + 1))
                if not chunk:
                    break
                if len(chunk) > allowed:
                    raise TrainingError(
                        "file grew beyond the remaining hash budget: %s" % path
                    )
                digest.update(chunk)
                total += len(chunk)
                if len(prefix) < MAX_TEXT_EXCERPT_BYTES:
                    prefix.extend(
                        chunk[: MAX_TEXT_EXCERPT_BYTES - len(prefix)]
                    )
            after = os.fstat(handle.fileno())
    except BaseException:
        # os.fdopen owns the descriptor after construction, but close it if that
        # construction itself ever fails.
        try:
            os.close(fd)
        except OSError:
            pass
        raise
    signature_before = (
        before.st_dev,
        before.st_ino,
        before.st_size,
        before.st_mtime_ns,
    )
    signature_after = (
        after.st_dev,
        after.st_ino,
        after.st_size,
        after.st_mtime_ns,
    )
    if signature_before != signature_after:
        raise TrainingError("file changed while being fingerprinted: %s" % path)

    excerpt_name = excerpt_path.name.casefold()
    if excerpt_name in SENSITIVE_FILENAMES or excerpt_name.startswith(".env."):
        excerpt, detectors = "", ["sensitive-filename"]
    elif excerpt_path.suffix.casefold() not in TEXT_EXTENSIONS:
        excerpt, detectors = "", []
    else:
        excerpt, detectors = redact_secrets(
            bytes(prefix).decode("utf-8", "replace")
        )
    return digest.hexdigest(), total, excerpt, detectors


def safe_text_excerpt(path: Path) -> Tuple[str, List[str]]:
    if path.name.casefold() in SENSITIVE_FILENAMES or path.name.casefold().startswith(".env."):
        return "", ["sensitive-filename"]
    if path.suffix.casefold() not in TEXT_EXTENSIONS:
        return "", []
    try:
        data = stable_read_prefix(path, MAX_TEXT_EXCERPT_BYTES)
    except (OSError, TrainingError):
        return "", []
    text = data.decode("utf-8", "replace")
    return redact_secrets(text)


def git_empty_tree(root: Path) -> str:
    value = git_text_checked(
        root,
        ["hash-object", "-t", "tree", "--stdin"],
        max_bytes=4096,
    )
    if not re.fullmatch(r"[0-9a-fA-F]{40,64}", value):
        raise TrainingError("git returned an invalid empty-tree object id")
    return value


def git_bootstrap_base(root: Path) -> Tuple[Optional[str], bool, int, bool]:
    recent_heads = git_text_checked(
        root,
        ["log", "--max-count=12", "--format=%H"],
        max_bytes=64 * 1024,
    ).splitlines()
    if not recent_heads:
        return None, False, 0, False
    total_commits_text = git_text_checked(
        root,
        ["rev-list", "--count", "HEAD"],
        max_bytes=4096,
    )
    total_commits = int(total_commits_text)
    oldest = recent_heads[-1]
    parent_code, parent_stdout, _ = run_process(
        ["git", "rev-parse", "%s^" % oldest],
        root,
        max_bytes=4096,
    )
    oldest_parent = (
        parent_stdout.decode("utf-8", "replace").strip()
        if parent_code == 0
        else ""
    )
    if oldest_parent:
        return (
            oldest_parent,
            total_commits > len(recent_heads),
            total_commits,
            False,
        )
    # A root commit has no commit parent. Compare it to Git's native empty
    # tree so the initial tracked project contents are reviewable evidence.
    return (
        git_empty_tree(root),
        total_commits > len(recent_heads),
        total_commits,
        True,
    )


def parse_git_worktree_porcelain(raw: bytes) -> List[Dict[str, Any]]:
    records: List[Dict[str, Any]] = []
    current: Dict[str, Any] = {}
    for field in raw.split(b"\0"):
        if not field:
            if current:
                if "worktree" not in current:
                    raise TrainingError("git worktree record has no root")
                records.append(current)
                current = {}
            continue
        key_bytes, separator, value_bytes = field.partition(b" ")
        try:
            key = key_bytes.decode("ascii")
            value = value_bytes.decode("utf-8") if separator else True
        except UnicodeDecodeError as exc:
            raise TrainingError(
                "git worktree list contains a non-UTF-8 field"
            ) from exc
        if key in current:
            raise TrainingError("git worktree record repeats field: %s" % key)
        current[key] = value
    if current:
        if "worktree" not in current:
            raise TrainingError("git worktree record has no root")
        records.append(current)
    return records


def resolved_git_path(root: Path, args: Sequence[str]) -> Path:
    value = git_text_checked(root, args, max_bytes=16 * 1024)
    if not value or "\0" in value or strip_control_chars(value) != value:
        raise TrainingError("git returned an unsafe path: git %s" % " ".join(args))
    candidate = Path(value)
    if not candidate.is_absolute():
        candidate = root / candidate
    try:
        return candidate.resolve(strict=True)
    except OSError as exc:
        raise TrainingError(
            "git path is inaccessible: %s" % candidate
        ) from exc


def registered_git_worktrees(root: Path) -> List[Dict[str, str]]:
    """Return verified non-bare worktrees registered in the same Git common dir."""
    root = root.resolve(strict=True)
    raw = run_git_checked(
        root,
        ["worktree", "list", "--porcelain", "-z"],
        max_bytes=4 * 1024 * 1024,
    )
    parsed = parse_git_worktree_porcelain(raw)
    non_bare = [record for record in parsed if record.get("bare") is not True]
    if len(non_bare) > MAX_LINKED_WORKTREES + 1:
        raise TrainingError(
            "Git repository has %d linked worktrees; safety limit is %d"
            % (len(non_bare) - 1, MAX_LINKED_WORKTREES)
        )

    common_dir = resolved_git_path(root, ["rev-parse", "--git-common-dir"])
    verified: List[Dict[str, str]] = []
    seen: set[str] = set()
    found_root = False
    for record in non_bare:
        raw_path = record.get("worktree")
        if not isinstance(raw_path, str) or not raw_path or "\0" in raw_path:
            raise TrainingError("git worktree record has an invalid root")
        candidate = Path(raw_path)
        if not candidate.is_absolute():
            raise TrainingError(
                "registered linked worktree root is not absolute: %s" % raw_path
            )
        try:
            candidate_stat = candidate.lstat()
        except OSError as exc:
            raise TrainingError(
                "registered linked worktree root is inaccessible: %s" % candidate
            ) from exc
        if stat.S_ISLNK(candidate_stat.st_mode):
            raise TrainingError(
                "registered linked worktree root is a symlink: %s" % candidate
            )
        if not stat.S_ISDIR(candidate_stat.st_mode):
            raise TrainingError(
                "registered linked worktree root is not a directory: %s" % candidate
            )
        try:
            resolved = candidate.resolve(strict=True)
        except OSError as exc:
            raise TrainingError(
                "registered linked worktree root is inaccessible: %s" % candidate
            ) from exc
        resolved_text = str(resolved)
        if resolved_text in seen:
            raise TrainingError(
                "git worktree list repeats root: %s" % resolved
            )
        seen.add(resolved_text)

        top_level = resolved_git_path(
            resolved,
            ["rev-parse", "--show-toplevel"],
        )
        if top_level != resolved:
            raise TrainingError(
                "registered linked worktree root does not match its Git top-level: %s"
                % resolved
            )
        linked_common_dir = resolved_git_path(
            resolved,
            ["rev-parse", "--git-common-dir"],
        )
        if linked_common_dir != common_dir:
            raise TrainingError(
                "registered linked worktree has a different Git common dir: %s"
                % resolved
            )

        advertised_head = record.get("HEAD")
        if not isinstance(advertised_head, str) or not re.fullmatch(
            r"[0-9a-fA-F]{40,64}", advertised_head
        ):
            raise TrainingError(
                "registered linked worktree has an invalid HEAD: %s" % resolved
            )
        head = git_text_checked(resolved, ["rev-parse", "HEAD"], max_bytes=4096)
        if head != advertised_head:
            raise TrainingError(
                "registered linked worktree HEAD changed during discovery: %s"
                % resolved
            )
        actual_branch = git_text_checked(
            resolved,
            ["branch", "--show-current"],
            max_bytes=4096,
        )
        branch = actual_branch or "detached"
        if strip_control_chars(branch) != branch:
            raise TrainingError(
                "registered linked worktree has an unsafe branch name: %s"
                % resolved
            )
        advertised_branch = record.get("branch")
        if isinstance(advertised_branch, str):
            if (
                not actual_branch
                or advertised_branch != "refs/heads/%s" % actual_branch
            ):
                raise TrainingError(
                    "registered linked worktree branch state is inconsistent: %s"
                    % resolved
                )
        elif actual_branch or record.get("detached") is not True:
            raise TrainingError(
                "registered linked worktree branch changed during discovery: %s"
                % resolved
            )

        if resolved == root:
            found_root = True
        verified.append(
            {
                "root": resolved_text,
                "head": head,
                "branch": branch,
            }
        )
    if not found_root:
        raise TrainingError(
            "current project root is missing from git worktree list: %s" % root
        )
    return sorted(verified, key=lambda item: item["root"])


def linked_paths_within(
    root: Path,
    worktrees: Sequence[Dict[str, str]],
) -> List[str]:
    nested: List[str] = []
    for item in worktrees:
        linked = Path(item["root"])
        if linked == root:
            continue
        try:
            relative = linked.relative_to(root).as_posix()
        except ValueError:
            continue
        normalized = normalize_relative_path(relative).rstrip("/")
        if normalized:
            nested.append(normalized)
    return sorted(set(nested))


def git_dirty_fingerprint(root: Path, source_path: str) -> Tuple[str, int]:
    return git_digest_checked(
        root,
        [
            "diff",
            "--no-ext-diff",
            "--binary",
            "--relative",
            "HEAD",
            "--",
            ".",
            *git_exclusions(source_path),
        ],
    )


def git_untracked_snapshot(
    root: Path,
    source_path: str,
    registered_nested_roots: Sequence[str],
) -> Dict[str, Any]:
    raw = run_git_checked(
        root,
        ["ls-files", "--others", "--exclude-standard", "-z"],
        max_bytes=128 * 1024 * 1024,
    )
    try:
        paths = sorted(
            {
                item.decode("utf-8")
                for item in raw.split(b"\0")
                if item
            }
        )
    except UnicodeDecodeError as exc:
        raise TrainingError("git returned a non-UTF-8 untracked path") from exc

    nested_roots = {
        normalize_relative_path(value).rstrip("/")
        for value in registered_nested_roots
        if normalize_relative_path(value).rstrip("/")
    }
    detectors: List[str] = []
    eligible_paths: List[Tuple[str, str]] = []
    for raw_relative in paths:
        relative = normalize_relative_path(raw_relative).rstrip("/")
        safe_relative, path_detectors = redact_secrets(relative)
        detectors.extend(path_detectors)
        relative_value = Path(relative)
        if (
            not relative
            or relative_value.is_absolute()
            or ".." in relative_value.parts
        ):
            raise TrainingError("git returned an unsafe untracked path")
        if path_is_ignored(relative, source_path):
            continue
        if any(
            relative == nested
            or relative.startswith(nested + "/")
            for nested in nested_roots
        ):
            # This directory is fingerprinted as a registered linked worktree
            # below. Never walk it as an arbitrary untracked directory.
            continue
        eligible_paths.append((relative, safe_relative))

    total_files = len(eligible_paths)
    omitted_files = max(0, total_files - MAX_GIT_UNTRACKED_FILES)
    selected_paths = eligible_paths[:MAX_GIT_UNTRACKED_FILES]
    root_resolved = root.resolve(strict=True)
    manifest: List[Dict[str, Any]] = []
    context: List[str] = []
    incomplete_reasons: List[str] = []
    if omitted_files:
        incomplete_reasons.append(
            "Git untracked file count exceeded the %d-file safety limit; "
            "%d path(s) were omitted"
            % (MAX_GIT_UNTRACKED_FILES, omitted_files)
        )
    context_chars = 0
    total_hashed = 0
    budget_skipped = 0
    for relative, safe_relative in selected_paths:

        file_path = root / relative
        try:
            file_stat = file_path.lstat()
            if stat.S_ISLNK(file_stat.st_mode):
                target = os.readlink(file_path)
                manifest.append(
                    {
                        "path": relative,
                        "type": "symlink",
                        "hash": sha256_bytes(os.fsencode(target)),
                        "size": file_stat.st_size,
                    }
                )
                continue
            if not stat.S_ISREG(file_stat.st_mode):
                kind = (
                    "directory"
                    if stat.S_ISDIR(file_stat.st_mode)
                    else "special"
                )
                manifest.append({"path": relative, "type": kind})
                incomplete_reasons.append(
                    "unregistered untracked %s was not traversed: %s"
                    % (kind, safe_relative)
                )
                continue
            resolved = file_path.resolve(strict=True)
            if not path_is_within(resolved, root_resolved):
                manifest.append({"path": relative, "type": "unsafe"})
                incomplete_reasons.append(
                    "untracked path escapes worktree and was not followed: %s"
                    % safe_relative
                )
                continue
            remaining_hash_bytes = MAX_GIT_UNTRACKED_HASH_BYTES - total_hashed
            if file_stat.st_size > remaining_hash_bytes:
                manifest.append(
                    {
                        "path": relative,
                        "type": "hash-budget-exceeded",
                        "size": file_stat.st_size,
                    }
                )
                budget_skipped += 1
                continue
            file_hash, hashed_bytes = hash_file_bounded(
                resolved,
                remaining_hash_bytes,
            )
            total_hashed += hashed_bytes
            manifest.append(
                {
                    "path": relative,
                    "hash": file_hash,
                    "size": file_stat.st_size,
                }
            )
            if context_chars < MAX_UNTRACKED_CHARS:
                excerpt, found = safe_text_excerpt(resolved)
                detectors.extend(found)
                if excerpt:
                    available = MAX_UNTRACKED_CHARS - context_chars
                    piece = (
                        "FILE: %s\n%s\n" % (safe_relative, excerpt)
                    )[:available]
                    context.append(piece)
                    context_chars += len(piece)
        except (OSError, TrainingError):
            manifest.append({"path": relative, "type": "unreadable"})
            incomplete_reasons.append(
                "untracked path could not be fingerprinted: %s" % safe_relative
            )
    if budget_skipped:
        incomplete_reasons.append(
            "Git untracked content hash budget exceeded %d bytes; "
            "%d regular file(s) were not content-fingerprinted"
            % (MAX_GIT_UNTRACKED_HASH_BYTES, budget_skipped)
        )
    return {
        "hash": sha256_bytes(canonical_json(manifest)),
        "manifest": manifest,
        "totalFiles": total_files,
        "omittedFiles": omitted_files,
        "hashedBytes": total_hashed,
        "context": context,
        "secretDetectors": sorted(set(detectors)),
        "partial": bool(incomplete_reasons),
        "incompleteReasons": sorted(set(incomplete_reasons)),
    }


def git_index_flags_snapshot(root: Path, source_path: str) -> Dict[str, Any]:
    """Fingerprint tracked files whose index flags can hide working-tree edits."""
    raw = run_git_checked(
        root,
        [
            "ls-files",
            "-v",
            "-z",
            "--",
            ".",
            *git_exclusions(source_path),
        ],
        max_bytes=128 * 1024 * 1024,
    )
    flagged: List[Tuple[str, str]] = []
    for field in raw.split(b"\0"):
        if not field:
            continue
        tag_bytes, separator, path_bytes = field.partition(b" ")
        if not separator or len(tag_bytes) != 1:
            raise TrainingError("git returned an invalid index-flag record")
        try:
            tag = tag_bytes.decode("ascii")
            relative = path_bytes.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise TrainingError(
                "git returned a non-UTF-8 index-flag record"
            ) from exc
        if tag == "S" or tag.islower():
            flagged.append((relative, tag))

    flagged.sort()
    total_files = len(flagged)
    omitted_files = max(0, total_files - MAX_FLAGGED_INDEX_FILES)
    selected = flagged[:MAX_FLAGGED_INDEX_FILES]
    root_resolved = root.resolve(strict=True)
    manifest: List[Dict[str, Any]] = []
    evidence: List[Dict[str, Any]] = []
    incomplete_reasons: List[str] = []
    detectors: List[str] = []
    total_hashed = 0
    hash_budget_consumed = 0
    budget_skipped = 0
    if omitted_files:
        omitted_digest = hashlib.sha256()
        for relative, tag in flagged[MAX_FLAGGED_INDEX_FILES:]:
            omitted_digest.update(tag.encode("ascii"))
            omitted_digest.update(b"\0")
            omitted_digest.update(relative.encode("utf-8"))
            omitted_digest.update(b"\0")
        manifest.append(
            {
                "type": "file-count-limit",
                "omitted": omitted_files,
                "omittedPathsHash": omitted_digest.hexdigest(),
            }
        )
        incomplete_reasons.append(
            "flagged index file count exceeded the %d-file safety limit; "
            "%d path(s) were omitted"
            % (MAX_FLAGGED_INDEX_FILES, omitted_files)
        )

    for relative, tag in selected:
        safe_relative, found = redact_secrets(relative)
        detectors.extend(found)
        entry: Dict[str, Any] = {"path": relative, "flag": tag}
        try:
            path = root / relative
            path_stat = path.lstat()
            if stat.S_ISLNK(path_stat.st_mode):
                entry.update(
                    {
                        "type": "symlink",
                        "hash": sha256_bytes(os.fsencode(os.readlink(path))),
                        "size": path_stat.st_size,
                    }
                )
            elif stat.S_ISREG(path_stat.st_mode):
                resolved = path.resolve(strict=True)
                if not path_is_within(resolved, root_resolved):
                    raise TrainingError("flagged path escapes worktree")
                remaining_hash_bytes = (
                    MAX_FLAGGED_INDEX_HASH_BYTES - hash_budget_consumed
                )
                if (
                    remaining_hash_bytes <= 0
                    or path_stat.st_size > remaining_hash_bytes
                ):
                    entry.update(
                        {
                            "type": "hash-budget-exceeded",
                            "size": path_stat.st_size,
                        }
                    )
                    budget_skipped += 1
                else:
                    try:
                        file_hash, hashed_bytes = hash_file_bounded(
                            resolved,
                            remaining_hash_bytes,
                        )
                    except (OSError, TrainingError):
                        # A failed bounded read may have consumed the complete
                        # remaining budget before detecting growth or mutation.
                        # Conservatively exhaust it so later paths cannot turn
                        # repeated failures into unbounded hashing.
                        hash_budget_consumed = MAX_FLAGGED_INDEX_HASH_BYTES
                        raise
                    total_hashed += hashed_bytes
                    hash_budget_consumed += hashed_bytes
                    entry.update(
                        {
                            "type": "file",
                            "hash": file_hash,
                            "size": path_stat.st_size,
                        }
                    )
            else:
                entry["type"] = "non-regular"
                incomplete_reasons.append(
                    "flagged index path is non-regular: %s" % safe_relative
                )
        except FileNotFoundError:
            # Missing skip-worktree files are common in sparse checkouts. Their
            # absence is itself an exact, deterministic fingerprint.
            entry.update({"type": "missing", "present": False})
        except (OSError, TrainingError):
            entry["type"] = "unreadable"
            incomplete_reasons.append(
                "flagged index path could not be fingerprinted: %s"
                % safe_relative
            )
        manifest.append(entry)
        if len(evidence) < MAX_FLAGGED_INDEX_EVIDENCE:
            evidence.append(
                {
                    "path": safe_relative[:240],
                    "flag": tag,
                    "type": entry["type"],
                    "contentHash": entry.get("hash"),
                    "size": entry.get("size"),
                }
            )

    if budget_skipped:
        incomplete_reasons.append(
            "flagged index content hash budget exceeded %d bytes; "
            "%d regular file(s) were not content-fingerprinted"
            % (MAX_FLAGGED_INDEX_HASH_BYTES, budget_skipped)
        )
    evidence_truncated = len(selected) > len(evidence)
    if evidence_truncated:
        incomplete_reasons.append(
            "flagged index evidence exceeded the %d-entry display limit"
            % MAX_FLAGGED_INDEX_EVIDENCE
        )
    return {
        "hash": sha256_bytes(canonical_json(manifest)),
        "entries": evidence,
        "count": total_files,
        "manifestFiles": len(selected),
        "omittedFiles": omitted_files,
        "hashedBytes": total_hashed,
        "partial": bool(incomplete_reasons),
        "evidenceTruncated": evidence_truncated,
        "incompleteReasons": sorted(set(incomplete_reasons)),
        "secretDetectors": sorted(set(detectors)),
    }


def index_flags_changed(
    previous: Optional[Dict[str, Any]],
    current: Dict[str, Any],
) -> bool:
    previous_hash = previous.get("indexFlagsHash") if previous else None
    if isinstance(previous_hash, str):
        return previous_hash != current["hash"]
    # Compatibility for old cursors: an absent field is equivalent only when
    # no hiding index flags exist now. Flagged files require a fresh review.
    return bool(current["count"])


def git_history_window(
    root: Path,
    previous_head: Optional[str],
    head: str,
) -> Dict[str, Any]:
    history_mode = "bootstrap"
    base_head: Optional[str] = None
    common_merge_base: Optional[str] = None
    bootstrap_truncated = False
    bootstrap_total_commits: Optional[int] = None
    base_is_empty_tree = False

    if isinstance(previous_head, str) and previous_head:
        if previous_head == head:
            history_mode = "unchanged-head"
            base_head = previous_head
        else:
            ancestor_code, _, _ = run_process(
                ["git", "merge-base", "--is-ancestor", previous_head, head],
                root,
            )
            if ancestor_code == 0:
                history_mode = "incremental"
                base_head = previous_head
            elif ancestor_code == 1:
                merge_code, merge_stdout, merge_stderr = run_process(
                    ["git", "merge-base", previous_head, head],
                    root,
                    max_bytes=4096,
                )
                if merge_code == 0:
                    common_merge_base = (
                        merge_stdout.decode("utf-8", "replace").strip() or None
                    )
                elif merge_code not in (1,):
                    raise TrainingError(
                        "git merge-base failed (%d): %s"
                        % (
                            merge_code,
                            strip_control_chars(
                                merge_stderr.decode("utf-8", "replace")
                            ).strip(),
                        )
                    )
                history_mode = "history-rewritten"
                base_head = previous_head
            else:
                previous_code, _, previous_stderr = run_process(
                    ["git", "cat-file", "-e", "%s^{commit}" % previous_head],
                    root,
                    max_bytes=4096,
                )
                if previous_code in (1, 128):
                    history_mode = "previous-tree-missing"
                    (
                        base_head,
                        bootstrap_truncated,
                        bootstrap_total_commits,
                        base_is_empty_tree,
                    ) = git_bootstrap_base(root)
                else:
                    raise TrainingError(
                        "git ancestry check failed (%d) for %s..%s: %s"
                        % (
                            ancestor_code,
                            previous_head,
                            head,
                            strip_control_chars(
                                previous_stderr.decode("utf-8", "replace")
                            ).strip(),
                        )
                    )
    else:
        (
            base_head,
            bootstrap_truncated,
            bootstrap_total_commits,
            base_is_empty_tree,
        ) = git_bootstrap_base(root)

    return {
        "historyMode": history_mode,
        "historyComplete": (
            base_head is not None and history_mode != "previous-tree-missing"
        ),
        "baseHead": base_head,
        "baseIsEmptyTree": base_is_empty_tree,
        "commonMergeBase": common_merge_base,
        "bootstrapHistoryTruncated": bootstrap_truncated,
        "bootstrapTotalCommits": bootstrap_total_commits,
    }


def git_commit_evidence(
    root: Path,
    committed_range: Optional[str],
    head: str,
    base_is_empty_tree: bool,
) -> Tuple[str, List[str]]:
    if not committed_range:
        return "", []
    revision = head if base_is_empty_tree else committed_range
    commits = git_text_checked(
        root,
        [
            "log",
            "--date=iso-strict",
            "--format=%H%x09%ad%x09%s",
            revision,
        ],
        max_bytes=2 * 1024 * 1024,
    )
    commits, _ = truncate_text(commits, 12_000)
    commits, detectors = redact_secrets(commits)
    return commits, detectors


def linked_worktree_source(
    record: Dict[str, str],
    source_path: str,
    previous: Optional[Dict[str, Any]],
    registered_nested_roots: Sequence[str],
) -> Dict[str, Any]:
    root = Path(record["root"])
    head = git_text_checked(root, ["rev-parse", "HEAD"], max_bytes=4096)
    branch = git_text_checked(
        root,
        ["branch", "--show-current"],
        max_bytes=4096,
    ) or "detached"
    if head != record["head"] or branch != record["branch"]:
        raise TrainingError(
            "linked worktree changed during source scan: %s" % root
        )
    safe_branch, branch_detectors = redact_secrets(branch)
    dirty_hash, dirty_bytes = git_dirty_fingerprint(root, source_path)
    untracked = git_untracked_snapshot(
        root,
        source_path,
        registered_nested_roots,
    )
    previous = previous if isinstance(previous, dict) else None
    index_flags = git_index_flags_snapshot(root, source_path)
    flagged_changed = index_flags_changed(previous, index_flags)
    snapshot = {
        "root": str(root),
        "head": head,
        "branch": safe_branch,
        "branchHash": sha256_text(branch),
        "dirtyHash": dirty_hash,
        "dirtyBytes": dirty_bytes,
        "untrackedHash": untracked["hash"],
        "partial": bool(untracked["partial"] or index_flags["partial"]),
    }
    if index_flags["count"] or (
        previous and isinstance(previous.get("indexFlagsHash"), str)
    ):
        snapshot["indexFlagsHash"] = index_flags["hash"]
    previous_head = previous.get("head") if previous else None
    previous_dirty = previous.get("dirtyHash") if previous else None
    previous_untracked = previous.get("untrackedHash") if previous else None
    previous_branch_hash = previous.get("branchHash") if previous else None
    branch_changed = bool(
        previous
        and (
            (
                isinstance(previous_branch_hash, str)
                and previous_branch_hash != snapshot["branchHash"]
            )
            or (
                not isinstance(previous_branch_hash, str)
                and previous.get("branch") != safe_branch
            )
        )
    )
    history = git_history_window(root, previous_head, head)
    base_head = history["baseHead"]
    committed_range = (
        "%s..%s" % (base_head, head)
        if base_head and base_head != head
        else None
    )
    committed_diff = ""
    committed_truncated = False
    committed_detectors: List[str] = []
    if committed_range:
        (
            committed_diff,
            committed_truncated,
            committed_detectors,
        ) = bounded_git_diff(root, [base_head, head], source_path)

    dirty_diff = ""
    dirty_truncated = False
    dirty_detectors: List[str] = []
    if previous is None or previous_dirty != dirty_hash:
        dirty_diff, dirty_truncated, dirty_detectors = bounded_git_diff(
            root,
            ["HEAD"],
            source_path,
        )
    commits, commit_detectors = git_commit_evidence(
        root,
        committed_range,
        head,
        bool(history["baseIsEmptyTree"]),
    )
    committed_detectors.extend(commit_detectors)
    has_changes = bool(
        previous is None
        or previous.get("root") != snapshot["root"]
        or previous_head != head
        or branch_changed
        or previous_dirty != dirty_hash
        or previous_untracked != untracked["hash"]
        or flagged_changed
        or untracked["partial"]
        or index_flags["partial"]
    )
    return {
        "snapshot": snapshot,
        "root": str(root),
        "head": head,
        "branch": safe_branch,
        "previousBranch": previous.get("branch") if previous else None,
        "hasChanges": has_changes,
        **history,
        "blockingReason": (
            "linked Git history could not be compared with the previous cursor"
            if not history["historyComplete"]
            else None
        ),
        "committedRange": committed_range,
        "commits": commits,
        "committedDiff": committed_diff,
        "dirtyDiff": dirty_diff,
        "untracked": (
            untracked["context"]
            if previous is None or previous_untracked != untracked["hash"]
            else []
        ),
        "indexFlagged": index_flags["entries"] if flagged_changed else [],
        "truncated": bool(
            committed_truncated
            or dirty_truncated
            or history["bootstrapHistoryTruncated"]
            or untracked["partial"]
            or index_flags["evidenceTruncated"]
            or index_flags["partial"]
        ),
        "incompleteReasons": sorted(
            set(
                untracked["incompleteReasons"]
                + index_flags["incompleteReasons"]
            )
        ),
        "secretDetectors": sorted(
            set(
                committed_detectors
                + dirty_detectors
                + untracked["secretDetectors"]
                + index_flags["secretDetectors"]
                + branch_detectors
            )
        ),
        "counts": {
            "untrackedFiles": untracked["totalFiles"],
            "untrackedManifestFiles": len(untracked["manifest"]),
            "untrackedOmittedFiles": untracked["omittedFiles"],
            "untrackedHashedBytes": untracked["hashedBytes"],
            "indexFlaggedFiles": index_flags["count"],
            "indexFlaggedManifestFiles": index_flags["manifestFiles"],
            "indexFlaggedOmittedFiles": index_flags["omittedFiles"],
            "indexFlaggedHashedBytes": index_flags["hashedBytes"],
        },
    }


def trim_linked_evidence(
    evidence: Dict[str, Any],
    remaining: int,
) -> int:
    """Bound all linked-worktree source text across the complete scan."""
    truncated = False
    for field in ("committedDiff", "dirtyDiff"):
        value = evidence.get(field)
        if not isinstance(value, str) or not value:
            continue
        if remaining <= 0:
            evidence[field] = ""
            truncated = True
            continue
        if len(value) > remaining:
            evidence[field] = value[:remaining]
            remaining = 0
            truncated = True
        else:
            remaining -= len(value)

    bounded_untracked: List[str] = []
    raw_untracked = evidence.get("untracked")
    if isinstance(raw_untracked, list):
        for value in raw_untracked:
            if not isinstance(value, str) or not value:
                continue
            if remaining <= 0:
                truncated = True
                continue
            if len(value) > remaining:
                bounded_untracked.append(value[:remaining])
                remaining = 0
                truncated = True
            else:
                bounded_untracked.append(value)
                remaining -= len(value)
    evidence["untracked"] = bounded_untracked

    commits = evidence.get("commits")
    if isinstance(commits, str) and commits:
        if remaining <= 0:
            evidence["commits"] = ""
            truncated = True
        elif len(commits) > remaining:
            evidence["commits"] = commits[:remaining]
            remaining = 0
            truncated = True
        else:
            remaining -= len(commits)
    if truncated:
        evidence["truncated"] = True
        reasons = evidence.setdefault("incompleteReasons", [])
        reasons.append("linked worktree evidence exceeded the shared text budget")
        evidence["incompleteReasons"] = sorted(set(reasons))
    return remaining


def git_source_snapshot(
    root: Path,
    source_path: str,
    previous: Optional[Dict[str, Any]],
) -> Dict[str, Any]:
    root = root.resolve(strict=True)
    worktrees_before = registered_git_worktrees(root)
    current_records = [
        item for item in worktrees_before if item["root"] == str(root)
    ]
    if len(current_records) != 1:
        raise TrainingError(
            "git worktree list must contain the project root exactly once"
        )
    current_record = current_records[0]
    head = git_text_checked(root, ["rev-parse", "HEAD"], max_bytes=4096)
    branch = git_text_checked(
        root, ["branch", "--show-current"], max_bytes=4096
    ) or "detached"
    if head != current_record["head"] or branch != current_record["branch"]:
        raise TrainingError("project worktree changed during source discovery")
    safe_branch, branch_detectors = redact_secrets(branch)

    linked_records = [
        item for item in worktrees_before if item["root"] != str(root)
    ]
    nested_roots = linked_paths_within(root, worktrees_before)
    dirty_hash, dirty_bytes = git_dirty_fingerprint(root, source_path)
    untracked = git_untracked_snapshot(
        root,
        source_path,
        nested_roots,
    )

    previous_source = previous.get("source", {}) if previous else {}
    if not isinstance(previous_source, dict):
        raise TrainingError("previous Git source cursor is invalid")
    index_flags = git_index_flags_snapshot(root, source_path)
    flagged_changed = index_flags_changed(previous_source, index_flags)
    previous_head = previous_source.get("head")
    previous_dirty = previous_source.get("dirtyHash")
    previous_untracked = previous_source.get("untrackedHash")
    previous_branch_hash = previous_source.get("branchHash")
    branch_changed = bool(
        previous
        and (
            (
                isinstance(previous_branch_hash, str)
                and previous_branch_hash != sha256_text(branch)
            )
            or (
                not isinstance(previous_branch_hash, str)
                and previous_source.get("branch") != safe_branch
            )
        )
    )
    history = git_history_window(root, previous_head, head)
    base_head = history["baseHead"]

    committed_diff = ""
    committed_truncated = False
    committed_detectors: List[str] = []
    committed_range: Optional[str] = None
    if base_head and base_head != head:
        committed_range = "%s..%s" % (base_head, head)
        committed_diff, committed_truncated, committed_detectors = bounded_git_diff(
            root,
            [base_head, head],
            source_path,
        )

    dirty_diff = ""
    dirty_truncated = False
    dirty_detectors: List[str] = []
    if previous is None or previous_dirty != dirty_hash:
        dirty_diff, dirty_truncated, dirty_detectors = bounded_git_diff(
            root,
            ["HEAD"],
            source_path,
        )

    include_untracked = previous is None or previous_untracked != untracked["hash"]
    commits, commit_detectors = git_commit_evidence(
        root,
        committed_range,
        head,
        bool(history["baseIsEmptyTree"]),
    )
    committed_detectors.extend(commit_detectors)

    previous_linked_raw = previous_source.get("linkedWorktrees", [])
    if previous_linked_raw is None:
        previous_linked_raw = []
    if not isinstance(previous_linked_raw, list):
        raise TrainingError("previous linked worktree cursor is invalid")
    previous_linked: Dict[str, Dict[str, Any]] = {}
    for item in previous_linked_raw:
        if not isinstance(item, dict):
            raise TrainingError("previous linked worktree cursor is invalid")
        item_root = item.get("root")
        if not isinstance(item_root, str) or not item_root:
            raise TrainingError("previous linked worktree cursor has no root")
        if item_root in previous_linked:
            raise TrainingError(
                "previous linked worktree cursor repeats root: %s" % item_root
            )
        previous_linked[item_root] = item

    linked_snapshots: List[Dict[str, Any]] = []
    linked_evidence: List[Dict[str, Any]] = []
    linked_detectors: List[str] = []
    linked_incomplete_reasons: List[str] = []
    linked_history_incomplete: List[str] = []
    linked_untracked_files = 0
    evidence_remaining = MAX_LINKED_EVIDENCE_CHARS
    for record in linked_records:
        details = linked_worktree_source(
            record,
            source_path,
            previous_linked.get(record["root"]),
            linked_paths_within(Path(record["root"]), worktrees_before),
        )
        linked_snapshots.append(details.pop("snapshot"))
        evidence_remaining = trim_linked_evidence(
            details,
            evidence_remaining,
        )
        linked_evidence.append(details)
        linked_detectors.extend(details["secretDetectors"])
        linked_untracked_files += details["counts"]["untrackedFiles"]
        for reason in details["incompleteReasons"]:
            linked_incomplete_reasons.append(
                "%s: %s" % (record["root"], reason)
            )
        if not details["historyComplete"]:
            linked_history_incomplete.append(record["root"])

    linked_snapshots.sort(key=lambda item: item["root"])
    linked_evidence.sort(key=lambda item: item["root"])
    current_linked_roots = {item["root"] for item in linked_snapshots}
    removed_linked_roots = sorted(
        root_value
        for root_value in previous_linked
        if root_value not in current_linked_roots
    )
    removed_linked_reasons = [
        (
            "removed linked worktree could contain commits newer than its "
            "reviewed cursor and requires an explicit history rebaseline: %s"
        )
        % root_value
        for root_value in removed_linked_roots
    ]
    incomplete_reasons = sorted(
        set(
            untracked["incompleteReasons"]
            + index_flags["incompleteReasons"]
            + linked_incomplete_reasons
            + removed_linked_reasons
        )
    )
    snapshot_partial = bool(
        untracked["partial"]
        or index_flags["partial"]
        or any(item.get("partial") for item in linked_snapshots)
        or removed_linked_roots
    )
    snapshot = {
        "kind": "git",
        "head": head,
        "branch": safe_branch,
        "branchHash": sha256_text(branch),
        "dirtyHash": dirty_hash,
        "dirtyBytes": dirty_bytes,
        "untrackedHash": untracked["hash"],
        "linkedWorktrees": linked_snapshots,
        "partial": snapshot_partial,
    }
    if index_flags["count"] or isinstance(
        previous_source.get("indexFlagsHash"), str
    ):
        snapshot["indexFlagsHash"] = index_flags["hash"]
    history_complete = bool(
        history["historyComplete"]
        and not linked_history_incomplete
        and not removed_linked_roots
    )
    blocking_reasons: List[str] = []
    if not history["historyComplete"]:
        blocking_reasons.append(
            "Git history could not be compared with the previous cursor"
        )
    if linked_history_incomplete:
        blocking_reasons.append(
            "linked Git history could not be compared for: %s"
            % ", ".join(linked_history_incomplete)
        )
    if removed_linked_roots:
        blocking_reasons.append(
            "removed linked worktree history could not be compared for: %s"
            % ", ".join(removed_linked_roots)
        )

    current_linked_snapshot = linked_snapshots
    previous_linked_snapshot = sorted(
        previous_linked.values(),
        key=lambda item: str(item.get("root", "")),
    )
    linked_changed = (
        current_linked_snapshot != previous_linked_snapshot
        or any(item["hasChanges"] for item in linked_evidence)
        or bool(removed_linked_roots)
    )
    has_changes = bool(
        previous is None
        or previous_head != head
        or branch_changed
        or previous_dirty != dirty_hash
        or previous_untracked != untracked["hash"]
        or flagged_changed
        or linked_changed
        or snapshot_partial
    )
    worktrees_after = registered_git_worktrees(root)
    if worktrees_after != worktrees_before:
        raise TrainingError(
            "git worktree registry or HEAD changed during source scan; rescan required"
        )
    return {
        "snapshot": snapshot,
        "hasChanges": has_changes,
        "historyMode": history["historyMode"],
        "historyComplete": history_complete,
        "blockingReason": "; ".join(blocking_reasons) or None,
        "baseHead": base_head,
        "commonMergeBase": history["commonMergeBase"],
        "bootstrapHistoryTruncated": history[
            "bootstrapHistoryTruncated"
        ],
        "bootstrapTotalCommits": history["bootstrapTotalCommits"],
        "committedRange": committed_range,
        "commits": commits,
        "committedDiff": committed_diff,
        "dirtyDiff": dirty_diff,
        "untracked": untracked["context"] if include_untracked else [],
        "indexFlagged": index_flags["entries"] if flagged_changed else [],
        "linkedWorktrees": linked_evidence,
        "linkedWorktreesRemoved": removed_linked_roots,
        "truncated": bool(
            committed_truncated
            or dirty_truncated
            or history["bootstrapHistoryTruncated"]
            or index_flags["evidenceTruncated"]
            or snapshot_partial
            or any(item["truncated"] for item in linked_evidence)
        ),
        "incompleteReasons": incomplete_reasons,
        "secretDetectors": sorted(
            set(
                committed_detectors
                + dirty_detectors
                + untracked["secretDetectors"]
                + index_flags["secretDetectors"]
                + linked_detectors
                + branch_detectors
            )
        ),
        "counts": {
            "untrackedFiles": untracked["totalFiles"],
            "untrackedManifestFiles": len(untracked["manifest"]),
            "untrackedOmittedFiles": untracked["omittedFiles"],
            "untrackedHashedBytes": untracked["hashedBytes"],
            "indexFlaggedFiles": index_flags["count"],
            "indexFlaggedManifestFiles": index_flags["manifestFiles"],
            "indexFlaggedOmittedFiles": index_flags["omittedFiles"],
            "indexFlaggedHashedBytes": index_flags["hashedBytes"],
            "linkedWorktrees": len(linked_snapshots),
            "linkedWorktreesChanged": sum(
                1 for item in linked_evidence if item["hasChanges"]
            )
            + len(removed_linked_roots),
            "linkedUntrackedFiles": linked_untracked_files,
        },
    }


def iter_non_git_files(
    root: Path,
    source_path: str,
    walk_errors: Optional[List[str]] = None,
) -> Iterable[Tuple[str, Path]]:
    root = root.resolve(strict=True)
    errors = walk_errors if walk_errors is not None else []

    def record_walk_error(exc: OSError) -> None:
        raw_path = str(getattr(exc, "filename", "") or root)
        try:
            label = Path(raw_path).resolve(strict=False).relative_to(root).as_posix()
        except (OSError, ValueError):
            label = Path(raw_path).name or "."
        safe_label, _ = redact_secrets(label)
        errors.append("directory could not be traversed: %s" % safe_label)

    for current_root, dir_names, file_names in os.walk(
        str(root),
        topdown=True,
        onerror=record_walk_error,
        followlinks=False,
    ):
        current = Path(current_root)
        try:
            relative_dir = current.relative_to(root)
        except ValueError:
            errors.append("walker escaped project root")
            dir_names[:] = []
            continue

        traversable_dirs: List[str] = []
        directory_symlinks: List[Tuple[str, Path]] = []
        for name in sorted(dir_names):
            relative = (relative_dir / name).as_posix()
            if name in IGNORED_DIRS or path_is_ignored(
                relative + "/placeholder",
                source_path,
            ):
                continue
            candidate = current / name
            try:
                candidate_stat = candidate.lstat()
            except OSError:
                safe_relative, _ = redact_secrets(relative)
                errors.append(
                    "directory entry could not be inspected: %s" % safe_relative
                )
                continue
            if stat.S_ISLNK(candidate_stat.st_mode):
                directory_symlinks.append((relative, candidate))
            else:
                traversable_dirs.append(name)
        dir_names[:] = traversable_dirs

        for relative, path in directory_symlinks:
            yield relative, path
        for name in sorted(file_names):
            relative = (relative_dir / name).as_posix()
            if path_is_ignored(relative, source_path):
                continue
            yield relative, current / name


def non_git_source_snapshot(
    root: Path,
    source_path: str,
    previous: Optional[Dict[str, Any]],
) -> Dict[str, Any]:
    manifest: Dict[str, Dict[str, Any]] = {}
    sanitized_excerpts: Dict[str, Tuple[str, List[str]]] = {}
    total_hashed = 0
    partial = False
    incomplete_reasons: List[str] = []
    secret_detectors: List[str] = []
    walk_errors: List[str] = []
    root_resolved = root.resolve(strict=True)
    for relative, path in iter_non_git_files(
        root_resolved,
        source_path,
        walk_errors,
    ):
        if len(manifest) >= MAX_NON_GIT_FILES:
            partial = True
            incomplete_reasons.append(
                "non-Git file count exceeded the %d-file safety limit"
                % MAX_NON_GIT_FILES
            )
            break
        safe_relative, _ = redact_secrets(relative)
        try:
            path_stat = path.lstat()
            if stat.S_ISLNK(path_stat.st_mode):
                target = os.readlink(path)
                link_hash = sha256_bytes(os.fsencode(target))
                try:
                    resolved = path.resolve(strict=True)
                except OSError:
                    manifest[relative] = {
                        "type": "broken-symlink",
                        "linkHash": link_hash,
                    }
                    partial = True
                    incomplete_reasons.append(
                        "symlink target could not be resolved: %s" % safe_relative
                    )
                    continue
                if not path_is_within(resolved, root_resolved):
                    manifest[relative] = {
                        "type": "external-symlink",
                        "linkHash": link_hash,
                    }
                    partial = True
                    incomplete_reasons.append(
                        "symlink escapes project root and was not followed: %s"
                        % safe_relative
                    )
                    continue
                target_relative = resolved.relative_to(root_resolved).as_posix()
                if path_is_ignored(target_relative, source_path):
                    manifest[relative] = {
                        "type": "ignored-target-symlink",
                        "linkHash": link_hash,
                        "targetPathHash": sha256_text(target_relative),
                    }
                    partial = True
                    secret_detectors.append("sensitive-symlink-target")
                    incomplete_reasons.append(
                        "symlink target is ignored or sensitive and was not "
                        "followed: %s" % safe_relative
                    )
                    continue
                file_stat = resolved.stat()
                if not stat.S_ISREG(file_stat.st_mode):
                    manifest[relative] = {
                        "type": "non-file-symlink",
                        "linkHash": link_hash,
                    }
                    partial = True
                    incomplete_reasons.append(
                        "symlink target is not a regular file and was not traversed: %s"
                        % safe_relative
                    )
                    continue
                if total_hashed + file_stat.st_size > MAX_NON_GIT_HASH_BYTES:
                    partial = True
                    incomplete_reasons.append(
                        "non-Git hashed bytes exceeded the %d-byte safety limit"
                        % MAX_NON_GIT_HASH_BYTES
                    )
                    break
                digest, hashed_size, excerpt, detectors = (
                    fingerprint_regular_file(
                        resolved,
                        file_stat,
                        MAX_NON_GIT_HASH_BYTES - total_hashed,
                        Path(relative),
                    )
                )
                total_hashed += hashed_size
                sanitized_excerpts[relative] = (excerpt, detectors)
                manifest[relative] = {
                    "type": "symlink",
                    "linkHash": link_hash,
                    "hash": digest,
                    "size": hashed_size,
                }
                continue

            if not stat.S_ISREG(path_stat.st_mode):
                manifest[relative] = {"type": "non-regular"}
                partial = True
                incomplete_reasons.append(
                    "non-regular path was not fingerprinted: %s" % safe_relative
                )
                continue
            resolved = path.resolve(strict=True)
            if not path_is_within(resolved, root_resolved):
                manifest[relative] = {"type": "unsafe"}
                partial = True
                incomplete_reasons.append(
                    "path escapes project root and was not followed: %s"
                    % safe_relative
                )
                continue
            file_stat = resolved.stat()
            if total_hashed + file_stat.st_size > MAX_NON_GIT_HASH_BYTES:
                partial = True
                incomplete_reasons.append(
                    "non-Git hashed bytes exceeded the %d-byte safety limit"
                    % MAX_NON_GIT_HASH_BYTES
                )
                break
            digest, hashed_size, excerpt, detectors = fingerprint_regular_file(
                resolved,
                file_stat,
                MAX_NON_GIT_HASH_BYTES - total_hashed,
                Path(relative),
            )
            total_hashed += hashed_size
            sanitized_excerpts[relative] = (excerpt, detectors)
            manifest[relative] = {
                "hash": digest,
                "size": hashed_size,
            }
        except (OSError, TrainingError):
            manifest[relative] = {"type": "unreadable"}
            partial = True
            incomplete_reasons.append(
                "path could not be fingerprinted: %s" % safe_relative
            )
            continue
    if walk_errors:
        partial = True
        incomplete_reasons.extend(walk_errors)
    manifest_hash = sha256_bytes(canonical_json(manifest))
    snapshot = {
        "kind": "files",
        "manifestHash": manifest_hash,
        "fileManifest": manifest,
        "partial": partial,
    }
    previous_source = previous.get("source", {}) if previous else {}
    old_manifest = (
        previous_source.get("fileManifest", {})
        if previous_source.get("kind") == "files"
        else {}
    )
    if not isinstance(old_manifest, dict):
        old_manifest = {}
    added = sorted(path for path in manifest if path not in old_manifest)
    modified = sorted(
        path
        for path in manifest
        if path in old_manifest
        and manifest[path] != old_manifest[path]
    )
    removed = sorted(path for path in old_manifest if path not in manifest)
    context: List[Dict[str, Any]] = []
    for relative in (added + modified)[:40]:
        entry = manifest.get(relative, {})
        incomplete_entry = entry.get("type") in {
            "broken-symlink",
            "external-symlink",
            "ignored-target-symlink",
            "non-file-symlink",
            "non-regular",
            "unsafe",
            "unreadable",
        }
        excerpt, detectors = (
            ("", [])
            if incomplete_entry
            else sanitized_excerpts.get(relative, ("", []))
        )
        secret_detectors.extend(detectors)
        context.append(
            {
                "path": relative,
                "change": "added" if relative in added else "modified",
                "excerpt": excerpt,
                "quarantined": bool(incomplete_entry or (detectors and not excerpt)),
            }
        )
    previous_hash = previous_source.get("manifestHash")
    return {
        "snapshot": snapshot,
        # A coverage-limited cursor must never become a silent no-op: an unseen
        # file could have changed while the bounded manifest stayed identical.
        "hasChanges": previous is None or previous_hash != manifest_hash or partial,
        "historyMode": "bootstrap" if previous is None else "manifest-delta",
        "added": added[:200],
        "modified": modified[:200],
        "removed": removed[:200],
        "context": context,
        "truncated": len(added) + len(modified) + len(removed) > 200 or partial,
        "incompleteReasons": sorted(set(incomplete_reasons)),
        "secretDetectors": sorted(set(secret_detectors)),
        "counts": {
            "files": len(manifest),
            "added": len(added),
            "modified": len(modified),
            "removed": len(removed),
        },
    }


def is_git_project(root: Path) -> bool:
    code, stdout, stderr = run_process(
        ["git", "rev-parse", "--is-inside-work-tree"],
        root,
        max_bytes=1024,
    )
    if code == 0:
        return stdout.decode("utf-8", "replace").strip() == "true"
    if code == 128 and not (root / ".git").exists():
        return False
    raise TrainingError(
        "cannot determine Git state for %s: %s"
        % (
            root,
            strip_control_chars(stderr.decode("utf-8", "replace")).strip()
            or "git command failed",
        )
    )


def read_registry_payload(api_url: Optional[str], ports_file: Path) -> Tuple[Any, str]:
    if api_url:
        parsed = urllib.parse.urlparse(api_url)
        if (
            parsed.scheme != "http"
            or parsed.hostname not in {"localhost", "127.0.0.1", "::1"}
            or parsed.username is not None
            or parsed.password is not None
            or parsed.query
            or parsed.fragment
        ):
            raise TrainingError(
                "--api-url must be a plain HTTP loopback URL without credentials, "
                "query, or fragment"
            )
        url = api_url.rstrip("/") + "/api/ports"
        try:
            opener = urllib.request.build_opener(
                urllib.request.ProxyHandler({}),
                NoRedirectHandler(),
            )
            with opener.open(url, timeout=2.0) as response:
                data = response.read(8 * 1024 * 1024 + 1)
            if len(data) > 8 * 1024 * 1024:
                raise TrainingError("AgentsToZ registry response exceeds 8 MiB")
            return json.loads(data.decode("utf-8")), url
        except Exception:
            pass
    if ports_file.is_file():
        return load_json_file(ports_file, 16 * 1024 * 1024), str(ports_file)
    return [], str(ports_file)


def registry_projects(
    api_url: Optional[str],
    ports_file: Path,
    explicit_projects: Sequence[str],
    include_cwd: bool,
) -> Tuple[List[Dict[str, str]], List[str], str]:
    if explicit_projects:
        payload, source = [], "explicit-projects"
    else:
        payload, source = read_registry_payload(api_url, ports_file)
    rows = payload.get("ports", []) if isinstance(payload, dict) else payload
    warnings: List[str] = []
    if not isinstance(rows, list):
        raise TrainingError("ports registry must be an array or {ports: array}")
    by_root: Dict[str, Dict[str, str]] = {}
    if not explicit_projects:
        for row in rows:
            if not isinstance(row, dict):
                continue
            folder = row.get("folderPath")
            if not isinstance(folder, str) or not folder or "\0" in folder:
                continue
            path = Path(folder).expanduser()
            if not path.is_absolute() or not path.is_dir():
                continue
            resolved = str(path.resolve())
            by_root.setdefault(
                resolved,
                {
                    "root": resolved,
                    "name": str(row.get("name") or Path(resolved).name),
                    "origin": "ports-registry",
                },
            )
    for value in explicit_projects:
        path = Path(value).expanduser()
        if not path.is_absolute() or not path.is_dir():
            warnings.append("explicit project is missing or not absolute: %s" % value)
            continue
        resolved = str(path.resolve())
        by_root[resolved] = {
            "root": resolved,
            "name": Path(resolved).name,
            "origin": "explicit",
        }
    if include_cwd and not explicit_projects:
        cwd = Path.cwd().resolve()
        if (cwd / ".agent-memory" / "config.json").is_file():
            by_root.setdefault(
                str(cwd),
                {"root": str(cwd), "name": cwd.name, "origin": "cwd"},
            )
    return sorted(by_root.values(), key=lambda item: item["root"]), warnings, source


def resolve_memory_project(project: Dict[str, str]) -> Dict[str, Any]:
    root = Path(project["root"]).resolve(strict=True)
    agent_memory_dir = root / ".agent-memory"
    if agent_memory_dir.is_symlink():
        raise TrainingError("symlinked .agent-memory directory is unsafe: %s" % agent_memory_dir)
    resolved_agent_memory = agent_memory_dir.resolve(strict=True)
    if not path_is_within(resolved_agent_memory, root):
        raise TrainingError(".agent-memory escapes project root: %s" % agent_memory_dir)
    config_path = resolved_agent_memory / "config.json"
    if not config_path.is_file() or config_path.is_symlink():
        raise TrainingError("project memory config missing or unsafe: %s" % config_path)
    config = load_json_file(config_path, MAX_CONFIG_BYTES)
    if not isinstance(config, dict):
        raise TrainingError("project memory config must be an object: %s" % config_path)
    memory_id = config.get("memoryId")
    source_path = config.get("sourcePath")
    if not isinstance(memory_id, str) or not memory_id or len(memory_id) > 160:
        raise TrainingError("invalid memoryId in %s" % config_path)
    if not isinstance(source_path, str) or not source_path or "\0" in source_path:
        raise TrainingError("invalid sourcePath in %s" % config_path)
    source = Path(source_path)
    if source.is_absolute() or ".." in source.parts:
        raise TrainingError("sourcePath must stay project-relative: %s" % source_path)
    memory_path = (root / source).resolve(strict=True)
    if not path_is_within(memory_path, root):
        raise TrainingError("memory source escapes project root: %s" % memory_path)
    memory_bytes = stable_read_bytes(memory_path, MAX_MEMORY_BYTES)
    memory_text = decode_utf8(memory_bytes, memory_path)
    _, memory_secret_detectors = redact_secrets(memory_text)
    parsed = parse_memory_blocks(memory_text)
    return {
        "memoryId": memory_id,
        "projectName": project["name"],
        "projectRoot": str(root),
        "origin": project["origin"],
        "sourcePath": source_path.replace("\\", "/"),
        "memoryPath": str(memory_path),
        "memoryBytes": len(memory_bytes),
        "memoryModifiedAt": dt.datetime.fromtimestamp(
            memory_path.stat().st_mtime,
            tz=dt.timezone.utc,
        ).isoformat().replace("+00:00", "Z"),
        "configLastUpdatedAt": config.get("lastUpdatedAt"),
        "autoBackup": config.get("autoBackup") is True,
        "memory": parsed,
        "memorySecretDetectors": memory_secret_detectors,
    }


def build_scan(args: argparse.Namespace) -> Dict[str, Any]:
    state_path = Path(args.state_file).expanduser()
    state = load_state(state_path)
    previous_projects = consumer_projects(state, args.consumer)
    registry, warnings, registry_source = registry_projects(
        args.api_url,
        Path(args.ports_file).expanduser(),
        args.project,
        not args.no_cwd,
    )
    resolved: List[Dict[str, Any]] = []
    skipped: List[Dict[str, str]] = []
    for project in registry:
        config_path = Path(project["root"]) / ".agent-memory" / "config.json"
        if not config_path.is_file():
            continue
        try:
            resolved.append(resolve_memory_project(project))
        except (OSError, TrainingError) as exc:
            skipped.append({"projectRoot": project["root"], "error": str(exc)})

    by_memory_id: Dict[str, List[Dict[str, Any]]] = {}
    for item in resolved:
        by_memory_id.setdefault(item["memoryId"], []).append(item)

    projects: List[Dict[str, Any]] = []
    conflicts: List[Dict[str, Any]] = []
    for memory_id in sorted(by_memory_id):
        copies = sorted(by_memory_id[memory_id], key=lambda item: item["projectRoot"])
        hashes = {copy["memory"]["documentHash"] for copy in copies}
        if len(copies) > 1:
            conflicts.append(
                {
                    "memoryId": memory_id,
                    "reason": (
                        "same memoryId is registered at multiple roots; "
                        "scan one explicit canonical project"
                    ),
                    "contentDivergent": len(hashes) > 1,
                    "projectRoots": [copy["projectRoot"] for copy in copies],
                }
            )
            continue
        item = copies[0]
        aliases: List[str] = []
        previous = previous_projects.get(memory_id)
        if previous and previous.get("parserVersion") != PARSER_VERSION:
            skipped.append(
                {
                    "projectRoot": item["projectRoot"],
                    "error": "parser version changed; explicit rebaseline required",
                }
            )
            continue
        try:
            source = (
                git_source_snapshot(
                    Path(item["projectRoot"]),
                    item["sourcePath"],
                    previous,
                )
                if is_git_project(Path(item["projectRoot"]))
                else non_git_source_snapshot(
                    Path(item["projectRoot"]),
                    item["sourcePath"],
                    previous,
                )
            )
        except (OSError, TrainingError) as exc:
            skipped.append(
                {
                    "projectRoot": item["projectRoot"],
                    "error": "source scan failed closed: %s" % exc,
                }
            )
            continue
        source["requiresBootstrapAcceptance"] = previous is None
        delta = memory_delta(previous, item["memory"]["blocks"])
        memory_changed = (
            previous is None
            or previous.get("memoryHash") != item["memory"]["documentHash"]
        )
        needs_review = bool(
            args.force
            or source["hasChanges"]
            or memory_changed
            or delta["candidateCount"]
            or delta["removed"]
            or previous is None
        )
        projects.append(
            {
                "memoryId": memory_id,
                "projectName": item["projectName"],
                "projectRoot": item["projectRoot"],
                "aliases": aliases,
                "sourcePath": item["sourcePath"],
                "memoryPath": item["memoryPath"],
                "memoryBytes": item["memoryBytes"],
                "memoryModifiedAt": item["memoryModifiedAt"],
                "configLastUpdatedAtHintOnly": item["configLastUpdatedAt"],
                "autoBackup": item["autoBackup"],
                "baseGeneration": int(previous.get("generation", 0)) if previous else 0,
                "baseMemoryHash": previous.get("memoryHash") if previous else None,
                "memoryHashBefore": item["memory"]["documentHash"],
                "memoryChangedSinceCursor": memory_changed,
                "memoryParseValid": item["memory"]["valid"],
                "memoryWarnings": item["memory"]["warnings"],
                "memorySecretDetectors": item["memorySecretDetectors"],
                "memoryBlockCountBefore": len(item["memory"]["blocks"]),
                "memoryBlocksBefore": state_block_snapshot(item["memory"]["blocks"]),
                "memoryDelta": delta,
                "source": source,
                "needsReview": needs_review,
                "forced": bool(args.force),
            }
        )

    run = {
        "schemaVersion": RUN_SCHEMA,
        "parserVersion": PARSER_VERSION,
        "runId": str(uuid.uuid4()),
        "createdAt": utc_now(),
        "consumer": args.consumer,
        "stateFile": str(state_path),
        "registrySource": registry_source,
        "projects": projects,
        "conflicts": conflicts,
        "skipped": skipped,
        "warnings": warnings,
        "summary": {
            "registeredProjects": len(registry),
            "memoryEnabledProjects": len(resolved),
            "reviewableProjects": len(projects),
            "changedProjects": sum(1 for project in projects if project["needsReview"]),
            "memoryCandidates": sum(
                project["memoryDelta"]["candidateCount"] for project in projects
            ),
            "conflicts": len(conflicts),
            "skipped": len(skipped),
        },
    }
    return run


def write_run_file(path: Path, run: Dict[str, Any]) -> None:
    atomic_write_json(path, run)


def command_scan(args: argparse.Namespace) -> int:
    run = build_scan(args)
    if args.output:
        output_path = Path(args.output).expanduser()
        write_run_file(output_path, run)
        result = {
            "ok": True,
            "runId": run["runId"],
            "runFile": str(output_path),
            "summary": run["summary"],
            "projects": [
                {
                    "memoryId": project["memoryId"],
                    "projectName": project["projectName"],
                    "projectRoot": project["projectRoot"],
                    "needsReview": project["needsReview"],
                    "sourceKind": project["source"]["snapshot"]["kind"],
                    "sourceChanged": project["source"]["hasChanges"],
                    "memoryCandidates": project["memoryDelta"]["candidateCount"],
                    "memoryRemoved": len(project["memoryDelta"]["removed"]),
                    "secretDetectors": project["source"].get("secretDetectors", []),
                    "memorySecretDetectors": project.get(
                        "memorySecretDetectors", []
                    ),
                }
                for project in run["projects"]
            ],
            "conflicts": run["conflicts"],
            "skipped": run["skipped"],
            "warnings": run["warnings"],
        }
    else:
        result = run
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


def read_run_file(path: Path) -> Dict[str, Any]:
    if path.is_symlink():
        raise TrainingError("run file must not be a symlink: %s" % path)
    raw = load_json_file(path, 64 * 1024 * 1024)
    if not isinstance(raw, dict) or raw.get("schemaVersion") != RUN_SCHEMA:
        raise TrainingError("invalid training run file: %s" % path)
    if raw.get("parserVersion") != PARSER_VERSION:
        raise TrainingError("run parser version is incompatible: %s" % path)
    if not isinstance(raw.get("projects"), list):
        raise TrainingError("run has no projects array: %s" % path)
    return raw


def state_block_snapshot(blocks: Sequence[Dict[str, Any]]) -> List[Dict[str, Any]]:
    snapshots: List[Dict[str, Any]] = []
    for block in blocks:
        safe_section, _ = redact_secrets(str(block["section"]))
        safe_title, _ = redact_secrets(str(block["title"]))
        snapshots.append(
            {
            "key": block["key"],
            "hash": block["hash"],
            "section": safe_section[:240],
            "kind": block["kind"],
            "title": safe_title[:240],
            "trainable": bool(block.get("trainable")),
            }
        )
    return snapshots


def project_from_run(run: Dict[str, Any], memory_id: str) -> Dict[str, Any]:
    matches = [
        project
        for project in run["projects"]
        if project.get("memoryId") == memory_id
    ]
    if len(matches) != 1:
        raise TrainingError(
            "run must contain exactly one project for memoryId %s" % memory_id
        )
    return matches[0]


def command_backup(args: argparse.Namespace) -> int:
    run_path = Path(args.run_file).expanduser()
    run = read_run_file(run_path)
    project = project_from_run(run, args.memory_id)
    resolved = resolve_memory_project(
        {
            "root": project["projectRoot"],
            "name": project["projectName"],
            "origin": "backup",
        }
    )
    if resolved["memoryId"] != args.memory_id:
        raise TrainingError("project memoryId changed since scan; rescan required")
    if resolved["memory"]["documentHash"] != project.get("memoryHashBefore"):
        raise TrainingError("project memory changed since scan; rescan before editing")
    if resolved.get("memorySecretDetectors"):
        raise TrainingError(
            "project memory contains secret indicators; remove them before backup/training"
        )
    source = Path(resolved["memoryPath"])
    payload = stable_read_bytes(source, MAX_MEMORY_BYTES)
    stamp = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H-%M-%S-%fZ")
    backup_name = "CORE-%s-ltmt-%s.md" % (stamp, run["runId"][:8])
    project_root = Path(project["projectRoot"]).resolve(strict=True)
    memory_root = (project_root / ".agent-memory").resolve(strict=True)
    backup_dir = project_root / ".agent-memory" / "backups"
    if backup_dir.is_symlink():
        raise TrainingError("symlinked backup directory is unsafe: %s" % backup_dir)
    backup_dir.mkdir(parents=True, exist_ok=True)
    resolved_backup_dir = backup_dir.resolve(strict=True)
    if not path_is_within(resolved_backup_dir, memory_root):
        raise TrainingError("backup directory escapes .agent-memory: %s" % backup_dir)
    backup_path = resolved_backup_dir / backup_name
    if backup_path.exists():
        raise TrainingError("backup path already exists: %s" % backup_path)
    atomic_write_bytes(backup_path, payload)
    print(
        json.dumps(
            {
                "ok": True,
                "runId": run["runId"],
                "memoryId": args.memory_id,
                "memoryHash": resolved["memory"]["documentHash"],
                "backupPath": str(backup_path),
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


def command_diff_memory(args: argparse.Namespace) -> int:
    run_path = Path(args.run_file).expanduser()
    run = read_run_file(run_path)
    project = project_from_run(run, args.memory_id)
    resolved = resolve_memory_project(
        {
            "root": project["projectRoot"],
            "name": project["projectName"],
            "origin": "diff-memory",
        }
    )
    if resolved["memoryId"] != args.memory_id:
        raise TrainingError("project memoryId changed since scan; rescan required")
    previous = {"blocks": project.get("memoryBlocksBefore", [])}
    delta = memory_delta(previous, resolved["memory"]["blocks"])
    result = {
        "ok": True,
        "runId": run["runId"],
        "memoryId": args.memory_id,
        "memoryHashBefore": project.get("memoryHashBefore"),
        "memoryHashAfter": resolved["memory"]["documentHash"],
        "memoryChanged": (
            project.get("memoryHashBefore") != resolved["memory"]["documentHash"]
        ),
        "blocksBefore": len(project.get("memoryBlocksBefore", [])),
        "blocksAfter": len(resolved["memory"]["blocks"]),
        "delta": delta,
        "warnings": resolved["memory"]["warnings"],
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


def load_learning_queue(path: Path) -> List[Dict[str, Any]]:
    if path.is_symlink():
        raise TrainingError("learning queue must not be a symlink: %s" % path)
    if not path.is_file():
        raise TrainingError("learning queue not found: %s" % path)
    raw = load_json_file(path, 16 * 1024 * 1024)
    if not isinstance(raw, list):
        raise TrainingError("learning queue must contain a JSON array: %s" % path)
    return [item for item in raw if isinstance(item, dict)]


def absolute_without_symlink_resolution(path: Path) -> Path:
    """Make a path stable across commands while preserving symlink detection."""
    return Path(os.path.abspath(os.fspath(path.expanduser())))


def candidate_immutable_hash(item: Dict[str, Any]) -> str:
    immutable = {
        "id": item.get("id"),
        "idea": item.get("idea"),
        "evidence": item.get("evidence"),
        "tier": item.get("tier"),
        "provenance": item.get("provenance"),
    }
    return sha256_bytes(canonical_json(immutable))


def validate_review_candidates(
    run: Dict[str, Any],
    project: Dict[str, Any],
    candidate_ids: Sequence[str],
    queue_path: Path,
) -> List[Dict[str, Any]]:
    if not candidate_ids:
        return []
    if len(set(candidate_ids)) != len(candidate_ids):
        raise TrainingError("candidate ids must be unique")
    items = load_learning_queue(queue_path)
    by_id: Dict[str, List[Dict[str, Any]]] = {}
    for item in items:
        item_id = item.get("id")
        if isinstance(item_id, str) and item_id:
            by_id.setdefault(item_id, []).append(item)
    validated: List[Dict[str, Any]] = []
    for candidate_id in candidate_ids:
        matches = by_id.get(candidate_id, [])
        if len(matches) != 1:
            raise TrainingError(
                "candidate id must exist exactly once in queue: %s" % candidate_id
            )
        item = matches[0]
        if item.get("status") not in {"pending", "promoted", "rejected"}:
            raise TrainingError(
                "candidate has no durable disposition: %s" % candidate_id
            )
        provenance = item.get("provenance")
        if not isinstance(provenance, dict):
            raise TrainingError(
                "candidate has no structured provenance: %s" % candidate_id
            )
        if (
            provenance.get("source_run_id") != run["runId"]
            or provenance.get("memory_id") != project["memoryId"]
            or not provenance.get("source_range")
        ):
            raise TrainingError(
                "candidate provenance does not match this run/project: %s"
                % candidate_id
            )
        idea = item.get("idea")
        if not isinstance(idea, str) or not idea.startswith("[project-memory:"):
            raise TrainingError(
                "candidate is not a project-memory learning: %s" % candidate_id
            )
        validated.append(
            {
                "id": candidate_id,
                "status": item["status"],
                "provenance": provenance,
                "immutableHash": candidate_immutable_hash(item),
            }
        )
    return validated


def source_snapshot_hash(project: Dict[str, Any]) -> str:
    snapshot = project.get("source", {}).get("snapshot")
    if not isinstance(snapshot, dict):
        raise TrainingError("run project has no source snapshot")
    return sha256_bytes(canonical_json(snapshot))


def command_review_complete(args: argparse.Namespace) -> int:
    """Record a machine-verifiable review receipt before cursor commit."""
    run_path = Path(args.run_file).expanduser()
    with FileLock(run_path):
        run = read_run_file(run_path)
        project = project_from_run(run, args.memory_id)
        candidate_ids = list(args.candidate_id or [])
        if bool(candidate_ids) == bool(args.no_reusable_candidates):
            raise TrainingError(
                "provide candidate ids or --no-reusable-candidates, but not both"
            )
        source = project.get("source", {})
        snapshot = source.get("snapshot", {})
        incomplete_history = source.get("historyComplete") is False
        incomplete_coverage = bool(
            source.get("truncated")
            or (isinstance(snapshot, dict) and snapshot.get("partial"))
        )
        if incomplete_history and not args.accept_history_rebaseline:
            raise TrainingError(
                "source history could not be compared with the prior tree; review it and "
                "pass --accept-history-rebaseline"
            )
        if (
            source.get("requiresBootstrapAcceptance")
            and not args.accept_bootstrap
        ):
            raise TrainingError(
                "no prior successful cursor exists; review the initial memory/source "
                "baseline and pass --accept-bootstrap"
            )
        if incomplete_coverage and not args.accept_incomplete_source:
            raise TrainingError(
                "source evidence is coverage-limited; inspect the required files and "
                "pass --accept-incomplete-source"
            )

        resolved = resolve_memory_project(
            {
                "root": project["projectRoot"],
                "name": project["projectName"],
                "origin": "review-complete",
            }
        )
        if resolved["memoryId"] != args.memory_id:
            raise TrainingError("project memoryId changed since scan; rescan required")
        parsed = resolved["memory"]
        if not parsed["valid"]:
            raise TrainingError("reviewed memory failed Markdown structure validation")
        if resolved.get("memorySecretDetectors"):
            raise TrainingError(
                "reviewed memory contains secret indicators; remove them before training"
            )

        queue_path = absolute_without_symlink_resolution(Path(args.btw_file))
        queue_guard = (
            learning_queue_lock(queue_path) if candidate_ids else nullcontext()
        )
        with queue_guard:
            candidates = validate_review_candidates(
                run,
                project,
                candidate_ids,
                queue_path,
            )
            delta = memory_delta(
                {"blocks": project.get("memoryBlocksBefore", [])},
                parsed["blocks"],
            )
            receipt = {
                "reviewId": str(uuid.uuid4()),
                "reviewedAt": utc_now(),
                "memoryHash": parsed["documentHash"],
                "memoryBlocks": len(parsed["blocks"]),
                "sourceSnapshotHash": source_snapshot_hash(project),
                "candidateIds": candidate_ids,
                "candidateDispositions": candidates,
                "noReusableCandidates": bool(args.no_reusable_candidates),
                "queuePath": str(queue_path) if candidate_ids else None,
                "acceptedIncompleteSource": bool(args.accept_incomplete_source),
                "acceptedHistoryRebaseline": bool(args.accept_history_rebaseline),
                "acceptedBootstrap": bool(args.accept_bootstrap),
                "memoryDelta": delta,
            }
            reviews = run.setdefault("reviews", {})
            if not isinstance(reviews, dict):
                raise TrainingError("run reviews field is invalid")
            reviews[args.memory_id] = receipt
            atomic_write_json(run_path, run)

    print(
        json.dumps(
            {
                "ok": True,
                "runId": run["runId"],
                "memoryId": args.memory_id,
                "reviewId": receipt["reviewId"],
                "memoryHash": receipt["memoryHash"],
                "candidateIds": candidate_ids,
                "noReusableCandidates": receipt["noReusableCandidates"],
                "acceptedIncompleteSource": receipt["acceptedIncompleteSource"],
                "acceptedHistoryRebaseline": receipt[
                    "acceptedHistoryRebaseline"
                ],
                "acceptedBootstrap": receipt["acceptedBootstrap"],
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


def commit_receipt_queue_path(
    run: Dict[str, Any],
    project: Dict[str, Any],
) -> Tuple[Dict[str, Any], List[str], Optional[Path]]:
    reviews = run.get("reviews")
    receipt = reviews.get(project["memoryId"]) if isinstance(reviews, dict) else None
    if not isinstance(receipt, dict):
        raise TrainingError(
            "review receipt missing; run review-complete before commit"
        )
    candidate_ids = receipt.get("candidateIds")
    if (
        not isinstance(candidate_ids, list)
        or not all(isinstance(value, str) and value for value in candidate_ids)
        or len(set(candidate_ids)) != len(candidate_ids)
    ):
        raise TrainingError("review receipt candidate list is invalid")
    if candidate_ids:
        queue_value = receipt.get("queuePath")
        if not isinstance(queue_value, str) or not queue_value:
            raise TrainingError("review receipt has no queue path")
        queue_path = absolute_without_symlink_resolution(Path(queue_value))
    else:
        queue_path = None
    if not candidate_ids and receipt.get("noReusableCandidates") is not True:
        raise TrainingError(
            "review receipt has neither durable candidates nor a no-candidate decision"
        )
    return receipt, list(candidate_ids), queue_path


def validate_commit_receipt(
    run: Dict[str, Any],
    project: Dict[str, Any],
    parsed: Dict[str, Any],
) -> Dict[str, Any]:
    receipt, candidate_ids, queue_path = commit_receipt_queue_path(run, project)
    if receipt.get("sourceSnapshotHash") != source_snapshot_hash(project):
        raise TrainingError("review receipt source snapshot mismatch; rescan required")
    if receipt.get("memoryHash") != parsed["documentHash"]:
        raise TrainingError(
            "project memory changed after review-complete; review again before commit"
        )
    if candidate_ids:
        if queue_path is None:
            raise TrainingError("review receipt has no queue path")
        current = validate_review_candidates(
            run,
            project,
            candidate_ids,
            queue_path,
        )
        sealed_raw = receipt.get("candidateDispositions")
        if not isinstance(sealed_raw, list):
            raise TrainingError(
                "review receipt has no immutable candidate dispositions; "
                "run review-complete again"
            )
        sealed_by_id: Dict[str, Dict[str, Any]] = {}
        for item in sealed_raw:
            if not isinstance(item, dict):
                raise TrainingError("review receipt candidate dispositions are invalid")
            item_id = item.get("id")
            immutable_hash = item.get("immutableHash")
            if (
                not isinstance(item_id, str)
                or not item_id
                or item_id in sealed_by_id
                or not isinstance(immutable_hash, str)
                or not re.fullmatch(r"[0-9a-f]{64}", immutable_hash)
            ):
                raise TrainingError("review receipt candidate dispositions are invalid")
            sealed_by_id[item_id] = item
        if set(sealed_by_id) != set(candidate_ids):
            raise TrainingError(
                "review receipt candidate dispositions do not match candidate ids"
            )
        for item in current:
            sealed = sealed_by_id[item["id"]]
            if sealed["immutableHash"] != item["immutableHash"]:
                raise TrainingError(
                    "candidate immutable fields changed after review-complete: %s"
                    % item["id"]
                )
    source = project.get("source", {})
    snapshot = source.get("snapshot", {})
    if (
        source.get("historyComplete") is False
        and receipt.get("acceptedHistoryRebaseline") is not True
    ):
        raise TrainingError("history rebaseline was not explicitly accepted")
    if (
        source.get("requiresBootstrapAcceptance")
        and receipt.get("acceptedBootstrap") is not True
    ):
        raise TrainingError("initial cursor baseline was not explicitly accepted")
    if (
        source.get("truncated")
        or (isinstance(snapshot, dict) and snapshot.get("partial"))
    ) and receipt.get("acceptedIncompleteSource") is not True:
        raise TrainingError("coverage-limited source was not explicitly accepted")
    return receipt


def command_commit(args: argparse.Namespace) -> int:
    run_path = Path(args.run_file).expanduser()
    run = read_run_file(run_path)
    project = project_from_run(run, args.memory_id)
    state_path = (
        Path(args.state_file).expanduser()
        if args.state_file
        else Path(run["stateFile"]).expanduser()
    )
    consumer = args.consumer or run["consumer"]
    _, _, queue_path = commit_receipt_queue_path(run, project)
    with FileLock(state_path):
        state = load_state(state_path)
        projects = consumer_projects(state, consumer)
        previous = projects.get(args.memory_id)
        current_generation = int(previous.get("generation", 0)) if previous else 0
        if current_generation != int(project.get("baseGeneration", 0)):
            raise TrainingError(
                "cursor generation changed since scan (%d != %d); rescan required"
                % (current_generation, int(project.get("baseGeneration", 0)))
            )
        resolved = resolve_memory_project(
            {
                "root": project["projectRoot"],
                "name": project["projectName"],
                "origin": "commit",
            }
        )
        if resolved["memoryId"] != args.memory_id:
            raise TrainingError("project memoryId changed since scan; rescan required")
        parsed = resolved["memory"]
        if not parsed["valid"]:
            raise TrainingError("updated memory failed Markdown structure validation")
        if resolved.get("memorySecretDetectors"):
            raise TrainingError(
                "updated memory contains secret indicators; cursor not advanced"
            )
        queue_guard = (
            learning_queue_lock(queue_path)
            if queue_path is not None
            else nullcontext()
        )
        # Lock order is always state -> queue. Keep the queue locked from its
        # final validation through the atomic state replacement.
        with queue_guard:
            receipt = validate_commit_receipt(run, project, parsed)
            before_count = int(project.get("memoryBlockCountBefore", 0))
            after_count = len(parsed["blocks"])
            if (
                before_count >= 4
                and after_count * 2 < before_count
                and not args.allow_large_delete
            ):
                raise TrainingError(
                    "memory block count dropped from %d to %d; use --allow-large-delete "
                    "only after explicit review" % (before_count, after_count)
                )
            projects[args.memory_id] = {
                "generation": current_generation + 1,
                "parserVersion": PARSER_VERSION,
                "projectName": project["projectName"],
                "projectRoot": project["projectRoot"],
                "sourcePath": project["sourcePath"],
                "lastSuccessfulRunId": run["runId"],
                "lastSuccessfulAt": utc_now(),
                "memoryHash": parsed["documentHash"],
                "blocks": state_block_snapshot(parsed["blocks"]),
                "source": project["source"]["snapshot"],
            }
            atomic_write_json(
                state_path,
                state,
                max_bytes=MAX_STATE_BYTES,
            )
    result = {
        "ok": True,
        "runId": run["runId"],
        "memoryId": args.memory_id,
        "consumer": consumer,
        "generation": current_generation + 1,
        "memoryHash": parsed["documentHash"],
        "memoryChanged": (
            parsed["documentHash"] != project.get("memoryHashBefore")
        ),
        "blocks": len(parsed["blocks"]),
        "reviewId": receipt["reviewId"],
        "stateFile": str(state_path),
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


def command_status(args: argparse.Namespace) -> int:
    state_path = Path(args.state_file).expanduser()
    state = load_state(state_path)
    projects = consumer_projects(state, args.consumer)
    result = {
        "ok": True,
        "stateFile": str(state_path),
        "consumer": args.consumer,
        "projects": [
            {
                "memoryId": memory_id,
                "projectName": cursor.get("projectName"),
                "projectRoot": cursor.get("projectRoot"),
                "generation": cursor.get("generation"),
                "lastSuccessfulAt": cursor.get("lastSuccessfulAt"),
                "lastSuccessfulRunId": cursor.get("lastSuccessfulRunId"),
                "sourceKind": cursor.get("source", {}).get("kind"),
                "sourceHead": cursor.get("source", {}).get("head"),
                "memoryHash": cursor.get("memoryHash"),
                "blocks": len(cursor.get("blocks", [])),
            }
            for memory_id, cursor in sorted(projects.items())
        ],
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


def command_cleanup(args: argparse.Namespace) -> int:
    path = Path(args.run_file).expanduser()
    if path.exists():
        read_run_file(path)
        path.unlink()
    print(json.dumps({"ok": True, "removed": str(path)}, ensure_ascii=False, indent=2))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Incremental project long-term-memory training cursor helper."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    scan = subparsers.add_parser(
        "scan",
        help="Discover project memories and create a read-only incremental review run.",
    )
    scan.add_argument("--project", action="append", default=[], help="Explicit absolute project root.")
    scan.add_argument("--ports-file", default=str(default_ports_path()))
    scan.add_argument(
        "--api-url",
        default=None,
        help="Optional AgentsToZ API base URL; falls back to ports.json when unavailable.",
    )
    scan.add_argument("--state-file", default=str(default_state_path()))
    scan.add_argument("--consumer", default="cs-experiencing")
    scan.add_argument("--output", help="Write the complete run bundle atomically to this file.")
    scan.add_argument("--force", action="store_true", help="Review even unchanged projects.")
    scan.add_argument("--no-cwd", action="store_true", help="Do not add the current project.")
    scan.set_defaults(func=command_scan)

    commit = subparsers.add_parser(
        "commit",
        help="Advance one project cursor after its review and memory update succeeded.",
    )
    commit.add_argument("--run-file", required=True)
    commit.add_argument("--memory-id", required=True)
    commit.add_argument("--state-file")
    commit.add_argument("--consumer")
    commit.add_argument("--allow-large-delete", action="store_true")
    commit.set_defaults(func=command_commit)

    backup = subparsers.add_parser(
        "backup",
        help="Back up the scanned memory after verifying it has not changed.",
    )
    backup.add_argument("--run-file", required=True)
    backup.add_argument("--memory-id", required=True)
    backup.set_defaults(func=command_backup)

    diff_memory = subparsers.add_parser(
        "diff-memory",
        help="Compare the current memory with the exact scan-time snapshot.",
    )
    diff_memory.add_argument("--run-file", required=True)
    diff_memory.add_argument("--memory-id", required=True)
    diff_memory.set_defaults(func=command_diff_memory)

    review_complete = subparsers.add_parser(
        "review-complete",
        help="Record reviewed memory hash and durable candidate dispositions.",
    )
    review_complete.add_argument("--run-file", required=True)
    review_complete.add_argument("--memory-id", required=True)
    review_complete.add_argument(
        "--candidate-id",
        action="append",
        default=[],
        help="Durably queued candidate created by this run (repeatable).",
    )
    review_complete.add_argument(
        "--no-reusable-candidates",
        action="store_true",
        help="Attest that review found no cross-project reusable lesson.",
    )
    review_complete.add_argument(
        "--btw-file",
        default=str(Path.home() / ".claude" / ".experiencing-btw.json"),
    )
    review_complete.add_argument(
        "--accept-incomplete-source",
        action="store_true",
        help="Acknowledge that truncated/partial evidence was reviewed with bounded claims.",
    )
    review_complete.add_argument(
        "--accept-history-rebaseline",
        action="store_true",
        help="Acknowledge manual review of a Git history with no common merge-base.",
    )
    review_complete.add_argument(
        "--accept-bootstrap",
        action="store_true",
        help="Acknowledge review of the initial baseline when no cursor exists.",
    )
    review_complete.set_defaults(func=command_review_complete)

    status_parser = subparsers.add_parser("status", help="Show successful training cursors.")
    status_parser.add_argument("--state-file", default=str(default_state_path()))
    status_parser.add_argument("--consumer", default="cs-experiencing")
    status_parser.set_defaults(func=command_status)

    cleanup = subparsers.add_parser("cleanup", help="Remove a completed or abandoned run bundle.")
    cleanup.add_argument("--run-file", required=True)
    cleanup.set_defaults(func=command_cleanup)
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    try:
        return int(args.func(args))
    except (OSError, TrainingError, ValueError) as exc:
        print(
            json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False, indent=2),
            file=sys.stderr,
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
