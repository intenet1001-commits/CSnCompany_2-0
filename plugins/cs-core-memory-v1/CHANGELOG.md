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
- collector source read와 state merge를 같은 lock transaction으로 직렬화하고 source generation을 재검증해 느린 collector가 최신/해결 상태를 되돌리지 못하게 했다.
- duplicate `memoryId`의 모든 알려진 root를 state에 보존해 scoped collect가 충돌을 조기 해제하지 못하게 했다.
- Slack/Stripe/GitLab 등 공급자 토큰과 보수적인 고엔트로피 credential quarantine을 추가했다.
- bootstrap 20개와 next 5개를 우회 불가능한 hard limit으로 만들고 shared pending digest/queue/entry byte 상한을 추가했다.
- empty stable ID placeholder와 AgentsToZ split-manifest byte-exact 합성을 지원한다.
- scheduler는 `~/.csncompany/bin` stable copy를 실행하고 status에서 source hash와 native definition freshness를 검사한다.
- Codex-only versioned cache에서도 CEO project-memory recall helper를 찾도록 경로 parity를 보완했다.
- POSIX state transaction은 검증한 parent directory descriptor와 `O_NOFOLLOW` 상대 연산을 사용하고, Windows는 모든 ancestor directory handle을 reparse-point no-follow/delete-share 제외 모드로 유지해 validation/use 경로 재바인딩을 차단한다. collect 집계도 같은 lock snapshot에서 반환한다.
- provider credential detector를 collector와 shared queue/digest에 같은 semantics로 적용하고 public integrity/checksum/SSH key·문맥 없는 opaque 값의 entropy 오탐을 억제했다.
- session digest를 256 files/4 MiB/200 headers/128 KiB와 UTF-8 byte field 상한으로 제한하고 legacy secret row를 모델 입력에서 격리한다.
- empty stable ID가 채워질 때 `filled`로 기록하고 reviewable하지 않았던 placeholder candidate를 supersedes 대상으로 연결하지 않는다.
- `/cs-memory:learn`, `/cs-memory:schedule`, `/cs-memory:status`, `/cs-memory:upgrade` 계약을 새 소유권/비중복 흐름으로 정리했다.

## 2.0.1

- 장기기억 학습 후보와 선택적 에이전트 업그레이드 표면을 추가했다.
