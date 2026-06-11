---
description: "PR 전 최종 검증 게이트 — 스펙 준수·커버리지·커밋 품질 검사 (/cs-ship [path])"
allowed-tools: Bash, Read, Write, Edit, Glob, Grep, Agent, AskUserQuestion
---

# /cs-ship [path]

구현 완료 후 PR 생성 전 4-agent 팀이 최종 검증을 수행합니다. 스펙 미준수, 커버리지 갭, 불량 커밋 메시지를 차단합니다.

## 서브커맨드

| 커맨드 | 설명 |
|--------|------|
| `/cs-ship` | 현재 디렉토리 전체 검증 |
| `/cs-ship [path]` | 지정 경로 검증 |
| `/cs-ship --fix` | BLOCKED/WARNINGS 시 MISSING 항목 자동 수정 후 재검증 (최대 2라운드, 커밋은 수동) |

## 에이전트 팀

| 에이전트 | 역할 | 모델 |
|----------|------|------|
| **ship-lead** | 팀 리더 — 결과 종합 + SHIP-REPORT.md 생성 | opus |
| **pre-pr-validator** | PLAN.md vs 실제 구현 3-Way 검증 | sonnet |
| **coverage-auditor** | 테스트 커버리지 갭 탐지 | sonnet |
| **commit-crafter** | diff 분석 → 고품질 커밋 메시지 생성 | haiku |

## 합격 기준 (Pass = ship 승인)

- 스펙 준수: PLAN.md 항목 ≥ 90% 구현됨
- 커버리지: Critical 경로 테스트 존재 AND 실행 green (FAILING 1개라도 있으면 BLOCKED)
- 커밋: 의미 있는 메시지 (WIP/fix misc 금지)

## 실행 흐름

`skills/cs-ship/SKILL.md` 참고
