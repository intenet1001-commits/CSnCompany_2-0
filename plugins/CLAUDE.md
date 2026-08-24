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
- Complex multi-step task, plan then execute in parallel, 플랜 실행, execute a CS-plan PLAN.md → invoke smart-run (registered PLAN.md auto-detected — Phase 0.7 PLAN INTAKE)
- English conversation, convert session to dialog → invoke convo-maker
- Product ideas, "is this worth building", brainstorming → invoke office-hours
- Bugs, errors, "why is this broken" → invoke investigate
- Ship, deploy, push, create PR → invoke ship
- Code review, check my diff → invoke review
- Architecture review, plan review → invoke plan-eng-review
- Save progress, checkpoint, resume → invoke checkpoint
- "목표", complex multi-step task, unsure which domain, /goal → invoke cs-ceo
- Complex task routing, effort estimation, domain dispatch → invoke cs-ceo
- 한 문장으로 전체 개발, one-sentence to shipped, full SDLC pipeline (요구사항→배포 준비) → invoke cs-company
- Error capture, error note, 에러노트, 에러 기록, 오류 정리 → invoke cs-error-notes
- 프로젝트 장기기억 학습, 장기기억 학습 → invoke learn
- 장기기억 기반 에이전트 개선, 에이전트 업그레이드 → invoke upgrade
- 장기기억 상태, 학습 상태 → invoke status
- Create hook, block behavior, prevent pattern, 훅 생성, 동작 차단, 이 패턴 막아줘 → invoke hookify
- Code navigation, find symbol, go to definition, 코드 탐색, 심볼 검색, 정의 찾기, 참조 분석 → use serena (mcp__serena__* tools or /serena skill)

## Python 실행 규칙

- `shared/scripts/*.py` 는 항상 `uv run --quiet --no-project <script>` 로 실행한다 (직접 `python3` 호출 금지).
  설치: `brew install uv` 또는 `curl -LsSf https://astral.sh/uv/install.sh | sh`
- 진입점: `bash plugins/shared/run_prepass.sh <subcommand>` — python3 → uv run → uv install 순 자동 처리.

## Loop Engineering (공통 프로토콜)

- 모든 CS 리드(lead) 에이전트는 plugins/shared/LOOP-PROTOCOL.md를 따른다
  (EVIDENCE / SUCCESS CRITERIA FIRST / BOUNDED LOOP / COVERAGE HONESTY / REPORT FULL, FILTER DOWNSTREAM / OUTPUT PROPORTIONALITY).
  verdict 산출 플러그인(cs-ship, CS-test, CS-codebase-review)은 plugins/shared/GATE-LOOP.md를 추가로 따른다.
- 오케스트레이션 확장: 다중 도메인이 순서·조건·재작업 루프로 얽히면 plugins/shared/ORCHESTRATION-PATTERNS.md
  (P1 speaker selection / P2 termination conditions / P3 declarative chain manifest / P4 instructor-assistant 역할극 /
  P5 persona+output 계약 — CrewAI/AutoGen/ChatDev 벤치마크 이식)를 LOOP-PROTOCOL 위에 얹는다.
  선언적 파이프라인은 plugins/shared/chains/, 페르소나 계약은 plugins/shared/agents/AGENT-PERSONA-CONTRACT.md.
  정적 fan-out으로 충분하면 켜지 않는다 (Simplicity First).
  파이프라인 아티팩트(CLARIFY/PLAN/IMPLEMENT-REPORT/REVIEW/TEST-REPORT/SHIP-REPORT)를 생산/소비하는
  리드는 plugins/shared/ARTIFACT-CONTRACTS.md를 추가로 따른다 (frontmatter + register/find-meta 계약).
- 장기기억 회상: 모든 리드는 fan-out 전 plugins/shared/MEMORY-PROTOCOL.md의 Phase R을 1회 수행하고
  `recall: E<n>/C<n>/N<n>` 헤더를 출력한다. **AgentsToZ가 `<PROJECT_ROOT>/.agent-memory/`에 적재(write)하고
  CS 플러그인이 소비(read)하는 구조**이며, 전략 계층([R-c])의 단일 진입점은
  `plugins/shared/scripts/recall_project_memory.py`다 (읽기 전용, 항상 exit 0, 미연동 프로젝트에서는 무출력).
  리드가 `.agent-memory/`에 쓰거나 폐기된 `~/.claude/core-memory`로 폴백하는 것은 금지된다.
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
| cs-company | `./plugins/cs-ceo-v15` | 🏢 Company Pipeline |
| cs-clarify | `./plugins/cs-clarify-v1` | 💬 PM |
| CS-plan | `./plugins/CS-plan-v21` | 🏗️ Architect |
| cs-design | `./plugins/cs-design-v20` | 🎨 Designer |
| cs-design-sample1 | `./plugins/cs-design-sample1` | 🎨 Design Reference |
| cs-design-sample2 | `./plugins/cs-design-sample2` | 🎨 Design Reference |
| CS-test | `./plugins/CS-test-v26` | 🧪 QA Engineer |
| CS-codebase-review | `./plugins/CS-codebase-review-v29` | 🔍 Code Reviewer |
| cs-ship | `./plugins/cs-ship-v1` | 🚢 DevOps |
| cs-smart-run | `./plugins/cs-smart-run` | ⚡ Team Lead |
| cs-experiencing | `./plugins/cs-experiencing-v9` | 📚 Knowledge Backend |
| convo-maker | `./plugins/convo-maker` | 🗣️ Language Coach |
| cs-memory | `./plugins/cs-core-memory-v1` | 🧠 Memory Learner |
| csn-sync | `./plugins/csn-sync` | 🔄 Marketplace Sync |

<!-- AUTO-PLUGIN-INVENTORY:END -->
