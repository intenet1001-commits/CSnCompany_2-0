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

1. **visual-hierarchy** — 폰트 스케일, 색상 대비, 공간 구조
2. **interaction-quality** — 8대 컴포넌트 상태, focus, loading, error
3. **design-system-consistency** — 토큰 일관성, 컴포넌트 재사용률
4. **responsive-accessibility** — WCAG AA, 4pt 간격, 모바일 우선
5. **anti-pattern-detector** — 24개 AI slop 지표 탐지

## 실행

`skills/cs-design/SKILL.md` 프로토콜을 따라 design-lead 에이전트를 스폰합니다.
