from __future__ import annotations

import importlib.util
import json
import shutil
import subprocess
import sys
import tempfile
import time
import unittest
from contextlib import contextmanager
from pathlib import Path
from unittest import mock


SCRIPT = (
    Path(__file__).resolve().parents[1]
    / "scripts"
    / "long_term_memory_training.py"
)
SPEC = importlib.util.spec_from_file_location("long_term_memory_training", SCRIPT)
assert SPEC and SPEC.loader
LTMT = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(LTMT)


def run_git(root: Path, *args: str) -> None:
    subprocess.run(
        ["git", *args],
        cwd=root,
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )


def memory(project: str = "Fixture", extra: str = "") -> str:
    return f"""# Project Core Memory

**Project**: {project}
**Created**: 2026-07-26
**Last Updated**: 2026-07-26

## Project Identity

- Purpose: Test incremental memory training.

## Key Decisions

### Keep local memory authoritative

- decision: Keep the local file as source of truth.
- rationale: Offline work must remain possible.

## Strategic Patterns

- Verify installed CLI flags before automation.

## Recurring Issues

<!-- no issue yet -->

## Active Constraints

- Never store secrets.

## Contested Entries

{extra}
"""


class ParserTests(unittest.TestCase):
    def test_h3_flat_lists_and_fake_structures_are_parsed_safely(self) -> None:
        text = memory(
            extra="""
```md
### Fake heading
- fake list
```

<!--
### Hidden heading
-->

### Real contradiction

- contradiction: Current evidence disagrees.
"""
        )
        parsed = LTMT.parse_memory_blocks(text)
        self.assertTrue(parsed["valid"])
        titles = [block["title"] for block in parsed["blocks"]]
        self.assertIn("Keep local memory authoritative", titles)
        self.assertIn("Verify installed CLI flags before automation.", titles)
        self.assertIn("Never store secrets.", titles)
        self.assertIn("Real contradiction", titles)
        self.assertNotIn("Fake heading", titles)
        self.assertNotIn("Hidden heading", titles)

    def test_bom_crlf_and_lf_have_identical_block_hashes(self) -> None:
        lf = memory()
        crlf = "\ufeff" + lf.replace("\n", "\r\n")
        left = LTMT.parse_memory_blocks(lf)
        right = LTMT.parse_memory_blocks(crlf)
        self.assertEqual(
            [block["hash"] for block in left["blocks"]],
            [block["hash"] for block in right["blocks"]],
        )
        self.assertEqual(left["documentHash"], right["documentHash"])

    def test_secret_redaction_and_control_character_removal(self) -> None:
        private_body = "MIIEvQIBADANBgkqhkiG9w0BAQEFAASC"
        clean, detectors = LTMT.redact_secrets(
            "token=abcdefghijklmnopqrstuvwxyz123456\n"
            "sk-abcdefghijklmnopqrstuvwxyz123456\n\x1b[31mred\n"
            "-----BEGIN PRIVATE KEY-----\n"
            f"{private_body}\n"
            "-----END PRIVATE KEY-----\n"
        )
        self.assertIn("credential-assignment", detectors)
        self.assertIn("openai-key", detectors)
        self.assertIn("private-key", detectors)
        self.assertNotIn("abcdefghijklmnopqrstuvwxyz123456", clean)
        self.assertNotIn(private_body, clean)
        self.assertNotIn("END PRIVATE KEY", clean)
        self.assertNotIn("\x1b", clean)

    def test_blank_template_introductions_are_not_candidates(self) -> None:
        template = """# CS Core Memory

## Strategic Patterns

Patterns confirmed across 3+ sessions. These are durable patterns.

*(No entries yet — patterns emerge after 3+ corroborating sessions)*

## Recurring Issues

Issues that have appeared in 2+ sessions.

*(No entries yet)*

## Key Decisions

Architectural and strategic decisions with full rationale.

*(No entries yet)*

## Contested Entries

Entries where new evidence contradicts an existing pattern.

*(No entries yet)*
"""
        parsed = LTMT.parse_memory_blocks(template)
        self.assertTrue(parsed["valid"])
        self.assertEqual(parsed["blocks"], [])


class LowLevelSafetyTests(unittest.TestCase):
    def test_run_git_checked_kills_stdout_overflow_while_streaming(self) -> None:
        real_popen = subprocess.Popen
        spawned: list[subprocess.Popen[bytes]] = []

        def python_child(code: str):
            def spawn(command: list[str], **kwargs: object) -> subprocess.Popen[bytes]:
                process = real_popen([sys.executable, "-c", code], **kwargs)
                spawned.append(process)
                return process

            return spawn

        exact = "import os; os.write(1, b'abcdef')"
        with mock.patch.object(
            LTMT.subprocess,
            "Popen",
            side_effect=python_child(exact),
        ):
            self.assertEqual(
                LTMT.run_git_checked(Path.cwd(), ["status"], max_bytes=6),
                b"abcdef",
            )

        overflow = (
            "import os,time; os.write(1, b'abcdef'); time.sleep(10)"
        )
        started = time.monotonic()
        with mock.patch.object(
            LTMT.subprocess,
            "Popen",
            side_effect=python_child(overflow),
        ), mock.patch.object(LTMT, "GIT_TIMEOUT_SECONDS", 5):
            with self.assertRaisesRegex(LTMT.TrainingError, "stdout output exceeds"):
                LTMT.run_git_checked(Path.cwd(), ["status"], max_bytes=5)
        self.assertLess(time.monotonic() - started, 4)
        self.assertIsNotNone(spawned[-1].poll())

    def test_run_git_checked_caps_stderr_and_drains_both_pipes(self) -> None:
        real_popen = subprocess.Popen

        def spawn_with(code: str):
            def spawn(command: list[str], **kwargs: object) -> subprocess.Popen[bytes]:
                return real_popen([sys.executable, "-c", code], **kwargs)

            return spawn

        both_pipes = (
            "import os; os.write(2, b'e' * 131072); os.write(1, b'ok')"
        )
        with mock.patch.object(
            LTMT.subprocess,
            "Popen",
            side_effect=spawn_with(both_pipes),
        ), mock.patch.object(LTMT, "MAX_GIT_STDERR_BYTES", 256 * 1024):
            self.assertEqual(
                LTMT.run_git_checked(Path.cwd(), ["status"], max_bytes=2),
                b"ok",
            )

        stderr_overflow = (
            "import os,time; os.write(2, b'e' * 8192); time.sleep(10)"
        )
        started = time.monotonic()
        with mock.patch.object(
            LTMT.subprocess,
            "Popen",
            side_effect=spawn_with(stderr_overflow),
        ), mock.patch.object(LTMT, "MAX_GIT_STDERR_BYTES", 1024), mock.patch.object(
            LTMT,
            "GIT_TIMEOUT_SECONDS",
            5,
        ):
            with self.assertRaisesRegex(LTMT.TrainingError, "stderr output exceeds"):
                LTMT.run_git_checked(Path.cwd(), ["status"])
        self.assertLess(time.monotonic() - started, 4)

    def test_git_digest_checked_is_exact_and_kills_overflow(self) -> None:
        real_popen = subprocess.Popen

        def spawn_with(code: str):
            def spawn(command: list[str], **kwargs: object) -> subprocess.Popen[bytes]:
                return real_popen([sys.executable, "-c", code], **kwargs)

            return spawn

        payload = bytes(range(256)) * 4
        exact = "import os; os.write(1, bytes(range(256)) * 4)"
        with mock.patch.object(
            LTMT.subprocess,
            "Popen",
            side_effect=spawn_with(exact),
        ):
            digest, size = LTMT.git_digest_checked(
                Path.cwd(),
                ["diff"],
                max_bytes=len(payload),
            )
        self.assertEqual(digest, LTMT.sha256_bytes(payload))
        self.assertEqual(size, len(payload))

        overflow = (
            "import os,time; os.write(1, b'abcdef'); time.sleep(10)"
        )
        with mock.patch.object(
            LTMT.subprocess,
            "Popen",
            side_effect=spawn_with(overflow),
        ), mock.patch.object(LTMT, "GIT_TIMEOUT_SECONDS", 5):
            with self.assertRaisesRegex(LTMT.TrainingError, "stdout output exceeds"):
                LTMT.git_digest_checked(
                    Path.cwd(),
                    ["diff"],
                    max_bytes=5,
                )

    def test_dirty_git_digest_uses_the_explicit_global_cap(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            run_git(root, "init")
            run_git(root, "config", "user.email", "fixture@example.com")
            run_git(root, "config", "user.name", "Fixture")
            (root / "tracked.bin").write_bytes(b"before")
            run_git(root, "add", "tracked.bin")
            run_git(root, "commit", "-m", "initial")
            (root / "tracked.bin").write_bytes(b"\0" * 4096)

            with mock.patch.object(LTMT, "MAX_GIT_DIGEST_BYTES", 16):
                with self.assertRaisesRegex(
                    LTMT.TrainingError,
                    "stdout output exceeds",
                ):
                    LTMT.git_dirty_fingerprint(
                        root,
                        ".agent-memory/CORE.md",
                    )

    def test_queue_lock_is_compatible_with_prepass_lock(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            queue = root / "queue.json"
            queue.write_text("[]", encoding="utf-8")
            ready = root / "ready"
            acquired = root / "acquired"
            prepass = SCRIPT.parents[4] / "shared" / "scripts" / "pre_pass.py"
            child_code = (
                "import importlib.util,sys\n"
                "from pathlib import Path\n"
                "s=importlib.util.spec_from_file_location('prepass_lock',sys.argv[1])\n"
                "m=importlib.util.module_from_spec(s);s.loader.exec_module(m)\n"
                "Path(sys.argv[3]).write_text('ready')\n"
                "with m._queue_lock(Path(sys.argv[2])):\n"
                " Path(sys.argv[4]).write_text('acquired')\n"
            )
            process: subprocess.Popen[bytes] | None = None
            try:
                with LTMT.learning_queue_lock(queue):
                    process = subprocess.Popen(
                        [
                            sys.executable,
                            "-c",
                            child_code,
                            str(prepass),
                            str(queue),
                            str(ready),
                            str(acquired),
                        ],
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                    )
                    deadline = time.time() + 5
                    while not ready.exists() and time.time() < deadline:
                        time.sleep(0.02)
                    self.assertTrue(ready.exists())
                    time.sleep(0.1)
                    self.assertFalse(acquired.exists())
                    self.assertIsNone(process.poll())
                _, stderr = process.communicate(timeout=5)
                self.assertEqual(process.returncode, 0, stderr.decode("utf-8"))
                self.assertTrue(acquired.exists())
            finally:
                if process is not None and process.poll() is None:
                    process.terminate()
                    process.wait(timeout=5)


class IncrementalWorkflowTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.project = self.root / "project"
        self.project.mkdir()
        (self.project / ".agent-memory").mkdir()
        self.memory_id = "00000000-0000-4000-8000-000000000001"
        (self.project / ".agent-memory" / "config.json").write_text(
            json.dumps(
                {
                    "schemaVersion": 1,
                    "memoryId": self.memory_id,
                    "sourcePath": ".agent-memory/CORE.md",
                    "agent": "codex",
                    "autoBackup": False,
                }
            ),
            encoding="utf-8",
        )
        (self.project / ".agent-memory" / "CORE.md").write_text(
            memory(),
            encoding="utf-8",
        )
        (self.project / "app.txt").write_text("v1\n", encoding="utf-8")
        run_git(self.project, "init")
        run_git(self.project, "config", "user.email", "fixture@example.com")
        run_git(self.project, "config", "user.name", "Fixture")
        run_git(self.project, "add", "app.txt")
        run_git(self.project, "commit", "-m", "initial")
        self.ports = self.root / "ports.json"
        self.ports.write_text(
            json.dumps([{"name": "Fixture", "folderPath": str(self.project)}]),
            encoding="utf-8",
        )
        self.state = self.root / "state.json"
        self.run1 = self.root / "run1.json"

    def tearDown(self) -> None:
        self.temp.cleanup()

    def scan(self, output: Path) -> dict:
        parser = LTMT.build_parser()
        args = parser.parse_args(
            [
                "scan",
                "--ports-file",
                str(self.ports),
                "--state-file",
                str(self.state),
                "--output",
                str(output),
                "--no-cwd",
            ]
        )
        run = LTMT.build_scan(args)
        LTMT.write_run_file(output, run)
        return run

    def commit(self, run_file: Path) -> int:
        parser = LTMT.build_parser()
        args = parser.parse_args(
            [
                "commit",
                "--run-file",
                str(run_file),
                "--memory-id",
                self.memory_id,
                "--state-file",
                str(self.state),
            ]
        )
        return LTMT.command_commit(args)

    def backup(self, run_file: Path) -> int:
        parser = LTMT.build_parser()
        args = parser.parse_args(
            [
                "backup",
                "--run-file",
                str(run_file),
                "--memory-id",
                self.memory_id,
            ]
        )
        return LTMT.command_backup(args)

    def review_no_candidates(
        self,
        run_file: Path,
        *extra_args: str,
    ) -> int:
        parser = LTMT.build_parser()
        args = parser.parse_args(
            [
                "review-complete",
                "--run-file",
                str(run_file),
                "--memory-id",
                self.memory_id,
                "--no-reusable-candidates",
                "--accept-bootstrap",
                *extra_args,
            ]
        )
        return LTMT.command_review_complete(args)

    def review_candidate(
        self,
        run_file: Path,
        queue: Path,
        candidate_id: str,
    ) -> int:
        args = LTMT.build_parser().parse_args(
            [
                "review-complete",
                "--run-file",
                str(run_file),
                "--memory-id",
                self.memory_id,
                "--candidate-id",
                candidate_id,
                "--btw-file",
                str(queue),
                "--accept-bootstrap",
            ]
        )
        return LTMT.command_review_complete(args)

    def add_linked_worktree(self, name: str = "feature") -> Path:
        linked = self.project / ".claude" / "worktrees" / name
        linked.parent.mkdir(parents=True, exist_ok=True)
        run_git(
            self.project,
            "worktree",
            "add",
            "-b",
            "fixture-%s" % name,
            str(linked),
        )
        return linked

    def test_cold_start_commit_then_unchanged_scan(self) -> None:
        first = self.scan(self.run1)
        self.assertEqual(first["summary"]["changedProjects"], 1)
        self.assertGreater(first["summary"]["memoryCandidates"], 0)
        self.assertFalse(self.state.exists())
        self.assertEqual(self.review_no_candidates(self.run1), 0)
        self.assertEqual(self.commit(self.run1), 0)

        second_file = self.root / "run2.json"
        second = self.scan(second_file)
        self.assertEqual(second["summary"]["changedProjects"], 0)
        self.assertEqual(second["summary"]["memoryCandidates"], 0)

    def test_one_commit_bootstrap_includes_initial_tracked_content(self) -> None:
        run = self.scan(self.run1)
        source = run["projects"][0]["source"]

        self.assertIsNotNone(source["committedRange"])
        self.assertTrue(source["historyComplete"])
        self.assertIn("initial", source["commits"])
        self.assertIn("app.txt", source["committedDiff"])
        self.assertIn("+v1", source["committedDiff"])

    def test_git_backup_created_after_scan_does_not_cause_source_churn(self) -> None:
        first = self.scan(self.run1)
        self.assertEqual(
            first["projects"][0]["source"]["counts"]["untrackedFiles"],
            0,
        )
        self.assertEqual(self.backup(self.run1), 0)
        self.assertEqual(self.review_no_candidates(self.run1), 0)
        self.assertEqual(self.commit(self.run1), 0)

        second = self.scan(self.root / "run2.json")
        project = second["projects"][0]
        self.assertFalse(project["needsReview"])
        self.assertFalse(project["source"]["hasChanges"])
        self.assertEqual(project["source"]["counts"]["untrackedFiles"], 0)

    def test_non_git_backup_created_after_scan_does_not_cause_source_churn(
        self,
    ) -> None:
        nongit = self.root / "nongit-backup"
        (nongit / ".agent-memory").mkdir(parents=True)
        self.memory_id = "00000000-0000-4000-8000-000000000004"
        (nongit / ".agent-memory" / "config.json").write_text(
            json.dumps(
                {
                    "schemaVersion": 1,
                    "memoryId": self.memory_id,
                    "sourcePath": ".agent-memory/CORE.md",
                    "autoBackup": False,
                }
            ),
            encoding="utf-8",
        )
        (nongit / ".agent-memory" / "CORE.md").write_text(
            memory(project="NonGitBackup"),
            encoding="utf-8",
        )
        (nongit / "app.txt").write_text("v1\n", encoding="utf-8")
        self.ports.write_text(
            json.dumps(
                [{"name": "NonGitBackup", "folderPath": str(nongit)}]
            ),
            encoding="utf-8",
        )

        first = self.scan(self.run1)
        manifest = first["projects"][0]["source"]["snapshot"]["fileManifest"]
        self.assertEqual(sorted(manifest), ["app.txt"])
        self.assertEqual(self.backup(self.run1), 0)
        self.assertEqual(self.review_no_candidates(self.run1), 0)
        self.assertEqual(self.commit(self.run1), 0)

        second = self.scan(self.root / "run2.json")
        project = second["projects"][0]
        self.assertFalse(project["needsReview"])
        self.assertFalse(project["source"]["hasChanges"])
        self.assertEqual(
            sorted(project["source"]["snapshot"]["fileManifest"]),
            ["app.txt"],
        )

    def test_persistent_partial_source_never_becomes_silent_noop(self) -> None:
        nongit = self.root / "nongit-partial"
        (nongit / ".agent-memory").mkdir(parents=True)
        self.memory_id = "00000000-0000-4000-8000-000000000005"
        (nongit / ".agent-memory" / "config.json").write_text(
            json.dumps(
                {
                    "schemaVersion": 1,
                    "memoryId": self.memory_id,
                    "sourcePath": ".agent-memory/CORE.md",
                    "autoBackup": False,
                }
            ),
            encoding="utf-8",
        )
        (nongit / ".agent-memory" / "CORE.md").write_text(
            memory(project="NonGitPartial"),
            encoding="utf-8",
        )
        outside = self.root / "outside-partial.txt"
        outside.write_text("unreviewable\n", encoding="utf-8")
        (nongit / "outside-link.txt").symlink_to(outside)
        self.ports.write_text(
            json.dumps(
                [{"name": "NonGitPartial", "folderPath": str(nongit)}]
            ),
            encoding="utf-8",
        )

        first = self.scan(self.run1)
        self.assertTrue(first["projects"][0]["source"]["snapshot"]["partial"])
        self.assertEqual(
            self.review_no_candidates(
                self.run1,
                "--accept-incomplete-source",
            ),
            0,
        )
        self.assertEqual(self.commit(self.run1), 0)

        second = self.scan(self.root / "run2.json")
        project = second["projects"][0]
        self.assertTrue(project["source"]["snapshot"]["partial"])
        self.assertTrue(project["source"]["hasChanges"])
        self.assertTrue(project["needsReview"])

    def test_new_commit_is_detected_from_previous_head(self) -> None:
        self.scan(self.run1)
        self.review_no_candidates(self.run1)
        self.commit(self.run1)
        (self.project / "app.txt").write_text("v2\n", encoding="utf-8")
        run_git(self.project, "add", "app.txt")
        run_git(self.project, "commit", "-m", "second")

        second = self.scan(self.root / "run2.json")
        project = second["projects"][0]
        self.assertTrue(project["source"]["hasChanges"])
        self.assertEqual(project["source"]["historyMode"], "incremental")
        self.assertIn("second", project["source"]["commits"])
        self.assertIn("+v2", project["source"]["committedDiff"])

    def test_assume_unchanged_file_uses_independent_fingerprint(self) -> None:
        self.scan(self.run1)
        self.review_no_candidates(self.run1)
        self.commit(self.run1)
        run_git(self.project, "update-index", "--assume-unchanged", "app.txt")
        (self.project / "app.txt").write_text(
            "hidden assume-unchanged edit\n",
            encoding="utf-8",
        )
        self.assertEqual(
            subprocess.run(
                ["git", "diff", "--", "app.txt"],
                cwd=self.project,
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            ).stdout,
            "",
        )

        second = self.scan(self.root / "run2.json")
        source = second["projects"][0]["source"]

        self.assertTrue(source["hasChanges"])
        self.assertEqual(source["indexFlagged"][0]["path"], "app.txt")
        self.assertTrue(source["indexFlagged"][0]["flag"].islower())

    def test_skip_worktree_file_uses_independent_fingerprint(self) -> None:
        self.scan(self.run1)
        self.review_no_candidates(self.run1)
        self.commit(self.run1)
        run_git(self.project, "update-index", "--skip-worktree", "app.txt")
        (self.project / "app.txt").write_text(
            "hidden skip-worktree edit\n",
            encoding="utf-8",
        )
        self.assertEqual(
            subprocess.run(
                ["git", "diff", "--", "app.txt"],
                cwd=self.project,
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            ).stdout,
            "",
        )

        second = self.scan(self.root / "run2.json")
        source = second["projects"][0]["source"]

        self.assertTrue(source["hasChanges"])
        self.assertEqual(source["indexFlagged"][0]["path"], "app.txt")
        self.assertEqual(source["indexFlagged"][0]["flag"].upper(), "S")

    def test_index_flag_file_cap_is_counted_and_persistently_partial(self) -> None:
        (self.project / "b.txt").write_text("b\n", encoding="utf-8")
        (self.project / "c.txt").write_text("c\n", encoding="utf-8")
        run_git(self.project, "add", "b.txt", "c.txt")
        run_git(self.project, "commit", "-m", "more tracked files")
        run_git(
            self.project,
            "update-index",
            "--assume-unchanged",
            "app.txt",
            "b.txt",
            "c.txt",
        )

        with mock.patch.object(LTMT, "MAX_FLAGGED_INDEX_FILES", 2):
            first = self.scan(self.run1)
            source = first["projects"][0]["source"]
            self.assertTrue(source["snapshot"]["partial"])
            self.assertEqual(source["counts"]["indexFlaggedFiles"], 3)
            self.assertEqual(
                source["counts"]["indexFlaggedManifestFiles"],
                2,
            )
            self.assertEqual(
                source["counts"]["indexFlaggedOmittedFiles"],
                1,
            )
            self.assertGreater(
                source["counts"]["indexFlaggedHashedBytes"],
                0,
            )
            self.assertTrue(
                any(
                    "file count exceeded" in reason
                    for reason in source["incompleteReasons"]
                )
            )
            self.assertEqual(
                self.review_no_candidates(
                    self.run1,
                    "--accept-incomplete-source",
                ),
                0,
            )
            self.assertEqual(self.commit(self.run1), 0)
            second = self.scan(self.root / "run2.json")

        second_project = second["projects"][0]
        self.assertTrue(second_project["source"]["snapshot"]["partial"])
        self.assertTrue(second_project["source"]["hasChanges"])
        self.assertTrue(second_project["needsReview"])

    def test_index_flag_hash_budget_uses_bounded_hashing(self) -> None:
        run_git(self.project, "update-index", "--assume-unchanged", "app.txt")

        with mock.patch.object(LTMT, "MAX_FLAGGED_INDEX_HASH_BYTES", 2):
            result = LTMT.git_index_flags_snapshot(
                self.project,
                ".agent-memory/CORE.md",
            )

        self.assertEqual(result["count"], 1)
        self.assertEqual(result["manifestFiles"], 1)
        self.assertEqual(result["omittedFiles"], 0)
        self.assertEqual(result["hashedBytes"], 0)
        self.assertTrue(result["partial"])
        self.assertEqual(result["entries"][0]["type"], "hash-budget-exceeded")
        self.assertTrue(
            any(
                "hash budget exceeded" in reason
                for reason in result["incompleteReasons"]
            )
        )

    def test_registered_nested_linked_worktree_is_snapshotted(self) -> None:
        linked = self.add_linked_worktree()

        run = self.scan(self.run1)
        source = run["projects"][0]["source"]
        snapshots = source["snapshot"]["linkedWorktrees"]

        self.assertEqual(len(snapshots), 1)
        self.assertEqual(snapshots[0]["root"], str(linked.resolve()))
        self.assertEqual(snapshots[0]["head"], source["snapshot"]["head"])
        self.assertEqual(snapshots[0]["branch"], "fixture-feature")
        self.assertFalse(source["snapshot"]["partial"])
        self.assertFalse(source["truncated"])
        self.assertEqual(source["counts"]["linkedWorktrees"], 1)

    def test_dirty_linked_worktree_change_after_baseline_requires_review(self) -> None:
        linked = self.add_linked_worktree()
        first = self.scan(self.run1)
        first_linked = first["projects"][0]["source"]["snapshot"][
            "linkedWorktrees"
        ][0]
        self.review_no_candidates(self.run1)
        self.commit(self.run1)

        (linked / "app.txt").write_text("linked dirty\n", encoding="utf-8")
        (linked / "new.txt").write_text("linked untracked\n", encoding="utf-8")
        second = self.scan(self.root / "run2.json")
        project = second["projects"][0]
        linked_evidence = project["source"]["linkedWorktrees"][0]
        second_linked = project["source"]["snapshot"]["linkedWorktrees"][0]

        self.assertTrue(project["needsReview"])
        self.assertTrue(project["source"]["hasChanges"])
        self.assertTrue(linked_evidence["hasChanges"])
        self.assertIn("+linked dirty", linked_evidence["dirtyDiff"])
        self.assertNotEqual(
            first_linked["untrackedHash"],
            second_linked["untrackedHash"],
        )
        self.assertIn(
            "FILE: new.txt",
            "\n".join(linked_evidence["untracked"]),
        )

    def test_removed_linked_worktree_requires_explicit_incomplete_rebaseline(
        self,
    ) -> None:
        linked = self.add_linked_worktree()
        self.scan(self.run1)
        self.review_no_candidates(self.run1)
        self.commit(self.run1)

        (linked / "app.txt").write_text("commit only on linked\n", encoding="utf-8")
        run_git(linked, "add", "app.txt")
        run_git(linked, "commit", "-m", "linked-only commit")
        run_git(self.project, "worktree", "remove", str(linked))

        run2 = self.root / "run2.json"
        second = self.scan(run2)
        source = second["projects"][0]["source"]

        self.assertEqual(source["linkedWorktreesRemoved"], [str(linked.resolve())])
        self.assertTrue(source["hasChanges"])
        self.assertFalse(source["historyComplete"])
        self.assertTrue(source["snapshot"]["partial"])
        self.assertTrue(
            any(
                "removed linked worktree" in reason
                for reason in source["incompleteReasons"]
            )
        )
        with self.assertRaisesRegex(LTMT.TrainingError, "could not be compared"):
            self.review_no_candidates(run2)
        with self.assertRaisesRegex(
            LTMT.TrainingError,
            "accept-incomplete-source",
        ):
            self.review_no_candidates(run2, "--accept-history-rebaseline")
        self.assertEqual(
            self.review_no_candidates(
                run2,
                "--accept-history-rebaseline",
                "--accept-incomplete-source",
            ),
            0,
        )

    def test_symlinked_registered_linked_worktree_fails_closed(self) -> None:
        linked = self.add_linked_worktree()
        moved = self.root / "moved-linked-worktree"
        linked.rename(moved)
        linked.symlink_to(moved, target_is_directory=True)

        run = self.scan(self.run1)

        self.assertEqual(run["summary"]["reviewableProjects"], 0)
        self.assertEqual(run["summary"]["skipped"], 1)
        self.assertIn("linked worktree", run["skipped"][0]["error"])
        self.assertIn("symlink", run["skipped"][0]["error"])
        linked.unlink()
        shutil.rmtree(moved)

    def test_missing_registered_linked_worktree_fails_closed(self) -> None:
        linked = self.add_linked_worktree()
        shutil.rmtree(linked)

        run = self.scan(self.run1)

        self.assertEqual(run["summary"]["reviewableProjects"], 0)
        self.assertEqual(run["summary"]["skipped"], 1)
        self.assertIn("linked worktree", run["skipped"][0]["error"])
        self.assertIn("inaccessible", run["skipped"][0]["error"])

    def test_truncated_linked_evidence_requires_explicit_acceptance(self) -> None:
        linked = self.add_linked_worktree()
        (linked / "app.txt").write_text(
            "x" * (LTMT.MAX_LINKED_EVIDENCE_CHARS * 2),
            encoding="utf-8",
        )

        run = self.scan(self.run1)
        source = run["projects"][0]["source"]

        self.assertTrue(source["truncated"])
        self.assertTrue(
            any(
                "shared text budget" in reason
                for reason in source["incompleteReasons"]
            )
        )
        with self.assertRaisesRegex(
            LTMT.TrainingError,
            "accept-incomplete-source",
        ):
            self.review_no_candidates(self.run1)
        self.assertEqual(
            self.review_no_candidates(
                self.run1,
                "--accept-incomplete-source",
            ),
            0,
        )

    def test_commit_requires_review_receipt(self) -> None:
        self.scan(self.run1)
        with self.assertRaisesRegex(LTMT.TrainingError, "review receipt missing"):
            self.commit(self.run1)

    def test_initial_baseline_requires_explicit_acceptance(self) -> None:
        self.scan(self.run1)
        args = LTMT.build_parser().parse_args(
            [
                "review-complete",
                "--run-file",
                str(self.run1),
                "--memory-id",
                self.memory_id,
                "--no-reusable-candidates",
            ]
        )
        with self.assertRaisesRegex(LTMT.TrainingError, "accept-bootstrap"):
            LTMT.command_review_complete(args)

    def test_memory_change_after_review_is_not_swallowed(self) -> None:
        self.scan(self.run1)
        self.review_no_candidates(self.run1)
        core = self.project / ".agent-memory" / "CORE.md"
        core.write_text(
            memory(
                extra="""### Concurrent unreviewed change

- contradiction: This arrived after the review receipt.
"""
            ),
            encoding="utf-8",
        )
        with self.assertRaisesRegex(LTMT.TrainingError, "changed after review"):
            self.commit(self.run1)
        self.assertFalse(self.state.exists())

    def test_non_trainable_memory_edit_still_requires_review(self) -> None:
        self.scan(self.run1)
        self.review_no_candidates(self.run1)
        self.commit(self.run1)
        core = self.project / ".agent-memory" / "CORE.md"
        core.write_text(
            memory().replace(
                "Purpose: Test incremental memory training.",
                "Purpose: Updated durable project identity.",
            ),
            encoding="utf-8",
        )

        second = self.scan(self.root / "run2.json")
        project = second["projects"][0]

        self.assertTrue(project["memoryChangedSinceCursor"])
        self.assertEqual(project["memoryDelta"]["candidateCount"], 0)
        self.assertFalse(project["source"]["hasChanges"])
        self.assertTrue(project["needsReview"])

    def test_secret_bearing_memory_is_quarantined_from_run_and_review(self) -> None:
        secret = "sk-abcdefghijklmnopqrstuvwxyz123456"
        core = self.project / ".agent-memory" / "CORE.md"
        core.write_text(
            memory(
                extra=f"""### {secret}

- token={secret}
"""
            ),
            encoding="utf-8",
        )
        run = self.scan(self.run1)
        project = run["projects"][0]
        self.assertIn("openai-key", project["memorySecretDetectors"])
        self.assertNotIn(secret, json.dumps(run))
        with self.assertRaisesRegex(LTMT.TrainingError, "secret indicators"):
            self.review_no_candidates(self.run1)

    def test_candidate_receipt_must_remain_durable_until_commit(self) -> None:
        run = self.scan(self.run1)
        queue = self.root / "queue.json"
        candidate = {
            "id": "btw-current-run",
            "idea": "[project-memory:Fixture] Reusable verified lesson",
            "status": "pending",
            "provenance": {
                "source_run_id": run["runId"],
                "source_range": "bootstrap:test",
                "memory_id": self.memory_id,
            },
        }
        queue.write_text(json.dumps([candidate]), encoding="utf-8")
        args = LTMT.build_parser().parse_args(
            [
                "review-complete",
                "--run-file",
                str(self.run1),
                "--memory-id",
                self.memory_id,
                "--candidate-id",
                candidate["id"],
                "--btw-file",
                str(queue),
                "--accept-bootstrap",
            ]
        )
        self.assertEqual(LTMT.command_review_complete(args), 0)
        queue.write_text("[]", encoding="utf-8")
        with self.assertRaisesRegex(LTMT.TrainingError, "exactly once"):
            self.commit(self.run1)
        queue.write_text(json.dumps([candidate]), encoding="utf-8")
        self.assertEqual(self.commit(self.run1), 0)

    def test_candidate_immutable_fields_must_match_review_receipt(self) -> None:
        run = self.scan(self.run1)
        queue = self.root / "queue.json"
        candidate = {
            "id": "btw-immutable",
            "idea": "[project-memory:Fixture] Reviewed lesson",
            "evidence": "app.txt@initial",
            "tier": "tactical",
            "status": "pending",
            "provenance": {
                "source_run_id": run["runId"],
                "source_range": "bootstrap:reviewed",
                "memory_id": self.memory_id,
            },
        }
        queue.write_text(json.dumps([candidate]), encoding="utf-8")
        self.assertEqual(
            self.review_candidate(self.run1, queue, candidate["id"]),
            0,
        )
        receipt = json.loads(self.run1.read_text(encoding="utf-8"))["reviews"][
            self.memory_id
        ]
        self.assertEqual(
            receipt["candidateDispositions"][0]["immutableHash"],
            LTMT.candidate_immutable_hash(candidate),
        )

        changed = {
            **candidate,
            "idea": "[project-memory:Fixture] Different lesson",
            "evidence": "different evidence",
            "tier": "principle",
            "status": "rejected",
            "note": "status and note may change, immutable fields may not",
            "provenance": {
                **candidate["provenance"],
                "source_range": "tampered:after-review",
            },
        }
        queue.write_text(json.dumps([changed]), encoding="utf-8")
        with self.assertRaisesRegex(
            LTMT.TrainingError,
            "immutable fields changed",
        ):
            self.commit(self.run1)
        self.assertFalse(self.state.exists())

    def test_candidate_status_and_note_may_change_after_review(self) -> None:
        run = self.scan(self.run1)
        queue = self.root / "queue.json"
        candidate = {
            "id": "btw-status-transition",
            "idea": "[project-memory:Fixture] Reviewed lesson",
            "evidence": "app.txt@initial",
            "tier": "tactical",
            "status": "pending",
            "provenance": {
                "source_run_id": run["runId"],
                "source_range": "bootstrap:reviewed",
                "memory_id": self.memory_id,
            },
        }
        queue.write_text(json.dumps([candidate]), encoding="utf-8")
        self.assertEqual(
            self.review_candidate(self.run1, queue, candidate["id"]),
            0,
        )
        transitioned = {
            **candidate,
            "status": "promoted",
            "note": "Learning Gate completed after the receipt.",
        }
        queue.write_text(json.dumps([transitioned]), encoding="utf-8")
        self.assertEqual(self.commit(self.run1), 0)

    def test_commit_locks_state_then_queue_through_state_replace(self) -> None:
        run = self.scan(self.run1)
        queue = self.root / "queue.json"
        candidate = {
            "id": "btw-lock-order",
            "idea": "[project-memory:Fixture] Lock ordering",
            "evidence": "queue/state boundary",
            "tier": "tactical",
            "status": "pending",
            "provenance": {
                "source_run_id": run["runId"],
                "source_range": "bootstrap:lock-order",
                "memory_id": self.memory_id,
            },
        }
        queue.write_text(json.dumps([candidate]), encoding="utf-8")
        self.review_candidate(self.run1, queue, candidate["id"])

        events: list[str] = []
        queue_is_locked = False
        real_atomic_write = LTMT.atomic_write_json

        @contextmanager
        def recording_state_lock(target: Path):
            events.append("state-enter")
            try:
                yield
            finally:
                events.append("state-exit")

        @contextmanager
        def recording_queue_lock(target: Path):
            nonlocal queue_is_locked
            events.append("queue-enter")
            queue_is_locked = True
            try:
                yield
            finally:
                queue_is_locked = False
                events.append("queue-exit")

        def recording_atomic_write(
            path: Path,
            value: object,
            max_bytes: int | None = None,
        ) -> None:
            if path == self.state:
                self.assertTrue(queue_is_locked)
                events.append("state-replace")
            real_atomic_write(path, value, max_bytes=max_bytes)

        with mock.patch.object(
            LTMT,
            "FileLock",
            lambda target: recording_state_lock(target),
        ), mock.patch.object(
            LTMT,
            "learning_queue_lock",
            recording_queue_lock,
        ), mock.patch.object(
            LTMT,
            "atomic_write_json",
            recording_atomic_write,
        ):
            self.assertEqual(self.commit(self.run1), 0)

        self.assertEqual(
            events,
            [
                "state-enter",
                "queue-enter",
                "state-replace",
                "queue-exit",
                "state-exit",
            ],
        )

    def test_state_size_preflight_preserves_existing_state(self) -> None:
        self.scan(self.run1)
        self.review_no_candidates(self.run1)
        old_state = {
            "schemaVersion": LTMT.STATE_SCHEMA,
            "consumers": {},
            "sentinel": "preserve-exactly",
        }
        LTMT.atomic_write_json(self.state, old_state)
        old_bytes = self.state.read_bytes()
        with mock.patch.object(
            LTMT,
            "MAX_STATE_BYTES",
            len(old_bytes) + 64,
        ):
            with self.assertRaisesRegex(
                LTMT.TrainingError,
                "JSON payload exceeds",
            ):
                self.commit(self.run1)
        self.assertEqual(self.state.read_bytes(), old_bytes)

    def test_git_untracked_file_cap_is_partial_and_never_silent(self) -> None:
        self.scan(self.run1)
        self.review_no_candidates(self.run1)
        self.commit(self.run1)
        for index in range(3):
            (self.project / f"untracked-{index}.txt").write_text(
                f"value {index}\n",
                encoding="utf-8",
            )

        with mock.patch.object(LTMT, "MAX_GIT_UNTRACKED_FILES", 2):
            second = self.scan(self.root / "run2.json")
            source = second["projects"][0]["source"]

        self.assertTrue(source["hasChanges"])
        self.assertTrue(source["snapshot"]["partial"])
        self.assertTrue(source["truncated"])
        self.assertEqual(source["counts"]["untrackedFiles"], 3)
        self.assertEqual(source["counts"]["untrackedManifestFiles"], 2)
        self.assertEqual(source["counts"]["untrackedOmittedFiles"], 1)
        self.assertTrue(
            any("file count exceeded" in reason for reason in source["incompleteReasons"])
        )

    def test_git_untracked_hash_budget_is_partial_and_bounded(self) -> None:
        self.scan(self.run1)
        self.review_no_candidates(self.run1)
        self.commit(self.run1)
        (self.project / "a.txt").write_text("1234", encoding="utf-8")
        (self.project / "b.txt").write_text("5678", encoding="utf-8")

        with mock.patch.object(LTMT, "MAX_GIT_UNTRACKED_HASH_BYTES", 4):
            second = self.scan(self.root / "run2.json")
            source = second["projects"][0]["source"]

        self.assertTrue(source["hasChanges"])
        self.assertTrue(source["snapshot"]["partial"])
        self.assertTrue(source["truncated"])
        self.assertEqual(source["counts"]["untrackedHashedBytes"], 4)
        self.assertTrue(
            any("hash budget exceeded" in reason for reason in source["incompleteReasons"])
        )

    def test_backup_diff_and_compare_and_swap_guard(self) -> None:
        first = self.scan(self.run1)
        run_id = first["runId"]
        backup_args = LTMT.build_parser().parse_args(
            [
                "backup",
                "--run-file",
                str(self.run1),
                "--memory-id",
                self.memory_id,
            ]
        )
        self.assertEqual(LTMT.command_backup(backup_args), 0)
        backups = list((self.project / ".agent-memory" / "backups").glob("*.md"))
        self.assertEqual(len(backups), 1)
        self.assertIn(run_id[:8], backups[0].name)

        core = self.project / ".agent-memory" / "CORE.md"
        core.write_text(
            memory(
                extra="""### New durable warning

- contradiction: A new verified warning.
"""
            ),
            encoding="utf-8",
        )
        diff_args = LTMT.build_parser().parse_args(
            [
                "diff-memory",
                "--run-file",
                str(self.run1),
                "--memory-id",
                self.memory_id,
            ]
        )
        resolved = LTMT.resolve_memory_project(
            {"root": str(self.project), "name": "Fixture", "origin": "test"}
        )
        delta = LTMT.memory_delta(
            {"blocks": first["projects"][0]["memoryBlocksBefore"]},
            resolved["memory"]["blocks"],
        )
        self.assertEqual(delta["candidateCount"], 1)
        self.assertEqual(LTMT.command_diff_memory(diff_args), 0)
        self.review_no_candidates(self.run1)
        self.commit(self.run1)
        with self.assertRaises(LTMT.TrainingError):
            self.commit(self.run1)

    def test_traversal_source_path_is_skipped(self) -> None:
        config = self.project / ".agent-memory" / "config.json"
        payload = json.loads(config.read_text(encoding="utf-8"))
        payload["sourcePath"] = "../outside.md"
        config.write_text(json.dumps(payload), encoding="utf-8")
        run = self.scan(self.run1)
        self.assertEqual(run["summary"]["reviewableProjects"], 0)
        self.assertEqual(run["summary"]["skipped"], 1)

    def test_divergent_duplicate_memory_id_is_quarantined(self) -> None:
        other = self.root / "other"
        (other / ".agent-memory").mkdir(parents=True)
        (other / ".agent-memory" / "config.json").write_text(
            (self.project / ".agent-memory" / "config.json").read_text(encoding="utf-8"),
            encoding="utf-8",
        )
        (other / ".agent-memory" / "CORE.md").write_text(
            memory(project="Other", extra="Different"),
            encoding="utf-8",
        )
        rows = json.loads(self.ports.read_text(encoding="utf-8"))
        rows.append({"name": "Other", "folderPath": str(other)})
        self.ports.write_text(json.dumps(rows), encoding="utf-8")
        run = self.scan(self.run1)
        self.assertEqual(run["summary"]["conflicts"], 1)
        self.assertEqual(run["summary"]["reviewableProjects"], 0)

    def test_identical_duplicate_memory_id_is_also_quarantined(self) -> None:
        other = self.root / "identical"
        (other / ".agent-memory").mkdir(parents=True)
        for name in ("config.json", "CORE.md"):
            (other / ".agent-memory" / name).write_bytes(
                (self.project / ".agent-memory" / name).read_bytes()
            )
        rows = json.loads(self.ports.read_text(encoding="utf-8"))
        rows.append({"name": "Identical", "folderPath": str(other)})
        self.ports.write_text(json.dumps(rows), encoding="utf-8")
        run = self.scan(self.run1)
        self.assertEqual(run["summary"]["conflicts"], 1)
        self.assertFalse(run["conflicts"][0]["contentDivergent"])

    def test_explicit_project_filters_out_registry_peers(self) -> None:
        other = self.root / "peer"
        (other / ".agent-memory").mkdir(parents=True)
        other_id = "00000000-0000-4000-8000-000000000002"
        (other / ".agent-memory" / "config.json").write_text(
            json.dumps(
                {
                    "schemaVersion": 1,
                    "memoryId": other_id,
                    "sourcePath": ".agent-memory/CORE.md",
                }
            ),
            encoding="utf-8",
        )
        (other / ".agent-memory" / "CORE.md").write_text(
            memory(project="Peer"),
            encoding="utf-8",
        )
        rows = json.loads(self.ports.read_text(encoding="utf-8"))
        rows.append({"name": "Peer", "folderPath": str(other)})
        self.ports.write_text(json.dumps(rows), encoding="utf-8")
        args = LTMT.build_parser().parse_args(
            [
                "scan",
                "--ports-file",
                str(self.ports),
                "--state-file",
                str(self.state),
                "--project",
                str(self.project),
                "--no-cwd",
            ]
        )
        run = LTMT.build_scan(args)
        self.assertEqual(
            [project["projectRoot"] for project in run["projects"]],
            [str(self.project.resolve())],
        )

    def test_history_rewrite_without_merge_base_diffs_previous_tree(self) -> None:
        self.scan(self.run1)
        self.review_no_candidates(self.run1)
        self.commit(self.run1)
        run_git(self.project, "checkout", "--orphan", "rewritten")
        (self.project / "app.txt").write_text("orphan\n", encoding="utf-8")
        run_git(self.project, "add", "-A")
        run_git(self.project, "commit", "-m", "orphan history")
        run2 = self.root / "run2.json"
        second = self.scan(run2)
        source = second["projects"][0]["source"]
        self.assertEqual(source["historyMode"], "history-rewritten")
        self.assertTrue(source["historyComplete"])
        self.assertIsNone(source["commonMergeBase"])
        self.assertIn("+orphan", source["committedDiff"])
        self.assertIn("-v1", source["committedDiff"])
        self.assertEqual(self.review_no_candidates(run2), 0)

    def test_missing_previous_git_tree_requires_reviewed_rebaseline(self) -> None:
        self.scan(self.run1)
        self.review_no_candidates(self.run1)
        self.commit(self.run1)
        state = json.loads(self.state.read_text(encoding="utf-8"))
        cursor = state["consumers"]["cs-experiencing"]["projects"][self.memory_id]
        cursor["source"]["head"] = "f" * 40
        self.state.write_text(json.dumps(state), encoding="utf-8")

        run2 = self.root / "run2.json"
        second = self.scan(run2)
        source = second["projects"][0]["source"]
        self.assertEqual(source["historyMode"], "previous-tree-missing")
        self.assertFalse(source["historyComplete"])
        with self.assertRaisesRegex(LTMT.TrainingError, "could not be compared"):
            self.review_no_candidates(run2)
        self.assertEqual(
            self.review_no_candidates(run2, "--accept-history-rebaseline"),
            0,
        )

    def test_non_git_file_cap_never_becomes_silent_noop(self) -> None:
        nongit = self.root / "nongit"
        (nongit / ".agent-memory").mkdir(parents=True)
        nongit_id = "00000000-0000-4000-8000-000000000003"
        (nongit / ".agent-memory" / "config.json").write_text(
            json.dumps(
                {
                    "schemaVersion": 1,
                    "memoryId": nongit_id,
                    "sourcePath": ".agent-memory/CORE.md",
                }
            ),
            encoding="utf-8",
        )
        (nongit / ".agent-memory" / "CORE.md").write_text(
            memory(project="NonGit"),
            encoding="utf-8",
        )
        for index in range(LTMT.MAX_NON_GIT_FILES + 1):
            (nongit / f"f{index:05d}.txt").write_text("v1\n", encoding="utf-8")
        first = LTMT.non_git_source_snapshot(
            nongit,
            ".agent-memory/CORE.md",
            None,
        )
        self.assertTrue(first["snapshot"]["partial"])
        cursor = {"source": first["snapshot"]}
        (nongit / f"f{LTMT.MAX_NON_GIT_FILES:05d}.txt").write_text(
            "v2\n",
            encoding="utf-8",
        )
        second = LTMT.non_git_source_snapshot(
            nongit,
            ".agent-memory/CORE.md",
            cursor,
        )
        self.assertTrue(second["hasChanges"])
        self.assertTrue(second["truncated"])

    def test_non_git_external_file_symlink_is_always_partial(self) -> None:
        nongit = self.root / "nongit-external-link"
        nongit.mkdir()
        target = self.root / "outside.txt"
        target.write_text("v1\n", encoding="utf-8")
        (nongit / "outside-link.txt").symlink_to(target)

        first = LTMT.non_git_source_snapshot(
            nongit,
            ".agent-memory/CORE.md",
            None,
        )
        self.assertTrue(first["snapshot"]["partial"])
        self.assertTrue(
            any("escapes project root" in reason for reason in first["incompleteReasons"])
        )

        target.write_text("v2\n", encoding="utf-8")
        second = LTMT.non_git_source_snapshot(
            nongit,
            ".agent-memory/CORE.md",
            {"source": first["snapshot"]},
        )
        self.assertTrue(second["hasChanges"])
        self.assertTrue(second["truncated"])

    def test_non_git_internal_sensitive_symlink_is_quarantined(self) -> None:
        nongit = self.root / "nongit-sensitive-link"
        (nongit / ".agent-memory").mkdir(parents=True)
        env_secret = "VERY_PRIVATE_ENV_ALIAS_CONTENT"
        memory_secret = "VERY_PRIVATE_MEMORY_ALIAS_CONTENT"
        (nongit / ".env").write_text(env_secret, encoding="utf-8")
        (nongit / ".agent-memory" / "CORE.md").write_text(
            memory_secret,
            encoding="utf-8",
        )
        (nongit / "innocent-env.txt").symlink_to(".env")
        (nongit / "innocent-memory.md").symlink_to(
            ".agent-memory/CORE.md"
        )

        source = LTMT.non_git_source_snapshot(
            nongit,
            ".agent-memory/CORE.md",
            None,
        )

        self.assertTrue(source["snapshot"]["partial"])
        self.assertTrue(source["hasChanges"])
        self.assertIn(
            "sensitive-symlink-target",
            source["secretDetectors"],
        )
        manifest = source["snapshot"]["fileManifest"]
        for alias in ("innocent-env.txt", "innocent-memory.md"):
            entry = manifest[alias]
            self.assertEqual(entry["type"], "ignored-target-symlink")
            self.assertIn("linkHash", entry)
            self.assertIn("targetPathHash", entry)
            self.assertNotIn("hash", entry)
        serialized = json.dumps(source)
        self.assertNotIn(env_secret, serialized)
        self.assertNotIn(memory_secret, serialized)
        alias_context = {
            entry["path"]: entry for entry in source["context"]
        }
        self.assertTrue(alias_context["innocent-env.txt"]["quarantined"])
        self.assertEqual(alias_context["innocent-env.txt"]["excerpt"], "")
        self.assertTrue(alias_context["innocent-memory.md"]["quarantined"])
        self.assertEqual(alias_context["innocent-memory.md"]["excerpt"], "")

    def test_non_git_symlink_swap_cannot_redirect_excerpt(self) -> None:
        nongit = self.root / "nongit-link-swap"
        nongit.mkdir()
        public_text = "SAFE_PUBLIC_ALIAS_CONTENT"
        env_secret = "VERY_PRIVATE_ENV_ALIAS_CONTENT"
        (nongit / "safe.txt").write_text(public_text, encoding="utf-8")
        (nongit / ".env").write_text(env_secret, encoding="utf-8")
        alias = nongit / "innocent.txt"
        alias.symlink_to("safe.txt")
        original_redact = LTMT.redact_secrets
        swapped = False

        def swap_alias_after_descriptor_read(
            text: str,
        ) -> tuple[str, list[str]]:
            nonlocal swapped
            if not swapped and public_text in text:
                alias.unlink()
                alias.symlink_to(".env")
                swapped = True
            return original_redact(text)

        with mock.patch.object(
            LTMT,
            "redact_secrets",
            side_effect=swap_alias_after_descriptor_read,
        ):
            source = LTMT.non_git_source_snapshot(
                nongit,
                ".agent-memory/CORE.md",
                None,
            )

        self.assertTrue(swapped)
        alias_context = next(
            entry
            for entry in source["context"]
            if entry["path"] == "innocent.txt"
        )
        self.assertEqual(alias_context["excerpt"], public_text)
        self.assertNotIn(env_secret, json.dumps(source))

    def test_non_git_external_directory_symlink_is_partial(self) -> None:
        nongit = self.root / "nongit-external-dir-link"
        nongit.mkdir()
        outside = self.root / "outside-dir"
        outside.mkdir()
        (outside / "hidden.txt").write_text("hidden\n", encoding="utf-8")
        (nongit / "outside-dir").symlink_to(outside, target_is_directory=True)

        source = LTMT.non_git_source_snapshot(
            nongit,
            ".agent-memory/CORE.md",
            None,
        )

        self.assertTrue(source["snapshot"]["partial"])
        self.assertTrue(
            any("symlink" in reason for reason in source["incompleteReasons"])
        )

    def test_non_git_hash_error_is_partial_not_silently_skipped(self) -> None:
        nongit = self.root / "nongit-hash-error"
        nongit.mkdir()
        (nongit / "blocked.txt").write_text("blocked\n", encoding="utf-8")

        with mock.patch.object(
            LTMT,
            "fingerprint_regular_file",
            side_effect=OSError("permission denied"),
        ):
            source = LTMT.non_git_source_snapshot(
                nongit,
                ".agent-memory/CORE.md",
                None,
            )

        self.assertTrue(source["snapshot"]["partial"])
        self.assertTrue(source["hasChanges"])
        self.assertTrue(
            any("could not be fingerprinted" in reason for reason in source["incompleteReasons"])
        )

    def test_non_git_walk_error_is_partial(self) -> None:
        nongit = self.root / "nongit-walk-error"
        nongit.mkdir()
        blocked = nongit / "blocked-dir"

        def fake_walk(
            top: str,
            topdown: bool = True,
            onerror: object = None,
            followlinks: bool = False,
        ) -> object:
            self.assertTrue(topdown)
            self.assertFalse(followlinks)
            self.assertIsNotNone(onerror)
            onerror(PermissionError(13, "permission denied", str(blocked)))
            return iter([(str(nongit), [], [])])

        with mock.patch.object(LTMT.os, "walk", side_effect=fake_walk):
            source = LTMT.non_git_source_snapshot(
                nongit,
                ".agent-memory/CORE.md",
                None,
            )

        self.assertTrue(source["snapshot"]["partial"])
        self.assertTrue(
            any("could not be traversed" in reason for reason in source["incompleteReasons"])
        )

    def test_non_loopback_api_is_rejected_without_network_access(self) -> None:
        with self.assertRaisesRegex(LTMT.TrainingError, "loopback"):
            LTMT.read_registry_payload(
                "https://example.com",
                self.root / "missing-ports.json",
            )


if __name__ == "__main__":
    unittest.main()
