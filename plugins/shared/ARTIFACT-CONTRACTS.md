# ARTIFACT-CONTRACTS — CS 파이프라인 아티팩트 계약

CLARIFY→PLAN→IMPLEMENT→REVIEW/TEST→SHIP 체인의 모든 산출물(artifact)은 이 계약을 따른다.
참조 방법(리드 파일의 검증 프로토콜 줄에 덧붙이는 한 구절): `아티팩트를 생산/소비하는 리드는 plugins/shared/ARTIFACT-CONTRACTS.md를 추가로 Read한다.`
(런타임 경로는 `${CLAUDE_PLUGIN_ROOT}/../shared/`로 해석한다. 절대 경로 금지.)

## 아티팩트 타입 (artifact_registry.py DEFAULTS와 1:1)

| type | producer | 주 소비자 | 기본 경로 |
|---|---|---|---|
| CLARIFY.md | cs-clarify | CS-plan, cs-ship | `.cs-artifacts/CLARIFY.md` |
| PLAN.md | CS-plan | cs-smart-run, cs-ship | `[OUTPUT_DIR]/PLAN.md` (기본 `.tdd-plans/`) |
| IMPLEMENT-REPORT.md | cs-smart-run | CS-codebase-review, cs-ship | `.cs-artifacts/IMPLEMENT-REPORT.md` |
| REVIEW.md | CS-codebase-review | cs-ship, 사용자 | `.cs-artifacts/REVIEW.md` |
| TEST-REPORT.md | CS-test | cs-ship, 사용자 | `tests/results/REPORT.md` |
| SHIP-REPORT.md | cs-ship | 사용자 | `.cs-artifacts/SHIP-REPORT.md` |

## [1] FRONTMATTER — 모든 아티팩트는 YAML frontmatter로 자기 상태를 선언한다

파이프라인 아티팩트 파일 최상단에 다음 YAML frontmatter를 넣는다:

```yaml
---
cs_artifact:
  type: CLARIFY.md | PLAN.md | IMPLEMENT-REPORT.md | REVIEW.md | TEST-REPORT.md | SHIP-REPORT.md
  producer: <생산 플러그인 이름>
  produced_at: <ISO 8601 timestamp>
  status: ready | blocked        # blocked = 게이트 미통과 상태로 종료됨
  gate:
    passed: true | false
    criterion: "<한 줄 성공 기준 — LOOP-PROTOCOL [b]의 그 기준>"
    blocking_items: []           # 미통과 시 남은 차단 항목 목록
---
```

기존 frontmatter 키(예: cs-clarify의 `clarify_cycles`)는 `cs_artifact` 블록과 나란히 유지한다.

**이유**: 파일 존재 여부만으로는 "완성됐는가/통과했는가"를 알 수 없다 — 소비자가 미완성 산출물을 묵묵히 소비하는 것이 체인 단절의 주 원인이므로, 상태를 파일 자체가 선언해야 한다.

> 예시: cs-clarify가 clarify_score 5로 종료 → `status: blocked`, `gate: {passed: false, criterion: "clarify_score >= 7", blocking_items: ["HIGH 가정: 결제 게이트웨이 미확정"]}` → CS-plan이 이를 보고 그대로 설계에 들어가지 않고 사용자에게 확인한다.

## [2] PRODUCER — 생산 리드의 마지막 프로토콜 단계는 Write(frontmatter 포함) + register

아티팩트를 생산하는 리드의 **마지막** 프로토콜 단계는 두 동작이다:
1. [1]의 frontmatter를 포함해 아티팩트를 Write한다.
2. registry에 등록한다: `register <type> <path> <plugin>` (+ verdict 산출 플러그인은 `verdict <type> <PASS|FAIL|WARNINGS|BLOCKED> <round> [item ...]` — plugins/shared/GATE-LOOP.md).

**이유**: 등록되지 않은 아티팩트는 다음 단계가 `find-meta`로 발견하지 못한다 — Write만 하고 register를 생략하면 체인이 그 지점에서 조용히 끊긴다 (CLARIFY→PLAN 단절이 실측된 사례).

> 예시: plan-lead가 `.tdd-plans/PLAN.md` 합성 완료 → frontmatter `status: ready` 기록 → `register PLAN.md .tdd-plans/PLAN.md CS-plan` 실행 → 이후 `/smart-run`이 Phase 0.7에서 자동 감지.

## [3] CONSUMER — 소비 리드의 첫 컨텍스트 단계는 find-meta + 신선도 확인

업스트림 아티팩트를 소비하는 리드의 **첫** 컨텍스트 수집 단계는:
1. `find-meta <type>` 실행 → `{path, age_days, freshness, verdict, round, blocking_items}` 확보.
2. `freshness: fresh` **이고** frontmatter `status: ready`면 그대로 소비.
3. `freshness: stale`(기본 7일, `CS_ARTIFACT_STALE_DAYS`로 조정) 또는 `status: blocked`면 묵묵히 소비하지 않는다 (cs-ship R7 staleness 가드와 동일 의미론):
   - **main context에서 실행 중이면** AskUserQuestion으로 **1회** 확인 — "[type]이(가) N일 전 것입니다. 이 기준으로 진행할까요, 무시하고 새로 시작할까요?"
   - **서브에이전트로 실행 중이면** AskUserQuestion이 불가하므로 질문을 지어내 답하지 말고, 질문+선택지를 담은 **CHECKPOINT 블록을 호출자에게 반환**하고 중단한다 (호출자가 사용자에게 물은 뒤 답과 함께 재개).
4. 아티팩트가 아예 없으면(`find-meta` → null) 질문 없이 각 플러그인의 기존 무-아티팩트 경로로 진행한다 — 소비는 항상 **additive**여야 한다.

**이유**: 오래된/미통과 스펙을 신선한 것처럼 소비하면 검증이 유령 요구사항을 기준으로 돌아간다 — 반대로 아티팩트 부재를 에러로 만들면 단독 실행이 깨진다. 확인은 1회로 경계 짓는다.

> 예시: cs-smart-run이 `find-meta PLAN.md` → `{freshness: "stale", age_days: 12}` → main context이므로 AskUserQuestion 1회("12일 전 PLAN.md입니다. 이 플랜으로 실행할까요, 새로 플랜할까요?") → 사용자가 "새로"를 선택하면 Phase 1(Opus 플래너)로 폴스루.

## Registry 호출 규칙

plugins/CLAUDE.md의 Python 실행 규칙을 따른다 (run_prepass.sh와 동일한 폴백 순서 — python3 → uv):

```bash
REGISTRY="${CLAUDE_PLUGIN_ROOT}/../shared/artifact_registry.py"
if command -v python3 >/dev/null 2>&1; then RUN_PY="python3"; else RUN_PY="uv run --quiet --no-project python"; fi

$RUN_PY "$REGISTRY" register <type> <path> <plugin>                     # [2] 생산 등록
$RUN_PY "$REGISTRY" find-meta <type>                                    # [3] 소비 인테이크
$RUN_PY "$REGISTRY" verdict <type> <PASS|FAIL|WARNINGS|BLOCKED> <round> [item ...]  # GATE-LOOP 기록
```

셸 헬퍼(`source ${CLAUDE_PLUGIN_ROOT}/../shared/artifact_registry.sh` 후 `cs_artifact_meta` / `cs_record_verdict`)도 동등하다.

**이유**: 문서마다 다른 호출 방식(bare python3 vs uv)이 섞이면 Python 미설치 환경에서 절반만 동작한다 — 호출 규칙은 한 곳(이 파일)이 정본이다.
