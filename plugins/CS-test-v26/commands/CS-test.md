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
/CS-test --hitl=auto http://localhost:3000   # 무인 실행 — build-blocker 체크포인트에서 묻지 않음
```

## 옵션

| 옵션 | 설명 | 기본값 |
|------|------|--------|
| `--hitl` | HITL 모드: `auto`(중간 질문 없음 — 빌드 F여도 default로 전체 테스트 진행) / `gate`(build-blocker 체크포인트에서 continue/Quick/abort 질문) / `always`(모든 Phase 전환마다 확인). `--auto`는 `--hitl=auto` 별칭. plugins/shared/HITL-POLICY.md 참조 | `gate` |

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
