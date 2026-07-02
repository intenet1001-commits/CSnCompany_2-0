# AGENT-CARD — CS 플러그인 공통 에이전트 카드 표준

모든 `agents/*.md` 파일(리드·워커 공통)은 이 카드 스키마를 따른다.
리드는 워커를 스폰할 때 역할 프롬프트 본문을 인라인으로 복사하지 않는다. 스폰 프롬프트는
`FIRST ACTION (BLOCKING): ${CLAUDE_PLUGIN_ROOT}/agents/<name>.md를 Read하고 그 카드를 당신의 정체성으로 채택하세요`
한 줄 + **최대 5줄의 task delta**(대상 경로, OUTPUT_DIR, FOCUS/FIX_MODE 등 실행별 값)만 포함한다.
(공유 파일 런타임 경로는 `${CLAUDE_PLUGIN_ROOT}/../shared/`로 해석한다. 절대 경로 금지.)

**이유**: 동일 역할 프롬프트가 스킬/커맨드/리드 3곳에 복제되면 한 곳만 수정되는 드리프트가 실제 버그가 된다
(CS-test 노하우 #11 — 버전 참조 3중 불일치). 카드 파일을 단일 소스로 두면 수정 지점이 1곳이 된다.

> 예시 (design-lead → visual-hierarchy 스폰):
> ```
> Task(name: "visual-hierarchy", prompt: """
> FIRST ACTION (BLOCKING): ${CLAUDE_PLUGIN_ROOT}/agents/visual-hierarchy.md를 Read하고 그 카드를 당신의 정체성으로 채택하세요.
> 분석 대상: src/ | 출력: design-results/visual-report.json | FOCUS: none""")
> ```

## 필수 frontmatter 키 (KEEP-tier — plugins/shared/LOOP-PROTOCOL.md Prescription Policy)

| 키 | 내용 |
|----|------|
| `name` | 에이전트 이름 (Task 스폰 name과 동일) |
| `description` | 한 줄 역할 |
| `model` | opus / sonnet / haiku — **카드의 model이 유일한 권위. 리드가 스폰 시 다른 model로 오버라이드하는 것을 금지한다** |
| `tools` | 필요한 최소 도구 목록 |

**이유**: model이 카드와 리드 프롬프트 양쪽에 살면 어느 쪽이 이기는지 아무도 모른다 —
shared/agents/verifier.md(sonnet) vs design-lead Step 4.5(opus) 모순이 실제 사례였다.

## 필수 본문 섹션 (순서 고정, KEEP-tier)

### [1] `## Goal`

측정 가능한 성공 기준 **한 문장**. 이 문장이 그대로 해당 에이전트의 LOOP-PROTOCOL [b] success criterion이 된다.

**이유**: 기준 없는 워커는 "다 했다"는 자기 선언만 남긴다 — 채점 가능한 목표가 먼저다.

> 예시: "24개 안티패턴 각각에 대해 탐지를 시도하고, 모든 hit에 file:line 증거가 붙은 JSON 리포트를 산출한다."

### [2] `## Backstory`

판단을 형성하는 2-4문장의 경험 서사 (cs-core-memory-v1/agents/memory-keeper.md의 "30년차 직원" 프레이밍 참조).

**이유**: 역할 명사("보안 전문가")만으로는 애매한 케이스의 판단 방향이 서지 않는다 — 서사가 default 판단을 정한다.

> 예시 (security-reviewer): "당신은 리뷰를 통과한 하드코딩된 키 하나가 유출 사고로 이어진 포스트모템들을
> 직접 트리아지해 본 사람이다. 증명되기 전까지 모든 리터럴 문자열을 자격증명으로 취급한다."

### [3] `## 📌 OWNS / ❌ DOES NOT OWN`

소유권 계약 — 기존 하우스 컨벤션 그대로 (KEEP-tier).

**이유**: 소유권 경계가 없으면 워커가 리드의 필터링·판정을 침범하거나, 아무도 안 맡는 갭이 생긴다.

> 예시: `📌 OWNS: 안티패턴 탐지, [CSS] 항목 자동 수정` / `❌ DOES NOT OWN: [JSX]·[COMPONENT] 수정, 종합 등급 산정`

### [4] `## Expected Output`

아티팩트 경로 + 형식(JSON 필드 정의 등, KEEP-tier). TASK CONTRACT 블록을 여기에 삽입할 수 있다.
기존 파일의 `출력 계약` / `출력 포맷` / `출력` / `완료 보고` 섹션(헤딩 레벨 무관)은 이 섹션의 동등물로 인정한다.

**이유**: 출력 스키마가 없으면 리드의 취합 단계가 파싱 실패로 무너진다.

> 예시: `출력: [OUTPUT_DIR]/visual-report.json — {"score": 0-10, "grade": "A-F", "issues": [...], "summary": "..."}`

### [5] `## Escalates when`

자체 해결하지 말고 리드(또는 사용자)에게 반환해야 하는 조건 bullet 목록.

**이유**: 워커가 판단 범위를 넘는 결정(범위 확대, 파괴적 수정)을 스스로 내리면 경계 없는 스코프 폭주가 된다.

> 예시: "- 대상 경로에 분석 가능한 파일이 0개일 때 — 임의로 다른 경로를 탐색하지 말고 리드에 보고"

## Prescription Policy 적용

frontmatter 키·본문 섹션 목록·출력 스키마는 **KEEP** 처방이다 (LOOP-PROTOCOL.md Prescription Policy).
카드 본문 안의 탐지 방법·클릭 순서 같은 실행 세부는 리터럴 레시피 대신 "목표 + 증거 요건 + 품질 기준"으로 쓴다.

## 집행 (Enforcement)

cs-end의 doc-updater(plugins/cs-end-v4/agents/doc-updater.md)가 DOMAINS_USED 플러그인 디렉토리의
agents/*.md에서 필수 키/섹션 누락을 doc-code mismatch로 보고한다.
