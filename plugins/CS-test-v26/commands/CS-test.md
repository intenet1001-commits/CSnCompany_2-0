---
description: "CS-test 도메인 웹 테스트 실행 - 15개 AI 에이전트 팀 (playwright-test-v5 기반)"
allowed-tools: Bash, Read, Write, Edit, Glob, Grep, Task, ToolSearch, TaskCreate, TaskUpdate, TaskList, TaskGet, TeamCreate, TeamDelete, SendMessage
---

# /CS-test [url]

CS-test 도메인의 15-agent AI Teams 웹 테스트를 실행합니다.

## 사용법

```
/CS-test https://example.com
/CS-test http://localhost:3000
```

## 에이전트 팀 (15개)

1. build-validator, 2. test-lead, 3. page-explorer,
4. functional-tester, 5. visual-inspector, 6. api-interceptor,
7. perf-auditor, 8. social-share-auditor, 9. db-validator,
10. touch-interaction-validator, 11. image-optimizer,
12. security-auditor, 13. seo-auditor, 14. error-resilience,
15. finding-verifier

## 현재 버전

VERSION 파일 참조: `${CLAUDE_PLUGIN_ROOT}/VERSION`

## 실행

`${CLAUDE_PLUGIN_ROOT}/skills/CS-test/SKILL.md` 프로토콜을 따릅니다.
