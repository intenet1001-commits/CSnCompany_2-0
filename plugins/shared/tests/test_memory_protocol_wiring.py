"""AgentsToZ ↔ CSnCompany 회상 이음매 배선 검증.

왜 이 테스트가 있는가
--------------------
MEMORY-PROTOCOL [R-c]는 한동안 `~/.claude/core-memory/CORE.md`를 가리키고 있었다. 그 경로는
AgentsToZ 이관 때 폐기됐고 이후 어떤 머신에도 존재하지 않는다. [R-c]는 "파일이 없으면 조용히
스킵"하도록 설계돼 있었으므로 **아무 에러 없이 항상 스킵됐고**, 리드 4개는 전략 메모리를 한 번도
읽지 않으면서 `recall: C0`을 정상 출력했다. 침묵하는 graceful degradation이 끊긴 배선을 가린 것이다.

문서만으로는 이 부류의 결함을 잡을 수 없다 — 경로가 살아 있는지, 리드가 실제로 프로토콜을
참조하는지를 기계로 확인해야 한다. 이 테스트가 그 역할을 한다.
"""

import os
import re
import unittest

SHARED = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PLUGINS = os.path.dirname(SHARED)
PROTOCOL = os.path.join(SHARED, "MEMORY-PROTOCOL.md")

# MEMORY-PROTOCOL "적용 범위"가 표준 Phase R 수행자로 선언한 파일들
STANDARD_LEADS = [
    os.path.join(PLUGINS, "CS-plan-v21", "agents", "plan-lead.md"),
    os.path.join(PLUGINS, "cs-design-v20", "agents", "design-lead.md"),
    os.path.join(PLUGINS, "cs-ship-v1", "agents", "ship-lead.md"),
    os.path.join(PLUGINS, "CS-test-v26", "agents", "test-lead.md"),
    os.path.join(PLUGINS, "CS-codebase-review-v29", "skills", "CS-codebase-review", "SKILL.md"),
]

LEGACY_STORE = re.compile(r"~/\.claude/core-memory")


def _read(path):
    with open(path, encoding="utf-8") as f:
        return f.read()


class TestNoLegacyStoreReference(unittest.TestCase):
    """폐기된 전역 core-memory 저장소를 실행 경로에서 가리키지 않는다."""

    def test_shared_protocols_never_point_at_legacy_store(self):
        offenders = []
        for name in os.listdir(SHARED):
            p = os.path.join(SHARED, name)
            if not os.path.isfile(p) or not name.endswith(".md"):
                continue
            for i, line in enumerate(_read(p).splitlines(), 1):
                if not LEGACY_STORE.search(line):
                    continue
                # 금지를 서술하는 문장은 허용 — 가리키는 것과 막는 것은 다르다
                if any(k in line for k in ("폐기", "금지", "폴백하는 것", "소유권")):
                    continue
                offenders.append(f"{name}:{i}: {line.strip()[:90]}")
        self.assertEqual(offenders, [], "폐기된 core-memory 저장소를 참조함:\n" + "\n".join(offenders))

    def test_protocol_names_the_agentstoz_path(self):
        text = _read(PROTOCOL)
        self.assertIn(".agent-memory", text,
                      "MEMORY-PROTOCOL이 AgentsToZ 저장 경로를 명시하지 않음")


class TestRecallAdapterIsReachable(unittest.TestCase):
    """프로토콜이 지시하는 어댑터가 실제로 존재해야 한다."""

    def test_adapter_referenced_by_protocol_exists(self):
        text = _read(PROTOCOL)
        m = re.search(r"shared/(scripts/[A-Za-z0-9_./-]+\.py)", text)
        self.assertIsNotNone(m, "[R-c]가 어댑터 스크립트를 지시하지 않음")
        self.assertTrue(os.path.isfile(os.path.join(SHARED, m.group(1))),
                        f"프로토콜이 가리키는 {m.group(1)} 가 없음")

    def test_adapter_is_read_only_by_construction(self):
        """어댑터가 쓰기 API를 쓰지 않는다 — AgentsToZ가 유일한 writer다."""
        src = _read(os.path.join(SHARED, "scripts", "recall_project_memory.py"))
        body = "\n".join(l for l in src.splitlines() if not l.strip().startswith("#"))
        for forbidden in ("open(", "os.remove", "os.rename", "shutil.", "mkdir", "makedirs"):
            self.assertNotIn(forbidden, body,
                             f"회상 어댑터에 쓰기 가능 호출 `{forbidden}` 존재")


class TestLeadsDeclarePhaseR(unittest.TestCase):
    """적용 범위에 선언된 리드는 실제로 프로토콜을 참조하고 준수 헤더를 낸다."""

    def test_every_standard_lead_references_protocol_and_header(self):
        missing = []
        for path in STANDARD_LEADS:
            if not os.path.isfile(path):
                missing.append(f"{path} (파일 없음)")
                continue
            text = _read(path)
            rel = os.path.relpath(path, PLUGINS)
            if "MEMORY-PROTOCOL" not in text:
                missing.append(f"{rel}: MEMORY-PROTOCOL 참조 없음")
            if "recall: E" not in text:
                missing.append(f"{rel}: `recall: E<n>/C<n>/N<n>` 헤더 지시 없음")
        self.assertEqual(missing, [], "Phase R 미배선:\n" + "\n".join(missing))

    def test_scope_section_lists_the_leads_we_check(self):
        """적용 범위 문서와 이 테스트의 목록이 어긋나지 않게 묶어 둔다."""
        scope = _read(PROTOCOL).split("## 적용 범위", 1)
        self.assertEqual(len(scope), 2, "MEMORY-PROTOCOL에 '적용 범위' 섹션이 없음")
        body = scope[1]
        for token in ("plan-lead", "design-lead", "ship-lead", "test-lead", "CS-codebase-review"):
            self.assertIn(token, body, f"적용 범위에 {token}가 선언되지 않음")


if __name__ == "__main__":
    unittest.main()
