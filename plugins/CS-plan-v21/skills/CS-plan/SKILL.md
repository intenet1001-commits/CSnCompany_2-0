---
name: CS-plan
user-invocable: true
description: |
  TDD + Clean Architecture coding plan generator. Use when user types "/CS-plan", "코딩 플랜",
  "플랜 생성", "TDD 플랜", "clean architecture plan", or wants to generate an implementation plan
  using TDD and Clean Architecture. Standard scope uses 4 specialized agents (domain-analyst,
  arch-designer, tdd-strategist, checklist-builder); small scope (single module/util) gets a
  lightweight solo plan from plan-lead.
version: 21.1.0
---

# CS-plan - TDD + Clean Architecture 코딩 플랜 생성

## 개요

`plan-lead` 에이전트가 4개의 전문 Claude AI 에이전트 팀을 조율하여 TDD + Clean Architecture 기반의 즉시 실행 가능한 코딩 플랜을 생성합니다.

main context는 plan-lead 하나만 스폰하고, plan-lead가 팀 오케스트레이션 전체를 담당합니다.
이 방식으로 main context에 4개 에이전트의 raw output이 누적되지 않아 토큰 효율이 높습니다.

## 사용법

```
/CS-plan "기능 설명"
/CS-plan --lang typescript "기능 설명"
/CS-plan --output docs/plans "기능 설명"
/CS-plan --lang python --output src/plans "기능 설명"
/CS-plan --hitl=auto "기능 설명"        # 야간/무인 실행 — arch-choice 체크포인트에서 묻지 않음
```

## 실행 프로토콜

HITL 프로토콜 (BLOCKING): Step 3 스폰 전 plugins/shared/HITL-POLICY.md를 Read하고, 시작 안내에 `hitl: <auto|gate|always>` 한 줄을 포함한다 (런타임 경로: `${CLAUDE_PLUGIN_ROOT}/../shared/HITL-POLICY.md`).

### Step 1: 인자 파싱

입력값에서 다음을 추출합니다:

```
FEATURE  = 큰따옴표 안의 텍스트, 또는 옵션 제외 나머지 텍스트
LANG     = --lang [언어] (미지정 시 "미지정 (plan-lead가 코드베이스에서 추론)")
OUTPUT   = --output [경로] (미지정 시 ".tdd-plans")
HITL     = --hitl [auto|gate|always] (미지정 시 "gate"; --auto는 --hitl=auto 별칭 — plugins/shared/HITL-POLICY.md [1])
REWORK   = 상위 호출자(/cs-company conductor)가 전달한 리워크 payload (미전달 시 NONE) —
           GATE-LOOP "REVIEW — 아키텍처 레이어 위반 → PLAN (delta 재실행)" 라우팅 전용.
           형식: 위반 항목 목록 + 관련 PLAN.md 섹션 발췌. REWORK ≠ NONE이면 Step 1.4/1.5를 스킵한다
           (기존 PLAN.md가 이미 있고 스코프는 위반 항목으로 한정 — 새 인테이크/질문 불필요).
```

기능 설명이 없으면 사용자에게 기능 설명을 요청하고 중단한다 (문구 자유, 사용 예시 1개 포함 — 예: `/CS-plan "사용자 인증 시스템 (이메일+비밀번호, JWT)"`).

### Step 1.4: Upstream intake — CLARIFY.md 자동 소비 (plugins/shared/ARTIFACT-CONTRACTS.md [3])

Step 1.5 전에 업스트림 아티팩트를 확인한다:

```bash
REGISTRY="${CLAUDE_PLUGIN_ROOT}/../shared/artifact_registry.py"
if command -v python3 >/dev/null 2>&1; then RUN_PY="python3"; else RUN_PY="uv run --quiet --no-project python"; fi
CLARIFY_META=$($RUN_PY "$REGISTRY" find-meta CLARIFY.md 2>/dev/null || echo "")
```

1. `CLARIFY_META`가 null/빈 값이면 → 이 단계를 조용히 스킵하고 Step 1.5로 진행 (additive — CLARIFY 없이도 기존 경로 그대로).
2. `freshness: fresh` **이고** frontmatter `status: ready`(또는 `ready_for_plan: true`)면 CLARIFY.md를 Read하고:
   - **Context Anchor 테이블**, **`→ verify:` 성공 기준**, **HIGH 위험 가정**을 원문 그대로 FEATURE 브리프에 병합한다 (요약 금지 — 재해석에서 정보가 샌다).
   - Step 1.5의 AskUserQuestion(모호성 질문)을 **SKIP**한다 — clarify가 이미 물었다. 중복 인터럽션 제거. 단, Step 1.5의 5번(스코프 평가 small/standard)은 그대로 수행한다.
3. `freshness: stale` 또는 `status: blocked`면 AskUserQuestion **1회**: "CLARIFY.md가 N일 전 것입니다(또는 게이트 미통과 상태). 이 요구사항 기준으로 플랜할까요, 무시할까요?" — 무시 선택 시 Step 1.5를 정상 수행.
4. 소비한 CLARIFY.md의 경로를 Step 3의 plan-lead 프롬프트에 `CLARIFY: [경로]`로 전달한다 (미소비 시 `CLARIFY: NONE`).

### Step 1.5: 모호성 프리플라이트 (노하우 #3, #5 반영)

plan-lead는 서브에이전트라 AskUserQuestion을 쓸 수 없으므로, 사용자 질문은 **main context인 이 단계에서만** 수행한다.

1. FEATURE의 모호성을 평가한다: **명확 / 보통 / 모호**
   - 판단 기준: 목표(무엇을), 제약(언어·범위·외부 시스템), 수용 기준(언제 완료인가) 중 하나라도 추측 없이는 채울 수 없으면 "모호"
2. **모호**일 때만 AskUserQuestion으로 **정확히 1회** 명확화/반론 질문을 던진다.
   질문에는 범위 검증용 forcing question 성격을 포함한다 (예: "이 기능의 MVP 버전은 무엇인가요? 더 단순한 대안은 없나요?")
3. 답변을 FEATURE에 반영(병합)한 후 Step 2로 진행한다.
4. **명확/보통**이면 질문 없이 조용히 스킵한다. 질문은 최대 1회 — 추가 라운드 금지.
5. 모호성 평가와 함께 FEATURE의 스코프를 평가한다: **small / standard**
   - SCOPE=small 기준: 단일 모듈/유틸 수준 — 새 레이어 추가, 외부 시스템 연동, 도메인 모델 변경이 **모두 없음**
   - 셋 중 하나라도 해당하거나 판단이 애매하면 SCOPE=standard (보수적 기본값)
   - 평가 결과를 Step 3의 plan-lead 프롬프트에 `SCOPE: [small|standard]`로 전달한다. SCOPE=small이면 plan-lead가 4-agent 팀 대신 단독으로 경량 PLAN.md(테스트 목록 + 구현 체크리스트만)를 작성한다.

### Step 2: 시작 안내 출력

플랜 생성 시작을 알리는 짧은 안내를 출력한다 (형식 자유). 필수 포함: FEATURE, LANG(미지정 시 "자동 감지"), OUTPUT 경로, SCOPE, `hitl: [HITL]`, 실행 방식(standard면 plan-lead가 2-wave 파이프라인으로 4개 전문 에이전트를 조율, small이면 plan-lead 단독 경량 플랜).

### cmux 환경: 진행 상황 표시

```bash
if [ -n "$CMUX_SOCKET_PATH" ]; then
  cmux set-status "cs-plan" "running" --icon "gear"
  cmux set-progress 0.1 --label "CS-plan 시작: plan-lead 스폰 중..."
fi
```

### Step 3: plan-lead 에이전트 스폰

다음과 같이 plan-lead를 단일 Task로 스폰합니다:

```
Task(
  subagent_type: "general-purpose",
  name: "plan-lead",
  model: "sonnet",
  prompt: "당신은 CS-plan의 plan-lead입니다. 아래 컨텍스트로 플랜을 생성하세요.

FEATURE: [FEATURE]  ← Step 1.4에서 CLARIFY가 병합됐으면 병합본
LANG: [LANG]
OUTPUT_DIR: [OUTPUT]
SCOPE: [SCOPE]
CLARIFY: [Step 1.4에서 소비한 CLARIFY.md 경로 또는 NONE]
HITL: [HITL]
REWORK: [리워크 payload 원문 또는 NONE]

plan-lead.md 프로토콜을 따라 PLAN.md를 생성하세요 (SCOPE 분기 + 2-wave 파이프라인 + arch-choice 체크포인트 포함. REWORK ≠ NONE이면 리워크(REWORK) 경로 — arch-designer + checklist-builder만 재스폰)."
)
```

plan-lead가 에이전트 조율, 파일 생성, PLAN.md 합성을 모두 처리합니다.
SCOPE=standard면 2-wave 에이전트 팀(1a: domain-analyst ∥ arch-designer → 1b: tdd-strategist ∥ checklist-builder)을 오케스트레이션하고, SCOPE=small이면 팀 스폰 없이 단독으로 경량 PLAN.md를 작성합니다.

### Step 3.5: 체크포인트 버블링 (plugins/shared/HITL-POLICY.md [3])

plan-lead의 Task 결과가 `type: "CHECKPOINT"` JSON이면 (HITL=gate|always에서 arch-choice 발생):

1. AskUserQuestion 1회: payload의 `question` + `options`(각 label에 consequence 병기) + **"작업 취소" 옵션 필수**.
   - "작업 취소" 선택 → 즉시 종료하되 `resume.artifacts` 경로(지금까지 생성된 domain-analysis.md/architecture.md)를 사용자에게 알린다.
2. plan-lead를 **재스폰**한다 — Step 3의 원래 프롬프트에 두 줄을 추가: `CHECKPOINT_ANSWER: [선택 label]` + `RESUME: [payload의 resume 블록 원문]`. 재스폰된 plan-lead는 Phase 0~1a를 건너뛰고 Phase 1b부터 진행한다.
3. **경계 (BOUNDED)**: 재스폰은 checkpoint_id당 최대 1회, 런당 체크포인트 총 3회 — 재스폰된 plan-lead가 같은 checkpoint_id를 다시 반환하면 재스폰 없이 종료하고 종료 사유(`checkpoint arch-choice re-raised after resume`)와 함께 부분 산출물 경로를 보고한다.

CHECKPOINT가 아닌 정상 완료 결과면 이 단계를 조용히 스킵한다. HITL=auto면 plan-lead가 체크포인트에서 멈추지 않으므로 이 단계는 발동하지 않는다.

plan-lead 완료 후 완료 결과를 사용자에게 전달하고, 마지막 줄에 `다음 단계: /smart-run — PLAN.md 자동 감지됨`을 출력합니다 (smart-run Phase 0.7이 registry에서 PLAN.md를 자동 소비).

```bash
# cmux 환경: 완료 알림
if [ -n "$CMUX_SOCKET_PATH" ]; then
  cmux set-progress 1.0 --label "PLAN.md 생성 완료"
  cmux notify --title "CS-plan 완료" --body "PLAN.md 생성됨 — [FEATURE]"
  cmux set-status "cs-plan" "done" --icon "checkmark"
fi
```

## 에러 처리

- **기능 설명 없음**: 사용자에게 입력 요청 후 중단
- **plan-lead 실패**: 에러 메시지와 함께 수동 실행 방법 안내

## CS-plan v1 노하우

> **학습 반영 규칙**: 교훈이 프로토콜 변경을 지시하면(예: "Step 0 추가"), 같은 커밋에서 해당 agents/*.md 또는 SKILL.md 실행 단계에 반영하고 교훈에 "✅ 반영됨" 표시. 미반영 교훈은 문서일 뿐 실행되지 않는다.

- **토큰 효율**: plan-lead가 하위 에이전트 결과를 자체 context에서 처리 → main context 오염 없음
- **언어 미지정 시**: plan-lead가 코드베이스 컨텍스트에서 자동 추론
- **VERSION 파일**: 새 학습이 추가될 때마다 `/experiencing version-up plan` 으로 버전 증가

### 2. PLAN.md에 디자인 시스템 영향도 섹션 추가 (gstack /plan-design-review 학습, 2026-04-13)

- **상황**: 현재 PLAN.md는 TDD + 아키텍처 중심. UI 컴포넌트가 포함된 기능에서 디자인 영향이 누락됨.
- **발견**: gstack `/plan-design-review`는 각 디자인 차원(타이포그래피, 색상, 공간, 인터랙션, 반응형)을 0-10으로 평가 후 플랜을 수정. 코딩 전에 디자인 문제를 잡는 것이 훨씬 저렴.
- **교훈**: plan-lead가 PLAN.md 생성 시 "## 디자인 시스템 영향도" 섹션 추가. 기능이 UI 컴포넌트를 포함하면 영향받는 디자인 토큰, 컴포넌트 상태, 반응형 분기점 명시.

### 3. 범위 과대 설계 방지를 위한 강제 질문 (gstack /office-hours 학습, 2026-04-13) — ✅ 반영됨 (2026-06, SKILL.md Step 1.5)

- **상황**: plan-lead가 기능 설명을 받으면 즉시 full plan을 생성. 과대 설계 위험 있음.
- **발견**: gstack `/office-hours`는 "이 기능이 정말 필요한가?", "더 단순한 대안은?" 같은 forcing questions를 먼저 던져 범위를 검증함. 이를 통해 불필요한 복잡성을 사전에 제거.
- **교훈**: plan-lead 프로토콜에 Step 0 추가: 기능 설명 수신 직후 1개의 반론 질문 생성 (예: "이 기능의 MVP 버전은 무엇인가요?"). 사용자가 답변 후 플랜 생성 진행.

### 4. 빌드 검증 시 pre-existing 에러와 신규 에러 구분 (2026-04-17)

- **상황**: subagent가 `bun run build` 실행 시 rollup native 모듈 에러 발생
- **발견**: 에러가 이번 변경과 무관한 기존 환경 문제였음. subagent가 `DONE_WITH_CONCERNS`로 보고하여 혼동 없이 진행 가능했음.
- **교훈**: 빌드 검증 실패 시 git diff로 변경 범위 확인 후 pre-existing 에러 여부 판단. subagent는 `DONE_WITH_CONCERNS`로 명확히 구분하여 보고해야 함.

### 5. 플랜 생성 전 Think-Before-Coding 프리플라이트 (Karpathy 학습, 2026-04-20) — ✅ 반영됨 (2026-06, SKILL.md Step 1.5)

- **상황**: 기능 설명이 모호한 채로 플랜을 생성하면 4개 에이전트가 서로 다른 가정 위에서 설계함
- **발견**: Karpathy의 "Think Before Coding" — 구현 전 모호성을 명시적으로 드러내고 정리해야 함. "if 200 lines could be 50, rewrite it" 원칙: 플랜이 과도하게 복잡하면 단순화 질문을 먼저 던져야 함.
- **교훈**: plan-lead Step 1(인자 파싱) 직후, 기능 설명의 모호성 평가(명확/보통/모호). 모호하면 AskUserQuestion으로 명확화 질문 1회. 명확하면 스킵.

### 6. 아키텍처 선택 체크포인트 (bkit checkpoint 패턴 학습, 2026-04-20) — ✅ 반영됨 (2026-06 부분: PLAN.md 요약 노출 → 2026-07 완전 구현: plan-lead 2-wave 파이프라인 + arch-choice CHECKPOINT STOP-and-return + SKILL Step 3.5 버블링, plugins/shared/HITL-POLICY.md)

- **상황**: plan-lead가 아키텍처 옵션 없이 단일 설계만 생성하여 사용자가 방향 조정 기회를 놓침
- **발견**: bkit Checkpoint 3 패턴 — Design 단계에서 Minimal/Clean/Pragmatic 3가지 옵션을 제시하고 사용자가 선택하게 함. 선택 후 해당 방향으로 깊게 들어감.
- **교훈**: arch-designer가 결과 제출 시 "핵심 설계 결정 1가지 + 대안 접근법 1개" 명시. plan-lead가 이를 요약해 사용자 확인 후 checklist-builder로 진행.

### 7. 부가 기능(히스토리/로그) 저장 실패는 메인 작업을 블로킹 금지 (2026-04-21)

- **상황**: push 히스토리 스냅샷 저장 기능을 push 흐름에 삽입. 스냅샷 실패 시 push 자체가 롤백되는 설계 위험.
- **발견**: push_snapshots 테이블 저장을 try-catch로 감싸고 에러를 삼키는 non-blocking 패턴 적용. 히스토리 부재 = 복원 불가이지, 데이터 유실이 아님. 메인 작업(push)은 반드시 완료되어야 함.
- **교훈**: 플랜 설계 시 부가 기능(히스토리, 감사 로그, 통계 기록)은 항상 non-blocking으로 분리. `try { await sideEffect() } catch {}` 패턴을 명시적으로 문서화. 스냅샷 테이블은 `(table_name, device_id)` 복합 키로 도메인+기기 격리, 쓰기 시 MAX_SNAPSHOTS 초과분 즉시 prune-on-write.

### 8. Notion child_page 2-depth API 탐색 패턴 (2026-04-23)

- **상황**: Notion 페이지에서 테이블 데이터를 가져오려 했으나 직접 table 블록이 아닌 child_page 블록 안에 테이블이 있어 1회 API 호출로 데이터를 얻지 못함.
- **발견**: Notion 페이지 구조가 parent → child_page → table 2-depth인 경우, `GET /blocks/{parent_id}/children`로 child_page 블록 ID를 얻고, 다시 `GET /blocks/{child_page_id}/children`으로 table 블록을 얻어야 함. 1회 API 호출로 가정하면 데이터 없음 → 빈 결과.
- **교훈**: Notion 데이터 소스 플랜 수립 시 "페이지 구조 depth 확인" 단계 추가. child_page 블록 타입이 나오면 자동으로 한 단계 더 내려가는 순회 로직 설계.

### 9. 동시 작업 원격 39커밋 — rebase 대신 merge + checkout --theirs 후 additive 재적용 (2026-04-28)

- **상황**: portmanager 통합 모달 + Vercel 숨김을 로컬에 커밋한 사이 원격 main이 39커밋 진행. `git pull --rebase`로 시도하니 4개 파일(App.tsx, PortalManager, SetupWizard, api-server) 충돌, 그 중 App.tsx는 원격이 더 정교한 통합 모달(`projectModalTab`)을 이미 만들어 둔 상태 → 충돌 마커 5개 hunk, 수동 머지 도중 잘못된 마커 결합으로 코드 깨짐 → rebase abort.
- **발견**: 원격이 동일 의도의 더 큰 변경을 했을 때, rebase는 내 변경을 "위에 올리려" 시도해 충돌 폭발. `git merge origin/main` 후 `git checkout --theirs <conflicted files>`로 원격 우선 채택, 그다음 신규 파일(`src/lib/env.ts` 등)과 추가 라인(env import 1줄, Vercel hide 가드 등)만 layered patch로 재적용하면 안전. 핵심: **무엇을 "내 고유 추가분"으로 분리할 수 있는지 사전 식별**.
- **교훈**: PLAN.md에 "Critical Files" 우선순위 매길 때, 큰 파일(예: 4000+줄 App.tsx)은 가급적 **신규 파일 + 작은 import 라인**으로 분리해 변경하면 충돌 자가-회복 가능. 푸시 전 항상 `git fetch origin && git log HEAD..origin/main --oneline | wc -l` 로 차이 확인, 5커밋 이상 차이면 merge 우선 검토.
