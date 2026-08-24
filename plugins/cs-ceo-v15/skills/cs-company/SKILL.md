---
name: cs-company
user-invocable: true
description: |
  CS 전 단계 SDLC 파이프라인 conductor. 한 문장 요청을 CLARIFY → PLAN → IMPLEMENT → REVIEW → TEST → SHIP으로 배달한다.
  각 phase는 기존 CS 플러그인 SKILL 그대로이며, conductor는 순서·아티팩트 게이트·pipeline.json 상태·경계 있는 cross-phase 리워크만 소유한다.
  게이트는 cs_artifact frontmatter + artifact_registry verdict 판독 (게이트키퍼 에이전트 없음).
  세션 사망 후 --from <phase>로 재개, --checkpoint에서 인간 확인, --auto로 무인 실행.
  Use when user types "/cs-company" or asks for one-sentence-to-shipped full pipeline development.
version: 1.0.0
allowed-tools:
  - Task
  - Skill
  - Read
  - Write
  - Bash
  - AskUserQuestion
---

# cs-company — 전 단계 SDLC 파이프라인 conductor

**이 SKILL은 main context에서 실행한다** — 체크포인트 AskUserQuestion과 phase 리드들의 CHECKPOINT payload(HITL-POLICY [2])가 여기서 종결된다. conductor를 서브에이전트로 스폰하지 않는다.

파이프라인 프로토콜 (BLOCKING 첫 단계): 첫 phase 실행 전 첫 행동으로 plugins/shared/PIPELINE-PROTOCOL.md와 plugins/shared/LOOP-PROTOCOL.md를 Read하고(리워크 판단 시 plugins/shared/GATE-LOOP.md "파이프라인 리워크" 섹션, 체크포인트 시 plugins/shared/HITL-POLICY.md, 게이트 판독 시 plugins/shared/ARTIFACT-CONTRACTS.md 추가 Read), 런 헤더에 `protocol: PIPELINE-PROTOCOL [1-6] loaded` 한 줄을 출력한다. 이 줄이 없는 리포트는 프로토콜 미적용으로 간주한다. LOOP-PROTOCOL Read 직후 plugins/shared/MEMORY-PROTOCOL.md의 Phase R(회상)을 수행하고, protocol 줄 다음에 `recall: E<n>/C<n>/N<n>` 한 줄을, 그 옆에 `hitl: <auto|gate|always>` 한 줄을 출력한다.

---

## P0: 프로토콜 로드 + 경로 확보

1. 위 BLOCKING Read 수행 → 런 헤더 3줄 출력 (`protocol:` / `recall:` / `hitl:`).
2. 커맨드에서 전달받은 플래그 확정: `HITL`(기본 gate; `--auto`는 auto), `SKIP`(기본 없음), `FROM`(기본 없음), `CHECKPOINT`(기본 `plan,ship`).
3. phase 플러그인 경로는 기존 ceo-preflight 결과를 재사용한다 — 추가 `ls`/`sort -V` 금지:

```bash
PREPASS_RUNNER="$HOME/.claude/plugins/marketplaces/CSnCompany_2-0/plugins/shared/run_prepass.sh"
PREFLIGHT=$(bash "$PREPASS_RUNNER" ceo-preflight 2>/dev/null)
_f() { printf '%s' "$PREFLIGHT" | python3 -c "import sys,json;print(json.load(sys.stdin)$1)" 2>/dev/null; }
P_CLARIFY=$(_f "['plugins']['clarify']");  P_PLAN=$(_f "['plugins']['plan']")
P_SMARTRUN=$(_f "['plugins']['smartrun']"); P_REVIEW=$(_f "['plugins']['review']")
P_TEST=$(_f "['plugins']['test']");        P_SHIP=$(_f "['plugins']['ship']")

REGISTRY="${CLAUDE_PLUGIN_ROOT}/../shared/artifact_registry.py"
if command -v python3 >/dev/null 2>&1; then RUN_PY="python3"; else RUN_PY="uv run --quiet --no-project python"; fi
mkdir -p .cs-artifacts
```

4. **`--from <phase>` 재개 (PIPELINE-PROTOCOL [3])**: `FROM`이 있으면 `.cs-artifacts/pipeline.json`을 Read → `status: passed`인 phase는 재실행하지 않고, 각 passed phase의 artifact를 `find-meta`로 신선도 재확인(stale이면 AskUserQuestion 1회 — ARTIFACT-CONTRACTS [3] 의미론) → `FROM` phase부터 진행한다. pipeline.json이 없으면 "재개할 상태가 없습니다"를 알리고 처음부터 시작할지 1회 확인한다.

## P0.5: Goal Gate + phase-skip 결정

1. **Goal Gate**: 기존 goal 스킬을 실행한다 — `Skill(skill="goal", args="[유저 요청 원문]")` (또는 동일 프로토콜: `${CLAUDE_PLUGIN_ROOT}/skills/goal/SKILL.md` — 같은 플러그인 소속). 반환 `{goal_statement, scope, success_criteria, was_clarified}`를 확보한다. "작업 취소" 선택 시 즉시 종료.
2. **CLARIFY skip 판정 (PIPELINE-PROTOCOL [4])**: `was_clarified=false`이고 goal_statement에 미확정 HIGH 가정이 없으면 CLARIFY를 `skipped`로 기록하고 PLAN으로 직행.
3. **소규모 collapse 예약**: 요청이 CS-plan Step 1.5(항목 5 — 스코프 평가)의 small 기준(단일 모듈/유틸 — 새 레이어·외부 연동·도메인 모델 변경 모두 없음)에 해당할 것으로 보이면 메모해 두고, PLAN 산출물의 `SCOPE`가 실제로 small이면 IMPLEMENT를 collapse한다(P1 하단 "IMPLEMENT collapse" 참조).
4. `.cs-artifacts/pipeline.json` 초기화 (PIPELINE-PROTOCOL [3] 스키마 — goal, started_at, phases 6행 pending, current, reworks: []). `--skip` 지정 phase는 즉시 `skipped` + 사유 기록.

## P1: phase 실행 루프 (CLARIFY → PLAN → IMPLEMENT → REVIEW → TEST → SHIP)

각 phase에 대해 순서대로 (skipped 제외):

**(a) 실행** — pipeline.json의 해당 phase를 `running`으로 갱신하고, phase 플러그인의 기존 SKILL 프로토콜을 그대로 호출한다:

| phase | 호출 | 전달 컨텍스트 |
|-------|------|---------------|
| CLARIFY | `Skill(skill="cs-clarify")` | goal_statement + success_criteria |
| PLAN | `Skill(skill="CS-plan")` | goal_statement (+ CLARIFY.md는 CS-plan이 find-meta로 자체 인테이크) |
| IMPLEMENT | `Skill(skill="smart-run")` | PLAN.md는 smart-run Phase 0.7 PLAN INTAKE가 registry에서 자동 감지 |
| REVIEW | `Skill(skill="CS-codebase-review")` | 변경 범위(PLAN 체크리스트의 대상 경로) |
| TEST | `Skill(skill="CS-test")` | 대상 URL/dev 서버 (미탐지 시 auto-skip — PIPELINE-PROTOCOL [4]) |
| SHIP | `Skill(skill="cs-ship")` | (cs-ship이 PLAN.md/상류 리포트를 자체 인테이크) |

모든 phase 리드 스폰/호출에 `HITL: <mode>`를 전파한다. phase 내부의 팀 구성·프롬프트를 재정의하지 않는다 (PIPELINE-PROTOCOL [1]).

**(b) 게이트 판독 (PIPELINE-PROTOCOL [2])** — phase 완료 직후:

```bash
$RUN_PY "$REGISTRY" find-meta <TYPE>    # TYPE: CLARIFY.md | PLAN.md | IMPLEMENT-REPORT.md | REVIEW.md | TEST-REPORT.md | SHIP-REPORT.md
```

- artifact 파일이 존재하는데 find-meta가 null이면(리드가 register를 생략 — 체인 단절) conductor가 대신 `register <TYPE> <path> <plugin>` 후 재확인한다.
- 파일의 `cs_artifact` frontmatter를 Read → `gate.passed` / `status` / `blocking_items` 확인.
- **GATE PASS** → (c)로. **GATE FAIL** → P2 리워크로.

**(c) 상태 기록 + 체크포인트**:

- pipeline.json 갱신: `status: passed`, artifact 경로, verdict, round, termination.
- 해당 phase가 `CHECKPOINT` 목록에 있으면 (PIPELINE-PROTOCOL [5]): `HITL=auto`면 default(계속 진행)를 조용히 채택하고 기록만 남긴다. 그 외 AskUserQuestion 1회 — [계속 진행(default) / 아티팩트 보기(Read 후 재질문 1회) / 리워크(메모 포함 — 같은 phase를 blocking 스코프 재실행, 게이트당 리워크 예산에 계상) / 작업 취소(pipeline.json 경로 안내 후 종료)].

**CHECKPOINT payload 버블링**: phase 리드가 Task 결과로 `type: "CHECKPOINT"` JSON을 반환하면 HITL-POLICY [3]을 따라 conductor가 여기서 종결한다 — auto면 default 채택, gate/always면 AskUserQuestion(+"작업 취소" 옵션) 후 **같은 리드를 재스폰** (`CHECKPOINT_ANSWER` + `RESUME` 전달). 경계: 같은 checkpoint_id 재스폰 최대 1회, 런당 버블링 총 3회 — 초과 시 종료 사유와 함께 중단 (HITL-POLICY [3] BOUNDED).

**IMPLEMENT collapse (PIPELINE-PROTOCOL [4])**: PLAN이 SCOPE=small 경량 플랜을 산출했으면 smart-run 호출 대신 conductor가 체크리스트를 직접 실행한다. 단 `.cs-artifacts/IMPLEMENT-REPORT.md` Write(+frontmatter) + register 의무는 동일하게 수행한다.

## P2: cross-phase 리워크 (GATE-LOOP "파이프라인 리워크" 섹션 준수)

게이트 FAIL 시:

1. blocking_items의 fault 유형을 GATE-LOOP fault-routing 표에 매칭해 목적지 phase를 정한다 (TEST functional → IMPLEMENT, TEST 요구사항 갭 → PLAN, REVIEW critical → IMPLEMENT(red test 먼저), REVIEW 레이어 위반 → PLAN delta(CS-plan `REWORK:` 입력), SHIP MISSING → IMPLEMENT(cs-ship Phase 2.5 fixer 스펙)). **표에 매칭되지 않고 fault가 phase 자신의 아티팩트에서 온 경우**(CLARIFY/PLAN/IMPLEMENT blocked)는 GATE-LOOP "자기-phase fault" 규칙 — 같은 phase를 blocking_items 스코프로 재시도(게이트당 예산에 계상), 2회 연속 blocked면 STUCK.
2. **예산 확인**: 게이트당 리워크 디스패치 ≤ 2, 런 전체 backward hop ≤ 4. 소진 시 termination `budget`으로 중단하고 P3로.
3. payload(finding + 발췌 + 스코프)만 담아 목적지 phase를 **blocking_items 스코프로만** 재실행한다 — 상류 phase 전체 재실행 금지.
4. **re-gate**: 직전 실패 항목만 재검증 (TEST는 해당 finding을 냈던 워커만 재실행하는 미니 재테스트 — CS-test 노하우 #22).
5. 델타 0이면 **STUCK**: pipeline.json round 이력 + 남은 blocking_items 첨부, AskUserQuestion 1회 — [WARNINGS로 수용하고 계속 / 수동 수정 후 `--from <phase>` 재개 안내 / 작업 취소]. `HITL=auto`면 default(WARNINGS로 수용)를 채택하고 리포트에 명기한다.
6. 모든 hop 이중 기록: `$RUN_PY "$REGISTRY" verdict <TYPE> <verdict> <round> [item ...]` + pipeline.json `reworks` 배열 append.

## P3: 최종 파이프라인 리포트 (PIPELINE-PROTOCOL [6])

정상 종료/중단 모두 다음을 출력한다:

```
## /cs-company 파이프라인 리포트

**목표**: [goal_statement]
protocol: PIPELINE-PROTOCOL [1-6] loaded / hitl: [mode] / recall: E<n>/C<n>/N<n>
기준 대비: [success_criteria 채점 — PASS/FAIL + 근거 한 줄]  (LOOP-PROTOCOL [b])

| phase | artifact | gate | rounds | termination |
|-------|----------|------|--------|-------------|
| ...6행 (skipped 포함, 사유 병기)... |

리워크 이력: [reworks 배열 요약 — 각 hop의 from→to + 사유. 0건이면 "리워크 0회" 한 줄]
상태 파일: .cs-artifacts/pipeline.json  (재개: /cs-company --from <phase>)
```

termination이 `budget`/`no_delta`/`max_rounds`인 행이 있으면 그 아래 다음 행동 제안(수동 수정 대상 + `--from` 명령)을 1-3줄로 붙인다. 리워크 0회 클린 런이면 표 + 헤더만 출력하고 상세 섹션은 생략한다 (LOOP-PROTOCOL [f]).
