# MEMORY-PROTOCOL — CS 플러그인 공통 회상(Recall) 프로토콜

모든 CS 리드(lead) 에이전트는 fan-out 전에 아래 **Phase R (Recall)** 을 정확히 1회 수행한다.
참조 방법(리드 파일의 검증 프로토콜 줄에 덧붙이는 한 구절): `LOOP-PROTOCOL Read 직후 plugins/shared/MEMORY-PROTOCOL.md의 Phase R(회상)을 수행하고, 리포트 헤더에 'recall: E<n>/C<n>/N<n>' 한 줄을 출력한다. 이 줄이 없는 리포트는 회상 미수행으로 간주한다.`
(런타임 경로는 `${CLAUDE_PLUGIN_ROOT}/../shared/`로 해석한다. 절대 경로 금지. `~/.claude/...` 경로는 사용자 홈 저장소 — core-memory, error-notes — 에만 허용된다.)

**왜 이 프로토콜인가**: 이 스위트의 최대 자산(90+ 누적 학습, CORE.md 전략 메모리, 에러 아카이브)이 write-only였다 —
CS-plan·cs-design·cs-ship·CS-test는 런타임에 아무것도 읽지 않았다. Phase R은 학습 루프의 read 쪽을 닫는다.

## Phase R (Recall) — LOOP-PROTOCOL Read 직후, fan-out 전 1회

기존 3개 저장소(단기 아티팩트 / 에피소드 학습 / 전략 메모리) + 에러 아카이브를 아래 4단계 고정 순서로 소비한다.
새 저장소를 만들지 않는다 — Phase R은 전부 기존 스토어 위에서 동작한다.

### [R-a] SHORT-TERM — 파이프라인 아티팩트 인테이크 (find-meta)

`.cs-artifacts/manifest.json`에 등록된 상류 아티팩트를 `artifact_registry find-meta <type>`으로 조회한다.
이미 ARTIFACT-CONTRACTS [3] CONSUMER 단계를 수행하는 리드는 **그 결과를 재사용**한다 (find-meta 중복 실행 금지).

**이유**: 상류 산출물(CLARIFY/PLAN 등)은 가장 신선한 컨텍스트인데, 등록만 되고 소비되지 않으면 체인이 조용히 끊긴다.

> 예시: cs-ship이 `find-meta TEST-REPORT.md` → `{freshness: "fresh", verdict: "PASS"}` → 검증 게이트 입력으로 재사용, 별도 재조회 없음.

### [R-b] EPISODIC — cs-experiencing 학습 INDEX만 grep (SKILL.md 전체 Read 금지)

태스크에서 키워드(기술 스택·도메인 명사) 2-3개를 추출해 **학습 INDEX 테이블 행만** grep한다.
매칭 상위 3건까지 본문을 INDEX 위치 컬럼이 가리키는 곳(`knowledge/<topic>.md` 또는 인라인)에서 읽어
워커 CONTEXT 블록에 "과거 학습: ..." 으로 그대로(verbatim) 주입한다. 매칭 0건이면 주입 생략 — 질문/지연 금지.

```bash
EXP_DIR=$(ls -d "${CLAUDE_PLUGIN_ROOT}/../cs-experiencing-v"* 2>/dev/null | sort -V | tail -1)
# INDEX 행("|"로 시작)만 매칭 — 본문/헤더 오염 방지
grep -i -E "<키워드1>|<키워드2>" "$EXP_DIR/skills/experiencing/SKILL.md" | grep "^|" | head -3
```

**이유**: SKILL.md 전체(25k+ 토큰)를 읽는 회상은 비용이 학습 가치를 초과한다 — INDEX 1줄/항목 grep이 O(인덱스 행) 비용으로 같은 회상을 준다.

> 예시: 태스크 "worktree에서 vite dev server 안 뜸" → `grep -i -E "worktree|vite" ... | grep "^|" | head -3` → #30 매칭 → `knowledge/git-worktree.md`에서 #30 본문만 Read → 워커 CONTEXT에 주입.

### [R-c] STRATEGIC — CORE.md의 제약·반복 이슈 섹션만 Read

`~/.claude/core-memory/CORE.md`가 존재할 때만 `## Key Decisions`(constraint 항목)와 `## Recurring Issues` 섹션을 Read한다.
파일이 없으면 **조용히 스킵** (0 output, 0 extra tool calls — 기존 graceful-degradation 관례와 동일).
`constraint: yes` 결정과 `hit_count >= 2` 이슈만 워커 CONTEXT에 반영한다.

**이유**: 전략 메모리는 "하지 말 것"의 목록이다 — 제약을 모르는 fan-out은 이미 기각된 방향을 다시 실행한다.

> 예시: CORE.md Key Decisions에 `constraint: yes — vercel --prod는 auto-mode에서 hard block` → ship-lead가 배포 단계를 사용자 실행 안내로 설계.

### [R-d] ERROR — 에러 시그니처가 있을 때만 error-notes grep

요청/입력에 에러 시그니처(stack trace, 실패한 명령 출력, 반복 실패 로그)가 포함된 경우에**만**
`~/.claude/error-notes/INDEX.md`를 핵심 키워드로 grep해 매칭되는 resolved 노트를 먼저 surface한다
(plugins/CLAUDE.md의 기존 "에러 회상" 권고 규칙을 리드 의무로 공식화한 것). 시그니처가 없으면 이 단계는 grep 0회로 건너뛴다.

**이유**: 이미 해결한 에러를 다시 디버깅하는 것이 가장 비싼 중복이다 — 단, 에러가 없는 요청에서의 에러노트 grep은 순수 낭비이므로 조건부로 묶는다.

> 예시: 요청에 `ENOENT: no such file ... node_modules/.bin/vite` 포함 → `grep -i -E "ENOENT|vite" ~/.claude/error-notes/INDEX.md` → resolved 노트 매칭 시 그 해결책을 첫 가설로 채택.

## 예산 (BOUNDED — 상한 고정, 초과 금지)

- grep **≤ 3회** + Read **≤ 2회** (LOOP-PROTOCOL/GATE-LOOP Read와 [R-a]의 find-meta는 이 예산에 포함하지 않는다)
- 워커 CONTEXT에 verbatim 주입하는 학습 본문 **≤ 3건**
- 예산 내에서 다 못 담으면 확장하지 말고 매칭 점수 상위만 남긴다. 상한 도달 시 회상을 종료하고
  `recall:` 헤더에 그 시점까지의 카운트를 기록한다 (종료 사유 = budget cap).

**이유**: 무제한 회상은 리서치로 변질되어 fan-out 예산을 잠식한다 — Phase R은 회상이지 리서치가 아니다.

> 예시: 키워드 3개가 INDEX에서 7건 매칭 → 태스크 문면과 가장 가까운 3건만 본문 Read(2회 Read 상한 내에서 같은 topic 파일은 1회 Read로 묶음) → 나머지 4건은 제목만 헤더 아래 1줄로 언급.

## 준수 헤더 (grep-able) — `recall:` 한 줄

리포트 헤더의 `protocol: LOOP-PROTOCOL [a-f] loaded ...` 줄 바로 다음에 출력한다:

```
recall: E<episodic 매칭 수>/C<core 반영 항목 수>/N<error 노트 매칭 수>
```

이 줄이 없는 리포트는 Phase R 미수행으로 간주한다. 저장소가 없거나 매칭이 0이어도 `recall: E0/C0/N0`을 출력한다
(스킵과 미수행을 구분하기 위해 — 침묵은 증거가 아니다).

**이유**: 프로토콜 준수는 grep 가능한 아티팩트 문자열로만 검증할 수 있다 (LOOP-PROTOCOL 헤더 줄과 동일한 강제 장치, 학습 #71).

> 예시: `recall: E2/C1/N0` = 학습 2건 주입 + CORE.md 제약 1건 반영 + 에러 시그니처 없음(또는 매칭 0).

## 적용 범위

- **표준 Phase R 수행**: plan-lead(CS-plan), design-lead(cs-design), ship-lead(cs-ship), test-lead(CS-test SKILL preflight).
- **기존 풍부한 플로우 유지 + 헤더만 공유**: cs-ceo(Phase G.5 Core Memory Injection + Phase -3 에러노트 recall),
  cs-experiencing(공통 학습 회상 단계) — 자체 플로우를 그대로 수행하되 동일한 `recall: E/C/N` 헤더를 출력한다.
