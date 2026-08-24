# DEBATE-PROTOCOL — 재반박(Rebuttal) · 교차검토(Peer Cross-Exam) 프로토콜

verifier의 kill-by-default("의심스러우면 살리지 말고 죽인다")는 인용만 약했던 진짜 발견(true positive)까지 조용히 죽이고,
격리된 병렬 워커는 서로의 리포트를 보지 못해 중복 계상·상호 모순이 종합 단계까지 살아남는다.
이 파일의 두 섹션이 그 두 갭을 각각 막는다. 두 섹션은 독립적이다 — 트리거가 성립한 쪽만 실행한다.

참조 방법(리드 파일에 한 줄): `재반박·교차검토: verifier 디스패치 전 트리거 성립 시 plugins/shared/DEBATE-PROTOCOL.md Section B를, verifier 패스 후 REFUTED 발생 시 Section A를 실행한다.`
(런타임 경로는 `${CLAUDE_PLUGIN_ROOT}/../shared/`로 해석한다. 절대 경로 금지.)

## Section A — Rebuttal Round (advocate ↔ verifier, 최대 1회)

**트리거 (모두 만족할 때만):** verifier 패스에서 REFUTED된 finding 중 원(original) severity가 critical/high **이고** 원 confidence ≥ 0.8인 것이 1건 이상.
대상은 최대 **5건** (초과분은 confidence 내림차순 상위 5건, 나머지는 REFUTED 확정).
**REFUTED 0건이면 섹션 전체 스킵** — 클린 런 비용 0.

**이유**: kill-by-default는 오탐 방어로는 옳지만, 인용만 약했던 진짜 critical을 재심 기회 없이 죽이면 검증이 정보 손실 장치가 된다 — 고신뢰 REFUTED에만 딱 1회 재심을 준다.

**STEP 1 — advocate 스폰 (정확히 1개):** 리드는 `plugins/shared/agents/advocate.md` 카드로 advocate Task 1개를 스폰한다
(model/tools는 카드 frontmatter가 유일한 권위 — 오버라이드 금지, AGENT-CARD.md 표준).
finding별 입력: `{id, claim, original_evidence, counter_evidence}`.
advocate는 각 finding에 대해 **새 증거**(원 인용과 다른 file:line 또는 command+output)를 발굴해 REBUT하거나 CONCEDE한다.
동일 인용 재주장(new_evidence == original_evidence)은 리드가 자동 CONCEDE 처리한다.

**STEP 2 — verifier 라운드 2 (REBUT 항목만):** 리드는 REBUT된 항목만 공용 verifier(`plugins/shared/agents/verifier.md`)에 재전송한다.
라운드 2 verifier는 `new_evidence`만 검사한다 — 원 증거·원 판정을 재론하지 않는다 (verifier.md '반론 라운드' 참조).

**STEP 3 — 최종 상태 판정 (verifier가 아니라 리드가 부여):**

| 최종 상태 | 조건 |
|---|---|
| CONFIRMED | 라운드 2 verifier가 CONFIRMED로 뒤집음 |
| REFUTED | advocate가 CONCEDE했거나, 라운드 2도 REFUTED이고 new_evidence가 리드의 cold re-read(해당 file:line/명령 직접 재확인)에서도 무너짐 |
| CONTESTED | 라운드 2도 REFUTED이지만 advocate의 new_evidence가 리드의 cold re-read를 통과함 |

CONTESTED finding은 리포트의 필수 섹션 **`## 쟁점 (CONTESTED)`** 에 양측 증거(advocate new_evidence vs verifier counter_evidence)를 나란히 배치한다.
grade/verdict 산술에서는 제외하되, **조용히 삭제하는 것을 금지한다** — 사람이 판단할 몫이다.

**하드 바운드:** advocate 1개 · 재반박 라운드 최대 1회 · finding 최대 5건.
종료 시 리드는 검증 요약에 종료 사유를 포함한 한 줄을 출력한다:
`debate: N rebutted → X CONFIRMED / Y REFUTED / Z CONTESTED (종료 사유: 라운드 캡 도달 | REBUT 소진 | 스킵—REFUTED 0건)`

**이유(바운드)**: 재반박이 무제한이면 advocate와 verifier가 영원히 핑퐁한다 — 1라운드로 못 살린 finding은 CONTESTED로 기록하고 루프 대신 사람에게 넘긴다 (LOOP-PROTOCOL [c]와 동일한 철학).

> worked example: security-reviewer가 "하드코딩 API 키 — `config.ts:12`" (critical, confidence 0.9)를 보고 →
> verifier가 "config.ts:12는 주석 처리된 예시"로 REFUTED → 트리거 성립 →
> advocate가 재탐색으로 `deploy/prod.env.example:3`의 실제 라이브 키를 new_evidence로 REBUT →
> 라운드 2 verifier가 해당 라인만 재확인해 CONFIRMED → 최종 CONFIRMED.
> 인용만 틀렸던 진짜 발견이 구조된다. 반대로 advocate가 새 증거를 못 찾으면 CONCEDE → REFUTED 확정, 추가 라운드 없음.

## Section B — Peer Cross-Exam (교차검토, 1회)

**트리거 (둘 다 만족할 때만):** 병렬 워커 **≥ 3개**가 리포트를 산출했고, 총 finding **≥ 8건**.
미만이면 cross-examiner를 스폰하지 않고 리드가 인라인으로 중복 제거한다 (LOOP-PROTOCOL [f] 비례성).

**이유**: 격리된 병렬 분석가는 같은 결함을 두 렌즈로 두 번 세고(중복 계상), 서로 모순되는 주장을 내도 아무도 대조하지 않는다 — 종합 단계의 리드 혼자서는 N개 리포트의 교차 관계를 놓친다.

**실행 (정확히 1개 Task, 1회):** model: sonnet, tools: Read, Grep —
이미 디스크에 있는 형제 리포트 파일(예: design-results/*.json, tests/results/*.json)만 읽는다.
아티팩트가 파일이 아니라 리드 컨텍스트에만 있으면 finding 목록을 프롬프트에 인라인 전달한다.
출력 계약 (**finding·verdict 추가 금지** — 관계 판정만):

```json
[
  {
    "finding_id": "<id>",
    "relation": "DUPLICATE_OF:<id> | CORROBORATES:<id> | CONFLICTS_WITH:<id>",
    "evidence": "양쪽 리포트에서 인용한 두 스니펫"
  }
]
```

**리드 병합 규칙 (각 리드의 종합 단계에 3줄):**
- `DUPLICATE_OF` → 하나로 병합, grade 산술에 1회만 계상, 두 렌즈를 병기
- `CORROBORATES` → confidence 상향 + "2개 렌즈 일치" 주석
- `CONFLICTS_WITH` → 양쪽 finding을 severity 무관하게 verifier 검증 대상에 강제 포함, 검증으로도 미해소 시 Section A의 CONTESTED로 처리

> worked example: visual-hierarchy와 responsive-accessibility가 각각 "본문 폰트 12px 미만"을 별건으로 보고 →
> cross-examiner가 양쪽 스니펫을 인용해 DUPLICATE_OF 판정 → 리드는 1건으로 병합해 등급에 1회만 반영하고
> "visual + responsive 두 렌즈에서 검출"로 병기. security-auditor "CSP 헤더 없음" vs api-interceptor "CSP 헤더 확인됨"은
> CONFLICTS_WITH → 둘 다 verifier로 강제 회부, 미해소 시 CONTESTED.
