# HITL-POLICY — Human-in-the-Loop 체크포인트 프로토콜

체크포인트를 가진 모든 CS 플러그인(리드 + 그 리드를 스폰하는 main-context 호출자)은 이 4개 섹션을 따른다.
참조 방법(리드/SKILL 파일에 한 줄): `HITL 프로토콜 (BLOCKING): 체크포인트 발생 가능 구간 진입 전 plugins/shared/HITL-POLICY.md를 Read하고, 런 헤더의 protocol 줄 옆에 'hitl: <auto|gate|always>' 한 줄을 출력한다.` 이 줄이 없는 리포트는 HITL 미적용으로 간주한다.
LOOP-PROTOCOL.md의 Read-first BLOCKING 절차와 같은 패턴이다 — 리드는 fan-out 프로토콜과 함께 이 정책을 적용한다.
(런타임 경로는 `${CLAUDE_PLUGIN_ROOT}/../shared/HITL-POLICY.md`로 해석한다. 절대 경로 금지.)

## [1] MODES — --hitl 플래그 3모드

각 플러그인의 command 파일이 `--hitl=<mode>`를 파싱해 리드에게 `HITL: <mode>`로 전달한다. `--auto`는 `--hitl=auto`의 별칭이다.

| 모드 | 동작 |
|------|------|
| `auto` | 런 중간에 절대 묻지 않는다 — 모든 체크포인트에서 `default_option`을 조용히 채택하고 계속 진행 (야간 위임/overnight 운영 보존 — cs-ceo 노하우 #14) |
| `gate` | **기본값** — [4]의 Named Checkpoints 레지스트리에 등록된 체크포인트에서만 묻는다 |
| `always` | 모든 Phase 전환 직전마다 묻는다 (등록 체크포인트 + Phase 경계) |

**이유**: 전 플러그인이 인간 접촉을 시작 시점에 몰아넣고 이후 눈감고 달린다 — 모드가 플래그로 분리돼야 "밤새 돌려놓기"와 "중요 분기에서 확인받기"가 같은 프로토콜 안에서 공존한다.

> 예시: `/CS-plan --hitl=auto "결제 도메인"` → arch-choice 체크포인트에서 질문 없이 arch-designer 권장안 채택 + 리포트에 `hitl: auto — arch-choice: default(권장안) 자동 채택` 기록. 플래그 없이 `/CS-plan "결제 도메인"` → gate 모드 → arch-choice에서 사용자에게 옵션 제시.

## [2] CHECKPOINT PAYLOAD SCHEMA — 서브에이전트 리드는 AskUserQuestion을 호출하지 않는다

서브에이전트로 실행 중인 리드는 사용자에게 물을 수 없다 (AskUserQuestion은 main context 전용).
따라서 리드는 체크포인트에서 **STOP**하고, Task 결과로 아래 JSON을 반환한다:

```json
{
  "type": "CHECKPOINT",
  "checkpoint_id": "<[4] 레지스트리의 id>",
  "phase_done": "<완료한 마지막 Phase>",
  "question": "<사용자에게 물을 한 문장>",
  "options": [
    {"label": "<선택지 라벨>", "consequence": "<선택 시 결과 한 줄>"}
  ],
  "default_option": "<options 중 하나의 label — auto 모드/무응답 시 채택>",
  "resume": {
    "artifacts": ["<지금까지 작성한 산출물 절대 경로>"],
    "next_phase": "<재개할 Phase>",
    "context_note": "<재스폰된 리드가 알아야 할 상태 1-3줄>"
  }
}
```

STOP 전에 리드는 살아있는 팀 에이전트를 shutdown하고 산출물을 디스크에 남긴다 — 재스폰된 리드가 `resume.artifacts`를 Read해 작업을 이어받는다.
리드가 main context에서 직접 실행 중이면(예: CS-test의 test-lead) AskUserQuestion을 직접 호출해도 된다 — payload는 서브에이전트로 스폰됐을 때의 폴백이다.

**예외 (cs-clarify 인터랙티브 인터뷰)**: cs-clarify의 Socratic 인터뷰(requirements-interviewer 최대 3라운드)와 clarify-lead Phase 3 재명료화(최대 2사이클, 각 1라운드)는 질문 자체가 산출물의 원료다 — 라운드마다 STOP-and-return하면 팀 전체가 라운드 수만큼 죽고 살아나 체크포인트 비용이 산출물 가치를 초과한다. 이 구간에 한해 AskUserQuestion **시도**를 허용한다. 단 두 가지 경계는 그대로다: (a) 호출이 실패/사용 불가하면 답을 지어내지 않고 해당 차원을 UNANSWERED로 표시하고 진행한다 (cs-clarify SKILL의 기존 폴백), (b) `HITL=auto`면 인터뷰·재명료화 질문 전체를 생략한다 — cs-clarify가 QUICK 경로(scope+assumptions만)로 강등되고 재명료화는 opt-out default(현재 상태로 종료)를 채택한다.

**이유**: 이 예외가 문서에 없으면 "서브에이전트는 못 묻는다"와 cs-clarify의 인터뷰가 정면 모순으로 남는다 — 예외를 경계와 함께 명시해야 /cs-company `--auto`("런 중간에 절대 묻지 않는다")가 CLARIFY phase에서도 성립한다.

> 예시: `/cs-company --auto "결제 기능"` → conductor가 CLARIFY에 `HITL: auto` 전파 → clarify-lead가 STEP 1(인터뷰)을 스킵하고 scope-validator → assumption-mapper만 실행, Phase 3 재명료화 질문 없이 현재 점수로 확정 → CLARIFY.md frontmatter에 결과 그대로 기록(clarify_score < 7이면 `status: blocked` — 성공 위장 금지).

**이유**: "서브에이전트는 사용자에게 못 묻는다"는 제약 때문에 중간 체크포인트가 구조적으로 불가능했다 (CS-plan 노하우 #6이 요약-노출로 물타기된 정확한 원인). STOP-and-return이 그 구조적 해결이다 — 질문이 리드를 죽이지 않고 결과로 승격된다.

> 예시: plan-lead가 Phase 1a 완료 후 `{"type":"CHECKPOINT","checkpoint_id":"arch-choice","phase_done":"1a","question":"아키텍처 방향을 선택하세요","options":[{"label":"Clean 4레이어(권장)","consequence":"레이어 완전 분리, 파일 수 최다"},{"label":"Pragmatic 3레이어","consequence":"Application/Adapter 통합, 구현 빠름"}],"default_option":"Clean 4레이어(권장)","resume":{"artifacts":[".tdd-plans/domain-analysis.md",".tdd-plans/architecture.md"],"next_phase":"1b","context_note":"glossary 확정됨, wave 2는 선택된 레이어 목록을 프롬프트에 임베드할 것"}}` 를 Task 결과로 반환하고 종료.

## [3] BUBBLING RULE — 호출자가 질문을 대신 던지고, 같은 리드를 재스폰한다

리드를 스폰한 main-context 호출자(해당 SKILL.md, 또는 conductor)는 Task 결과에서 `type: "CHECKPOINT"`를 감지하면:

1. **auto 모드** → AskUserQuestion 없이 `default_option`을 조용히 채택하고 3으로.
2. **gate/always 모드** → AskUserQuestion 1회: `question` + `options`(각 label에 consequence 병기) + **"작업 취소" 옵션 필수** (Goal Gate 규율과 동일 — 탈출구 없는 질문 금지). "작업 취소" 선택 → 즉시 종료, 지금까지의 `resume.artifacts` 경로를 사용자에게 알린다.
3. 같은 리드를 **재스폰**한다 — 프롬프트에 원래 컨텍스트 + `CHECKPOINT_ANSWER: <선택 label>` + `RESUME: <payload의 resume 블록 원문>`을 전달한다. 재스폰된 리드는 `resume.artifacts`를 Read하고 `next_phase`부터 진행한다 — 완료된 Phase를 다시 실행하지 않는다.

**경계 (BOUNDED)**: 한 런에서 같은 `checkpoint_id`는 최대 1회만 버블링된다 — 재스폰된 리드가 동일 checkpoint_id를 다시 반환하면 재스폰 없이 STUCK으로 종료하고 종료 사유(`checkpoint <id> re-raised after resume`)를 리포트에 남긴다. 런당 체크포인트 총 3회 초과 시에도 동일하게 중단한다 (LOOP-PROTOCOL [c]와 같은 원리 — 상한 없는 일시정지는 상한 없는 루프다).

**이유**: 체크포인트를 리드가 아니라 호출자가 처리해야 질문 권한(main context)과 작업 상태(리드)의 소유가 분리된다 — resume 블록이 없으면 재스폰마다 전체 재작업이 되어 체크포인트 비용이 금지 수준으로 뛴다.

> 예시: CS-plan SKILL Step 3.5 — plan-lead 결과가 CHECKPOINT(arch-choice) → AskUserQuestion(옵션 2개 + 작업 취소) → 사용자가 "Pragmatic 3레이어" 선택 → plan-lead 재스폰: `CHECKPOINT_ANSWER: Pragmatic 3레이어` + `RESUME: {...}` → 재스폰된 plan-lead는 domain-analysis.md/architecture.md를 Read만 하고 Phase 1b(tdd-strategist ∥ checklist-builder)부터 실행.

## [4] NAMED CHECKPOINTS — 레지스트리

gate 모드가 묻는 체크포인트의 정본 목록. 새 체크포인트는 이 표에 등록해야 gate 모드에서 발동한다 (미등록 체크포인트는 always 모드에서만).

| plugin | checkpoint_id | trigger | default |
|--------|---------------|---------|---------|
| CS-plan | `arch-choice` | Phase 1a 완료 — architecture.md의 핵심 설계 결정에 2-3개 방향 옵션 존재 | 옵션 1 (arch-designer 권장안) |
| CS-test | `build-blocker` | Phase 0 build-validator grade F | continue full run |
| cs-smart-run | `plan-approval` | Phase 1.5 완료 — 플랜 확정 직전 (PLAN INTAKE 경로 포함) | approve (플랜대로 실행) |
| cs-ceo | `redispatch-confirm` | Phase 3.6 round-2 FAIL 재디스패치 직전 | proceed (재디스패치 진행) |
| cs-design | `direction-choice` | visual-hierarchy 리포트에 방향 A/B/C 옵션 존재 | 방향 A (현재 스타일 개선) |

**이유**: 체크포인트가 레지스트리 없이 각 플러그인 프롬프트에 흩어지면 gate 모드의 "어디서 멈추는가"가 비결정적이 된다 — 표 하나가 모드 계약의 단일 소스다.

> 예시: CS-test가 cs-ceo에 의해 서브에이전트로 스폰된 상태에서 build-validator가 F 반환 → test-lead는 `checkpoint_id: "build-blocker"` payload를 반환 → cs-ceo(또는 그 호출자)가 [3]에 따라 버블링. 같은 상황에서 `--hitl=auto`면 default(continue full run)로 무정지 진행.
