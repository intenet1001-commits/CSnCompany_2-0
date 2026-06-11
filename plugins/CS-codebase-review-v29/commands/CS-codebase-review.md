---
description: "5-agent parallel codebase review - Architecture, Quality, Security, Performance, Maintainability"
allowed-tools: Bash, Read, Write, Edit, Glob, Grep, Task
---

# /CS-codebase-review [path] [--focus aspect]

전체 코드베이스를 5가지 관점에서 병렬 분석하여 종합 리뷰 리포트를 생성합니다.

## 사용법

```
/CS-codebase-review                          # 전체 코드베이스 분석
/CS-codebase-review src/                     # 특정 경로만 분석
/CS-codebase-review --focus security         # 보안 관점만 분석
/CS-codebase-review --focus architecture     # 아키텍처 관점만 분석
```

## 실행

이 커맨드는 이 플러그인의 스킬 프로토콜을 실행합니다:

1. `${CLAUDE_PLUGIN_ROOT}/VERSION` 읽기 → 현재 버전 확인
2. `${CLAUDE_PLUGIN_ROOT}/skills/CS-codebase-review/SKILL.md` 프로토콜 실행
   (Phase 0 Python pre-pass → Phase 1 5-agent 병렬 리뷰 → Phase 1.5 커버리지 게이트 & 적대적 검증 → Phase 2 종합 리포트)

검증 프로토콜: plugins/shared/LOOP-PROTOCOL.md + plugins/shared/agents/verifier.md를 따른다.

## 에이전트 팀 (5개 병렬)

| 에이전트 | 분석 관점 |
|---------|---------|
| **architecture** | 의존성 구조, 레이어 분리 |
| **quality** | 코드 품질, 복잡도 |
| **security** | 취약점, 하드코딩 |
| **performance** | 병목, 비효율 패턴 |
| **maintainability** | 유지보수성, struct 동기화 |

## 출력

종합 코드 리뷰 리포트 — 전체 등급(A~F, CONFIRMED 이슈 기준), 검증 요약, 커버리지 %, 우선순위 상위 5개 액션 아이템
