---
description: "5관점 병렬 디자인 리뷰 - visual hierarchy, interaction quality, design system consistency, responsive/accessibility, anti-pattern detection"
allowed-tools: Bash, Read, Write, Edit, Glob, Grep, Task, TaskCreate, TaskUpdate, TaskList, TaskGet, TeamCreate, TeamDelete, SendMessage
---

# /cs-design [path] [--focus aspect] [--fix]

CS-design 도메인의 5-agent 병렬 디자인 리뷰를 실행합니다.

## 사용법

```
/cs-design                              # 현재 디렉토리 전체 분석
/cs-design src/                         # 특정 경로 분석
/cs-design --focus visual               # 시각 계층만 분석
/cs-design --focus interaction          # 인터랙션 품질만 분석
/cs-design --focus consistency          # 디자인 시스템 일관성만 분석
/cs-design --focus responsive           # 반응형/접근성만 분석
/cs-design --focus antipatterns         # 안티패턴 탐지만 실행
/cs-design --fix                        # 발견된 안티패턴 자동 수정
```

## 분석 관점 (5개)

visual-hierarchy · interaction-quality · design-system-consistency · responsive-accessibility · anti-pattern-detector
— 각 관점의 역할·분석 항목·출력 스키마는 `agents/<name>.md` 카드가 단일 소스 (plugins/shared/AGENT-CARD.md 표준).

## 실행

`skills/cs-design/SKILL.md` 프로토콜을 따라 design-lead 에이전트를 스폰합니다.
