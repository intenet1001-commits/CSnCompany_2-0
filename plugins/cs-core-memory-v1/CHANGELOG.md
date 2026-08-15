# cs-memory CHANGELOG

## 2.1.0 — 2026-08-15

- AgentsToZ 프로젝트 기억을 유일한 원본으로 사용하고 구형 `~/.claude/core-memory` reader/writer를 제거했다.
- 단일 `CORE.md`와 `notes/manifest.json` 분할 기억을 모두 읽는 `memory_learning.py`를 추가했다.
- `memoryId + memory-entry-id + contentVersionHash` 기반 증분 상태, tombstone, superseded version, 원자적 잠금/저장을 도입했다.
- unchanged file stamp는 본문을 읽지 않고 건너뛰며 7일마다 full audit한다.
- 최초 발견한 기존 기억은 `observed` baseline으로 처리해 역사 전체를 새 후보로 누적하지 않고, 명시적 learn만 한 번에 최대 20개를 bootstrap한다.
- folder/PC/AgentsToZ registry 범위와 안전한 prune, symlink/secret/oversize quarantine, 중복 memory ID conflict 차단을 추가했다.
- 뒤늦게 발생한 memory ID 충돌은 기존 pending 후보까지 block하고, 분할 기억은 합성 뒤 manifest/노트 세대가 바뀌지 않았는지 재검증한다.
- state는 원본 재검증 포인터·ID/hash/time/disposition/정수 우선순위만 유지하며 기억 제목과 본문을 저장하지 않는다.
- 한 번에 최대 5개 현재 버전만 모델에 전달하고, entry version당 한 개의 컴팩트 교훈만 큐잉한다.
- shared learning queue에 `candidate_key` 중복 방지를 추가해 같은 기억 버전의 표현만 다른 교훈이 누적되지 않게 했다.
- macOS launchd, Linux systemd user timer, Windows Task Scheduler용 zero-model-call 정기 수집기를 추가했다.
- `/cs-memory:learn`, `/cs-memory:schedule`, `/cs-memory:status`, `/cs-memory:upgrade` 계약을 새 소유권/비중복 흐름으로 정리했다.

## 2.0.1

- 장기기억 학습 후보와 선택적 에이전트 업그레이드 표면을 추가했다.
