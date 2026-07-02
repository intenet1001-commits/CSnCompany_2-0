# CSnCompany_2-0 — An AI Team You Hire Inside Claude Code

> 🇺🇸 English · [🇰🇷 한국어](./README.ko.md)

**TL;DR — One marketplace, eleven AI teammates.** Install it once, and you can call a CEO, PM, Architect, Designer, QA Engineer, Code Reviewer, and DevOps engineer from inside Claude Code with simple slash commands like `/cs-ceo` or `/CS-test`.

> ⚡ **Optional: Install [uv](https://docs.astral.sh/uv/) for 70%+ token savings on code analysis** — `brew install uv` or `curl -LsSf https://astral.sh/uv/install.sh | sh`. Works without it too (automatic fallback).

---

## 🤔 What is this? (For Beginners)

[Claude Code](https://docs.claude.com/en/docs/claude-code) is Anthropic's official AI coding CLI. It supports **plugins** — bundles of slash commands, agents, and skills you install on top of it.

**CSnCompany_2-0** is a marketplace that bundles **11 plugins**, each one a specialist on a virtual AI team:

```
You ──▶ /cs-ceo "build a dashboard"
              │
              ▼
      🧭 CEO  decides which teammates to call
              │
   ┌──────────┼──────────┬──────────┐
   ▼          ▼          ▼          ▼
🏗️ Plan   🎨 Design   🧪 Test    🚢 Ship
```

You don't need to remember which command does what — type `/cs-ceo "your goal"` and it dispatches the right teammates. Or call them directly when you know what you need.

---

## 👥 The Team

| Member | Plugin | Slash Command | What it does |
|--------|--------|--------------|------|
| 🧭 **CEO** | `cs-ceo` | `/cs-ceo "goal"` | Estimates effort, picks teammates, dispatches them. **Start here if unsure.** |
| 💬 **PM** | `cs-clarify` | `/cs-clarify` | Asks Socratic questions, surfaces hidden assumptions, prevents over-engineering |
| 🏗️ **Architect** | `CS-plan` | `/CS-plan "feature"` | TDD + Clean Architecture plan: domain analysis, architecture, test strategy, checklist |
| 🎨 **Designer** | `cs-design` | `/cs-design <url>` | 5-agent design review: hierarchy, interaction, design system, a11y, anti-patterns |
| 🎨 **Design Reference** | `cs-design-sample1` | `/cs-design-sample1` | Crextio-style design guide for Tailwind/Next.js dashboards |
| 🧪 **QA Engineer** | `CS-test` | `/CS-test <url>` | 14-agent web test: security, SEO, perf, a11y, DB, PWA, touch, image |
| 🔍 **Code Reviewer** | `CS-codebase-review` | `/CS-codebase-review ./src` | 5-agent review: architecture, quality, security, perf, maintainability |
| 🚢 **DevOps** | `cs-ship` | `/cs-ship` | Pre-PR validation: spec compliance, coverage, commit messages |
| ⚡ **Team Lead** | `cs-smart-run` | `/cs-smart-run "task"` | Plan with Opus → execute with Sonnet agents in parallel |
| 📚 **Knowledge Keeper** | `cs-experiencing` | `/cs-experiencing` | Versioned learnings + `/cs-end` session-wrap *(author-only push)* |
| 🗣️ **Language Coach** | `convo-maker` | `/convo-maker` | Turns session Q&A into natural American English conversations |

---

## 🆕 What's new (2026-07)

**`/cs-company` — the whole company in one command.** One sentence in, a shipped feature out: it runs the full SDLC pipeline `CLARIFY → PLAN → IMPLEMENT → REVIEW → TEST → SHIP`, passing artifacts between phases through gates and routing rework back to the right phase (e.g. a failed test re-opens IMPLEMENT, a requirements gap re-opens PLAN).

```
/cs-company "add a dark-mode toggle with settings persistence"
```

**Shared protocol layer.** All teammates now follow the same set of protocols in `plugins/shared/`, so every plugin behaves predictably:

| Protocol | What it standardizes |
|----------|----------------------|
| `AGENT-CARD.md` | One card per agent: goal, backstory, ownership, expected output |
| `TASK-CONTRACT.md` | Every agent spawn carries a machine-checkable output contract |
| `DEBATE-PROTOCOL.md` | Disputed findings get a rebuttal round instead of silent discard |
| `ARTIFACT-CONTRACTS.md` | CLARIFY.md → PLAN.md → reports flow between plugins automatically |
| `MEMORY-PROTOCOL.md` | Leads recall past learnings/artifacts before starting work |
| `HITL-POLICY.md` | Human checkpoints (`--hitl auto/gate/always`) at key decisions |
| `PIPELINE-PROTOCOL.md` | The `/cs-company` phase table, gates, and rework routing |

---

## 🚀 Install in 60 seconds

### Prerequisite

Install [Claude Code](https://docs.claude.com/en/docs/claude-code/setup):

```bash
npm install -g @anthropic-ai/claude-code
```

Then launch it:

```bash
claude
```

### Step 1 — Add the marketplace

Inside Claude Code, paste:

```
/plugin marketplace add intenet1001-commits/CSnCompany_2-0
```

### Step 2 — Install the plugins you want

Pick à la carte, or install everything:

```
/plugin install cs-ceo@CSnCompany_2-0
/plugin install cs-clarify@CSnCompany_2-0
/plugin install CS-plan@CSnCompany_2-0
/plugin install cs-design@CSnCompany_2-0
/plugin install cs-design-sample1@CSnCompany_2-0
/plugin install CS-test@CSnCompany_2-0
/plugin install CS-codebase-review@CSnCompany_2-0
/plugin install cs-ship@CSnCompany_2-0
/plugin install cs-smart-run@CSnCompany_2-0
/plugin install cs-experiencing@CSnCompany_2-0
/plugin install convo-maker@CSnCompany_2-0
```

### Step 3 — Restart Claude Code

That's it. Type `/` in Claude Code and you'll see the new commands.

---

## 🧭 Don't know where to start?

Ask the CEO:

```
/cs-ceo "I want to build a user dashboard with auth"
```

The CEO estimates effort, decides which teammates to call (PM, Architect, Designer, etc.), and runs them in the right order. You just sit back and answer when they ask clarifying questions.

---

## 💡 Common Workflows

### Build a new feature from scratch

```
/cs-clarify "add Stripe payments"     # PM: surface assumptions
   ↓
/CS-plan "Stripe checkout + webhook"  # Architect: TDD plan
   ↓
… you implement code …
   ↓
/CS-test https://staging.example.com  # QA: 14-agent web test
   ↓
/CS-codebase-review ./src             # Reviewer: 5-agent code review
   ↓
/cs-ship                              # DevOps: pre-PR gate
```

### Audit an existing site

```
/cs-design https://example.com    # Visual + UX review
/CS-test https://example.com      # Security/SEO/perf/a11y
```

### Just let the CEO drive

```
/cs-ceo "audit my landing page and tell me what to fix first"
```

---

## 🏛️ Architecture — Lead-Agent Pattern + Python Pre-Pass

Every multi-agent plugin uses the **lead-agent pattern**: the main conversation spawns **one** lead agent, and the lead orchestrates N specialist workers internally. Worker output never pollutes your main context — only the final synthesized report comes back.

```
Main Claude Code conversation
  └─ SKILL.md (thin wrapper: parse args, spawn 1 lead Task)
       └─ lead agent (own context: orchestrate N workers)
            ├─ worker-1 → result file
            ├─ worker-2 → result file
            └─ worker-N → result file
            → synthesize final doc → return to main context
```

### Python Pre-Pass (optional, requires uv or python3)

For code analysis plugins, a Python pre-pass runs **before** the agents to extract structural data deterministically. The agents receive a compact JSON summary instead of reading raw files — cutting input tokens by 70%+.

```
plugins/shared/
├── _bootstrap.sh          ← uv/python3 detection + graceful fallback
└── scripts/
    ├── extract_summary.py ← file structure + import graph → JSON
    ├── ts_rust_diff.py    ← TypeScript ↔ Rust struct field diff
    └── abspath_check.py   ← hardcoded absolute path detection
```

**Without uv/python3**: all plugins still work normally — agents read files directly (more tokens, same results).
**With uv/python3**: agents receive pre-extracted JSON → faster, cheaper, more accurate cross-file analysis.

### Per-plugin agent counts

| Plugin | Agents | Mode |
|--------|--------|------|
| CS-test | 14 | Phase 1 sequential (build, page-explore) → Phase 2 parallel (12 specialists) |
| CS-plan | 4 | Parallel: domain, architecture, TDD, checklist |
| CS-codebase-review | 5 | Parallel: architecture, quality, security, perf, maintainability |
| cs-design | 5 | Parallel: visual, interaction, design-system, responsive/a11y, anti-pattern |
| cs-clarify | 4 | Sequential Socratic elicitation |
| cs-ship | 4 | Parallel pre-PR validation |
| cs-ceo | 1 lead → routes to others | Adaptive |

---

## 📁 Repo Layout

```
CSnCompany_2-0/
├── .claude-plugin/
│   └── marketplace.json           # the marketplace manifest
├── plugins/
│   ├── shared/                    # 🔧 Shared Python scripts (token optimizer)
│   │   ├── _bootstrap.sh          #    uv/python3 detection + graceful fallback
│   │   └── scripts/
│   │       ├── extract_summary.py #    file structure + import graph → JSON
│   │       ├── ts_rust_diff.py    #    TypeScript ↔ Rust struct field diff
│   │       └── abspath_check.py   #    hardcoded absolute path detection
│   ├── cs-ceo-v11/                # 🧭 CEO orchestrator
│   ├── cs-clarify-v1/             # 💬 PM
│   ├── CS-plan-v21/               # 🏗️ Architect
│   ├── cs-design-v19/             # 🎨 Designer
│   ├── cs-design-sample1/         # 🎨 Design reference
│   ├── CS-test-v26/               # 🧪 QA
│   ├── CS-codebase-review-v29/    # 🔍 Reviewer (Python pre-pass enabled)
│   ├── cs-ship-v1/                # 🚢 DevOps
│   ├── cs-smart-run/              # ⚡ Team Lead
│   ├── cs-experiencing-v8/        # 📚 Knowledge keeper
│   └── convo-maker/               # 🗣️ Language coach
├── docs/                          # extra documentation
├── README.md                      # this file
└── README.ko.md                   # Korean version
```

Each plugin folder contains its own `.claude-plugin/plugin.json`, plus `agents/`, `commands/`, `skills/` as needed.

---

## ❓ FAQ

**Q: Do I need to install all 11 plugins?**
A: No. Install only what you need. `cs-ceo` alone covers most cases since it dispatches others on demand (you'll need them installed for the CEO to call them).

**Q: Does this cost extra?**
A: The plugins themselves are free (MIT). They run on your existing Claude Code subscription / API usage.

**Q: Will plugins update automatically?**
A: When the marketplace publishes a new version, Claude Code prompts you to update. You stay in control. For git-based installs, `git pull` inside the marketplace folder is enough.

**Q: I don't see the slash commands after installing.**
A: Restart Claude Code (Ctrl-C → `claude` again). New plugins load on startup.

**Q: How do I get the 70% token savings?**
A: Install [uv](https://docs.astral.sh/uv/) — the Python environment manager. One command: `brew install uv` (Mac) or `curl -LsSf https://astral.sh/uv/install.sh | sh`. No Python pre-install needed. The plugins auto-detect uv and use it; without it they fall back silently to LLM-based analysis.

**Q: Can I use `/cs-end`?**
A: `/cs-end` is designed for the plugin author. If you run it, Phase 4 (git push to the marketplace repo) is automatically skipped — your local session learnings are still saved normally. Use `--project /path/to/your/repo` to include your project's push status in the report.

**Q: Something is broken / I want to contribute.**
A: Open an issue or PR at [github.com/intenet1001-commits/CSnCompany_2-0](https://github.com/intenet1001-commits/CSnCompany_2-0).

**Q: Something is broken / I want to contribute.**
A: Open an issue or PR at [github.com/intenet1001-commits/CSnCompany_2-0](https://github.com/intenet1001-commits/CSnCompany_2-0).

---

## 📜 License

MIT — see [LICENSE](LICENSE).

## 🔗 Links

- [한국어 문서](./README.ko.md)
- [GitHub Repository](https://github.com/intenet1001-commits/CSnCompany_2-0)
- [Claude Code Documentation](https://docs.claude.com/en/docs/claude-code)
