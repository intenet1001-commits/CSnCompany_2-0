## Skill routing

When the user's request matches an available skill, prefer invoking it via the Skill
tool over answering ad-hoc — skills have specialized workflows that produce better results.
Route directly when confidence is high; when the match is ambiguous, confirm with ONE
short question before routing instead of guessing.

Key routing rules:
- Web testing, playwright, site QA, find bugs on a URL → invoke CS-test
- TDD plan, clean architecture plan, coding plan for a feature → invoke CS-plan
- Codebase review, architecture review, code quality check → invoke CS-codebase-review
- Design review, UI audit, UX analysis, 디자인 리뷰, anti-pattern detection → invoke cs-design
- Sync plugins, push to GitHub, update marketplace → invoke cs-sync
- Complex multi-step task, plan then execute in parallel → invoke smart-run
- English conversation, convert session to dialog → invoke convo-maker
- Product ideas, "is this worth building", brainstorming → invoke office-hours
- Bugs, errors, "why is this broken" → invoke investigate
- Ship, deploy, push, create PR → invoke ship
- Code review, check my diff → invoke review
- Architecture review, plan review → invoke plan-eng-review
- Save progress, checkpoint, resume → invoke checkpoint
- "목표", complex multi-step task, unsure which domain, /goal → invoke cs-ceo
- Complex task routing, effort estimation, domain dispatch → invoke cs-ceo
- Error capture, error note, 에러노트, 에러 기록, 오류 정리 → invoke cs-error-notes

## Loop Engineering (공통 프로토콜)

- 모든 CS 리드(lead) 에이전트는 plugins/shared/LOOP-PROTOCOL.md를 따른다
  (EVIDENCE / SUCCESS CRITERIA FIRST / BOUNDED LOOP / COVERAGE HONESTY / REPORT FULL, FILTER DOWNSTREAM / OUTPUT PROPORTIONALITY).
  verdict 산출 플러그인(cs-ship, CS-test, CS-codebase-review)은 plugins/shared/GATE-LOOP.md를 추가로 따른다.
- 학습 반영 규칙: 교훈이 프로토콜 변경을 지시하면 같은 커밋에서 해당 SKILL/agents/*.md에
  반영하고 ✅ 반영됨 표시한다. 미반영 교훈은 실행되지 않는다.
- 통합 제거 규칙: 외부 시스템 통합·의존성을 제거하는 변경은 같은 커밋에서 커플링된
  반대편(READ↔WRITE, 타 플러그인 포함)까지 수정한다. ✅ 반영됨의 목표:
  활성 플러그인 범위(.claude-plugin/marketplace.json plugins 배열이 가리키는 디렉토리
  + plugins/shared/ + plugins/CLAUDE.md)에서 해당 외부 시스템에 대한 실행성 참조
  (읽기/쓰기 경로, 호출 단계, 조건 분기) 0건 — 결정 기록·교훈 같은 문서적 언급은 제외.
  이 목표를 검색 명령+출력 인용을 증거로 입증한 뒤에만 표시한다. 탐지 방법은 자유.
  원칙이 기록됐다는 것은 실행됐다는 보증이 아니다.
- 에러 회상: 새로운 에러(stack trace, 실패 명령, 반복 실패)를 디버깅하기 전에
  ~/.claude/error-notes/INDEX.md를 해당 에러의 핵심 키워드로 grep하여
  (즉 /cs-error-notes recall) 매칭되는 resolved 노트를 먼저 surface한 뒤 수정에 착수한다.

## 플러그인 인벤토리 (자동 생성)

<!-- AUTO-PLUGIN-INVENTORY:BEGIN (routing_sync.py write 로 재생성 — 직접 편집 금지) -->

| 플러그인 | 디렉토리 | 설명 |
|---|---|---|
| cs-end | `./plugins/cs-end-v3` | 🏁 Session Closer |
| cs-error-notes | `./plugins/cs-error-notes-v1` | 📝 Error Note Manager |
| cs-ceo | `./plugins/cs-ceo-v15` | 🧭 CEO |
| goal | `./plugins/cs-ceo-v15` | 🎯 Goal |
| cs-partnership | `./plugins/cs-ceo-v15` | 🤝 Partnership |
| cs-clarify | `./plugins/cs-clarify-v1` | 💬 PM |
| CS-plan | `./plugins/CS-plan-v21` | 🏗️ Architect |
| cs-design | `./plugins/cs-design-v20` | 🎨 Designer |
| cs-design-sample1 | `./plugins/cs-design-sample1` | 🎨 Design Reference |
| CS-test | `./plugins/CS-test-v26` | 🧪 QA Engineer |
| CS-codebase-review | `./plugins/CS-codebase-review-v29` | 🔍 Code Reviewer |
| cs-ship | `./plugins/cs-ship-v1` | 🚢 DevOps |
| cs-smart-run | `./plugins/cs-smart-run` | ⚡ Team Lead |
| cs-experiencing | `./plugins/cs-experiencing-v8` | 📚 Knowledge Keeper |
| convo-maker | `./plugins/convo-maker` | 🗣️ Language Coach |

<!-- AUTO-PLUGIN-INVENTORY:END -->
