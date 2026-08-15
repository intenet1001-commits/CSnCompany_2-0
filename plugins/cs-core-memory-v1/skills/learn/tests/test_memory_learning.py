from __future__ import annotations

import contextlib
import copy
import importlib.util
import json
import os
import re
import shutil
import tempfile
import threading
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from unittest import mock

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "memory_learning.py"
SPEC = importlib.util.spec_from_file_location("memory_learning", SCRIPT)
assert SPEC and SPEC.loader
MEMORY = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MEMORY)

MEMORY_ID = "00000000-0000-4000-8000-000000000001"
ENTRY_A = "111111111111111111111111"
ENTRY_B = "222222222222222222222222"


def document(
    decision_title: str = "Keep local memory authoritative",
    decision_body: str = "- decision: Local memory is authoritative.\n- first_seen: 2026-08-01",
    decision_section: str = "Key Decisions",
) -> str:
    return f"""# Project Core Memory

**Project**: Fixture

## Project Identity

- Purpose: Fixture memory.

## {decision_section}

### {decision_title}
<!-- memory-entry-id:{ENTRY_A} -->

{decision_body}

## Active Constraints

### Never persist secrets
<!-- memory-entry-id:{ENTRY_B} -->

- constraint: Never store credentials in learned skills.
- first_seen: 2026-08-10

## Contested Entries

### Whether the legacy path is still active
<!-- memory-entry-id:333333333333333333333333 -->

- evidence: Conflicting observations remain.
- first_seen: 2026-07-01
"""


def make_project(root: Path, memory_id: str = MEMORY_ID, split: bool = False) -> Path:
    memory_dir = root / ".agent-memory"
    memory_dir.mkdir(parents=True)
    (memory_dir / "config.json").write_text(json.dumps({
        "schemaVersion": 1,
        "memoryId": memory_id,
        "sourcePath": ".agent-memory/CORE.md",
        "agent": "claude",
        "lastUpdatedAt": "2026-08-10T00:00:00.000Z",
    }), encoding="utf-8")
    value = document()
    if not split:
        (memory_dir / "CORE.md").write_text(value, encoding="utf-8")
        return root

    starts = [0, value.index("## Key Decisions"), value.index("## Active Constraints"), value.index("## Contested Entries")]
    ends = starts[1:] + [len(value)]
    names = ["00-header.md", "01-key.md", "02-constraints.md", "03-contested.md"]
    titles = [None, "Key Decisions", "Active Constraints", "Contested Entries"]
    notes = memory_dir / "notes"
    notes.mkdir()
    manifest = []
    for name, title, start, end in zip(names, titles, starts, ends):
        text = value[start:end]
        (notes / name).write_text(text, encoding="utf-8")
        manifest.append({"file": name, "title": title, "entries": [], "bytes": len(text.encode())})
    (notes / "manifest.json").write_text(
        json.dumps({"version": 1, "parts": manifest}), encoding="utf-8"
    )
    (memory_dir / "CORE.md").write_text(
        "# Project Core Memory\n\n## 목차\n\n- generated index only\n", encoding="utf-8"
    )
    return root


class ParserTests(unittest.TestCase):
    def test_identity_survives_title_and_section_move(self) -> None:
        before = MEMORY.parse_memory_document(document())
        after = MEMORY.parse_memory_document(document(
            decision_title="Local memory remains authoritative",
            decision_section="Strategic Patterns",
        ))
        left = next(x for x in before["entries"] if x["entryId"] == ENTRY_A)
        right = next(x for x in after["entries"] if x["entryId"] == ENTRY_A)
        self.assertEqual(left["contentVersionHash"], right["contentVersionHash"])
        self.assertNotEqual(left["title"], right["title"])

    def test_body_edit_advances_version_and_extracts_time_hint(self) -> None:
        before = MEMORY.parse_memory_document(document())
        after = MEMORY.parse_memory_document(document(
            decision_body="- decision: Revised rule.\n- first_seen: 2026-08-12"
        ))
        left = next(x for x in before["entries"] if x["entryId"] == ENTRY_A)
        right = next(x for x in after["entries"] if x["entryId"] == ENTRY_A)
        self.assertEqual(left["entryId"], right["entryId"])
        self.assertNotEqual(left["contentVersionHash"], right["contentVersionHash"])
        self.assertEqual(right["knowledgeTimeHint"], "2026-08-12")

    def test_crossing_the_contested_boundary_changes_version(self) -> None:
        accepted = MEMORY.parse_memory_document(document("Policy"))
        contested = MEMORY.parse_memory_document(document(
            "Policy",
            decision_section="Contested Entries",
        ))
        accepted_hash = next(
            item["contentVersionHash"] for item in accepted["entries"] if item["entryId"] == ENTRY_A
        )
        contested_hash = next(
            item["contentVersionHash"] for item in contested["entries"] if item["entryId"] == ENTRY_A
        )
        self.assertNotEqual(accepted_hash, contested_hash)

    def test_fenced_heading_is_ignored_and_duplicate_id_fails(self) -> None:
        fenced = document(decision_body=f"""- decision: Literal example.
```md
### Fake
<!-- memory-entry-id:aaaaaaaaaaaaaaaaaaaaaaaa -->
```
- first_seen: 2026-08-01""")
        parsed = MEMORY.parse_memory_document(fenced)
        self.assertNotIn("aaaaaaaaaaaaaaaaaaaaaaaa", {x["entryId"] for x in parsed["entries"]})
        duplicate = document() + f"\n## Strategic Patterns\n### Duplicate\n<!-- memory-entry-id:{ENTRY_A} -->\n- duplicate\n"
        invalid = MEMORY.parse_memory_document(duplicate)
        self.assertFalse(invalid["valid"])
        self.assertTrue(any("duplicate" in warning for warning in invalid["warnings"]))

    def test_empty_explicit_id_is_retained_as_a_non_trainable_placeholder(self) -> None:
        parsed = MEMORY.parse_memory_document(document(decision_body=""))
        placeholder = next(
            item for item in parsed["entries"] if item["entryId"] == ENTRY_A
        )
        self.assertFalse(placeholder["substantive"])
        self.assertFalse(placeholder["trainable"])
        self.assertTrue(placeholder["trackable"])

    def test_high_entropy_detector_ignores_repository_paths_and_hashes(self) -> None:
        safe_values = [
            "intenet1001-commits/CSnCompany_2-0",
            "archive/CSnCompany_2-0/plugins/cache/versioned",
            "0123456789abcdef" * 4,
        ]
        for value in safe_values:
            redacted, detectors = MEMORY.redact_secrets(value)
            self.assertEqual(detectors, [])
            self.assertEqual(redacted, value)


class ProjectReadTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)

    def tearDown(self) -> None:
        self.temp.cleanup()

    def test_windows_state_guard_contract_is_no_reparse_and_no_delete_share(self) -> None:
        self.assertTrue(MEMORY.WINDOWS_FILE_FLAG_OPEN_REPARSE_POINT)
        self.assertEqual(
            MEMORY.WINDOWS_STATE_SHARE_MODE & MEMORY.WINDOWS_FILE_SHARE_DELETE,
            0,
        )

    def test_composite_snapshot_verifier_detects_replaced_file(self) -> None:
        path = self.root / "note.md"
        path.write_text("before", encoding="utf-8")
        _payload, observed = MEMORY.read_regular_bytes(path, 100)
        replacement = self.root / "replacement.md"
        replacement.write_text("after", encoding="utf-8")
        replacement.replace(path)
        with self.assertRaisesRegex(MEMORY.MemoryLearningError, "changed"):
            MEMORY.assert_file_unchanged(path, observed)

    def test_split_manifest_composes_notes_not_generated_index(self) -> None:
        project = make_project(self.root / "project", split=True)
        loaded = MEMORY.load_project_memory(project)
        self.assertEqual(loaded["layout"], "split")
        self.assertEqual(loaded["text"], document())
        self.assertIn("Keep local memory authoritative", loaded["text"])
        self.assertNotIn("generated index only", loaded["text"])
        self.assertEqual({
            x["entryId"] for x in loaded["parsed"]["entries"] if x["trainable"]
        }, {
            ENTRY_A, ENTRY_B, "333333333333333333333333"
        })

    def test_missing_or_escaping_split_note_fails_closed(self) -> None:
        project = make_project(self.root / "project", split=True)
        note = project / ".agent-memory/notes/01-key.md"
        note.unlink()
        with self.assertRaisesRegex(MEMORY.MemoryLearningError, "missing"):
            MEMORY.load_project_memory(project)
        project = make_project(self.root / "other", split=True)
        path = project / ".agent-memory/notes/manifest.json"
        manifest = json.loads(path.read_text(encoding="utf-8"))
        manifest["parts"][0]["file"] = "../CORE.md"
        path.write_text(json.dumps(manifest), encoding="utf-8")
        with self.assertRaisesRegex(MEMORY.MemoryLearningError, "manifest"):
            MEMORY.load_project_memory(project)

    @unittest.skipIf(os.name == "nt", "symlink creation varies on Windows")
    def test_symlinked_note_fails_closed(self) -> None:
        project = make_project(self.root / "project", split=True)
        note = project / ".agent-memory/notes/01-key.md"
        target = self.root / "outside.md"
        target.write_text("outside", encoding="utf-8")
        note.unlink()
        note.symlink_to(target)
        with self.assertRaisesRegex(MEMORY.MemoryLearningError, "symlink"):
            MEMORY.load_project_memory(project)

    @unittest.skipIf(os.name == "nt", "symlink privileges differ on Windows")
    def test_symlinked_state_parent_is_rejected(self) -> None:
        project = make_project(self.root / "state-parent", "memory-state-parent")
        outside = self.root / "outside-state"
        outside.mkdir()
        linked_parent = self.root / "linked-state"
        linked_parent.symlink_to(outside, target_is_directory=True)
        args = MEMORY.build_parser().parse_args([
            "collect", "--project", str(project), "--state-file", str(linked_parent / "state.json"),
            "--no-cwd", "--no-registry",
        ])
        with self.assertRaisesRegex(MEMORY.MemoryLearningError, "state parent"):
            MEMORY.collect(args)

    @unittest.skipIf(os.name == "nt", "symlink privileges differ on Windows")
    def test_state_parent_rejects_a_symlinked_ancestor(self) -> None:
        target = self.root / "real-state" / "nested"
        target.mkdir(parents=True)
        linked = self.root / "linked-ancestor"
        linked.symlink_to(self.root / "real-state", target_is_directory=True)
        state = linked / "nested" / "state.json"
        with self.assertRaisesRegex(MEMORY.MemoryLearningError, "state parent"):
            MEMORY.load_state(state)

    @unittest.skipIf(os.name == "nt", "symlink privileges differ on Windows")
    def test_state_write_rejects_parent_rebinding_after_validation(self) -> None:
        parent = self.root / "state-write-parent"
        parent.mkdir()
        parked = self.root / "state-write-parent-original"
        outside = self.root / "state-write-outside"
        outside.mkdir()
        state = parent / "state.json"
        original_validate = MEMORY.validate_state_parent
        rebound = False

        def rebind_after_validation(path: Path, *, create: bool) -> None:
            nonlocal rebound
            original_validate(path, create=create)
            if not rebound:
                parent.rename(parked)
                parent.symlink_to(outside, target_is_directory=True)
                rebound = True

        with mock.patch.object(
            MEMORY,
            "validate_state_parent",
            side_effect=rebind_after_validation,
        ):
            with self.assertRaisesRegex(MEMORY.MemoryLearningError, "state parent"):
                MEMORY.atomic_write_state(state, MEMORY.empty_state())
        self.assertFalse((outside / "state.json").exists())

    @unittest.skipIf(os.name == "nt", "symlink privileges differ on Windows")
    def test_state_lock_rejects_parent_rebinding_after_validation(self) -> None:
        parent = self.root / "state-lock-parent"
        parent.mkdir()
        parked = self.root / "state-lock-parent-original"
        outside = self.root / "state-lock-outside"
        outside.mkdir()
        state = parent / "state.json"
        original_validate = MEMORY.validate_state_parent
        rebound = False

        def rebind_after_validation(path: Path, *, create: bool) -> None:
            nonlocal rebound
            original_validate(path, create=create)
            if not rebound:
                parent.rename(parked)
                parent.symlink_to(outside, target_is_directory=True)
                rebound = True

        with mock.patch.object(
            MEMORY,
            "validate_state_parent",
            side_effect=rebind_after_validation,
        ):
            with self.assertRaisesRegex(MEMORY.MemoryLearningError, "state parent"):
                with MEMORY.state_lock(state):
                    pass
        self.assertFalse((outside / "state.json.lock").exists())

    def test_oversize_memory_fails_closed(self) -> None:
        project = make_project(self.root / "project")
        (project / ".agent-memory/CORE.md").write_text(
            "x" * (MEMORY.MAX_MEMORY_BYTES + 1), encoding="utf-8"
        )
        with self.assertRaisesRegex(MEMORY.MemoryLearningError, "limit"):
            MEMORY.load_project_memory(project)

    def test_unknown_state_schema_is_not_overwritten(self) -> None:
        project = make_project(self.root / "project")
        state = self.root / "state.json"
        original = '{"schemaVersion":999,"sentinel":"keep"}\n'
        state.write_text(original, encoding="utf-8")
        args = MEMORY.build_parser().parse_args([
            "collect", "--project", str(project), "--state-file", str(state),
            "--no-cwd", "--no-registry",
        ])
        with self.assertRaisesRegex(MEMORY.MemoryLearningError, "incompatible schema"):
            MEMORY.collect(args)
        self.assertEqual(state.read_text(encoding="utf-8"), original)

    def test_explicit_registry_outage_is_not_reported_as_an_empty_registry(self) -> None:
        opener = mock.Mock()
        opener.open.side_effect = OSError("offline")
        with mock.patch.object(MEMORY.urllib.request, "build_opener", return_value=opener):
            with self.assertRaisesRegex(MEMORY.MemoryLearningError, "unavailable"):
                MEMORY.registry_payload(
                    "http://127.0.0.1:3001",
                    self.root / "missing-ports.json",
                )


class IncrementalTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.project = make_project(self.root / "project")
        self.state = self.root / "state.json"

    def tearDown(self) -> None:
        self.temp.cleanup()

    def args(self, command: str, *extra: str):
        base = [command, "--state-file", str(self.state)]
        if command == "collect":
            base += [
                "--project", str(self.project), "--no-cwd", "--no-registry",
                "--bootstrap-history",
            ]
        return MEMORY.build_parser().parse_args([*base, *extra])

    def test_default_first_collection_is_a_zero_backlog_baseline(self) -> None:
        baseline_args = MEMORY.build_parser().parse_args([
            "collect", "--project", str(self.project), "--state-file", str(self.state),
            "--no-cwd", "--no-registry",
        ])
        baseline = MEMORY.collect(baseline_args)
        self.assertEqual(baseline["newVersions"], 0)
        self.assertEqual(baseline["pending"], 0)
        self.assertEqual(baseline["observed"], 2)

        bootstrap_args = MEMORY.build_parser().parse_args([
            "collect", "--project", str(self.project), "--state-file", str(self.state),
            "--no-cwd", "--no-registry", "--bootstrap-history",
        ])
        bootstrap = MEMORY.collect(bootstrap_args)
        self.assertEqual(bootstrap["bootstrapQueued"], 2)
        self.assertEqual(bootstrap["pending"], 2)

    def test_user_limits_cannot_exceed_the_documented_hard_caps(self) -> None:
        with self.assertRaisesRegex(MEMORY.MemoryLearningError, "between 0 and 20"):
            MEMORY.collect(self.args("collect", "--bootstrap-limit", "21"))
        MEMORY.collect(self.args("collect"))
        with self.assertRaisesRegex(MEMORY.MemoryLearningError, "between 1 and 5"):
            MEMORY.next_candidates(self.args("next", "--limit", "6"))

    def test_filling_an_empty_stable_id_becomes_a_pending_change(self) -> None:
        core = self.project / ".agent-memory/CORE.md"
        core.write_text(document(decision_body=""), encoding="utf-8")
        first = MEMORY.collect(self.args("collect"))
        self.assertEqual(first["newVersions"], 0)
        placeholder = MEMORY.load_state(self.state)["memories"][MEMORY_ID]["entries"][ENTRY_A]
        self.assertEqual(placeholder["status"], "placeholder")

        core.write_text(
            document(decision_body="- decision: Filled after the stable ID was reserved."),
            encoding="utf-8",
        )
        changed = MEMORY.collect(self.args("collect"))
        current = MEMORY.load_state(self.state)["memories"][MEMORY_ID]["entries"][ENTRY_A]
        self.assertEqual(changed["newVersions"], 1)
        self.assertEqual(current["status"], "pending")
        self.assertEqual(current["changeKind"], "filled")
        self.assertNotIn("supersedesCandidateId", current)
        filled_candidate = current["candidateId"]

        core.write_text(document(decision_body=""), encoding="utf-8")
        MEMORY.collect(self.args("collect"))
        current = MEMORY.load_state(self.state)["memories"][MEMORY_ID]["entries"][ENTRY_A]
        self.assertEqual(current["status"], "placeholder")
        self.assertEqual(current["changeKind"], "cleared")
        candidates = MEMORY.next_candidates(self.args("next", "--limit", "5"))["candidates"]
        self.assertNotIn(ENTRY_A, {item["entryId"] for item in candidates})

        core.write_text(
            document(decision_body="- decision: Filled after the stable ID was reserved."),
            encoding="utf-8",
        )
        refilled = MEMORY.collect(self.args("collect"))
        current = MEMORY.load_state(self.state)["memories"][MEMORY_ID]["entries"][ENTRY_A]
        self.assertEqual(refilled["newVersions"], 1)
        self.assertEqual(current["status"], "pending")
        self.assertEqual(current["changeKind"], "filled")
        self.assertEqual(current["candidateId"], filled_candidate)
        self.assertNotIn("supersedesCandidateId", current)
        self.assertEqual(MEMORY.collect(self.args("collect"))["newVersions"], 0)

    def test_collect_is_idempotent_and_stores_no_memory_body(self) -> None:
        first = MEMORY.collect(self.args("collect"))
        with mock.patch.object(
            MEMORY,
            "load_project_memory",
            wraps=MEMORY.load_project_memory,
        ) as full_reader:
            second = MEMORY.collect(self.args("collect"))
        self.assertEqual(first["newVersions"], 0)
        self.assertEqual(first["bootstrapQueued"], 2)
        self.assertEqual(second["newVersions"], 0)
        self.assertEqual(second["pending"], 2)
        self.assertEqual(second["unchangedByStamp"], 1)
        full_reader.assert_not_called()
        state_text = self.state.read_text(encoding="utf-8")
        self.assertNotIn("Local memory is authoritative", state_text)
        self.assertNotIn("Store project memory locally", state_text)
        self.assertNotIn("Never store credentials", state_text)
        if os.name != "nt":
            self.assertEqual(self.state.stat().st_mode & 0o777, 0o600)

    def test_concurrent_collectors_converge_on_one_candidate_per_version(self) -> None:
        def run_once(_index: int) -> dict:
            return MEMORY.collect(self.args("collect"))

        with ThreadPoolExecutor(max_workers=4) as executor:
            list(executor.map(run_once, range(8)))
        entries = MEMORY.load_state(self.state)["memories"][MEMORY_ID]["entries"]
        self.assertEqual(len(entries), 3)
        self.assertEqual(len({entry["candidateId"] for entry in entries.values()}), 3)

    def test_slow_collector_cannot_overwrite_a_newer_source_snapshot(self) -> None:
        core = self.project / ".agent-memory/CORE.md"
        original = MEMORY.load_project_memory(self.project)
        original_hash = next(
            entry["contentVersionHash"]
            for entry in original["parsed"]["entries"]
            if entry["entryId"] == ENTRY_A
        )
        changed_text = document(
            decision_body="- decision: Newer concurrent version.\n- first_seen: 2026-08-15"
        )
        changed = MEMORY.parse_memory_document(changed_text)
        changed_hash = next(
            entry["contentVersionHash"]
            for entry in changed["entries"]
            if entry["entryId"] == ENTRY_A
        )
        self.assertNotEqual(original_hash, changed_hash)

        slow_waiting_for_lock = threading.Event()
        release_slow = threading.Event()
        original_state_lock = MEMORY.state_lock

        @contextlib.contextmanager
        def controlled_state_lock(path: Path):
            if threading.current_thread().name == "slow-collector":
                slow_waiting_for_lock.set()
                self.assertTrue(release_slow.wait(timeout=5))
            with original_state_lock(path) as access:
                yield access

        failures: list[BaseException] = []

        def run_collect() -> None:
            try:
                MEMORY.collect(self.args("collect"))
            except BaseException as exc:  # surface thread failures in the test
                failures.append(exc)

        with mock.patch.object(MEMORY, "state_lock", side_effect=controlled_state_lock):
            slow = threading.Thread(target=run_collect, name="slow-collector")
            slow.start()
            self.assertTrue(slow_waiting_for_lock.wait(timeout=5))
            core.write_text(changed_text, encoding="utf-8")
            MEMORY.collect(self.args("collect"))
            pending = MEMORY.load_state(self.state)["memories"][MEMORY_ID]["entries"][ENTRY_A]
            MEMORY.resolve_candidate(self.args(
                "resolve",
                "--candidate-id", pending["candidateId"],
                "--status", "queued",
                "--learning-id", "learning-v2",
            ))
            resolved = copy.deepcopy(
                MEMORY.load_state(self.state)["memories"][MEMORY_ID]["entries"][ENTRY_A]
            )
            release_slow.set()
            slow.join(timeout=5)

        self.assertFalse(slow.is_alive())
        self.assertEqual(failures, [])
        current = MEMORY.load_state(self.state)["memories"][MEMORY_ID]["entries"][ENTRY_A]
        self.assertEqual(current["contentVersionHash"], changed_hash)
        self.assertNotEqual(current["contentVersionHash"], original_hash)
        self.assertEqual(current["status"], "queued")
        self.assertEqual(current["learningId"], "learning-v2")
        self.assertEqual(current["candidateId"], resolved["candidateId"])
        self.assertEqual(current["resolvedAt"], resolved["resolvedAt"])
        self.assertEqual(core.read_text(encoding="utf-8"), changed_text)

    def test_collect_response_uses_its_locked_transaction_snapshot(self) -> None:
        baseline_args = MEMORY.build_parser().parse_args([
            "collect", "--project", str(self.project), "--state-file", str(self.state),
            "--no-cwd", "--no-registry",
        ])
        MEMORY.collect(baseline_args)
        core = self.project / ".agent-memory/CORE.md"
        core.write_text(
            document(decision_body="- decision: Transaction-local response version."),
            encoding="utf-8",
        )
        original_load = MEMORY.load_state
        calls = 0

        def later_snapshot(path: Path, access=None) -> dict:
            nonlocal calls
            calls += 1
            state = original_load(path, access)
            if calls == 2:
                state = copy.deepcopy(state)
                for memory in state["memories"].values():
                    for entry in memory.get("entries", {}).values():
                        if entry.get("status") == "pending":
                            entry["status"] = "queued"
            return state

        with mock.patch.object(MEMORY, "load_state", side_effect=later_snapshot):
            result = MEMORY.collect(baseline_args)
        self.assertEqual(result["newVersions"], 1)
        self.assertEqual(result["pending"], 1)

    def test_next_is_bounded_and_excludes_contested(self) -> None:
        MEMORY.collect(self.args("collect"))
        batch = MEMORY.next_candidates(self.args("next", "--limit", "5"))
        self.assertLessEqual(len(batch["candidates"]), 5)
        self.assertFalse(batch["hasMore"])
        self.assertNotIn("Contested Entries", {item["section"] for item in batch["candidates"]})
        self.assertLessEqual(
            sum(len(item["body"]) for item in batch["candidates"]),
            MEMORY.MAX_BATCH_BODY_CHARS,
        )
        self.assertTrue(all(
            len(item["body"]) <= MEMORY.MAX_CANDIDATE_BODY_CHARS
            for item in batch["candidates"]
        ))

    def test_candidate_disposition_is_forward_only(self) -> None:
        MEMORY.collect(self.args("collect"))
        candidate_id = MEMORY.load_state(self.state)["memories"][MEMORY_ID]["entries"][ENTRY_A]["candidateId"]
        MEMORY.resolve_candidate(self.args(
            "resolve", "--candidate-id", candidate_id,
            "--status", "queued", "--learning-id", "learn-1",
        ))
        MEMORY.resolve_candidate(self.args(
            "resolve", "--candidate-id", candidate_id, "--status", "promoted",
        ))
        with self.assertRaisesRegex(MEMORY.MemoryLearningError, "transition"):
            MEMORY.resolve_candidate(self.args(
                "resolve", "--candidate-id", candidate_id, "--status", "queued",
            ))

    def test_move_is_not_new_but_body_update_replaces_pending_in_place(self) -> None:
        MEMORY.collect(self.args("collect"))
        initial = MEMORY.load_state(self.state)["memories"][MEMORY_ID]["entries"][ENTRY_A]
        resolve = self.args("resolve", "--candidate-id", initial["candidateId"], "--status", "queued")
        MEMORY.resolve_candidate(resolve)
        core = self.project / ".agent-memory/CORE.md"
        core.write_text(document("Renamed", decision_section="Strategic Patterns"), encoding="utf-8")
        moved = MEMORY.collect(self.args("collect"))
        self.assertEqual(moved["newVersions"], 0)
        core.write_text(document(decision_body="- decision: New version.\n- first_seen: 2026-08-15"), encoding="utf-8")
        updated = MEMORY.collect(self.args("collect"))
        state = MEMORY.load_state(self.state)
        current = state["memories"][MEMORY_ID]["entries"][ENTRY_A]
        self.assertEqual(updated["newVersions"], 1)
        self.assertEqual(current["status"], "pending")
        self.assertNotEqual(current["candidateId"], initial["candidateId"])
        self.assertEqual(current["supersedesCandidateId"], initial["candidateId"])
        self.assertEqual(len(state["memories"][MEMORY_ID]["entries"]), 3)

    def test_readded_entry_is_a_change_not_a_new_baseline(self) -> None:
        MEMORY.collect(self.args("collect"))
        original = (self.project / ".agent-memory/CORE.md").read_text(encoding="utf-8")
        without_decision = re.sub(
            r"\n## Key Decisions\n.*?(?=\n## Active Constraints)",
            "",
            original,
            flags=re.DOTALL,
        )
        (self.project / ".agent-memory/CORE.md").write_text(without_decision, encoding="utf-8")
        removed = MEMORY.collect(self.args("collect"))
        self.assertEqual(removed["newVersions"], 0)

        (self.project / ".agent-memory/CORE.md").write_text(original, encoding="utf-8")
        restored_args = MEMORY.build_parser().parse_args([
            "collect", "--project", str(self.project), "--state-file", str(self.state),
            "--no-cwd", "--no-registry",
        ])
        restored = MEMORY.collect(restored_args)
        self.assertEqual(restored["newVersions"], 1)
        state = json.loads(self.state.read_text(encoding="utf-8"))
        self.assertEqual(state["memories"][MEMORY_ID]["entries"][ENTRY_A]["status"], "pending")

    def test_secret_memory_and_duplicate_ids_are_quarantined(self) -> None:
        secret = "sk-abcdefghijklmnopqrstuvwxyz123456"
        core = self.project / ".agent-memory/CORE.md"
        core.write_text(document(decision_body=f"- token={secret}"), encoding="utf-8")
        result = MEMORY.collect(self.args("collect"))
        self.assertEqual(result["projectsUpdated"], 0)
        self.assertEqual(result["quarantined"], 1)
        self.assertNotIn(secret, json.dumps(result))

        core.write_text(document(), encoding="utf-8")
        other = make_project(self.root / "other", memory_id=MEMORY_ID)
        args = MEMORY.build_parser().parse_args([
            "collect", "--project", str(self.project), "--project", str(other),
            "--state-file", str(self.state), "--no-cwd", "--no-registry",
        ])
        conflict = MEMORY.collect(args)
        self.assertEqual(conflict["conflicts"], 1)
        self.assertEqual(conflict["projectsUpdated"], 0)

    def test_common_provider_and_high_entropy_credentials_fail_closed(self) -> None:
        credentials = {
            "slack-token": "xoxb-" + ("1234567890-" * 3) + "abcdef",
            "stripe-key": "sk_live_" + ("Ab3" * 12),
            "gitlab-token": "glpat-" + ("Ab3_" * 7),
            "credential-assignment": "Q7vN2pL9sR4xT8mK3dF6hJ1cW5yB0zUe",
        }
        core = self.project / ".agent-memory/CORE.md"
        for expected_detector, credential in credentials.items():
            value = (
                "token=" + credential
                if expected_detector == "credential-assignment"
                else "credential " + credential
            )
            redacted, detectors = MEMORY.redact_secrets(value)
            self.assertIn(expected_detector, detectors)
            self.assertNotIn(credential, redacted)

            core.write_text(
                document(decision_body="- evidence: " + value),
                encoding="utf-8",
            )
            collected = MEMORY.collect(self.args("collect"))
            self.assertEqual(collected["projectsUpdated"], 0)
            self.assertEqual(collected["quarantined"], 1)
            self.assertNotIn(credential, json.dumps(collected))
            with self.assertRaisesRegex(MEMORY.MemoryLearningError, "quarantined"):
                MEMORY.recall(MEMORY.build_parser().parse_args([
                    "recall", "--project", str(self.project), "--query", "evidence",
                ]))

    def test_adjacent_provider_families_are_detected_without_public_artifact_false_positives(self) -> None:
        credentials = {
            "aws-key": "ASIA" + ("A1" * 8),
            "github-token": "gho_" + ("Ab3" * 12),
            "google-oauth-token": "ya29." + ("Ab3_" * 8),
            "pypi-token": "pypi-" + ("Ab3_" * 8),
            "slack-webhook": "https://hooks.slack.com/services/T12345678/B12345678/" + ("Ab3" * 8),
            "stripe-key": "sk_test_" + ("Ab3" * 8),
            "sendgrid-token": "SG." + ("Ab3_" * 6) + "." + ("Cd4_" * 6),
        }
        for expected_detector, credential in credentials.items():
            redacted, detectors = MEMORY.redact_secrets(credential)
            self.assertIn(expected_detector, detectors)
            self.assertNotIn(credential, redacted)

        opaque = "Q7vN2pL9sR4xT8mK3dF6hJ1cW5yB0zUe"
        safe_values = [
            "integrity: sha512-" + ("Ab3+/" * 20),
            "checksum=" + ("0123456789abcdef" * 4),
            "ssh-rsa " + ("Ab3+/" * 30) + " public@example.test",
            "public-resource-" + opaque,
            opaque,
        ]
        for value in safe_values:
            redacted, detectors = MEMORY.redact_secrets(value)
            self.assertEqual(detectors, [], value)
            self.assertEqual(redacted, value)

        redacted, detectors = MEMORY.redact_secrets("Authorization: Bearer " + opaque)
        self.assertIn("high-entropy-token", detectors)
        self.assertNotIn(opaque, redacted)

    def test_new_duplicate_memory_id_blocks_previously_pending_candidates(self) -> None:
        MEMORY.collect(self.args("collect"))
        other = make_project(self.root / "duplicate", memory_id=MEMORY_ID)
        conflict_args = MEMORY.build_parser().parse_args([
            "collect", "--project", str(self.project), "--project", str(other),
            "--state-file", str(self.state), "--no-cwd", "--no-registry",
        ])
        conflict = MEMORY.collect(conflict_args)
        self.assertEqual(conflict["conflicts"], 1)
        self.assertEqual(conflict["pending"], 0)
        self.assertEqual(conflict["blockedPending"], 2)
        self.assertEqual(MEMORY.status(self.args("status"))["actionablePending"], 0)
        self.assertEqual(MEMORY.next_candidates(self.args("next", "--limit", "5"))["returned"], 0)

        still_blocked = MEMORY.collect(self.args("collect"))
        self.assertEqual(still_blocked["conflicts"], 1)
        self.assertEqual(still_blocked["blockedPending"], 2)
        self.assertEqual(MEMORY.next_candidates(self.args("next", "--limit", "5"))["returned"], 0)

        shutil.rmtree(other)
        recovered = MEMORY.collect(self.args("collect"))
        self.assertEqual(recovered["conflicts"], 0)
        self.assertEqual(recovered["blockedPending"], 0)
        self.assertGreater(MEMORY.next_candidates(self.args("next", "--limit", "5"))["returned"], 0)

    def test_next_revalidates_version_after_collection(self) -> None:
        MEMORY.collect(self.args("collect"))
        candidate_id = MEMORY.load_state(self.state)["memories"][MEMORY_ID]["entries"][ENTRY_A]["candidateId"]
        (self.project / ".agent-memory/CORE.md").write_text(
            document(decision_body="- decision: Changed after collection."), encoding="utf-8"
        )
        batch = MEMORY.next_candidates(self.args("next", "--limit", "5"))
        self.assertNotIn(ENTRY_A, {x["entryId"] for x in batch["candidates"]})
        self.assertGreaterEqual(batch["stale"], 1)
        with self.assertRaisesRegex(MEMORY.MemoryLearningError, "changed"):
            MEMORY.resolve_candidate(self.args(
                "resolve", "--candidate-id", candidate_id, "--status", "queued"
            ))


class DiscoveryRecallTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)

    def tearDown(self) -> None:
        self.temp.cleanup()

    def test_folder_discovery_prunes_dependencies(self) -> None:
        project = make_project(self.root / "workspace/real")
        make_project(self.root / "workspace/node_modules/fake", memory_id="other")
        found, warnings = MEMORY.discover_under(self.root / "workspace", max_depth=6)
        self.assertEqual(found, [project.resolve()])
        self.assertEqual(warnings, [])

    def test_recall_is_bounded_prioritizes_constraints_and_reads_split_notes(self) -> None:
        project = make_project(self.root / "project", split=True)
        args = MEMORY.build_parser().parse_args([
            "recall", "--project", str(project), "--query", "credentials store local memory", "--limit", "1"
        ])
        result = MEMORY.recall(args)
        self.assertEqual(result["memoryId"], MEMORY_ID)
        self.assertEqual(result["memoryAgent"], "claude")
        self.assertEqual(len(result["hits"]), 1)
        self.assertEqual(result["hits"][0]["entryId"], ENTRY_B)
        self.assertLessEqual(len(result["hits"][0]["excerpt"]), MEMORY.MAX_RECALL_EXCERPT_CHARS)

    def test_discovery_root_must_be_absolute(self) -> None:
        with self.assertRaisesRegex(MEMORY.MemoryLearningError, "absolute"):
            MEMORY.discover_under(Path("relative"), max_depth=3)


if __name__ == "__main__":
    unittest.main()
