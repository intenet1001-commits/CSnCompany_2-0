---
description: "AI Teams web testing - runs the latest CS-test-v* sibling domain protocol"
allowed-tools: Bash, Read, Write, Edit, Glob, Grep, Task, TaskCreate, TaskUpdate, TaskList, TaskGet, TeamCreate, TeamDelete, SendMessage, ToolSearch
---

# /CS-test [URL]

전문 Claude AI 에이전트들이 팀을 구성하여 웹 앱을 종합 테스트합니다.

## 사용법

```
/CS-test https://example.com
/CS-test https://example.com --skip-build
```

## 실행

이 커맨드는 최신 `CS-test-v*` 도메인의 SKILL.md 프로토콜을 실행합니다.
(도메인은 cs-experiencing-v*과 같은 레벨의 plugins/ 디렉토리에 위치 — 버전은 디렉토리명이 단일 진실, `ls -d ... | sort -V`로 항상 최신을 해석)

```bash
BASE="$HOME/.claude/plugins/marketplaces/CSnCompany_2-0/plugins"
LATEST_TEST=$(ls -d "$BASE/CS-test-v"* 2>/dev/null | sort -V | tail -1)
```

1. `$LATEST_TEST/VERSION` 읽기 → 현재 버전 확인
2. `$LATEST_TEST/skills/CS-test/SKILL.md` 프로토콜 실행
3. URL을 대상으로 멀티 에이전트 팀 가동

## 에이전트 팀

에이전트 구성·개수의 단일 진실은 `$LATEST_TEST/commands/CS-test.md`의 로스터다 — 여기에 복제하지 않는다.

## 출력

`tests/results/REPORT.md` — 종합 테스트 리포트
