from __future__ import annotations

import importlib.util
import plistlib
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "memory_learning_schedule.py"
SPEC = importlib.util.spec_from_file_location("memory_learning_schedule", SCRIPT)
assert SPEC and SPEC.loader
SCHEDULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(SCHEDULE)


class ScheduleGenerationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.learning = self.root / "memory_learning.py"
        self.learning.write_text("print('fixture')\n", encoding="utf-8")
        self.state = self.root / "state.json"
        self.uv = self.root / "uv"
        self.uv.write_text("", encoding="utf-8")

    def tearDown(self) -> None:
        self.temp.cleanup()

    def test_registry_command_is_shell_free_quiet_collection(self) -> None:
        command = SCHEDULE.build_collect_command(
            self.uv, self.learning, self.state, "registry", None, self.root
        )
        self.assertEqual(command[:5], [
            str(self.uv.resolve()), "run", "--quiet", "--no-project", "python"
        ])
        self.assertIn("collect", command)
        self.assertIn("--quiet", command)
        self.assertIn("--no-cwd", command)
        self.assertNotIn("--root", command)

    def test_pc_and_folder_scopes_are_explicit_and_bounded(self) -> None:
        pc = SCHEDULE.build_collect_command(
            self.uv, self.learning, self.state, "pc", None, self.root
        )
        self.assertEqual(pc[pc.index("--root") + 1], str(self.root.resolve()))
        self.assertEqual(pc[pc.index("--max-depth") + 1], "8")
        folder = self.root / "projects"
        folder.mkdir()
        scoped = SCHEDULE.build_collect_command(
            self.uv, self.learning, self.state, "folder", folder, self.root
        )
        self.assertEqual(scoped[scoped.index("--root") + 1], str(folder.resolve()))
        self.assertIn("--no-registry", scoped)

    def test_launchd_plist_uses_argument_array_and_interval(self) -> None:
        command = SCHEDULE.build_collect_command(
            self.uv, self.learning, self.state, "registry", None, self.root
        )
        payload = SCHEDULE.launchd_plist(command, 6, self.root / "latest.log")
        parsed = plistlib.loads(payload)
        self.assertEqual(parsed["Label"], SCHEDULE.LABEL)
        self.assertEqual(parsed["ProgramArguments"], command)
        self.assertEqual(parsed["StartInterval"], 6 * 60 * 60)
        self.assertTrue(parsed["RunAtLoad"])
        self.assertNotIn("Program", parsed)

    def test_systemd_units_use_one_shot_and_persistent_timer(self) -> None:
        command = SCHEDULE.build_collect_command(
            self.uv, self.learning, self.state, "registry", None, self.root
        )
        service, timer = SCHEDULE.systemd_units(command, 6)
        self.assertIn("Type=oneshot", service)
        self.assertIn("Environment=UV_CACHE_DIR=%h/.csncompany/uv-cache", service)
        self.assertIn("OnUnitActiveSec=6h", timer)
        self.assertIn("Persistent=true", timer)
        self.assertIn(str(self.learning), service)

    def test_invalid_scope_and_relative_folder_fail_closed(self) -> None:
        with self.assertRaisesRegex(SCHEDULE.ScheduleError, "scope"):
            SCHEDULE.build_collect_command(
                self.uv, self.learning, self.state, "other", None, self.root
            )
        with self.assertRaisesRegex(SCHEDULE.ScheduleError, "absolute"):
            SCHEDULE.build_collect_command(
                self.uv, self.learning, self.state, "folder", Path("relative"), self.root
            )


if __name__ == "__main__":
    unittest.main()
