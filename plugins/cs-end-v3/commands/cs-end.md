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

**v3 신규 (CS_V7 지식 루프 연동):**
- **CS_V7 Knowledge Write** (Phase 2.1) — principle-tier 학습을 CS_V7/raw/에 자동 저장 → graphify-sync 트리거 → 다음 ingest에서 위키 컴파일
- **Error Note 점검 + 캡처** (Phase 2.2) — open 에러노트 항상 점검 + 에러→해결 시퀀스 감지 시 ~/.claude/error-notes/ 에 자동 저장 제안

## ⚠️ Author-Only Command

`/cs-end` is designed for the **plugin author** (`intenet1001-commits`). It commits and pushes changes back to the marketplace repository.

If you are not the author, Phase 4 (git push) is automatically skipped — your local learnings are still saved.

검증 프로토콜: plugins/shared/LOOP-PROTOCOL.md + plugins/shared/agents/verifier.md를 따른다. (런타임 경로: `${CLAUDE_PLUGIN_ROOT}/../shared/`)

## 실행 순서

0. **Phase 0 — 플래그 파싱 + Origin 확인** (자동)
0.5. **Phase 0.5 — Session Pre-Pass Digest** ← 신규 (Attention + KV Cache)
1. **Phase 1 — 4-Agent 병렬 분석** (Digest 공유 컨텍스트 주입)
2. **Phase 2 — 학습 영속화 + Learning Gate** (3-axis 품질 스코어)
2.1. **Phase 2.1 — CS_V7 Knowledge Write** ← v3 신규 (principle-tier → CS_V7/raw/)
2.2. **Phase 2.2 — Error Note 점검 + 캡처** ← 신규 (open 노트 항상 점검 + 에러→해결 캡처)
2.5. **Phase 2.5 — Knowledge Decay Check** ← 신규 (Forget Gate, 항목 있을 때만)
2.6. **Phase 2.6 — Prompt Patch** ← 신규 (PASS 학습 → 운영 프롬프트 즉시 반영)
2.7. **Phase 2.7 — Patch Verification** ← 신규 (패치 결정적 점검 + verifier 1회)
3. **Phase 3 — Selective 버전업** (DOMAINS_USED 기반 필터링)
4. **Phase 4 — Git commit + push** (atomic commit, marketplace.json 동기화)
5. **Phase 5 — Push 완료 리포트** (두 레포 상태 명확 구분 출력)
6. **Phase 6 — 구조화 세션 Compact 핸드오프** ← 개선 (Hidden State 5-field 포맷)

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

**Digest 요약 출력** (디버그용):
```
🔍 Session Digest:
   사용 도메인: [DOMAINS_USED 또는 "탐지 없음 → all fallback"]
   노하우 항목: [SKILL_SNAPSHOT 항목 수]개
   BTW pending: [BTW_COUNT]개
   오래된 항목: [STALE_COUNT]개
```

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

## Phase 2 — 학습 영속화 + Learning Gate (Input Gate 패턴)

`learning-extractor` 결과를 cs-experiencing 노하우 섹션에 저장하기 전에 **3-axis 품질 게이트**를 통과시킵니다.

### Learning Gate 채점 기준 (임계값: 4/6)

각 학습 후보에 대해 다음 3개 축으로 점수를 계산합니다:

**Axis 1: 노벨티 (0-2점)** — 본문 비교 필수 (제목 비교만으로 확정 금지)

노벨티는 SKILL_SNAPSHOT(제목+날짜)만으로 확정할 수 없다. 각 후보에 대해:
1. 후보의 핵심 키워드 2-3개로 `grep -n`을 `$SKILL` 전체 본문에 실행한다.
2. 매칭된 기존 항목(최대 3개)의 전체 텍스트(상황/발견/교훈)를 Read하여 비교한 뒤에만 점수를 부여한다.

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

## Phase 2.1 — CS_V7 Knowledge Write (v3 신규)

**Learning Gate PASS 항목 중 `tier=principle`인 것이 있을 때만 실행한다. CS_V7 개인 위키 파이프라인에 세션 학습을 영속화한다.**

### 실행 조건

```bash
CS_V7_RAW="$HOME/CS_V7/raw"
CS_V7_OK=true
[ -d "$CS_V7_RAW" ] || { echo "CS_V7 없음 — 이 Phase 스킵"; CS_V7_OK=false; }
# CS_V7_OK=true이고 GATE_PASS 항목 중 tier=principle 존재할 때만 아래 절차 진행
```

조건 미충족(principle 항목 0개 또는 CS_V7 없음) → 조용히 Phase 2.5로 진행.

### 절차

1. **파일 생성**: principle-tier 항목을 `CS_V7/raw/` 마크다운으로 포맷

   파일명: `cs-session-YYYY-MM-DD-<slug>.md`  
   (`<slug>` = 학습 제목에서 kebab-case 추출, 한글 허용)

   ```markdown
   # <학습 제목> — CS Session Learning

   source: cs-end session YYYY-MM-DD
   domains: <DOMAINS_USED>

   ## 상황
   <상황 필드>

   ## 발견
   <발견 필드>

   ## 교훈
   <교훈 필드>
   ```

2. **CS_V7/raw/ 에 Write** (Write 도구 사용)

3. **graphify-sync 트리거**:

   ```bash
   cd "$HOME/CS_V7" && bash scripts/graphify-sync.sh 2>/dev/null \
     && echo "graphify 완료" || echo "graphify 스킵 (변경 없음)"
   ```

4. **출력**:

   ```
   📚 CS_V7 저장: [N]개 principle → CS_V7/raw/cs-session-YYYY-MM-DD-*.md
      다음 세션에서 /llm-wiki ingest 실행 시 wiki로 컴파일됩니다.
   ```

5. **Phase 6 NEXT 필드에 힌트 추가** (신규 파일이 저장된 경우):

   ```
   CS_V7 /llm-wiki ingest 실행 권장 (신규 session learning 저장됨)
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

**open 노트가 1개 이상이면** 다음을 출력합니다:

```
📝 Error Notes 점검:
   미해결 에러노트 [OPEN_COUNT]개 — /cs-error-notes list --open 으로 확인
   최근 open: [최신 open 노트 ID + 제목 1줄]
```

**open 노트가 0개이면** 한 줄만 출력합니다:
```
📝 Error Notes: 미해결 없음 ✅
```

이번 세션에서 해결한 에러가 있다면 `resolve` 추천:
```
   💡 이번 세션에서 해결한 에러가 있다면: /cs-error-notes resolve ERR-xxx
```

---

### Part B — 신규 에러→해결 캡처 (감지 시에만)

`learning-extractor` 결과에서 에러→해결 시퀀스를 감지합니다:
- 상황 필드에 "에러", "오류", "실패", "error", "bug", "crash" 포함
- 발견 필드에 "해결", "수정", "fix", "resolved" + 원인 분석 포함

감지 시 제안:

```
AskUserQuestion(
  question: "에러→해결 시퀀스 감지됨. 에러노트로 저장할까요?",
  options: [
    "저장 — ~/.claude/error-notes/ 에 기록",
    "건너뛰기 — 이번 세션은 생략"
  ]
)
```

저장 선택 시:
- learning-extractor 결과를 5-필드 포맷으로 변환 (상황/문제점/시도/원인/해결점)
- ERR-YYYY-MM-DD-NNN ID 자동 부여
- `~/.claude/error-notes/` 에 Write, INDEX.md 갱신
- Learning Gate PASS 항목에 `<!-- error-ref: [ID] -->` 태그 추가
- 출력: `📝 에러노트 저장: [ID]`

미감지 → 조용히 Phase 2.5로 진행.

---

## Phase 2.5 — Knowledge Decay Check (Forget Gate 패턴)

**`--no-decay-check` 플래그가 있거나 `STALE_COUNT == 0`이면 이 Phase를 조용히 스킵합니다.**

`STALE_ENTRIES`에 항목이 있을 때만 아래를 출력합니다:

```
🕰️  Forget Gate — 오래된 tactical 노하우 감지 (30일+ 경과):
   #[n]. [title] ([date]) — [age_days]일 경과
   → 아카이빙 권장 (자동 삭제 아님, 검토 필요)
```

각 stale 항목에 대해:
1. SKILL.md에서 해당 항목의 전체 내용 읽기
2. 이번 세션 지식으로 볼 때 여전히 정확한지 평가
3. 구식인 경우: 항목 하단에 주석 추가 (삭제 금지)

```markdown
<!-- deprecated: [이유] — [YYYY-MM-DD] -->
```

**Decay 완료 요약 출력:**
```
Decay 리뷰: [N]개 검토, [M]개 deprecated 주석 추가
```

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

(a) **DIGEST 유효 + domains_used 비어 있음** → 변경된 플러그인 목록을 출력하고 AskUserQuestion으로 확인:

```
AskUserQuestion(
  question: "도메인 탐지 없음 — 변경된 전체 플러그인 [목록]을 버전업할까요?",
  options: [
    "전체 진행 — 변경된 플러그인 모두 버전업",
    "도메인 수동 지정 — --domains 값 입력",
    "버전업 스킵 — 이번 세션은 버전업 없이 진행"
  ]
)
```

(b) **DIGEST_FAILED=true** (Phase 0.5 검증 실패) → 자동 fallback 금지. `--domains` 명시 또는 사용자의 명시적 확인 없이는 어떤 버전업도 하지 않는다.

**출력 포맷:**
```
📦 버전업 스코프:
   ✅ CS-test    — 이번 세션 사용 → 버전업 진행
   ✅ cs-design  — 이번 세션 사용 → 버전업 진행
   ⏭️ CS-plan   — 이번 세션 미사용 → 스킵
   ⏭️ CS-codebase-review — 이번 세션 미사용 → 스킵
```

이후 `$SKILL`의 version-up 프로토콜에 따라 선택된 도메인만 버전업을 진행합니다 (VERSION 파일 + plugin.json bump).

## Phase 4 — Git commit + push (atomic)

**Skip guard (이 Phase의 첫 판정):** `AUTO_NO_PUSH=true` 또는 `--no-push` 또는 `--learning-only`이면
`⏭️ Phase 4 SKIPPED (no-push 모드)`를 출력하고 커밋 없이 Phase 5로 진행한다 (상태: SKIPPED).

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

### 출력 포맷

Phase 4 완료 직후, 다음 형식으로 출력합니다:

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 Push 완료 리포트
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

 [마켓플레이스]  CSnCompany_2-0
   ✅ PUSHED     branch: main → intenet1001-commits/CSnCompany_2-0
   (또는)
   ⏭️  SKIPPED   --no-push 모드 / author 아님

 [프로젝트]      <project-name>
   ✅ PUSHED     branch: main → <owner>/<repo>
   (또는)
   ⚠️  UNPUSHED  <N>개 커밋이 아직 remote에 없음
                 → git -C <path> push origin <branch>
   (또는)
   ─  해당없음   세션 중 별도 프로젝트 레포 없음

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

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
| `DONE` | `followup-suggester` 완료 목록 + `doc-updater` 결과 | 이번 세션 완료 항목 1-2줄 |
| `LEARNED` | Learning Gate 통과 항목 중 최고 점수 1개 | 핵심 발견 1줄 |
| `DOMAINS` | `DOMAINS_USED` | 이번 세션 활성 CS 도메인 |
| `NEXT` | `followup-suggester` 최우선 항목 | 다음 세션 첫 번째 구체적 액션 |
| `BTWS` | `BTW_COUNT` + `BTW_PENDING` 첫 항목 제목 | 미처리 BTW 수 + 최우선 1개 |

`/compact` 인자는 DONE + LEARNED 필드를 1-2줄로 합성하여 생성합니다.

### 출력 포맷

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 세션 종결 완료 — context를 정리하세요
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

/compact [DONE 요약 + LEARNED 핵심 1-2줄]

━━━━ 다음 세션 재개 정보 (선택: 복사 보관) ━━━━━
DONE    : [이번 세션 완료 항목]
LEARNED : [최고 점수 학습 1줄, 없으면 "(저장된 학습 없음)"]
DOMAINS : [DOMAINS_USED 목록]
NEXT    : [다음 세션 첫 번째 액션]
BTWS    : [BTW_COUNT]개 pending — [최우선 BTW 제목 또는 "없음"]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

 또는 완전 초기화: /clear
```

**예시:**
```
/compact 2026-05-13 cs-end LSTM게이트 개선 적용 완료. Session Pre-Pass로 Phase1 토큰 ~60% 절감 패턴 확립

DONE    : cs-end v2.1 개선 (Digest + Learning Gate + Selective 버전업 + 구조화 compact)
LEARNED : session-digest 서브커맨드가 SKILL.md 노하우 헤더를 regex로 파싱, 4에이전트에 공유해 토큰 절감
DOMAINS : cs-end
NEXT    : 실제 세션에서 /cs-end 실행 후 Phase1 토큰 절감 측정 확인
BTWS    : 0개 pending — 없음
```

## 사용 예

```
/cs-end                                        # 표준 종료 (Digest → 분석 → 게이트 → 버전업 → push → compact)
/cs-end --project /path/to/repo               # 프로젝트 레포 명시
/cs-end --no-push                             # push 생략 (로컬만)
/cs-end --no-compact                          # Phase 6 생략
/cs-end --learning-only                       # 학습 추출/저장만 (버전업/push/compact 생략)
/cs-end --no-decay-check                      # Phase 2.5 Forget Gate 스킵
/cs-end --no-error-notes                      # Phase 2.2 Error Note 점검 스킵
/cs-end --domains test,design                 # 버전업 도메인 수동 지정 (자동 탐지 오버라이드)
/cs-end --project ~/Documents/GitHub/myproduct_v4/easyconversion_web1  # 프로젝트 명시
```
