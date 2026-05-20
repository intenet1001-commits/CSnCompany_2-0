## Skill routing

When the user's request matches an available skill, ALWAYS invoke it using the Skill
tool as your FIRST action. Do NOT answer directly, do NOT use other tools first.
The skill has specialized workflows that produce better results than ad-hoc answers.

Key routing rules:
- Web testing, playwright, site QA, find bugs on a URL → invoke CS-test
- TDD plan, clean architecture plan, coding plan for a feature → invoke CS-plan
- Codebase review, architecture review, code quality check → invoke CS-codebase-review
- Design review, UI audit, UX analysis, 디자인 리뷰, anti-pattern detection → invoke cs-design
- Sync plugins, push to GitHub, update marketplace → invoke cs-sync
- Complex multi-step task, plan then execute in parallel → invoke smart-run
- English conversation, convert session to dialog → invoke convo-maker
- Product ideas, "is this worth building", brainstorming → invoke office-hours
- Bugs, errors, "why is this broken" → invoke investigate
- Ship, deploy, push, create PR → invoke ship
- Code review, check my diff → invoke review
- Architecture review, plan review → invoke plan-eng-review
- Save progress, checkpoint, resume → invoke checkpoint
- "목표", complex multi-step task, unsure which domain, /goal → invoke cs-ceo
- Complex task routing, effort estimation, domain dispatch → invoke cs-ceo
- Error capture, error note, 에러노트, 에러 기록, 오류 정리 → invoke cs-error-notes
