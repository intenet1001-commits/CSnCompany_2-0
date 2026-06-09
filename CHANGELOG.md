# Changelog

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
