# Changelog


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
