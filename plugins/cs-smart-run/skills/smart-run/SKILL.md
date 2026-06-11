---
name: cs-smart-run
user-invocable: true
description: |
  Orchestrator: Spec check → Plan with Opus → Plan review → Execute with Sonnet → Verify.
  Opus analyzes the task and produces a structured plan; Sonnet agents
  execute each step in parallel where possible; an independent verifier
  checks the Definition of Done with tool evidence.
  Use when asked to "smart run", "/smart-run", "플랜실행", or when the user
  wants Opus-quality planning with Sonnet-speed execution across multiple skills.
version: 1.0.0
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

검증 프로토콜: plugins/shared/LOOP-PROTOCOL.md + plugins/shared/agents/verifier.md를 따른다.

## How this skill works

When invoked, you orchestrate these phases:

0. **SPEC CHECK** — confirm goal/constraints/acceptance criteria before any agent spawn
1. **PLAN phase** — spawn a single Opus agent to think deeply and produce a structured plan
1.5. **PLAN REVIEW** — one Sonnet critic refutes the plan; Opus revises once if defects found
2. **EXEC phase** — spawn one or more Sonnet agents to implement the plan
2.5. **VERIFY** — an independent agent checks the Definition of Done with tool evidence (max 2 verify→fix rounds)

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

---

## Phase 2: EXEC (Sonnet)

fan-out 직전에 플랜의 Definition of Done을 한 줄 성공 기준으로 요약 출력한다
(LOOP-PROTOCOL [b] SUCCESS CRITERIA FIRST).

Read the plan from Phase 1. For each step:

- **Independent steps** (marked `[PARALLEL]`): spawn Sonnet agents **simultaneously** in a single message
- **Sequential steps**: spawn Sonnet agents one at a time, passing the previous result as context

Spawn each execution agent with `model: "sonnet"`.

Prompt each Sonnet execution agent with:
```
You are an expert implementer. Execute this specific step from a larger plan:

## Your Step
<step description>

## Full Plan Context
<full plan from Opus>

## Prior Step Results (if any)
<results>

Execute completely. Return: what you did, files changed (exact paths), commands you ran with their exit status, and any output the next step needs.
```

---

## Phase 2.5: VERIFY (independent agent)

After all execution agents complete, spawn ONE independent `model: "sonnet"`
agent that did NOT execute any step. Skip this phase only if the plan was
read-only (no files changed, no commands with side effects).

Prompt the verifier with:
```
You are an adversarial verifier. Your job is to REFUTE the claim that this plan is complete. Do not trust the executors' self-reports.

## Definition of Done (from the plan)
<DoD section from the Opus plan>

## Claimed results per step
<each step's self-report>

For EVERY Definition of Done item:
1. Gather tool evidence yourself — re-run the relevant tests/builds/lints, read the changed files, run `git diff`/`git status` to confirm claimed changes actually exist.
2. Mark the item PASS or FAIL, citing the exact command output or file content as evidence. A self-report is never evidence.

Return a checklist: item → PASS/FAIL → evidence. List any FAILed items with the specific gap.
```

**verify→fix 루프 (BOUNDED, 최대 2라운드)**:

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
- What was planned (Opus), including the Phase 1.5 critic's verdict
- What was executed (Sonnet agents)
- Verification results: each Definition of Done item with PASS/FAIL and evidence
- Any steps that failed or need follow-up (unresolved FAILs go here)

If any step failed, was re-planned, or a correction worked, draft a candidate
learning entry (task, plan shape, failed step, correction) and end the report with:
"💡 학습 저장: `/cs-experiencing version-up smart-run` 으로 이번 패턴을 노하우에 추가하세요."

---

## Invocation

When the user runs `/smart-run <task>` or `/플랜실행 <task>`:

1. Confirm you understood the task (one line)
2. Run Phase 0 (SPEC CHECK); ask clarifying questions only if goal/constraints/acceptance criteria are missing
3. Announce: "**[PLAN]** Thinking with Opus..."
4. Run Phase 1 (Opus agent); if it returned BLOCKING QUESTIONS, resolve via AskUserQuestion and re-run Phase 1
5. Announce: "**[REVIEW]** Critiquing plan..." then run Phase 1.5 (Sonnet critic, one Opus revision pass max)
6. Show the plan to the user, ask for approval or proceed automatically at L2+ (at L2+, auto-proceed only after the critic pass; the revised plan replaces the original shown to the user)
7. Announce: "**[EXEC]** Executing with Sonnet..."
8. Run Phase 2 (Sonnet agents)
9. Announce: "**[VERIFY]** Checking Definition of Done..." then run Phase 2.5 (max 2 verify→fix rounds, escalate to Opus on 2nd retry)
10. Report results

---

## 노하우

(누적 학습 — `/cs-experiencing version-up smart-run` 으로 추가된다. 아직 없음.)
