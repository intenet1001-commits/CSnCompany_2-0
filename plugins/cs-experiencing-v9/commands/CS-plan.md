---
description: "TDD + Clean Architecture 4-agent planning - runs the latest CS-plan-v* sibling domain protocol"
allowed-tools: Bash, Read, Write, Edit, Glob, Grep, Task, TaskCreate, TaskUpdate, TaskList, TaskGet, TeamCreate, TeamDelete, SendMessage
---

# /CS-plan [기능 설명]

TDD + Clean Architecture 기반의 즉시 실행 가능한 코딩 플랜을 자동 생성합니다.
4개 전문 에이전트가 병렬로 도메인 분석, 아키텍처 설계, 테스트 전략, 구현 체크리스트를 생성합니다.

## 사용법

```
/CS-plan "기능 설명"
/CS-plan --lang typescript "기능 설명"
/CS-plan --output docs/plans "기능 설명"
```

## 실행

이 커맨드는 최신 `CS-plan-v*` 도메인의 SKILL.md 프로토콜을 실행합니다.
(도메인은 cs-experiencing-v*과 같은 레벨의 plugins/ 디렉토리에 위치 — 버전은 디렉토리명이 단일 진실, `ls -d ... | sort -V`로 항상 최신을 해석)

```bash
BASE="$HOME/.claude/plugins/marketplaces/CSnCompany_2-0/plugins"
LATEST_PLAN=$(ls -d "$BASE/CS-plan-v"* 2>/dev/null | sort -V | tail -1)
```

1. `$LATEST_PLAN/VERSION` 읽기 → 현재 버전 확인
2. `$LATEST_PLAN/skills/CS-plan/SKILL.md` 프로토콜 실행

## 에이전트 팀 (4개 병렬)

| 에이전트 | 역할 | 출력 파일 |
|---------|------|---------|
| **domain-analyst** | DDD 도메인 분석 (Aggregate, VO, Event) | `domain-analysis.md` |
| **arch-designer** | Clean Architecture 4레이어 설계 | `architecture.md` |
| **tdd-strategist** | TDD 테스트 전략 (Red-Green-Refactor) | `tdd-strategy.md` |
| **checklist-builder** | Inside-Out 구현 체크리스트 | `implementation-checklist.md` |

## 출력

```
.tdd-plans/
├── domain-analysis.md
├── architecture.md
├── tdd-strategy.md
├── implementation-checklist.md
└── PLAN.md  ← 종합 플랜 (빠른 시작 가이드)
```
