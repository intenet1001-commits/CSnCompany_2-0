# GATE-LOOP — verdict 산출 플러그인용 게이트 루프 프로토콜

적용 대상: verdict를 산출하는 플러그인 (cs-ship, CS-test, CS-codebase-review).
루프 의미론(증거/경계/조기 종료)은 plugins/shared/LOOP-PROTOCOL.md를 따른다.

## 프로토콜 (최대 3라운드)

```
round = 1
loop:
  1. GATE   — 게이트 실행 (검증/테스트/리뷰)
  2. RECORD — verdict + round + blocking_items 기록:
              `$RUN_PY "${CLAUDE_PLUGIN_ROOT}/../shared/artifact_registry.py" verdict <TYPE> <PASS|FAIL|WARNINGS|BLOCKED> <round> [item ...]`
              (RUN_PY = python3, 없으면 `uv run --quiet --no-project python` — 호출 규칙 정본은
              plugins/shared/ARTIFACT-CONTRACTS.md "Registry 호출 규칙".
              또는 `source plugins/shared/artifact_registry.sh` 후 `cs_record_verdict`).
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

## 파이프라인 리워크 (cross-phase)

적용 대상: /cs-company conductor (plugins/shared/PIPELINE-PROTOCOL.md). 위의 게이트 루프가 **phase 내부**(같은 게이트 재시도)라면, 이 섹션은 **phase 사이**(하류 게이트 FAIL → 상류 phase로 되돌리기)를 다룬다. 루프 의미론(실패 범위만, 델타 없으면 중단)은 동일하다.

### fault-routing 표

하류 게이트 FAIL 시 conductor는 blocking_items의 fault 유형으로 목적지를 정한다:

| fault (게이트에서 확인된 것) | 리워크 목적지 | payload (스코프) |
|---|---|---|
| TEST — confirmed functional/console/db finding | IMPLEMENT | finding JSON + REPORT.md 해당 발췌 — **인용된 파일만** 수정 스코프 |
| TEST — finding이 누락된 요구사항으로 추적됨 | PLAN | finding + CLARIFY.md 해당 anchor (요구사항 갭 명시) |
| REVIEW — CONFIRMED critical/high | IMPLEMENT | finding + file:line 증거. fixer는 **red test를 먼저** 작성·실행한 뒤 수정한다 |
| REVIEW — 아키텍처 레이어 위반 (PLAN.md 대비) | PLAN (delta 재실행) | 위반 항목 + PLAN.md 해당 섹션 — 전체 4-agent 재실행 금지, **arch-designer + checklist-builder만** 재스폰 (cs-clarify의 델타만 재실행 패턴과 동일) |
| SHIP — spec-item MISSING 또는 coverage MISSING | IMPLEMENT | cs-ship Phase 2.5의 항목별 sonnet fixer 스펙 그대로 재사용 (항목 + 관련 PLAN.md 섹션 + 변경 파일 목록) |

### 자기-phase fault (표에 없는 게이트 FAIL — CLARIFY/PLAN/IMPLEMENT)

fault가 하류 게이트가 아니라 **그 phase 자신의 아티팩트**에서 확인된 경우(CLARIFY `status: blocked`/clarify_score < 7, PLAN 정합성 CRITICAL 미해결, IMPLEMENT DoD FAIL/UNDONE 항목)는 backward hop이 아니라 **같은 phase 재시도**다: 해당 플러그인의 내부 경계 루프로 blocking_items 스코프만 재실행하고(전체 재실행 금지), 게이트당 리워크 디스패치 예산(≤2)에 계상한다. 같은 phase가 2회 연속 blocked로 돌아오면 아래 STUCK 규칙으로 에스컬레이션한다 (자동 PASS 처리 금지).

**이유**: fault-routing 표는 "하류가 상류 결함을 발견"한 경우만 다룬다 — 자기 게이트 FAIL에 목적지 규칙이 없으면 첫 3개 phase의 FAIL에서 conductor 행동이 미정의가 되어 파이프라인이 조용히 선다.

> 예시: PLAN 게이트 FAIL — frontmatter `status: blocked`, blocking_items에 "정합성 CRITICAL: architecture.md에 Infrastructure 레이어 누락" → 표 매칭 없음 + fault 출처가 PLAN 자신 → CS-plan을 해당 blocking_items 스코프로 재실행(PLAN 게이트 리워크 예산 1/2 소비) → 재게이트 PASS → 진행. 두 번째도 blocked → STUCK AskUserQuestion.

### 예산과 종료 (KEEP-tier 숫자)

- **게이트당 리워크 디스패치 ≤ 2회**, **런 전체 backward hop ≤ 4회**. 초과 시 즉시 중단하고 termination을 `budget`으로 기록한다.
- 리워크는 상류 phase **전체를 재실행하지 않는다** — blocking_items 스코프만 (위 "실패 항목만 재검증" 규칙의 cross-phase 확장).
- **re-gate는 직전 실패 항목만 재검증한다.** TEST의 경우 blocking_items를 냈던 워커만 재실행하는 미니 재테스트다 (CS-test 노하우 #22 — 수정 후 핵심 경로 재검증; full re-run 금지).
- 한 hop이 델타(새 PASS/해소된 blocking_item) 0이면 → **STUCK 리포트**: pipeline.json의 round 이력 전체 + 남은 blocking_items를 첨부하고 AskUserQuestion 1회 — [WARNINGS로 수용하고 계속 / 수동 수정 후 `--from <phase>` 재개 / 작업 취소]. 자동 PASS 처리 금지.
- 모든 hop은 이중 기록한다: ① `$RUN_PY "$REGISTRY" verdict <TYPE> <verdict> <round> [item ...]` ② pipeline.json `reworks` 배열 append (`{from, to, reason, items, hop}`). 최종 파이프라인 리포트 표(PIPELINE-PROTOCOL [6])에 게이트별 termination(`clean|max_rounds|no_delta|budget`)을 출력한다.

**이유**: 되돌리기가 없으면 하류 발견이 리포트로만 남고(수정은 사람 몫), 예산이 없으면 TEST↔IMPLEMENT 무한 탁구가 된다 — fault별 목적지 표 + 숫자 예산이 그 사이의 유일한 안정점이다.

> 예시: TEST 게이트 FAIL — blocking_items에 "결제 확인 페이지 404 (functional, confirmed)" → 표 1행 매칭 → IMPLEMENT로 hop 1 디스패치 (payload: finding JSON + REPORT.md 발췌, 스코프: `src/pages/confirm.tsx`) → 수정 후 re-gate는 해당 finding을 냈던 functional 워커만 재실행 → PASS → pipeline.json `reworks: [{from: "TEST", to: "IMPLEMENT", reason: "confirm 404", items: [...], hop: 1}]`, TEST termination = `clean` (rework 1회 병기).
