# CHAIN-SCHEMA — 선언적 파이프라인 매니페스트 스키마 (P3)

ChatDev `ChatChainConfig.json`의 `chain[]`을 CS 마켓플레이스로 이식한 선언적 파이프라인 규격이다.
리드(cs-ceo Mode D, experiencing-lead)가 이 매니페스트를 읽고 위→아래로 walk하며 각 phase를
Task 도구로 디스패치한다. ORCHESTRATION-PATTERNS.md P3와 함께 읽는다.

## 왜 매니페스트인가

파이프라인 순서를 산문이 아니라 데이터로 선언하면: (1) 재사용·조합 가능 (2) 리드가 결정적으로
walk 가능 (3) 리포트에 실행 계획을 그대로 인용 가능. ChatDev가 SDLC 워터폴을 `chain[]` 배열
순서로 실행하는 것과 동일한 발상.

## 최상위 스키마

```jsonc
{
  "name": "review-fix",                  // 매니페스트 식별자
  "goal": "코드 리뷰 후 HIGH 이슈 수정까지",  // 한 문장 목표 (LOOP-PROTOCOL [b])
  "success_criteria": "HIGH 이슈 0건 또는 모두 티켓화", // 종료 채점 기준
  "context_dir": ".cs-chain",            // 런 스코프 공유 컨텍스트(ChatEnv) 디렉토리
  "chain": [ /* phase 객체 배열 — 실행 순서 = 배열 순서 */ ]
}
```

## phase 객체 스키마

```jsonc
{
  "phase": "review",                 // (필수) phase 이름 — 고유
  "domain": "CS-codebase-review",    // (필수) 담당 CS 도메인 또는 에이전트
  "phaseType": "simple",             // (필수) "simple" | "composed"
  "inputs": ["explore.report"],      // (선택) 주입할 이전 phase 산출물 (phase.artifact 참조)
  "expected_output": "리뷰 리포트 md + HIGH 이슈 목록", // (권장, P5) 완료 형태
  "speaker": "parallel",             // (선택, P1) parallel|round_robin|auto|manual — 기본 parallel

  // phaseType == "composed" 일 때만 (P4 역할극 루프):
  "cycleNum": 3,                     // 루프 상한 (하드 캡: review/test=3, complete=10)
  "instructor": "reviewer",          // 지시자 역할 (최우선 이슈 1개씩 제시)
  "assistant": "fixer",              // 실행자 역할 (지시받은 항목만 수정)
  "break_on": "<INFO> Finished",     // 센티넬 종료 토큰 (P2 sentinel)
  "termination": "max_turns(3) OR sentinel(<INFO> Finished) OR no_delta" // (권장) 종료식
}
```

## 실행 규약 (리드가 따르는 것)

1. **walk**: `chain[]`을 순서대로 처리. 각 phase 시작 시 `Running [phase] ([domain]) N/M...` 출력.
2. **inputs 수집** (ChatDev `update_phase_env`): `inputs`에 나열된 `phase.artifact`를 읽어
   디스패치 프롬프트의 컨텍스트로 주입. 없으면 생략.
3. **디스패치**:
   - `simple` → 도메인 리드/에이전트 1회 스폰. `speaker`가 있으면 P1 정책 적용.
   - `composed` → P4 instructor↔assistant 루프를 `cycleNum`만큼. 매 턴 후 `termination` 평가,
     `break_on` 센티넬 또는 no_delta면 조기 종료.
4. **write-back** (ChatDev `update_chat_env`): phase 산출물을 `context_dir` 또는 도메인이 선언한
   아티팩트 경로에 남겨 다음 phase가 `inputs`로 참조 가능하게 한다.
5. **게이트**: 각 phase 후 LOOP-PROTOCOL [a] 증거 스팟체크(인용 1건 Read/grep). 실패 시 등급 강등.
6. **종료 보고**: 각 composed phase가 어떤 종료 조건으로 끝났는지 기록
   (`review: sentinel(<INFO> Finished) @ round 2`).

## 프롬프트 기반 한계 (정직성)

- 이 매니페스트는 **선언**이지 실행 엔진이 아니다 — 리드 LLM이 해석해 walk한다 (ChatDev는 Python이
  실행). 따라서 JSON 필드는 리드에 대한 지시이며, 잘못된 참조는 런타임 에러가 아니라 리드가 감지해
  보고해야 한다.
- 조건부 분기(다음 phase를 결과로 결정)는 `speaker: auto` + P1 transition table로 표현한다 —
  매니페스트 자체에 if/else를 넣지 않는다(단순성 유지).

## 예제

- `feature-dev.chain.json` — plan → review → test 순차 (기능 개발 파이프라인).
- `review-fix.chain.json` — explore → review(composed 리뷰어 루프) → test (버그 수정 파이프라인).
