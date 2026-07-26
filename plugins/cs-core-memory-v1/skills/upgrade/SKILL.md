---
name: upgrade
description: Review pending long-term-memory and cs-end lessons, promote reusable evidence, and improve only the affected CS domain skills or agents. Use when the user invokes `/cs-memory:upgrade`, says "에이전트 업그레이드", "장기기억으로 에이전트 개선", "학습 후보 반영", or asks to evolve agents from accumulated project memory.
---

# Upgrade agents from memory

Consume accumulated candidates in one bounded batch. Do not rescan projects; `$learn` owns
project-memory collection.

## Public interface

```text
/cs-memory:upgrade
```

If there are no pending candidates, report a no-op without loading domain protocols or spawning
agents.

## Triage once

1. Read pending items from `~/.claude/.experiencing-btw.json`.
2. Reject secrets, temporary project facts, raw implementation summaries, and unsupported claims.
3. Search the latest `cs-experiencing-v*/skills/experiencing/SKILL.md` INDEX and relevant
   `knowledge/*.md` bodies for semantic duplicates.
4. Score novelty, impact, and cross-project reuse from 0 to 2:
   - `0–1`: reject;
   - `2–3`: keep pending;
   - `4–6`: promote or merge into an existing entry.
5. Run one skeptic pass over the full batch of proposed `principle` lessons. Do not spawn a team
   for ordinary triage.

## Route only actionable lessons

| Evidence changes future behavior in | Owner |
|---|---|
| browser, Playwright, QA, performance testing | latest `CS-test-v*` |
| planning, architecture, TDD boundaries | latest `CS-plan-v*` |
| code quality, security, maintainability review | latest `CS-codebase-review-v*` |
| UI, UX, accessibility, design systems | latest `cs-design-v*` |
| requirements and ambiguity handling | latest `cs-clarify-v*` |
| task allocation and orchestration decisions | latest `cs-ceo-v*` or `cs-smart-run` |

Keep project-specific knowledge only in project memory. A reusable fact may enter the experiencing
store without changing an agent. Upgrade an owner only when the lesson changes a concrete prompt,
checklist, tool rule, stopping condition, or validation gate.

## Apply safely

1. Run `bash plugins/shared/run_prepass.sh index-check` before writing.
2. Add or merge the promoted lesson in the experiencing store with provenance and exactly one
   INDEX row.
3. Update the smallest relevant owner `SKILL.md`, command, or `agents/*.md`. Do not copy the same
   rule into unrelated domains.
4. Run that domain's relevant deterministic checks or focused tests.
5. For learning-only changes, bump the affected plugin's patch version in place across `VERSION`,
   Claude/Codex manifests, primary SKILL metadata when present, and marketplace metadata when
   present. Create a new `-vN` directory only for an actual schema/structure generation change.
6. Re-run `index-check`, the changed plugin's `version-check`, and routing checks.
7. Update each candidate with `learn-update-status` only after its durable outcome is verified.
8. If any gate fails, revert only this upgrade's edits and leave candidates pending.

Never run `version-up all`. Never increase an unaffected domain's version.

## Report

List promoted, merged, pending, and rejected candidate counts; changed owner domains; validation
results; and old-to-new versions. Keep evidence concise.

