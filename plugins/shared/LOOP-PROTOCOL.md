# LOOP-PROTOCOL — CS 플러그인 공통 루프 엔지니어링 프로토콜

모든 CS 리드(lead) 에이전트는 이 6가지 규칙을 따른다.
참조 방법(리드 파일에 한 줄): `검증 프로토콜 (BLOCKING 첫 단계): fan-out 전 첫 행동으로 plugins/shared/LOOP-PROTOCOL.md를 Read하고 (verdict 플러그인은 plugins/shared/GATE-LOOP.md 추가 Read), 리포트 헤더에 'protocol: LOOP-PROTOCOL [a-f] loaded (round budget N)' 한 줄을 출력한다. 이 줄이 없는 리포트는 프로토콜 미적용으로 간주한다. verifier 디스패치는 plugins/shared/agents/verifier.md를, 재반박·교차검토는 plugins/shared/DEBATE-PROTOCOL.md를 따른다.` fan-out 계약은 plugins/shared/TASK-CONTRACT.md를 따른다 — CONTRACT 블록 없는 fan-out은 프로토콜 위반.
(런타임 경로는 `${CLAUDE_PLUGIN_ROOT}/../shared/`로 해석한다. 절대 경로 금지.)

## [a] EVIDENCE — 모든 발견은 증거를 인용한다

모든 finding/claim은 command+output 스니펫 또는 file:line 인용을 포함해야 한다.
증거 없는 주장은 `UNVERIFIED` 태그를 달고 grade/verdict 계산에서 제외한다.

**이유**: 그럴듯하지만 틀린 발견(plausible-but-wrong)이 단일 패스를 그대로 통과하는 것이 전 플러그인 공통 실패 모드다. 증거 의무화가 가장 싼 방어선이다.

> 예시: ❌ "로그인 폼에 validation이 없음" → ✅ "로그인 폼에 validation 없음 — `src/Login.tsx:42` `<input type=\"text\" name=\"email\">` (required/pattern 속성 부재)"

## [b] SUCCESS CRITERIA FIRST — 성공 기준을 먼저 선언한다

fan-out 전에 한 줄짜리 성공 기준(success criterion)을 출력하고, 보고 전에 그 기준에 대해 채점한다.

**이유**: 기준 없이 실행하면 "다 했다"는 자기 선언만 남는다. 기준을 먼저 박아야 약한 모델도 채점 가능한 목표를 갖는다.

> 예시: fan-out 직전 `성공 기준: 결제 플로우 3단계 모두 실제 클릭으로 통과하고 콘솔 에러 0건` 출력 → 보고서 첫 줄에 `기준 대비: PASS (3/3 통과, 콘솔 에러 0)` 채점.

## [c] BOUNDED LOOP — 실패 시 실패 범위만, 최대 2-3라운드

채점 FAIL 시 실패한 범위(scope)만 grade feedback을 첨부해 재디스패치한다.
최대 2-3라운드. 한 라운드가 델타(새 수정/새 통과)를 만들지 못하면 즉시 중단하고 루프 대신 **STUCK 리포트**(시도 이력 + 막힌 지점 + 필요한 결정)를 낸다.

**이유**: 무한 루프는 비용 폭주, 0회 루프는 단일 패스 품질. 경계 있는 루프가 "약한 모델 + 반복 > 강한 모델 1회"를 만든다.

> 예시: round 1에서 criterion 2/3 PASS → round 2는 실패한 criterion #3 담당 에이전트만 재디스패치(피드백: "FAIL 사유: 주문 확인 페이지 404"). round 2도 동일 결과면 round 3 없이 STUCK 리포트.

## [d] COVERAGE HONESTY — N/A는 등급을 깎는다

N/A 또는 죽은(무응답) 에이전트는 전체 grade에 상한을 건다:
- N/A 1-2개 → 최대 B
- N/A 3-5개 → 최대 C
- N/A 6개 이상 → Incomplete

커버리지 %는 리포트 헤더에 반드시 출력한다. (예: `커버리지: 12/14 에이전트 (86%)`)

**이유**: 14개 중 6개가 침묵했는데 A를 주는 것은 채점이 아니라 장식이다. 커버리지를 등급에 묶어야 누락이 보인다.

**[d-1] 합의는 표본의 증거일 뿐 전칭명제의 증거가 아니다.** 워커 N개의 일치는 "표본 N에서 관찰됨"으로 읽는다. 전역 주장으로 승격하기 전에 리드가 **스코프 밖을 최소 1회 직접 확인**한다. 특히 **부정 주장(X가 없다)** 은 합의만으로 확정하지 않는다 — 없음의 증명은 각 워커의 시야 밖에 있다. (근거: 학습 #118)

**[d-2] 없는 커버리지는 없다고 보고한다.** 의식적으로 남긴 작업은 침묵하거나 커버된 것처럼 쓰지 말고 (a) 시도하지 않은 것, (b) 미루는 것이 옳은 판단인 이유, (c) 무언가가 평가할 수 있는 구조화된 revisit 트리거를 적은 deferred 항목으로 남긴다. 존재하지 않는 커버리지를 주장하는 것이 가장 비싼 실수다.

## [e] REPORT FULL, FILTER DOWNSTREAM — 워커는 전부 보고, 필터는 리드가

워커(worker)는 발견한 모든 finding을 severity+confidence와 함께 보고한다.
필터링은 리드/verifier만 수행한다. 워커에게 "high-severity만 보고하라"고 지시하는 것을 금지한다.

**이유**: 워커 단계에서 필터하면 리드가 패턴(저심각도 발견 10개 = 구조적 문제 1개)을 볼 기회 자체가 사라진다. 정보 손실은 가장 늦은 단계에서 일어나야 한다.

> 예시: 워커 출력 `[{finding, severity: low, confidence: 0.9, evidence: ...}, ...]` 전체 전달 → 리드가 종합 후 리포트에는 critical/high만 본문, 나머지는 부록으로 배치.

## [f] OUTPUT PROPORTIONALITY — 리포트 크기는 confirmed finding 수에 비례한다

confirmed/unverified finding이 0건이면 풀 템플릿 대신 필수 헤더(커버리지 % + 성공 기준 채점 + 등급 — [b]/[d] 의무는 그대로 유지)와 에이전트별 1줄 요약만 출력하고, 섹션별 상세·부록은 생략한다. 단, 에이전트별 1줄 요약에는 해당 에이전트의 핵심 측정값을 포함한다 (예: 성능 에이전트면 FCP/LCP 수치 — 클린 런이어도 측정값은 정보다). 빈 섹션("없음"만 들어갈 섹션)은 만들지 않는다.

**이유**: [e](워커는 전부 보고)만 있고 리드 측 균형추가 없으면 클린 런에서도 풀 템플릿을 채우는 방향으로 밀린다. 필수 섹션을 채우려고 발견을 지어내는 template-filling이 실제 실패 모드다.

## → TASK-CONTRACT — fan-out 계약 (별도 파일)

워커 Task() 스폰 계약은 `plugins/shared/TASK-CONTRACT.md`가 정의한다: CONTRACT 블록(expected_output + acceptance_criteria) → 내용 Read 전 ls/wc/grep 수락 검사 → 실패 시 실패 assertion 원문 인용 1회 재디스패치 → 2회째 실패는 N/A로 [d] 등급 상한에 반영 → 리포트 헤더에 `contracts: N issued / M accepted`.
CONTRACT 블록 없는 fan-out은 프로토콜 위반이다.

## [g] FAN-OUT BRIEFING — 리드가 주입한 전제는 지시가 아니라 검증 대상이다

워커에게 팬아웃할 때 브리핑에 사전 전제를 넣으려면:

- 전제마다 **출처(file:line / 노드 ID / 커맨드)** 를 붙인다. 출처를 못 붙이는 전제는 브리핑에서 뺀다.
- 전제 블록에 **"independently verify, do NOT adopt"** 를 명시한다.
- 워커 리턴 계약에 **`briefing_correction` 슬롯**을 두고, 정정할 것이 없으면 빈 값으로 채우게 한다.

**이유**: 반박 채널이 없으면 리드의 오류율이 곧 시스템 오류율이 된다. 잘못된 전제는 워커의 오류가 되어 그대로 돌아오고, 실제로 정정 리턴은 "verify independently, do NOT adopt"라고 쓴 브리핑에서만 돌아왔다. (근거: 학습 #119)

## [h] PARALLEL WRITE ISOLATION — 공유 경로에 고정 파일명을 쓰지 않는다

다수 에이전트가 같은 공유 위치에 중간 파일(SQL/스크립트 등)을 병렬로 쓸 때는 job/agent 스코프의 **고유 tmp 경로(`mktemp` 방식)** 를 쓰고, 고정된 일반 파일명은 쓰지 않는다. 공유 파일시스템에 쓴 파일은 **실행 직전 내용을 재확인**한다.

**이유**: 예측 가능한 tmp 파일명은 동시 실행 중인 다른 에이전트의 stale 콘텐츠를 담을 수 있고, 그대로 실행하면 잘못된 대상에 적용된다. 파일명 자체는 충돌을 막아주지 않는다. (근거: 학습 #122)

## Prescription Policy — 처방 정책

프로토콜/프롬프트를 작성·수정할 때:

**KEEP (유지할 처방)**: 루브릭, 숫자 임계값(점수 컷, 라운드 상한), 출력 스키마(JSON 필드 정의), 소유권 계약(📌 OWNS / ❌ DOES NOT OWN), worked example, 결정적 스크립트를 구동하는 bash(pre_pass.py 호출 등).

**PREFER 목표 진술 (리터럴 레시피 대신)**: grep 레시피, 이모지 박스 리포트 템플릿, AskUserQuestion 문구 고정, 단계별 클릭 순서 같은 것은 "목표 + 증거 요건 + 품질 기준"으로 바꾸고 방법은 모델이 고르게 한다.

> 예시: ❌ `grep -rn "font-family" src/ | grep -v Inter` → ✅ "금지 폰트 사용을 탐지하고 file:line 증거를 인용하라. 탐지 방법은 자유."

**이유**: 강한 모델에게 레시피는 족쇄, 약한 모델에게 품질 기준 부재는 함정이다. 기계적 정확성이 필요한 곳만 처방하고, 나머지는 기준으로 묶는다.
