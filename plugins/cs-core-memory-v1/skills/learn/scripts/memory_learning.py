#!/usr/bin/env python3
"""Bounded, read-only learning intake for AgentsToZ project memories.

The authoritative memory stays in each project's .agent-memory directory. This
helper stores only stable entry/version pointers and dispositions, so periodic
collection is deterministic, idempotent, and requires no model call.
"""

from __future__ import annotations

import argparse
import contextlib
import datetime as dt
import hashlib
import json
import os
import re
import stat
import sys
import tempfile
import unicodedata
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any, Dict, Iterable, Iterator, List, Optional, Sequence, Tuple


STATE_SCHEMA = 2
MAX_CONFIG_BYTES = 128 * 1024
MAX_MANIFEST_BYTES = 512 * 1024
MAX_MEMORY_BYTES = 1024 * 1024
MAX_MANIFEST_PARTS = 256
MAX_STATE_BYTES = 8 * 1024 * 1024
MAX_DISCOVERY_DIRS = 50_000
MAX_PROJECTS = 200
MAX_CANDIDATE_BODY_CHARS = 3_000
MAX_BATCH_BODY_CHARS = 8_000
MAX_RECALL_EXCERPT_CHARS = 600
MAX_RECALL_HITS = 5
FULL_AUDIT_INTERVAL_DAYS = 7
DEFAULT_BOOTSTRAP_LIMIT = 20
ENTRY_ID_RE = re.compile(r"^<!--\s*memory-entry-id:([0-9a-f]{24})\s*-->$", re.I)
DATE_RE = re.compile(r"(?<!\d)(20\d{2}-\d{2}-\d{2})(?!\d)")

TRAINABLE_SECTIONS = {
    "key decisions",
    "strategic patterns",
    "recurring issues",
    "active constraints",
    "contested entries",
    "핵심 결정",
    "전략 패턴",
    "반복 문제",
    "활성 제약",
    "논쟁 항목",
}
CONTESTED_SECTIONS = {"contested entries", "논쟁 항목"}
CONSTRAINT_SECTIONS = {"active constraints", "활성 제약"}
DISCOVERY_PRUNE = {
    ".git", ".hg", ".svn", ".ssh", ".gnupg", ".aws", ".kube",
    ".docker", ".cache", ".Trash", ".claude", ".codex", ".hermes",
    ".venv", "venv", "node_modules", "vendor", "dist", "build",
    "target", "Library", "AppData", "Applications", "System", "Pictures", "Movies",
}
GENERIC_QUERY_TERMS = {
    "memory", "project", "agent", "work", "task", "remember",
    "기억", "프로젝트", "에이전트", "작업", "장기기억", "관련",
}
DISPOSITION_NOTES = {
    "duplicate",
    "merged",
    "project-local",
    "promoted",
    "stale",
    "temporary",
    "unsupported",
}
STATUS_TRANSITIONS = {
    "pending": {"queued", "rejected", "contested"},
    "queued": {"queued", "promoted", "rejected"},
    "contested": {"contested", "queued", "rejected"},
    "promoted": {"promoted"},
    "rejected": {"rejected"},
}


class MemoryLearningError(RuntimeError):
    pass


def utc_now() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat().replace("+00:00", "Z")


def default_state_path() -> Path:
    override = os.environ.get("CS_MEMORY_LEARNING_STATE")
    if override:
        return Path(override).expanduser()
    return Path.home() / ".csncompany" / "state" / "memory-learning.json"


def default_ports_path() -> Path:
    if sys.platform == "darwin":
        return Path.home() / "Library/Application Support/com.portmanager.portmanager/ports.json"
    if os.name == "nt":
        base = os.environ.get("APPDATA") or str(Path.home() / "AppData/Roaming")
        return Path(base) / "com.portmanager.portmanager/ports.json"
    return Path.home() / ".config/com.portmanager.portmanager/ports.json"


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def normalize(value: str) -> str:
    return re.sub(r"\s+", " ", unicodedata.normalize("NFKC", value).casefold()).strip()


def strip_control_chars(value: str) -> str:
    return "".join(
        char for char in value
        if char in "\n\t" or (ord(char) >= 32 and ord(char) != 127)
    )


def redact_secrets(value: str) -> Tuple[str, List[str]]:
    patterns = [
        ("private-key", re.compile(r"-----BEGIN [^-\n]*PRIVATE KEY-----.*?-----END [^-\n]*PRIVATE KEY-----", re.I | re.S)),
        ("openai-key", re.compile(r"\bsk-[A-Za-z0-9_-]{20,}\b")),
        ("github-token", re.compile(r"\b(?:ghp|github_pat)_[A-Za-z0-9_]{20,}\b")),
        ("aws-key", re.compile(r"\bAKIA[0-9A-Z]{16}\b")),
        ("jwt", re.compile(r"\beyJ[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\b")),
        (
            "credential-assignment",
            re.compile(
                r"(?im)\b(?:api[_-]?key|access[_-]?token|auth[_-]?token|password|secret|token)\s*[:=]\s*[\"']?([^\s\"']{16,})"
            ),
        ),
    ]
    clean = strip_control_chars(value)
    found: List[str] = []
    for name, pattern in patterns:
        if pattern.search(clean):
            found.append(name)
            clean = pattern.sub("[REDACTED]", clean)
    return clean, sorted(set(found))


def public_error(error: BaseException) -> str:
    value, _detectors = redact_secrets(str(error))
    return value[:300]


def path_is_within(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
        return True
    except ValueError:
        return False


def read_regular_bytes(path: Path, max_bytes: int) -> Tuple[bytes, os.stat_result]:
    if not path.exists():
        raise MemoryLearningError("required file is missing: %s" % path)
    if path.is_symlink():
        raise MemoryLearningError("symlinked file is unsafe: %s" % path)
    flags = os.O_RDONLY
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    try:
        descriptor = os.open(path, flags)
    except OSError as exc:
        raise MemoryLearningError("could not open file safely: %s" % path) from exc
    try:
        before = os.fstat(descriptor)
        if not stat.S_ISREG(before.st_mode):
            raise MemoryLearningError("memory input is not a regular file: %s" % path)
        if before.st_size > max_bytes:
            raise MemoryLearningError("file exceeds %d-byte limit: %s" % (max_bytes, path))
        chunks: List[bytes] = []
        total = 0
        while True:
            chunk = os.read(descriptor, min(64 * 1024, max_bytes + 1 - total))
            if not chunk:
                break
            chunks.append(chunk)
            total += len(chunk)
            if total > max_bytes:
                raise MemoryLearningError("file exceeds %d-byte limit: %s" % (max_bytes, path))
        after = os.fstat(descriptor)
        identity_before = (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns)
        identity_after = (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns)
        if identity_before != identity_after:
            raise MemoryLearningError("file changed while being read: %s" % path)
        return b"".join(chunks), after
    finally:
        os.close(descriptor)


def assert_file_unchanged(path: Path, observed: os.stat_result) -> None:
    if path.is_symlink():
        raise MemoryLearningError("file became a symlink during composite memory read: %s" % path)
    current = path.stat()
    before_signature = (
        observed.st_dev,
        observed.st_ino,
        observed.st_size,
        observed.st_mtime_ns,
    )
    current_signature = (
        current.st_dev,
        current.st_ino,
        current.st_size,
        current.st_mtime_ns,
    )
    if before_signature != current_signature:
        raise MemoryLearningError("composite project memory changed while being read")


def decode_utf8(payload: bytes, path: Path) -> str:
    try:
        return payload.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise MemoryLearningError("memory input is not UTF-8: %s" % path) from exc


def read_json(path: Path, max_bytes: int) -> Any:
    payload, _ = read_regular_bytes(path, max_bytes)
    try:
        return json.loads(decode_utf8(payload, path))
    except json.JSONDecodeError as exc:
        raise MemoryLearningError("invalid JSON file: %s" % path) from exc


def normalized_body(body: str) -> str:
    value = body.replace("\r\n", "\n").replace("\r", "\n")
    lines = value.split("\n")
    while lines and not lines[0].strip():
        lines.pop(0)
    while lines and not lines[-1].strip():
        lines.pop()
    return unicodedata.normalize("NFC", "\n".join(lines))


def content_version_hash(body: str) -> str:
    return sha256_text(normalized_body(body))[:32]


def legacy_entry_id(section: str, title: str, occurrence: int) -> str:
    base = "%s\n%s" % (normalize(section), normalize(title))
    if occurrence:
        base += "\nduplicate:%d" % occurrence
    return sha256_text(base)[:24]


def knowledge_time_hint(title: str, body: str) -> Optional[str]:
    dates: List[dt.date] = []
    for value in DATE_RE.findall((title + "\n" + body)[:8_000]):
        try:
            dates.append(dt.date.fromisoformat(value))
        except ValueError:
            continue
    return max(dates).isoformat() if dates else None


def visible_structure_lines(lines: Sequence[str]) -> List[str]:
    visible: List[str] = []
    fence_char: Optional[str] = None
    fence_len = 0
    in_comment = False
    for line in lines:
        if fence_char is not None:
            close = re.match(r"^\s{0,3}([`~]{3,})\s*$", line)
            if close and close.group(1)[0] == fence_char and len(close.group(1)) >= fence_len:
                fence_char = None
                fence_len = 0
            visible.append("")
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
        opening = re.match(r"^\s{0,3}(`{3,}|~{3,})", without_comments)
        if opening:
            token = opening.group(1)
            fence_char = token[0]
            fence_len = len(token)
            visible.append("")
        else:
            visible.append(without_comments if not in_comment else "")
    return visible


def parse_memory_document(text: str) -> Dict[str, Any]:
    normalized = text.replace("\r\n", "\n").replace("\r", "\n").lstrip("\ufeff")
    lines = normalized.split("\n")
    visible = visible_structure_lines(lines)
    h2_re = re.compile(r"^##\s+(?!#)(.+?)\s*$")
    h3_re = re.compile(r"^###\s+(?!#)(.+?)\s*$")
    h2_indices = [index for index, line in enumerate(visible) if h2_re.match(line)]
    warnings: List[str] = []
    if not h2_indices:
        return {"valid": False, "warnings": ["memory has no H2 sections"], "entries": [], "documentHash": sha256_text(normalized)}

    entries: List[Dict[str, Any]] = []
    seen_explicit: set[str] = set()
    legacy_occurrences: Dict[str, int] = {}

    def append_entry(section: str, title: str, body_lines: Sequence[str], start: int, end: int, explicit: Optional[str]) -> None:
        body = normalized_body("\n".join(body_lines))
        if not body.strip():
            return
        identity_source = "explicit" if explicit else "legacy"
        if explicit:
            entry_id = explicit.lower()
            if entry_id in seen_explicit:
                warnings.append("duplicate explicit memory entry id: %s" % entry_id)
                return
            seen_explicit.add(entry_id)
        else:
            legacy_key = "%s\n%s" % (normalize(section), normalize(title))
            occurrence = legacy_occurrences.get(legacy_key, 0)
            legacy_occurrences[legacy_key] = occurrence + 1
            entry_id = legacy_entry_id(section, title, occurrence)
        clean_title, _ = redact_secrets(title)
        clean_section, _ = redact_secrets(section)
        section_key = normalize(section)
        semantic_class = "contested" if section_key in CONTESTED_SECTIONS else "accepted"
        entries.append({
            "entryId": entry_id,
            "entryKey": entry_id,
            "identitySource": identity_source,
            "contentVersionHash": content_version_hash(semantic_class + "\0" + body),
            "section": clean_section[:240],
            "title": clean_title[:240],
            "body": body,
            "lineStart": start + 1,
            "lineEnd": end,
            "ordinal": len(entries),
            "trainable": section_key in TRAINABLE_SECTIONS,
            "caution": section_key in CONTESTED_SECTIONS,
            "knowledgeTimeHint": knowledge_time_hint(title, body),
        })

    for position, h2_index in enumerate(h2_indices):
        section_end = h2_indices[position + 1] if position + 1 < len(h2_indices) else len(lines)
        match = h2_re.match(visible[h2_index])
        if not match:
            continue
        section = match.group(1).strip()
        h3_indices = [i for i in range(h2_index + 1, section_end) if h3_re.match(visible[i])]
        prefix_end = h3_indices[0] if h3_indices else section_end

        # Legacy v10 memories may have durable top-level list entries without H3 IDs.
        list_starts = [
            i for i in range(h2_index + 1, prefix_end)
            if re.match(r"^\s{0,3}(?:[-+*]|\d+[.)])\s+", visible[i])
        ]
        for list_position, start in enumerate(list_starts):
            end = list_starts[list_position + 1] if list_position + 1 < len(list_starts) else prefix_end
            first = re.sub(r"^\s{0,3}(?:[-+*]|\d+[.)])\s+", "", visible[start]).strip()
            title = re.sub(r"[`*_]+", "", first)[:160] or "%s item" % section
            append_entry(section, title, lines[start:end], start, end, None)

        for h3_position, start in enumerate(h3_indices):
            end = h3_indices[h3_position + 1] if h3_position + 1 < len(h3_indices) else section_end
            title_match = h3_re.match(visible[start])
            if not title_match:
                continue
            title = title_match.group(1).strip()
            body_lines = list(lines[start + 1:end])
            first_content = next((i for i, line in enumerate(body_lines) if line.strip()), -1)
            explicit: Optional[str] = None
            if first_content >= 0:
                marker = ENTRY_ID_RE.match(body_lines[first_content].strip())
                if marker:
                    explicit = marker.group(1)
                    body_lines.pop(first_content)
            append_entry(section, title, body_lines, start, end, explicit)

    valid = not any("duplicate explicit" in warning for warning in warnings)
    if not entries:
        warnings.append("memory contains no substantive entries")
    return {
        "valid": valid,
        "warnings": warnings,
        "entries": entries,
        "documentHash": sha256_text(normalized),
    }


def validate_relative_source(value: str) -> Path:
    normalized = value.replace("\\", "/")
    source = Path(normalized)
    if not normalized or "\0" in normalized or source.is_absolute() or ".." in source.parts:
        raise MemoryLearningError("sourcePath must stay project-relative")
    return source


def load_project_memory(project_root: Path) -> Dict[str, Any]:
    root = project_root.expanduser().resolve(strict=True)
    memory_dir = root / ".agent-memory"
    if not memory_dir.is_dir():
        raise MemoryLearningError("project memory directory is missing: %s" % memory_dir)
    if memory_dir.is_symlink():
        raise MemoryLearningError("symlinked .agent-memory directory is unsafe: %s" % memory_dir)
    config_path = memory_dir / "config.json"
    config = read_json(config_path, MAX_CONFIG_BYTES)
    if not isinstance(config, dict):
        raise MemoryLearningError("project memory config must be an object")
    memory_id = config.get("memoryId")
    source_value = config.get("sourcePath")
    if not isinstance(memory_id, str) or not memory_id or len(memory_id) > 160:
        raise MemoryLearningError("project memory config has an invalid memoryId")
    if not isinstance(source_value, str):
        raise MemoryLearningError("project memory config has no sourcePath")
    source_relative = validate_relative_source(source_value)
    source_path = root / source_relative
    if source_path.is_symlink():
        raise MemoryLearningError("symlinked memory source is unsafe: %s" % source_path)
    resolved_source = source_path.resolve(strict=True)
    if not path_is_within(resolved_source, root):
        raise MemoryLearningError("memory source escapes project root")

    notes_dir = memory_dir / "notes"
    manifest_path = notes_dir / "manifest.json"
    layout = "single"
    newest_ns = 0
    total_bytes = 0
    observed_files: List[Tuple[Path, os.stat_result]] = []
    if manifest_path.exists() or manifest_path.is_symlink():
        layout = "split"
        if notes_dir.is_symlink() or manifest_path.is_symlink():
            raise MemoryLearningError("symlinked memory manifest is unsafe")
        manifest_payload, manifest_stat = read_regular_bytes(manifest_path, MAX_MANIFEST_BYTES)
        manifest = json.loads(decode_utf8(manifest_payload, manifest_path))
        observed_files.append((manifest_path, manifest_stat))
        if not isinstance(manifest, dict) or manifest.get("version") != 1:
            raise MemoryLearningError("memory manifest has an unsupported schema")
        parts = manifest.get("parts")
        if not isinstance(parts, list) or not parts or len(parts) > MAX_MANIFEST_PARTS:
            raise MemoryLearningError("memory manifest parts are invalid")
        seen_files: set[str] = set()
        payloads: List[bytes] = []
        for part in parts:
            if not isinstance(part, dict) or not isinstance(part.get("file"), str):
                raise MemoryLearningError("memory manifest part is invalid")
            name = part["file"]
            if name in seen_files or name != Path(name).name or name in {".", ".."} or not name.endswith(".md"):
                raise MemoryLearningError("memory manifest contains an unsafe note path")
            seen_files.add(name)
            note_path = notes_dir / name
            payload, note_stat = read_regular_bytes(note_path, MAX_MEMORY_BYTES)
            total_bytes += len(payload)
            if total_bytes > MAX_MEMORY_BYTES:
                raise MemoryLearningError("composed memory exceeds %d-byte limit" % MAX_MEMORY_BYTES)
            newest_ns = max(newest_ns, note_stat.st_mtime_ns)
            payloads.append(payload)
            observed_files.append((note_path, note_stat))
        raw = b"\n\n".join(payloads)
    else:
        raw, source_stat = read_regular_bytes(resolved_source, MAX_MEMORY_BYTES)
        observed_files.append((resolved_source, source_stat))
        newest_ns = source_stat.st_mtime_ns
        total_bytes = len(raw)

    for observed_path, observed_stat in observed_files:
        assert_file_unchanged(observed_path, observed_stat)

    text = decode_utf8(raw, resolved_source)
    _, detectors = redact_secrets(text)
    parsed = parse_memory_document(text)
    modified = dt.datetime.fromtimestamp(newest_ns / 1_000_000_000, tz=dt.timezone.utc).isoformat().replace("+00:00", "Z") if newest_ns else None
    return {
        "memoryId": memory_id,
        "projectRoot": str(root),
        "projectName": root.name,
        "sourcePath": source_relative.as_posix(),
        "memoryPath": str(resolved_source),
        "agent": config.get("agent"),
        "memoryAgentId": config.get("memoryAgentId") or config.get("agentId"),
        "configLastUpdatedAtHintOnly": config.get("lastUpdatedAt"),
        "memoryModifiedAtObservation": modified,
        "layout": layout,
        "bytes": total_bytes,
        "text": text,
        "parsed": parsed,
        "secretDetectors": detectors,
    }


def project_memory_stamp(project_root: Path) -> Dict[str, Any]:
    """Read only config/manifest plus file metadata for cheap periodic polling."""
    root = project_root.expanduser().resolve(strict=True)
    memory_dir = root / ".agent-memory"
    if not memory_dir.is_dir() or memory_dir.is_symlink():
        raise MemoryLearningError("project memory directory is missing or unsafe")
    config_path = memory_dir / "config.json"
    config = read_json(config_path, MAX_CONFIG_BYTES)
    if not isinstance(config, dict):
        raise MemoryLearningError("project memory config must be an object")
    memory_id = config.get("memoryId")
    source_value = config.get("sourcePath")
    if not isinstance(memory_id, str) or not memory_id or len(memory_id) > 160:
        raise MemoryLearningError("project memory config has an invalid memoryId")
    if not isinstance(source_value, str):
        raise MemoryLearningError("project memory config has no sourcePath")
    source_relative = validate_relative_source(source_value)
    source_path = root / source_relative
    if source_path.is_symlink():
        raise MemoryLearningError("symlinked memory source is unsafe")
    resolved_source = source_path.resolve(strict=True)
    if not path_is_within(resolved_source, root):
        raise MemoryLearningError("memory source escapes project root")

    config_stat = config_path.stat()
    stamp_items: List[Tuple[str, int, int]] = [
        (".agent-memory/config.json", config_stat.st_size, config_stat.st_mtime_ns)
    ]
    notes_dir = memory_dir / "notes"
    manifest_path = notes_dir / "manifest.json"
    newest_ns = 0
    layout = "single"
    if manifest_path.exists() or manifest_path.is_symlink():
        layout = "split"
        if notes_dir.is_symlink() or manifest_path.is_symlink():
            raise MemoryLearningError("symlinked memory manifest is unsafe")
        manifest = read_json(manifest_path, MAX_MANIFEST_BYTES)
        if not isinstance(manifest, dict) or manifest.get("version") != 1:
            raise MemoryLearningError("memory manifest has an unsupported schema")
        parts = manifest.get("parts")
        if not isinstance(parts, list) or not parts or len(parts) > MAX_MANIFEST_PARTS:
            raise MemoryLearningError("memory manifest parts are invalid")
        manifest_stat = manifest_path.stat()
        stamp_items.append((".agent-memory/notes/manifest.json", manifest_stat.st_size, manifest_stat.st_mtime_ns))
        seen: set[str] = set()
        total = 0
        for part in parts:
            if not isinstance(part, dict) or not isinstance(part.get("file"), str):
                raise MemoryLearningError("memory manifest part is invalid")
            name = part["file"]
            if name in seen or name != Path(name).name or name in {".", ".."} or not name.endswith(".md"):
                raise MemoryLearningError("memory manifest contains an unsafe note path")
            seen.add(name)
            note = notes_dir / name
            if not note.exists():
                raise MemoryLearningError("required memory note is missing")
            if note.is_symlink():
                raise MemoryLearningError("symlinked memory note is unsafe")
            note_stat = note.stat()
            if not stat.S_ISREG(note_stat.st_mode):
                raise MemoryLearningError("memory note is not a regular file")
            total += note_stat.st_size
            if total > MAX_MEMORY_BYTES:
                raise MemoryLearningError("composed memory exceeds its size limit")
            newest_ns = max(newest_ns, note_stat.st_mtime_ns)
            stamp_items.append((".agent-memory/notes/%s" % name, note_stat.st_size, note_stat.st_mtime_ns))
    else:
        source_stat = resolved_source.stat()
        if not stat.S_ISREG(source_stat.st_mode) or source_stat.st_size > MAX_MEMORY_BYTES:
            raise MemoryLearningError("memory source is not a bounded regular file")
        newest_ns = source_stat.st_mtime_ns
        stamp_items.append((source_relative.as_posix(), source_stat.st_size, source_stat.st_mtime_ns))

    stamp_payload = json.dumps(stamp_items, ensure_ascii=False, separators=(",", ":"))
    return {
        "memoryId": memory_id,
        "projectRoot": str(root),
        "sourcePath": source_relative.as_posix(),
        "layout": layout,
        "fileStamp": sha256_text(stamp_payload),
        "memoryModifiedAtObservation": (
            dt.datetime.fromtimestamp(newest_ns / 1_000_000_000, tz=dt.timezone.utc)
            .isoformat()
            .replace("+00:00", "Z")
            if newest_ns
            else None
        ),
    }


def full_audit_is_recent(value: Any, now: dt.datetime) -> bool:
    if not isinstance(value, str) or not value:
        return False
    try:
        parsed = dt.datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return False
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=dt.timezone.utc)
    age = now - parsed.astimezone(dt.timezone.utc)
    return dt.timedelta(0) <= age < dt.timedelta(days=FULL_AUDIT_INTERVAL_DAYS)


def discover_under(root: Path, max_depth: int = 8) -> Tuple[List[Path], List[str]]:
    if not root.is_absolute():
        raise MemoryLearningError("discovery root must be absolute")
    resolved = root.expanduser().resolve(strict=True)
    found: List[Path] = []
    warnings: List[str] = []
    visited = 0

    def onerror(error: OSError) -> None:
        warnings.append("discovery skipped an unreadable directory")

    for current, directories, _files in os.walk(resolved, topdown=True, onerror=onerror, followlinks=False):
        visited += 1
        if visited > MAX_DISCOVERY_DIRS:
            warnings.append("discovery stopped at the %d-directory safety limit" % MAX_DISCOVERY_DIRS)
            break
        current_path = Path(current)
        depth = len(current_path.relative_to(resolved).parts)
        directories[:] = sorted(
            name for name in directories
            if name not in DISCOVERY_PRUNE and not (current_path / name).is_symlink()
        )
        if depth >= max_depth:
            directories[:] = []
        config = current_path / ".agent-memory" / "config.json"
        if config.is_file() and not config.is_symlink():
            found.append(current_path.resolve())
            directories[:] = [name for name in directories if name != ".agent-memory"]
            if len(found) >= MAX_PROJECTS:
                warnings.append("folder discovery reached its bounded project limit")
                break
    return sorted(set(found)), sorted(set(warnings))


class NoRedirectHandler(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req: Any, fp: Any, code: int, msg: str, headers: Any, newurl: str) -> None:
        return None


def registry_payload(api_url: Optional[str], ports_file: Path) -> Any:
    api_failed = False
    if api_url:
        parsed = urllib.parse.urlparse(api_url)
        if parsed.scheme not in {"http", "https"} or parsed.hostname not in {"127.0.0.1", "localhost", "::1"}:
            raise MemoryLearningError("AgentsToZ API URL must use loopback")
        url = api_url.rstrip("/") + "/api/ports"
        try:
            opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), NoRedirectHandler())
            with opener.open(url, timeout=2.0) as response:
                payload = response.read(8 * 1024 * 1024 + 1)
            if len(payload) > 8 * 1024 * 1024:
                raise MemoryLearningError("AgentsToZ registry response is too large")
            return json.loads(payload.decode("utf-8"))
        except MemoryLearningError:
            raise
        except Exception:
            api_failed = True
    if ports_file.is_file() and not ports_file.is_symlink():
        return read_json(ports_file, 16 * 1024 * 1024)
    if api_failed:
        raise MemoryLearningError("AgentsToZ registry API is unavailable and no ports fallback exists")
    return []


def discover_projects(args: argparse.Namespace) -> Tuple[List[Path], List[str]]:
    roots: set[Path] = set()
    warnings: List[str] = []
    for value in args.project:
        path = Path(value).expanduser()
        if not path.is_absolute() or not path.is_dir():
            warnings.append("explicit project is missing or not absolute")
            continue
        roots.add(path.resolve())
    for value in args.root:
        path = Path(value).expanduser()
        try:
            discovered, found_warnings = discover_under(path, args.max_depth)
            roots.update(discovered)
            warnings.extend(found_warnings)
        except (OSError, MemoryLearningError):
            warnings.append("configured discovery root could not be scanned")
    if not args.no_registry:
        try:
            payload = registry_payload(args.api_url, Path(args.ports_file).expanduser())
            rows = payload.get("ports", []) if isinstance(payload, dict) else payload
            if not isinstance(rows, list):
                raise MemoryLearningError("AgentsToZ ports registry is not an array")
            for row in rows:
                if not isinstance(row, dict) or not isinstance(row.get("folderPath"), str):
                    continue
                path = Path(row["folderPath"]).expanduser()
                if path.is_absolute() and path.is_dir():
                    roots.add(path.resolve())
        except (OSError, ValueError, MemoryLearningError):
            warnings.append("AgentsToZ registry could not be read")
    if not args.no_cwd:
        cwd = Path.cwd().resolve()
        if (cwd / ".agent-memory/config.json").is_file():
            roots.add(cwd)
    ordered = sorted(roots)
    if len(ordered) > MAX_PROJECTS:
        warnings.append("project discovery reached its bounded project limit")
        ordered = ordered[:MAX_PROJECTS]
    return ordered, sorted(set(warnings))


def empty_state() -> Dict[str, Any]:
    return {"schemaVersion": STATE_SCHEMA, "updatedAt": None, "memories": {}}


def validate_state_parent(path: Path, *, create: bool) -> None:
    parent = path.expanduser().parent
    if parent.is_symlink():
        raise MemoryLearningError("state parent must not be a symlink")
    if parent.exists() and not parent.is_dir():
        raise MemoryLearningError("state parent is not a directory")
    if not create:
        return
    probe = parent
    while not probe.exists() and probe != probe.parent:
        probe = probe.parent
    if probe.is_symlink():
        raise MemoryLearningError("state parent must not traverse a symlink")
    parent.mkdir(parents=True, exist_ok=True)
    if parent.is_symlink() or not parent.is_dir():
        raise MemoryLearningError("state parent is unsafe")


def load_state(path: Path) -> Dict[str, Any]:
    path = path.expanduser()
    validate_state_parent(path, create=False)
    if path.is_symlink():
        raise MemoryLearningError("learning state must not be a symlink")
    if not path.exists():
        return empty_state()
    raw = read_json(path, MAX_STATE_BYTES)
    if not isinstance(raw, dict) or raw.get("schemaVersion") != STATE_SCHEMA or not isinstance(raw.get("memories"), dict):
        raise MemoryLearningError("learning state has an incompatible schema")
    return raw


@contextlib.contextmanager
def state_lock(path: Path) -> Iterator[None]:
    lock_path = path.expanduser().with_suffix(path.suffix + ".lock")
    validate_state_parent(lock_path, create=True)
    if lock_path.is_symlink():
        raise MemoryLearningError("state lock must not be a symlink")
    handle = open(lock_path, "a+b")
    try:
        os.chmod(lock_path, 0o600)
    except OSError:
        pass
    try:
        if os.name == "nt":
            import msvcrt
            handle.seek(0, os.SEEK_END)
            if handle.tell() == 0:
                handle.write(b"\0")
                handle.flush()
            handle.seek(0)
            msvcrt.locking(handle.fileno(), msvcrt.LK_LOCK, 1)
        else:
            import fcntl
            fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
        yield
    finally:
        try:
            if os.name == "nt":
                import msvcrt
                handle.seek(0)
                msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                import fcntl
                fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
        finally:
            handle.close()


def atomic_write_state(path: Path, state: Dict[str, Any]) -> None:
    path = path.expanduser()
    validate_state_parent(path, create=True)
    payload = (json.dumps(state, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode("utf-8")
    if len(payload) > MAX_STATE_BYTES:
        raise MemoryLearningError("learning state exceeds its bounded size")
    descriptor, temporary = tempfile.mkstemp(prefix=path.name + ".", dir=str(path.parent))
    try:
        if hasattr(os, "fchmod"):
            os.fchmod(descriptor, 0o600)
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def candidate_id(memory_id: str, entry_id: str, version_hash: str) -> str:
    digest = sha256_text("\0".join((memory_id, entry_id, version_hash)))[:24]
    return "memory-%s" % digest


def entry_priority_rank(entry: Dict[str, Any]) -> int:
    section = normalize(str(entry.get("section", "")))
    if entry.get("caution"):
        rank = 5
    elif section in CONSTRAINT_SECTIONS:
        rank = 0
    elif section in {"key decisions", "핵심 결정"}:
        rank = 1
    elif section in {"strategic patterns", "전략 패턴"}:
        rank = 2
    elif section in {"recurring issues", "반복 문제"}:
        rank = 3
    else:
        rank = 4
    return rank


def source_entry_priority(entry: Dict[str, Any]) -> Tuple[int, int]:
    return entry_priority_rank(entry), int(entry.get("ordinal", 0))


def state_entry(
    entry: Dict[str, Any],
    previous: Optional[Dict[str, Any]],
    now: str,
    bootstrap: bool,
) -> Tuple[Dict[str, Any], bool, bool, bool]:
    version_changed = (
        previous is None
        or previous.get("status") == "removed"
        or previous.get("contentVersionHash") != entry["contentVersionHash"]
    )
    if version_changed:
        current_id = candidate_id("", entry["entryId"], entry["contentVersionHash"])
        # The caller rewrites this with the memory-scoped ID.
        first_observation = previous is None
        bootstrap_queued = bool(first_observation and bootstrap and not entry["caution"])
        result = {
            "entryId": entry["entryId"],
            "contentVersionHash": entry["contentVersionHash"],
            "identitySource": entry["identitySource"],
            "priorityRank": entry_priority_rank(entry),
            "knowledgeTimeHint": entry["knowledgeTimeHint"],
            "caution": bool(entry["caution"]),
            "status": (
                "contested"
                if entry["caution"]
                else "pending"
                if (not first_observation or bootstrap_queued)
                else "observed"
            ),
            "candidateId": current_id,
            "changeKind": "added" if previous is None else "updated",
            "firstObservedAt": previous.get("firstObservedAt", now) if previous else now,
            "versionObservedAt": now,
            "lastObservedAt": now,
        }
        if previous and previous.get("candidateId"):
            result["supersedesCandidateId"] = previous["candidateId"]
        changed_candidate = bool(not first_observation and not entry["caution"])
        return result, changed_candidate, bool(entry["caution"]), bootstrap_queued
    result: Dict[str, Any] = (
        {str(key): value for key, value in previous.items()}
        if isinstance(previous, dict)
        else {}
    )
    result.update({
        "identitySource": entry["identitySource"],
        "priorityRank": entry_priority_rank(entry),
        "knowledgeTimeHint": entry["knowledgeTimeHint"],
        "caution": bool(entry["caution"]),
        "lastObservedAt": now,
    })
    result.pop("section", None)
    result.pop("title", None)
    bootstrap_queued = bool(
        bootstrap
        and result.get("status") == "observed"
        and not entry["caution"]
    )
    if bootstrap_queued:
        result["status"] = "pending"
        result["changeKind"] = "bootstrap"
    return result, False, False, bootstrap_queued


def collect(args: argparse.Namespace) -> Dict[str, Any]:
    project_roots, discovery_warnings = discover_projects(args)
    state_path = Path(args.state_file).expanduser()
    state_before = load_state(state_path)
    now_datetime = dt.datetime.now(dt.timezone.utc)
    now = now_datetime.isoformat().replace("+00:00", "Z")
    inspections: List[Dict[str, Any]] = []
    quarantined: List[Dict[str, Any]] = []
    for root in project_roots:
        try:
            inspections.append(project_memory_stamp(root))
        except (OSError, ValueError, MemoryLearningError) as exc:
            quarantined.append({"projectRoot": str(root), "reason": public_error(exc)})

    by_id: Dict[str, List[Dict[str, Any]]] = {}
    for inspection in inspections:
        by_id.setdefault(inspection["memoryId"], []).append(inspection)
    conflicts: List[Dict[str, Any]] = []
    unique_inspections: List[Dict[str, Any]] = []
    for memory_id, copies in sorted(by_id.items()):
        unique_roots = sorted({copy["projectRoot"] for copy in copies})
        if len(unique_roots) > 1:
            conflicts.append({"memoryId": memory_id, "projectRoots": unique_roots, "reason": "same memoryId exists at multiple roots"})
        else:
            unique_inspections.append(copies[0])
    blocked_memory_ids = {item["memoryId"] for item in conflicts}

    loaded: List[Dict[str, Any]] = []
    unchanged_by_stamp = 0
    bootstrap_history = bool(getattr(args, "bootstrap_history", False))
    bootstrap_budget = max(
        0,
        min(100, int(getattr(args, "bootstrap_limit", DEFAULT_BOOTSTRAP_LIMIT))),
    )
    previous_memories = state_before["memories"]
    existing_pending = sum(
        1
        for memory in previous_memories.values()
        if isinstance(memory, dict)
        for entry in memory.get("entries", {}).values()
        if isinstance(entry, dict) and entry.get("status") == "pending"
    )
    bootstrap_remaining = max(0, bootstrap_budget - existing_pending)
    bootstrap_scan_remaining = bootstrap_remaining
    for inspection in unique_inspections:
        previous = previous_memories.get(inspection["memoryId"], {})
        observed_count = (
            sum(
                1
                for entry in previous.get("entries", {}).values()
                if isinstance(entry, dict) and entry.get("status") == "observed"
            )
            if isinstance(previous, dict) and isinstance(previous.get("entries"), dict)
            else 0
        )
        needs_bootstrap_scan = bool(
            bootstrap_history and bootstrap_scan_remaining > 0 and observed_count > 0
        )
        if needs_bootstrap_scan:
            bootstrap_scan_remaining -= min(bootstrap_scan_remaining, observed_count)
        if (
            isinstance(previous, dict)
            and not previous.get("blockedReason")
            and previous.get("projectRoot") == inspection["projectRoot"]
            and previous.get("fileStamp") == inspection["fileStamp"]
            and full_audit_is_recent(previous.get("lastFullScanAt"), now_datetime)
            and not needs_bootstrap_scan
        ):
            unchanged_by_stamp += 1
            continue
        try:
            project = load_project_memory(Path(inspection["projectRoot"]))
            project["fileStamp"] = inspection["fileStamp"]
            if project["secretDetectors"]:
                quarantined.append({"projectRoot": inspection["projectRoot"], "reason": "secret-indicators", "detectors": project["secretDetectors"]})
            elif not project["parsed"]["valid"]:
                quarantined.append({"projectRoot": inspection["projectRoot"], "reason": "invalid-memory-structure", "warnings": project["parsed"]["warnings"]})
            else:
                loaded.append(project)
        except (OSError, ValueError, MemoryLearningError) as exc:
            quarantined.append({"projectRoot": inspection["projectRoot"], "reason": public_error(exc)})

    accepted = loaded
    new_versions = 0
    contested_versions = 0
    bootstrap_queued = 0
    project_results: List[Dict[str, Any]] = []
    with state_lock(state_path):
        state = load_state(state_path)
        memories = state["memories"]
        state_changed = False
        for blocked_memory_id in blocked_memory_ids:
            blocked_memory = memories.get(blocked_memory_id)
            if isinstance(blocked_memory, dict) and blocked_memory.get("blockedReason") != "duplicate-memory-id":
                blocked_memory["blockedReason"] = "duplicate-memory-id"
                blocked_memory["blockedAt"] = now
                state_changed = True
        for project in accepted:
            memory_id = project["memoryId"]
            for old_memory_id, old_memory in list(memories.items()):
                if (
                    old_memory_id != memory_id
                    and isinstance(old_memory, dict)
                    and old_memory.get("projectRoot") == project["projectRoot"]
                ):
                    del memories[old_memory_id]
            previous_memory = memories.get(memory_id, {})
            previous_entries = previous_memory.get("entries", {}) if isinstance(previous_memory, dict) else {}
            old_removed = previous_memory.get("removed", {}) if isinstance(previous_memory, dict) else {}
            current_entries: Dict[str, Dict[str, Any]] = {}
            project_new = 0
            project_contested = 0
            project_bootstrap = 0
            trainable_entries = sorted(
                (entry for entry in project["parsed"]["entries"] if entry["trainable"]),
                key=source_entry_priority,
            )
            for entry in trainable_entries:
                previous = previous_entries.get(entry["entryId"]) if isinstance(previous_entries, dict) else None
                if previous is None and isinstance(old_removed, dict):
                    previous = old_removed.get(entry["entryId"])
                may_bootstrap = bootstrap_history and bootstrap_remaining > 0
                snapshot, is_new, is_contested, is_bootstrap = state_entry(
                    entry, previous, now, may_bootstrap
                )
                snapshot["candidateId"] = candidate_id(memory_id, entry["entryId"], entry["contentVersionHash"])
                if snapshot.get("supersedesCandidateId") == snapshot["candidateId"]:
                    snapshot.pop("supersedesCandidateId", None)
                if is_new:
                    project_new += 1
                if is_contested:
                    project_contested += 1
                if is_bootstrap:
                    project_bootstrap += 1
                    bootstrap_remaining -= 1
                current_entries[entry["entryId"]] = snapshot

            removed: Dict[str, Dict[str, Any]] = {}
            if isinstance(old_removed, dict):
                removed.update(old_removed)
            for entry_id in current_entries:
                removed.pop(entry_id, None)
            if isinstance(previous_entries, dict):
                for entry_id, previous in previous_entries.items():
                    if entry_id not in current_entries and isinstance(previous, dict):
                        removed[entry_id] = {
                            "contentVersionHash": previous.get("contentVersionHash"),
                            "candidateId": previous.get("candidateId"),
                            "firstObservedAt": previous.get("firstObservedAt"),
                            "status": "removed",
                            "removedAt": now,
                        }
            removed = dict(sorted(removed.items(), key=lambda pair: pair[1].get("removedAt", ""), reverse=True)[:256])
            memories[memory_id] = {
                "projectRoot": project["projectRoot"],
                "projectName": project["projectName"],
                "sourcePath": project["sourcePath"],
                "agent": project.get("agent"),
                "memoryAgentId": project.get("memoryAgentId"),
                "layout": project["layout"],
                "documentHash": project["parsed"]["documentHash"],
                "memoryModifiedAtObservation": project["memoryModifiedAtObservation"],
                "configLastUpdatedAtHintOnly": project["configLastUpdatedAtHintOnly"],
                "lastScannedAt": now,
                "lastFullScanAt": now,
                "fileStamp": project["fileStamp"],
                "entries": current_entries,
                "removed": removed,
            }
            new_versions += project_new
            contested_versions += project_contested
            bootstrap_queued += project_bootstrap
            project_results.append({
                "memoryId": memory_id,
                "projectName": project["projectName"],
                "projectRoot": project["projectRoot"],
                "layout": project["layout"],
                "newVersions": project_new,
                "bootstrapQueued": project_bootstrap,
                "contestedVersions": project_contested,
                "pending": sum(1 for item in current_entries.values() if item.get("status") == "pending"),
            })
        if accepted or state_changed:
            state["updatedAt"] = now
            atomic_write_state(state_path, state)

    final_state = load_state(state_path) if state_path.exists() else empty_state()
    pending_total = 0
    blocked_pending_total = 0
    contested_total = 0
    observed_total = 0
    for memory in final_state["memories"].values():
        blocked = bool(memory.get("blockedReason"))
        for entry in memory.get("entries", {}).values():
            if entry.get("status") == "pending":
                if blocked:
                    blocked_pending_total += 1
                else:
                    pending_total += 1
            contested_total += entry.get("status") == "contested"
            observed_total += entry.get("status") == "observed"
    return {
        "ok": True,
        "stateFile": str(state_path),
        "scanned": len(project_roots),
        "projectsUpdated": len(accepted),
        "unchangedByStamp": unchanged_by_stamp,
        "newVersions": new_versions,
        "bootstrapQueued": bootstrap_queued,
        "contestedVersions": contested_versions,
        "pending": pending_total,
        "blockedPending": blocked_pending_total,
        "contested": contested_total,
        "observed": observed_total,
        "conflicts": len(conflicts),
        "blockedMemories": len(blocked_memory_ids),
        "quarantined": len(quarantined),
        "projects": project_results,
        "conflictDetails": conflicts,
        "quarantineDetails": quarantined,
        "warnings": discovery_warnings,
    }


def priority_key(item: Tuple[str, str, Dict[str, Any], Dict[str, Any]]) -> Tuple[int, int, str, str]:
    _memory_id, _entry_id, entry, _memory = item
    section_rank = int(entry.get("priorityRank", 4))
    if entry.get("changeKind") == "updated":
        section_rank = min(section_rank, 1)
    date_value = entry.get("knowledgeTimeHint") or "0000-00-00"
    date_rank = -int(date_value.replace("-", "")) if re.fullmatch(r"\d{4}-\d{2}-\d{2}", date_value) else 0
    return section_rank, date_rank, str(entry.get("versionObservedAt", "")), str(entry.get("candidateId", ""))


def next_candidates(args: argparse.Namespace) -> Dict[str, Any]:
    state_path = Path(args.state_file).expanduser()
    state = load_state(state_path)
    pending: List[Tuple[str, str, Dict[str, Any], Dict[str, Any]]] = []
    for memory_id, memory in state["memories"].items():
        if not isinstance(memory, dict):
            continue
        if memory.get("blockedReason"):
            continue
        for entry_id, entry in memory.get("entries", {}).items():
            if isinstance(entry, dict) and entry.get("status") == "pending":
                pending.append((memory_id, entry_id, entry, memory))
    pending.sort(key=priority_key)
    limit = max(1, min(20, int(args.limit)))
    candidates: List[Dict[str, Any]] = []
    batch_body_chars = 0
    stale = 0
    project_cache: Dict[str, Optional[Dict[str, Any]]] = {}
    for memory_id, entry_id, snapshot, memory in pending:
        if len(candidates) >= limit:
            break
        root = str(memory.get("projectRoot", ""))
        if root not in project_cache:
            try:
                loaded = load_project_memory(Path(root))
                if loaded["memoryId"] != memory_id or loaded["secretDetectors"] or not loaded["parsed"]["valid"]:
                    loaded = None
                project_cache[root] = loaded
            except (OSError, ValueError, MemoryLearningError):
                project_cache[root] = None
        project = project_cache[root]
        if project is None:
            stale += 1
            continue
        current = next((entry for entry in project["parsed"]["entries"] if entry["entryId"] == entry_id), None)
        if current is None or current["contentVersionHash"] != snapshot.get("contentVersionHash"):
            stale += 1
            continue
        safe_body, detectors = redact_secrets(current["body"])
        if detectors:
            stale += 1
            continue
        remaining_body_chars = MAX_BATCH_BODY_CHARS - batch_body_chars
        if remaining_body_chars <= 0:
            break
        body_limit = min(MAX_CANDIDATE_BODY_CHARS, remaining_body_chars)
        bounded_body = safe_body[:body_limit]
        batch_body_chars += len(bounded_body)
        candidates.append({
            "candidateId": snapshot["candidateId"],
            "memoryId": memory_id,
            "memoryAgentId": memory.get("memoryAgentId"),
            "memoryAgent": memory.get("agent"),
            "projectName": memory.get("projectName"),
            "projectRoot": root,
            "entryId": entry_id,
            "contentVersionHash": current["contentVersionHash"],
            "identitySource": current["identitySource"],
            "section": current["section"],
            "title": current["title"],
            "changeKind": snapshot.get("changeKind"),
            "knowledgeTimeHint": current["knowledgeTimeHint"],
            "versionObservedAt": snapshot.get("versionObservedAt"),
            "memoryModifiedAtObservationOnly": project["memoryModifiedAtObservation"],
            "caution": current["caution"],
            "body": bounded_body,
            "bodyTruncated": len(safe_body) > body_limit,
            "sourceRunId": "memory:%s" % snapshot["candidateId"],
            "sourceRange": "entry:%s@%s" % (entry_id, current["contentVersionHash"]),
        })
    return {
        "ok": True,
        "stateFile": str(state_path),
        "candidates": candidates,
        "returned": len(candidates),
        "pending": len(pending),
        "hasMore": len(pending) > len(candidates),
        "stale": stale,
    }


def resolve_candidate(args: argparse.Namespace) -> Dict[str, Any]:
    allowed = {"queued", "promoted", "rejected", "contested"}
    if args.status not in allowed:
        raise MemoryLearningError("candidate status must be one of: %s" % ", ".join(sorted(allowed)))
    state_path = Path(args.state_file).expanduser()
    with state_lock(state_path):
        state = load_state(state_path)
        matches: List[Tuple[str, str, Dict[str, Any], Dict[str, Any]]] = []
        for memory_id, memory in state["memories"].items():
            for entry_id, entry in memory.get("entries", {}).items():
                if isinstance(entry, dict) and entry.get("candidateId") == args.candidate_id:
                    matches.append((memory_id, entry_id, entry, memory))
        if len(matches) != 1:
            raise MemoryLearningError("candidate id must exist exactly once")
        memory_id, entry_id, target, memory = matches[0]
        if memory.get("blockedReason"):
            raise MemoryLearningError("candidate memory is blocked; resolve the memoryId conflict first")
        current_project = load_project_memory(Path(str(memory.get("projectRoot", ""))))
        if (
            current_project["memoryId"] != memory_id
            or current_project["secretDetectors"]
            or not current_project["parsed"]["valid"]
        ):
            raise MemoryLearningError("project memory changed or became unsafe after collection")
        current_entry = next(
            (
                entry
                for entry in current_project["parsed"]["entries"]
                if entry["entryId"] == entry_id
            ),
            None,
        )
        if (
            current_entry is None
            or current_entry["contentVersionHash"] != target.get("contentVersionHash")
        ):
            raise MemoryLearningError("memory entry changed after collection; collect again")
        if current_entry["caution"] and args.status in {"queued", "promoted"}:
            raise MemoryLearningError("contested memory entries cannot be queued or promoted")
        current_status = str(target.get("status", "pending"))
        if args.status not in STATUS_TRANSITIONS.get(current_status, set()):
            raise MemoryLearningError(
                "invalid candidate status transition: %s -> %s" % (current_status, args.status)
            )
        target["status"] = args.status
        target["resolvedAt"] = utc_now()
        if args.note:
            target["dispositionNote"] = strip_control_chars(args.note).strip()[:300]
        if args.learning_id:
            target["learningId"] = strip_control_chars(args.learning_id).strip()[:160]
        state["updatedAt"] = target["resolvedAt"]
        atomic_write_state(state_path, state)
    return {"ok": True, "candidateId": args.candidate_id, "status": args.status}


def query_terms(query: str) -> List[str]:
    terms = re.findall(r"[^\W_]{2,}", normalize(query), flags=re.UNICODE)
    return list(dict.fromkeys(term for term in terms if term not in GENERIC_QUERY_TERMS))[:24]


def recall(args: argparse.Namespace) -> Dict[str, Any]:
    project = load_project_memory(Path(args.project))
    if project["secretDetectors"]:
        raise MemoryLearningError("project memory is quarantined by secret indicators")
    if not project["parsed"]["valid"]:
        raise MemoryLearningError("project memory structure is invalid")
    terms = query_terms(args.query)
    limit = max(1, min(MAX_RECALL_HITS, int(args.limit)))
    constraint_scored: List[Tuple[int, int, Dict[str, Any]]] = []
    topical_scored: List[Tuple[int, int, Dict[str, Any]]] = []
    for entry in project["parsed"]["entries"]:
        if not entry["trainable"]:
            continue
        title = normalize(entry["title"])
        section = normalize(entry["section"])
        body = normalize(entry["body"])
        matched = [term for term in terms if term in title or term in section or term in body]
        is_constraint = section in CONSTRAINT_SECTIONS
        if not matched and not is_constraint:
            continue
        score = 0
        normalized_query = normalize(args.query)
        if title == normalized_query:
            score += 80
        elif normalized_query in title or title in normalized_query:
            score += 45
        for term in matched:
            if term in title:
                score += 18
            if term in section:
                score += 8
            if term in body:
                score += 3
        if is_constraint:
            score += 50
        if entry["caution"]:
            score -= 10
        ranked = (
            score,
            entry["ordinal"],
            {
                **entry,
                "matchedTerms": matched,
                "selectionReason": "active-constraint" if is_constraint else "topical",
            },
        )
        (constraint_scored if is_constraint else topical_scored).append(ranked)
    constraint_scored.sort(key=lambda item: (-item[0], item[1]))
    topical_scored.sort(key=lambda item: (-item[0], item[1]))
    selected = constraint_scored[: min(2, limit)]
    selected.extend(topical_scored[: max(0, limit - len(selected))])
    hits: List[Dict[str, Any]] = []
    for score, _ordinal, entry in selected:
        safe_body, _ = redact_secrets(entry["body"])
        compact = re.sub(r"\n{3,}", "\n\n", safe_body).strip()
        hits.append({
            "entryId": entry["entryId"],
            "contentVersionHash": entry["contentVersionHash"],
            "identitySource": entry["identitySource"],
            "section": entry["section"],
            "title": entry["title"],
            "score": score,
            "selectionReason": entry["selectionReason"],
            "matchedTerms": entry["matchedTerms"],
            "knowledgeTimeHint": entry["knowledgeTimeHint"],
            "memoryModifiedAtObservationOnly": project["memoryModifiedAtObservation"],
            "caution": entry["caution"],
            "excerpt": compact[:MAX_RECALL_EXCERPT_CHARS],
        })
    return {
        "ok": True,
        "memoryId": project["memoryId"],
        "memoryAgentId": project.get("memoryAgentId"),
        "memoryAgent": project.get("agent"),
        "projectRoot": project["projectRoot"],
        "hits": hits,
    }


def status(args: argparse.Namespace) -> Dict[str, Any]:
    state = load_state(Path(args.state_file))
    counts: Dict[str, int] = {}
    blocked_memories = 0
    actionable_pending = 0
    memories: List[Dict[str, Any]] = []
    for memory_id, memory in sorted(state["memories"].items()):
        blocked_memories += bool(memory.get("blockedReason"))
        local: Dict[str, int] = {}
        for entry in memory.get("entries", {}).values():
            value = str(entry.get("status", "unknown"))
            counts[value] = counts.get(value, 0) + 1
            local[value] = local.get(value, 0) + 1
            if value == "pending" and not memory.get("blockedReason"):
                actionable_pending += 1
        memories.append({
            "memoryId": memory_id,
            "projectName": memory.get("projectName"),
            "projectRoot": memory.get("projectRoot"),
            "lastScannedAt": memory.get("lastScannedAt"),
            "blockedReason": memory.get("blockedReason"),
            "statuses": local,
        })
    return {"ok": True, "stateFile": str(Path(args.state_file).expanduser()), "updatedAt": state.get("updatedAt"), "blockedMemories": blocked_memories, "actionablePending": actionable_pending, "statuses": counts, "memories": memories}


def add_discovery_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--project", action="append", default=[], help="Explicit absolute project root (repeatable).")
    parser.add_argument("--root", action="append", default=[], help="Bounded folder discovery root (repeatable).")
    parser.add_argument("--max-depth", type=int, default=8)
    parser.add_argument("--ports-file", default=str(default_ports_path()))
    parser.add_argument("--api-url")
    parser.add_argument("--no-registry", action="store_true")
    parser.add_argument("--no-cwd", action="store_true")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Idempotent AgentsToZ memory-change intake and bounded recall.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    collect_parser = subparsers.add_parser("collect", help="Detect memory entry-version changes without an LLM call.")
    collect_parser.add_argument("--state-file", default=str(default_state_path()))
    collect_parser.add_argument(
        "--quiet",
        action="store_true",
        help="Print nothing when no new versions, conflicts, or quarantines were found.",
    )
    collect_parser.add_argument(
        "--bootstrap-history",
        action="store_true",
        help="Queue a bounded set of observed history; periodic collectors leave existing history as a baseline.",
    )
    collect_parser.add_argument(
        "--bootstrap-limit",
        type=int,
        default=DEFAULT_BOOTSTRAP_LIMIT,
        help="Maximum observed historical entries to queue in this explicit collection (max 100).",
    )
    add_discovery_arguments(collect_parser)
    collect_parser.set_defaults(func=collect)

    next_parser = subparsers.add_parser("next", help="Read a bounded batch of current pending entry versions.")
    next_parser.add_argument("--state-file", default=str(default_state_path()))
    next_parser.add_argument("--limit", type=int, default=5)
    next_parser.set_defaults(func=next_candidates)

    resolve_parser = subparsers.add_parser("resolve", help="Record one candidate's durable disposition.")
    resolve_parser.add_argument("--state-file", default=str(default_state_path()))
    resolve_parser.add_argument("--candidate-id", required=True)
    resolve_parser.add_argument("--status", required=True)
    resolve_parser.add_argument("--note", choices=sorted(DISPOSITION_NOTES), default="")
    resolve_parser.add_argument("--learning-id", default="")
    resolve_parser.set_defaults(func=resolve_candidate)

    recall_parser = subparsers.add_parser("recall", help="Recall at most five current project-memory entries for a goal.")
    recall_parser.add_argument("--project", required=True)
    recall_parser.add_argument("--query", required=True)
    recall_parser.add_argument("--limit", type=int, default=5)
    recall_parser.set_defaults(func=recall)

    status_parser = subparsers.add_parser("status", help="Show compact learning intake state.")
    status_parser.add_argument("--state-file", default=str(default_state_path()))
    status_parser.set_defaults(func=status)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    try:
        result = args.func(args)
        quiet_no_change = (
            getattr(args, "quiet", False)
            and args.command == "collect"
            and result.get("newVersions", 0) == 0
            and result.get("bootstrapQueued", 0) == 0
            and result.get("contestedVersions", 0) == 0
            and result.get("conflicts", 0) == 0
            and result.get("quarantined", 0) == 0
            and not result.get("warnings")
        )
        if not quiet_no_change:
            print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    except (OSError, ValueError, MemoryLearningError) as exc:
        print(json.dumps({"ok": False, "error": public_error(exc)}, ensure_ascii=False, indent=2), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
