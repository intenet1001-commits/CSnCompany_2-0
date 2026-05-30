---
description: "CS 시리즈 CEO — 자연어 요청을 받아 공수 추정 후 최적 도메인 자율 배분. v5: 파트너십 프로토콜 추가 (/cs-ceo [요청] 또는 /cs-ceo with [partner]: [요청])"
allowed-tools: Bash, Read, Write, Edit, Glob, Grep, Agent, AskUserQuestion, Task, ToolSearch
---

# /cs-ceo [요청]

CS 시리즈 총괄 CEO. 자연어로 요청하면 CEO가 공수를 추정하고 최적 실행 모드를 스스로 판단합니다.
**v5.1**: Universal Partnership Protocol — 설치된 **어떤 스킬이든** `with [스킬명]:` 으로 협업 가능.

## 기본 사용법

```
/cs-ceo 이 URL을 테스트해줘
/cs-ceo 새 결제 기능 설계해줘
/cs-ceo 전체 코드베이스 분석해줘
/cs-ceo 뭔가 이상한 것 같아 찾아봐줘
```

## 파트너십 사용법 — 어떤 스킬이든 가능

```
# 잘 알려진 파트너
/cs-ceo with superpowers: 이 기능 어떻게 접근할지 잘 모르겠어
/cs-ceo with bkit: 전체 PDCA 사이클로 개발해줘
/cs-ceo with omc: 이 버그 근본 원인 깊이 파봐줘
/cs-ceo with gstack: 분석 결과를 구글 시트에 정리해줘

# 설치된 어떤 스킬이든
/cs-ceo with tdd-workflow: 새 기능 TDD로 개발해줘
/cs-ceo with deep-research: 이 기술 스택 대안 조사해줘
/cs-ceo with stripe-integration: 결제 구현하면서 코드 리뷰

# 멀티 파트너 (2개 이상)
/cs-ceo with superpowers,gstack: 기능 설계 후 드라이브에 저장
/cs-ceo with cs-clarify,tdd-workflow: 요구사항 정리 후 TDD로 개발
/cs-ceo with deep-research,stripe-integration,gstack: 조사→구현→정리
```

## CEO 자동 파트너 감지

파트너 명시 없이도 맥락에서 자동 감지:
- "잘 모르겠어" / "막막해" → superpowers:brainstorming
- "구글 시트" / "드라이브" / "Gmail" → gstack
- "버그" + 복잡한 증상 → omc:deep-dive
- "PDCA로" / "전체 사이클" → bkit:pdca

## 파트너 탐색 방식

명시된 스킬이 알려진 파트너가 아니면 자동으로 탐색:
`CS-plugins → 마켓플레이스 → 플러그인 캐시 → 유저 스킬` 순으로 검색 후 타이밍 자동 추론

## 실행 방식

```bash
BASE="$HOME/.claude/plugins/marketplaces/CSnCompany_2-0/plugins"
LATEST_CEO=$(ls -d "$BASE/cs-ceo-v"* 2>/dev/null | sort -V | tail -1)
```

CEO 에이전트 파일: `$LATEST_CEO/agents/ceo.md`
CEO 스킬 파일: `$LATEST_CEO/skills/cs-ceo/SKILL.md`

SKILL.md 프로토콜에 따라 CEO 에이전트를 Task()로 스폰합니다.
