---
name: convo-maker
description: Use this skill when the user types "/convo-maker", "/convo", "make conversation", "영어 대화 만들어", "미국식 영어", "native english dialog", "session to english", "대화로 만들어", or wants to convert current session Q&A into natural American English conversations.
user-invocable: true
---

# ConvoMaker - Session to American English Conversation

> Transform your session Q&A into natural, native-sounding American English dialogues

## What This Skill Does

Scans the **current session's conversation history** — your questions and Claude's answers — and rewrites them as a realistic dialogue between two Americans (Alex and Jamie). The output sounds like real casual or professional conversation, not textbook English.

---

## Protocol

### Step 1: Extract Session Q&A

Review the conversation so far in this session. Identify:
- **User questions/statements** (the topics discussed)
- **Claude's key answers** (the core information)

Skip meta-talk (greetings, "sure!", "of course!" etc.) and focus on **substantive exchanges**.

### Step 2: Build Natural American Dialogue

For each Q&A pair, rewrite as a conversation between **Alex** (the asker) and **Jamie** (the knowledgeable friend). Apply these rules:

**Language Style Rules:**
- Use contractions always: "I'm", "it's", "you've", "that's", "gonna", "wanna", "kinda"
- Add filler phrases naturally: "So basically...", "Here's the thing...", "Honestly...", "I mean...", "Right, so...", "Yeah, like..."
- Use American idioms where natural: "heads up", "figure out", "run into", "on the same page", "no big deal", "makes sense"
- Keep sentences short and punchy — Americans don't speak in paragraphs
- Add back-and-forth reactions: "Oh interesting!", "Wait, really?", "That makes sense.", "Gotcha.", "Huh, never thought of it that way."
- Use rhetorical questions: "You know what I mean?", "Right?", "Make sense?"
- Technical terms are fine — just frame them conversationally

**Tone Options** (choose based on topic):
- **Casual**: Friends chatting over coffee
- **Professional**: Colleagues discussing at work
- **Curious**: One person genuinely learning from another

### Step 3: Format Output

Output the conversation in this format:

---

## Conversation: [Topic Title]

**Setting**: [1-line scene description — where/when/why they're talking]

---

**Alex**: [Opening line that naturally introduces the topic]

**Jamie**: [Response with key information, conversational tone]

**Alex**: [Follow-up question or reaction]

**Jamie**: [Deeper explanation or example]

**Alex**: [Clarifying question or "aha" moment]

**Jamie**: [Wrap-up with practical tip or summary]

---

### Vocabulary Highlights
| Expression | Meaning | Example from conversation |
|------------|---------|--------------------------|
| [phrase used] | [plain English meaning] | [quote from above] |

### Why This Sounds American
- [1-2 notes on specific choices made — idioms used, contractions, etc.]

### Step 4: Self-Check Before Saving

Before saving to Obsidian, re-read the drafted dialogue and verify every item:

- [ ] No textbook connectors anywhere ("Furthermore", "Moreover", "It is important to note", "In conclusion", "Additionally") — if found, rewrite that line in spoken register
- [ ] Contractions used throughout — no uncontracted "I am", "it is", "do not" in dialogue lines
- [ ] 6–10 exchanges per topic — trim padding or add a natural follow-up if outside range
- [ ] Every fact in the dialogue traces to something actually discussed in this session — delete invented details
- [ ] Every Vocabulary Highlights entry quotes a phrase that literally appears in the dialogue above — fix the table or the dialogue so they match

Rewrite any failing lines, then re-check the rewritten lines once. Only after all items pass, proceed to the auto-save in Rule 5.

---

## Example Output

If the session covered "How does TypeScript help with bugs?":

---

**Setting**: Two dev friends catching up at a coffee shop after work.

---

**Alex**: Hey, so I keep hearing about TypeScript. Like, is it actually worth switching from plain JavaScript?

**Jamie**: Oh man, honestly? Yeah, it's totally worth it — especially if you're working on anything bigger than a side project. Here's the thing: TypeScript basically catches your bugs *before* you even run the code.

**Alex**: Wait, what do you mean before you run it?

**Jamie**: So you know how in regular JS you can just pass whatever into a function and it won't complain until it blows up in production? TypeScript won't even let you do that. It flags it right in your editor.

**Alex**: Oh, so it's like... a spellcheck but for your logic?

**Jamie**: Exactly! That's a great way to put it. It's like having a really picky coworker who catches all your typos before the code ships. Kinda annoying at first, but you get used to it fast.

**Alex**: Huh. And the learning curve — is it rough?

**Jamie**: Not really. If you already know JS, you're probably looking at a week or two before it clicks. I'd say just start with one file, add types gradually. No need to go all in from day one.

---

### Vocabulary Highlights
| Expression | Meaning | Example |
|------------|---------|---------|
| "blows up in production" | causes an error when real users run it | "...it won't complain until it blows up in production" |
| "go all in" | commit completely from the start | "No need to go all in from day one." |
| "clicks" | suddenly makes sense / you understand it | "...before it clicks" |

### Why This Sounds American
- "Oh man" and "Exactly!" are natural American enthusiasm markers
- "Kinda annoying" softens criticism the way Americans typically do in conversation

---

## Rules

1. **Stay faithful to the content** — don't invent facts, just reframe what was actually discussed
2. **Multiple exchanges** — if the session covered multiple topics, create a separate conversation section for each
3. **Natural length** — 6–10 exchanges per topic is ideal; don't pad, don't cut too short
4. **No stiff language** — if you catch yourself writing "Furthermore" or "It is important to note", rewrite it
5. **Auto-save** — after generating and passing the Step 4 self-check, automatically save to `/Users/gwanli/CS_V7_eng/raw/` as a `.md` file. File name format: `convo_YYYY-MM-DD_[Topic].md` (e.g., `convo_2026-04-05_TypeScript.md`). Use today's date and the first topic title. Do not ask — just save silently and confirm with the file path at the end.

## Completion Signal

When the conversation is generated:
```
<promise>CONVO_MAKER_COMPLETE</promise>
```
