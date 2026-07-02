# cs-end CHANGELOG

## 4.0.0 — 2026-07-02
- **Phase 4.5 워크트리 머지 (opt-in)** 신규. `--merge-worktree` 플래그 시에만 실행.
  - cs-worktree `/cs-start` 매니페스트(`~/.claude/state/cs-worktree/manifest.json`)에서 대상 프로젝트의 active 워크트리를 탐색.
  - 머지 방식은 실행 시 AskUserQuestion으로 물어보며 **기본값은 PR 생성**(`gh pr create`), 직접 머지 선택 가능.
  - conflict 감지 시 **자동 해결 없이 중단** + 수동 해결 안내 (git merge-tree 비뮤테이팅 사전 점검 우선).
  - `--validate` 플래그로 머지 전 cs-ship 검증을 선택적으로 실행.
  - 머지 전 사전 점검: 워크트리 clean 여부, base 대비 커밋 존재 여부.
  - 결과에 따라 매니페스트 status를 merged/pr-open으로 갱신. force-push·브랜치 삭제·워크트리 제거는 자동 수행하지 않음(안내만).
- Phase 5 리포트에 워크트리 머지 결과 라인 추가 (MERGED/PR-OPEN/HALTED(conflict)/SKIPPED).
- **기존 경계 보존**: `--merge-worktree`가 없으면 v3와 100% 동일하게 동작. "마켓플레이스 레포만 자동 커밋, 프로젝트 디렉토리는 손대지 않는다" 원칙 유지 — 프로젝트 미커밋 변경을 자동 커밋하지 않고, 이미 커밋된 워크트리 브랜치만 반영.
- 출처: "특정 프로젝트에서 워크트리 생성 후 cs-end 시 main 머지" 워크플로우 요청 (cs-ceo 오케스트레이션, 사용자 승인 기본값).

## 3.1.0 이전
- v3: Error Note 점검/캡처 (Phase 2.2), Core Memory Update (Phase 1.5).
- v2.1: LSTM/GRU 게이트 패턴 — Session Pre-Pass Digest, Selective Version-Up, Learning Gate, Knowledge Decay, 구조화 compact 핸드오프.
