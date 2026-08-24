"""recall_project_memory 어댑터 테스트.

이 어댑터의 계약은 세 가지다: (1) AgentsToZ 메모리를 절대 쓰지 않는다,
(2) 무엇이 없든 exit 0으로 끝난다, (3) contested 항목을 확정 사실과 섞지 않는다.
테스트는 그 세 가지를 지킨다.
"""

import json
import os
import subprocess
import sys
import tempfile
import unittest

SCRIPTS = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts")
SCRIPT = os.path.join(SCRIPTS, "recall_project_memory.py")
sys.path.insert(0, SCRIPTS)

import recall_project_memory as rpm  # noqa: E402


def _run(*args, cwd=None):
    return subprocess.run([sys.executable, SCRIPT, *args],
                          capture_output=True, text=True, cwd=cwd, timeout=60)


class TestFindProjectRoot(unittest.TestCase):
    def test_finds_marker_in_start_dir(self):
        with tempfile.TemporaryDirectory() as d:
            os.makedirs(os.path.join(d, ".agent-memory"))
            open(os.path.join(d, ".agent-memory", "config.json"), "w").write("{}")
            self.assertEqual(rpm.find_project_root(d), os.path.abspath(d))

    def test_walks_up_to_marker(self):
        with tempfile.TemporaryDirectory() as d:
            os.makedirs(os.path.join(d, ".agent-memory"))
            open(os.path.join(d, ".agent-memory", "config.json"), "w").write("{}")
            deep = os.path.join(d, "a", "b", "c")
            os.makedirs(deep)
            self.assertEqual(rpm.find_project_root(deep), os.path.abspath(d))

    def test_returns_none_without_marker(self):
        with tempfile.TemporaryDirectory() as d:
            # 상위에 마커가 있으면 안 되므로 결과가 None이거나 d 밖의 경로여야 한다
            got = rpm.find_project_root(d)
            self.assertNotEqual(got, os.path.abspath(d))


class TestBuildDigest(unittest.TestCase):
    def test_empty_hits_yield_empty_string(self):
        self.assertEqual(rpm.build_digest({"hits": []}), "")
        self.assertEqual(rpm.build_digest({}), "")

    def test_settled_entry_rendered_with_section_and_reason(self):
        out = rpm.build_digest({
            "memoryId": "81aa80f5-41aa", "memoryAgent": "claude",
            "hits": [{"section": "Active Constraints", "selectionReason": "active-constraint",
                      "excerpt": "- 비밀값을 저장하지 않는다", "caution": False}],
        })
        self.assertIn("Active Constraints · active-constraint", out)
        self.assertIn("비밀값을 저장하지 않는다", out)
        self.assertIn("81aa80f5", out)
        self.assertNotIn("- - ", out)  # excerpt 앞 불릿이 중복되지 않는다

    def test_time_hint_adds_reverify_note(self):
        out = rpm.build_digest({"hits": [
            {"section": "Key Decisions", "excerpt": "x", "caution": False,
             "knowledgeTimeHint": "2026-07-24"}]})
        self.assertIn("2026-07-24", out)
        self.assertIn("재확인 필요", out)

    def test_contested_listed_separately_and_labelled(self):
        out = rpm.build_digest({"hits": [
            {"section": "Key Decisions", "excerpt": "확정된 것", "caution": False},
            {"section": "Contested Entries", "excerpt": "대립 중인 것", "caution": True},
        ]})
        self.assertIn("미해결 대립", out)
        # contested 항목이 확정 목록보다 뒤에, 별도 라벨 아래 온다
        self.assertLess(out.index("확정된 것"), out.index("미해결 대립"))
        self.assertLess(out.index("미해결 대립"), out.index("대립 중인 것"))

    def test_contested_only_still_labelled(self):
        out = rpm.build_digest({"hits": [
            {"section": "Contested Entries", "excerpt": "대립", "caution": True}]})
        self.assertIn("미해결 대립", out)


class TestGracefulDegradation(unittest.TestCase):
    def test_exit_zero_and_silent_without_agent_memory(self):
        with tempfile.TemporaryDirectory() as d:
            r = _run("--query", "무엇이든", "--root", d)
            self.assertEqual(r.returncode, 0)
            self.assertEqual(r.stdout.strip(), "")

    def test_json_reports_reason_without_agent_memory(self):
        with tempfile.TemporaryDirectory() as d:
            r = _run("--query", "무엇이든", "--root", d, "--format", "json")
            self.assertEqual(r.returncode, 0)
            payload = json.loads(r.stdout)
            self.assertFalse(payload["available"])
            self.assertEqual(payload["reason"], "no_agent_memory")
            self.assertEqual(payload["count"], 0)

    def test_header_format_always_emits_count(self):
        with tempfile.TemporaryDirectory() as d:
            r = _run("--query", "무엇이든", "--root", d, "--format", "header")
            self.assertEqual(r.returncode, 0)
            self.assertEqual(r.stdout.strip(), "C0")

    def test_never_writes_into_project(self):
        """어댑터는 읽기 전용 — AgentsToZ가 유일한 writer다."""
        with tempfile.TemporaryDirectory() as d:
            am = os.path.join(d, ".agent-memory")
            os.makedirs(am)
            open(os.path.join(am, "config.json"), "w").write(
                json.dumps({"schemaVersion": 1, "sourcePath": ".agent-memory/CORE.md"}))
            before = sorted(os.listdir(am))
            r = _run("--query", "무엇이든", "--root", d, "--format", "json")
            self.assertEqual(r.returncode, 0)
            self.assertEqual(sorted(os.listdir(am)), before)


class TestQueryHygiene(unittest.TestCase):
    def test_query_truncated_to_cap(self):
        self.assertEqual(rpm.MAX_QUERY_CHARS, 240)
        with tempfile.TemporaryDirectory() as d:
            r = _run("--query", "가" * 5000, "--root", d, "--format", "json")
            self.assertEqual(r.returncode, 0)   # 긴 질의로 죽지 않는다

    def test_limit_is_clamped(self):
        with tempfile.TemporaryDirectory() as d:
            for bad in ("0", "-3", "999"):
                r = _run("--query", "q", "--root", d, "--limit", bad, "--format", "json")
                self.assertEqual(r.returncode, 0, f"limit={bad}")


class TestLiveRepoRecall(unittest.TestCase):
    """이 저장소 자체가 AgentsToZ 연동 프로젝트이므로 실제 회상 경로를 탄다."""

    def setUp(self):
        self.repo = os.path.dirname(os.path.dirname(os.path.dirname(
            os.path.dirname(os.path.abspath(__file__)))))
        if not os.path.isfile(os.path.join(self.repo, ".agent-memory", "config.json")):
            self.skipTest("이 체크아웃에는 .agent-memory가 없음")

    def test_recall_returns_hits_and_digest(self):
        r = _run("--query", "플러그인 rename 매니페스트", "--root", self.repo, "--format", "json")
        self.assertEqual(r.returncode, 0)
        payload = json.loads(r.stdout)
        if not payload["available"]:
            self.skipTest(f"cs-memory 미해석: {payload['reason']}")
        self.assertGreater(payload["count"], 0)
        self.assertTrue(payload["digest"].startswith("과거 프로젝트 기억"))
        self.assertEqual(payload["projectRoot"], self.repo)


if __name__ == "__main__":
    unittest.main()
