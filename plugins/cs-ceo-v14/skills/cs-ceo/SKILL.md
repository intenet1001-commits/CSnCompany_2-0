---
name: cs-ceo
user-invocable: true
description: |
  CS 시리즈 CEO 오케스트레이터. 자연어 요청을 받아 공수 추정 후 CS-test/CS-plan/CS-codebase-review/cs-design/cs-smart-run 중 최적 조합을 자율 선택·배분한다.
  v5.1: Universal Partnership Protocol — "with [어떤스킬이든]:" 구문으로 시스템에 설치된 모든 스킬과 협업 가능.
  v5.2: External Knowledge Gate — 외부 지식이 필요하다고 판단되면 지체 없이 context7-auto-research를 자동 호출하여 학습 후 진행.
  v5.3: Goal Gate — 모든 요청 진입 직전 목표(WHAT)를 추출·확정. 불명확 시 1회 질문.
  v5.4: Personal Knowledge Gate (Phase -3.5) — context7 호출 전 CS_V7 개인 위키를 우선 조회.
  v5.5: Dynamic Resolve v2 — 파트너 타입(AGENT/SKILL/PROTOCOL) 자동 감지. AGENT 타입은 Task(subagent_type)로 직접 호출. 외부 플러그인 에이전트(oh-my-claudecode:executor 등) 지원.
  설치된 스킬/에이전트를 자동 탐색하고, 타이밍(Pre/In/Post/Wraps)을 description 기반으로 자동 추론한다.
  Use when user types "/cs-ceo", "cs-ceo", "/goal", or "/cs-partnership".
version: 1.4.0
allowed-tools:
  - Task
  - Agent
  - Read
  - Write
  - Edit
  - Bash
  - Glob
  - Grep
  - AskUserQuestion
  - ToolSearch
---

# CS-CEO — CS 시리즈 총괄 오케스트레이터 (v5 + Partnership Protocol)

## 개요

유저가 `/cs-ceo [자연어 요청]`을 입력하면:
1. **(v5.3 신규) Goal Gate**: CEO가 요청에서 목표(WHAT)를 추출. 불명확하면 사용자에게 1회 질문하여 목표 확정 (Phase G)
2. **(v5.2 신규) 외부 지식 게이트**: CEO가 라이브러리/프레임워크/최신 동향 등 외부 도움이 필요할 것 같으면 즉시 `/context7-auto-research`를 호출해 공부 후 진행 (Phase -3)
3. CEO가 외부 파트너 스킬 필요 여부 판단 (Phase -2)
3. CEO 에이전트(opus)가 공수를 추정하고
4. 어떤 CS 도메인을 어떤 순서로 실행할지 스스로 결정하고
5. 필요 시 cs-smart-run(Opus 플랜→Sonnet 실행)을 자율 선택한다

유저는 도메인이나 파트너를 지정할 필요 없다. 원하는 것을 말하면 CEO가 판단한다.

### v5.2 External Knowledge Gate — 자동 학습 루프

```
요청 진입
  ↓
[Phase G]  목표 명확?  ← WHAT(달성 목표) 추출
  │ 명확  → GOAL_STATEMENT 확정 → 다음 Phase
  │ 불명확 → AskUserQuestion: "어떤 목표를 달성하고 싶으신가요?"
  │          └─ 답변 → GOAL_STATEMENT 확정 → 다음 Phase
  │          └─ 취소 → 종료
  ↓
[Phase -3] 외부 지식 필요?  ← 라이브러리/최신 변경/모르는 용어/대안 비교/외부 stack trace
  │ Yes → context7-auto-research 설치됨?
  │        ├─ 설치됨    → Skill(context7-auto-research) → 학습 결과를 INPUT으로 보관
  │        └─ 미설치    → AskUserQuestion: [Install / Skip once / Abort]
  │                       └─ Install 선택 시 `npx skills add -g BenedictKing/context7-auto-research` 자동 실행 후 진행
  │ No  → 그대로 진행
  ↓
[Phase -2] 파트너십 탐지 → ... → [Phase 4] 종합 리포트 → [Phase 5-B] 버전업 결정
                                                              │
                                                              └→ 외부 학습이 판단을 바꿨다면 노하우 후보로 적재 → 다음 version-up에서 영속화
```

- 발동 시 알림: `📚 외부 지식 필요 감지: [주제] — context7-auto-research로 학습 후 진행합니다.`
- 미설치 시: 설치 명령(`npx skills add -g BenedictKing/context7-auto-research`)과 함께 Install/Skip/Abort 3지선다 제시 — 사용자가 명시적으로 Skip하지 않는 한 무단으로 외부 학습을 건너뛰지 않는다.

---

## 사용법

### 기본 (기존과 동일)

```
/cs-ceo 이 URL을 테스트해줘
/cs-ceo 새 결제 기능 플랜 짜줘
/cs-ceo 전체 코드베이스 분석해줘
/cs-ceo 이 서비스 뭔가 이상한 것 같아
/cs-ceo 대규모 아키텍처 개편 어떻게 할지 알려줘
```

### 파트너십 명시 (v5 — 어떤 스킬이든 가능)

```
# 잘 알려진 파트너 (Fast-Path)
/cs-ceo with superpowers: 이 기능 어떻게 접근할지 잘 모르겠어
/cs-ceo with bkit: 전체 PDCA 사이클로 개발해줘
/cs-ceo with omc: 이 버그 깊이 파봐줘
/cs-ceo with gstack: 분석 결과를 구글 시트에 저장해줘
/cs-ceo with cs-clarify: 요구사항이 불명확해, 먼저 정리해줘

# 설치된 어떤 스킬이든 (Dynamic Resolve)
/cs-ceo with tdd-workflow: 새 결제 기능 TDD로 개발해줘
/cs-ceo with deep-research: 이 라이브러리 대안 조사해줘
/cs-ceo with stripe-integration: 결제 붙이면서 코드베이스 리뷰해줘
/cs-ceo with systematic-debugging: 이 에러 근본 원인 찾아줘
```

### 멀티 파트너

```
/cs-ceo with superpowers,gstack: 기능 설계 후 결과를 드라이브에 저장해줘
/cs-ceo with omc,bkit: 버그 근본 원인 파악 후 PDCA로 수정해줘
/cs-ceo with cs-clarify,tdd-workflow: 요구사항 정리 후 TDD로 개발해줘
/cs-ceo with deep-research,stripe-integration,gstack: 결제 옵션 조사 → 구현 → 시트 정리
```

---

## 파트너 스킬 가이드

### Fast-Path 파트너 (자동 감지 포함)

| 파트너 키 | 핵심 스킬 | 언제 쓰나 | 자동 감지 트리거 |
|----------|----------|----------|----------------|
| `superpowers` | brainstorming, writing-plans, executing-plans, systematic-debugging | 설계 불명확, 체계적 플랜, 병렬 작업, 디버깅 방법론 | "잘 모르겠어" / "어떻게 접근" / "막막해" |
| `bkit` | pdca, qa-phase | PDCA 전체 사이클, 품질 게이트, 장기 피처 개발 | "PDCA로" / "전체 사이클" / "품질 게이트" |
| `omc` | deep-dive, autoresearch, autopilot | 심층 버그 조사, 리서치, 집중 실행 모드 | "깊이 파봐" / "근본 원인" + 복잡한 증상 |
| `gstack` | gstack | Google Drive/Sheets/Docs/Gmail/Calendar 연동 | "구글 시트" / "드라이브에" / "Gmail" / "캘린더" |
| `cs-clarify` | cs-clarify | 요구사항 모호, scope 정의 필요 | "뭘 만들어야" / "요구사항 불명확" |

### Dynamic Resolve 파트너 (설치된 모든 스킬)

`with [스킬이름]:` 에 **어떤 스킬 이름이든** 넣으면 CEO가 자동으로:
1. 시스템 전체(마켓플레이스 → 캐시 → 유저스킬)에서 해당 SKILL.md 탐색
2. SKILL.md `description`을 읽어 타이밍(Pre/In/Post/Wraps) 자동 추론
3. 적절한 실행 모드로 협업 진행

탐색 순서: CS-plugins 내부 → `~/.claude/plugins/marketplaces` → `~/.claude/plugins/cache` → `~/.claude/skills`

파트너를 명시하지 않아도 CEO가 알려진 패턴은 자동으로 감지해 알린 후 진행한다.

---

## 실행 프로토콜

### Step 1: 최신 CEO 경로 확인

```bash
BASE="$HOME/.claude/plugins/marketplaces/CSnCompany_2-0/plugins"
LATEST_CEO=$(ls -d "$BASE/cs-ceo-v"* 2>/dev/null | sort -V | tail -1)
echo "CEO 경로: $LATEST_CEO"
echo "CEO 버전: $(cat $LATEST_CEO/VERSION)"
```

### Step 2: CEO 에이전트 스폰

```
에이전트 파일: $LATEST_CEO/agents/ceo.md
```

Task() 스폰 시 유저 요청을 원문 그대로 전달 (`with [partner]:` 구문 포함):
```
유저 요청: [원문 그대로]
```

CEO 에이전트 내부 처리:
- Phase -2: 파트너십 탐지 (명시/자동)
- Partnership Registry: 파트너 경로 확보
- Phase -1~0: 컨텍스트 점검 + 도메인/파트너 경로 확인
- Phase 1~5: 공수 추정 → 모드 결정 → 실행 → 리포트

### Step 3: 결과 출력

CEO 에이전트가 반환한 종합 리포트를 그대로 출력한다.

---

## CEO 판단 모드 요약

| 모드 | 조건 | 실행 |
|------|------|------|
| **A** (직접 단독) | 도메인 1개, 명확 | 해당 도메인 직접 실행 |
| **B** (CEO 오케스트레이션) | 도메인 2~3개 | CEO가 순차/병렬 조합 |
| **C** (smart-run 위임) | 복잡/대규모/불확실 | Opus 플랜→Sonnet 실행 |
| **P-Pre** (파트너 선행) | 파트너 결과가 플랜 INPUT | 파트너 → A/B/C |
| **P-In** (파트너 병렬) | 파트너와 독립 병렬 가능 | 파트너 ‖ CS 도메인 동시 |
| **P-Post** (파트너 후처리) | 파트너가 CEO 결과 처리 | A/B/C → 파트너 |
| **P-Wraps** (파트너 감싸기) | bkit:pdca 전체 사이클 | pdca 방법론 안에서 A/B/C |

모드 선택은 CEO가 자율 결정. 유저가 지정하지 않아도 된다.

---

## CEO 노하우

*(버전업마다 이 섹션에 판단 패턴이 축적됩니다)*

### 1. 인프라 진단 태스크는 도메인 에이전트 없이 직접 Bash 실행이 효율적 (2026-04-24)
- **상황**: localhost:9000 점검 + GitHub sync + 폴더 선택 기능 에러 개선 확인 요청
- **판단**: 도메인 에이전트 스폰 없이 직접 Bash 명령으로 진단
- **결과**: 즉시 근본 원인 진단. 효율적이었음.
- **교훈**: 인프라 진단은 CEO 직접 Bash. 도메인 에이전트는 심층 분석에만.

### 2. 코드 변경 검증 요청은 Mode A + 직접 분석 (2026-04-24)
- **상황**: 워크트리 UX 개선 코드 변경 후 6개 항목 검증 요청
- **판단**: Mode A — Bash+Read로 직접 코드 분석
- **결과**: 6개 항목 모두 빠르게 검증 완료.
- **교훈**: "implemented code verify" = 항상 Mode A. Bash grep + Read로 충분.

### 3. 외부 지식 게이트 — context7-auto-research 자동 호출 (2026-04-25)
- **상황**: CEO 내부 노하우만으로는 라이브러리/프레임워크 최신 동향, 새 API, 마이너 변경점을 정확히 답할 수 없음.
- **판단**: Phase -3 신설 — 모든 요청 진입 직전에 "외부 지식 필요 여부" 평가. 트리거 신호 1개라도 감지되면 즉시 context7-auto-research 호출.
- **결과**: 도메인 에이전트에게 정확한 최신 문서 INPUT 전달 → 잘못된 가정 기반 실행 감소.
- **교훈**: 의심되면 호출이 기본값. 동일 세션 내 재호출 금지. 미설치 시 AskUserQuestion으로 Install/Skip/Abort 3지선다 제시.

### 12. HTTP-first 자동화 아키텍처: 서버리스 호환 fetch → Playwright 폴백 → AI 진단 게이트 (2026-04-26)

- **상황**: Playwright 전용 파킹 자동화 앱을 Vercel 배포에서도 동작하도록 전환 요청
- **판단**: Playwright는 서버리스 환경에서 Chromium 바이너리 실행 불가 → plain fetch로 HTTP 세션 자동화 먼저 시도. 실패 시 UI에 "Claude Code에 전달" 버튼으로 진단 프롬프트를 클립보드에 복사하는 UX 패턴 설계.
- **결과**: fetch 구현은 AJPark 로그인 인코딩(Base64 ID) 문제로 추가 디버깅 필요했으나 아키텍처 방향은 유효. 진단 버튼 패턴은 비기술 사용자가 오류를 개발자(Claude Code)에게 전달하는 효과적인 채널이 됨.
- **교훈**: Playwright 필수처럼 보이는 작업도 HTTP-first로 먼저 시도. 실패 경로에 "AI 진단 게이트(클립보드 복사 프롬프트)" 설계 → 사용자가 직접 Claude Code에 붙여넣으면 자동 디버깅 루프 완성.


### 13. Electron auto-paste 디버깅 — 3-레이어 격리 전략 (2026-04-27)

- **상황**: Electron 앱에서 단축키 → 클립보드 → 붙여넣기 파이프라인이 동작하지 않아 root cause 특정이 어려움.
- **판단**: 3-레이어 격리 방식 적용: ① pbpaste로 클립보드 직접 확인(Electron clipboard.writeText 정상 여부) ② osascript 단독 실행(AppleScript 문법 + 권한 여부) ③ Electron exec() 통합 테스트(자식 프로세스 sandbox 이슈 여부). Layer 2 성공 + Layer 3 실패 → Electron 자식 프로세스 권한 문제로 즉시 특정.
- **결과**: keystroke "v" using command down은 Layer 2에서는 동작하지만 Layer 3(Electron exec)에서 silent fail → click menu item "Paste"로 교체 후 해결.
- **교훈**: Electron 앱에서 osascript 오작동 시 반드시 3-레이어 격리부터. 특히 exit 0이지만 효과 없는 경우 sandbox/권한 문제 → AppleScript 메뉴 클릭 방식으로 우회.

### 14. 야간 위임 — 사용자 sleep 중 Phase별 자율 진행 + 아침 보고서 (2026-04-28)

- **상황**: 사용자가 "난 자야하니까 잘 처리해 아침에 보자"로 위임. 5-phase 작업(handoff UX + Windows tmux fallback + wizard 개선 + Windows 빌드 + 설치)을 사용자 컨펌 없이 자율 진행해야 함.
- **판단**: 안전한 작업(코드 변경, 빌드, git push)은 자율 진행, **destructive/installing 동작**(NSIS 인스톨러 실행)은 silent flag(`/S`)로 사용자 확인 없이 가능하지만 **결과 검증 필수**(설치 경로 ls, 프로세스 살아있는지 tasklist). Phase 단위로 commit/push 분리 → 아침에 사용자가 git log로 진행 트레이스 가능.
- **결과**: 5-phase 모두 완료, 6커밋 푸시, 앱 설치 + 실행 검증, 아침 보고서에 시나리오별 검증 절차 명시(핸드오프, cmux 폴백, 기기명 변경, 자동 실행). 사용자가 깨어나면 30초 내에 상태 파악 가능.
- **교훈**: 야간 위임 받을 때 (1) Phase별 commit으로 트레이스 보장 (2) destructive는 검증까지 묶음 (3) 마지막 메시지에 **시나리오 체크리스트** 포함 — "Step N: 이걸 클릭하면 X가 보여야 함" 식. ScheduleWakeup 으로 장시간 빌드 polling 가능 (270초 간격이 cache TTL 적정).

### 15. 빌드 시스템 크로스 디바이스 버그 — Mode B 인라인 분석으로 절대경로 즉시 진단 (2026-05-01)

- **상황**: Tauri 앱 DMG 빌드가 iCloud ETIMEDOUT + E0601(main 미발견)로 반복 실패. 다른 Mac에서도 빌드 오류 보고됨.
- **판단**: Mode B — CS-codebase-review 인라인 분석. `.cargo/config.toml`의 하드코딩 절대경로(`/Users/gwanli/cargo-targets/portmanager`)가 크로스 디바이스 실패의 근본 원인으로 즉시 특정. `build-macos.ts` 래퍼 생성으로 `CARGO_TARGET_DIR=$HOME/...` 동적 설정 제안.
- **결과**: 크로스 디바이스 문제 해결. 추가로 fix-dmg stale 파일 버그 + 로그 offset UTF-8 버그 동시 발견 및 수정. 8파일 커밋 + 푸시.
- **교훈**: 빌드 실패 디버깅에서 "다른 기기에서도 재현"은 **환경 고유값 하드코딩**(절대경로, username, 홈 디렉토리)을 1순위 의심. 코드 리뷰 시 `.cargo/config.toml`, `CMakeLists.txt`, Makefile의 절대경로 항목을 체크리스트 필수 항목으로 추가.

### 16. Tauri 앱 필드 사라짐 버그 — TypeScript ↔ Rust struct 필드 불일치 1순위 확인 (2026-05-01)

- **상황**: 즐겨찾기(favorite) 추가 후 앱 재시작 또는 창 전환 시 사라지는 버그. Pull 직후에는 나타나지만 바로 소실됨.
- **판단**: Mode A 직접 분석. CEO 직접 Bash+Read로 3단계 원인 추적.
- **결과**: 3중 원인 발견: ① App.tsx 자동 Push rows에 `favorite` 누락 ② Supabase `ports` 테이블에 `favorite` 컬럼 없음 ③ **핵심 근본 원인** — Rust `PortInfo` 구조체에 `favorite` 필드 없어서 `save_ports` 호출 시 JSON 역직렬화 과정에서 필드 드롭. `ports.json`에 저장될 때마다 `favorite`가 사라짐.
- **교훈**: Tauri 앱에서 특정 필드가 저장 안 될 때 → **1순위: `src-tauri/src/lib.rs`의 `struct PortInfo` 필드 목록과 TS `interface PortInfo` 비교**. Rust 구조체 누락 필드는 serde 역직렬화 시 silently drop됨. 이후 Supabase 컬럼/Push 로직은 2·3차 확인 순서.

### 17. GUI 앱 PATH Desert — Tauri invoke()는 zsh -l -c로 실행해야 사용자 PATH 확보 (2026-05-14)
- **상황**: Tauri 앱에서 `claude --bg`가 "claude not found in PATH" 오류. CLI/API 서버 경로에서는 정상 동작. Playwright 테스트도 통과했으나 앱에서만 계속 실패.
- **판단**: Mode A 직접 분석. isTauri() 분기 발견 → Tauri invoke() 경로(lib.rs)와 HTTP 경로(api-server.ts)가 완전히 독립적. PATH enhancedPath로 부족, `zsh -l -c` 필요.
- **결과**: `open_claude_bg()`를 `Command::new("/bin/zsh").args(["-l", "-c", &shell_cmd])`로 수정 → DMG v80 빌드 완료.
- **교훈**: Tauri(Finder 실행) = 최소 PATH(`/usr/bin:/bin`). **CLI에서 작동 + Playwright 통과 + 앱에서만 실패 → isTauri() 분기 확인 → Rust invoke() 경로는 `zsh -l -c` 필수**. Playwright는 HTTP 경로만 검증 — Rust invoke() 경로는 별도 테스트 필요.

### 18. CS_V7 지식 루프 — 개인 위키를 context7 폴백 체인 앞에 배치 (2026-05-15)
- **상황**: 사용자가 CS_V7(Graphify + LLM Wiki, 3-레이어) 개인 지식베이스와 CS 플러그인 SKILL.md 운영 지식의 구조적 병렬성을 발견. 두 시스템이 독립적으로 운영되며 지식이 교환되지 않음.
- **판단**: CS_V7의 `wiki query → raw 폴백 체인` 패턴을 cs-ceo에 적용. Phase -3.5 신설: GOAL 확정 직후, context7(외부 API) 호출 전에 CS_V7 개인 위키를 우선 조회. cs-end Phase 2.1로 principle-tier 학습을 CS_V7/raw/에 역류입.
- **결과**: 지식 루프 완성: `context7(외부) → 세션 → cs-end Phase 2.1 → CS_V7/raw/ → graphify → wiki → cs-ceo Phase -3.5 조회 → context7 SKIP`. cs-partnership 실행 코드 누락(Step 1~4)도 동시 수정.
- **교훈**: **두 개의 병렬 지식 시스템이 있을 때 → 빠른 것(개인 위키)을 느린 것(외부 API) 앞에 배치**. CS_V7 master-index.md가 관련 토픽 히트 여부를 O(1)로 판단하는 인덱스 역할. principle vs tactical tier 구분이 CS_V7 저장 여부를 결정하는 게이트 — 재사용성 2점 항목만 개인 위키로 역류입.
