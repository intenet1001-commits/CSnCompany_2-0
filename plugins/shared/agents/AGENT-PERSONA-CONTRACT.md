# AGENT-PERSONA-CONTRACT — 에이전트 페르소나 + 출력 계약 (P5)

CrewAI `Agent(role, goal, backstory)` + `Task(expected_output, context, guardrail)`를 CS
마켓플레이스로 이식한 표준. ORCHESTRATION-PATTERNS.md P5의 구체 규약이다.

## 왜 필요한가

CrewAI 문서(docs.crewai.com): "role establishes specialized expertise, goal directs effort
toward specific outcomes, backstory provides contextual reasoning — collectively creating a
consistent behavioral persona." 안티패턴: 모호한 role("Developer")은 책임 중첩·잘못된 위임을
낳는다. CS 에이전트는 role과 OWNS 계약은 있으나 goal/backstory/expected_output이
표준화돼 있지 않다 → 이 문서로 표준화한다. **기존 파일을 깨지 않는 추가 규약**이다.

## 1. 에이전트 페르소나 (agents/*.md)

기존 frontmatter + 본문을 유지하되, 아래 4요소가 **명시적으로 식별 가능**해야 한다.
새 에이전트는 이 형태로 작성하고, 기존 에이전트는 버전업 시 점진 적용한다.

| 요소 | 위치 | 규칙 |
|------|------|------|
| **role** | frontmatter `name` + `description` 첫 구절 | 구체적 전문성. "리뷰어" ❌ → "HTTP 헤더·쿠키·인젝션 전문 보안 리뷰어" ✅ |
| **goal** | `description` 또는 본문 상단 1줄 | 단일 결과 지향. "이 에이전트는 [X]를 산출하기 위해 존재한다" |
| **backstory** | 본문 (방법론/지식 섹션) | 기존 지식 본문이 이 역할 — 라벨만 명확히 |
| **OWNS / DOES NOT OWN** | 본문 상단 📌/❌ | 소유권 경계 (기존 유지) |

예 (verifier.md는 이미 근접):
```
role:      공용 반박(refuter) 에이전트
goal:      critical/high finding을 재검증해 CONFIRMED/REFUTED/UNCERTAIN 판정
backstory: "확인이 아니라 반박이 기본 자세" + 검증 범위 규칙
OWNS:      finding 재검증 / ❌ DOES NOT OWN: 새 finding 발굴·수정
```

## 2. 태스크 계약 (리드가 디스패치할 때)

리드가 Task 프롬프트를 만들 때 아래를 포함한다 (CrewAI Task 필드 이식):

- **`expected_output` (필수)** — "완료가 어떤 모습인지"를 명시한다. CrewAI에서 필수 필드인 이유:
  이것이 없으면 에이전트가 "무엇을 반환해야 완료인지" 모른다.
  - ❌ "보안을 분석해라"
  - ✅ "JSON 배열 반환. 각 원소 `{file, line, severity, confidence, evidence, fix}`. 최소 reviewed_files 목록 포함."
- **`context` (선택)** — 주입할 이전 산출물 (P3 chain `inputs`와 동일 개념). 파일 경로 또는 요약.
- **`guardrail` (선택)** — 출력이 만족해야 할 검증 조건 1줄. 리드가 결과 수신 후 이 조건으로 검사하고,
  실패면 재프롬프트한다 (재시도 상한 = P2 `max_turns`, 기본 2). 예: "evidence 필드가 file:line 또는
  command+output 형식이 아니면 재작성 요구."

## 3. 기존 워커 공통 계약과의 관계

CS 리드들은 이미 워커에게 2줄 공통 계약을 주입한다(예: test-lead):
1. "첫 행동: Read agents/<name>.md"
2. "finding 보고 계약: 모든 finding을 severity+confidence+evidence와 함께 빠짐없이 보고 (LOOP-PROTOCOL [a][e])"

P5는 여기에 **3번째 줄**을 더한다:
3. "expected_output: <이 태스크의 완료 형태 1줄>. guardrail: <검증 조건>."

## 4. 한계 (정직성)

CrewAI는 `output_pydantic`으로 출력을 **코드 검증(타입 강제)**한다. CS는 프롬프트 기반이라
**LLM 검증(재프롬프트)**만 가능하다. 결정적 검증이 필요하면 기존 Python pre-pass 스크립트
(abspath_check.py, ts_rust_diff.py, extract_summary.py)를 계속 사용한다 — 이것이 CS의
"코드 검증" 레이어다.
