# cs-worktree CHANGELOG

## 1.0.0 — 2026-07-02
- 신규 플러그인. `/cs-start` 명령 추가.
- 대상 프로젝트에 격리된 git worktree + `cs-work/<slug>-<timestamp>` 브랜치 생성.
- 전역 매니페스트(`~/.claude/state/cs-worktree/manifest.json`)에 생성 사실 기록 → cs-end `--merge-worktree` 연동의 단일 출처.
- base 브랜치 자동 감지(origin/HEAD → main → master → 현재 HEAD), `--base`/`--name`/`--list` 플래그.
- 비파괴 설계: 워크트리 추가만 수행, force-push·브랜치 삭제·워킹트리 리셋 없음, 대상 저장소 파일 자동 편집 없음.
- 출처: "특정 프로젝트에서 워크트리 생성 후 cs-end 시 main 머지" 워크플로우 요청 (cs-ceo 오케스트레이션, 사용자 승인 기본값).
