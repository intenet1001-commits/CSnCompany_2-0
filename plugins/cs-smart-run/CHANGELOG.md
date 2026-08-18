# cs-smart-run CHANGELOG

## 1.1.1 — 2026-08-02
- `smart-run`에서 `cs-smart-run`으로 이름을 바꿀 때 남은 내부 식별자와 트리거 문구를 통일
  - Claude/Codex 플러그인 매니페스트의 `name` 수정
  - 스킬 호출 예시를 `/cs-smart-run`으로 수정

## 1.1.0 — 2026-07-02
- VERIFY→fix 루프(Phase 2.5)를 벤치마크 패턴으로 정식화
  - P4 instructor↔assistant 역할극: verifier=instructor(한 번에 하나씩 지시), executor=assistant(지시 항목만 수정)
  - P2 종료식: `max_turns(2) OR sentinel(모든 DoD PASS) OR no_delta`, 종료 조건 발화 기록
- 근거: plugins/shared/ORCHESTRATION-PATTERNS.md P2/P4 (AutoGen termination + ChatDev role-play)

## 1.0.0
- Spec check → Opus 플랜 → Sonnet 실행 → 독립 verifier (bounded verify→fix)
