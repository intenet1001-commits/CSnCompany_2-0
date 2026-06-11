---
name: cs-ship
version: 1.0.0
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
PLAN_DOC=$(python3 "$REGISTRY" find PLAN.md 2>/dev/null || echo "")
CLARIFY_DOC=$(python3 "$REGISTRY" find CLARIFY.md 2>/dev/null || echo "")
[ -n "$PLAN_DOC" ] && echo "Found PLAN.md: $PLAN_DOC" || echo "No PLAN.md"

# PLAN.md 및 CLARIFY.md 탐색 (현재 디렉토리 + .cs-artifacts/)
for loc in "$PWD" "$PWD/.cs-artifacts"; do
  [ -f "$loc/PLAN.md" ]    && echo "PLAN.md found: $loc/PLAN.md"
  [ -f "$loc/CLARIFY.md" ] && echo "CLARIFY.md found: $loc/CLARIFY.md"
done

echo "Ship target: $SHIP_TARGET (FIX_MODE: $FIX_MODE)"
```

탐색 결과를 ship-lead에게 전달합니다.
PLAN.md가 없으면 ship-lead가 git log 역추론 모드로 전환합니다.

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
# SHIP-REPORT — [날짜]

## 최종 판정: ✅ PASS / ⚠️ WARNINGS / ❌ BLOCKED

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

### Phase 2.5 — Fix Loop (FIX_MODE=true이고 verdict가 BLOCKED/WARNINGS일 때만)

게이트 의미론은 plugins/shared/GATE-LOOP.md를 따릅니다. **최대 2라운드, 경계 있는 루프:**

1. pre-pr-validator의 MISSING 항목 + coverage-auditor의 MISSING 경로마다 sonnet fixer
   에이전트 1개 스폰 (항목 + 관련 PLAN.md 섹션 + 변경 파일 목록 전달).
   금지 커밋 패턴은 ship-lead가 commit-crafter 재실행으로 직접 처리.
2. 수정 후 MISSING이 있었던 도메인의 validator만 재실행 (전체 팀 재실행 금지).
3. 종료 조건: verdict PASS / 2라운드 도달 / 라운드 간 델타 없음(MISSING 집합 동일 → STUCK 표시).
4. 자동 commit/push 금지 — 최종 액션은 사용자 몫.
5. 라운드 이력은 SHIP-REPORT.md `## Fix Rounds`에 기록.

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
- **에이전트 실패**: ship-lead가 실패한 에이전트 영역을 UNKNOWN으로 표시하고 나머지로 판정 진행
- **.cs-artifacts/ 없음**: ship-lead가 자동 생성

## Artifacts

`.cs-artifacts/SHIP-REPORT.md` — 스펙 준수 / 커버리지 갭 / 커밋 메시지 종합 검증 리포트
