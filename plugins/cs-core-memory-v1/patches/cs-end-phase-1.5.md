# Patch: cs-end Phase 1.5 — Core Memory Synthesis

**Target file:** `plugins/cs-end-v*/commands/cs-end.md`
**Insert position:** After Phase 1 (4-Agent parallel analysis), before Phase 2 (Learning Gate)
**Depends on:** cs-core-memory-v1 installed

---

## Phase 1.5 — Core Memory Synthesis (memory-keeper)

**Skip condition:** If `$HOME/.claude/plugins/marketplaces/CSnCompany_2-0/plugins/cs-core-memory-v1/` does not exist, output one line "Phase 1.5: cs-core-memory not installed — skipping" and proceed to Phase 2.

```bash
CORE_MEMORY_PLUGIN=$(ls -d "$HOME/.claude/plugins/marketplaces/CSnCompany_2-0/plugins/cs-core-memory-v"* 2>/dev/null | sort -V | tail -1)
MEMORY_KEEPER="$CORE_MEMORY_PLUGIN/agents/memory-keeper.md"
CORE_MEMORY_FILE="$HOME/.claude/core-memory/CORE.md"

if [ -z "$CORE_MEMORY_PLUGIN" ] || [ ! -f "$MEMORY_KEEPER" ]; then
  echo "Phase 1.5: cs-core-memory not installed — skipping"
  CORE_MEMORY_SUMMARY=""
else
  echo "Phase 1.5: Spawning memory-keeper agent..."
fi
```

**When cs-core-memory IS installed**, spawn memory-keeper as a single Task with the following inputs from Phase 0.5 and Phase 1:

```
Task(
  model: "sonnet",
  description: "memory-keeper: Cross-session core memory synthesis",
  prompt: """
  [memory-keeper agent instructions from MEMORY_KEEPER file]

  ## Inputs for this session

  SESSION_DATE: [YYYY-MM-DD from current date]
  DOMAINS_USED: [DOMAINS_USED from Phase 0.5]
  SESSION_SUMMARY: [2-3 sentence digest constructed from Phase 0.5 DIGEST]
  SESSION_LEARNINGS: [JSON array from learning-extractor Phase 1 output]

  ## Task

  Execute the memory-keeper protocol:
  1. Read CORE_MEMORY_FILE
  2. Cross-reference SESSION_LEARNINGS against existing patterns
  3. Update CORE.md (reinforce, create new, flag contradictions)
  4. Return core_memory_summary JSON

  CORE_MEMORY_FILE path: ~/.claude/core-memory/CORE.md
  """
)
```

**Extract core_memory_summary from Task output:**

```bash
CORE_MEMORY_SUMMARY=$(task_result | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    print(json.dumps(data.get('core_memory_summary', {})))
except:
    print('{}')
" 2>/dev/null)
```

**Phase 1.5 output (always print, even if CORE.md was empty before):**

```
Phase 1.5 — Core Memory Synthesis
  Patterns reinforced : [patterns_reinforced from summary]
  New entries         : [new_entries from summary]
  Contradictions      : [contradictions from summary, or "none"]
  Top insight         : [top_insight from summary, or "none yet"]
  Historical warning  : [historical_warning from summary, or "none"]
```

If memory-keeper Task returns `status: error`, print the error and set `CORE_MEMORY_SUMMARY=""`. Proceed to Phase 2 without blocking.

**CORE_MEMORY_SUMMARY variable is passed to Phase 6.**

---

## Phase 6 Integration (modification to existing Phase 6)

In the Phase 6 Compact Handoff, add a 6th field to the 5-field structure:

```
CORE    : [top_insight from CORE_MEMORY_SUMMARY, or "no cross-session patterns yet"]
```

**Example extended compact:**

```
/compact 2026-06-25 cs-end core-memory-v1 integrated. memory-keeper synthesizes cross-session patterns.

DONE    : cs-core-memory-v1 plugin created and integrated with cs-end Phase 1.5 and cs-ceo Phase G
LEARNED : memory-keeper distinguishes episodic (cs-experiencing) from semantic/strategic (CORE.md) — no duplication
DOMAINS : cs-end, cs-core-memory
NEXT    : Run first real session with /cs-end to populate CORE.md with actual patterns
BTWS    : 0 pending — none
CORE    : No cross-session patterns yet (first session)
```

The CORE field is omitted (not shown as "none") if `CORE_MEMORY_SUMMARY` is empty or if `top_insight` is null.
