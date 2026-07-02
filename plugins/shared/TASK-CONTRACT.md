# TASK-CONTRACT — fan-out Task 계약 프로토콜

모든 CS 리드(lead)는 워커를 Task()로 스폰할 때 프롬프트 끝에 아래 CONTRACT 블록을 붙이고,
워커 완료 시 [2] 수락 절차(acceptance procedure)로 산출물을 기계적으로 검사한다.
LOOP-PROTOCOL.md의 Read-first BLOCKING 절차에 포함된다 — LOOP-PROTOCOL을 Read한 리드는 fan-out 시 이 파일의 계약을 함께 적용한다. CONTRACT 블록 없는 fan-out은 프로토콜 위반이다.
(런타임 경로는 `${CLAUDE_PLUGIN_ROOT}/../shared/TASK-CONTRACT.md`로 해석한다. 절대 경로 금지.)

## [1] CONTRACT BLOCK — 모든 Task 프롬프트 끝에 붙인다

```
## TASK CONTRACT
task_id: <plugin>:<agent>:<n>
expected_output:
  artifact: <exact path>
  format: json | md
  required_keys: [findings, reviewed_files, passFail]   # md: required_sections
  min_bytes: 200
acceptance_criteria:   # each checkable with one ls/wc/grep
  - "grep -q '\"reviewed_files\"' <artifact>"
context_in: [<upstream artifact paths>]
re_dispatch_budget: 1
```

필드 규칙: `artifact`는 정확한 경로 1개, `required_keys`(json)/`required_sections`(md)는 리드가 합성에 실제로 소비하는 키만, `acceptance_criteria`의 각 항목은 ls/wc/grep **하나**로 검사 가능해야 한다 (내용 해석이 필요한 기준 금지 — 그것은 리드의 합성 단계 몫이다).

**이유**: silent agent death와 형식 붕괴 출력을 오늘은 CS-test의 커버리지 산식만 잡는다 — 나머지 리드는 prose를 그대로 합성에 받아들인다. 계약이 있어야 수락이 결정적(ls/wc/grep)이 된다.

> 예시: ❌ "결과를 design-results/visual-report.json에 저장하세요" (수락 검사 불가)
> → ✅ 프롬프트 끝 CONTRACT 블록: `artifact: design-results/visual-report.json` / `format: json` / `required_keys: [score, issues]` / `min_bytes: 200` / `acceptance_criteria: - "grep -q '\"issues\"' design-results/visual-report.json"`

## [2] ACCEPTANCE — 내용을 읽기 전에 계약부터 검사한다

워커 완료(SendMessage 수신) 시 리드는 산출물을 Read하기 **전에** 다음을 순서대로 실행한다:

1. `ls <artifact>` — 존재 확인
2. `wc -c <artifact>` — `min_bytes` 이상
3. `acceptance_criteria`의 각 assertion 실행 — 전부 통과해야 ACCEPT

**이유**: 워커의 prose 완료 보고를 먼저 읽으면 "다 했다"는 서술에 anchoring되어 빈/깨진 아티팩트를 통과시킨다. 기계 검사가 먼저다.

> 예시: `wc -c design-results/visual-report.json` → `0 design-results/visual-report.json` → 내용을 읽지 않고 즉시 [3] 재디스패치.

## [3] RE-DISPATCH — 실패 시 정확히 1회, 실패한 assertion을 원문 인용

수락 실패 시 **정확히 1회** 재디스패치한다 (`re_dispatch_budget: 1` — LOOP-PROTOCOL [c] BOUNDED LOOP의 하위 예산).
재디스패치 프롬프트에는 실패한 assertion을 **원문 그대로**(명령 + 실제 출력) 인용한다.
2회째 실패 → 해당 에이전트를 **N/A**로 마킹하고 종료 사유 한 줄(`contract failed after 1 re-dispatch: <assertion>`)을 리포트에 남긴다.
계약 실패 N/A는 LOOP-PROTOCOL [d] COVERAGE HONESTY의 등급 상한(1-2개→최대 B, 3-5개→최대 C, 6개+→Incomplete)에 그대로 반영된다.

**이유**: 상한 없는 재시도는 비용 폭주, 0회 재시도는 침묵 통과다. 실패한 assertion 원문이 워커에게 줄 수 있는 가장 정확한 수정 지시다.

> 예시: round 1 수락 실패 → 재디스패치 프롬프트에 `FAIL: grep -q '"reviewed_files"' review.json → exit 1 (키 부재)` 인용 → round 2도 실패 → 에이전트 N/A + 등급 상한 적용 + 종료 사유 기록, 추가 라운드 없음.

## [4] REPORT HEADER — 계약 집계를 헤더에 출력한다

리드 리포트 헤더에 한 줄을 추가한다: `contracts: N issued / M accepted` (재디스패치로 뒤늦게 수락된 것 포함).
M < N이면 어떤 계약이 어떤 assertion에서 실패했는지를 본문 또는 부록에 남긴다.

**이유**: 커버리지 %와 같은 원리 — 계약 수락률이 헤더에 없으면 누락이 침묵하고, 등급이 장식이 된다.

> 예시: `contracts: 5 issued / 4 accepted (visual-hierarchy: min_bytes FAIL ×2 → N/A)`
