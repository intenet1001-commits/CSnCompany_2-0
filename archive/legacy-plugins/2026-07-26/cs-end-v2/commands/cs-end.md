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

## ⚠️ Author-Only Command

`/cs-end` is designed for the **plugin author** (`intenet1001-commits`). It commits and pushes changes back to the marketplace repository.

If you are not the author, Phase 4 (git push) is automatically skipped — your local learnings are still saved.

## 실행 순서

0. **Phase 0 — 플래그 파싱 + Origin 확인** (자동)
0.5. **Phase 0.5 — Session Pre-Pass Digest** ← 신규 (Attention + KV Cache)
1. **Phase 1 — 4-Agent 병렬 분석** (Digest 공유 컨텍스트 주입)
2. **Phase 2 — 학습 영속화 + Learning Gate** (3-axis 품질 스코어)
2.5. **Phase 2.5 — Knowledge Decay Check** ← 신규 (Forget Gate, 항목 있을 때만)
3. **Phase 3 — Selective 버전업** (DOMAINS_USED 기반 필터링)
4. **Phase 4 — Git commit + push** (atomic commit, marketplace.json 동기화)
5. **Phase 5 — Push 완료 리포트** (두 레포 상태 명확 구분 출력)
6. **Phase 6 — 구조화 세션 Compact 핸드오프** ← 개선 (Hidden State 5-field 포맷)

## Phase 0 — 플래그 파싱 + Origin 확인

```bash
PREPASS_RUNNER="$HOME/.claude/plugins/marketplaces/CSnCompany_2-0/shared/run_prepass.sh"
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

`$SKILL`의 프로토콜에 따라 4-Agent를 단일 메시지에 병렬 스폰하여 실행합니다.

## Phase 2 — 학습 영속화 + Learning Gate (Input Gate 패턴)

`learning-extractor` 결과를 cs-experiencing 노하우 섹션에 저장하기 전에 **3-axis 품질 게이트**를 통과시킵니다.

### Learning Gate 채점 기준 (임계값: 4/6)

각 학습 후보에 대해 다음 3개 축으로 점수를 계산합니다:

**Axis 1: 노벨티 (0-2점)** — SKILL_SNAPSHOT과 비교
- 2점: SKILL_SNAPSHOT에 유사 항목 없음 (새로운 발견)
- 1점: 관련 항목은 있으나 새로운 각도/구체사항 추가
- 0점: 기존 항목과 실질적으로 동일 (상황+교훈이 겹침)

**Axis 2: 임팩트 (0-2점)**
- 2점: 블로커 해결 / 세션의 핵심 돌파구
- 1점: 효율을 높인 유용한 인사이트
- 0점: 이미 자명한 편의 메모

**Axis 3: 재사용성 (0-2점)**
- 2점: 이 도메인/패턴을 사용하는 모든 미래 세션에 적용 가능
- 1점: 이 코드베이스/프로젝트 계열에 한정 적용
- 0점: 특정 파일명·버전·타이밍에 종속된 일회성 정보

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
```

- **principle**: 플랫폼/언어 동작, 아키텍처 패턴 등 시간이 지나도 안정적인 지식
- **tactical**: 특정 버전·설정·워크어라운드 등 변경 가능성이 있는 전술적 지식

**0개 저장 시:** "0 learnings persisted this session" 출력 후 Phase 2.5로 진행 (오류 없음).

CHANGELOG도 함께 갱신합니다.

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

## Phase 3 — Selective 버전업 (GRU Update Gate 패턴)

`version-scout` 결과를 **DOMAINS_USED 기반으로 필터링**합니다.

**필터링 로직:**
- `DOMAINS_USED`에 포함된 도메인만 버전업 후보
- `DOMAINS_USED`가 비어 있거나 탐지 실패 시 → 기존 방식 fallback (변경된 전체 플러그인)
- `--domains` 명시 플래그 → 해당 값으로 오버라이드

**출력 포맷:**
```
📦 버전업 스코프:
   ✅ CS-test    — 이번 세션 사용 → 버전업 진행
   ✅ cs-design  — 이번 세션 사용 → 버전업 진행
   ⏭️ CS-plan   — 이번 세션 미사용 → 스킵
   ⏭️ CS-codebase-review — 이번 세션 미사용 → 스킵
```

이후 `$SKILL`의 version-up 프로토콜에 따라 선택된 도메인만 버전업을 진행합니다 (VERSION 파일 + plugin.json bump).

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
/cs-end --domains test,design                 # 버전업 도메인 수동 지정 (자동 탐지 오버라이드)
/cs-end --project ~/Documents/GitHub/myproduct_v4/easyconversion_web1  # 프로젝트 명시
```
