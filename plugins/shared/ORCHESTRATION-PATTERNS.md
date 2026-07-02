# ORCHESTRATION-PATTERNS — CS 멀티에이전트 오케스트레이션 패턴 (벤치마크 이식)

CrewAI · AutoGen · ChatDev 3개 프레임워크의 멀티에이전트 아키텍처를 벤치마크하여
CS 마켓플레이스(프롬프트 기반 리드-에이전트 오케스트레이션)에 이식한 5가지 재사용 패턴이다.

**적용 대상**: 서브에이전트를 스폰하는 모든 CS 리드(cs-ceo, cs-smart-run, experiencing-lead,
test-lead, plan-lead, design-lead, review, ship-lead).
**관계**: 이 문서는 LOOP-PROTOCOL(증거·경계·커버리지)을 **대체하지 않고 확장한다**.
LOOP-PROTOCOL이 "루프를 어떻게 안전하게 도는가"라면, 이 문서는 "누가 언제 말하고,
언제 멈추고, 파이프라인을 어떻게 선언하는가"를 다룬다.

참조 방법(리드 파일에 한 줄): `오케스트레이션 확장: 다중 도메인/조건부 흐름/역할극 루프가 필요하면
plugins/shared/ORCHESTRATION-PATTERNS.md의 P1~P5를 적용한다 (LOOP-PROTOCOL 위에 얹는다).`
(런타임 경로는 `${CLAUDE_PLUGIN_ROOT}/../shared/`로 해석한다.)

---

## 벤치마크 요약 (무엇을 이식했나)

| 프레임워크 | 핵심 강점 | 이식 패턴 | 근거 |
|-----------|----------|----------|------|
| **AutoGen** (GroupChat) | 동적 speaker selection — 다음 화자를 매 턴 선택 (auto/round_robin/manual/transition-table) | **P1 Speaker Selection** | `GroupChat(speaker_selection_method=...)`, `allowed_speaker_transitions_dict` (StateFlow) — microsoft.github.io/autogen 0.2 groupchat |
| **AutoGen** (Termination) | 조합 가능한 종료 조건 — max-msg \| sentinel \| source-match \| custom, AND/OR 결합 | **P2 Termination Conditions** | `MaxMessageTermination`, `TextMentionTermination`, `max &amp; text` / `max \| text` — autogen agentchat termination |
| **ChatDev** (ChatChain) | 선언적 파이프라인 매니페스트 — `chain[]`을 위→아래로 실행, SimplePhase/ComposedPhase | **P3 Declarative Chain Manifest** | `ChatChainConfig.json`의 `chain[]` + `phaseType` + `cycleNum` (v1.1.6) |
| **ChatDev** (role_playing) | instructor↔assistant 2-에이전트 역할극 + inception + `<INFO>` 종료 토큰 | **P4 Instructor-Assistant Role-Play** | `camel/agents/role_playing.py`, CodeReview ComposedPhase(`cycleNum=3`, break on `<INFO> Finished`) |
| **CrewAI** (Agent+Task) | role-goal-backstory 페르소나 + expected_output 태스크 계약 + guardrail | **P5 Persona & Output Contract** | `Agent(role/goal/backstory)`, `Task(expected_output/context/guardrail)` — docs.crewai.com |

**설계 원칙**: 정적 fan-out(리드→고정 로스터 병렬→취합→등급)은 CS의 기본값으로 유지한다.
이 패턴들은 **정적 파이프라인으로 부족할 때만** 켜는 확장이다 — 항상 켜면 Karpathy Simplicity First 위반.

---

## P1 — SPEAKER SELECTION (동적 화자 선택)

**출처**: AutoGen `GroupChat.speaker_selection_method`.
**문제**: CS 리드는 고정 순서(prose)로 에이전트를 스폰한다. 조건에 따라 "다음에 누가"를
바꿀 방법이 없다.
**이식**: 리드 = GroupChatManager. 다음 화자 선택 정책을 4가지 중에서 고른다.

| 모드 | 의미 | CS 구현 |
|------|------|---------|
| `parallel` (기본) | 독립 에이전트 동시 스폰 | 단일 응답 블록 fan-out (현행 유지) |
| `round_robin` | 로스터를 정해진 순서로 1개씩 | 순차 Task 스폰, 이전 결과를 다음 프롬프트에 전달 |
| `auto` | 리드 LLM이 transcript를 읽고 다음 에이전트를 지명 | 리드가 직전 출력의 미해결 항목을 보고 담당 에이전트 1개 선택 |
| `manual` | 사람이 선택 | AskUserQuestion 1회로 다음 단계 선택 |

**Transition Table (StateFlow)** — 조건부 상태 기계. 정적 순서 대신 "각 화자 다음에 허용되는 화자"를 선언한다:

```
transitions:
  start        -> [explorer]
  explorer     -> [reviewer, tester]      # 병렬 분기
  reviewer     -> [fixer | DONE]          # HIGH 있으면 fixer, 없으면 종료
  fixer        -> [reviewer]              # 재검증으로 되돌아감 (루프)
  tester       -> [DONE]
```

리드는 이 표를 프롬프트 내부 상태로 들고, 각 에이전트 결과를 받은 뒤 표를 참조해 다음 화자를 정한다.
이것이 "정적 파이프라인 → 조건부 루프 있는 상태 기계"로의 전환이다.

**선택 근거를 한 줄 출력한다**: `speaker-selection: auto — reviewer가 HIGH 2건 보고 → fixer 지명`.
**언제 켜나**: 도메인 결과가 다음 단계 분기를 결정할 때(조건부), 또는 재작업 루프가 필요할 때.
단순 독립 병렬이면 `parallel` 기본값을 그대로 쓴다.

---

## P2 — TERMINATION CONDITIONS (조합 가능한 종료 조건)

**출처**: AutoGen `TerminationCondition` (Max/Text/Timeout/SourceMatch/Functional) + `&amp;`/`|` 결합.
**문제**: CS의 종료는 "round > N" 카운터뿐이다. 조건 기반 조기 종료(예: 리뷰어가 '만족'
신호를 내면 즉시 종료)가 없다.
**이식**: 루프 진입 전에 **종료 조건 객체**를 선언하고, 매 턴 후 평가한다.

원자 종료 조건 (택1 이상):

| 조건 | 트리거 | LOOP-PROTOCOL 연계 |
|------|--------|-------------------|
| `max_turns(N)` | N턴 도달 | [c] BOUNDED LOOP round budget과 동일 — 항상 포함(하드 캡) |
| `sentinel(TOKEN)` | 에이전트 출력에 정지 토큰 등장 (예: `<DONE>`, `<INFO> Finished`, `NO DEFECTS`) | 조기 종료 |
| `no_delta` | 한 라운드가 새 수정/새 PASS를 못 만듦 | [c] "델타 없으면 즉시 중단" |
| `source_match(agent)` | 특정 에이전트가 발언 완료 (예: verifier가 PASS 판정) | 게이트 통과 |
| `grade_reached(≥B)` | 목표 등급 도달 | [b] SUCCESS CRITERIA |

**결합**: `OR`(어느 하나라도 → 종료), `AND`(모두 만족해야 → 종료).
- 기본 종료식: `max_turns(N) OR sentinel OR no_delta` — 항상 이 3개를 최소로 결합한다.
- 예: `max_turns(3) OR sentinel(<DONE>) OR no_delta` — ChatDev CodeReview(`cycleNum=3` + break on `<INFO> Finished`)와 동형.

**선언 의무**: fan-out/루프 진입 전에 종료식을 한 줄 출력한다:
`termination: max_turns(3) OR sentinel(<DONE>) OR no_delta`.
루프 종료 시 어떤 조건이 발화했는지 기록한다: `종료: sentinel(<DONE>) @ round 2`.

---

## P3 — DECLARATIVE CHAIN MANIFEST (선언적 파이프라인 매니페스트)

**출처**: ChatDev `ChatChainConfig.json`의 `chain[]` (`phase`, `phaseType`, `cycleNum`).
**문제**: 파이프라인 순서가 각 리드의 산문에 하드코딩돼 재사용/조합이 안 된다.
(experiencing-lead의 "Pipeline Decision Matrix"가 대표적 — 매트릭스가 코드가 아니라 표다.)
**이식**: 파이프라인을 **JSON 매니페스트**로 선언하고, 리드가 위→아래로 walk하며 각 phase를
Task로 디스패치한다. 스키마와 예제는 `plugins/shared/chains/`.

핵심 스키마 (전체는 `chains/CHAIN-SCHEMA.md`):

```json
{
  "chain": [
    { "phase": "explore",  "domain": "CS-codebase-review", "phaseType": "simple" },
    { "phase": "plan",     "domain": "CS-plan",            "phaseType": "simple",
      "inputs": ["explore.report"] },
    { "phase": "review",   "domain": "CS-codebase-review", "phaseType": "composed",
      "cycleNum": 3, "instructor": "reviewer", "assistant": "fixer",
      "break_on": "<INFO> Finished" }
  ]
}
```

- `phaseType: "simple"` → 1회 디스패치 (SimplePhase).
- `phaseType: "composed"` → P4 역할극 루프를 `cycleNum` 만큼 반복, `break_on` 센티넬로 조기 종료 (P2).
- `inputs` → 이전 phase의 산출물을 이 phase 프롬프트에 주입 (CrewAI Task `context` = ChatDev `update_phase_env`).

**환경 전달 규약** (ChatDev ChatEnv): phase는 실행 전 지정된 `inputs`를 읽어(gather) 프롬프트에
넣고, 실행 후 산출 아티팩트(리포트/PLAN.md 등)를 다음 phase가 읽을 수 있게 남긴다(write-back).
공유 컨텍스트 = 런 스코프 아티팩트 파일(기존 `PLAN.md`, `tests/results/REPORT.md` 등 재사용).

**언제 켜나**: 3개 이상 도메인이 순서/의존으로 얽힐 때. 1~2 도메인이면 매니페스트 없이 직접 스폰.

---

## P4 — INSTRUCTOR-ASSISTANT ROLE-PLAY (역할극 리뷰 루프)

**출처**: ChatDev `role_playing.py` (2-에이전트 inception) + CodeReview ComposedPhase.
**문제**: CS 워커는 단독으로 산출물을 낸 뒤 verifier가 사후 반박한다. "지시자↔실행자"가
쌍으로 대화하며 수렴하는 구조(리뷰어가 지적 → 실행자가 수정 → 재리뷰)가 없다.
**이식**: 한 phase를 **2개의 캐릭터 고정(character-locked) 에이전트**로 구성한다.

- **instructor** (user_role): 지시/평가만 한다. 예: CS-codebase-review 리뷰어 — 최우선 이슈 1개를
  근거와 함께 제시 (한 번에 전부가 아니라 가장 중요한 것부터, ChatDev "one highest-priority comment").
- **assistant** (assistant_role): 실행/수정만 한다. 예: fixer/executor — 지시받은 항목만 패치.
- **루프**: `for i in range(cycleNum)`: instructor 지시 → assistant 수정 → instructor 재평가.
  **종료 (P2)**: `max_turns(cycleNum) OR sentinel(<INFO> Finished / <DONE>) OR no_delta`.
- **inception (캐릭터 고정)**: 각 에이전트 프롬프트는 역할·목표를 고정하고 상대 역할을 명시한다
  ("당신은 리뷰어다. 실행자에게 지시만 하고 직접 코드를 쓰지 않는다"). 역할 이탈을 막는다.

**cycleNum 상한 (ChatDev 기본값 기반, 하드 캡)**: 리뷰/수정 루프 = **3**, 완성 루프 = **10**,
테스트/수정 루프 = **3**. LOOP-PROTOCOL [c]의 2-3라운드와 정합.

**dehallucination (환각 억제)**: 산출자와 검증자를 분리하고 역할을 교차시켜 자기 동의(self-agreement)를
막는다. CS의 verifier(refuter)가 이미 사후 분리를 하지만, P4는 이를 **루프 내부의 실시간 지시자**로
끌어올린다. 단 — 이 루프는 opt-in이다: 코드 수정 에이전트를 자율 투입하는 것은 사용자/기존
opt-in 메커니즘(cs-design --fix, cs-ship 등)의 범위 안에서만 한다 (experiencing-lead Phase 2 경계 준수).

**worked example (review-fix)**:
```
instructor(reviewer): "src/auth.ts:42 — 비밀번호 평문 로깅. [HIGH] 근거: `console.log(pw)`. 이것만 고쳐라."
assistant(fixer): "src/auth.ts:42 수정 — 로깅 제거. diff 첨부."
instructor(reviewer): 재확인 → 통과 → "<INFO> Finished" (또는 다음 최우선 이슈)
→ sentinel 발화 → 루프 종료
```

---

## P5 — PERSONA & OUTPUT CONTRACT (페르소나 + 출력 계약)

**출처**: CrewAI `Agent(role, goal, backstory)` + `Task(expected_output, context, guardrail)`.
**문제**: CS 에이전트는 role(제목)과 OWNS 계약은 있으나 goal/backstory/expected_output이
표준화돼 있지 않다. 모호한 역할("Developer" vs "Senior React Developer")은 책임 중첩을 만든다.
**이식**: 에이전트 정의와 태스크 디스패치에 아래 계약을 표준으로 얹는다.
전체 규약은 `plugins/shared/agents/AGENT-PERSONA-CONTRACT.md`.

**에이전트 페르소나 (agents/*.md 상단)**:
- `role` — 구체적 전문성 ("보안 리뷰어" 말고 "HTTP 헤더·쿠키·인젝션 전문 보안 리뷰어").
- `goal` — 이 에이전트가 향하는 단일 결과.
- `backstory` — 방법론/지식 (기존 본문이 이미 이 역할을 함 — 명시적으로 라벨링).
- `📌 OWNS / ❌ DOES NOT OWN` — 소유권 경계 (기존 유지).

**태스크 계약 (리드가 디스패치할 때)**:
- `expected_output` — "완료가 어떤 모습인지" 명시 (CrewAI 필수 필드). 예: "JSON 배열, 각 원소는
  `{finding, severity, confidence, evidence}`". 모호한 "분석해라" 금지.
- `context` — 주입할 이전 산출물 (P3 `inputs`와 동일).
- `guardrail` — 출력 검증 조건. 실패 시 재프롬프트 (CrewAI `guardrail_max_retries`≈ P2 max_turns).

**한계 (정직하게)**: CrewAI는 Pydantic으로 출력을 **코드 검증**한다. CS는 프롬프트 기반이라
**LLM 검증(재프롬프트)**만 가능하다 — 런타임 타입 강제는 없다. 결정적 검증이 필요한 곳은
기존 Python pre-pass 스크립트(abspath_check/ts_rust_diff)를 계속 쓴다.

---

## 적용 매트릭스 (리드별 우선 패턴)

| 리드 | 우선 패턴 | 적용 지점 |
|------|----------|----------|
| **cs-ceo** | P1, P2, P3 | Mode D(Dynamic Chain) — 다중 도메인 시 매니페스트 walk + speaker selection |
| **cs-smart-run** | P2, P4 | EXEC의 verify→fix를 instructor-assistant 루프 + 종료식으로 정식화 |
| **experiencing-lead** | P2, P3 | Pipeline Decision Matrix를 chain 매니페스트로, 재실행 루프에 종료식 |
| **test-lead / review / plan-lead** | P5 | 워커 페르소나 + expected_output 계약 강화 (fan-out은 유지) |
| **review (composed)** | P4 | reviewer→fixer 루프 (opt-in) |

**정직성 규칙**: 이 패턴들은 도구가 아니라 **선택지**다. 정적 fan-out으로 충분한 태스크에
P1~P4를 억지로 켜면 오버헤드다. 리드는 켠 패턴과 그 근거를 리포트 헤더에 한 줄로 기록한다:
`orchestration: P3 chain(review-fix) + P4 loop(cycleNum=3) — 다중 도메인 재작업 필요`.
