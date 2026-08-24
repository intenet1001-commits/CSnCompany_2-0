#!/usr/bin/env python3
"""AgentsToZ 프로젝트 장기기억 회상 어댑터 (읽기 전용, 모델 호출 없음).

MEMORY-PROTOCOL [R-c] STRATEGIC 단계의 단일 진입점.

왜 이 어댑터인가
----------------
AgentsToZ가 `<PROJECT_ROOT>/.agent-memory/`에 전략 메모리를 적재하고, CSnCompany는 그것을
읽어 fan-out 품질을 올린다. 그런데 그 소비 경로를 리드마다 따로 구현하면
(a) 프로젝트 루트 탐색, (b) cs-memory 플러그인 경로 해석(Claude 마켓플레이스 / Codex 캐시 /
repo-local), (c) 부재 시 graceful degradation, (d) contested 항목 취급 규칙이 리드 수만큼
갈라진다. cs-ceo Phase G.5가 이미 (a)(b)를 20여 줄 bash로 풀어 두었으므로, 그 로직을 여기
한 곳에 모으고 나머지 리드는 이 스크립트만 호출한다.

계약
----
- **절대 쓰지 않는다.** AgentsToZ가 프로젝트 메모리의 유일한 writer다 (CORE.md 전략 패턴).
- 무엇이 없든 **exit 0**으로 끝난다. 회상 실패가 리드를 막아서는 안 된다.
- `caution: true`(Contested Entries 소속) 항목은 확정 사실이 아니라 **미해결 대립**으로 표시한다.
- `knowledgeTimeHint`가 있으면 함께 노출한다 — 오래된 주장은 현재 저장소 증거로 재검증해야 한다.
- 질의는 240자로 자른다. 원문 전체·비밀값·raw 로그가 질의에 실려 들어가는 것을 막는 마지막 방어선.

사용
----
    python3 recall_project_memory.py --query "<핵심 명사 몇 개>" [--root DIR] [--limit 5]
                                     [--format digest|json|header]

    digest : 워커 CONTEXT에 그대로 붙여 넣는 텍스트 (기본값)
    json   : 프로그램 소비용 원본 구조
    header : `recall:` 헤더에 쓸 C<n> 숫자 한 줄
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys

MAX_QUERY_CHARS = 240
DEFAULT_LIMIT = 5
RECALL_TIMEOUT_SEC = 20


def find_project_root(start: str) -> str | None:
    """`.agent-memory/config.json`을 가진 가장 가까운 상위 디렉터리."""
    cur = os.path.abspath(start)
    while True:
        if os.path.isfile(os.path.join(cur, ".agent-memory", "config.json")):
            return cur
        parent = os.path.dirname(cur)
        if parent == cur:
            return None
        cur = parent


def _versioned_candidates(pattern_dir: str, prefix: str) -> list[str]:
    """`<prefix>*` 디렉터리를 버전 오름차순 비슷하게 정렬해 반환."""
    if not os.path.isdir(pattern_dir):
        return []
    hits = [
        os.path.join(pattern_dir, n)
        for n in os.listdir(pattern_dir)
        if n.startswith(prefix) and os.path.isdir(os.path.join(pattern_dir, n))
    ]
    return sorted(hits)


def find_recall_script(project_root: str | None) -> str | None:
    """cs-memory의 memory_learning.py를 Claude/Codex/repo 순으로 해석한다.

    cs-ceo Phase G.5의 폴백 순서를 그대로 따른다 — 두 런타임 모두에서 동작해야 하고,
    마켓플레이스 미설치 머신(= repo만 체크아웃된 머신)에서도 동작해야 한다.
    """
    home = os.path.expanduser("~")
    roots: list[str] = []

    # 1) Claude 마켓플레이스 캐시
    roots += _versioned_candidates(
        os.path.join(home, ".claude", "plugins", "marketplaces", "CSnCompany_2-0", "plugins"),
        "cs-core-memory-v",
    )
    # 2) Codex 버전별 캐시
    roots += _versioned_candidates(
        os.path.join(home, ".codex", "plugins", "cache", "CSnCompany_2-0", "cs-memory"), ""
    )
    # 3) 이 스크립트가 사는 repo (shared/scripts/ → plugins/)
    here = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # plugins/shared
    roots += _versioned_candidates(os.path.dirname(here), "cs-core-memory-v")
    # 4) 대상 프로젝트가 곧 이 repo인 경우
    if project_root:
        roots += _versioned_candidates(os.path.join(project_root, "plugins"), "cs-core-memory-v")

    for r in reversed(roots):  # 최신 버전 우선
        p = os.path.join(r, "skills", "learn", "scripts", "memory_learning.py")
        if os.path.isfile(p):
            return p
    return None


def run_recall(script: str, project_root: str, query: str, limit: int) -> dict:
    """recall CLI 호출. 어떤 실패든 예외를 밖으로 내보내지 않는다."""
    for runner in (["python3"], ["uv", "run", "--quiet", "--no-project", "python"]):
        try:
            proc = subprocess.run(
                runner + [script, "recall", "--project", project_root,
                          "--query", query, "--limit", str(limit)],
                capture_output=True, text=True, timeout=RECALL_TIMEOUT_SEC,
            )
        except (OSError, subprocess.SubprocessError):
            continue
        if proc.returncode == 0 and proc.stdout.strip():
            try:
                return json.loads(proc.stdout)
            except json.JSONDecodeError:
                return {"ok": False, "reason": "recall_bad_json"}
    return {"ok": False, "reason": "recall_unavailable"}


def build_digest(payload: dict) -> str:
    """워커 CONTEXT에 verbatim 주입할 텍스트. 없으면 빈 문자열."""
    hits = payload.get("hits") or []
    if not hits:
        return ""

    settled = [h for h in hits if not h.get("caution")]
    contested = [h for h in hits if h.get("caution")]

    mid = (payload.get("memoryId") or "")[:8]
    agent = payload.get("memoryAgent") or "unknown"
    lines = [f"과거 프로젝트 기억 (AgentsToZ {agent}, memoryId {mid}) — 읽기 전용, 확정 사실 아님:"]

    for h in settled:
        section = h.get("section") or "?"
        why = h.get("selectionReason") or "match"
        text = (h.get("excerpt") or h.get("title") or "").strip().lstrip("- ")
        when = h.get("knowledgeTimeHint")
        stamp = f" [기록 시점 {when} — 현재 저장소 증거로 재확인 필요]" if when else ""
        lines.append(f"- ({section} · {why}) {text}{stamp}")

    if contested:
        lines.append("미해결 대립 (Contested — 어느 쪽도 확정 아님, 한쪽을 전제로 삼지 말 것):")
        for h in contested:
            text = (h.get("excerpt") or h.get("title") or "").strip().lstrip("- ")
            lines.append(f"- {text}")

    return "\n".join(lines)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--query", required=True, help="목표·도메인 핵심 명사 (한/영 동의어 포함)")
    ap.add_argument("--root", default=None, help="탐색 시작 디렉터리 (기본: 현재 디렉터리)")
    ap.add_argument("--limit", type=int, default=DEFAULT_LIMIT)
    ap.add_argument("--format", choices=("digest", "json", "header"), default="digest")
    args = ap.parse_args()

    query = " ".join(args.query.split())[:MAX_QUERY_CHARS]
    limit = max(1, min(args.limit, 10))

    project_root = find_project_root(args.root or os.getcwd())
    result = {"available": False, "reason": None, "count": 0, "contested": 0,
              "projectRoot": project_root, "hits": []}

    if project_root is None:
        result["reason"] = "no_agent_memory"          # AgentsToZ 미연동 프로젝트
    else:
        script = find_recall_script(project_root)
        if script is None:
            result["reason"] = "cs_memory_not_found"  # 이 머신에 cs-memory 없음
        else:
            payload = run_recall(script, project_root, query, limit)
            if not payload.get("ok"):
                result["reason"] = payload.get("reason") or "recall_failed"
            else:
                hits = payload.get("hits") or []
                result.update(
                    available=True, reason=None, hits=hits, count=len(hits),
                    contested=sum(1 for h in hits if h.get("caution")),
                    memoryId=payload.get("memoryId"), memoryAgent=payload.get("memoryAgent"),
                    digest=build_digest(payload),
                )

    if args.format == "json":
        print(json.dumps(result, ensure_ascii=False, indent=2))
    elif args.format == "header":
        print(f"C{result['count']}")
    else:
        # digest: 회상할 게 없으면 아무것도 출력하지 않는다 (주입 생략과 동일 의미)
        text = result.get("digest") or ""
        if text:
            print(text)
    return 0  # 회상 실패는 결코 리드를 막지 않는다


if __name__ == "__main__":
    sys.exit(main())
