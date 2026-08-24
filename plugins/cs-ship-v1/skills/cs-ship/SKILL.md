---
name: cs-ship
version: 1.1.0
description: |
  Pre-PR validation and commit crafting. Use when user types "/cs-ship", "ship",
  "PR 생성 전 검증", "배포 전 체크", or wants to validate implementation against plan,
  audit test coverage, and generate a clean commit message before pushing a PR.
user-invocable: true
---

# cs-ship — Pre-Ship Validation

## 개요

`ship-lead` 에이전트가 3개의 전문 Claude AI 에이전트 팀을 병렬 조율하여 PR 생성 전 최종 게이트를 수행합니다.
스펙 준수 검증, 커버리지 감사, 커밋 메시지 생성이 동시에 실행되어 SHIP-REPORT.md 한 장으로 합성됩니다.

main context는 ship-lead 하나만 스폰하고, ship-lead가 팀 오케스트레이션 전체를 담당합니다.
이 방식으로 3개 에이전트의 raw output이 main context에 누적되지 않아 토큰 효율이 높습니다.

## 사용법

```
/cs-ship
/cs-ship [path]
/cs-ship --fix
```

| 커맨드 | 설명 |
|--------|------|
| `/cs-ship` | 현재 디렉토리 전체 검증 |
| `/cs-ship [path]` | 지정 경로 검증 |
| `/cs-ship --fix` | BLOCKED/WARNINGS 시 MISSING 항목 자동 수정 후 재검증 (최대 2라운드, 커밋은 수동) |

## 실행 프로토콜

### Phase 0 — Context Detection

인자 파싱 및 컨텍스트 수집:

```bash
# 인자 파싱 — --fix는 positional 인자보다 먼저 처리 (SHIP_TARGET으로 소비되지 않도록)
FIX_MODE=false
SHIP_TARGET="$PWD"
for arg in "$@"; do
  [ "$arg" = "--fix" ] && FIX_MODE=true || SHIP_TARGET="$arg"
done

# 변경된 파일 목록 수집
git diff --name-only 2>/dev/null || git diff --name-only HEAD 2>/dev/null
REGISTRY="${CLAUDE_PLUGIN_ROOT}/../shared/artifact_registry.py"
# find-meta: 경로 + age_days + fresh|stale (+ 이전 gate verdict/round) — R7
PLAN_META=$(python3 "$REGISTRY" find-meta PLAN.md 2>/dev/null || echo "")
CLARIFY_DOC=$(python3 "$REGISTRY" find CLARIFY.md 2>/dev/null || echo "")
[ -n "$PLAN_META" ] && [ "$PLAN_META" != "null" ] && echo "PLAN.md meta: $PLAN_META" || echo "No PLAN.md"

# 상류 리포트 인테이크 (ARTIFACT-CONTRACTS [3] — cs-ship은 세 리포트의 주 소비자, additive: 없으면 조용히 생략)
IMPL_META=$(python3 "$REGISTRY" find-meta IMPLEMENT-REPORT.md 2>/dev/null || echo "")
REVIEW_META=$(python3 "$REGISTRY" find-meta REVIEW.md 2>/dev/null || echo "")
TEST_META=$(python3 "$REGISTRY" find-meta TEST-REPORT.md 2>/dev/null || echo "")

# PLAN.md 및 CLARIFY.md 탐색 (현재 디렉토리 + .cs-artifacts/)
for loc in "$PWD" "$PWD/.cs-artifacts"; do
  [ -f "$loc/PLAN.md" ]    && echo "PLAN.md found: $loc/PLAN.md"
  [ -f "$loc/CLARIFY.md" ] && echo "CLARIFY.md found: $loc/CLARIFY.md"
done

echo "Ship target: $SHIP_TARGET (FIX_MODE: $FIX_MODE)"
```

탐색 결과를 ship-lead에게 전달합니다.
PLAN.md가 없으면 ship-lead가 git log 역추론 모드로 전환합니다.

**Staleness 가드 (R7)**: `PLAN_META`의 `freshness`가 `stale`이면(기본 7일,
`CS_ARTIFACT_STALE_DAYS`로 조정) 그대로 소비하지 말고 AskUserQuestion으로
1회 확인한다 — "PLAN.md가 N일 전 것입니다. 이 스펙 기준으로 검증할까요,
git log 역추론 모드로 전환할까요?" 이전 gate 기록(`verdict`/`round`/`blocking_items`)이
있으면 ship-lead에게 전달하여 GATE-LOOP 재검증 시 blocking item만 재확인하게 한다.

**상류 리포트 소비 규칙**: `IMPL_META`/`REVIEW_META`/`TEST_META` 중 `freshness: fresh`인 것만
경로를 ship-lead에게 `UPSTREAM_REPORTS`로 전달한다 (stale/blocked/부재는 전달하지 않고 시작 안내에
사유 1줄 표기 — additive, 단독 실행은 그대로 동작). ship-lead는 전달받은 리포트의 verdict/blocking_items를
pre-pr-validator(스펙 잔여 MISSING 교차 확인)와 coverage-auditor(FAILING/confirmed critical 재확인) 프롬프트에 주입한다.

### Phase 0 완료 후 시작 안내 출력

```
🚀 cs-ship Pre-Ship Validator 시작
📁 대상: [SHIP_TARGET]
📋 PLAN.md: [발견됨 / 없음 → git log 역추론 모드]
🔄 git diff: [변경 파일 수]개 파일

ship-lead 에이전트가 3개 전문 에이전트 팀을 병렬 조율합니다...
```

### Phase 1 — Parallel Validation

ship-lead가 3개 에이전트를 **동시에** 스폰합니다:

```
Task(
  subagent_type: "general-purpose",
  name: "ship-lead",
  model: "opus",
  prompt: "당신은 cs-ship의 ship-lead입니다. 아래 컨텍스트로 PR 전 최종 검증을 수행하세요.

SHIP_TARGET: [SHIP_TARGET]
FIX_MODE: [true/false]
PLAN_PATH: [PLAN.md 경로 또는 NONE]
CHANGED_FILES: [git diff --name-only 결과]
UPSTREAM_REPORTS: [fresh인 IMPLEMENT-REPORT.md / REVIEW.md / TEST-REPORT.md 경로 목록 또는 NONE]

ship-lead.md 프로토콜에 따라 아래 3개 에이전트를 동시에 스폰하세요:

1. pre-pr-validator — PLAN.md vs 실제 구현 3-Way 검증 (PLAN_PATH 전달)
2. coverage-auditor — Critical 경로 테스트 커버리지 감사 (CHANGED_FILES 전달)
3. commit-crafter — git diff 분석 → Conventional Commits 메시지 생성

각 에이전트는 완료 시 SendMessage(recipient: 'ship-lead')로 결과 보고.
모든 에이전트 완료 후 .cs-artifacts/SHIP-REPORT.md를 합성하세요."
)
```

**에이전트별 담당 영역:**

| 에이전트 | 역할 | 출력 | 모델 |
|----------|------|------|------|
| **pre-pr-validator** | PLAN.md ↔ 서버 ↔ 클라이언트 3-Way 체크 | DONE / PARTIAL / MISSING | sonnet |
| **coverage-auditor** | Critical 경로별 테스트 존재 여부 분류 | VERIFIED / PARTIAL / MISSING / FAILING / UNVERIFIED-NO-RUNNER | sonnet |
| **commit-crafter** | diff 분석 → Conventional Commits 초안 생성 | 커밋 메시지 제안 | haiku |

**pre-pr-validator** — PLAN.md가 있으면 계획된 항목과 실제 구현을 3-Way 비교합니다.
PLAN.md가 없으면 git log에서 의도를 역추론하여 구현 완전성을 평가합니다.
결과는 DONE / PARTIAL / MISSING 3단계로 분류하고 준수율(X/Y 항목, XX%)을 계산합니다.

**coverage-auditor** — 변경된 파일에서 Critical 경로(use-case, service, domain)를 식별합니다.
각 경로에 대응하는 테스트 파일을 확인하고, Step 2.5에서 탐지된 테스트 러너로 suite를 **실제 실행**합니다.
VERIFIED는 "테스트 존재 AND 실행 green"을 의미하며, red가 있으면 FAILING(→ BLOCKED),
러너 탐지 불가면 UNVERIFIED-NO-RUNNER로 분류합니다.
동일 갭 3회 탐색 실패 시 Iron Law에 따라 STUCK 리포트를 발행합니다.

**commit-crafter** — `git diff --stat HEAD` 분석 후 Conventional Commits 포맷으로 메시지를 생성합니다.
WIP / fix misc / update / temp / asdf 등 금지 패턴을 자동 탐지하고 플래그합니다.

### Phase 2-0 — Adversarial spot-check (산술 계산 전 필수)

ship-lead는 준수율 계산 전에, pre-pr-validator의 모든 DONE 주장과 coverage-auditor의 모든
VERIFIED 주장에 대해 인용된 증거를 Read/Bash로 직접 확인합니다 (주장이 틀린 이유를 찾는 관점:
파일 없음, 인용 심볼 부재, 테스트 빈 파일/skip). 전체 항목 ≤ 15개면 전수 검사,
그 이상이면 90%/80% 임계값 ±2 항목 전수 + 30% 무작위 샘플.
증거 불일치 항목은 PARTIAL로 강등 + 집계 제외 + `## Refuted claims` 기록.
**2개 이상 반박 시 verdict 상한 WARNINGS.**

### Phase 2 — Synthesis

ship-lead가 3개 에이전트 결과를 수신하면 `.cs-artifacts/SHIP-REPORT.md`를 생성합니다:

```markdown
---
cs_artifact:
  type: SHIP-REPORT.md
  producer: cs-ship
  produced_at: [ISO timestamp]
  status: [ready | blocked]      # 판정 PASS → ready, WARNINGS/BLOCKED → blocked
  gate:
    passed: [판정 == PASS]
    criterion: "스펙 준수 ≥90% AND 실행 suite 전체 green AND Refuted <2"
    blocking_items: [MISSING/FAILING 항목 각 1줄]
---
# SHIP-REPORT — [날짜]

## 최종 판정: ✅ PASS / ⚠️ WARNINGS / ❌ BLOCKED

에이전트 커버리지: X/3 (LOOP-PROTOCOL [d] COVERAGE HONESTY)

| 검증 영역 | 결과 |
|-----------|------|
| 스펙 준수 | X/Y 항목 DONE (XX%) |
| 커버리지  | VERIFIED Z개 / PARTIAL A개 / MISSING B개 / FAILING W개 |
| 커밋 품질 | 금지 패턴 탐지: 없음 ✅ / [패턴명] ⚠️ |

## 테스트 실행 결과

[러너 출력 요약 라인 원문 인용 (예: "Tests: 2 failed, 41 passed") 또는 "runner not detected"]

## 스펙 준수 검증 결과

[pre-pr-validator 출력 — DONE/PARTIAL/MISSING 테이블 (증거 컬럼 포함)]

## Refuted claims

[Phase 2-0에서 반박된 DONE/VERIFIED 주장 + 확인한 증거 — 없으면 "없음"]

## 커버리지 갭 (MISSING만 표시)

[coverage-auditor 출력 — MISSING 항목만]

## Fix Rounds (--fix 모드일 때만)

[라운드별 before/after MISSING 수 + 재실행된 validator]

## 제안 커밋 메시지

[Conventional Commits 포맷 커밋 메시지]

## 다음 단계

[PASS]     → git commit -m "[제안 메시지]" 후 PR 생성
[BLOCKED]  → 미구현 항목 수정 후 /cs-ship 재실행 (또는 /cs-ship --fix)
[WARNINGS] → 확인 후 진행 여부 결정
```

**판정 기준:**

| 항목 | 기준 | 판정 |
|------|------|------|
| 스펙 준수율 | DONE ≥ 90% | ❌ BLOCKED if < 90% |
| Critical 커버리지 | VERIFIED ≥ 80% | ⚠️ WARNINGS if PARTIAL |
| 테스트 실행 | 실행된 suite 전체 green | ❌ BLOCKED if any FAILING (다른 점수 무관); ⚠️ WARNINGS if UNVERIFIED-NO-RUNNER |
| 커밋 메시지 | 금지 패턴 없음 | ⚠️ WARNINGS + 자동 수정 제안 |
| Refuted claims | Phase 2-0 반박 2개 미만 | ⚠️ 2개 이상 반박 시 verdict 상한 WARNINGS |
| 에이전트 커버리지 (LOOP-PROTOCOL [d]) | 3개 중 3개 응답 | 1개 UNKNOWN → verdict 상한 WARNINGS; 2개 이상 UNKNOWN → verdict 상한 BLOCKED |

**RECORD (GATE-LOOP.md 필수 단계)**: 판정이 확정되면 세션이 끊겨도 다음 게이트가 복원할 수 있도록
즉시 기록한다:

```bash
python3 "$REGISTRY" verdict SHIP <PASS|FAIL|WARNINGS|BLOCKED> <round> [blocking_item ...]
```

Phase 2.5로 진입하지 않는 라운드(즉시 PASS/BLOCKED 확정)도 round=1로 기록한다.

**register + verdict 기록 (plugins/shared/ARTIFACT-CONTRACTS.md [2] + GATE-LOOP RECORD)** — SHIP-REPORT.md 생성 직후 ship-lead가 실행 (마지막 프로토콜 단계):

```bash
REGISTRY="${CLAUDE_PLUGIN_ROOT}/../shared/artifact_registry.py"
if command -v python3 >/dev/null 2>&1; then RUN_PY="python3"; else RUN_PY="uv run --quiet --no-project python"; fi
$RUN_PY "$REGISTRY" register SHIP-REPORT.md .cs-artifacts/SHIP-REPORT.md cs-ship
$RUN_PY "$REGISTRY" verdict SHIP-REPORT.md <PASS|WARNINGS|BLOCKED> <round> [MISSING/FAILING 항목 ...]
```

- round는 GATE-LOOP의 gate→fix→re-gate 라운드 번호 — Phase 2.5 Fix Loop 각 라운드 재판정 후 frontmatter/verdict를 갱신한다 (재실행 시 `find-meta SHIP-REPORT.md`로 이전 round/blocking_items 복원, blocking item만 재확인).
- 등록 실패는 non-blocking (경고 1줄) — 판정 자체를 차단하지 않는다. 이 verdict가 /cs-company SHIP 게이트("registry verdict PASS")의 판독 소스다.

### Phase 2.5 — Fix Loop (FIX_MODE=true이고 verdict가 BLOCKED/WARNINGS일 때만)

게이트 의미론은 plugins/shared/GATE-LOOP.md를 따릅니다. **최대 2라운드, 경계 있는 루프:**

1. pre-pr-validator의 MISSING 항목 + coverage-auditor의 MISSING 경로마다 sonnet fixer
   에이전트 1개 스폰 (항목 + 관련 PLAN.md 섹션 + 변경 파일 목록 전달).
   금지 커밋 패턴은 ship-lead가 commit-crafter 재실행으로 직접 처리.
2. 수정 후 MISSING이 있었던 도메인의 validator만 재실행 (전체 팀 재실행 금지).
3. 종료 조건: verdict PASS / 2라운드 도달 / 라운드 간 델타 없음(MISSING 집합 동일 → STUCK 표시).
4. 자동 commit/push 금지 — 최종 액션은 사용자 몫.
5. 라운드 이력은 SHIP-REPORT.md `## Fix Rounds`에 기록.
6. 각 라운드 종료마다 RECORD를 재실행한다: `python3 "$REGISTRY" verdict SHIP <verdict> <round> [blocking_item ...]`
   — round 번호를 갱신해 다음 게이트가 find-meta로 최신 라운드 상태를 복원할 수 있게 한다.

### Phase 2 완료 후 결과 출력

```
[판정]: ✅ PASS / ⚠️ WARNINGS / ❌ BLOCKED
📄 .cs-artifacts/SHIP-REPORT.md 생성됨

[PASS]     → git commit -m "[제안 커밋 메시지]"
[BLOCKED]  → 미구현 항목 수정 후 /cs-ship 재실행 (또는 /cs-ship --fix: 최대 2라운드 자동 수정)
[WARNINGS] → SHIP-REPORT.md 확인 후 진행 여부 결정
```

## 에러 처리

- **git repo 없음**: `git diff` 실패 시 ship-lead가 파일 시스템 직접 스캔으로 전환
- **PLAN.md 없음**: pre-pr-validator가 git log 역추론 모드 활성화 (결과 신뢰도 명시)
- **에이전트 실패**: ship-lead가 실패한 에이전트 영역을 UNKNOWN으로 표시하고 나머지로 판정 진행하되,
  LOOP-PROTOCOL [d] COVERAGE HONESTY에 따라 verdict 상한을 건다 (UNKNOWN 1개 → WARNINGS, 2개 이상 → BLOCKED).
  SHIP-REPORT.md 헤더의 "에이전트 커버리지: X/3"에 반영한다.
- **.cs-artifacts/ 없음**: ship-lead가 자동 생성

## Artifacts

`.cs-artifacts/SHIP-REPORT.md` — 스펙 준수 / 커버리지 갭 / 커밋 메시지 종합 검증 리포트
