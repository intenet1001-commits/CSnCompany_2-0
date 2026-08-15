---
description: "CS 세션 종료 자동화 - Session Digest → 4-Agent 병렬 분석 → 학습 게이트 → Selective 버전업 → GitHub push → 구조화 compact 제안 (/cs-end)"
allowed-tools: Bash, Read, Write, Edit, Glob, Grep, Task, Agent, AskUserQuestion
---

# /cs-end — CS Session Closing

세션을 안전하게 종료하면서 학습을 영속화하고 변경된 플러그인을 자동으로 버전업·푸시합니다.

**v2.1 개선 (LSTM/GRU 게이트 패턴 적용):**
- **Session Pre-Pass Digest** (Attention) — 4-Agent가 raw 히스토리 대신 압축 digest 공유 → 토큰 ~60% 절감
- **Selective Version-Up** (GRU Update Gate) — 이번 세션에 실제 사용한 도메인만 버전업
- **Learning Gate** (Input Gate) — 노벨티/임팩트/재사용성 3-axis 점수 기반 품질 게이팅
- **Knowledge Decay Check** (Forget Gate) — 오래된 tactical 노하우 자동 감지
- **구조화 Compact 핸드오프** (Hidden State) — 다음 세션 재개를 위한 5-field 구조화 출력

**v3 신규:**
- **Error Note 점검 + 캡처** (Phase 2.2) — open 에러노트 항상 점검 + 에러→해결 시퀀스 감지 시 ~/.claude/error-notes/ 에 자동 저장 제안

> **자체 완결 원칙:** 이 플러그인은 외부 볼트(CS_V7 등)에 아무것도 읽거나 쓰지 않는다. 학습의 유일한 저장소는 cs-experiencing SKILL.md 노하우 섹션이다 (cs-ceo 노하우 #18, 2026-05-30 / cs-end 적용 2026-06-12).

## ⚠️ Author-Only Command

`/cs-end` is designed for the **plugin author** (`intenet1001-commits`). It commits and pushes changes back to the marketplace repository.

If you are not the author, Phase 4 (git push) is automatically skipped — your local learnings are still saved.

검증 프로토콜 (BLOCKING 첫 단계): fan-out 전 첫 행동으로 plugins/shared/LOOP-PROTOCOL.md를 Read하고, 리포트 헤더에 `protocol: LOOP-PROTOCOL [a-f] loaded (round budget N)` 한 줄을 출력한다. 이 줄이 없는 리포트는 프로토콜 미적용으로 간주한다. verifier 디스패치는 plugins/shared/agents/verifier.md를 따른다. (런타임 경로: `${CLAUDE_PLUGIN_ROOT}/../shared/`)

## 실행 순서

0. **Phase 0 — 플래그 파싱 + Origin 확인** (자동)
0.5. **Phase 0.5 — Session Pre-Pass Digest** ← 신규 (Attention + KV Cache)
1. **Phase 1 — 4-Agent 병렬 분석** (Digest 공유 컨텍스트 주입)
1.5. **Phase 1.5 — Project Memory Owner Handoff** (AgentsToZ 장기기억 에이전트 위임)
2. **Phase 2 — 학습 영속화 + Learning Gate** (3-axis 품질 스코어)
2.2. **Phase 2.2 — Error Note 점검 + 캡처** ← 신규 (open 노트 항상 점검 + 에러→해결 캡처)
2.5. **Phase 2.5 — Knowledge Decay Check** ← 신규 (Forget Gate, 항목 있을 때만)
2.6. **Phase 2.6 — Prompt Patch** ← 신규 (PASS 학습 → 운영 프롬프트 즉시 반영)
2.7. **Phase 2.7 — Patch Verification** ← 신규 (패치 결정적 점검 + verifier 1회)
3. **Phase 3 — Selective 버전업** (DOMAINS_USED 기반 필터링)
4. **Phase 4 — Git commit + push** (atomic commit, marketplace.json 동기화)
5. **Phase 5 — Push 완료 리포트** (두 레포 상태 명확 구분 출력)
6. **Phase 6 — 구조화 세션 Compact 핸드오프** ← 개선 (Hidden State 5-field 포맷)
6.5. **Phase 6.5 — CLAUDE.md 세션 반영** (revise-claude-md 로직 내부 실행, 항상)
6.7. **Phase 6.7 — CLAUDE.md 품질 감사** (claude-md-improver, 누적 학습 N건 도달 시)
7. **Phase 7 — 통합 CLAUDE.md 승인** (6.5 + 6.7 제안 합산 후 단일 승인)

## Phase 0 — 플래그 파싱 + Origin 확인

```bash
PREPASS_RUNNER="$HOME/.claude/plugins/marketplaces/CSnCompany_2-0/plugins/shared/run_prepass.sh"
PREFLIGHT=$(bash "$PREPASS_RUNNER" end-preflight "$@" 2>/dev/null)
_f() { printf '%s' "$PREFLIGHT" | python3 -c "import sys,json;print(json.load(sys.stdin)$1)" 2>/dev/null; }

EXPLICIT_PROJECT=$(_f "['flags']['explicit_project']")
AUTO_NO_PUSH=$(_f "['flags']['auto_no_push']")
NO_DECAY_CHECK=$(_f "['flags']['no_decay_check']")
EXPLICIT_DOMAINS=$(_f "['flags']['explicit_domains']")
PROJECT_DIR=$(_f "['paths']['project']")
PROJECT_NAME=$(_f "['paths']['project_name']")
MARKETPLACE_DIR=$(_f "['paths']['marketplace']")
```

`origin`이 `intenet1001-commits`가 아니면 `AUTO_NO_PUSH=true`로 자동 설정됩니다.

## Phase 0.5 — Session Pre-Pass Digest (Attention + KV Cache 패턴)

**목적:** 4개 에이전트가 각각 전체 세션 히스토리를 읽는 대신, Python이 1회 추출한 compact digest를 공유함으로써 Phase 1 토큰을 ~60% 절감한다.

```bash
VERSIONS=$(bash "$PREPASS_RUNNER" plugin-versions 2>/dev/null)
_v() { printf '%s' "$VERSIONS" | python3 -c "import sys,json;print(json.load(sys.stdin)['$1'])" 2>/dev/null; }
LATEST_EXP=$(_v "cs-experiencing")
SKILL="$LATEST_EXP/skills/experiencing/SKILL.md"

DIGEST=$(bash "$PREPASS_RUNNER" session-digest \
  --skill "$SKILL" \
  --btw-file "$HOME/.claude/.experiencing-btw.json" \
  2>/dev/null)
_d() { printf '%s' "$DIGEST" | python3 -c "import sys,json;print(json.load(sys.stdin)$1)" 2>/dev/null; }

DOMAINS_USED=$(_d "['domains_used']")     # GRU Update Gate: 실제 사용 도메인
SKILL_SNAPSHOT=$(_d "['skill_snapshot']") # 노하우 인덱스 (제목+날짜, 본문 제외)
BTW_PENDING=$(_d "['btw_pending']")       # 미처리 BTW 항목 목록
BTW_COUNT=$(_d "['btw_count']")           # BTW pending 개수
STALE_ENTRIES=$(_d "['stale_entries']")   # Forget Gate: 오래된 항목
STALE_COUNT=$(_d "['stale_count']")       # 오래된 항목 수
```

**DIGEST 유효성 검증** (silent failure 방지 — `2>/dev/null`이 실패를 빈 문자열로 삼키는 것을 막는다):

```bash
DIGEST_FAILED=false
printf '%s' "$DIGEST" | python3 -c "import sys,json; d=json.load(sys.stdin); sys.exit(1 if 'error' in d else 0)" \
  || {
    # 1회 재실행 — 이번엔 stderr를 숨기지 않고 사용자에게 보여준다
    DIGEST=$(bash "$PREPASS_RUNNER" session-digest \
      --skill "$SKILL" \
      --btw-file "$HOME/.claude/.experiencing-btw.json")
    printf '%s' "$DIGEST" | python3 -c "import sys,json; d=json.load(sys.stdin); sys.exit(1 if 'error' in d else 0)" \
      || DIGEST_FAILED=true
  }
```

`DIGEST_FAILED=true`이면 stderr 내용을 사용자에게 출력하고 Phase 3의 (b) 규칙을 적용한다 (자동 fallback 금지).

**EXPLICIT_DOMAINS 오버라이드:** `--domains test,plan` 플래그가 있으면 DOMAINS_USED를 해당 값으로 덮어씀.

```bash
if [ -n "$EXPLICIT_DOMAINS" ]; then
  DOMAINS_USED="$EXPLICIT_DOMAINS"
fi
```

**Digest 요약 출력** (디버그용) — 출력에 반드시 포함: 사용 도메인(없으면 "탐지 없음" 명시), 노하우 항목 수, BTW pending 개수, 오래된 항목 수. 포맷은 자유.

**성공 기준 선언 (LOOP-PROTOCOL [b], Phase 1 fan-out 직전 필수):** Digest 요약 직후 한 줄로 출력한다 — `성공 기준: 4-Agent(doc-updater/learning-extractor/version-scout/followup-suggester) 각각 유효 JSON 반환 + Phase 2 Learning Gate 판정 완료 + (push 대상 시) Phase 4 커밋 성공`. Phase 5·6 리포트는 이 기준 대비 채점 결과(`기준 대비: PASS/FAIL (n/n 통과)`)를 첫 줄에 출력한다.

## Phase 1 — 4-Agent 병렬 분석 (Shared Digest 주입)

4개 에이전트를 **단일 메시지에 병렬로** 스폰합니다.

각 에이전트는 raw 세션 히스토리 대신 **SESSION_DIGEST**를 공유 컨텍스트로 수신합니다:

- **SKILL_SNAPSHOT** — 노하우 인덱스 (Learning Gate 점수 계산용)
- **DOMAINS_USED** — 사용 도메인 목록 (version-scout 필터용)
- **BTW_PENDING** — 미처리 BTW 항목 (learning-extractor + followup-suggester 우선 처리)
- **STALE_ENTRIES** — 오래된 항목 목록 (Decay Check 참고용)

**에이전트별 지시사항:**

| 에이전트 | 역할 | Digest 활용 |
|---------|------|------------|
| `doc-updater` | 문서 업데이트 필요 항목 추출 | DOMAINS_USED로 관련 도메인 디렉토리만 스캔 |
| `learning-extractor` | TIL/패턴/결정 사항 추출 + Learning Gate 사전 점수화 | SKILL_SNAPSHOT으로 노벨티 판정, BTW_PENDING 선순위 처리 |
| `version-scout` | 변경 플러그인 탐지 | DOMAINS_USED를 1차 필터로 사용 |
| `followup-suggester` | 다음 세션 follow-up 제안 | BTW_PENDING 항목을 최우선 follow-up으로 포함 |

이 플러그인의 `agents/` 디렉토리에 정의된 4개 에이전트(`doc-updater`, `learning-extractor`, `version-scout`, `followup-suggester`)를 **단일 메시지에 병렬 스폰**하여 실행합니다. 각 에이전트 프롬프트에 위 Digest 변수들을 주입합니다. 모델 배정은 각 agent 파일의 frontmatter를 따릅니다 (learning-extractor만 sonnet, 나머지는 haiku).

어떤 에이전트 결과가 비어 있거나 명백히 불완전하면 **해당 에이전트만 1회 재실행**한다 (재실행도 실패하면 그 에이전트는 N/A로 처리하고 진행 — 무한 재시도 금지).

**계약 체크 (Phase 2 진입 전):**
- `learning-extractor` 후보에 상황/발견/교훈/tier/pre_scores 중 하나라도 누락 → 해당 에이전트에 1회 재포맷 요청.
- `version-scout` 출력에 domain 매핑이 없으면 → Phase 3의 fallback 규칙 (a) (AskUserQuestion 확인)로 처리한다. 자동 전체 버전업 금지.
- `doc-updater` 후보에 file/needed_change/reason 중 하나라도 누락되면 해당 항목만 드롭하고 나머지는 사용한다. 배열 전체가 파싱 불가하면 doc-updater를 1회 재실행한다 (140번째 줄 "해당 에이전트만 1회 재실행" 규칙 재사용, 재실행도 실패하면 N/A 처리).

## Phase 1.5 — Project Memory Owner Handoff

장기기억 저장의 단일 소유자는 AgentsToZ가 프로젝트에 설치한 장기기억 에이전트다.
CSnCompany는 별도 전역 기억을 생성하거나 직접 합성하지 않는다.

```bash
PROJECT_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
if [ ! -f "$PROJECT_ROOT/.agent-memory/config.json" ]; then
  PROJECT_ROOT="$PWD"
  while [ "$PROJECT_ROOT" != "/" ] && [ ! -f "$PROJECT_ROOT/.agent-memory/config.json" ]; do
    PROJECT_ROOT="$(dirname "$PROJECT_ROOT")"
  done
fi
PROJECT_MEMORY_CONFIG="$PROJECT_ROOT/.agent-memory/config.json"
```

`PROJECT_MEMORY_CONFIG`가 없으면 조용히 Phase 2로 진행한다. 있으면 현재 표면의 프로젝트 로컬
`remember-session` 어댑터를 한 번만 호출한다. 후보 경로는 다음 순서이며, **어댑터의 지침을
그대로 실행**하고 저장 로직을 이 명령 안에 복제하지 않는다.

```text
.claude/skills/remember-session/SKILL.md
.agents/skills/remember-session/SKILL.md
.codex/skills/remember-session/SKILL.md
```

어댑터 입력에는 Phase 0.5/1에서 이미 계산한 다음의 컴팩트한 결론만 전달한다.

- 세션 목표와 실제 완료 결과
- 검증된 결정/제약/워크플로 변화
- 반복 실패의 원인과 확인된 해결법
- 미해결 충돌은 해결된 사실처럼 쓰지 않고 contested evidence로 전달

raw 대화, 비밀값, 임시 상태, 전체 diff, 모든 에이전트 출력을 복제하지 않는다. 기억 에이전트가
현재 `memoryId`와 기존 entry ID를 읽고 병합·저장·mark-remembered·Push를 소유한다.

어댑터가 없으면 직접 폴백 저장하지 말고 다음 한 줄만 남긴 뒤 Phase 2로 계속한다:

```text
⚠️ Project Memory handoff skipped: AgentsToZ remember-session adapter missing
```

어댑터의 **로컬 기억 갱신이 성공한 뒤** cs-memory가 설치되어 있으면, 변경 포인터만 무토큰으로
수집한다. 원격 Push만 실패한 경우에도 로컬 갱신은 성공으로 보고 수집하며 Push 경고는 별도로 남긴다:

```bash
MEMORY_PLUGIN=$(ls -d "$HOME/.claude/plugins/marketplaces/CSnCompany_2-0/plugins/cs-core-memory-v"* 2>/dev/null | sort -V | tail -1)
if [ -z "$MEMORY_PLUGIN" ] && [ -n "$LATEST_EXP" ] && [ -d "$(dirname "$LATEST_EXP")/cs-core-memory-v1" ]; then
  MEMORY_PLUGIN="$(dirname "$LATEST_EXP")/cs-core-memory-v1"
fi
if [ -z "$MEMORY_PLUGIN" ] && [ -d "$PROJECT_ROOT/plugins/cs-core-memory-v1" ]; then
  MEMORY_PLUGIN="$PROJECT_ROOT/plugins/cs-core-memory-v1"
fi
MEMORY_COLLECTOR="$MEMORY_PLUGIN/skills/learn/scripts/memory_learning.py"
if [ -f "$MEMORY_COLLECTOR" ]; then
  uv run --quiet --no-project python "$MEMORY_COLLECTOR" collect \
    --project "$PROJECT_ROOT" --no-registry --no-cwd --quiet
fi
```

이 수집은 `.agent-memory`를 수정하지 않고 `memoryId + entryId + contentVersionHash` 포인터만
갱신한다. 실패해도 기억 저장 성공을 롤백하지 않으며, 실패 사유 한 줄을 최종 리포트에 남긴다.

## Phase 2 — 학습 영속화 + Learning Gate (Input Gate 패턴)

`learning-extractor` 결과를 cs-experiencing 노하우 섹션에 저장하기 전에 **3-axis 품질 게이트**를 통과시킵니다.

### Learning Gate 채점 기준 (임계값: 4/6)

각 학습 후보에 대해 다음 3개 축으로 점수를 계산합니다:

**Axis 1: 노벨티 (0-2점)** — 본문 비교 필수 (제목 비교만으로 확정 금지)

노벨티는 SKILL_SNAPSHOT(제목+날짜)만으로 확정할 수 없다. 각 후보에 대해:
1. 후보의 핵심 키워드 2-3개로 `grep -rn`을 `$SKILL` **및 그 형제 디렉토리 `$(dirname $SKILL)/knowledge/`** 전체 본문에 실행한다 — 본문 오프로드(8.2.0+)로 대부분의 기존 항목이 SKILL.md가 아니라 knowledge/*.md에 있다. `$SKILL`만 검색하면 이관된 항목과의 중복을 놓친다.
2. 매칭된 기존 항목(최대 3개, SKILL.md 인라인이든 knowledge/*.md 소재든 무관)의 전체 텍스트(상황/발견/교훈 + 기존 addendum)를 Read하여 비교한 뒤에만 점수를 부여한다.

- 2점: 본문 비교 결과 유사 항목 없음 (새로운 발견) — **전체 본문 비교를 수행하지 않은 후보는 최대 1점 (2점 금지)**
- 1점: 관련 항목은 있으나 새로운 각도/구체사항 추가
- 0점: 기존 항목과 실질적으로 동일 — **상황+교훈이 겹치면 제목이 달라도 0점** (입증 책임은 후보 쪽에 있다)

**중복-갱신 규칙:** 기존 항목 #N과의 겹침으로 노벨티 1점이 된 후보는 새 번호 항목을 만들지 않고, 항목 #N 하단에 날짜 붙은 addendum 1줄로 추가한다.

**Axis 2: 임팩트 (0-2점)**
- 2점: 블로커 해결 / 세션의 핵심 돌파구
- 1점: 효율을 높인 유용한 인사이트
- 0점: 이미 자명한 편의 메모

**Axis 3: 재사용성 (0-2점)**
- 2점: 이 도메인/패턴을 사용하는 모든 미래 세션에 적용 가능
- 1점: 이 코드베이스/프로젝트 계열에 한정 적용
- 0점: 특정 파일명·버전·타이밍에 종속된 일회성 정보

**근거 의무 (EVIDENCE 규칙):** 모든 후보는 `근거` 필드(세션에서 직접 인용한 command+output 스니펫 또는 대화 인용)를 가져야 한다. **근거가 비어 있으면 tier를 tactical로 강등한다 (principle 금지).**

**Principle-tier 스켑틱 검증:** tier=principle 후보가 1개 이상이면, 게이트 판정 전에 경량 스켑틱 Task 1개(sonnet, plugins/shared/agents/verifier.md의 반박 자세 준용)를 스폰한다. 입력은 principle 후보들(근거 포함)이며, 각 후보에 대해 다음 중 하나를 판정한다:
- `CONFIRM` — 근거가 principle(플랫폼/언어/아키텍처 수준 안정 지식)을 뒷받침함
- `DOWNGRADE` — 지식 자체는 유효하나 버전/설정 종속 → tier를 tactical로 변경
- `REJECT` — 근거가 주장을 뒷받침하지 못함 → 후보 드롭 (사유 1줄 첨부)

스켑틱은 1회만 실행한다 (루프 금지).

**게이트 판정:**
```
총점 4-6 → ✅ PASS:    SKILL.md에 저장 (tier: principle|tactical 함께 기록)
총점 2-3 → ⚠️ PENDING: Phase 5 리포트에만 출력, 저장 안 함
총점 0-1 → ❌ REJECT:  조용히 드롭 (출력 없음)
```

**저장 포맷** (PASS된 항목):
```markdown
### [N]. [학습 제목] ([YYYY-MM-DD])
<!-- tier: principle|tactical -->
- **상황**: [어떤 작업 중에 발견했는지]
- **발견**: [구체적으로 무엇을 배웠는지]
- **교훈**: [다음에 어떻게 적용할지]
- **근거**: [세션 증거 인용 1줄]
```

- **principle**: 플랫폼/언어 동작, 아키텍처 패턴 등 시간이 지나도 안정적인 지식
- **tactical**: 특정 버전·설정·워크어라운드 등 변경 가능성이 있는 전술적 지식

**0개 저장 시:** "0 learnings persisted this session" 출력 후 Phase 2.5로 진행 (오류 없음).

CHANGELOG도 함께 갱신합니다.

**LEARNED_COUNT 업데이트 (Phase 6.5/6.7 카운터용):**

Learning Gate PASS 건수를 확보한 직후:

```bash
LEARNED_COUNT=<PASS 건수>   # 0이면 0으로 명시

STATE_DIR="$HOME/.claude/state"
STATE_FILE="$STATE_DIR/cs-end-counter.json"
mkdir -p "$STATE_DIR"

# 파일 없으면 초기값으로 생성
[ -f "$STATE_FILE" ] || python3 -c "
import json, pathlib
pathlib.Path('$STATE_FILE').write_text(json.dumps({
  'accumulated': 0, 'threshold': 5, 'last_improver_run': ''
}, indent=2))
"

# 누적 카운터 업데이트
UPDATED=$(python3 -c "
import json, sys
f = open('$STATE_FILE')
d = json.load(f)
f.close()
d['accumulated'] = d.get('accumulated', 0) + $LEARNED_COUNT
print(json.dumps(d, indent=2))
")
echo "$UPDATED" > "$STATE_FILE"

ACCUMULATED=$(python3 -c "import json,sys; print(json.load(open('$STATE_FILE'))['accumulated'])")
THRESHOLD=$(python3 -c "import json,sys; print(json.load(open('$STATE_FILE'))['threshold'])")
```

## Phase 2.2 — Error Note 점검 + 캡처 (cs-error-notes 연동)

**`--no-error-notes` 플래그가 있으면 이 Phase를 조용히 스킵합니다. 없으면 항상 실행합니다.**

### Part A — 기존 Open 에러노트 점검 (항상 실행)

```bash
ERROR_NOTES_DIR="$HOME/.claude/error-notes"
INDEX="$ERROR_NOTES_DIR/INDEX.md"
```

INDEX.md가 존재하면 open 상태 노트를 집계합니다:

```bash
OPEN_COUNT=$(grep -c "| open |" "$INDEX" 2>/dev/null || echo 0)
```

**open 노트가 1개 이상이면** 출력에 반드시 포함: open 노트 개수, 확인 명령(`/cs-error-notes list --open`), 최신 open 노트의 ID+제목. 이번 세션에서 해결한 에러가 있어 보이면 `/cs-error-notes resolve ERR-xxx` 추천도 포함한다.

**open 노트가 0개이면** "미해결 없음" 취지의 한 줄만 출력한다.

---

### Part B — 신규 에러→해결 캡처 (감지 시에만)

`learning-extractor` 결과에서 에러→해결 시퀀스를 감지합니다:
- 상황 필드에 "에러", "오류", "실패", "error", "bug", "crash" 포함
- 발견 필드에 "해결", "수정", "fix", "resolved" + 원인 분석 포함

감지 시 AskUserQuestion으로 저장 여부를 확인한다 — 의도: 에러→해결 시퀀스가 감지되었음을 알리고 저장할지 묻는다. 옵션은 (1) 저장 (`~/.claude/error-notes/`에 기록), (2) 건너뛰기. 문구는 자유.

건너뛰기 선택 시: 저장하지 않고 Phase 2.5로 진행하되, learning-extractor 결과 원본은 그대로 유지한다 (error-ref 태그 없음). "감지됐지만 미저장"과 "미감지"는 이 태그 유무로만 구분되며 그 외 산출물 차이는 없다.

저장 선택 시:
- learning-extractor 결과를 5-필드 포맷으로 변환 (상황/문제점/시도/원인/해결점)
- ERR-YYYY-MM-DD-NNN ID 자동 부여
- `~/.claude/error-notes/` 에 Write, INDEX.md 갱신
- Learning Gate PASS 항목에 `<!-- error-ref: [ID] -->` 태그 추가
- 저장 완료 출력에 반드시 포함: 부여된 노트 ID

미감지 → 조용히 Phase 2.5로 진행.

---

## Phase 2.5 — Knowledge Decay Check (Forget Gate 패턴)

**`--no-decay-check` 플래그가 있거나 `STALE_COUNT == 0`이면 이 Phase를 조용히 스킵합니다.**

`STALE_ENTRIES`에 항목이 있을 때만 출력한다 — 출력에 반드시 포함: 30일+ 경과 tactical 항목 각각의 번호/제목/날짜/경과일, 그리고 "아카이빙 권장이며 자동 삭제가 아님"이라는 안내. 포맷은 자유.

각 stale 항목에 대해:
1. SKILL.md에서 해당 항목의 전체 내용 읽기
2. 이번 세션 지식으로 볼 때 여전히 정확한지 평가
3. 구식인 경우: 항목 하단에 주석 추가 (삭제 금지)

```markdown
<!-- deprecated: [이유] — [YYYY-MM-DD] -->
```

**Decay 완료 요약** — 출력에 반드시 포함: 검토한 항목 수, deprecated 주석을 추가한 항목 수.

### 인용 기반 우선순위 (Forget Gate 보강)

stale 항목 검토 시 인용 횟수(이번 세션 포함, 해당 항목이 실제 참조·적용된 흔적)를 함께 판단한다:

- **인용 0회 tactical 항목** → deprecation 검토 최우선 순위 (위 deprecated 주석 절차 적용)
- **인용 多 항목** → 운영 프롬프트(SKILL/agents 지시문)로의 승격 후보로 플래그 — Phase 2.6 Prompt Patch 입력에 포함
- **principle 항목 중 ~180일 이상 경과** → 검토 대상으로 표시만 한다. **principle은 절대 자동 deprecate 하지 않는다** (사용자 검토 필요 표시만).

## Phase 2.6 — Prompt Patch (PASS 학습 → 운영 프롬프트 반영)

**Learning Gate PASS 항목이 0개이면 조용히 스킵합니다.**

각 PASS 학습에 대해 다음 질문에 답한다: **"어떤 SKILL/agent 지시문을 바꾸면 이 실수가 재발할 수 없는가?"**

답에 따라 3가지 중 하나로 처리한다:

| 처리 | 조건 | 액션 |
|------|------|------|
| **PATCH** | 대상 파일·수정 내용이 명확하고 이번 세션에서 적용 가능 | 해당 SKILL/agents/*.md에 지금 Edit 적용 + 학습 항목에 `✅ 반영됨 (YYYY-MM)` 표시 |
| **MEMO** | 프롬프트 변경 대상이 없고 지식 축적만 필요 | 지식 파일(SKILL.md 노하우 섹션)에만 저장 (Phase 2 저장으로 충분) |
| **DEFER** | 대상 파일은 알지만 이번 세션에서 적용이 위험/불명확 | `~/.claude/.experiencing-btw.json`에 pending patch로 기록 (`{"type":"pending-patch","target":"<파일 경로>","change":"<1줄>","learning":"<제목>"}`) |

PATCH가 1건 이상 적용되면 Phase 2.7로 진행한다. PATCH 0건이면 Phase 2.7을 조용히 스킵한다.

## Phase 2.7 — Patch Verification (적용된 패치 검증)

Phase 2.6에서 적용한 각 PATCH에 대해:

**1. 결정적 점검 (bash/Read):**
- 패치된 파일의 frontmatter가 여전히 유효하게 파싱되는지 (`---` 블록 + YAML)
- 패치가 참조하는 경로(파일/디렉토리)가 실제로 존재하는지

**2. Verifier Task 1회** (plugins/shared/agents/verifier.md, 패치된 파일을 cold로 Read):
- "Sonnet 실행자가 이 지시문을 모호함 없이 따를 수 있는가?"
- "이 플러그인의 다른 지시문과 모순되지 않는가?"

**판정:**
- `CONFIRMED` → 패치 유지, Phase 4 스테이징 대상에 포함
- `REFUTED` → **패치를 revert**하고 DEFER로 강등 (verifier의 반박 사유를 `.experiencing-btw.json` pending patch 항목에 첨부)
- `UNCERTAIN` → REFUTED와 동일하게 처리 (revert + DEFER 강등)

검증은 패치당 1회만 수행한다 (재패치 루프 금지 — 실패한 패치는 다음 세션의 DEFER 큐로).

## Phase 3 — Selective 버전업 (GRU Update Gate 패턴)

`version-scout` 결과를 **DOMAINS_USED 기반으로 필터링**합니다.

**필터링 로직:**
- `DOMAINS_USED`에 포함된 도메인만 버전업 후보
- `--domains` 명시 플래그 → 해당 값으로 오버라이드

**Fallback 규칙 (두 경우를 구분한다 — 묵시적 전체 버전업 금지):**

(a) **DIGEST 유효 + domains_used 비어 있음** → 변경된 플러그인 목록을 출력하고 AskUserQuestion으로 확인한다 — 의도: 도메인 탐지가 없었음을 알리고 변경된 플러그인을 어떻게 처리할지 묻는다. 옵션은 (1) 변경된 플러그인 전체 버전업, (2) `--domains` 값으로 수동 지정, (3) 이번 세션 버전업 스킵. 문구는 자유.

(b) **DIGEST_FAILED=true** (Phase 0.5 검증 실패) → 자동 fallback 금지. `--domains` 명시 또는 사용자의 명시적 확인 없이는 어떤 버전업도 하지 않는다.

**버전업 스코프 출력** — 출력에 반드시 포함: 변경 탐지된 각 플러그인에 대해 버전업 진행/스킵 여부와 그 사유(이번 세션 사용/미사용). 포맷은 자유.

이후 `$SKILL`의 version-up 프로토콜에 따라 선택된 도메인만 버전업을 진행합니다 (VERSION 파일 + plugin.json bump).

## Phase 4 — Git commit + push (atomic)

**Skip guard (이 Phase의 첫 판정):** `AUTO_NO_PUSH=true` 또는 `--no-push` 또는 `--learning-only`이면
Phase 4를 스킵한다고 한 줄로 알리고(사유: no-push 모드) 커밋 없이 Phase 5로 진행한다 (상태: SKIPPED).

### 1. 스테이징 스코프 (마켓플레이스 레포만, 명시적 경로만)

**`git add -A` / `git add .` 절대 금지.** 스테이징 대상은 다음 세 가지뿐이다:

```bash
# (1) Phase 3에서 버전업된 플러그인 디렉토리 (신규 dir 추가 + 이전 dir 정리 삭제)
git -C "$MARKETPLACE_DIR" add plugins/<bumped-domain>-v*/
git -C "$MARKETPLACE_DIR" add -u "plugins/<bumped-domain>-v*"   # 삭제 반영 — 이전/신규 버전 디렉토리만 (plugins/ 전체 금지)
# (2) marketplace.json
git -C "$MARKETPLACE_DIR" add .claude-plugin/marketplace.json
# (3) Phase 2에서 갱신된 cs-experiencing SKILL.md + CHANGELOG (+ Phase 2.6 PATCH 파일)
# 주의: 존재하지 않는 경로를 git add에 섞으면 exit 128로 전체가 실패한다 — 각각 분리 + 가드
git -C "$MARKETPLACE_DIR" add "$LATEST_EXP/skills/experiencing/SKILL.md"
[ -f "$LATEST_EXP/CHANGELOG.md" ] && git -C "$MARKETPLACE_DIR" add "$LATEST_EXP/CHANGELOG.md"
```

이 경로들 밖의 untracked 파일(`.claude/`, `__pycache__/`, `.env` 등)은 **절대 스테이징하지 않는다.**

### 1.5 라우팅/버전 정합성 게이트 (R7/R9 — commit 전 차단)

```bash
# (a) 라우팅 단일 출처 검증: 라우팅 규칙 ↔ marketplace.json drift 탐지
python3 "$MARKETPLACE_DIR/plugins/shared/scripts/routing_sync.py" check
# ok=false → `routing_sync.py write`로 인벤토리 재생성 후 unknown 타깃을 수동 정리, 재검증

# (b) 버전업된 각 플러그인의 메타데이터 정합성 (VERSION == plugin.json == SKILL frontmatter)
python3 "$MARKETPLACE_DIR/plugins/shared/scripts/pre_pass.py" version-check "<bumped-plugin-dir>"
# ok=false → VERSION 파일 값으로 동기화 후 재검증. ok 전에는 commit하지 않는다.
```

### 2. Staged-set 검증

```bash
git -C "$MARKETPLACE_DIR" diff --cached --name-only
```

모든 경로가 `plugins/<bumped-domain>-v*/`, `.claude-plugin/marketplace.json`, Phase 2 학습 파일(또는 Phase 2.6 PATCH 파일) 중 하나에 속하는지 확인한다. 예상 밖 경로가 스테이징되어 있으면 unstage하고 경고를 출력한다. 워킹 트리에 남은 untracked 잡파일 때문에 abort하지 않는다 (porcelain clean을 요구하지 않음).

### 3. Atomic commit

버전 디렉토리 + marketplace.json + 학습 파일을 **단일 커밋**으로 묶는다 (marketplace.json이 같은 커밋에 없는 디렉토리를 가리키는 일이 없도록).

커밋 메시지 템플릿 (기존 히스토리 스타일):

```
feat(<domains>): 학습 <N>건 + <plugin> v<X> 버전업 (YYYY-MM-DD)
```

### 4. Push + 복구

```bash
git -C "$MARKETPLACE_DIR" push origin main
```

- 거부(rejected) 시 → `git -C "$MARKETPLACE_DIR" pull --rebase origin main` 1회 실행 후 재push.
- 인증 실패 또는 2번째 실패 시 → 커밋은 로컬에 그대로 두고 Phase 5에서 `⚠️ UNPUSHED`로 보고한다 (루프 금지).

### 5. 프로젝트 레포는 건드리지 않는다

Phase 4는 **마켓플레이스 레포만** 커밋/푸시한다. `PROJECT_DIR`는 절대 자동 커밋하지 않으며, Phase 5가 ahead/behind 상태와 수동 push 명령만 안내한다.

## Phase 5 — Push 완료 리포트

모든 phase가 끝난 뒤 두 레포의 push 상태를 **반드시 구분하여** 출력합니다.

### 탐지 로직

```bash
# Phase 0 PREFLIGHT에서 이미 확보된 값 사용
MARKETPLACE_DIR="$HOME/.claude/plugins/marketplaces/CSnCompany_2-0"
MARKETPLACE_NAME="CSnCompany_2-0"
# PROJECT_DIR, PROJECT_NAME은 Phase 0 PREFLIGHT에서 설정됨

# push 완료 후 최신 git 상태 조회 (Python — Phase 4 이후 호출)
check_push_status() {
  bash "$PREPASS_RUNNER" git-status "$1" 2>/dev/null
  # Returns JSON: {"state":"pushed","ahead":"0","behind":"0","branch":"main","remote":"owner/repo"}
}
_ps() { printf '%s' "$1" | python3 -c "import sys,json;print(json.load(sys.stdin).get('$2',''))" 2>/dev/null; }
```

### 출력 요건

Phase 4 완료 직후 리포트를 출력한다. 출력에 반드시 포함 (포맷은 자유, 두 레포를 시각적으로 구분할 것):

- **커버리지 (LOOP-PROTOCOL [d], 목록 맨 앞에 출력)**: `커버리지: X/4 에이전트 (완전 응답 기준)` — Phase 1에서 재실행 후에도 실패해 N/A 처리된 에이전트가 있으면 이름을 함께 명시 (`N/A: <에이전트명>`). 4/4면 N/A 목록 생략.
- **마켓플레이스 레포**: 레포 이름 + 상태(PUSHED/SKIPPED) + PUSHED면 branch와 remote, SKIPPED면 사유(--no-push 모드 / author 아님)
- **프로젝트 레포**: 레포 이름 + 상태(PUSHED/UNPUSHED/해당없음) + UNPUSHED면 미push 커밋 수와 수동 push 명령(`git -C <path> push origin <branch>`)

### 판정 기준

| 상태 | 조건 |
|------|------|
| `✅ PUSHED` | `ahead == 0` (local이 remote와 동일하거나 push 직후) |
| `⚠️ UNPUSHED` | `ahead > 0` (local에 push 안 된 커밋 존재) |
| `⏭️ SKIPPED` | `--no-push` 플래그 또는 `AUTO_NO_PUSH=true` |
| `─ 해당없음` | 프로젝트 레포 탐지 불가 또는 마켓플레이스와 동일 |

## Phase 6 — 구조화 세션 Compact 핸드오프 (Hidden State 패턴)

**`--no-compact` 또는 `--learning-only` 모드이면 이 Phase를 스킵합니다.**

Phase 1의 `learning-extractor`·`followup-suggester` 결과와 Session Digest를 바탕으로
**5-field 구조화 핸드오프**를 생성합니다. 다음 세션이 구조 없이 복구하는 대신 즉시 이어서 작업할 수 있습니다.

### 5-field 구성 규칙

| 필드 | 출처 | 내용 |
|------|------|------|
| `DONE` | `followup-suggester` 완료 목록 (source:session 중 완료 표시분) | 이번 세션 완료 항목 1-2줄 |
| `LEARNED` | Learning Gate 통과 항목 중 최고 점수 1개 | 핵심 발견 1줄 |
| `DOMAINS` | `DOMAINS_USED` | 이번 세션 활성 CS 도메인 |
| `NEXT` | `followup-suggester` 최우선 항목 (`doc-updater` needed_change가 있으면 그중 우선순위 1건을 합산) | 다음 세션 첫 번째 구체적 액션 |
| `BTWS` | `BTW_COUNT` + `BTW_PENDING` 첫 항목 제목 | 미처리 BTW 수 + 최우선 1개 |

`doc-updater`는 "이미 완료된 것"이 아니라 "아직 반영 안 된 문서 변경 필요 항목"(needed_change/reason)을 산출하므로 `DONE`이 아니라 `NEXT`에 합류시킨다 — 두 산출물의 의미가 반대이기 때문이다.

`/compact` 인자는 DONE + LEARNED 필드를 1-2줄로 합성하여 생성합니다.

### 출력 요건

출력에 반드시 포함 (포맷은 자유):

1. 세션 종결이 완료되었고 context 정리를 권한다는 안내
2. 복사해 실행할 수 있는 `/compact [DONE 요약 + LEARNED 핵심 1-2줄]` 한 줄
3. 5-field 재개 정보 — `DONE` / `LEARNED`(없으면 "저장된 학습 없음" 명시) / `DOMAINS` / `NEXT` / `BTWS`(pending 개수 + 최우선 1개 또는 "없음") 각 필드를 라벨과 함께. Phase 5에서 N/A 처리된 에이전트가 1개 이상이면 `DONE` 필드 끝에 `(N/A: <에이전트명>)`을 덧붙여 커버리지 결손을 다음 세션에도 전달한다 (LOOP-PROTOCOL [d]).
4. 대안으로 `/clear` (완전 초기화) 안내

**예시:**
```
/compact 2026-05-13 cs-end LSTM게이트 개선 적용 완료. Session Pre-Pass로 Phase1 토큰 ~60% 절감 패턴 확립

DONE    : cs-end v2.1 개선 (Digest + Learning Gate + Selective 버전업 + 구조화 compact)
LEARNED : session-digest 서브커맨드가 SKILL.md 노하우 헤더를 regex로 파싱, 4에이전트에 공유해 토큰 절감
DOMAINS : cs-end
NEXT    : 실제 세션에서 /cs-end 실행 후 Phase1 토큰 절감 측정 확인
BTWS    : 0개 pending — 없음
```

## Phase 6.5 — CLAUDE.md 세션 반영 (항상 실행)

**`--no-compact` 또는 `--learning-only` 이면 스킵합니다.**

revise-claude-md 로직을 내부에서 실행하되, 변경을 즉시 적용하지 않고 **버퍼에 저장**합니다.

### Step 1 — 반영 대상 추출

이번 세션에서 다음 중 해당하는 항목을 확인합니다:
- 새로 발견한 bash 명령 / 워크플로우
- 코드 스타일 패턴 / 환경 quirk / gotcha
- 반복될 가능성이 있는 설정 변경
- Learning Gate PASS 항목 중 CLAUDE.md에 기록할 만한 인사이트

반복될 가능성 없는 일회성 fix는 제외합니다.

### Step 2 — CLAUDE.md 파일 탐색

```bash
find . -name "CLAUDE.md" -o -name ".claude.local.md" 2>/dev/null | head -20
```

각 파일에 대해 추가 위치를 판단합니다:
- `CLAUDE.md` — 팀 공유 (git tracked)
- `.claude.local.md` — 개인/로컬 (gitignored)

### Step 3 — 제안 초안 생성

추가할 내용이 있으면 diff 형식으로 버퍼에 저장합니다:

```
[6.5-BUFFER]
파일: ./CLAUDE.md
+ <한 줄 요약>
```

**없으면 버퍼 비움** (Phase 7에서 "세션 반영: 추가 없음" 표시).

간결성 기준:
- 1개념 1줄
- 이미 존재하거나 자명한 내용은 제외
- 일회성 fix는 제외

---

## Phase 6.7 — CLAUDE.md 품질 감사 (조건부)

**트리거 조건:** `ACCUMULATED >= THRESHOLD` (기본 threshold=5)

```bash
if [ "$ACCUMULATED" -ge "$THRESHOLD" ] 2>/dev/null; then
  TRIGGER_IMPROVER=true
else
  TRIGGER_IMPROVER=false
fi
```

**`TRIGGER_IMPROVER=false`이면:** `[카운터: $ACCUMULATED/$THRESHOLD]` 한 줄만 출력하고 Phase 7로 진행합니다.

**`TRIGGER_IMPROVER=true`이면:** claude-md-improver 로직(Phase 1-3)을 실행합니다.

### Discovery (claude-md-improver Phase 1)

```bash
find . -name "CLAUDE.md" -o -name ".claude.md" -o -name ".claude.local.md" 2>/dev/null | head -50
```

### Quality Assessment (claude-md-improver Phase 2)

각 파일을 6개 기준으로 평가합니다:

| 기준 | 비중 |
|------|------|
| Commands/workflows 문서화 | High |
| Architecture 명확성 | High |
| 비자명 패턴 기록 | Medium |
| 간결성 | Medium |
| 최신성 | High |
| 실행 가능성 | High |

등급: A(90-100) / B(70-89) / C(50-69) / D(30-49) / F(0-29)

### 제안 생성 (claude-md-improver Phase 3)

개선이 필요한 파일에 대해 diff 형식으로 버퍼에 저장합니다:

```
[6.7-BUFFER]
파일: <경로> (현재 등급: X → 예상 등급: Y)
+ <추가 내용>
```

### 카운터 리셋

```bash
python3 -c "
import json
f = open('$STATE_FILE')
d = json.load(f)
f.close()
d['accumulated'] = 0
d['last_improver_run'] = '$(date +%Y-%m-%d)'
open('$STATE_FILE', 'w').write(json.dumps(d, indent=2))
"
```

---

## Phase 7 — 통합 CLAUDE.md 승인

**6.5-BUFFER와 6.7-BUFFER가 모두 비어 있으면** "CLAUDE.md 업데이트 제안 없음" 한 줄만 출력하고 종료합니다.

하나라도 있으면 통합 제안을 표시하고 AskUserQuestion으로 승인을 요청합니다.

### 출력 형식

```
━━━ Phase 7: CLAUDE.md 업데이트 제안 ━━━

[6.5 세션반영] ./CLAUDE.md
  + ## Gotchas
  + - cs-end --no-push: origin이 intenet1001-commits가 아닐 때 자동 활성화

[6.7 품질감사] ./plugins/CLAUDE.md  (C→B 예상)   ← TRIGGER_IMPROVER=true 시에만
  + ## Commands
  + - /cs-end --domains test,plan: 버전업 도메인 수동 지정

카운터: $ACCUMULATED/$THRESHOLD (리셋됨 or 현재값)
```

### 승인 방식

AskUserQuestion으로 각 파일별 옵션을 제시합니다:
- **all** — 모든 제안 적용
- **번호 선택** — 일부만 적용 (예: "1, 3")
- **skip** — 이번엔 건너뜀

### 적용

승인된 항목에 대해 Edit 툴로 CLAUDE.md 파일에 직접 적용합니다.

적용 후 "Phase 7 완료: X개 파일 업데이트됨" 출력.

---

## 사용 예

```
/cs-end                                        # 표준 종료 (Digest → 분석 → 게이트 → 버전업 → push → compact)
/cs-end --project /path/to/repo               # 프로젝트 레포 명시
/cs-end --no-push                             # push 생략 (로컬만)
/cs-end --no-compact                          # Phase 6 + 6.5 + 6.7 + 7 생략
/cs-end --learning-only                       # 학습 추출/저장만 (버전업/push/compact/CLAUDE.md 생략)
/cs-end --no-decay-check                      # Phase 2.5 Forget Gate 스킵
/cs-end --no-error-notes                      # Phase 2.2 Error Note 점검 스킵
/cs-end --domains test,design                 # 버전업 도메인 수동 지정 (자동 탐지 오버라이드)
/cs-end --project ~/Documents/GitHub/myproduct_v4/easyconversion_web1  # 프로젝트 명시
```
