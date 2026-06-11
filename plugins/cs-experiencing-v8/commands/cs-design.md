---
description: "5-agent parallel design review - visual hierarchy, interaction quality, design system consistency, responsive/accessibility, anti-pattern detection"
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

## 실행

이 커맨드는 최신 `cs-design-v*` 도메인의 SKILL.md 프로토콜을 실행합니다.
(도메인은 cs-experiencing-v*과 같은 레벨의 plugins/ 디렉토리에 위치 — 버전은 디렉토리명이 단일 진실, `ls -d ... | sort -V`로 항상 최신을 해석)

```bash
BASE="$HOME/.claude/plugins/marketplaces/CSnCompany_2-0/plugins"
LATEST_DESIGN=$(ls -d "$BASE/cs-design-v"* 2>/dev/null | sort -V | tail -1)
```

1. `$LATEST_DESIGN/VERSION` 읽기 → 현재 버전 확인
2. `$LATEST_DESIGN/skills/cs-design/SKILL.md` 프로토콜 실행
3. design-lead 에이전트를 스폰하여 5-agent 병렬 리뷰 실행
