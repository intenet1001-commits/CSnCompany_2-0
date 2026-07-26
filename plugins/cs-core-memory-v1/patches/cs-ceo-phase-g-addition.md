# Patch: cs-ceo Phase G Addition — Core Memory Context Injection

**Target file:** `plugins/cs-ceo-v*/agents/ceo.md`
**Insert position:** In Phase G, after GOAL_STATEMENT is confirmed (after Step 3), before Phase -3
**Depends on:** `cs-memory` installed (source directory: `cs-core-memory-v1`)

---

## Phase G Addition — Core Memory Context Injection

Insert this block immediately after the GOAL_STATEMENT confirmation echo and before Phase -3 execution:

```
### Phase G.5: Core Memory Recall (Historical Context)

After GOAL_STATEMENT is confirmed, check for relevant cross-session patterns.
```

**Implementation:**

```bash
CORE_MEMORY_PLUGIN=$(ls -d "$HOME/.claude/plugins/marketplaces/CSnCompany_2-0/plugins/cs-core-memory-v"* 2>/dev/null | sort -V | tail -1)
CORE_MEMORY_FILE="$HOME/.claude/core-memory/CORE.md"
CORE_MEMORY_SKILL="$CORE_MEMORY_PLUGIN/skills/cs-core-memory/SKILL.md"

# Skip silently if plugin not installed or CORE.md empty/missing
if [ -z "$CORE_MEMORY_PLUGIN" ] || [ ! -f "$CORE_MEMORY_FILE" ]; then
  CORE_CONTEXT=""
else
  # Check if CORE.md has any actual entries (not just template)
  ENTRY_COUNT=$(grep -c '^### ' "$CORE_MEMORY_FILE" 2>/dev/null || echo 0)
  if [ "$ENTRY_COUNT" -eq 0 ]; then
    CORE_CONTEXT=""
  fi
fi
```

**When CORE.md has entries (ENTRY_COUNT > 0):**

Read CORE.md and extract relevant patterns for GOAL_STATEMENT. CEO performs inline recall (no Task spawn needed — CEO reads and filters directly):

```bash
Read("$CORE_MEMORY_FILE")
```

After reading, CEO applies this filter:

1. Extract 3-5 keywords from GOAL_STATEMENT (technical nouns, action verbs, domain names)
2. Search CORE.md sections for keyword matches
3. Prioritize in this order:
   - `constraint: yes` Key Decisions (non-negotiable — MUST surface these)
   - `validated` Strategic Patterns matching keywords
   - Recurring Issues with `hit_count >= 2` matching keywords
   - `confirmed` Strategic Patterns matching keywords

4. If matches found, output the "Core Memory" block:

```
📚 Core Memory: [GOAL_STATEMENT keywords]
[For each matched entry — max 3 total]
  • [Entry title] ([confidence/hit_count]) — [recommendation or workaround, 1 sentence]
[If any constraint: yes decision matched]
  🔒 Constraint active: [Decision title] — [decision field, 1 sentence]
[If any recurring issue hit_count >= 2 matched]
  ⚠️ Historical warning: [Issue title] (seen [hit_count]x) — [workaround field]
```

5. If NO matches found: output nothing (proceed silently). Do NOT output "no relevant patterns" — silence means no match.

**CORE_CONTEXT variable** (used in Phase 4 report):

Set `CORE_CONTEXT` to the matched text (or empty string if no match). Include in Phase 4 CEO report under a new "Core Memory Applied" field if non-empty:

```
---
**Core Memory Applied**: [CORE_CONTEXT summary, 1-2 lines]
```

This field is omitted entirely if CORE_CONTEXT is empty.

---

## Phase G Full Sequence (updated)

After this patch, Phase G runs in this order:

```
① Goal signal analysis (existing)
② AskUserQuestion if unclear (existing)
③ GOAL_STATEMENT confirmed (existing)
→ [NEW] Phase G.5: Read CORE.md, surface relevant patterns (0-3 entries)
④ Proceed to Phase -3
```

The core memory recall adds at most 1 Read tool call and produces at most 3 bullet points of output. If CORE.md is missing or empty, this step is invisible (0 output, 0 tool calls beyond the existence check).

---

## Phase 4 Report Addition

Add to the CEO report template, after the `---` separator before domain results:

```
**Core Memory Applied**: [if CORE_CONTEXT non-empty: summarize in 1-2 lines | else: omit this field entirely]
```

This makes the historical context traceable in the CEO report — useful for understanding why certain decisions were made with awareness of past patterns.
