---
name: cs-smart-run
user-invocable: true
description: |
  Orchestrator: Spec check → Plan with Opus → Plan review → Execute with Sonnet → Verify.
  Opus analyzes the task and produces a structured plan; Sonnet agents
  execute each step in parallel where possible; an independent verifier
  checks the Definition of Done with tool evidence.
  Use when asked to "smart run", "/cs-smart-run", "플랜실행", or when the user
  wants Opus-quality planning with Sonnet-speed execution across multiple skills.
version: 1.2.0

allowed-tools:
  - Agent
  - Read
  - Write
  - Edit
  - Bash
  - Glob
  - Grep
  - AskUserQuestion
---

# Smart Run — Plan with Opus, Execute with Sonnet

검증 프로토콜 (BLOCKING 첫 단계): fan-out 전 첫 행동으로 plugins/shared/LOOP-PROTOCOL.md를 Read하고, 리포트 헤더에 `protocol: LOOP-PROTOCOL [a-f] loaded (round budget N)` 한 줄을 출력한다. 이 줄이 없는 리포트는 프로토콜 미적용으로 간주한다. verifier 디스패치는 plugins/shared/agents/verifier.md를 따른다. 아티팩트 소비/생산(PLAN.md 인테이크, IMPLEMENT-REPORT.md 등록)은 plugins/shared/ARTIFACT-CONTRACTS.md를 추가로 Read하고 따른다. 체크포인트 처리(plan-approval, --hitl 모드)는 plugins/shared/HITL-POLICY.md를 추가로 Read하고 따르며, protocol 줄 옆에 `hitl: <auto|gate|always>` 한 줄을 출력한다.

오케스트레이션 확장 (v1.1): VERIFY→fix 루프(Phase 2.5)는 plugins/shared/ORCHESTRATION-PATTERNS.md의 P4(instructor-assistant 역할극) + P2(조합 가능한 종료 조건)로 정식화한다 — verifier=instructor(지시), executor=assistant(수정), 종료식 `max_turns(2) OR sentinel OR no_delta`.

## How this skill works

When invoked, you orchestrate these phases:

0. **SPEC CHECK** — confirm goal/constraints/acceptance criteria before any agent spawn
0.7. **PLAN INTAKE** — consume a fresh, accepted CS-plan PLAN.md if one exists; skip Opus planning entirely in that case
1. **PLAN phase** — spawn a single Opus agent to think deeply and produce a structured plan
1.5. **PLAN REVIEW** — one Sonnet critic refutes the plan; Opus revises once if defects found
2. **EXEC phase** — spawn one or more Sonnet agents to implement the plan
2.5. **VERIFY** — an independent agent checks the Definition of Done with tool evidence (max 2 verify→fix rounds)
3. **REPORT** — summarize + persist `.cs-artifacts/IMPLEMENT-REPORT.md`

---

## cmux 환경 지원

cmux 터미널(`$CMUX_SOCKET_PATH` 설정됨)에서 실행 시 진행 상황을 사이드바에 표시한다:

```bash
# Phase 시작 시 호출
[ -n "$CMUX_SOCKET_PATH" ] && cmux set-status "smart-run" "running" --icon "gear"
[ -n "$CMUX_SOCKET_PATH" ] && cmux set-progress 0.0 --label "Smart Run 시작..."
```

각 Phase 전환 시:
- Phase 1 시작: `cmux set-progress 0.2 --label "PLAN: Opus 분석 중..."`
- Phase 1.5 시작: `cmux set-progress 0.35 --label "REVIEW: 플랜 검증 중..."`
- Phase 2 시작: `cmux set-progress 0.5 --label "EXEC: Sonnet 실행 중..."`
- Phase 2.5 시작: `cmux set-progress 0.8 --label "VERIFY: DoD 검증 중..."`
- Phase 3 완료: `cmux set-progress 1.0 --label "완료"` + `cmux notify --title "Smart Run 완료" --body "[태스크 요약]"`

---

## Phase 0: SPEC CHECK (orchestrator, no agent spawn)

Before spawning the Opus planner, check the task for the three essentials:
- **Goal** — what outcome is wanted?
- **Constraints** — scope boundaries, tech choices, things NOT to touch
- **Acceptance criteria** — how the user will judge it done

If any of these is missing or ambiguous, use **AskUserQuestion** (one round,
max 3 questions, each with concrete options) to resolve them. Skip this
entirely when the task is already specific — do not interrogate clear requests.
For large or contested requirements, suggest running `/cs-clarify` first instead.

Pass the **resolved spec** (task + answers, restated in 2-4 lines) to Phase 1,
not the raw task string.

---

## Phase 0.7: PLAN INTAKE (orchestrator — plugins/shared/ARTIFACT-CONTRACTS.md [3])

Opus 플래너를 스폰하기 전에 CS-plan이 만든 PLAN.md가 있는지 확인한다:

```bash
REGISTRY="${CLAUDE_PLUGIN_ROOT}/../shared/artifact_registry.py"
if command -v python3 >/dev/null 2>&1; then RUN_PY="python3"; else RUN_PY="uv run --quiet --no-project python"; fi
PLAN_META=$($RUN_PY "$REGISTRY" find-meta PLAN.md 2>/dev/null || echo "")
# registry 미등록 구버전 폴백: Glob .tdd-plans/PLAN.md
```

**분기 (경계: 사용자 확인 최대 1회):**

- **PLAN.md 없음** (find-meta null + Glob 미발견) → 이 Phase를 조용히 스킵하고 Phase 1로 진행 (기존 경로 그대로 — purely additive).
- **`freshness: stale`** (기본 7일) 또는 frontmatter **`status: blocked`** → AskUserQuestion **1회**: "PLAN.md가 N일 전 것입니다(또는 게이트 미통과). 이 플랜으로 실행할까요, 새로 플랜할까요?" — 거절 시 Phase 1로 폴스루.
- **`freshness: fresh` 이고 accepted** (`status: ready`, 사용자가 위 질문에서 수락했거나 질문 불필요) → **Phase 1(Opus 플래너)과 Phase 1.5(critic)를 SKIP**한다. 플랜은 CS-plan Phase 2a 정합성 게이트를 이미 통과했다 — 이중 비평은 비용만 든다.

**체크리스트 → 실행 스텝 결정적 변환 (SKIP 경로일 때):**

PLAN.md와 같은 디렉토리의 `implementation-checklist.md`(경량 플랜이면 PLAN.md 내 구현 체크리스트 섹션)와 `tdd-strategy.md`를 Read하고, LLM 재플래닝 없이 결정적으로 변환한다:

1. Inside-Out 섹션 순서(VO → Entities → Repo fake → Services → Use Cases → Repo impl → Controllers → Infra)가 **순차 스텝 그룹**이 된다 — 그룹 간 순서 고정.
2. 한 섹션 안에서 서로 다른 파일을 만드는 독립 항목은 `[PARALLEL]`로 표시 (같은 파일을 건드리면 순차).
3. 각 실행 에이전트 프롬프트에 반드시 포함:
   - (a) 체크리스트 항목 원문 (🔴 RED / 🟢 GREEN / 🔵 RFCT 체크박스 포함)
   - (b) tdd-strategy.md에서 해당 단위에 매칭되는 Given/When/Then 케이스 — 이것이 그 스텝의 **Definition of Done**
   - (c) 체크리스트의 'Critical Files / 충돌 위험' 섹션 — **do-not-touch 가드레일** (여기 명시된 완화 전략 외 방식으로 해당 파일 수정 금지)
4. 실행 에이전트는 🔴 test-first 순서를 지키고(테스트 먼저 작성·실패 확인 후 구현), 완료한 항목의 체크박스를 `[ ]`→`[x]`로 직접 갱신한다 — 체크리스트 파일이 **세션 간 재개 상태**다 (재실행 시 `[x]` 항목 스킵).
5. Phase 2.5 verifier는 각 스텝의 DoD(Given/When/Then)를 해당 테스트 **재실행**으로 반증한다 — 실행자의 self-report는 증거가 아니다.

변환 결과(스텝 그룹 + PARALLEL 표시)를 Phase 2의 플랜으로 사용하고, PLAN.md의 Definition of Done을 성공 기준 요약에 사용한다.

**이유**: CS-plan의 산출물이 실행으로 이어지지 않으면 플래닝 rigor가 통째로 버려진다 — 그리고 이미 정합성-게이트된 플랜을 Opus로 다시 플래닝하는 것은 정보를 잃는 재해석이다.

---

## Phase 1: PLAN (Opus)

Spawn ONE agent with `model: "opus"` to analyze the task and return a structured plan.

Prompt the Opus agent with:
```
You are a senior architect. The user wants: <resolved spec from Phase 0>

Relevant prior learnings from past runs: <paste any entries from the 노하우 section that match this task's domain>

Produce a PLAN with these sections:
## Goal
One-sentence summary.

## Steps
Numbered list. Each step must specify:
- What to do
- Which skill or tool to use (if applicable)
- Input/output dependencies with other steps
- Whether it can run in PARALLEL with other steps (mark with [PARALLEL])

## Risks
Key risks or blockers to watch for.

## Definition of Done
How to verify the work is complete. Each item must be objectively checkable
(a command to run, a file to inspect) — not a vague statement.

If the spec is still too underspecified to plan safely, do NOT guess:
return only a section titled "## BLOCKING QUESTIONS" listing what must be
answered. The orchestrator will ask the user and re-run you with the answers.

Be thorough but concise. This plan will be handed directly to execution agents.
```

Wait for the Opus agent to return the plan before proceeding.

If Phase 1 returned **BLOCKING QUESTIONS**, resolve them via AskUserQuestion
and re-run Phase 1 with the answers before any Sonnet agent is spawned.

If the Opus agent returns no output, or a plan missing any of ## Goal /
## Steps / ## Definition of Done, retry once with an explicit format
reminder ("Your last response did not include a valid ## Goal/## Steps/##
Definition of Done structure — return the plan in exactly that format").
On a second empty or malformed result, stop and report a STUCK finding to
the user per LOOP-PROTOCOL [c] instead of proceeding to Phase 1.5 with a
broken plan.

---

## Phase 1.5: PLAN REVIEW (Sonnet critic)

Skip this phase if the plan has 2 or fewer steps and no [PARALLEL] markers.

Spawn ONE agent with `model: "sonnet"` prompted to refute the plan:

```
You are an adversarial plan reviewer. Your job is to find concrete defects, not to praise.
Review this plan and report ONLY defects in these categories:
1. PARALLEL conflicts: steps marked [PARALLEL] that read/write the same files, or where one step's input depends on another [PARALLEL] step's output.
2. Missing dependencies: sequential steps whose required inputs are not produced by any earlier step.
3. Undefined outputs: steps that do not state what they produce for later steps.
4. Untestable DoD: Definition of Done items that cannot be objectively verified.
Return either "NO DEFECTS" or a numbered defect list, each with the step number and a one-line fix.

PLAN:
<plan from Phase 1>
```

If the critic returns defects, send them back to the Opus planner for exactly
ONE revision pass ("Revise the plan to address these defects; change only what
is needed"). Do not loop further — proceed to Phase 2 with the revised plan.
Include the critic's verdict in the Phase 3 report.

If the critic agent returns no output, or a response that is neither
"NO DEFECTS" nor a numbered defect list, retry once with an explicit format
reminder. On a second empty/malformed result, skip Phase 1.5 (proceed with
the Phase 1 plan unreviewed) and report a STUCK finding to the user per
LOOP-PROTOCOL [c] rather than blocking the run indefinitely.

---

## Phase 2: EXEC (Sonnet)

fan-out 직전에 플랜의 Definition of Done을 한 줄 성공 기준으로 요약 출력한다
(LOOP-PROTOCOL [b] SUCCESS CRITERIA FIRST).

Read the plan from Phase 1. For each step:

- **Independent steps** (marked `[PARALLEL]`): spawn Sonnet agents **simultaneously** in a single message
- **Sequential steps**: spawn Sonnet agents one at a time, passing the previous result as context

Spawn each execution agent with `model: "sonnet"`.

Prompt each Sonnet execution agent with (per plugins/shared/agents/AGENT-PERSONA-CONTRACT.md
§2 Task contract — `expected_output` is required, `context` carries prior output verbatim):
```
You are an expert implementer. Execute this specific step from a larger plan:

## Your Step
<step description>

## Full Plan Context
<full plan from Opus>

## Expected Output
완료 형태: <1-line spec of what this step must return, derived from the step's
stated input/output dependencies in the plan — e.g. "modified file X with Y
passing" or "JSON summary of Z">

## Prior Step Results (if any)
<verbatim "files changed / commands run + exit status / output next step needs"
block returned by the upstream agent(s) this step depends on — never a
paraphrased or vague prose summary>

Execute completely. Return: what you did, files changed (exact paths), commands you ran with their exit status, and any output the next step needs.
```

---

## Phase 2.5: VERIFY (independent agent)

After all execution agents complete, spawn ONE independent `model: "sonnet"`
agent that did NOT execute any step. Skip this phase only if the plan was
read-only (no files changed, no commands with side effects).

이 디스패치는 line 25의 검증 프로토콜 마당대로 plugins/shared/agents/verifier.md를
그대로 재사용한다 — 첫 행동으로 verifier.md를 Read시키고, 그 OWNS/DOES NOT OWN
경계(finding 재검증만 수행, 새 finding 발굴·수정은 하지 않음)와 JSON 출력 계약을
그대로 프롬프트에 주입한다. 각 Definition of Done 항목을 finding으로 취급한다.

Prompt the verifier with:
```
첫 행동: Read plugins/shared/agents/verifier.md — 아래 임무는 그 파일의 계약을 따른다.

📌 OWNS: 이 태스크의 finding = 아래 Definition of Done 각 항목. 재검증(반증 시도) +
CONFIRMED/REFUTED/UNCERTAIN 판정 + counter-evidence 수집만 한다.
❌ DOES NOT OWN: 새로운 결함/DoD 항목 발굴, 코드 수정, 최종 grade 계산.

You are an adversarial verifier. Do not trust the executors' self-reports —
확인이 아니라 반박이 기본 자세다.

## Definition of Done (from the plan) — 각 항목이 하나의 finding이다
<DoD section from the Opus plan>

## Claimed results per step
<each step's self-report>

For EVERY Definition of Done item, gather tool evidence yourself — re-run the
relevant tests/builds/lints, read the changed files, run `git diff`/`git status`
to confirm claimed changes actually exist. 증거가 약하면 기본 판정은 REFUTED.

Return ONLY a JSON array, one object per DoD item, per verifier.md's output contract:
[
  {
    "id": "<DoD item 식별자>",
    "verdict": "CONFIRMED | REFUTED | UNCERTAIN",
    "counter_evidence": "file:line 인용 또는 command+output 스니펫. CONFIRMED면 재확인한 증거, REFUTED면 모순 증거, UNCERTAIN이면 체크 불가 사유."
  }
]
```
CONFIRMED는 PASS로, REFUTED는 FAIL로, UNCERTAIN은 FAIL로 취급해 아래 verify→fix
루프에 넘긴다.

**verify→fix 루프 (BOUNDED, 최대 2라운드) — P4 instructor-assistant + P2 종료식**:

이 루프를 ORCHESTRATION-PATTERNS.md P4 역할극으로 구성한다:
- **instructor = verifier**: FAIL 항목마다 "무엇이 왜 틀렸는지 + 어떤 증거로 확인했는지"를 한 번에
  하나씩 지시한다 (ChatDev "one highest-priority comment" — 가장 중요한 것부터).
- **assistant = executor**: 지시받은 항목만 수정한다. 스스로 새 작업을 벌이지 않는다.
- **종료식 (P2)**: 루프 진입 전 선언 → `max_turns(2) OR sentinel(모든 DoD PASS) OR no_delta`.
  매 라운드 후 평가하고, 종료 시 어떤 조건이 발화했는지 리포트에 기록 (`종료: no_delta @ round 2`).

1. If any item FAILs: re-dispatch ONLY the failed steps with added context —
   the original step description, the failed attempt's output, the verifier's
   specific findings (what was wrong/missing), and outputs of upstream steps.
2. Re-run downstream sequential steps whose input came from a failed step
   (their prior context is now stale). Then re-verify the FAILed items.
3. On a step's 2nd retry, escalate it to `model: "opus"`.
4. Limit to a maximum of 2 verify→fix rounds. If a round produces no delta
   (no new PASS), stop early. After the budget is exhausted, report remaining
   FAILs to the user as incomplete rather than looping.

---

## Phase 3: REPORT

After verification completes, summarize:
- What was planned (Opus — or "PLAN INTAKE: [PLAN.md 경로]" when Phase 0.7 skipped planning), including the Phase 1.5 critic's verdict when it ran
- What was executed (Sonnet agents)
- Verification results: each Definition of Done item with PASS/FAIL and evidence
- Any steps that failed or need follow-up (unresolved FAILs go here)

**IMPLEMENT-REPORT.md 영속화 (plugins/shared/ARTIFACT-CONTRACTS.md [2])** — 실행이 파일을 변경했으면
(Phase 0.7 PLAN INTAKE 모드에서는 필수) `.cs-artifacts/IMPLEMENT-REPORT.md`를 Write하고 등록한다:

- `cs_artifact` frontmatter (`type: IMPLEMENT-REPORT.md`, `producer: cs-smart-run`,
  `status`: 미완료(UNDONE/FAIL) 항목 0건이면 `ready` 아니면 `blocked`,
  `gate`: `{passed, criterion: "Definition of Done 전 항목 PASS", blocking_items: [남은 FAIL/UNDONE 항목]}`)
- 스텝 진행률: done/total (PLAN INTAKE 모드면 체크리스트 `[x]`/전체 기준)
- 테스트 러너 요약 라인 **원문 인용** (coverage-auditor 컨벤션 — 예: `Tests: 2 failed, 41 passed`; 러너 없으면 "runner not detected")
- 변경된 파일 목록 (정확한 경로)
- UNDONE 항목 + 사유 (verify→fix 예산 소진분 포함, 종료 사유 명시 — 예: "2라운드 후 델타 없음으로 중단")

```bash
REGISTRY="${CLAUDE_PLUGIN_ROOT}/../shared/artifact_registry.py"
if command -v python3 >/dev/null 2>&1; then RUN_PY="python3"; else RUN_PY="uv run --quiet --no-project python"; fi
$RUN_PY "$REGISTRY" register IMPLEMENT-REPORT.md .cs-artifacts/IMPLEMENT-REPORT.md cs-smart-run
```

If any step failed, was re-planned, or a correction worked, draft a candidate
learning entry (task, plan shape, failed step, correction) and end the report with:
"💡 학습 저장: `/cs-experiencing version-up smart-run` 으로 이번 패턴을 노하우에 추가하세요."

---

## Invocation

When the user runs `/cs-smart-run <task>` or `/플랜실행 <task>`:

0. Parse `--hitl [auto|gate|always]` from the invocation (default `gate`; `--auto` is an alias for `--hitl=auto` — plugins/shared/HITL-POLICY.md [1]). Print `hitl: <mode>` next to the protocol line.
1. Confirm you understood the task (one line)
2. Run Phase 0 (SPEC CHECK); ask clarifying questions only if goal/constraints/acceptance criteria are missing
2.5. Run Phase 0.7 (PLAN INTAKE) — fresh + accepted PLAN.md 발견 시 "**[PLAN INTAKE]** CS-plan PLAN.md 감지 — Opus 플래닝 스킵" 안내 후 steps 3-5를 건너뛰고 step 6으로
3. Announce: "**[PLAN]** Thinking with Opus..."
4. Run Phase 1 (Opus agent); if it returned BLOCKING QUESTIONS, resolve via AskUserQuestion and re-run Phase 1
5. Announce: "**[REVIEW]** Critiquing plan..." then run Phase 1.5 (Sonnet critic, one Opus revision pass max)
6. **`plan-approval` checkpoint (plugins/shared/HITL-POLICY.md [4])** — show the plan (the revised plan when the critic ran; PLAN INTAKE 경로에서는 변환된 스텝 그룹 요약) to the user, then:
   - `hitl=gate|always` → AskUserQuestion once: approve (플랜대로 실행 — default) / revise (사용자 수정 지시 1회 반영 후 재확인 없이 진행) / 작업 취소. **Effort level(L2+)과 무관하게 묻는다** — 이전의 "L2+ 자동 진행"은 gate 모드에서 더 이상 적용되지 않는다.
   - `hitl=auto` → default(approve)를 조용히 채택하고 진행 — 기존 L2+ 무정지 동작은 이 플래그로 복원된다. 리포트에 `plan-approval: auto default(approve)` 기록.
   - 서브에이전트로 실행 중이라 AskUserQuestion이 불가하면 → HITL-POLICY [2] 스키마의 CHECKPOINT payload(`checkpoint_id: "plan-approval"`, `default_option: "approve"`, `resume: {artifacts: [플랜 텍스트를 저장한 파일 경로], next_phase: "Phase 2", context_note: "승인 시 플랜 무변경 실행"}`)를 결과로 반환한다 — 버블링은 호출자가 HITL-POLICY [3]으로 처리.
7. Announce: "**[EXEC]** Executing with Sonnet..."
8. Run Phase 2 (Sonnet agents)
9. Announce: "**[VERIFY]** Checking Definition of Done..." then run Phase 2.5 (max 2 verify→fix rounds, escalate to Opus on 2nd retry)
10. Report results

---

## 노하우

(누적 학습 — `/cs-experiencing version-up smart-run` 으로 추가된다. 아직 없음.)
