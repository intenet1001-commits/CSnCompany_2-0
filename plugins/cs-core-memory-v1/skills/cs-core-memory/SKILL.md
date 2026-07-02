---
name: cs-core-memory
user-invocable: true
description: |
  Cross-session strategic memory recall. Reads ~/.claude/core-memory/CORE.md and
  surfaces patterns, decisions, and historical warnings relevant to the current task.
  Used by cs-ceo at session start after GOAL_STATEMENT is confirmed.
  Use when invoked via /cs-core-memory, or when user says "과거 패턴", "이전에 어떻게 했지", "historical context".
version: 1.0.0
allowed-tools:
  - Read
  - Bash
  - Grep
---

# /cs-core-memory — Cross-Session Strategic Memory Recall

## Purpose

Surface relevant historical wisdom from `~/.claude/core-memory/CORE.md` for the current task.
This is NOT a log reader — it is a pattern matcher that answers: "What does our institutional memory say about this?"

## Usage

```
/cs-core-memory recall [topic]       # Surface patterns relevant to [topic]
/cs-core-memory status               # Show CORE.md summary stats
/cs-core-memory warnings             # List all Recurring Issues with hit_count >= 2
/cs-core-memory decisions            # List all Key Decisions
/cs-core-memory contested            # List all Contested Entries, oldest-unresolved first
/cs-core-memory full                 # Dump entire CORE.md (for deep review)
```

## Storage Location

```bash
CORE_MEMORY="$HOME/.claude/core-memory/CORE.md"
```

---

## Execution Protocol

### `/cs-core-memory recall [topic]`

**Step 1 — Existence check**

```bash
CORE_MEMORY="$HOME/.claude/core-memory/CORE.md"
if [ ! -f "$CORE_MEMORY" ]; then
  echo "CORE.md does not exist yet. No cross-session memory available."
  echo "Core memory is built automatically after the first /cs-end session closure."
  exit 0
fi
```

**Step 2 — Keyword extraction**

Extract 3-5 search keywords from [topic]:
- Technical nouns (framework names, tool names, domain names)
- Action verbs describing the work (deploy, refactor, test, design)
- Error keywords if present

**Step 3 — Search CORE.md sections**

Search each section independently:

```bash
# Strategic Patterns — highest priority
grep -n -i "<keyword>" "$CORE_MEMORY" | head -20

# Recurring Issues — surface as warnings
# Key Decisions — surface as constraints
```

For each match, read the full entry (from the `###` header to the next `###` or `---`).

**Step 4 — Relevance ranking**

Score each matched entry:
- `validated` confidence + domain match → 3 points
- `confirmed` confidence → 2 points
- `emerging` confidence → 1 point
- Recurring Issue with hit_count >= 3 → 2 points (WARNING flag)
- Key Decision with `constraint: yes` → 3 points (CONSTRAINT flag)

Take top 3-5 by score.

**Step 5 — Output**

Format output as:

```
## Core Memory: [topic]

**Strategic Patterns** (validated across sessions):
[For each matched pattern]
- [Title] (seen [session_count]x, last: [last_seen])
  → [recommendation field — 1 sentence]

**Historical Warnings** (recurring issues):
[For each matched recurring issue with hit_count >= 2]
⚠️ [Title] (hit [hit_count]x — [last_seen])
  Root cause: [root_cause field]
  Workaround: [workaround field]

**Active Constraints** (key decisions):
[For each matched decision with constraint: yes]
🔒 [Title] ([date])
  Decision: [decision field]
  Rejected: [rejected_alternatives field]

**No relevant core memory** — [if no matches found, state this explicitly]
```

If CORE.md exists but has no entries yet (all sections empty), output:
```
Core memory file exists but contains no entries yet.
Entries accumulate automatically as sessions close via /cs-end.
```

---

### `/cs-core-memory status`

Read CORE.md header and section counts:

```bash
echo "=== Core Memory Status ==="
head -5 "$CORE_MEMORY"
echo ""
echo "Strategic Patterns: $(grep -c '^### ' <(sed -n '/^## Strategic Patterns/,/^## Recurring Issues/p' "$CORE_MEMORY") 2>/dev/null || echo 0)"
echo "Recurring Issues:   $(grep -c '^### ' <(sed -n '/^## Recurring Issues/,/^## Key Decisions/p' "$CORE_MEMORY") 2>/dev/null || echo 0)"
echo "Key Decisions:      $(grep -c '^### ' <(sed -n '/^## Key Decisions/,/^## Contested/p' "$CORE_MEMORY") 2>/dev/null || echo 0)"
echo "Contested Entries:  $(grep -c '^### ' <(sed -n '/^## Contested/,/^## Growth/p' "$CORE_MEMORY") 2>/dev/null || echo 0)"
```

Output a one-line health summary:
- GREEN: 0 contested entries, >= 1 validated pattern
- YELLOW: contested entries exist (need review), OR 0 patterns after 5+ sessions
- RED: CORE.md missing or unreadable

---

### `/cs-core-memory warnings`

List all Recurring Issues sorted by hit_count descending:

```bash
sed -n '/^## Recurring Issues/,/^## Key Decisions/p' "$CORE_MEMORY"
```

Highlight any with `hit_count >= 3` as CRITICAL (promoted to Strategic Patterns expected).

---

### `/cs-core-memory decisions`

List all Key Decisions with constraint status:

```bash
sed -n '/^## Key Decisions/,/^## Contested/p' "$CORE_MEMORY"
```

Separate output into:
- CONSTRAINTS (constraint: yes) — show first, bold
- GUIDELINES (constraint: no) — show after

---

### `/cs-core-memory contested`

List all Contested Entries, sorted by `sessions_unresolved` descending:

```bash
sed -n '/^## Contested Entries/,/^## Growth/p' "$CORE_MEMORY"
```

Highlight any with `sessions_unresolved >= 3` as CRITICAL — these have survived 3+ memory-keeper
runs without resolution and need an explicit user decision (accept one side, merge, or archive
both) rather than continuing to accumulate silently.

---

### `/cs-core-memory full`

Read and output entire CORE.md verbatim. Prepend:
```
[Full Core Memory Dump — YYYY-MM-DD — Session [N]]
```

---

## Integration: Referenced by cs-ceo Phase G.5

cs-ceo does NOT invoke this skill via `Skill()` — Phase G.5 in `cs-ceo-v15/agents/ceo.md`
performs an **inline recall** instead (CEO reads `CORE.md` directly and filters, no Task/Skill
spawn). Phase G.5 reimplements a simplified 3-tier priority version of the ranking described
in Step 2-4 above (Key Decisions with `constraint: yes` → Strategic Patterns `validated` →
Recurring Issues `hit_count >= 2`), rather than the full 5-tier scored ranking in this file.

The two implementations are intentionally decoupled for performance (no extra tool call at
session start) but must be kept in sync manually: any change to the recall/ranking logic here
should be mirrored in `cs-ceo-v15/agents/ceo.md` Phase G.5, and vice versa.

The `recall`/`status`/`warnings`/`decisions`/`full` subcommands above remain the canonical,
user-invocable entry points (`/cs-core-memory recall [topic]`, etc.) and use the full scoring
algorithm. Phase G.5's output convention mirrors this file's Step 5 format:
```
📚 Core Memory: [relevant insight]
```

If no relevant patterns found, CEO proceeds silently without the block.

---

## Notes on What This Is NOT

- NOT a replacement for cs-experiencing — episodic learning storage remains in cs-experiencing SKILL.md
- NOT a session log — CORE.md contains only synthesized patterns, not event records
- NOT auto-pruned — Strategic Patterns and Key Decisions are permanent unless explicitly revised
- NOT searched during task execution (only at session start via cs-ceo, and on explicit recall)
