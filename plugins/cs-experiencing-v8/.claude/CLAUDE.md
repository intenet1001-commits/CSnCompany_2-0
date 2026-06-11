# cs-experiencing - 경험 지식 저장소

이 플러그인은 누적된 학습 경험을 도메인별로 관리합니다.

**버전은 디렉토리명이 단일 진실** — `ls -d "$BASE/<도메인>-v"* | sort -V | tail -1`로 항상 최신을 해석한다.
도메인 개수·순서의 단일 진실은 `skills/experiencing/SKILL.md`의 캐노니컬 목록
(`test → plan → review → design → clarify → smart-run → ceo`)이다.

## 도메인 구성

| 도메인 | 현재 버전 | 내용 |
|--------|-----------|------|
| **CS-test** | CS-test-v* (latest via sort -V) | 웹 테스트 (14-agent playwright 팀) |
| **CS-plan** | CS-plan-v* (latest via sort -V) | TDD+CleanArch 플랜 (4-agent: domain-analyst, arch-designer, tdd-strategist, checklist-builder) |
| **CS-codebase-review** | CS-codebase-review-v* (latest via sort -V) | 5-관점 병렬 코드 리뷰 (Architecture/Quality/Security/Performance/Maintainability) |
| **cs-design** | cs-design-v* (latest via sort -V) | 5-관점 병렬 디자인 리뷰 (visual-hierarchy/interaction-quality/design-system-consistency/responsive-accessibility/anti-pattern-detector) |
| **cs-clarify** | cs-clarify-v* (latest via sort -V) | 요구사항 명료화 (4-agent: clarify-lead, requirements-interviewer, scope-validator, assumption-mapper) |
| **cs-smart-run** | cs-smart-run (VERSION 파일만, 디렉토리 suffix 없음) | Opus 플랜 + 병렬 Sonnet 실행 |
| **cs-ship** | cs-ship-v* (latest via sort -V) | PR 전 검증 게이트 (4-agent: ship-lead, pre-pr-validator, coverage-auditor, commit-crafter) |
| **cs-ceo** | cs-ceo-v* (latest via sort -V) | CS 시리즈 CEO 오케스트레이터 — 공수 추정 후 도메인 자율 배분 + cs-smart-run 자율 선택 |

## 사용법

```
/cs-experiencing                                          # 도메인 목록 및 버전 확인
/cs-experiencing test [URL]                               # CS-test 실행 (14개 에이전트로 웹 테스트)
/cs-experiencing plan [task]                              # CS-plan 실행
/cs-experiencing review [path] [--focus aspect]           # CS-codebase-review 실행 (5-관점 코드 리뷰)
/cs-experiencing design [path] [--focus aspect] [--fix]  # cs-design 실행 (5-관점 디자인 리뷰)
/cs-experiencing version-up test                          # CS-test 버전 업그레이드
/cs-experiencing version-up plan                          # CS-plan 버전 업그레이드
/cs-experiencing version-up review                        # CS-codebase-review 버전 업그레이드
/cs-experiencing version-up design                        # cs-design 버전 업그레이드
/cs-experiencing version-up clarify                       # cs-clarify 버전 업그레이드
/cs-experiencing version-up smart-run                     # cs-smart-run VERSION 증가
/cs-experiencing version-up ceo                           # cs-ceo 버전 업그레이드
/cs-experiencing version-up all                           # 캐노니컬 7개 도메인 한번에 버전업 (SKILL.md 목록 참조)
/cs-clarify "[요청]"                                      # 요구사항 명료화 (플랜 전)
/cs-ship                                                  # PR 전 최종 검증 게이트
/cs-experiencing btw "[아이디어]"                         # [v4] 세션 중 개선 아이디어 캡처
/cs-experiencing checkpoint                               # [v4] WIP 체크포인트 커밋
```

## 버전 관리

각 도메인의 VERSION 파일이 현재 콘텐츠 버전을 나타냅니다.
새 학습이 추가되면 `/cs-experiencing version-up [domain]` 으로 버전 증가.

## 도메인 파일 구조

도메인들은 cs-experiencing-v*과 같은 레벨의 plugins/ 디렉토리에 위치합니다
(버전 숫자는 하드코딩하지 않음 — 디렉토리명 sort -V가 단일 진실):

```
plugins/
├── cs-experiencing-v*/    ← 이 플러그인 (오케스트레이터)
│   └── skills/experiencing/
│       ├── SKILL.md       # 학습 INDEX + 오케스트레이터 도메인 학습 (인라인)
│       └── knowledge/     # 프로젝트-특화 학습 (topic별 .md 파일)
├── CS-test-v*/
│   ├── VERSION
│   ├── agents/            # 14개 테스트 에이전트
│   ├── skills/CS-test/SKILL.md
│   └── commands/CS-test.md
├── CS-plan-v*/
│   ├── VERSION
│   ├── agents/            # 4개: domain-analyst, arch-designer, tdd-strategist, checklist-builder
│   ├── commands/CS-plan.md
│   ├── knowledge/README.md
│   └── skills/CS-plan/SKILL.md
├── CS-codebase-review-v*/
│   ├── VERSION
│   ├── skills/CS-codebase-review/SKILL.md
│   └── commands/CS-codebase-review.md
├── cs-design-v*/
│   ├── VERSION
│   ├── agents/design-lead.md
│   ├── commands/cs-design.md
│   ├── references/        # typography, color-contrast, spacing-layout, interaction-states, anti-patterns
│   └── skills/cs-design/SKILL.md
├── cs-clarify-v*/
├── cs-smart-run/          # 디렉토리 버전 suffix 없음 — VERSION 파일만
└── cs-ceo-v*/
```
