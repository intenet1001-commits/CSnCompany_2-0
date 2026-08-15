# cs-memory

CSnCompany의 장기 학습 계층입니다. **AgentsToZ 프로젝트 기억이 원본**이고 cs-memory는 읽기 전용 소비자입니다.

## 데이터 흐름

```text
AgentsToZ memory agent
  └─ .agent-memory/config.json + CORE.md 또는 notes/manifest.json
       ├─ cs-ceo: 분할 전 active constraints + 목표 관련 항목 최대 5개 recall
       ├─ periodic collector: 파일 스탬프 → 변경 entry version 포인터만 저장 (LLM 0회)
       └─ /cs-memory:learn: pending 최대 5개 → entry version당 교훈 최대 1개
            └─ shared learning queue
                 └─ /cs-memory:upgrade → 가장 작은 owner skill에 merge/replace
```

## 안정적인 식별

- 원본 기억: `memoryId`
- 논리 항목: H3 다음의 `<!-- memory-entry-id:<24 lowercase hex> -->`
- 내용 버전: marker를 제외한 정규화 본문과 contested/accepted 경계의 SHA-256
- 학습 후보: `memoryId + entryId + contentVersionHash`

제목 변경·일반 섹션 이동·노트 이동·manifest 순서 변경·mtime-only touch는 같은 본문을 다시 학습하지 않습니다. 단, contested 경계 이동과 본문 수정은 새 버전으로 처리합니다. 미처리 이전 버전은 superseded 처리하고 삭제는 tombstone으로 제한 보존합니다.

## 명령

- `/cs-memory:learn [here|folder /abs|pc|pending]`
- `/cs-memory:schedule [status|install registry|install folder /abs|install pc|remove]`
- `/cs-memory:status`
- `/cs-memory:upgrade`

기본 정기 수집 간격은 6시간이며 unchanged stamp는 노트 본문을 읽지 않습니다. 7일마다 full audit를 수행합니다. 정기 수집 자체는 모델을 호출하지 않습니다.
처음 발견한 기존 기억은 `observed` baseline으로만 기록해 과거 전체를 새 교훈으로 쌓지 않습니다. 사용자가 `/cs-memory:learn`을 명시했을 때만 baseline 중 최대 20개를 후보화하고 실제 본문 전달은 한 번에 최대 5개입니다.
CS CEO는 실행 종료 시 `actionablePending`이 있을 때만 같은 활성 세션에서 `learn pending`을 한 번 처리합니다. 별도 무인 모델 프로세스는 시작하지 않습니다.

## 보안/비용 경계

- 원본 기억을 initialize/edit/backup/push/pull하지 않습니다.
- 상태에는 재검증용 프로젝트 포인터·file stamp와 ID/hash/timestamp/disposition/정수 우선순위만 저장하며, 기억 제목과 본문은 저장하지 않습니다.
- symlink, 범위 탈출, 중복 memory ID, 비밀 패턴, 비정상 크기, 불안정한 읽기는 fail closed/quarantine합니다.
- PC 범위는 홈 디렉터리와 AgentsToZ registry로 제한하고 dependency/cache/credential 디렉터리를 prune합니다.
- 모델에는 현재 pending 버전 최대 5개만 전달하며 전체 기억이나 전체 PC 내용을 전달하지 않습니다.
