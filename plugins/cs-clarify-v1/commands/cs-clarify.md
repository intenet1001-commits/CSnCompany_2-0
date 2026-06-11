---
description: "요구사항 명료화 — 플랜/구현 전 숨겨진 가정과 범위를 명확히 함 (/cs-clarify [요청 설명])"
allowed-tools: Bash, Read, Write, Edit, Glob, Grep, Agent, AskUserQuestion
---

# /cs-clarify [요청 설명]

플랜 생성 전에 요구사항을 명료화합니다. 4개 에이전트가 Socratic 방식으로 숨겨진 가정, 범위 과대설계, 모호한 성공 기준을 제거합니다.

## 서브커맨드

| 커맨드 | 설명 |
|--------|------|
| `/cs-clarify "[요청]"` | 전체 명료화 분석 (4-agent) |
| `/cs-clarify --quick "[요청]"` | 빠른 명료화 — 인터뷰 스킵, scope + assumptions만 실행 |

## 에이전트 팀

| 에이전트 | 역할 | 모델 |
|----------|------|------|
| **clarify-lead** | 팀 리더 — 결과 종합 + CLARIFY.md 생성 | opus |
| **requirements-interviewer** | Socratic 질문 생성 (최대 3라운드) | sonnet |
| **scope-validator** | 과대설계 탐지 + 단순화 제안 | sonnet |
| **assumption-mapper** | 숨겨진 가정 명시화 | sonnet |

> 3개 워커는 **순차 실행** (interviewer → scope-validator → assumption-mapper, 병렬 스폰 금지).
> ready_for_plan=false 시 최대 2회 재명료화 루프 (--quick: 1회).

## 실행 흐름

`skills/cs-clarify/SKILL.md` 참고
