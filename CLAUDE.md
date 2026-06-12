## Skill routing

When the user's request matches an available skill, ALWAYS invoke it using the Skill
tool as your FIRST action. Do NOT answer directly, do NOT use other tools first.
The skill has specialized workflows that produce better results than ad-hoc answers.
Exception — if the request is a single-fact check or touches ≤1 file/page (answerable
with 1-3 direct tool calls), answer directly with Bash/Read instead of launching a
multi-agent skill, and state in one line why the pipeline was skipped. When in doubt
about scope, ask one short question before routing.

Key routing rules:
- Web testing, playwright, site QA, find bugs on a URL → invoke CS-test
- TDD plan, clean architecture plan, coding plan for a feature → invoke CS-plan
- Codebase review, architecture review, code quality check → invoke CS-codebase-review
- Design review, UI audit, UX analysis, 디자인 리뷰 → invoke cs-design
- Crextio style components, --audit/--apply design file → invoke cs-design-sample1
- Requirements unclear, 요구사항 정리, 스펙 명확화 → invoke cs-clarify
- Session ending, 세션 마무리, 오늘 작업 끝내자 → invoke cs-end
- Error capture, 에러 저장, 에러노트 → invoke cs-error-notes
- Know-how lookup, 이전 학습, 경험 조회 → invoke cs-experiencing
- Pre-PR validation, 배포 전 검증, ship, create PR → invoke cs-ship
- Opus plan + parallel Sonnet execution, 플랜실행 → invoke smart-run
- English conversation, session to dialog → invoke convo-maker
- Complex multi-step task, 목표 설정, unsure which domain, /goal → invoke cs-ceo
