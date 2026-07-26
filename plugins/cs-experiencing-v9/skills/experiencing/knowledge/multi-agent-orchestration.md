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

### 89. 멀티에이전트 오케스트레이션 벤치마크 — CrewAI/AutoGen/ChatDev → P1~P5 이식 (2026-07-02)
<!-- tier: principle -->
- **본문**: 이 파일 상단의 프레임워크별 핵심 정리(CrewAI/AutoGen/ChatDev)가 INDEX #89의 본문이다.
  전체 규약은 `plugins/shared/ORCHESTRATION-PATTERNS.md`(P1~P5) 참조.

### 118. N개 서브에이전트의 합의는 진실이 아니다 — 각자 참인 국소 관찰이 거짓 전역 주장으로 굳는다 (2026-07-16)
<!-- tier: principle -->

- **상황**: Figma 파일 NDS_CI를 6개 배치로 나눠 13페이지를 병렬 학습하고, 배치별 리턴을 CORE에 병합하던 중.
- **발견**: 5개 배치가 각자 독립적으로 "내 페이지에는 컴포넌트가 0개"라고 보고했고, 나는 이를 **"이 파일의 모든 인벤토리 페이지는 컴포넌트가 0개"** 로 일반화해 CORE에 기록했다. 6번째 배치가 자기 페이지를 직접 확인해 **24개의 실재하는 로컬 마스터 컴포넌트(full 40-hex 키)** 를 찾아 반박했다. **5개 배치는 거짓말하지 않았다 — 각자의 관찰은 전부 참이었고, 거짓은 그 합의를 전역으로 확장한 리드(나)의 추론에 있었다.** 합의는 오히려 위험을 키웠다: 5개가 일치하니 검증할 이유가 없어 보였다. 같은 현상이 이미 #116의 근거에 1회 기록돼 있었다(5개 에이전트가 "key가 Core와 다르다" 오탐) — **2번째 독립 목격이므로 자체 교훈으로 승격한다.**
- **교훈**: **에이전트 N개의 일치는 표본 N의 증거이지 전칭명제의 증거가 아니다.** 워커의 보고는 "내 스코프에서 관찰됨"으로 읽고, 전역 주장으로 승격할 때는 **스코프 밖을 최소 1회 직접 확인**한다. 특히 **부정 주장(X가 없다)** 은 합의로 확정하지 않는다 — 없음의 증명은 각 워커의 시야 밖에 있기 때문이다. 리드가 병합 전 헤드라인 주장을 1회 재검증하는 비용은 잘못된 CORE 엔트리 하나보다 항상 싸다.
- **근거**: 6번째 배치 리턴 — "⛔ REFUTATION 1 — '0 components on every inventory page' is FALSE. 간편인증기관 **18** COMPONENT / 공공기관 **6** COMPONENT (guarded `findAllWithCriteria`)". 이 시점에 CORE에는 이미 "COMPONENT/COMPONENT_SET = 0 on every inventory page"가 병합돼 있었다.

### 119. 리드가 주입한 잘못된 전제는 워커의 오류가 되어 돌아온다 — 브리핑은 지시가 아니라 검증 대상이다 (2026-07-16)
<!-- tier: principle -->

- **상황**: 16개 서브에이전트에 Figma 학습을 팬아웃하며, 각 브리핑에 "이 파일이 X의 authoritative home이다" 같은 사전 전제를 넣어 보냄.
- **발견**: 내 브리핑 중 **3건이 사실과 달랐고, 에이전트들은 지시대로 따랐다.** (1) "NDS_CI가 브랜드 규칙의 원본"이라 했으나 그 규칙은 그 파일에 **아예 없었다**(스코프 불일치 — 제3자 로고 파일이라 자사 브랜드 색 관할이 없음). (2) "`guide_parent`는 세트의 variant"라 했으나 **독립 COMPONENT**여서 import 함수 자체가 달랐다. (3) "카드에 `제작중`이 있으니 ⛔로 플래그하라"고 했으나 그 텍스트는 **흰 배경 위 흰 글자로 비가시**였고, 따랐다면 **실재하는 152개 에셋을 차단**할 뻔했다. 세 건 모두 에이전트가 "당신 브리핑에 대한 정정"으로 시작하는 리턴을 보내와서야 드러났다 — **명시적으로 "verify independently, do NOT adopt"라고 쓴 브리핑에서만 그랬다.**
- **교훈**: 리드의 브리핑은 워커에게 **사전 확률이 아니라 사실로 읽힌다.** 따라서 (1) 브리핑의 모든 전제에 **출처를 붙이고**(어느 파일/노드에서 왔는지), (2) "이건 내 가설이니 **독립 검증하고 반박하라**"를 명시하며, (3) 리턴 계약에 **"브리핑 정정" 슬롯을 요구**한다. 워커가 리드를 반박할 수 있게 만드는 것이 팬아웃 품질의 상한을 정한다 — 반박 채널이 없으면 **리드의 오류율이 곧 시스템의 오류율**이다.
- **근거**: 3개 배치 리턴이 각각 "🚨 CORRECTION TO YOUR BRIEFING — Nmoji is NOT incomplete… `제작중` reports `visible:true` but its fill is `{r:1,g:1,b:1}`", "⚠️ BRIEF WAS WRONG, PLEASE READ — They are two separate components", "**ABSENT ENTIRELY** — zero hits for `Deep Blue`… This inverts the brief's premise"로 시작.

### 122. 병렬 에이전트가 공유 tmp 경로에 고정 파일명으로 쓰면 서로의 stale 콘텐츠와 충돌해 잘못된 대상에 실행될 위험이 있다 (2026-07-17)
<!-- tier: principle -->

- **상황**: 16개 서브에이전트가 각자 독립적으로 DB에 쓸 SQL을 준비하며 공유 파일시스템의 임시 경로에 ad-hoc 파일을 저장.
- **발견**: 한 서브에이전트가 실행 직전 파일 내용을 확인했더니, 자신이 쓰려던 일반적/예측 가능한 tmp 파일명에 **이미 다른 동시 실행 중인 에이전트가 다른 대상 행(row)용으로 남긴 stale SQL**이 들어있었다. 그대로 실행했다면 잘못된 DB 행을 덮어썼을 것 — 실행 직전 내용 확인이라는 우연한 습관 덕에 발견됐을 뿐, 파일명 자체는 충돌을 막아주지 않았다.
- **교훈**: 다수 에이전트가 같은 공유 위치에 중간 파일을 병렬로 쓸 때는 반드시 job/agent 스코프의 고유 tmp 경로(`mktemp` 방식 등)를 쓰고, 고정된 일반 파일명은 절대 쓰지 않는다. 공유 파일시스템에 쓴 파일은 실행 직전 내용을 재확인하는 습관도 함께 둔다.
- **근거**: 서브에이전트 원문 — "a generic/predictable tmp filename it was about to write to and execute already held ANOTHER concurrent subagent's stale SQL content for a different target row — executing it as-is would have overwritten the wrong database row." (skeptic verifier CONFIRMED — 존재/위험 주장은 예측된 실패 양상을 직접 목격한 1회 관측만으로도 충분히 성립하며, 공유 경로+예측 가능 파일명+동시성이라는 메커니즘 자체가 그 관측을 완전히 설명함.)
- **추가 (2026-07-26, Supabase CLI tactical)**: 같은 project ref를 공유한 nhdesign3/4에서 동시 `db query --linked` 호출이 project-scoped 임시 로그인 상태와 경합해 SASL 인증 실패를 냈다고 보고됐다. fan-out 시 orchestrator가 한 번 snapshot하고 worker는 job-unique 파일만 읽으며 SQL 적용은 직렬화한다. 아직 다른 project/CLI version에서 재현되지 않았으므로 tactical 사례로 한정한다.
<!-- provenance: candidate=btw-provenance-db3ae46bbcda39673a16d119; run=9eed3fbd-5a8b-4a10-91ff-32dd357c4cdc; memory=1eb621cd-79c2-46fa-bf38-dd6c2a9a9657; range=git:231e4bfd61d91ceb623edfbe62055fa7b55106e9..51e68d3b5a5639b6cb90d0ecfc7cab94d0315b19;truncated=true -->
- **추가 (2026-07-26, stateful CLI tactical)**: shared-state collision은 한 명령이 아니라 open → register → create → ready → send → switch 전체 transaction에 걸칠 수 있다. 이 sequence 전체를 runtime별 process-local lock으로 직렬화하고, retry budget을 제한하면서 알려진 deterministic failure를 제외하며, wrapper가 exit status를 normalize할 때는 semantic `ok:false`를 검사하고 send 전에 readiness를 poll한다. process-local lock끼리는 서로 다른 runtime/process를 조정하지 않는다.
<!-- provenance: candidate=btw-provenance-99d3290d5388ee8639b6ae8f; run=9eed3fbd-5a8b-4a10-91ff-32dd357c4cdc; memory=884575df-63c4-407c-8b43-860d1295e663; range=git:8b4bc0ae03bf556eebe0a76f694c7f7a950d4fc7..beecbff7a96de131a08553d4e195c90d036c84b7;dirty:9c216341282624b328db07058c32ca6cad3d7f0176f0426aa70ebb575f49de6a;truncated=true -->

### 129. AI 서브에이전트의 성능/원인 진단은 가설이다 — 코드 반영 전 반드시 실측으로 재검증한다 (2026-07-17)
<!-- tier: principle -->
<!-- error-ref: ERR-2026-07-17-002 -->

- **상황**: "AI 별명짓기 새로고침이 느리다"는 리포트를 cs-ceo:ceo에게 위임했고, CEO는 정적 분석만으로 "claude -p 호출에 --model 미지정이 느림의 원인"이라 진단했다.
- **발견**: CEO의 진단대로 --model haiku만 적용해 `time`으로 실측했더니 42s→41s로 거의 무변화였다. 실제 병목은 CLI 부팅 오버헤드(무거운 플러그인/훅이 다수 설치된 계정)였고, 이를 스킵하는 플래그를 적용하자 42~47s→13~18s로 개선됐다.
- **교훈**: 서브에이전트/AI가 내놓은 성능·원인 진단은 검증 전 가설로만 취급한다. 코드에 반영하기 전 `time` 등 실측 도구로 전/후를 직접 비교해 진단이 맞는지 확인한다 — 정적 분석 기반 추정은 그럴듯해도 틀릴 수 있다.
- **근거**: portmanagement git commit 492846a 메시지: "--model haiku만으로는 속도 개선이 거의 없었음(42s→41s, 모델 자체는 병목이 아니었음). 실측 결과 진짜 병목은 CLI 부팅 오버헤드…" (skeptic verifier CONFIRM — 특정 도구/버전에 종속되지 않는 일반 인식론적 원칙).

### 134. Workflow의 parallel adversarial review가 "cleanup 완전 비활성화"라는 스코프 오류를 잡아낸 사례 (2026-07-17)
<!-- tier: principle -->
- **상황**: Implement → 병렬 Verify(logic reviewer + build/typecheck reviewer) → Apply Fixes 순서의 Workflow로 포트 관련 크래시를 수정하던 중, 1차 구현이 "override가 설정되면 stale listener cleanup을 통째로 꺼버리는" 방식으로 만들어졌다.
- **발견**: 병렬 리뷰어 중 하나가 "워크트리 세션이 크래시하면 동일 override로 재시작해도 orphan 리스너가 안 지워진다"는 구체적 회귀 시나리오를 지적했다 — cleanup을 "완전 비활성화"가 아니라 "이번 세션이 실제로 바인딩할 포트로 범위 한정"하는 방식으로 교정하는 후속 Apply Fixes 단계에서 반영됨.
- **교훈**: 런타임 정리/가드 로직을 조건부로 끄는 수정을 설계할 때 "완전 비활성화" 대신 "대상 범위 축소"를 먼저 검토한다. 이런 트레이드오프 오류는 순수 자기검토보다 Workflow의 병렬 adversarial reviewer 단계(서로 다른 관점의 리뷰어를 동시에 붙이는 구조)로 걸러내는 것이 실증적으로 효과적이었다 — 리뷰어가 실제로 "완전 비활성화 vs 범위 축소"라는 구체적 대안까지 제시했다.
- **근거**: 리뷰어 코멘트 원문 — "if a worktree session crashes, the next launch with the same override won't clear the orphaned listener because cleanup was fully disabled whenever ANY override was set" → Apply Fixes 단계에서 cleanup을 실제 타겟 포트로 스코프하는 수정 적용, 재검증 통과 (portmanagement PR #12, cs-end Workflow run).

### 141. 서브에이전트가 idle_notification만 반복하고 도구 호출이 전혀 없으면 데드락 신호로 보고 직접 실행으로 전환한다 (2026-07-17)
<!-- tier: tactical -->

- **상황**: 목표(회귀 테스트 수행)를 스폰한 CS 오케스트레이터 서브에이전트에 위임했는데, 4분여 동안 idle_notification 이벤트만 여러 차례(4회) 수신되고 실제 작업 도구 호출(브라우저 자동화, 계정 생성 등)은 한 건도 없었다.
- **발견**: 진행 상황을 묻는 상태확인 메시지를 2회 보냈지만 idle_notification만 반복될 뿐 실질적 응답이 없었다. 무한정 대기하는 대신 사용자에게 상황을 알리고 "직접 진행" 여부를 확인받은 뒤 shutdown_request로 해당 서브에이전트를 종료하고 동일 작업을 직접 수행했다 — 그 과정에서 실제 버그 여러 건을 찾아 수정할 수 있었다.
- **교훈**: 스폰한 서브에이전트가 idle_notification(또는 이에 준하는 무진행 신호)만 반복하고, 상태확인 메시지에도 실질적 응답 없이 동일 신호만 되풀이하면(대략 3회 이상), 이를 데드락/무진행 신호로 간주한다. 무한정 대기하지 말고 사용자 확인을 받아 종료 후 직접 작업으로 전환하는 편이 낫다 — 위임을 계속 신뢰하며 기다리는 것보다 빠르게 결과를 낸다.
- **근거**: idle_notification 4회 연속(12:34, 12:35, 12:36, 12:37 타임스탬프) + 상태확인 메시지 2건에도 무응답, 이후 직접 실행으로 전환해 세션 내 다수의 실제 버그(레이아웃 충돌, pseudo-account 400, 이름 충돌 등)를 발견/수정함.

### 155. 여러 항목에 동일 패턴의 오차가 의심되면 먼저 read-only로 전수 진단해 상수-델타 여부를 확인한 뒤 단일 배치 연산으로 고친다 (2026-07-21)
<!-- tier: principle -->

- **상황**: Figma FRAME 이동 후 그 안의 16개 자식 노드가 전부 프레임 밖으로 어긋나 보이는 문제를, diagnose(읽기 전용)→fix→verify 3단계 멀티에이전트 워크플로우로 처리.
- **발견**: 진단 에이전트가 16개 자식 전부의 상대좌표를 읽어 비교한 결과, 전부 동일한 상수 델타(Δx≈+5004, Δy≈-8888)만큼 어긋나 있고 내부 상대 배치 자체는 정확함을 확인했다. 이 진단 결과 덕분에 수정 에이전트는 벡터/지오메트리를 개별 편집하지 않고 `x += Δx; y += Δy` 형태의 단일 배치 시프트만으로 전체를 한 번에 고칠 수 있었고, 검증 에이전트가 스크린샷+좌표 재확인으로 1라운드 만에 통과 판정했다.
- **교훈**: 여러 항목에서 같은 종류의 어긋남이 관찰되면, 항목별로 개별 수정을 시도하기 전에 먼저 read-only 진단 단계로 "오차가 상수(delta)인지, 개별 노이즈인지"부터 확인한다. 상수 델타라면 단일 배치 연산이 개별 편집보다 안전하고 빠르며, 진단→수정→검증을 서로 다른(교차 검증되는) 에이전트로 나누면 수정 에이전트의 자기보고를 그대로 신뢰하지 않고 실제 스크린샷/좌표로 재확인할 수 있다.
- **근거**: 진단 에이전트가 산출한 16개 자식의 relX/relY 표에서 전부 relX∈[-5004,-2844], relY∈[8887,10390] 범위로 일관된 오프셋 확인 → 수정 에이전트가 Δx=+5004.378, Δy=-8887.525 단일 시프트 적용 → 검증 에이전트가 5개 DoD 항목 전부 PASS (roundsUsed: 1).
