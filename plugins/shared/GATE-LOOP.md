# GATE-LOOP — verdict 산출 플러그인용 게이트 루프 프로토콜

적용 대상: verdict를 산출하는 플러그인 (cs-ship, CS-test, CS-codebase-review).
루프 의미론(증거/경계/조기 종료)은 plugins/shared/LOOP-PROTOCOL.md를 따른다.

## 프로토콜 (최대 3라운드)

```
round = 1
loop:
  1. GATE   — 게이트 실행 (검증/테스트/리뷰)
  2. RECORD — verdict + round + blocking_items 기록:
              `python3 plugins/shared/artifact_registry.py verdict <TYPE> <PASS|FAIL|WARNINGS|BLOCKED> <round> [item ...]`
              (또는 `source plugins/shared/artifact_registry.sh` 후 `cs_record_verdict`).
              세션이 끊겨도 다음 게이트가 `find-meta`로 이전 라운드 상태를 복원한다.
  3. PASS → 종료. 리포트에 round 이력 포함.
  4. BLOCKED/FAIL → blocking_items에 해당하는 범위만 수정 에이전트 디스패치
              (전체 재실행 금지 — 실패 항목만)
  5. RE-GATE — 직전 라운드에서 실패했던 항목만 재검증
  6. round += 1; round > 3 또는 라운드 델타 없음(새로 고쳐진 항목 0개)
     → 루프 중단, 사용자 에스컬레이션
```

## 규칙

- **실패 항목만 재검증**: 재실행(re-gate)은 이전 라운드의 blocking_items만 대상으로 한다. 이미 PASS한 항목을 다시 돌리지 않는다.
- **델타 없으면 즉시 중단**: 한 라운드가 아무것도 고치지 못하면 round 3까지 기다리지 않고 중단한다.
- **3라운드 후 에스컬레이션**: round 이력(각 라운드의 verdict + 남은 blocking_items)을 첨부해 사용자에게 결정을 요청한다. 자동으로 PASS 처리하지 않는다.
- 모든 라운드의 verdict는 증거 기반이어야 한다 (LOOP-PROTOCOL [a]).
