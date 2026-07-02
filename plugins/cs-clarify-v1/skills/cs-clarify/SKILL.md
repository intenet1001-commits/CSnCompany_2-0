---
name: cs-clarify
version: 1.0.0
description: |
  Socratic requirements clarification — sequential interview→scope→assumptions→CLARIFY.md.
  Use when user types "/cs-clarify", "요구사항 명료화", "clarify", "플랜 전 정리",
  or wants to clarify requirements before planning/implementation using sequential
  interview-driven analysis (requirements-interviewer → scope-validator → assumption-mapper).
user-invocable: true
---

# cs-clarify — Socratic Requirements Clarification

## 개요

`clarify-lead` 에이전트가 **순차적(sequential)** 3단계 파이프라인을 오케스트레이션합니다.

```
STEP 1: requirements-interviewer   ← AskUserQuestion (최대 3라운드)
        ↓ requirements_summary 전달
STEP 2: scope-validator            ← STEP 1 output 수신 후 실행
        ↓ scope_report 전달
STEP 3: assumption-mapper          ← STEP 1+2 output 수신 후 실행
        ↓
Phase 2: clarify-lead synthesizes → CLARIFY.md
```

> **Architecture Decision**: STEP 2, 3은 STEP 1 완료 후에만 실행됩니다.
> requirements-interviewer가 AskUserQuestion으로 사용자 입력을 수집하기 전에
> scope-validator나 assumption-mapper를 병렬 실행하면 인터뷰 데이터 없이 동작하는 critical bug가 발생합니다.
> 이를 방지하기 위해 strict sequential 실행을 강제합니다.

## 사용법

```
/cs-clarify "기능 설명"
/cs-clarify --quick "기능 설명"
```

| 옵션 | 설명 |
|------|------|
| (없음) | 전체 명료화 — interview 3라운드 + scope + assumptions |
| `--quick` | 빠른 명료화 — interview 스킵, scope + assumptions만 실행 |

## 실행 프로토콜

### Step 1: 인자 파싱

```
FEATURE = 큰따옴표 안의 텍스트, 또는 --quick 제외 나머지 텍스트
QUICK   = --quick 플래그 존재 여부 (true/false)
OUTPUT  = .cs-artifacts (기본값, 없으면 PWD)
```

기능 설명이 없으면 사용자에게 요청 후 중단:
```
❓ 명료화할 기능/요청을 설명해주세요.
예: /cs-clarify "사용자 인증 시스템 구현"
```

### Step 2: 시작 안내 출력

```
🔍 CS-clarify 시작
📋 기능: [FEATURE]
⚡ 모드: [전체 명료화 / --quick 빠른 명료화]
📁 아티팩트: [OUTPUT]/

clarify-lead가 순차적 3단계 파이프라인을 실행합니다...
```

### Step 3: clarify-lead 에이전트 스폰 (단일 Task)

main context는 clarify-lead 하나만 스폰합니다.
clarify-lead가 내부에서 순차적으로 3개 서브에이전트를 오케스트레이션합니다.

```
Task(
  subagent_type: "general-purpose",
  name: "clarify-lead",
  model: "opus",
  prompt: "당신은 CS-clarify의 clarify-lead입니다. 아래 컨텍스트로 요구사항 명료화를 실행하세요.

FEATURE: [FEATURE]
QUICK_MODE: [true/false]
OUTPUT_DIR: [OUTPUT]

[clarify-lead.md 전체 내용 삽입]

CRITICAL: 순차 실행을 강제합니다.
- QUICK_MODE=false: STEP 1 → STEP 2 → STEP 3 순서로 실행. 이전 STEP 완료 확인 후 다음 스폰.
- QUICK_MODE=true: STEP 1 스킵, STEP 2 → STEP 3 순서로 실행.

노하우 섹션의 과거 학습을 인터뷰 질문 우선순위에 반영하세요.
검증 프로토콜 (BLOCKING 첫 단계): fan-out 전 첫 행동으로 plugins/shared/LOOP-PROTOCOL.md를 Read하고, 리포트 헤더에 'protocol: LOOP-PROTOCOL [a-f] loaded (round budget N)' 한 줄을 출력한다. 이 줄이 없는 리포트는 프로토콜 미적용으로 간주한다."
)
```

---

## clarify-lead 오케스트레이션 상세

clarify-lead는 아래 프로토콜을 따릅니다.

### Phase 0: 팀 생성 + 컨텍스트 수집

먼저 팀을 생성합니다:

```
TeamCreate(team_name: "CS-clarify")
```

이어서 컨텍스트를 수집합니다:

```bash
# README, PLAN.md, CLARIFY.md 등 존재 시 읽어 인터뷰 컨텍스트 보강
ls README.md PLAN.md CLARIFY.md 2>/dev/null
```

인터뷰어에게 전달할 `context_brief` 구성:
- 기존 README의 기술 스택 (있는 경우)
- 기존 PLAN.md의 설계 방향 (있는 경우)
- 사용자가 제공한 FEATURE 설명

### Phase 1: 순차적 3단계 실행

#### STEP 1 — requirements-interviewer (QUICK_MODE=false 시만 실행)

```
Task(
  name: "requirements-interviewer",
  prompt: "아래 컨텍스트로 Socratic 인터뷰를 진행하세요.

FEATURE: [FEATURE]
CONTEXT_BRIEF: [context_brief]

[requirements-interviewer.md 전체 내용]

프로토콜:
1. 4개 차원(Goal/Constraints/Success/Context) 0-100 평가
2. 최저 차원에 대해 1개 질문 → AskUserQuestion
3. 답변 반영 → 재평가
4. 모든 차원 ≥70 또는 3라운드 완료 시 종료
5. requirements_summary + 최종 차원별 점수 4개를 clarify-interview.md에 저장
6. SendMessage(recipient: 'clarify-lead', content: requirements_summary)

CRITICAL: AskUserQuestion이 실패하거나 사용 불가하면 답변을 지어내지 말 것.
해당 차원을 UNANSWERED로 표시하고 그대로 clarify-lead에 보고할 것."
)
```

**STEP 1 완료 대기**: clarify-lead는 requirements-interviewer의 SendMessage 수신 후에만 STEP 2를 스폰합니다.

#### STEP 2 — scope-validator (STEP 1 output 수신 후 실행)

```
Task(
  name: "scope-validator",
  prompt: "아래 인터뷰 결과를 바탕으로 범위를 검증하세요.

FEATURE: [FEATURE]
REQUIREMENTS_SUMMARY: [STEP 1 output]

[scope-validator.md 전체 내용]

Karpathy Simplicity First 원칙 적용:
- 과대설계 요소 탐지 (YAGNI 체크)
- MVP 대안 제시 (Phase 1 / Phase 2 분리)
- 단순화 권고사항 목록

scope_report를 clarify-scope.md에 저장.
SendMessage(recipient: 'clarify-lead', content: scope_report)"
)
```

**STEP 2 완료 대기**: scope_report 수신 후에만 STEP 3 스폰.

#### STEP 3 — assumption-mapper (STEP 1+2 output 수신 후 실행)

```
Task(
  name: "assumption-mapper",
  prompt: "아래 인터뷰 + 범위 검증 결과를 바탕으로 숨겨진 가정을 매핑하세요.

FEATURE: [FEATURE]
REQUIREMENTS_SUMMARY: [STEP 1 output]
SCOPE_REPORT: [STEP 2 output]

[assumption-mapper.md 전체 내용]

카테고리별 가정 매핑:
- Tech: 기술 선택 가정
- User: 사용자 행동 가정
- Infra: 인프라 가정
- Timing: 타이밍/의존성 가정

각 가정에 위험도 레이블:
- LOW: 틀려도 작은 수정으로 해결
- MEDIUM: 일부 재설계 필요
- HIGH: 전체 방향 재검토 필요

assumption_report를 clarify-assumptions.md에 저장.
SendMessage(recipient: 'clarify-lead', content: assumption_report)"
)
```

### Phase 2: CLARIFY.md 합성

모든 스폰된 에이전트 완료 후 (QUICK_MODE: 2개) clarify-lead가 합성:

```markdown
# CLARIFY.md — [FEATURE]

> Generated: [ISO timestamp]
> Mode: [전체 / --quick]

## Context Anchor

| 차원 | 내용 |
|------|------|
| WHY  | [핵심 목표] |
| WHO  | [사용자/사용 맥락] |
| RISK | [주요 위험 요소] |
| SUCCESS | [성공 기준 → verify: [측정 가능한 조건]] |
| SCOPE | [MVP Phase 1 / Full Phase 2] |

## 요구사항 요약

[requirements_summary 내용]

## 범위 검증 결과

[scope_report 내용]

### 제외 권장 항목 (YAGNI)
- [항목]: [이유]

## 가정 목록

| # | 가정 | 카테고리 | 위험도 | 틀렸을 때 영향 |
|---|------|----------|--------|----------------|
| 1 | [가정] | Tech/User/Infra/Timing | HIGH/MEDIUM/LOW | [영향] |

### HIGH 위험 가정 — 즉시 확인 필요
- [가정]: [확인 방법]

## 성공 기준

- → verify: [조건 1]
- → verify: [조건 2]
```

```json
{
  "clarify_score": 8,
  "dimensions": {
    "requirements_clarity": 8,
    "scope_defined": 9,
    "assumptions_mapped": 7
  },
  "ready_for_plan": true
}
```

**점수 산정 기준**:
- `requirements_clarity`: 4개 차원(Goal/Constraints/Success/Context) 평균 점수 / 10
- `scope_defined`: MVP 명확도 (MVP 정의됨=10, 과대설계 의심=5, 미정의=1)
- `assumptions_mapped`: HIGH 위험 가정 수 반비례 (0개=10, 1-2개=7, 3+개=4)
- `clarify_score`: 3개 차원 평균
- `ready_for_plan`: `clarify_score >= 7`이면 `true`

### Phase 2.5: Self-audit (점수 산정은 반드시 아티팩트에서)

clarify-lead는 자기 출력에 자기 점수를 매기지 않습니다. 점수 JSON 산출 전에:

1. **Artifact check** (Bash): `wc -c [OUTPUT_DIR]/clarify-interview.md [OUTPUT_DIR]/clarify-scope.md [OUTPUT_DIR]/clarify-assumptions.md`
   — 파일 누락 또는 200바이트 미만이면 `ready_for_plan=false`로 설정하고 실패 파일을 보고 후 중단 (clarify_score 미출력).
   (`--quick` 모드: clarify-interview.md 면제)
2. **점수 재계산** — 기억이 아니라 파일 내용에서 도출:
   - `requirements_clarity`: clarify-interview.md에 기록된 최종 차원별 점수
   - `assumptions_mapped`: `grep -c '| HIGH' [OUTPUT_DIR]/clarify-assumptions.md` — 가정 목록 테이블 행만 카운트 (섹션 헤더 '### HIGH 위험 가정'은 매칭되지 않음) → 0개=10, 1-2개=7, 3+개=4
   - `scope_defined`: clarify-scope.md의 "MVP Phase 1" 섹션 + 구체 항목 1개 이상=10 / 과대설계 플래그+MVP 존재=5 / MVP 섹션 없음=1
3. **Refutation pass**: 미래 CS-plan 작성자 입장에서 질문 3개 작성 → 각각 CLARIFY.md에서 답이 되는 라인 인용.
   인용 불가 질문 존재 → `ready_for_plan=false`, clarify_score 상한 6, 완료 메시지에 "⚠️ 미해결 질문" 목록 출력.

### Phase 3: 품질 게이트 + 완료 메시지

```
✅ CS-clarify 완료
📄 CLARIFY.md 생성됨: [OUTPUT]/CLARIFY.md
📊 커버리지: [성공한 워커 수]/[전체 워커 수] ([%])
📊 Clarify Score: [N]/10
🔁 Clarify Cycles: [cycle_count]
🚀 ready_for_plan: [true/false]

[ready_for_plan=true인 경우]
➡️  다음 단계: /CS-plan "[FEATURE]" 로 진행하세요.
```

커버리지 분모는 QUICK_MODE=false면 3(interviewer+validator+mapper), true면 2(validator+mapper).
Phase 2.5 Artifact check에서 200바이트 미만/누락으로 판정된 워커는 분자에서 제외한다 (LOOP-PROTOCOL [d] COVERAGE HONESTY).

**`ready_for_plan=false`인 경우 — 경계 있는 재명료화 루프** (단순 종료 금지):

`cycle_count < 2`이면 (`--quick`: `cycle_count < 1`):

1. 후속 질문 세트 구성 (최대 3개):
   (a) clarify-assumptions.md의 HIGH 위험 가정, (b) 7 미만 최약 차원에서 도출
2. AskUserQuestion 1라운드 — **"현재 상태로 종료" opt-out 옵션 필수**.
   opt-out 시 `ready_for_plan=false`로 확정, CLARIFY.md의 '미해결 가정' 섹션에 미해결 HIGH 가정 나열 후 종료.
3. 답변 수신 시 전체 파이프라인 재실행 금지 — **델타만 재실행**:
   - requirements_summary 인라인 갱신
   - assumption-mapper만 새 답변으로 재스폰 → 영향받은 가정 재등급 (다운그레이드/해소)
   - 답변이 범위를 바꿨을 때만 scope_report 조정
4. CLARIFY.md 재합성 → Phase 2.5 재채점 → `cycle_count` 증가 → 게이트 재확인
5. 한 라운드가 델타(점수 변화/가정 해소)를 만들지 못하면 즉시 루프 중단

상한 도달 후에도 `clarify_score < 7`이면 `ready_for_plan=false`로 확정:

```
⚠️ 2회 추가 명료화 후에도 미달 (Clarify Score: [N]/10)
미해결 HIGH 가정 (수동 확인 필요):
- [가정]: [확인 방법]
```

사이클 이력은 CLARIFY.md frontmatter에 `clarify_cycles: N`으로 기록 — CS-plan이 요구사항이 얼마나 분쟁적이었는지 볼 수 있습니다.

---

## 아티팩트

| 파일 | 생성자 | 내용 |
|------|--------|------|
| `clarify-interview.md` | requirements-interviewer | 인터뷰 Q&A + 차원별 점수 |
| `clarify-scope.md` | scope-validator | 범위 검증 결과 + MVP 대안 |
| `clarify-assumptions.md` | assumption-mapper | 가정 목록 + 위험도 |
| `CLARIFY.md` | clarify-lead | 최종 합성 문서 + completeness score |

모든 파일은 `[OUTPUT_DIR]/` 에 저장됩니다. (`OUTPUT_DIR` 기본값: `.cs-artifacts`, 없으면 PWD)

---

## 에이전트 팀

| 에이전트 | 모델 | 역할 | 실행 순서 |
|----------|------|------|-----------|
| clarify-lead | opus | 팀 오케스트레이터 + 합성 | 항상 먼저 |
| requirements-interviewer | sonnet | Socratic 인터뷰 (AskUserQuestion) | STEP 1 |
| scope-validator | sonnet | 과대설계 탐지 + MVP 제안 | STEP 2 (STEP 1 후) |
| assumption-mapper | sonnet | 숨겨진 가정 + 위험도 | STEP 3 (STEP 2 후) |

---

## 다음 단계

`ready_for_plan: true` 이면:
```
/CS-plan "[FEATURE]"
```

CLARIFY.md가 PWD에 있으면 CS-plan이 자동으로 컨텍스트로 활용합니다.

---

## cs-clarify 노하우

> 누적 학습 저장소. `/cs-experiencing version-up clarify`로 세션 학습을 캡처해 여기에 추가한다.
> 이 섹션은 스킬 호출 시 자동 로드되므로, 과거 학습이 인터뷰 질문 우선순위의 prior로 작용한다.
> 형식: `### [N]. [제목] ([YYYY-MM-DD])`

(아직 기록된 학습 없음)
