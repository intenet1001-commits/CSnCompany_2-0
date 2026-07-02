# PIPELINE-PROTOCOL — CS 전 단계 SDLC 파이프라인 프로토콜 (/cs-company)

한 문장 요청을 CLARIFY → PLAN → IMPLEMENT → REVIEW → TEST → SHIP으로 배달하는 conductor(cs-company)가 이 프로토콜을 따른다.
루프 의미론(증거/경계/조기 종료)은 plugins/shared/LOOP-PROTOCOL.md, cross-phase 리워크는 plugins/shared/GATE-LOOP.md의 "파이프라인 리워크" 섹션, 게이트 판독은 plugins/shared/ARTIFACT-CONTRACTS.md, 체크포인트는 plugins/shared/HITL-POLICY.md를 따른다.
참조 방법(conductor SKILL에 한 줄): `파이프라인 프로토콜 (BLOCKING 첫 단계): 첫 phase 실행 전 첫 행동으로 plugins/shared/PIPELINE-PROTOCOL.md와 plugins/shared/LOOP-PROTOCOL.md를 Read하고(리워크 판단 시 plugins/shared/GATE-LOOP.md "파이프라인 리워크" 섹션, 체크포인트 시 plugins/shared/HITL-POLICY.md, 게이트 판독 시 plugins/shared/ARTIFACT-CONTRACTS.md 추가 Read), 런 헤더에 'protocol: PIPELINE-PROTOCOL [1-6] loaded' 한 줄을 출력한다. 이 줄이 없는 리포트는 프로토콜 미적용으로 간주한다.`
(런타임 경로는 `${CLAUDE_PLUGIN_ROOT}/../shared/`로 해석한다. 절대 경로 금지.)

## [1] PHASE TABLE — 정본 단계 표

| # | phase | plugin entry | artifact_in | artifact_out | gate criterion |
|---|-------|--------------|-------------|--------------|----------------|
| 1 | CLARIFY | cs-clarify (SKILL) | GOAL_STATEMENT | `.cs-artifacts/CLARIFY.md` | frontmatter `gate.passed=true` (= ready_for_plan=true, clarify_score ≥ 7) |
| 2 | PLAN | CS-plan (SKILL) | CLARIFY.md | `[OUTPUT_DIR]/PLAN.md` (기본 `.tdd-plans/`) + implementation-checklist.md | "⚠️ 정합성 노트"에 미해결 CRITICAL 0건 (frontmatter `status: ready`) |
| 3 | IMPLEMENT | cs-smart-run (SKILL — Phase 0.7 PLAN INTAKE 경로) | PLAN.md | `.cs-artifacts/IMPLEMENT-REPORT.md` | DoD verifier PASS (frontmatter `gate.passed=true`) |
| 4 | REVIEW | CS-codebase-review (SKILL) | IMPLEMENT-REPORT.md | `.cs-artifacts/REVIEW.md` | grade ≥ B AND CONFIRMED critical 0건 (registry verdict PASS) |
| 5 | TEST | CS-test (SKILL) | 대상 URL/dev 서버 | `tests/results/REPORT.md` (type: TEST-REPORT.md) | 선언된 성공 기준 충족 AND confirmed critical 0건 (= CS-test 종합 pass — frontmatter `gate.passed=true` + registry verdict PASS; grade는 게이트 입력이 아니다) — URL/dev 서버 미탐지 시 auto-skip ([4]) |
| 6 | SHIP | cs-ship (SKILL) | PLAN.md + 상류 리포트 전체 | `.cs-artifacts/SHIP-REPORT.md` | registry verdict PASS |

각 phase는 독립 플러그인으로 단독 실행 가능해야 한다 — conductor는 phase 내부 프로토콜을 재정의하지 않고 각 플러그인의 기존 SKILL을 그대로 호출한다. artifact 타입/기본 경로는 ARTIFACT-CONTRACTS.md의 타입 표와 1:1이다.

**이유**: 파이프라인이 phase 내부를 소유하기 시작하면 단계별 단독 사용성(이 스위트의 핵심 차별점)이 죽는다 — conductor는 순서·게이트·상태만 소유한다.

> 예시: IMPLEMENT 단계에서 conductor는 구현 방법을 지시하지 않는다 — `smart-run` SKILL을 호출하면 그 안의 Phase 0.7이 registry에서 fresh PLAN.md를 감지해 Opus 플래닝을 스킵하고 체크리스트를 실행한다.

## [2] GATE EVALUATION — 게이트는 frontmatter + registry 판독이다 (게이트키퍼 에이전트 금지)

phase 완료 직후 conductor는 두 소스만 읽어 게이트를 판정한다:

1. `find-meta <type>` (ARTIFACT-CONTRACTS "Registry 호출 규칙") → `{path, age_days, freshness, verdict, round, blocking_items}`
2. artifact 파일의 `cs_artifact` frontmatter → `status` / `gate.passed` / `gate.blocking_items`

판정: artifact가 존재하고 `freshness: fresh`이고 [1] 표의 gate criterion(frontmatter `gate.passed=true`, verdict 산출 phase는 registry verdict PASS 병행 확인)을 만족하면 **GATE PASS**. 그 외(파일 부재, stale, `status: blocked`, verdict FAIL/BLOCKED)는 **GATE FAIL** → GATE-LOOP "파이프라인 리워크"로 라우팅한다. 판정에 새 에이전트를 스폰하지 않는다.

**이유**: 게이트 상태는 각 phase 리드가 이미 frontmatter+verdict로 기록해 놓았다 ([2] PRODUCER 계약) — 이를 다시 평가하는 게이트키퍼 에이전트는 비용만 있고 정보가 없다.

> 예시: REVIEW 완료 → `find-meta REVIEW.md` → `{verdict: "FAIL", round: 1, blocking_items: ["CONFIRMED critical: SQL injection src/db.ts:88"]}` → conductor는 REVIEW.md를 재채점하지 않고 blocking_items를 리워크 라우팅 표의 입력으로 사용한다.

## [3] PIPELINE STATE — `.cs-artifacts/pipeline.json`

conductor는 매 phase 전이(시작/게이트 판정/리워크 hop)마다 `.cs-artifacts/pipeline.json`을 갱신한다:

```json
{
  "goal": "<GOAL_STATEMENT>",
  "started_at": "<ISO 8601>",
  "current": "<지금 실행/대기 중인 phase>",
  "phases": [
    {"name": "CLARIFY", "status": "pending|running|passed|failed|skipped",
     "artifact": "<경로>", "verdict": "<PASS|FAIL|WARNINGS|BLOCKED|null>",
     "round": 0, "rework_count": 0, "termination": "clean|max_rounds|no_delta|budget|skipped|null"}
  ],
  "reworks": [
    {"from": "TEST", "to": "IMPLEMENT", "reason": "<fault 한 줄>", "items": ["<blocking_item>"], "hop": 1}
  ]
}
```

`--from <phase>` 재개: conductor는 pipeline.json을 Read하고 `status: passed`인 phase는 재실행하지 않으며, 각 passed phase의 artifact를 `find-meta`로 신선도 재확인한 뒤 지정 phase부터 진행한다 — GATE-LOOP의 find-meta 세션 복원과 동일 의미론.

**이유**: 6-phase 파이프라인은 한 세션에 다 안 들어갈 수 있다 — 상태가 디스크에 없으면 세션 사망 = 전체 재실행이고, 그 비용이 파이프라인 자체를 못 쓰게 만든다.

> 예시: SHIP 직전 세션이 끊김 → 새 세션에서 `/cs-company --from ship` → pipeline.json에서 CLARIFY~TEST가 passed임을 확인, `find-meta PLAN.md`가 fresh → SHIP만 실행.

## [4] SKIP RULES — 단계 생략 규칙

생략된 phase는 pipeline.json에 `status: skipped` + 사유 한 줄로 기록한다 (묵묵히 건너뛰기 금지).

- **CLARIFY**: Goal Gate(Skill goal) 결과 `was_clarified=false`이고 goal_statement에 미확정 HIGH 가정이 없으면(목표가 unambiguous) skip.
- **IMPLEMENT collapse**: CS-plan Step 1.5(항목 5)의 스코프 평가가 small(단일 모듈/유틸 — 새 레이어·외부 시스템 연동·도메인 모델 변경 모두 없음)이면 cs-smart-run 팀 스폰 대신 conductor가 체크리스트를 직접 실행한다. 단 IMPLEMENT-REPORT.md 생산+register 의무([1] 표)는 그대로 유지한다.
- **TEST auto-skip**: 대상 URL이 없고 실행 중인 dev 서버도 탐지되지 않으면 skip (탐지 방법 자유 — 목표: "브라우저로 접근 가능한 대상이 있는가"의 증거 확보).
- **`--skip <phase,...>`**: 사용자가 명시한 phase는 무조건 skipped. SHIP은 `--skip` 명시로만 생략할 수 있다 (auto-skip 없음 — 파이프라인의 최종 검증 게이트).

**이유**: 파이프라인이 모든 요청에 6단계 전부를 강제하면 작은 작업에서 비용이 산출물을 초과한다 — 생략은 허용하되 반드시 기록해 커버리지 정직성(LOOP-PROTOCOL [d])을 지킨다.

> 예시: "util 함수 하나에 캐시 붙여줘" → Goal Gate 명확(was_clarified=false) → CLARIFY skip, PLAN이 SCOPE=small 경량 플랜 산출 → IMPLEMENT collapse(conductor 직접 실행), URL 없음 → TEST skip → 최종 리포트에 skipped 3건 + 사유가 그대로 보인다.

## [5] CHECKPOINTS — 인간 확인 지점

- 기본 체크포인트 phase: `plan, ship` (`--checkpoint <phase,...>`로 변경). `--auto`(= `--hitl=auto`)면 중간 체크포인트 0회 — 모든 질문에서 default(계속 진행)를 조용히 채택한다 (HITL-POLICY [1]).
- 체크포인트 phase의 **게이트 PASS 직후** AskUserQuestion 1회: [계속 진행(default) / 아티팩트 보기 / 리워크(메모 포함) / 작업 취소]. "리워크" 선택 시 사용자의 메모를 payload로 같은 phase를 blocking_items 스코프 재실행하고(게이트당 리워크 예산에 계상 — GATE-LOOP "파이프라인 리워크"), "작업 취소"는 pipeline.json 경로를 알리고 즉시 종료한다.
- conductor는 **main context에서 실행**되므로 AskUserQuestion을 직접 호출한다. 서브에이전트 phase 리드가 반환한 CHECKPOINT payload(HITL-POLICY [2])는 conductor가 [3] 버블링 규칙으로 여기서 종결한다 — 더 위로 올리지 않는다.

**이유**: 질문 권한(main context)과 파이프라인 상태(conductor)가 한 곳에 있어야 phase 리드들의 체크포인트가 구조적으로 종착지를 갖는다 — conductor가 서브에이전트면 6단계 전부가 무질문 파이프라인이 된다.

> 예시: PLAN 게이트 PASS → 체크포인트 → 사용자가 "리워크: 결제는 Stripe 말고 Toss로" 선택 → conductor가 CS-plan을 delta 재실행(arch-designer+checklist-builder만) 후 재게이트 → PASS → IMPLEMENT 진행. PLAN 게이트 리워크 예산 1/2 소비로 기록.

## [6] FINAL REPORT — 파이프라인 리포트 + 종료 사유 의무

파이프라인 종료(정상/중단 모두) 시 conductor는 다음 표를 출력한다. 모든 행은 termination(종료 사유)을 가진다 — 사유 없는 종료는 프로토콜 위반이다:

```
| phase | artifact | gate | rounds | termination |
|-------|----------|------|--------|-------------|
| PLAN  | .tdd-plans/PLAN.md | PASS | 1 | clean |
| TEST  | tests/results/REPORT.md | PASS | 2 | clean (rework 1: → IMPLEMENT) |
| SHIP  | .cs-artifacts/SHIP-REPORT.md | FAIL | 2 | no_delta |
```

termination ∈ `clean`(게이트 1회 이상 시도 후 PASS) | `max_rounds`(라운드 상한 도달) | `no_delta`(델타 없음 조기 중단) | `budget`(리워크 예산 소진) | `skipped`(사유 병기). 표 아래에 reworks 배열 요약(각 hop의 from→to + 사유)을 붙인다.

**이유**: "왜 여기서 멈췄는가"가 리포트에 없으면 사용자는 pipeline.json을 직접 파야 한다 — 종료 사유가 표에 있어야 다음 행동(--from 재개 / 수동 수정 / 수용)이 한눈에 결정된다.

> 예시: SHIP이 `no_delta`로 끝난 리포트를 본 사용자 → SHIP-REPORT.md의 남은 MISSING 2건을 수동 수정 → `/cs-company --from ship`으로 SHIP만 재실행.
