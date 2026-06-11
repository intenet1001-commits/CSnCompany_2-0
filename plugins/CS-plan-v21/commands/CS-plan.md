---
description: "TDD + Clean Architecture 기반 즉시 실행 가능한 코딩 플랜을 자동 생성합니다 - 4개 전문 에이전트가 도메인 분석, 아키텍처, 테스트 전략, 구현 체크리스트를 병렬로 생성"
allowed-tools: Bash, Read, Write, Edit, Glob, Grep, Task, TaskCreate, TaskUpdate, TaskList, TaskGet, TeamCreate, TeamDelete, SendMessage
---

# /CS-plan [기능 설명]

TDD + Clean Architecture 기반의 즉시 실행 가능한 코딩 플랜을 자동 생성합니다.

## 사용법

```
/CS-plan "기능 설명"
/CS-plan --lang typescript "기능 설명"
/CS-plan --output docs/plans "기능 설명"
/CS-plan --lang python --output src/plans "기능 설명"
```

## 옵션

| 옵션 | 설명 | 기본값 |
|------|------|--------|
| `--lang` | 구현 언어 (typescript, python, java, go, kotlin 등) | 자동 감지 |
| `--output` | 플랜 저장 디렉토리 | `.tdd-plans` |

## 예시

```bash
/CS-plan "사용자 인증 시스템 (이메일+비밀번호, JWT)"
/CS-plan --lang typescript "장바구니 도메인"
/CS-plan --output docs/plans "결제 처리 유스케이스"
/CS-plan --lang python --output plans "이메일 발송 서비스"
```

## 에이전트 팀 구성

4개의 전문 Claude AI 에이전트가 병렬로 플랜을 생성합니다:

1. **domain-analyst** - DDD 기반 도메인 분석 (Aggregate, Entity, Value Object, Bounded Context)
2. **arch-designer** - Clean Architecture 레이어 설계 (4레이어 + SOLID + 인터페이스)
3. **tdd-strategist** - TDD 테스트 케이스 전략 (Red-Green-Refactor, Given/When/Then)
4. **checklist-builder** - 레이어별 구현 체크리스트 (Inside-Out 순서, Definition of Done)

## 출력 파일

```
.tdd-plans/                        (기본값, --output으로 변경 가능)
├── domain-analysis.md             ← 도메인 엔티티, 유스케이스, 액터, 경계
├── architecture.md                ← Clean Architecture 레이어 구조 + 인터페이스
├── tdd-strategy.md                ← 테스트 케이스 순서 + Given/When/Then
├── implementation-checklist.md   ← 레이어별 Red-Green-Refactor 체크박스
└── PLAN.md                        ← 종합 플랜 (빠른 시작 가이드 포함)
```

## 참고

자세한 실행 프로토콜은 `skills/CS-plan/SKILL.md`를 참조하세요 (`${CLAUDE_PLUGIN_ROOT}/skills/CS-plan/SKILL.md`).
각 에이전트의 동작 정의는 `agents/*.md` 파일에 명시되어 있습니다 (`${CLAUDE_PLUGIN_ROOT}/agents/*.md`).
