# CSnCompany_2-0 루프 엔지니어링 감사 보고서 (2026-06)

## Executive Summary

The CSnCompany_2-0 marketplace is an unusually mature "virtual AI company": 11 plugins plus a shared Python layer, with real working assets most plugin ecosystems lack — a deterministic pre-pass (pre_pass.py, extract_summary.py), an artifact registry pipeline (CLARIFY → PLAN → SHIP-REPORT), lead-isolated fan-out orchestration, and a genuinely closed memory write loop (68 learnings captured via cs-end's rubric-gated Learning Gate).

However, every plugin shares the same structural weakness: **execution is single-pass with self-asserted success.** No plugin adversarially verifies findings, no plugin loops until its own success criteria pass, and the memory loop closes only on the write side — learnings are appended as prose but almost never compiled back into the operative prompts (CS-plan's knowhow #3/#5/#6 and CS-test's #16/#21/#22 prescribe protocol changes that were never applied).

To get Fable-5-class results on Sonnet, the fix is not more prescription — the repo is already over-prescribed in mechanics and under-prescribed in quality bars — but three shared primitives applied everywhere:

1. **Evidence-bound claims** — every finding cites command output or file:line; unevidenced = UNVERIFIED
2. **One reusable verifier/refuter agent** gating every lead's synthesis
3. **Bounded verify→fix→re-check loops** keyed to the success criteria each plugin already writes but never consumes

Crucially, almost all of this is markdown edits to existing SKILL/agent files plus ~50 lines of Python — no rewrite needed.

## 플러그인 성숙도 테이블

| 플러그인 | 점수 (/10) | 한 줄 평가 |
|---|---|---|
| cs-end-v3 | 6 | Best-in-repo: LSTM-style gated memory pipeline with deterministic digest, but Phase 4 (git push) is unspecified and its 4 agents have no definitions. |
| self-upgrade-mechanism | 6 | Write half of the learning loop genuinely works (68 entries); read half is weak — append-only file, no retrieval, learnings never become prompt edits. |
| cs-experiencing-v8 | 5 | Real preflight gate and version-up machinery, but stale paths/version drift everywhere and no adversarial check on stored learnings. |
| shared-infra | 5 | Strongest pattern in the repo (deterministic Python pre-pass + artifact registry), missing the shared loop/verifier harness everything else needs. |
| cs-clarify-v1 | 4 | Good rubric-gated interview loop, but a parallel-vs-sequential contradiction between SKILL and agent file reproduces its own documented critical bug. |
| cs-design-v20 | 4 | Excellent constraint-document quality bar and generator self-check grep loop; review side is single-pass with hardcoded success checkmarks. |
| cs-error-notes-v1 | 4 | Solid 5-field failure-memory format with cross-plugin wiring, but notes are never recalled at debugging time and root causes are unevidenced. |
| cs-ceo-v15 | 3 | Right scaffolding (Goal Gate, partnership protocol, knowhow log) but the GOAL.success_criteria it produces is never checked — pure single-pass dispatch. |
| CS-plan-v21 | 3 | Clean hub-and-spoke fan-out, but specialists can't see the repo, artifacts are never cross-checked, and recorded learnings were never wired into protocols. |
| CS-test-v26 | 3 | 14-agent harness with the best learning log (31 entries), yet zero verification of findings and its own #16/#22 fix-loop learnings sit unimplemented. |
| CS-codebase-review-v29 | 3 | Deterministic pre-pass grounding is exemplary; everything downstream (5 reviewers, grade) is model say-so with a broken commands/ packaging. |
| cs-ship-v1 | 3 | Numeric ship gate with tiered models, but VERIFIED never means 'tests ran green' and --fix is advertised yet unimplemented. |
| cs-smart-run | 2 | Cleanest Opus-plan/Sonnet-execute tiering in the repo, wrapped around zero verification — Definition of Done is written and never checked. |
| cs-design-sample1 | 1 | --apply claims success without re-auditing its own edits; checklist duplicates and lags the knowledge file. |
| convo-maker | 1 | Single-pass prompt skill with a great worked example but no faithfulness check, no quality gate, hardcoded vault path. |

## 재구조화 계획 (R1-R9)

### R1 — 공유 루프 프로토콜 + 재사용 verifier 에이전트 생성 [P0 — ✅ 구현됨]

**Scope**: NEW plugins/shared/LOOP-PROTOCOL.md, plugins/shared/agents/verifier.md, plugins/shared/GATE-LOOP.md

Three small shared markdown files every lead agent references instead of duplicating per plugin: (1) LOOP-PROTOCOL.md — the five rules (EVIDENCE / SUCCESS CRITERIA FIRST / BOUNDED LOOP / COVERAGE HONESTY / REPORT FULL, FILTER DOWNSTREAM) plus the Prescription Policy; (2) agents/verifier.md — the reusable refuter prompt (CONFIRMED/REFUTED/UNCERTAIN with counter-evidence, critical/high only, skip deterministic-backed findings); (3) GATE-LOOP.md — gate→record→fix-blocking-items-only→re-gate, max 3 rounds. All paths via `${CLAUDE_PLUGIN_ROOT}/../shared/`, never absolute.

**근거**: Every single audit found the same two critical gaps (no adversarial verification, no loop-until-done). One shared protocol file referenced by 11 plugins is the maximum-leverage, zero-duplication fix.

### R2 — 4대 fan-out 플러그인에 verifier + 증거 규칙 배선 [P0 — ✅ 구현됨]

**Scope**: cs-ceo-v15/agents/ceo.md, CS-test-v26 (test-lead + SKILL + new finding-verifier), CS-codebase-review-v29 SKILL, cs-ship-v1 (ship-lead + pre-pr-validator)

cs-ceo: evidence requirement in Phase 3 Task prompts, UNVERIFIED tagging, conditional Phase 3.5 spot-check. CS-test: Phase 2.5 finding-verifier (reproduce critical/high from scratch), coverage % header + N/A grade caps. CS-codebase-review: Phase 1.5 refuter (default REFUTED unless confirmed in code), reviewers report ALL findings with file:line+confidence, grade from CONFIRMED items only with [verified]/[model-claimed] tags. cs-ship: Phase 2-0 adversarial spot-check of DONE/VERIFIED claims (refuted → PARTIAL, 2+ refutations cap at WARNINGS); coverage-auditor actually RUNS the test suite — VERIFIED means "exists AND ran green".

**근거**: These four plugins produce the verdicts the user acts on; killing the plausible-but-wrong-finding failure mode here delivers most of the Sonnet→Fable-quality gap closure.

### R3 — 활성 정합성 버그 및 드리프트 수정 [P0 — ✅ 구현됨]

**Scope**: cs-clarify-v1 clarify-lead.md, cs-end-v3 cs-end.md, cs-experiencing-v8 commands + plugin.json, CS-test-v26/CS-plan-v21 commands, cs-ship SKILL, stray "VERSION 2" files

One hygiene pass: clarify-lead parallel→sequential rewrite with CRITICAL callout; cs-end Phase 4 written (explicit staging scope, never `git add -A`, AUTO_NO_PUSH guard, pull --rebase retry); hardcoded `../CS-test-v1` paths → canonical `sort -V | tail -1` snippet; version metadata sync + stray file deletion; cs-ship hardcoded /Users/gwanli path → `${CLAUDE_PLUGIN_ROOT}`-relative + TeamDelete allowlist; dead domains/ command paths fixed; cs-end `exit 0` skip → CS_V7_OK variable.

**근거**: Weak models follow instructions literally; contradictions, dead paths, and missing sections are where Sonnet silently does the wrong thing.

### R4 — 묵혀둔 학습 적용 + "학습은 프롬프트를 패치해야 한다" 규칙 [P0 — ✅ 구현됨]

**Scope**: CS-plan-v21, CS-test-v26, cs-design-v20, plugins/CLAUDE.md, all knowhow sections

(a) Apply now: CS-plan #3/#5 → Step 1.5 ambiguity preflight, #6 → "핵심 설계 결정 + 대안 1개" in arch-designer; CS-test #21/#23 → 사전 준비 port/build verification + mandatory success criterion per agent prompt; cs-design lessons 5/6 → A/B/C direction options + [CSS]/[JSX] risk labels. Mark each applied entry "✅ 반영됨 (2026-06)". (b) Institute the rule in plugins/CLAUDE.md + cs-end Phase 2 gate: 교훈이 프로토콜 변경을 지시하면 같은 커밋에서 해당 SKILL/agents/*.md에 반영하고 ✅ 반영됨 표시. 미반영 교훈은 실행되지 않는다.

**근거**: The self-improvement loop currently terminates at documentation — the single biggest systemic flaw. These learnings are already validated by real sessions; applying them is free quality.

### R5 — 실행 플러그인에 경계 있는 verify→fix 루프 추가 [P1 — ✅ 구현됨]

**Scope**: cs-smart-run, cs-ceo-v15, cs-ship-v1, cs-design-v20, CS-plan-v21, cs-design-sample1

All referencing LOOP-PROTOCOL.md for loop semantics: cs-smart-run — Phase 0 SPEC CHECK + Phase 1.5 plan-critic + Phase 2.5 VERIFY (max 2 verify→fix rounds, escalate to opus on 2nd retry). cs-ceo — Phase 3.5 Goal Gate Check (grade each success_criterion PASS/FAIL, re-dispatch failing domains max 2 rounds, 목표 달성도 table). cs-ship — --fix as a max-2-round loop over MISSING items re-running only failed validators. cs-design — Step 5.5 verify-after-fix (before/after counts, cap 2 re-runs) + grep-count placeholders instead of hardcoded ✓. CS-plan — Phase 2a consistency gate (name-table cross-check, one targeted revision round) + codebase survey CONTEXT block. cs-design-sample1 — --apply re-runs the audit until pass or 3 rounds.

**근거**: Loop-until-done is the second half of the Sonnet-compensation strategy: a cheap model that iterates against a checked criterion beats a strong model running once. All loops are bounded.

### R6 — 메모리 재구조화: 인덱스 + 검색 + 도메인별 knowledge 파일 [P1 — ✅ 구현됨]

**Scope**: cs-experiencing-v8 SKILL + new knowledge/ dir, all plugin kickoff sections, plugins/CLAUDE.md, cs-error-notes-v1

(1) Split the 68-entry blob: orchestrator-domain entries inline, project-specific entries → knowledge/<topic>.md with a one-line-per-entry index table in SKILL.md. (2) Read side: each fan-out plugin's kickoff greps the knowledge index for task keywords and injects top 2-3 matches into dispatched agent prompts. (3) Register clarify/smart-run as version-up domains with seeded 노하우 sections. (4) cs-ceo Phase 5-B appends 노하우 후보 to .experiencing-btw.json. (5) Error recall: cs-error-notes `recall` subcommand + the plugins/CLAUDE.md rule — before debugging any NEW error, grep ~/.claude/error-notes/INDEX.md first.

**근거**: The store already exceeds read limits and is write-only for most plugins. An index + explicit retrieval step turns 68 inert memos into priors every run actually consumes.

### R7 — 공유 인프라 확장: gate verdict, staleness, learn-append, version-check [P2 — 향후 과제]

**Scope**: plugins/shared/artifact_registry.py, pre_pass.py, abspath_check.py, cs-ship SKILL

~80 lines of Python: artifact_registry gets {verdict, round, blocking_items} fields + `record`/`verdict`/`find-meta` subcommands (mtime-based staleness, CS_ARTIFACT_STALE_DAYS default 7); pre_pass.py gets `learn-append` and `version-check <plugin_dir>`; abspath_check.py ignore-regex fix; artifact_registry.sh routed through the _bootstrap fallback chain.

**근거**: Durable rails under R1/R5/R6 — verdict+round state makes gate loops auditable across sessions. P2 because the markdown protocols work without them on day one.

### R8 — 탈처방(de-prescription) 패스 [P2 — 향후 과제]

**Scope**: All SKILL.md/agent files; worst offenders: CS-test agents, cs-end output templates, cs-ceo infer_timing, cs-design-v20 embedded greps, checklist-builder.md

One sweep per plugin guided by the Prescription Policy in LOOP-PROTOCOL.md: KEEP rubrics, thresholds, schemas, ownership contracts, worked examples, deterministic bash; REPLACE literal grep recipes, emoji box templates, exact question strings, and the 160-line TypeScript skeleton with goal statements. Normalize model assignment: alias tiers only (opus/sonnet/haiku), strongest model on leads/verifiers, haiku on grep-heavy workers.

**근거**: The repo is prescriptive exactly backwards — rigid where flexibility is cheap, vague where rigor matters. Doing it after R1-R5 means the new quality bars exist to replace the deleted scaffolding.

### R9 — 라우팅 및 플러그인 메타데이터 단일 소스화 [P2 — 향후 과제]

**Scope**: .claude-plugin/marketplace.json, plugins/CLAUDE.md, root CLAUDE.md routing block, pre_pass.py DOMAIN_PATTERNS, README.md

Make marketplace.json (or one routing.json) the single source of truth; generate the CLAUDE.md routing block and pre_pass.py domain tables from it via a small sync script. (The routing-rule softening — "prefer the matching skill; route directly on high confidence, otherwise confirm with one question" — was applied early as part of this restructuring.) Longer term: retire directory-copy versioning (CS-test-v26 → stable dir + VERSION + git tags).

**근거**: Four divergent copies of routing/domain knowledge drift independently and silently break domain detection; generation from one source ends the class of bug rather than the instance.

## 자가 업그레이드 루프 설계 (7단계)

The loop reuses cs-end + cs-experiencing end-to-end; the only additions are a skeptic gate, a "prompt patch" step, and adversarial verification of the edit itself. All seven stages trigger from the existing /cs-end ritual.

1. **CAPTURE** (기존, 강화) — btw mid-session capture to .experiencing-btw.json for all plugins; cs-error-notes capture with verbatim tool output mandatory. At session end, cs-end Phase 0.5 runs the deterministic session-digest and the four now-defined agents extract candidates. New rule: every candidate carries a 근거 field quoting actual session evidence; no evidence → tier capped at tactical, annotated `<!-- unverified -->`.

2. **GRADE** (기존 Learning Gate, 적대화) — The 3-axis novelty/impact/reusability gate stays, but novelty is no longer title-only: grep the full knowhow store and Read the 3 nearest entries before scoring; overlaps become dated addenda. For principle-tier survivors only, one lightweight skeptic Task attempts refutation (CONFIRM / DOWNGRADE-to-tactical / REJECT).

3. **CONVERT** (신규 — cs-end Phase 2.6 "Prompt Patch") — For each PASS learning, answer one forced question: "which SKILL/agent instruction should change so this mistake cannot recur?" Outcomes: (a) PATCH — apply a concrete Edit in the same run and mark ✅ 반영됨; (b) MEMO — append to the knowledge/ topic file + index; (c) DEFER — write to .experiencing-btw.json as a pending patch with the target file named. This single step fixes the systemic flaw found everywhere.

4. **VERIFY THE EDIT** (신규, 기계 우선) — For every prompt patch: (i) deterministic checks via pre_pass.py (frontmatter parses, referenced paths exist, version-check passes); (ii) one shared-verifier Task reads the patched file cold: "Could a Sonnet executor follow this unambiguously? Does it contradict any other instruction in this plugin?" — exactly the check that would have caught the cs-clarify parallel-vs-sequential contradiction. REFUTED patches are reverted and demoted to DEFER.

5. **VERSION BUMP** (기존 version-up, 강화) — Selective bump filtered by DOMAINS_USED, plus STEP 4b runs version-check so VERSION/plugin.json/SKILL frontmatter can never disagree; the DIGEST-failure mass-bump fallback now requires explicit AskUserQuestion confirmation.

6. **CHANGELOG + PUSH** (기존 Phase 4/5, 명세화) — Defined staging scope (never `add -A`), atomic commit template, CHANGELOG append as a scripted mandatory step. Push remains author-gated (AUTO_NO_PUSH) with the grounded post-push report.

7. **MEASURE AND DECAY** (외부 루프 폐쇄) — pre_pass.py greps the session digest for '#NN' knowhow citations and records hits; the Forget Gate prioritizes zero-hit tactical entries for non-destructive deprecation and flags high-hit entries for promotion into operative prompt text. Principle entries older than ~180 days surface for review (never auto-deprecate). The next session's 5-field handoff carries pending DEFER patches forward.

**자율성 자세**: Stages 1-2 and 4-7 run autonomously inside /cs-end; humans gate exactly twice — the one-click learning confirmation (with the skeptic's verdict shown inline) and the final push. Prompt patches apply autonomously because stage 4 adversarially verifies them and git makes them revertible. Net effect: every session that teaches the system something ends with the system's own prompts measurably changed, checked, versioned, and pushed.

## 검증 방법론

본 감사는 80개 에이전트를 동원한 다층 감사로 수행되었다: 플러그인별 병렬 감사에서 64개의 gap을 식별하고, 각 gap을 적대적 검증(adversarial verification) 라운드에 통과시켜 54개를 확정(confirmed)했다. 본 보고서의 R1-R9 계획과 수정 사항은 확정된 54개 gap만을 근거로 한다. 미확정 10개는 증거 불충분 또는 반증으로 제외되었다 — 본 보고서가 처방하는 EVIDENCE 규칙을 보고서 자신에게도 적용한 결과다.
