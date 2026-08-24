# Changelog

## [fix] 2026-08-25 — AgentsToZ 회상 이음매 복구 (MEMORY-PROTOCOL [R-c])

### 문제
[R-c] STRATEGIC이 `~/.claude/core-memory/CORE.md`를 가리키고 있었다. 그 경로는 AgentsToZ 이관 때
폐기됐고(cs-ceo 15.2.0 "구형 전역 폴백 제거") 어떤 머신에도 존재하지 않는다. [R-c]는 "파일이 없으면
조용히 스킵"으로 설계돼 있어 **에러 없이 항상 스킵**됐고, 리드들은 전략 메모리를 한 번도 읽지 않은 채
`recall: C0`을 정상 출력했다 — AgentsToZ가 적재해도 CSnCompany가 소비하지 않는 상태였다.
repo 전체에서 이 죽은 경로를 가리키던 실행 참조는 `MEMORY-PROTOCOL.md:42` 단 1곳이었다.

### Added
- `plugins/shared/scripts/recall_project_memory.py` — AgentsToZ 전략 메모리 회상 단일 진입점.
  프로젝트 루트 탐색(상위 방향 `.agent-memory/config.json`), cs-memory 경로 해석(Claude 마켓플레이스 →
  Codex 캐시 → repo-local), 질의 240자 상한, `digest|json|header` 출력. **읽기 전용이며 항상 exit 0** —
  미연동 프로젝트에서는 무출력. cs-ceo Phase G.5가 이미 풀어 둔 로직을 한 곳으로 모은 것이다.
- `contested` 항목을 확정 사실과 분리해 "미해결 대립" 블록으로 출력하고, `knowledgeTimeHint`가 있으면
  `[기록 시점 YYYY-MM-DD — 현재 저장소 증거로 재확인 필요]`를 붙인다.
- `plugins/shared/tests/test_recall_project_memory.py` (15건), `test_memory_protocol_wiring.py` (6건).
  후자는 폐기 경로 참조·어댑터 부재·리드 미배선을 기계로 잡는 회귀 가드다 — 원래 버그를 재현하면 실패한다.

### Fixed
- MEMORY-PROTOCOL [R-c]를 AgentsToZ 경로로 재작성. 헤더의 저장소 설명·예산(어댑터 Bash 1회)·
  적용 범위도 함께 갱신.
- `CS-codebase-review`에 Phase R이 아예 없던 것을 추가 (29.1.0 → **29.2.0**). `## Recurring Issues`는
  이 저장소에서 이미 반복 확인된 결함 패턴이므로 리뷰어 CONTEXT에 verbatim 주입한다.
- `plugins/CLAUDE.md` 공유 프로토콜 색인에 MEMORY-PROTOCOL이 0건이던 것을 추가 —
  "AgentsToZ가 적재(write)하고 CS 플러그인이 소비(read)한다"는 역할 분담을 명시.

## [integration] 2026-08-25 — csn-upgrade-u1-u7(PR #3) 통합

7주간 48커밋 앞서간 main 위로 U1~U7을 통합했다. 31개 충돌은 **main의 학습 승격분을 보존하는 쪽**으로 해소했다.

### 보존한 main 내용 (브랜치가 덮어쓰려던 것)
- LOOP-PROTOCOL `[g] FAN-OUT BRIEFING` / `[h] PARALLEL WRITE ISOLATION` (8/22 승격, 근거 #119/#122) — 브랜치의 TASK-CONTRACT 포인터와 **병기**
- cs-design design-lead: design-system-consistency ↔ anti-pattern-detector 중복 채점 분리 규칙
- CS-codebase-review SKILL: finding ID F001 재부여 + 필터링 금지 계약 (브랜치의 카드 채택 지시 `FIRST ACTION`은 추가)
- cs-ship ship-lead: `GATE-LOOP RECORD(verdict 기록)` OWNS, "cs-ship은 별도 verifier를 스폰하지 않는다"
- CS-plan plan-lead: 테스트명 문자열 완전 일치 규칙 (브랜치의 2-wave 스팟체크 위에 유지)
- cs-smart-run 매니페스트 `name` — 브랜치의 `smart-run` 회귀를 차단 (1.1.1에서 고친 rename 버그)

### 번호 충돌 재부여
- CS-test `Phase 2.6` 중복 → 2.5 검증 → **2.6 반론 라운드**(DEBATE) → **2.7 게이트 루프**(GATE-LOOP)
- cs-ceo `모드 D` 중복 → main의 Dynamic Chain이 D 유지(37행이 참조), `/cs-company` 위임은 **모드 E**

### 제외
- `cs-end-v4` — marketplace의 `cs-end`를 v3에서 v4로 재지정해 main의 3.2.0을 대체하게 됨. v4(4.1.0)는 번호가 높지만 AgentsToZ 위임 참조 0건, v3는 6개 파일 보유 — v3가 실질적 최신
- `cs-experiencing-v8`(23파일), `cs-ceo-v14`, `cs-design-v19`, `cs-end-v1/v2` — main이 아카이브한 구버전
- v8 `knowledge/llm-api.md` — 항목 87/88이 v9 `llm-patterns.md`에 이미 존재(중복)

### Fixed
- Codex 매니페스트 8종이 VERSION과 어긋나 있던 것을 동기화 (CS-codebase-review·cs-ceo·cs-smart-run·CS-plan·CS-test·cs-clarify·cs-design·cs-ship)
- plugins/CLAUDE.md 인벤토리를 `routing_sync.py write`로 marketplace.json 기준 재생성

### 미배선 (후속)
- `cs-worktree-v1` — 파일만 존재, marketplace 미등록. 짝인 `/cs-end --merge-worktree`가 cs-end-v4에만 있어 v3에는 없음


## [session] 2026-07-02 — 프레임워크 업그레이드 U1-U7: 공유 프로토콜 계층 7종 + /cs-company 엔드투엔드 파이프라인

### Added
- **U1 AGENT-CARD 표준** (`plugins/shared/AGENT-CARD.md`): 필수 frontmatter(name/description/model/tools) + 5개 본문 섹션(Goal/Backstory/OWNS/Expected Output/Escalates when) 표준화. cs-design 인라인 분석가 5개 + CS-codebase-review 리뷰어 5개를 실제 에이전트 카드로 추출, 기존 17개 에이전트 파일 backfill, card-Read 스폰 패턴(≤5줄 delta)으로 3중 중복 제거
- **U2 TASK-CONTRACT** (`plugins/shared/TASK-CONTRACT.md`): 모든 Task 스폰에 기계 검증 가능한 CONTRACT 블록(expected_output/acceptance_criteria/re_dispatch_budget: 1) 의무화. 리드는 산출물을 읽기 전에 ls/wc -c/grep 수락 검사 → 실패 시 1회 재디스패치 후 N/A. 리포트 헤더에 `contracts: N issued / M accepted`
- **U3 DEBATE-PROTOCOL** (`plugins/shared/DEBATE-PROTOCOL.md` + `shared/agents/advocate.md`): REFUTED critical/high 판정에 1회 반론 라운드 + CONTESTED 상태 + '## 쟁점' 리포트 섹션, 워커 ≥3 & finding ≥8이면 peer cross-exam(DUPLICATE_OF/CORROBORATES/CONFLICTS_WITH)
- **U4 ARTIFACT-CONTRACTS** (`plugins/shared/ARTIFACT-CONTRACTS.md`): cs_artifact frontmatter + registry 등록/staleness 가드로 CLARIFY→PLAN→IMPLEMENT→REVIEW 아티팩트 체인 수리. CS-plan이 CLARIFY.md를 verbatim 인수, smart-run이 PLAN.md 자동 감지(Phase 0.7) + IMPLEMENT-REPORT.md 기록, CS-codebase-review가 REVIEW.md 게이트 기록
- **U5 MEMORY-PROTOCOL** (`plugins/shared/MEMORY-PROTOCOL.md`): Phase R(Recall) — 단기(registry)/일화(cs-experiencing INDEX)/전략(CORE.md)/에러노트 4계층 회상, 예산 상한(≤3 grep + ≤2 Read) + `recall: E<n>/C<n>/N<n>` 준수 헤더. BTW 경로 split-brain 수정(정본 ~/.claude/.experiencing-btw.json), cs-experiencing 학습 93건으로 재구조화(knowledge/llm-api.md 신설)
- **U6 HITL-POLICY** (`plugins/shared/HITL-POLICY.md`): auto/gate/always 모드 + --hitl 플래그, 서브에이전트용 CHECKPOINT payload + 버블링 규칙(재상신 1회, 런당 3회 상한), 명명된 체크포인트 5종 레지스트리. CS-plan 2-wave(arch-choice), CS-test build-blocker, smart-run plan-approval, cs-ceo redispatch-confirm, cs-design direction-choice
- **U7 /cs-company 파이프라인** (`plugins/shared/PIPELINE-PROTOCOL.md` + `cs-ceo-v15/commands/cs-company.md` + `skills/cs-company/`): CLARIFY→PLAN→IMPLEMENT→REVIEW→TEST→SHIP 엔드투엔드 SDLC 컨덕터 — frontmatter+registry 게이트, pipeline.json 상태/--from 재개, 스킵 규칙, cross-phase 리워크 라우팅(게이트당 ≤2, 총 ≤4 hop), GATE-LOOP에 5행 fault-routing 테이블

### Changed
- 버전업(minor): CS-plan 21.1.0, CS-test 26.1.0, CS-codebase-review 29.1.0, cs-design 20.1.0, cs-clarify 1.1.0, cs-ship 1.1.0
  (2026-08-25 통합 시 정정: cs-ceo는 main 15.2.0 위에 올려 **15.3.0**, cs-smart-run은 1.1.1 위에 올려 **1.2.0**.
  cs-end 4.1.0과 cs-experiencing 8.1.0은 반영하지 않음 — main의 cs-end-v3 3.2.0·cs-experiencing-v9 9.1.2가 실질적으로 최신)
- marketplace.json에 cs-company 항목 추가 (source ./plugins/cs-ceo-v15, 신규 플러그인 디렉토리 없음)
- plugins/CLAUDE.md: cs-company 라우팅 규칙 + Loop Engineering 공유 프로토콜 인덱스 갱신
- artifact_registry.py: REVIEW/IMPLEMENT-REPORT/TEST-REPORT 타입 추가 + `register` CLI 서브커맨드 노출; pre_pass.py ceo-preflight에 ship 경로 추가


## [session] 2026-06-12 — BTW pending 해소: plugins/CLAUDE.md 통합 제거 규칙 (goal-statement 재작성)

### Changed
- plugins/CLAUDE.md Loop Engineering: "통합 제거 규칙" 추가 — 커플링 반대편 동일 커밋 수정 + ✅ 반영됨 조건을 목표 진술(활성 플러그인 범위 = marketplace.json plugins 배열 + plugins/shared/ + plugins/CLAUDE.md 에서 실행성 참조 0건, 증거 인용 필수, 탐지 방법 자유)로 정의
- cs-experiencing #69: ⏸ DEFER → ✅ 반영됨 (REFUTED 사유 2건 해소: 스코프 기계적 정의 + Prescription Policy 준수)

### Session notes
- 스코프 정의 검증: git grep "CS_V7" 결과 활성 플러그인 내 잔존 참조는 전부 문서적 언급(노하우 #18 기록, cs-end 자체 완결 원칙 주석)이며 실행성 참조 0건 — 규칙 자체가 자기 사례로 PASS. 'git 추적 파일 전체' 1차 초안은 stale 버전 디렉토리(cs-ceo-v14)와 문서적 언급을 오탐해 폐기.
- ~/.claude/.experiencing-btw.json pending-patch 큐 비움


## [session] 2026-06-12 — /cs-end: 학습 3건 (#72-74) + cs-experiencing 8.0.3

### Added (cs-experiencing — knowledge/claude-code-platform.md)
- #72 하드코딩 시크릿 제거 ≠ 완료 — provider 측 rotation이 별도 필수 단계 (principle, 6/6)
- #73 컨텍스트 없는 재개 요청 — episodic memory 검색을 첫 단계로 (principle, 5/6)
- #74 JSON 설정 파일 수정은 json.load/json.dump 라운드트립 (tactical, 4/6)

### Changed
- cs-experiencing 8.0.2 → 8.0.3 (VERSION + plugin.json + SKILL frontmatter)
- 학습 INDEX 카운트 보정 (68건 표기 → 74건, #69-71 추가분 미반영분 포함)

### Session notes
- ~/.claude harness-diet 후속: settings.local.json Supabase 토큰 제거 + skills/README.md 삭제 (사용자 토큰 rotation 대기)
- Decay 리뷰: stale 3건(#7-9) 검토, 이번 세션 지식으로 반박 근거 없음 → deprecated 0건
- BTW pending 1건 유지: plugins/CLAUDE.md Loop Engineering 규칙 goal-statement 재작성 대기


## [session] 2026-06-12 — /cs-end: 학습 3건 (#69-71) + cs-experiencing 8.0.2

### Added (cs-experiencing — knowledge/claude-code-platform.md)
- #69 의존성 제거 결정의 커플링 드리프트 — 원칙 기록 ≠ 실행 (principle, 6/6, 스켑틱 CONFIRM)
- #70 외부 소스 원칙 추출 — 생성/기각(adversarial refuter) 단계 분리 (tactical, 6/6, 스켑틱 DOWNGRADE — kill-rate는 관찰값 한정)
- #71 새 프로토콜은 grep 가능한 준수 아티팩트 문자열과 함께 설계 (principle, 6/6, 스켑틱 CONFIRM)

### Changed
- cs-experiencing 8.0.1 → 8.0.2 (VERSION + plugin.json + SKILL frontmatter)

### Deferred (Phase 2.7 verifier REFUTED → btw 큐)
- plugins/CLAUDE.md 학습 반영 규칙 강화 패치 — '활성 파일' 미정의 + Prescription Policy(목표 진술 우선) 위반으로 revert, goal-statement 형태 재작성 대기

## [session] 2026-06-12 — cs-end CS_V7 외부 볼트 의존 제거 (자체 완결 원칙 적용)

사용자 지시: 이 프로젝트는 단독으로 작동해야 하며 CS_V7과 무관하다. cs-ceo 노하우 #18(2026-05-30)에서 이미 확립된 원칙이 cs-end에는 미적용 상태로 남아 있던 드리프트를 해소.

### Removed
- `cs-end-v3/commands/cs-end.md` Phase 2.1 (CS_V7 Knowledge Write) 전체 삭제 — `$HOME/CS_V7/raw/` 쓰기 + `graphify-sync.sh` 트리거 + Phase 6 ingest 힌트 제거
- `cs-end-v3/.claude-plugin/plugin.json` 설명의 CS_V7 문구 + `cs-v7` 키워드 제거
- `marketplace.json` cs-end 설명의 "CS_V7 knowledge write" 문구 제거

### Added
- `cs-end.md` 상단에 자체 완결 원칙 명문화: 외부 볼트 읽기/쓰기 금지, 학습 저장소는 cs-experiencing SKILL.md 단일
- cs-ceo 노하우 #18에 ✅ 반영됨 addendum (cs-end 측 적용 완료 기록)

## [session] 2026-06-12 — cs-experiencing 노하우 3개 추가 (dash1-v2 대시보드 세션)

### Added (cs-experiencing SKILL.md)
- #12 Korean 파일에서 Edit 툴 실패 — Python writelines 패턴 (principle, 6/6)
- #13 Derived slice 재사용으로 다수 sparkline 데이터 생성 (principle, 6/6)
- #14 HeroSparkline optional height prop — 컴포넌트 복제 없이 크기 변형 흡수 (tactical, 4/6)

## [session] 2026-06-12 — Fable 5 프롬프트 델타 (P3) — 공수 비례 + 프로토콜 검증 가능화 + 단일 진실 드리프트 제거

공개된 Fable 5 시스템 프롬프트(claude.ai 소비자판)에서 이식 가능한 원칙 8개를 추출, 60-에이전트 감사로 27건 후보 → 적대적 반박 검증으로 12건 확정 → 전부 구현.

### Added
- `plugins/shared/LOOP-PROTOCOL.md` 규칙 [f] OUTPUT PROPORTIONALITY: confirmed finding 0건이면 풀 템플릿 대신 필수 헤더 + 에이전트별 1줄(핵심 측정치 포함) — 빈 '없음' 섹션 금지. [b]/[d] 의무는 유지
- CS-test 스코프 티어 (knowhow #16 승격): Quick(페이지 ≤2 / 단일 기능) · Standard(기본 11개) · 단일 관심사 — 커버리지 분모를 스폰 수로 조정, 하드코딩 /13 제거
- CS-codebase-review 스코프 게이트: total_files ≤10 또는 total_lines ≤1500 → 5-agent 대신 통합 리뷰어 1개 (Phase 1.5b 검증은 유지); 0-candidate 렌즈 스킵 규칙
- CS-plan SCOPE=small 경량 경로: 단일 모듈/유틸이면 plan-lead 단독으로 경량 PLAN.md (4-agent 팀 생략)
- 루트 CLAUDE.md 라우팅 예외: 1-3개 직접 도구 호출로 답할 수 있는 단건 요청은 파이프라인 생략 (생략 사유 1줄)

### Changed
- LOOP-PROTOCOL 참조 규약: '따른다' 선언 → BLOCKING Read-first + 리포트 헤더 `protocol: LOOP-PROTOCOL [a-f] loaded` 검증 가능 아티팩트 (13개 캐리어 일괄 갱신)
- 워커 계약: read-first + 전량 보고(severity+confidence+evidence, 필터링 금지 — 필터는 리드) — CS-test/plan/design/codebase-review 스폰 템플릿에 주입
- design-lead: 성공 기준 fan-out 선언 + DESIGN-REVIEW.md 2번째 줄 verdict-first (`종합 — 기준 대비: PASS/FAIL`)
- cs-experiencing 14-agent 로스터 드리프트 제거 (실제 15-agent; 5개 파일 → count-free + $LATEST_TEST 로스터 포인터); .claude/CLAUDE.md 85줄 → 목적+sort -V 규칙+포인터로 축소
- cs-ceo External Knowledge Gate: 설치 버전을 쿼리에 포함 + 발췌에 문서 버전/조회 날짜 기록 + 메이저 불일치 플래그; 캐시 스킵 조건을 동일 주제·동일 버전 범위로 한정 (중복 3곳 일괄)
- pre_pass.py: Python 3.11 호환 수정 (f-string 내 백슬래시 SyntaxError)
- 검증: 충실성 verifier PASS (12/12) + 회귀 verifier 2건 차단 → 수정 라운드 후 레일 전부 exit 0

## [session] 2026-06-12 — Loop Engineering P2 (R7~R9) — Python 레일 + 탈처방 + 라우팅 단일 소스화

### Added
- `plugins/shared/scripts/routing_sync.py`: marketplace.json ↔ 라우팅 규칙 drift 탐지(`check`) + plugins/CLAUDE.md 플러그인 인벤토리 자동 생성(`write`)
- `pre_pass.py learn-append`: 모든 플러그인이 구조화 학습 후보를 BTW 저장소에 캡처 (근거 없으면 tactical 상한)
- `pre_pass.py version-check`: VERSION == plugin.json == SKILL frontmatter 단언 (숫자 정규화 1==1.0.0) — cs-end Phase 4 §1.5 + version-up STEP 4b push 차단 게이트로 wiring
- `artifact_registry.py find-meta / verdict`: 아티팩트 신선도(fresh/stale/missing) + GATE-LOOP verdict/round/blocking_items 세션 간 기록·복원; cs-ship Phase 0 staleness 가드

### Changed
- **R8 탈처방 스윕** (5개 플러그인, 순감 약 -660줄): 리터럴 grep/bash/JS 탐지 레시피 → 목표+증거 진술, 이모지 박스 템플릿 → 필수 필드 리스트, cs-ceo infer_timing() 키워드 매칭 → 판단 지시. 수치 임계값/루브릭/JSON 스키마/측정용 스크립트는 전부 보존
- **R9 단일 소스화**: pre_pass.py 도메인 테이블이 marketplace.json에서 런타임 파생; plugin-versions도 동일; latest_plugin 숫자 정렬 (v9>v26 사전순 버그 수정)
- ceo-preflight에 session_digest 동봉 (라우팅이 메모리 소비); plugins.ceo 키 추가 + ceo.md LATEST_CEO 잘못된 'experiencing' 키 조회 수정 + PREPASS_RUNNER 경로 누락(/plugins/) 수정
- abspath_check.py: 라인 중간 `#` 가 라인 전체를 스킵시키던 버그 수정 (전체 라인 주석만 스킵)
- 버전 메타데이터 7개 플러그인 동기화 (CS-test 1.0.0→26.0.0 등)
- 검증: 적대적 verifier 2개 모두 PASS (발견된 3건 — find-meta 파일 의존, verdict 인자 검증, ceo 경로 — 즉시 수정)

## [session] 2026-06-12 — Loop Engineering 구조조정 (R1~R6)

### Added
- `plugins/shared/LOOP-PROTOCOL.md`: 공유 루프 엔지니어링 프로토콜 — EVIDENCE / SUCCESS CRITERIA FIRST / BOUNDED LOOP / COVERAGE HONESTY / REPORT FULL, FILTER DOWNSTREAM + Prescription Policy. 모든 CS 리드가 참조
- `plugins/shared/agents/verifier.md`: 재사용 가능한 반박(refuter) 검증 에이전트 — CONFIRMED/REFUTED/UNCERTAIN
- `plugins/shared/GATE-LOOP.md`: 판정형 플러그인용 gate→record→fix→re-gate 프로토콜 (최대 3라운드)
- `plugins/CS-test-v26/agents/finding-verifier.md`: critical/high 발견 재현 검증 에이전트 (Phase 2.5)
- `plugins/cs-end-v3/agents/`: 누락되었던 4개 에이전트 정의 (JSON 출력 계약, haiku/sonnet 티어)
- `plugins/cs-experiencing-v8/skills/experiencing/knowledge/`: 학습 저장소 주제별 분리 + 인덱스 테이블
- `docs/LOOP-ENGINEERING-AUDIT-2026-06.md`: 전체 감사 보고서 (15개 감사, 54개 확정 갭, R1~R9 플랜, 7단계 자가 업그레이드 루프 설계)

### Changed
- **모든 판정형 플러그인에 적대적 검증 + 유한 루프 도입**: cs-ceo (Phase 3.5 스팟체크 + 3.6 Goal Gate Check, 목표 달성도 테이블), CS-test (Phase 2.5 검증 + coverage 캡), CS-codebase-review (Phase 1.5 refuter, CONFIRMED 기반 등급, provenance 태그), cs-ship (Phase 2-0 DONE/VERIFIED 스팟체크, 테스트 스위트 실제 실행, --fix 유한 루프)
- **자가 업그레이드 루프 폐쇄** (cs-end-v3): Phase 2.6 Prompt Patch (PASS 학습 → PATCH/MEMO/DEFER), Phase 2.7 패치 적대적 검증, Learning Gate 신규성 grep 강화 + principle 스켑틱, Phase 4 git 절차 명세 (staging scope, AUTO_NO_PUSH), Forget Gate 인용 기반 감쇠
- **휴면 학습 적용**: CS-plan #3/#5/#6, CS-test #17/#21/#23, cs-design lessons 5/6 → 운영 프롬프트에 반영 (✅ 반영됨 표시)
- **버그/드리프트 수정**: cs-clarify 병렬↔순차 모순 해소, cs-experiencing 하드코딩 버전 경로 → sort -V 패턴, cs-ship 절대경로 제거, CS-test/CS-plan 죽은 경로 수정, VERSION 2 잔재 삭제
- `plugins/CLAUDE.md`: Loop Engineering 공통 프로토콜 섹션 + "학습은 프롬프트를 패치해야 한다" 규칙 + 에러 노트 recall 규칙
- cs-smart-run: Phase 0 SPEC CHECK + Phase 1.5 plan-critic + Phase 2.5 VERIFY (최대 2라운드, 2회차 opus 승격)

## [session] 2026-06-09

### Added
- `plugins/cs-experiencing-v8/skills/experiencing/SKILL.md`: 학습 #67~68 추가
  - #67 (tactical): Vercel CDN bundle mismatch artifact — tsc+build 통과 시 CDN 불일치 의심, 재배포로 해결
  - #68 (principle): 대형 JSX 파일에서 `</>}` vs `})()}` 구조 추적 패턴 — 인덴테이션+토큰 타입 동시 추적
- `plugins/cs-experiencing-v8/VERSION`: 8.0.0 → 8.0.1
- `CS_V7/raw/cs-session-2026-06-09-large-jsx-fragment-iife-tracing.md`: principle-tier 학습 CS_V7 저장

## [session] 2026-05-23

### Added
- `plugins/cs-experiencing-v8/skills/experiencing/SKILL.md`: 학습 #49 추가 — "known_marketplaces.json은 신뢰할 만한 source-of-truth가 아니다" (principle tier)
  - 배경: /doctor가 extraKnownMarketplaces 14개 항목의 source 누락 오류를 보고했고, 복원 source로 쓰려던 known_marketplaces.json에서 두 항목(`claude-code-plugins → anthropics/claude-code`, `cli → googleworkspace/cli`)이 잘못된 repo를 가리키고 있었음
  - 교훈: known_marketplaces.json은 최초 설치 시 입력 URL을 그대로 기록 — 마켓플레이스 실체 검증 없음. 일괄 변환 전 entry 검증 필수
- `plugins/cs-experiencing-v8/VERSION`: 10 → 11

## [session] 2026-05-02

### Fixed
- `~/.claude/hooks/notification-hook.sh`, `stop-hook.sh`: `.env` 없는 프로젝트에서 `exit 1` → `exit 0` 변경
  - 원인: 훅 비정상 종료가 Claude Code 입력창을 회색으로 블로킹
  - 영향: CS볼트V5 등 `.env` 없는 작업 폴더에서 입력 불가 현상 해소

## [cs-end-v1] 1.1.0 — 2026-05-01

### Added
- Phase 6: Context Compact suggestion — after Phase 5 push report, generates a
  1-2 line session summary and presents a ready-to-run `/compact [summary]` command.
  Skip with `--no-compact` or `--learning-only`.
- `--no-compact` flag added to usage examples.

### Changed
- Frontmatter description updated to include "context compact 제안".
- plugin.json description updated.
