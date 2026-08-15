from __future__ import annotations

import json
import unittest
from html.parser import HTMLParser
from pathlib import Path


ROOT = Path(__file__).resolve().parents[5]


class BalancedHtmlParser(HTMLParser):
    VOID = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "param", "source", "track", "wbr"}

    def __init__(self) -> None:
        super().__init__()
        self.stack: list[str] = []
        self.errors: list[str] = []

    def handle_starttag(self, tag: str, attrs) -> None:
        if tag not in self.VOID:
            self.stack.append(tag)

    def handle_endtag(self, tag: str) -> None:
        if not self.stack or self.stack[-1] != tag:
            self.errors.append(f"unexpected </{tag}> after {self.stack[-1:]}")
            return
        self.stack.pop()


class MemorySurfaceContractTests(unittest.TestCase):
    def read(self, relative: str) -> str:
        return (ROOT / relative).read_text(encoding="utf-8")

    def payload(self, relative: str) -> dict:
        return json.loads(self.read(relative))

    def test_memory_plugin_has_one_read_only_learning_surface(self) -> None:
        plugin = ROOT / "plugins/cs-core-memory-v1"
        skill_names = sorted(path.parent.name for path in (plugin / "skills").glob("*/SKILL.md"))
        self.assertEqual(skill_names, ["learn", "schedule", "status", "upgrade"])
        self.assertFalse((plugin / "agents/memory-keeper.md").exists())
        self.assertFalse((plugin / "skills/cs-core-memory/SKILL.md").exists())

        learn = self.read("plugins/cs-core-memory-v1/skills/learn/SKILL.md")
        self.assertIn("read-only consumer", learn)
        self.assertIn("--candidate-key", learn)
        self.assertIn("next --limit 5", learn)
        self.assertNotIn("long_term_memory_training.py", learn)

    def test_ceo_recalls_project_memory_before_decomposition(self) -> None:
        ceo = self.read("plugins/cs-ceo-v15/agents/ceo.md")
        recall = ceo.index("#### Phase G.5 — Project Memory Context Injection")
        phase_minus_three = ceo.index("### Phase -3:")
        phase_one = ceo.index("### Phase 1:")
        self.assertLess(recall, phase_minus_three)
        self.assertLess(recall, phase_one)
        self.assertIn(".agent-memory/config.json", ceo[recall:phase_minus_three])
        self.assertIn('python "$MEMORY_RECALL" recall', ceo[recall:phase_minus_three])
        self.assertIn("--limit 5", ceo[recall:phase_minus_three])
        self.assertIn("selectionReason=active-constraint", ceo[recall:phase_minus_three])
        self.assertIn("cs-memory:learn pending", ceo)
        self.assertIn("actionablePending", ceo)
        self.assertIn("- Skill", ceo.split("---", 2)[1])
        self.assertNotIn("MEMORY_KEEPER=", ceo)

    def test_cs_end_delegates_storage_to_agents_to_z_owner(self) -> None:
        closing = self.read("plugins/cs-end-v3/commands/cs-end.md")
        handoff = closing.index("## Phase 1.5 — Project Memory Owner Handoff")
        learning_gate = closing.index("## Phase 2 —")
        self.assertLess(handoff, learning_gate)
        phase = closing[handoff:learning_gate]
        self.assertIn("remember-session/SKILL.md", phase)
        self.assertIn("mark-remembered", phase)
        self.assertIn("memory_learning.py", phase)
        self.assertNotIn("memory-keeper", phase)
        self.assertNotIn("CORE_MEMORY_SUMMARY", closing)
        self.assertNotIn('mkdir -p "$HOME/.claude/core-memory"', closing)
        codex = self.payload("plugins/cs-end-v3/.codex-plugin/plugin.json")
        self.assertEqual(codex.get("skills"), "./skills/")
        adapter = self.read("plugins/cs-end-v3/skills/cs-end/SKILL.md")
        self.assertIn("../../commands/cs-end.md", adapter)

    def test_memory_manual_html_is_structurally_balanced(self) -> None:
        parser = BalancedHtmlParser()
        parser.feed(self.read("docs/cs-memory-manual.html"))
        parser.close()
        self.assertEqual(parser.errors, [])
        self.assertEqual(parser.stack, [])

    def test_versions_match_claude_codex_and_marketplace(self) -> None:
        marketplace = self.payload(".claude-plugin/marketplace.json")
        entries = {item["name"]: item for item in marketplace["plugins"]}
        cases = [
            ("cs-memory", "plugins/cs-core-memory-v1"),
            ("cs-ceo", "plugins/cs-ceo-v15"),
            ("cs-end", "plugins/cs-end-v3"),
        ]
        for name, relative in cases:
            expected = self.read(relative + "/VERSION").strip()
            claude = self.payload(relative + "/.claude-plugin/plugin.json")
            codex = self.payload(relative + "/.codex-plugin/plugin.json")
            self.assertEqual(claude["version"], expected, name)
            self.assertEqual(codex["version"], expected, name)
            self.assertEqual(entries[name]["version"], expected, name)

    def test_periodic_collector_never_schedules_a_model_command(self) -> None:
        schedule = self.read("plugins/cs-core-memory-v1/skills/learn/scripts/memory_learning_schedule.py")
        self.assertIn('"collect"', schedule)
        self.assertIn('"--quiet"', schedule)
        self.assertNotIn("claude -p", schedule)
        self.assertNotIn("codex exec", schedule)
        self.assertNotIn("dangerously-skip", schedule)


if __name__ == "__main__":
    unittest.main()
