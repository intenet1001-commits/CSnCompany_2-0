from __future__ import annotations

import json
import os
import stat
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "pre_pass.py"


def run_prepass(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        check=False,
        capture_output=True,
        text=True,
    )


class LearningQueueTests(unittest.TestCase):
    def test_40_concurrent_appends_are_lossless_unique_and_private(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            queue = Path(tmp) / "queue.json"
            processes = [
                subprocess.Popen(
                    [
                        sys.executable,
                        str(SCRIPT),
                        "learn-append",
                        "--plugin",
                        f"stress-{index}",
                        "--lesson",
                        f"lesson-{index}",
                        "--btw-file",
                        str(queue),
                    ],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                )
                for index in range(40)
            ]
            results = [process.communicate(timeout=30) for process in processes]

            self.assertTrue(
                all(process.returncode == 0 for process in processes),
                results,
            )
            items = json.loads(queue.read_text(encoding="utf-8"))
            ids = [item["id"] for item in items]
            self.assertEqual(len(items), 40)
            self.assertEqual(len(set(ids)), 40)
            self.assertEqual(
                stat.S_IMODE(os.stat(queue).st_mode),
                0o600,
            )

    def test_complete_provenance_is_idempotent_and_project_memory_requires_it(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            queue = Path(tmp) / "queue.json"
            common = (
                "learn-append",
                "--plugin",
                "project-memory:demo",
                "--lesson",
                "same lesson",
                "--source-run-id",
                "run-1",
                "--memory-id",
                "memory-1",
                "--source-range",
                "abc..def",
                "--btw-file",
                str(queue),
            )
            processes = [
                subprocess.Popen(
                    [sys.executable, str(SCRIPT), *common],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                )
                for _ in range(20)
            ]
            completed = [process.communicate(timeout=30) for process in processes]
            self.assertTrue(
                all(process.returncode == 0 for process in processes),
                completed,
            )
            results = [json.loads(stdout) for stdout, _stderr in completed]
            self.assertEqual(sum(bool(result["created"]) for result in results), 1)
            self.assertEqual(sum(bool(result["deduplicated"]) for result in results), 19)
            self.assertEqual(len(json.loads(queue.read_text(encoding="utf-8"))), 1)

            second_lesson = run_prepass(
                "learn-append",
                "--plugin",
                "project-memory:demo",
                "--lesson",
                "different lesson from the same source range",
                "--source-run-id",
                "run-1",
                "--memory-id",
                "memory-1",
                "--source-range",
                "abc..def",
                "--btw-file",
                str(queue),
            )
            self.assertEqual(second_lesson.returncode, 0, second_lesson.stderr)
            self.assertTrue(json.loads(second_lesson.stdout)["created"])
            self.assertEqual(len(json.loads(queue.read_text(encoding="utf-8"))), 2)

            incomplete = run_prepass(
                "learn-append",
                "--plugin",
                "project-memory:demo",
                "--lesson",
                "missing range",
                "--source-run-id",
                "run-2",
                "--memory-id",
                "memory-1",
                "--btw-file",
                str(queue),
            )
            self.assertNotEqual(incomplete.returncode, 0)
            self.assertIn("requires --source-run-id", json.loads(incomplete.stdout)["error"])

            legacy_producer = run_prepass(
                "learn-append",
                "--plugin",
                "ordinary-plugin",
                "--lesson",
                "provenance remains optional",
                "--source-run-id",
                "legacy-partial-run",
                "--btw-file",
                str(queue),
            )
            self.assertEqual(legacy_producer.returncode, 0, legacy_producer.stderr)

    def test_memory_candidate_key_deduplicates_paraphrases_from_one_entry_version(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            queue = Path(tmp) / "queue.json"
            candidate_key = "memory-" + ("a" * 24)
            common = (
                "--plugin", "project-memory:demo",
                "--source-run-id", f"memory:{candidate_key}",
                "--memory-id", "memory-1",
                "--source-range", "entry:abc@version-1",
                "--candidate-key", candidate_key,
                "--btw-file", str(queue),
            )
            first = run_prepass(
                "learn-append", "--lesson", "compact first phrasing", *common
            )
            second = run_prepass(
                "learn-append", "--lesson", "a paraphrase from the same entry version", *common
            )
            self.assertEqual(first.returncode, 0, first.stderr)
            self.assertEqual(second.returncode, 0, second.stderr)
            self.assertTrue(json.loads(first.stdout)["created"])
            self.assertTrue(json.loads(second.stdout)["deduplicated"])
            items = json.loads(queue.read_text(encoding="utf-8"))
            self.assertEqual(len(items), 1)
            self.assertEqual(items[0]["provenance"]["candidate_key"], candidate_key)

            collision = run_prepass(
                "learn-append", "--lesson", "different source",
                "--plugin", "project-memory:other",
                "--source-run-id", f"memory:{candidate_key}",
                "--memory-id", "memory-2",
                "--source-range", "entry:other@version-2",
                "--candidate-key", candidate_key,
                "--btw-file", str(queue),
            )
            self.assertNotEqual(collision.returncode, 0)
            self.assertIn("provenance", collision.stdout)

    def test_legacy_migration_is_stable_and_status_update_touches_one_entry(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            queue = Path(tmp) / "queue.json"
            queue.write_text(
                json.dumps(
                    [
                        {
                            "id": "old-a",
                            "type": "pending-patch",
                            "learning": "legacy duplicate",
                        },
                        {
                            "id": "old-b",
                            "type": "pending-patch",
                            "learning": "legacy duplicate",
                        },
                        {
                            "id": "duplicate-id",
                            "idea": "first canonical",
                            "status": "pending",
                        },
                        {
                            "id": "duplicate-id",
                            "idea": "second canonical",
                            "status": "pending",
                        },
                    ]
                ),
                encoding="utf-8",
            )

            digest = run_prepass("session-digest", "--btw-file", str(queue))
            self.assertEqual(digest.returncode, 0, digest.stderr)
            migrated = json.loads(queue.read_text(encoding="utf-8"))
            migrated_ids = [item["id"] for item in migrated]
            self.assertEqual(len(set(migrated_ids)), 4)
            self.assertTrue(all(item["status"] == "pending" for item in migrated))
            self.assertTrue(migrated[0]["id"].startswith("btw-legacy-"))
            self.assertTrue(migrated[1]["id"].startswith("btw-legacy-"))

            second_digest = run_prepass("session-digest", "--btw-file", str(queue))
            self.assertEqual(second_digest.returncode, 0, second_digest.stderr)
            self.assertEqual(
                migrated_ids,
                [item["id"] for item in json.loads(queue.read_text(encoding="utf-8"))],
            )

            update = run_prepass(
                "learn-update-status",
                "--id",
                "duplicate-id",
                "--status",
                "promoted",
                "--btw-file",
                str(queue),
            )
            self.assertEqual(update.returncode, 0, update.stderr)
            self.assertEqual(json.loads(update.stdout)["updated_count"], 1)
            after = json.loads(queue.read_text(encoding="utf-8"))
            self.assertEqual(
                sum(item.get("status") == "promoted" for item in after),
                1,
            )

    def test_result_errors_exit_nonzero_and_do_not_overwrite_bad_queue(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            queue = Path(tmp) / "queue.json"
            bad_content = "{ definitely not json"
            queue.write_text(bad_content, encoding="utf-8")

            append = run_prepass(
                "learn-append",
                "--plugin",
                "ordinary-plugin",
                "--lesson",
                "must not erase corruption",
                "--btw-file",
                str(queue),
            )
            self.assertNotEqual(append.returncode, 0)
            self.assertIn("error", json.loads(append.stdout))
            self.assertEqual(queue.read_text(encoding="utf-8"), bad_content)

            missing = run_prepass(
                "learn-update-status",
                "--id",
                "missing",
                "--status",
                "promoted",
                "--btw-file",
                str(Path(tmp) / "missing.json"),
            )
            self.assertNotEqual(missing.returncode, 0)
            result = json.loads(missing.stdout)
            self.assertFalse(result["updated"])
            self.assertIn("error", result)

    def test_version_check_includes_codex_and_marketplace_versions(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            plugin = Path(tmp) / "plugin"
            (Path(tmp) / ".claude-plugin").mkdir(parents=True)
            (plugin / ".claude-plugin").mkdir(parents=True)
            (plugin / ".codex-plugin").mkdir(parents=True)
            (plugin / "skills" / "primary").mkdir(parents=True)
            (Path(tmp) / ".claude-plugin" / "marketplace.json").write_text(
                json.dumps(
                    {
                        "plugins": [
                            {
                                "name": "fixture",
                                "source": "./plugin",
                                "version": "0.9.0",
                            }
                        ]
                    }
                ),
                encoding="utf-8",
            )
            (plugin / "VERSION").write_text("1.1.0\n", encoding="utf-8")
            (plugin / ".claude-plugin" / "plugin.json").write_text(
                json.dumps({"version": "1.1.0"}),
                encoding="utf-8",
            )
            (plugin / ".codex-plugin" / "plugin.json").write_text(
                json.dumps({"version": "1.0.0"}),
                encoding="utf-8",
            )
            (plugin / "skills" / "primary" / "SKILL.md").write_text(
                "---\nname: primary\nversion: 1.1.0\n---\n",
                encoding="utf-8",
            )
            checked = run_prepass("version-check", str(plugin))
            self.assertNotEqual(checked.returncode, 0)
            result = json.loads(checked.stdout)
            self.assertFalse(result["ok"])
            self.assertEqual(
                result["sources"][".codex-plugin/plugin.json"],
                "1.0.0",
            )
            self.assertEqual(result["sources"]["marketplace.json"], "0.9.0")

    def test_bundled_skill_agents_metadata_does_not_hide_plugin_root(self) -> None:
        resolved = run_prepass("resolve-partner", "learn")
        self.assertEqual(resolved.returncode, 0, resolved.stderr)
        result = json.loads(resolved.stdout)
        self.assertTrue(result["found"])
        self.assertEqual(result["type"], "SKILL")
        self.assertEqual(result["plugin_name"], "cs-memory")
        self.assertEqual(
            result["invocation"],
            "cs-memory:learn",
        )


if __name__ == "__main__":
    unittest.main()
