# Changelog

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
