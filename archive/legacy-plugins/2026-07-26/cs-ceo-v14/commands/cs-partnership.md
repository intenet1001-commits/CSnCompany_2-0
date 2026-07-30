---
description: "다른 스킬/에이전트와 협업해서 목표 달성 — /cs-partnership with [파트너들] [목표]. cs-ceo P-모드의 명시적 진입점. Goal Gate + Dynamic Resolve v2 내장. v5.5: AGENT/SKILL/PROTOCOL 타입 자동 감지."
allowed-tools: Bash, Read, Write, Edit, Glob, Grep, Agent, AskUserQuestion, Task, ToolSearch
---

# /cs-partnership with [파트너들] [목표]

협업할 스킬이나 에이전트를 명시하면 CEO가 타입을 자동 감지해 최적 방법으로 협업합니다.
`/cs-ceo with [partner]: [목표]`의 전용 진입점입니다. Goal Gate + Dynamic Resolve v2가 내장되어 있습니다.

## 사용법

```
# 스킬 파트너
/cs-partnership with gstack 분석 결과를 구글 시트에 정리해줘
/cs-partnership with superpowers 이 기능 어떻게 접근할지 막막해
/cs-partnership with brainstorming 새 기능 아이디어 탐색해줘

# 에이전트 파트너 (oh-my-claudecode 등 외부 플러그인 에이전트)
/cs-partnership with executor 이 기능 구현 위임해줘
/cs-partnership with debugger 이 버그 심층 분석해줘
/cs-partnership with architect 아키텍처 설계 맡겨줘

# 멀티 파트너 (쉼표 구분)
/cs-partnership with deep-dive,gstack 버그 분석 후 결과를 시트에 정리
/cs-partnership with cs-clarify,executor 요구사항 정리 후 구현 위임
/cs-partnership with architect,executor 설계 후 바로 구현까지
```

## 파트너 타입 (v5.5 자동 감지)

| 파트너 | 타입 | 실행 방법 | CEO P-모드 |
|--------|------|---------|----------|
| `superpowers` (brainstorming 등) | SKILL | `Skill(skill="superpowers:brainstorming")` | P-Pre |
| `executor`, `debugger`, `architect` | AGENT | `Task(subagent_type="oh-my-claudecode:executor")` | P-In/Pre |
| `deep-dive`, `autoresearch` | AGENT | `Task(subagent_type="oh-my-claudecode:debugger")` | P-Pre |
| `gstack` | PROTOCOL | SKILL.md 직접 실행 | P-Post |
| `bkit` | PROTOCOL | SKILL.md 직접 실행 | P-Wraps |
| `cs-clarify` | AGENT | `Task(subagent_type="cs-clarify:clarify-lead")` | P-Pre |
| *(미등록)* | 자동 탐색 | Dynamic Resolve v2 → 타입 자동 판정 | 자동 결정 |

## 실행 방식

### Step 1: 최신 CEO 경로 확인

```bash
BASE="$HOME/.claude/plugins/marketplaces/CSnCompany_2-0/plugins"
LATEST_CEO=$(ls -d "$BASE/cs-ceo-v"* 2>/dev/null | sort -V | tail -1)
```

### Step 2: 입력 파싱

유저 입력에서 파트너 목록과 태스크를 추출한다:

- 입력 예: `with executor,gstack 이 기능 구현 후 시트에 정리`
- 파싱 결과: `partners="executor,gstack"`, `task="이 기능 구현 후 시트에 정리"`
- CEO 전달 포맷: `with executor,gstack: 이 기능 구현 후 시트에 정리`

파싱 실패(with 키워드 없음, 목표 없음) → AskUserQuestion으로 재확인:
```
"파트너와 목표를 확인해 주세요.\n예시: with executor 이 기능 구현 위임해줘\n      with debugger,gstack 버그 분석 후 시트 정리"
```

### Step 3: CEO 에이전트 스폰

Task() 도구로 CEO 에이전트를 스폰한다:
- `description`: "CS-CEO Partnership Mode"
- `subagent_type`: `"cs-ceo:ceo"`
- `prompt`: 유저 요청을 `with [파트너]: [태스크]` 형태로 그대로 전달

```
# 예시 prompt
with executor,gstack: 이 기능 구현 후 결과를 구글 시트에 정리해줘
```

CEO가 내부적으로:
1. **Goal Gate** → 목표 확정
2. **Phase -2 Dynamic Resolve v2** → 각 파트너 타입(AGENT/SKILL/PROTOCOL) 자동 감지
3. **P-모드 결정** → Pre/In/Post/Wraps 타이밍 자동 추론
4. **타입별 실행** → AGENT: `Task(subagent_type=...)` / SKILL: `Skill(skill=...)` / PROTOCOL: Read+직접실행
5. **멀티 파트너 체이닝** → Pre결과 → CEO실행 → Post파트너 순서 자동 관리

### Step 4: 결과 출력

CEO 에이전트가 반환한 종합 리포트를 그대로 출력한다.
