# 멀티에이전트 오케스트레이션 (벤치마크: CrewAI · AutoGen · ChatDev)

CS 마켓플레이스를 3개 대표 프레임워크와 벤치마크해 이식한 오케스트레이션 지식.
전체 규약은 `plugins/shared/ORCHESTRATION-PATTERNS.md`(P1~P5) +
`plugins/shared/chains/`(선언적 매니페스트) + `plugins/shared/agents/AGENT-PERSONA-CONTRACT.md`.

## 프레임워크별 핵심 (근거와 함께)

### CrewAI — role-goal-backstory 페르소나 + 태스크 계약
- Agent = `role`(전문성) + `goal`(단일 결과) + `backstory`(맥락/방법론). 셋이 합쳐 일관된 페르소나.
  근거: docs.crewai.com/concepts/agents. 안티패턴: 모호한 role("Developer")은 책임 중첩.
- Task = `description` + `expected_output`(완료 형태, 필수) + `context`(의존 태스크 산출물 주입) +
  `guardrail`(출력 검증, `guardrail_max_retries`=3). Process: sequential(순차 컨텍스트 전달) /
  hierarchical(manager_llm이 동적 위임).
- **이식(P5)**: CS 에이전트는 이미 role+OWNS 계약 보유 → goal/backstory/expected_output/guardrail
  표준화. 한계: CrewAI는 Pydantic 코드 검증, CS는 LLM 재프롬프트 검증(+ Python pre-pass가 결정적 층).

### AutoGen — 동적 화자 선택 + 조합 가능한 종료
- GroupChat + GroupChatManager: `speaker_selection_method` = auto(매니저 LLM이 지명) / round_robin /
  manual / custom callable / `allowed_speaker_transitions_dict`(StateFlow 상태 기계).
  근거: microsoft.github.io/autogen 0.2 groupchat.
- Termination: `MaxMessageTermination`, `TextMentionTermination`(센티넬), `SourceMatchTermination`,
  `FunctionalTermination` 등을 `&`/`|`로 결합. 근거: autogen agentchat termination.
- conversation-as-primitive: `initiate_chat` 턴 루프. 이벤트 코어(autogen-core): RoutedAgent +
  `@message_handler`, pub/sub(topic/subscription) vs direct send.
- **이식(P1/P2)**: 리드 = GroupChatManager. 정적 fan-out → 조건부 상태 기계(transition table) +
  종료식 선언. 프롬프트 기반 한계: 네이티브 peer-to-peer/pub-sub 없음 → 리드가 메시지 라우터로 근사.

### ChatDev — 선언적 체인 + instructor↔assistant 역할극 루프
- ChatChainConfig.json `chain[]`: 워터폴 SDLC를 배열 순서로 실행. entry = `{phase, phaseType:
  Simple|Composed, cycleNum, need_reflect}`. 근거: OpenBMB/ChatDev v1.1.6.
- PhaseConfig: `{assistant_role(실행자), user_role(지시자), phase_prompt}`. role_playing.py가 phase마다
  2-에이전트(instructor↔assistant) inception 대화, `<INFO>` 토큰으로 자기 종료.
- ComposedPhase(CodeReview cycleNum=3, CodeComplete=10, Test=3): `for i in range(cycleNum)` 루프,
  `break_cycle`로 조기 종료(리뷰어 "<INFO> Finished" / 버그 없음). ChatEnv(전역) ↔ phase_env(지역)로
  phase 간 컨텍스트 전달(update_phase_env/update_chat_env).
- **이식(P3/P4)**: chain 매니페스트(shared/chains/) + reviewer↔fixer 역할극 루프(cycleNum 하드 캡 +
  센티넬 종료). 주의: main 브랜치는 graph-node 구조로 재작성됨 — 이식한 건 v1.x 클래식 chat-chain.

## CS 적용 요약 (무엇이 바뀌었나)

| 갭 (이식 전) | 패턴 | 적용 리드 |
|-------------|------|----------|
| 정적 고정 순서만 (조건부 분기 없음) | P1 speaker selection + transition table | cs-ceo Mode D |
| round 카운터만 (조건 종료 없음) | P2 종료식 (max_turns \| sentinel \| no_delta ...) | ceo/smart-run/experiencing |
| 파이프라인이 산문에 하드코딩 | P3 선언적 chain 매니페스트 | cs-ceo Mode D, experiencing-lead |
| 워커 단독 산출 + 사후 검증만 | P4 instructor↔assistant 실시간 역할극 루프 | smart-run, review(composed) |
| goal/backstory/expected_output 비표준 | P5 페르소나+출력 계약 | 전 워커 (점진 적용) |

## 판단 기준 (언제 켜나)

- 정적 fan-out(모드 A/B)으로 충분하면 **켜지 않는다** — Karpathy Simplicity First. 억지 적용은 오버헤드.
- 3개+ 도메인이 순서·의존·조건부·재작업 루프로 얽힐 때만 Mode D + chain 매니페스트.
- 코드 수정 역할극 루프(P4 composed)는 opt-in — 사용자 승인/--fix 컨텍스트에서만 자율 패치.
