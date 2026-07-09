---
name: cs-experiencing
user-invocable: true
description: |
  경험 지식 저장소 오케스트레이터.
  도메인별 누적 학습 조회, 실행, 버전 관리.
  Use when invoked via /cs-experiencing, or when user says "경험", "학습 실행", "버전업".
version: 8.1.4
allowed-tools:
  - Read
  - Write
  - Edit
  - Bash
  - Agent
  - AskUserQuestion
---

# Experiencing - 경험 지식 저장소

## 도메인 위치

도메인들은 cs-experiencing-v*과 같은 레벨의 plugins/ 디렉토리에 위치합니다:

```
plugins/
├── cs-experiencing-v*/      ← 이 플러그인 (오케스트레이터)
├── CS-test-v*/              ← 멀티 에이전트 웹 테스트 도메인 (에이전트 구성·개수의 단일 진실은 해당 디렉토리의 commands/CS-test.md 로스터)
├── CS-plan-v*/              ← TDD+CleanArch 4-agent 플랜 도메인
├── CS-codebase-review-v*/   ← 5-agent 코드 리뷰 도메인
├── cs-design-v*/            ← 5-agent 디자인 리뷰 도메인
├── cs-clarify-v*/           ← 4-agent 요구사항 명료화 도메인
├── cs-smart-run/            ← Opus 플랜 + 병렬 Sonnet 실행 (디렉토리 버전 suffix 없음, VERSION 파일만)
└── cs-ceo-v*/               ← CEO 오케스트레이터 도메인
```

**버전은 디렉토리명이 단일 진실** — 항상 `ls -d "$BASE/<도메인>-v"* | sort -V | tail -1`로 최신을 해석한다.
문서에 버전 숫자를 하드코딩하지 않는다.

마켓플레이스 절대 경로: `~/.claude/plugins/marketplaces/CSnCompany_2-0/plugins/`

## 사용법

```
/cs-experiencing                                          # 도메인 목록 + 버전 현황 표시
/cs-experiencing test [URL]                               # CS-test 실행 (멀티 에이전트 웹 테스트)
/cs-experiencing plan [task]                              # CS-plan 실행
/cs-experiencing review [path] [--focus aspect]           # CS-codebase-review 실행 (5-관점 코드 리뷰)
/cs-experiencing design [path] [--focus aspect] [--fix]  # CS-design 실행 (5-관점 디자인 리뷰)
/cs-experiencing update                                   # 모든 도메인 버전업 (version-up all 단축키)
/cs-experiencing version-up [domain]                      # 도메인 버전 증가 (test/plan/review/design/clarify/smart-run/ceo)
/cs-experiencing version-up all                           # 7개 도메인 한번에 버전 증가 (test→plan→review→design→clarify→smart-run→ceo)
/cs-experiencing status                                   # 모든 도메인 VERSION 파일 읽기
/cs-experiencing btw [idea]                               # [v4 신규] 세션 중 개선 아이디어 즉시 캡처
/cs-experiencing checkpoint                               # [v4 신규] WIP 체크포인트 커밋 생성
/cs-experiencing pipeline [project]                       # 전체 파이프라인 실행 (review→design→test)
```

---

## 실행 프로토콜

### 공통: 학습 회상 (read-side) — fan-out 디스패치 전 필수

test/plan/review/design/pipeline 프로토콜은 에이전트 디스패치 직전에 아래를 수행한다:

1. 현재 태스크에서 키워드 추출 (기술 스택·도메인 명사, 예: `worktree`, `vercel`, `supabase`)
2. 이 SKILL.md의 **학습 INDEX** 테이블을 키워드로 grep → 매칭 상위 2-3건 선별
3. 선별 항목의 본문을 위치 컬럼(인라인 또는 `knowledge/<topic>.md`)에서 읽어
   디스패치 프롬프트에 그대로 주입 ("과거 학습: ..." 블록)
4. 매칭 없으면 주입 생략 — 사용자에게 묻거나 지연하지 않는다

### `/experiencing` (인수 없음)

도메인 목록과 현재 버전을 표시:

```bash
BASE="$HOME/.claude/plugins/marketplaces/CSnCompany_2-0/plugins"
# 7개 도메인 (test→plan→review→design→clarify→smart-run→ceo)
for domain in CS-test CS-plan CS-codebase-review cs-design cs-clarify cs-ceo; do
  LATEST=$(ls -d "$BASE/${domain}-v"* 2>/dev/null | sort -V | tail -1)
  VERSION=$(cat "$LATEST/VERSION" 2>/dev/null || echo "?")
  echo "📦 $domain | 현재 콘텐츠 버전: $VERSION"
done
# cs-smart-run은 버전 접미사 없는 단일 디렉토리 — 직접 경로
VERSION=$(cat "$BASE/cs-smart-run/VERSION" 2>/dev/null || echo "?")
echo "📦 cs-smart-run | 현재 콘텐츠 버전: $VERSION"
```

### `/cs-experiencing test [URL]`

1. 최신 CS-test 도메인 경로 찾기:
   ```bash
   BASE="$HOME/.claude/plugins/marketplaces/CSnCompany_2-0/plugins"
   LATEST_TEST=$(ls -d "$BASE/CS-test-v"* 2>/dev/null | sort -V | tail -1)
   if [ -z "$LATEST_TEST" ]; then echo "❌ CS-test 디렉토리 없음 — marketplace.json 확인 필요"; exit 1; fi
   ```
2. `$LATEST_TEST/VERSION` 읽기 → 현재 버전 확인
3. `$LATEST_TEST/skills/CS-test/SKILL.md` 프로토콜 실행
4. **학습 회상**(공통 read-side 단계) 수행 후 URL을 대상으로 멀티 에이전트 팀 가동 (에이전트 구성·개수는 `$LATEST_TEST/commands/CS-test.md` 로스터가 단일 진실)

### `/cs-experiencing plan [task]`

1. 최신 CS-plan 도메인 경로 찾기:
   ```bash
   BASE="$HOME/.claude/plugins/marketplaces/CSnCompany_2-0/plugins"
   LATEST_PLAN=$(ls -d "$BASE/CS-plan-v"* 2>/dev/null | sort -V | tail -1)
   if [ -z "$LATEST_PLAN" ]; then echo "❌ CS-plan 디렉토리 없음 — marketplace.json 확인 필요"; exit 1; fi
   ```
2. `$LATEST_PLAN/VERSION` 읽기 → 현재 버전 확인
3. **학습 회상**(공통 read-side 단계) 수행 후 `$LATEST_PLAN/skills/CS-plan/SKILL.md` 프로토콜 실행

### `/cs-experiencing review [path] [--focus aspect]`

1. 최신 CS-codebase-review 도메인 경로 찾기:
   ```bash
   BASE="$HOME/.claude/plugins/marketplaces/CSnCompany_2-0/plugins"
   LATEST_REVIEW=$(ls -d "$BASE/CS-codebase-review-v"* 2>/dev/null | sort -V | tail -1)
   if [ -z "$LATEST_REVIEW" ]; then echo "❌ CS-codebase-review 디렉토리 없음 — marketplace.json 확인 필요"; exit 1; fi
   ```
2. `$LATEST_REVIEW/VERSION` 읽기 → 현재 버전 확인
3. `$LATEST_REVIEW/skills/CS-codebase-review/SKILL.md` 프로토콜 실행
3. 인수 파싱:
   - `[path]` 없음 → 현재 작업 디렉토리 전체 분석
   - `[path]` 있음 → 해당 경로만 분석
   - `--focus [aspect]` 있음 → 해당 관점만 집중 분석 (architecture/quality/security/performance/maintainability)
4. **학습 회상**(공통 read-side 단계) 수행 후 5개 에이전트(Architecture/Quality/Security/Performance/Maintainability)를 병렬 실행
5. 결과 종합 → 등급(A/B/C/D) + 우선순위별 권장 조치사항 리포트 출력

### `/cs-experiencing update`

`version-up all`의 단축 명령어. 아래 `version-up all` 프로토콜의 캐노니컬 도메인 목록
(`test → plan → review → design → clarify → smart-run → ceo`)과 동일하게 실행.
도메인 개수는 이 목록이 단일 진실 — 다른 문서의 "N개 도메인" 표현은 이 목록을 참조한다.

---

### `/cs-experiencing design [path] [--focus aspect] [--fix]`

1. 최신 CS-design 도메인 경로 찾기:
   ```bash
   BASE="$HOME/.claude/plugins/marketplaces/CSnCompany_2-0/plugins"
   LATEST_DESIGN=$(ls -d "$BASE/cs-design-v"* 2>/dev/null | sort -V | tail -1)
   if [ -z "$LATEST_DESIGN" ]; then echo "❌ cs-design 디렉토리 없음 — marketplace.json 확인 필요"; exit 1; fi
   ```
2. `$LATEST_DESIGN/VERSION` 읽기 → 현재 버전 확인
3. `$LATEST_DESIGN/skills/cs-design/SKILL.md` 프로토콜 실행
4. 인수 파싱:
   - `[path]` 없음 → 현재 작업 디렉토리
   - `--focus [aspect]` 있음 → 해당 관점만 집중 분석 (visual/interaction/consistency/responsive/antipatterns)
   - `--fix` 있음 → 발견된 안티패턴 자동 수정 활성화
5. **학습 회상**(공통 read-side 단계) 수행 후 design-lead 에이전트를 스폰하여 5개 에이전트(visual-hierarchy/interaction-quality/design-system-consistency/responsive-accessibility/anti-pattern-detector) 병렬 실행
6. 결과 종합 → 관점별 점수(0-10) + 등급(A~F) + 우선순위별 수정사항 DESIGN-REVIEW.md 출력

---

### `/cs-experiencing version-up [domain|all]`

**정책: 직전 버전 + 현재 버전 2개만 유지. 더 오래된 버전은 자동 삭제.**

**`all` 키워드 (캐노니컬 도메인 목록)**: `test → plan → review → design → clarify → smart-run → ceo` 7개 도메인 순차 처리.

**각 도메인마다 아래 순서로 실행:**

---

#### STEP 1: 학습 캡처 (AI 자동 추출 우선)

**AI가 먼저 세션 컨텍스트를 분석해서 핵심 노하우를 추출한다. 발견 시 제안 → 사용자 확인. 없으면 직접 질문.**

**1-A. AI 자동 분석**

현재 세션 대화에서 해당 도메인과 관련된 다음 항목을 탐색:
- 예상과 달랐던 동작 (버그, 엣지케이스, 특이 동작)
- 문제 해결 과정에서 발견한 패턴 또는 원인
- 반복 적용 가능한 팁, 설정, 명령어
- 공식 문서/가정과 실제 동작의 차이

각 발견에는 근거(세션 내 실제 command 출력, 파일 경로, 또는 에러 메시지 인용) 1건을 첨부한다
(plugins/shared/LOOP-PROTOCOL.md [a] EVIDENCE 준용). 근거를 제시할 수 없는 항목은 tier를
자동으로 `tactical`로 강등하고, 1-B 확인 문구에 `[근거없음]` 경고를 함께 노출한다.

**1-B. 발견사항이 있으면 → 제안 후 확인 (AskUserQuestion 1회)**

```
💡 CS-[DOMAIN] — AI가 분석한 이번 세션 핵심 학습:

"[AI가 추출한 학습 제목]: [구체적 발견 내용 1-2줄]"
근거: [command 출력/파일:줄/에러 메시지 인용]  ← 없으면 "[근거없음] tier: tactical로 강등"

이대로 저장할까요?
```
옵션:
- "저장" → 그대로 SKILL.md에 추가
- "직접 수정" → Other 선택 후 수정 내용 입력
- "스킵" → 학습 없이 버전만 증가

**1-C. 발견사항이 없으면 → 자동 스킵 (질문 없음)**

AskUserQuestion 호출하지 않음. 그냥 "📝 학습 스킵 (이번 세션 발견사항 없음)" 출력 후 STEP 3으로 진행.

#### STEP 2: 학습 내용 저장 (입력이 있을 경우)

1. 최신 도메인 디렉토리의 SKILL.md 읽기
2. **반박 패스 (refutation pass) — 저장 전 필수 체크리스트** (SKILL.md를 이미 열어둔 상태에서 오케스트레이터가 직접 수행, 별도 에이전트 금지):
   - (a) 학습 INDEX(또는 해당 도메인 노하우 섹션)를 동일 키워드/도메인으로 grep → 중복·모순 항목 발견 시
     표면화: "#[N]이 이미 이 내용을 다룸 — 병합 또는 스킵?"
   - (b) 절대어(항상/절대/always/never/불가능) 포함 시 제목 또는 상황 줄에 범위 한정자 요구
     (예: "auto-mode 기준 2026-05", "Tauri v1 WebKit")
   - (c) 외부 서비스·도구 동작에 대한 **1회 관찰** 주장은 무조건 `tier: tactical` (principle 금지)
   - (d) 다음 항목 번호가 실제로 학습 INDEX의 max+1인지 검증 (번호 드리프트 방지)
   - 반박 결과는 STEP 1-B의 동일한 AskUserQuestion(저장/수정/스킵) 안에 함께 제시 — 사용자 클릭은 1회 유지
3. 다음 번호 결정: **학습 INDEX의 max+1** (마지막 인라인 항목 번호가 아님)
4. 오늘 날짜 확인: `date +%Y-%m-%d`
5. 학습의 **tier** 결정:
   - `principle` — 플랫폼 동작·언어 특성·아키텍처 패턴 등 시간이 지나도 안정적인 지식
   - `tactical` — 특정 버전·설정·워크어라운드 등 변경 가능성이 있는 전술적 지식 (기본값)
6. **저장 위치 라우팅**:
   - 오케스트레이터 자체 도메인 학습(version-up/파이프라인/학습 캡처) → cs-experiencing SKILL.md 인라인 섹션 끝
   - 해당 도메인 고유 학습 → 그 도메인 SKILL.md 노하우 섹션 끝
   - 프로젝트-특화 학습 → 매칭되는 `skills/experiencing/knowledge/<topic>.md` 끝에 append (주제 파일 없으면 새로 생성)
   - 어느 경우든 **cs-experiencing 학습 INDEX 테이블에 1줄 추가** (번호, 제목, tier, 태그, 위치)
7. Edit 도구로 아래 포맷으로 추가:

```markdown
### [N]. [학습 제목] ([YYYY-MM-DD])
<!-- tier: principle|tactical -->
- **상황**: [어떤 작업 중에 발견했는지]
- **발견**: [구체적으로 무엇을 배웠는지]
- **교훈**: [다음에 어떻게 적용할지]
```

**tier 분류 가이드:**
- `principle` 예시: "/compact는 스킬에서 직접 호출 불가 (Claude Code 내장)", "훅 non-zero exit code는 UI 블로킹"
- `tactical` 예시: "osascript choose folder 특정 파라미터 금지", "bun --watch 파일변경 미감지"

**Knowledge Decay 정책:** `tactical` 항목은 cs-end의 Forget Gate가 30일 경과 시 자동으로 재검토를 권장한다. `principle` 항목은 decay 검토 대상에서 제외된다.

#### STEP 3: 버전 디렉토리 생성

```bash
BASE_PATH="$HOME/.claude/plugins/marketplaces/CSnCompany_2-0/plugins"
ALL_DIRS=($(ls -d "$BASE_PATH/CS-${DOMAIN}-v"* 2>/dev/null | sort -V))
LATEST_DIR="${ALL_DIRS[-1]}"
CURRENT_VERSION=$(cat "$LATEST_DIR/VERSION" 2>/dev/null || echo "1")
NEXT_VERSION=$((CURRENT_VERSION + 1))
NEW_DIR="$BASE_PATH/CS-${DOMAIN}-v${NEXT_VERSION}"

cp -r "$LATEST_DIR" "$NEW_DIR"
echo "$NEXT_VERSION" > "$NEW_DIR/VERSION"
```

#### STEP 4: marketplace.json 업데이트

파일: `~/.claude/plugins/marketplaces/CSnCompany_2-0/.claude-plugin/marketplace.json`

Edit 도구로:
- `"./plugins/CS-[DOMAIN]-v[CURRENT]"` → `"./plugins/CS-[DOMAIN]-v[NEXT]"`

#### STEP 4b: 버전 메타데이터 정합성 검증 (push 차단 게이트)

```bash
bash "$BASE_PATH/shared/run_prepass.sh" version-check "$NEW_DIR"
```

(`plugins/CLAUDE.md`의 Python 실행 규칙 준수 — `shared/scripts/*.py`를 `python3`로 직접 호출하지
않고 항상 이 진입점을 통해 python3 → uv run → uv install 순 자동 폴백을 태운다.)

`"ok": false`이거나 스크립트가 non-zero로 종료하면, 불일치 소스(plugin.json / SKILL frontmatter)를
VERSION 파일 값으로 맞춘 뒤 재실행한다. ok가 될 때까지 commit/push 단계로 진행하지 않는다 —
자가 업그레이드가 낡은 자기 서술을 배포하는 것을 막는 게이트.
(숫자 정규화 비교: `1` == `1.0.0`)

#### STEP 5: 오래된 버전 정리

```bash
TOTAL=${#ALL_DIRS[@]}
DELETE_COUNT=$((TOTAL - 1))
if [ $DELETE_COUNT -gt 0 ]; then
  for dir in "${ALL_DIRS[@]:0:$DELETE_COUNT}"; do
    echo "🗑️ 삭제: $(basename $dir)"
    rm -rf "$dir"
  done
fi
```

#### STEP 6: 완료 안내

```
✅ CS-[DOMAIN] 버전업 완료
📦 현재 버전: CS-[DOMAIN]-v[NEXT] (VERSION=[NEXT])
📦 보관 버전: CS-[DOMAIN]-v[CURRENT] (직전)
🗑️ 삭제됨: [삭제된 버전들]
📝 학습 추가: "[제목]" (노하우 #[N])   ← 입력 있을 경우
📝 학습 스킵                           ← 입력 없을 경우
```

---

**`version-up all` 실행 순서**: `test → plan → review → design → clarify → smart-run → ceo` (7개 순차)

**`clarify` 도메인**: 최신 `cs-clarify-v*` 디렉토리 대상. 학습은
`skills/cs-clarify/SKILL.md`의 `## cs-clarify 노하우` 섹션 끝에 추가
(형식 동일: `### [N]. [제목] ([YYYY-MM-DD])`).

**`smart-run` 도메인**: `cs-smart-run`은 디렉토리 버전 suffix가 없다 —
디렉토리 복사/삭제(STEP 3, 5) 및 marketplace.json 경로 변경 없이
`plugins/cs-smart-run/VERSION` 파일만 +1 하고, 학습은 `plugins/cs-smart-run/skills/` 하위
SKILL.md 노하우 섹션 끝에 추가한다.

**`version-up ceo` 프로토콜** (6-step):

CEO 버전업은 다른 6개 도메인과 동일한 구조이나 학습 캡처 내용이 다르다.

**STEP 1: 학습 분석 (CEO 특화)**

이번 세션에서 CEO가 내린 배분 결정을 회고한다:
- smart-run을 선택한/안 한 결정이 올바랐는가?
- 어떤 요청 패턴에서 공수 추정이 틀렸는가?
- 새로 발견한 효과적인 도메인 조합은?
- 어떤 상황에서 모드 C(smart-run)가 효과적이었는가?

발견사항이 있으면 AskUserQuestion으로 1회 확인. 없으면 자동 스킵.

**STEP 2: 학습 추가** (입력 있을 경우)

**⚠️ 두 파일 동시 업데이트 필수** — 에이전트(ceo.md)와 스킬(SKILL.md)이 항상 동기화되어야 한다.

1. `$LATEST_CEO/agents/ceo.md`의 `## CEO 노하우` 섹션 끝에 추가
2. `$LATEST_CEO/skills/cs-ceo/SKILL.md`의 `## CEO 노하우` 섹션 끝에 추가

두 파일 모두 동일한 내용을 추가한다:

```markdown
### [N]. [학습 제목] ([YYYY-MM-DD])
- **상황**: [어떤 요청이었는가]
- **판단**: [CEO가 내린 결정]
- **결과**: [효과적이었는가]
- **교훈**: [다음에 유사 상황에서 어떻게 판단할 것인가]
```

**STEP 3: 버전 디렉토리 생성**

```bash
BASE_PATH="$HOME/.claude/plugins/marketplaces/CSnCompany_2-0/plugins"
ALL_DIRS=($(ls -d "$BASE_PATH/cs-ceo-v"* 2>/dev/null | sort -V))
LATEST_DIR="${ALL_DIRS[-1]}"
CURRENT_VERSION=$(cat "$LATEST_DIR/VERSION" 2>/dev/null || echo "1")
NEXT_VERSION=$((CURRENT_VERSION + 1))
NEW_DIR="$BASE_PATH/cs-ceo-v${NEXT_VERSION}"

cp -r "$LATEST_DIR" "$NEW_DIR"
echo "$NEXT_VERSION" > "$NEW_DIR/VERSION"
```

**STEP 4: marketplace.json 업데이트**

Edit 도구로: `"./plugins/cs-ceo-v[CURRENT]"` → `"./plugins/cs-ceo-v[NEXT]"`

이후 STEP 4b(버전 메타데이터 정합성 검증)를 도메인 공통 프로토콜과 동일하게 수행한다.

**STEP 5: 오래된 버전 정리** (2개 유지)

```bash
TOTAL=${#ALL_DIRS[@]}
DELETE_COUNT=$((TOTAL - 1))
if [ $DELETE_COUNT -gt 0 ]; then
  for dir in "${ALL_DIRS[@]:0:$DELETE_COUNT}"; do
    rm -rf "$dir"
  done
fi
```

**STEP 6: 완료 안내**

```
✅ cs-ceo 버전업 완료
📦 현재 버전: cs-ceo-v[NEXT] (VERSION=[NEXT])
📦 보관 버전: cs-ceo-v[CURRENT] (직전)
📝 학습 추가: "[제목]" (노하우 #[N])  또는  📝 학습 스킵
```

---

**`all` 완료 후 종합 안내:**
```
✅ 전체 버전업 완료
📦 CS-test: v[N] → v[N+1]  (학습 추가/스킵)
📦 CS-plan: v[N] → v[N+1]  (학습 추가/스킵)
📦 CS-codebase-review: v[N] → v[N+1]  (학습 추가/스킵)
📦 cs-design: v[N] → v[N+1]  (학습 추가/스킵)
📦 cs-clarify: v[N] → v[N+1]  (학습 추가/스킵)
📦 cs-smart-run: VERSION [N] → [N+1]  (학습 추가/스킵)
📦 cs-ceo: v[N] → v[N+1]  (학습 추가/스킵)
```

### `/cs-experiencing pipeline [project]`

전체 파이프라인을 순서대로 실행합니다. experiencing-lead 에이전트가 오케스트레이션을 담당합니다.

1. **Preflight** (preflight-checker 에이전트 호출): 성공 기준 정의 + 범위 확인 + 도메인별 재실행 버짓 1회 질문 (기본 2회)
2. **Checkpoint**: 파이프라인 시퀀스 확인 (AskUserQuestion)
3. **학습 회상**: 공통 read-side 단계 수행 (INDEX grep → 상위 2-3건 디스패치 프롬프트 주입)
4. **실행 순서**: `review → design → test` (순차, 각 단계 후 체크포인트 + Grounding Gate)
5. **Evaluator-Optimizer (bounded loop)**: 등급 < B이면 실패 원인 에이전트만 범위 한정 재실행 —
   도메인당 최대 2라운드, 등급 ≥ B 또는 라운드가 새 발견을 못 만들면 즉시 종료,
   상한 도달 시 STUCK 리포트 (상세: `agents/experiencing-lead.md` Phase 2)
6. **최종 요약**: 3개 도메인 결과(아티팩트 검증 여부 포함) + 우선순위 액션 3개

```
경험 lead 에이전트 스폰:
BASE="$HOME/.claude/plugins/marketplaces/CSnCompany_2-0/plugins"
LEAD_DIR=$(ls -d "$BASE/cs-experiencing-v"* 2>/dev/null | sort -V | tail -1)
```

에이전트 파일: `$LEAD_DIR/agents/experiencing-lead.md`

---

### `/cs-experiencing btw [idea]` ← v4 신규 (bkit btw 패턴)

세션 중 발견한 개선 아이디어를 즉시 캡처합니다.

```bash
BTW_FILE="$(dirname $(ls -d "$HOME/.claude/plugins/marketplaces/CSnCompany_2-0" 2>/dev/null || echo "/tmp"))/.experiencing-btw.json"
# {id, idea, date, status: "pending"} 형태로 JSON 배열에 추가
```

저장 후: `💡 BTW #[N] 캡처됨: "[아이디어]"` 출력. version-up 시 pending 항목 자동 제안.

---

### `/cs-experiencing checkpoint` ← v4 신규 (gstack 패턴)

현재 작업 상태를 WIP 커밋으로 보존합니다.

```bash
DATE=$(date +%Y-%m-%d-%H%M)
git -C "$HOME/.claude/plugins/marketplaces/CSnCompany_2-0" add -A
git -C "$HOME/.claude/plugins/marketplaces/CSnCompany_2-0" commit -m "wip: cs-experiencing checkpoint $DATE"
```

완료 후: `✅ 체크포인트 저장됨 (${DATE})` 출력.

---

### `/cs-experiencing status`

모든 도메인의 VERSION 파일 표시:

```bash
BASE="$HOME/.claude/plugins/marketplaces/CSnCompany_2-0/plugins"
# 7개 도메인 (test→plan→review→design→clarify→smart-run→ceo)
for PATTERN in "CS-test-v" "CS-plan-v" "CS-codebase-review-v" "cs-design-v" "cs-clarify-v" "cs-ceo-v"; do
  LATEST=$(ls -d "$BASE/${PATTERN}"* 2>/dev/null | sort -V | tail -1)
  if [ -n "$LATEST" ]; then
    VER=$(cat "$LATEST/VERSION" 2>/dev/null || echo "?")
    DOMAIN=$(basename "$LATEST")
    echo "📋 $DOMAIN: v$VER"
  fi
done
# cs-smart-run은 버전 접미사 없는 단일 디렉토리 — 직접 경로
VER=$(cat "$BASE/cs-smart-run/VERSION" 2>/dev/null || echo "?")
echo "📋 cs-smart-run: v$VER"
```

---

## 버전 철학

- **도메인 디렉토리명** (`CS-test-v2`): 스키마/구조 버전 — 큰 구조 변경 시에만 변경
- **VERSION 파일**: 콘텐츠 버전 — 새 학습이 추가될 때마다 증가
- **plugin.json version**: 전체 플러그인 버전 — semver (major.minor.patch)
- **cs-experiencing 자체 버전업 시**: `plugin.json version` + SKILL.md frontmatter `version` + `VERSION` 파일을
  **반드시 같은 커밋에서 함께** 갱신한다 (세 값의 불일치 = 버전 드리프트, 약한 모델이 잘못된 경로를 따르는 원인)

---

## experiencing 노하우

### 학습 INDEX (전체 80건 — 1줄/항목, 단일 진실)

**검색 프로토콜 (read-side, 디스패치 전 필수):** fan-out을 수행하는 모든 프로토콜(test/plan/review/design/pipeline)은
에이전트 디스패치 전에 이 INDEX를 현재 태스크의 키워드(기술 스택·도메인 명사)로 grep하고,
매칭된 상위 2-3건의 본문을 해당 위치(인라인 또는 `knowledge/<topic>.md`)에서 읽어
**디스패치 프롬프트에 그대로 주입**한다. 매칭 없으면 주입 생략 (질문/지연 금지).

```bash
# 예: 태스크 키워드가 "worktree vite" 인 경우
grep -i -E "worktree|vite" skills/experiencing/SKILL.md | grep "^|" | head -3
```

신규 학습 추가 시: INDEX에 1줄 추가(번호 = 현재 max+1) + 본문은 매칭되는 `knowledge/<topic>.md`에 append
(주제 파일이 없으면 새로 생성). 오케스트레이터 자체(version-up/파이프라인/학습 캡처) 도메인 학습만 아래 인라인 섹션에 둔다.

| # | 제목 | tier | 태그 | 위치 |
|---|------|------|------|------|
| 1 | version-up은 학습 캡처 + 디렉토리 복사 두 단계여야 한다 (2026-04-11) | principle | orchestrator, version-up | 인라인 |
| 2 | `all` 키워드로 3개 도메인 한번에 버전업 (2026-04-11) | principle | orchestrator, version-up, all | 인라인 |
| 3 | AI 자동 학습 추출 — 수동 입력보다 먼저 시도 (2026-04-14) | principle | orchestrator, 학습추출, AI분석 | 인라인 |
| 4 | 외부 소스 학습 통합 — bkit·Karpathy·gstack 패턴 (2026-04-20) | principle | orchestrator, bkit, karpathy, gstack | 인라인 |
| 5 | bkit btw 패턴 — 세션 중 아이디어 즉시 캡처 (2026-04-20) | principle | orchestrator, btw, 캡처 | 인라인 |
| 6 | gstack Iron Law — version-up 루프 실패 상한 (2026-04-20) | principle | orchestrator, iron-law, retry, STUCK | 인라인 |
| 7 | osascript 디버깅 — 레이어 격리로 root cause 빠르게 찾기 (2026-04-25) | tactical | osascript, 디버깅, bun, 레이어격리 | knowledge/debugging.md |
| 8 | Tauri webview에서 `window.open()` silent 실패 — 외부 URL은 항상 API.openInChrome (2026-04-26) | tactical | tauri, window.open, 외부URL | knowledge/react-frontend.md |
| 9 | ClipboardItem text/html+text/plain 이중 포맷으로 Slack 하이퍼링크 복사 (2026-04-28) | tactical | clipboard, slack, html, 하이퍼링크 | knowledge/react-frontend.md |
| 10 | `/compact`는 스킬에서 직접 호출 불가 — 생성된 요약을 제안하는 패턴으로 우회 (2026-05-01) | principle | claude-code, compact, 내장명령 | 인라인 |
| 11 | Claude Code 훅 exit code — non-zero는 UI를 블로킹한다 (2026-05-02) | principle | claude-code, hooks, exit-code, 블로킹 | 인라인 |
| 12 | Git worktree base ref: local branch vs. remote tracking — unpushed commits invisible (2026-05-17) | principle | git-worktree, base-ref, origin | knowledge/git-worktree.md |
| 13 | Browser cache busting: `?t=Date.now()` + `cache: 'no-store'` 둘 다 필요 (2026-05-17) | principle | fetch, cache, no-store, 캐시버스팅 | knowledge/react-frontend.md |
| 14 | Build "unchanged" ≠ 파일 미재기록 — onRefresh는 항상 호출해야 (2026-05-17) | principle | build, refresh, unchanged | knowledge/react-frontend.md |
| 15 | React 부모→자식 이벤트: 모노토닉 카운터 증가 패턴 (2026-05-17) | tactical | react, counter, props, 이벤트 | knowledge/react-frontend.md |
| 16 | Node.js native `fs.watch({ recursive: true })` macOS에서 chokidar 없이 동작 (2026-05-17) | principle | nodejs, fs.watch, macos, chokidar | knowledge/misc-tooling.md |
| 17 | HTML 목록 스크래핑 — 복합 정규식 대신 분리 추출 후 index 매칭 (2026-05-17) | tactical | 정규식, 스크래핑, html | knowledge/debugging.md |
| 18 | `[^"']*` 정규식 — 혼합 따옴표 HTML 속성에서 조기 종료 (2026-05-17) | tactical | 정규식, html-attribute, 따옴표 | knowledge/debugging.md |
| 19 | SSE 이벤트 핸들러에서 연관 React state 동시 호출 필요 (2026-05-17) | tactical | react, sse, state, 배칭 | knowledge/react-frontend.md |
| 20 | Pull merge: 동일 폴더 다른 ID 중복 방지 — 결정적 ID + folderPath dedup (2026-05-17) | principle | supabase, dedup, sync, deterministic-id | knowledge/data-sync-db.md |
| 21 | Merge 전략: 사용자 직접 편집 필드는 local-first (2026-05-17) | principle | merge, local-first, 동기화 | knowledge/data-sync-db.md |
| 22 | ~/.claude/settings.json extraKnownMarketplaces는 객체 shape 필수 (2026-05-17) | tactical | claude-code, marketplace, settings.json | knowledge/claude-code-platform.md |
| 23 | 배포 웹 UI 버그는 빌드 설정 먼저 확인 — `vercel.json` / `vite.*.config.ts` 추적 (2026-05-17) | principle | vercel, vite, 빌드설정, 진입점 | knowledge/deployment.md |
| 24 | 멀티 entry Vite 프로젝트는 entry별 분리 모델 (2026-05-17) | tactical | vite, multi-entry, config | knowledge/deployment.md |
| 25 | globals.css element selector vs 인라인 스타일 명시도 충돌 (2026-05-19) | principle | css, 명시도, tailwind, globals | knowledge/css-design.md |
| 26 | sticky 헤더 대응 스크롤 오프셋 패턴 (2026-05-19) | tactical | scroll, sticky, offset | knowledge/css-design.md |
| 27 | aria-selected CSS selector 기반 chip 상태 패턴 (2026-05-19) | tactical | aria-selected, chip, css | knowledge/css-design.md |
| 28 | CSS 디자인 토큰 통일 — bg-white/bg-slate-900 교체 전략 (2026-05-19) | principle | css-token, 다크모드, tailwind | knowledge/css-design.md |
| 29 | Git Worktree 파일 격리 — 수정은 해당 브랜치에만 적용 (2026-05-20) | principle | git-worktree, 격리, 파일 | knowledge/git-worktree.md |
| 30 | Vite Dev Server는 자신의 소스 디렉토리만 Watch (2026-05-20) | principle | vite, watch, worktree, hmr | knowledge/git-worktree.md |
| 31 | Object Spread 시 commandPath 등 상위 속성 상속 차단 패턴 (2026-05-20) | tactical | spread, commandPath, undefined | knowledge/react-frontend.md |
| 32 | Worktree base ref mismatch — origin/main vs 로컬 main (2026-05-22) | tactical | git-worktree, origin, mismatch | knowledge/git-worktree.md |
| 33 | 단일 레코드 반복 태스크의 done 리셋 패턴 (2026-05-22) | principle | supabase, recurring, done-리셋 | knowledge/data-sync-db.md |
| 34 | 완료 후 즉시 재등장: virtual spread 패턴으로 다음 주기 표현 (2026-05-22) | principle | react, virtual-spread, 주기UI | knowledge/react-frontend.md |
| 35 | done_at UTC timestamptz → 로컬 날짜 변환 비교 (2026-05-22) | tactical | timezone, timestamptz, utc | knowledge/data-sync-db.md |
| 36 | Python으로 merge conflict marker를 즉석 파싱·해결 (2026-05-22) | tactical | merge-conflict, python, marker | knowledge/git-worktree.md |
| 37 | Claude Code CLI를 Bun 서버 서브프로세스로 AI 추론 백엔드로 활용 (2026-05-23) | principle | claude-cli, bun, subprocess, -p | knowledge/claude-code-platform.md |
| 38 | 사이드바 버튼 중복 — 메인 영역이 primary, 사이드바는 secondary (2026-05-23) | tactical | ui, 사이드바, 버튼중복 | knowledge/misc-tooling.md |
| 39 | SVG 일러스트로 스크린샷 완전 대체 전략 (2026-05-23) | principle | svg, 스크린샷, 일러스트 | knowledge/misc-tooling.md |
| 40 | Bash heredoc으로 멀티라인 파일 생성 (Write 도구 차단 우회) (2026-05-23) | principle | heredoc, bash, write-차단 | knowledge/git-worktree.md |
| 41 | Python 인라인 스크립트로 TSX 수술적 문자열 교체 (Edit 도구 차단 우회) (2026-05-23) | principle | python, edit-차단, str.replace | knowledge/git-worktree.md |
| 42 | useState + onChange 정규화 → live CodeBlock 주입 패턴 (2026-05-23) | tactical | react, input, 정규화, codeblock | knowledge/react-frontend.md |
| 43 | Git worktree 삭제 후에도 세션 도구 차단 상태 유지 (2026-05-23) | tactical | worktree, 도구차단, 세션 | knowledge/git-worktree.md |
| 44 | ScreenshotPlaceholder 점진적 fallback 설계 패턴 (2026-05-23) | tactical | placeholder, fallback, 스크린샷 | knowledge/misc-tooling.md |
| 45 | 마켓플레이스 플러그인 폴더명 vs 캐노니컬 이름 — 항상 manifest 우선 (2026-05-23) | principle | marketplace, canonical-name, manifest | knowledge/claude-code-platform.md |
| 46 | claude --bg 플래그: CLI 내장 백그라운드 에이전트 실행 (2026-05-23) | principle | claude-cli, bg, 백그라운드 | knowledge/claude-code-platform.md |
| 47 | Next.js에서 useState 초기화에 localStorage 사용 금지 — useEffect 패턴 필수 (2026-05-23) | principle | nextjs, localstorage, ssr, useeffect | knowledge/react-frontend.md |
| 48 | 터미널 선택자 UI — TYPE(라디오)과 MODE(토글) 분리 패턴 (2026-05-23) | tactical | ui, radio, toggle, type-mode | knowledge/react-frontend.md |
| 49 | known_marketplaces.json은 신뢰할 만한 source-of-truth가 아니다 — 자동 기록된 URL은 잘못될 수 있음 (2026-05-23) | principle | known_marketplaces, 검증, source | knowledge/claude-code-platform.md |
| 50 | 아이콘 Morph — absolute+scale/opacity 토글 패턴 (2026-05-23) | tactical | icon, transition, morph | knowledge/react-frontend.md |
| 51 | Tailwind v4 `@theme inline` — CSS 변수 → 유틸리티 브리지 필수 (2026-05-23) | principle | tailwind-v4, theme-inline, css변수 | knowledge/css-design.md |
| 52 | `navigator.clipboard` 비보안 컨텍스트 Fallback 패턴 (2026-05-23) | tactical | clipboard, fallback, securecontext | knowledge/react-frontend.md |
| 53 | fp_logs 복원 시 failed 상태는 silent drop — stale 실패 기록을 오류 배지로 부활 금지 (2026-05-30) | principle | 로그복원, 상태, failed | knowledge/data-sync-db.md |
| 54 | Git 워크트리의 node_modules — Turbopack은 심링크 거부, npm install 필수 (2026-05-30) | principle | worktree, node_modules, turbopack | knowledge/git-worktree.md |
| 55 | 시스템 공통 데이터는 임의 대표 엔트리에서 읽어도 안전 (2026-05-30) | tactical | quota, system-wide, 대표엔트리 | knowledge/data-sync-db.md |
| 56 | vercel --prod는 Claude Code auto-mode에서 항상 차단됨 (2026-05-30) | tactical | vercel, prod, auto-mode, 차단 | knowledge/deployment.md |
| 57 | content 컬럼 센티넬 접두사로 스키마 마이그레이션 없이 새 콘텐츠 타입 추가 (2026-05-30) | principle | sentinel, schema, content컬럼 | knowledge/data-sync-db.md |
| 58 | window CustomEvent로 React 레이어 밖에서 컴포넌트 간 느슨한 결합 (2026-05-30) | principle | customevent, pub-sub, react | knowledge/react-frontend.md |
| 59 | Next.js App Router에서 인증 사용자 전용 UI는 (main)/layout에 마운트 (2026-05-30) | tactical | nextjs, layout, auth, 라우트그룹 | knowledge/react-frontend.md |
| 60 | 기능 구현 전 코드베이스에서 기존 구현 탐색 필수 (2026-05-30) | principle | grep, 기존구현, 탐색 | knowledge/misc-tooling.md |
| 61 | 메모리 불만 시 먼저 어느 프로세스가 RSS를 소유하는지 확인 (2026-05-30) | principle | 메모리, ps, rss, 프로세스 | knowledge/debugging.md |
| 62 | manualChunks는 캐시 효율이지 런타임 메모리 감소가 아니다 (2026-05-30) | principle | manualchunks, 캐시, react-lazy | knowledge/react-frontend.md |
| 63 | document.hidden으로 setInterval 폴링 게이팅 — Playwright로 검증 (2026-05-30) | principle | polling, document.hidden, setinterval | knowledge/react-frontend.md |
| 64 | React.lazy + Suspense는 Tauri WebKit 웹뷰에서 정상 동작 (2026-05-30) | tactical | react-lazy, suspense, tauri | knowledge/react-frontend.md |
| 65 | Playwright adversarial 워크플로우로 메모리 누수 후보 기각 (2026-05-30) | tactical | playwright, 메모리검증, heap | knowledge/debugging.md |
| 66 | 포트 매니저 앱 JS heap 기준값 — 15-18MB 안정 (2026-05-30) | tactical | heap, 기준값, 포트매니저 | knowledge/debugging.md |
| 67 | 배포 직후 화면 깨짐 — Vercel CDN 번들 mismatch artifact (2026-06-09) | tactical | vercel, cdn, 재배포 | knowledge/deployment.md |
| 68 | 대형 JSX 파일에서 `</>}` vs `})()}` 구조 추적 패턴 (2026-06-09) | principle | jsx, 구조추적, fragment, iife | knowledge/debugging.md |
| 69 | 의존성 제거 결정의 커플링 드리프트 — repo-wide grep 통과 후에만 ✅ 반영됨 (2026-06-12) | principle | 커플링, 드리프트, grep, 반영됨 | knowledge/claude-code-platform.md |
| 70 | 외부 소스 원칙 추출 — 생성/기각(adversarial refuter) 단계 분리 (2026-06-12) | tactical | 원칙추출, refuter, 기각률 | knowledge/claude-code-platform.md |
| 71 | 새 프로토콜은 grep 가능한 준수 아티팩트 문자열과 함께 설계 (2026-06-12) | principle | 프로토콜, 아티팩트, 검증가능성 | knowledge/claude-code-platform.md |
| 72 | 하드코딩 시크릿 제거 ≠ 완료 — provider 측 rotation이 별도 필수 단계 (2026-06-12) | principle | 보안, 시크릿, rotation, settings | knowledge/claude-code-platform.md |
| 73 | 컨텍스트 없는 재개 요청 — episodic memory 검색을 첫 단계로 (2026-06-12) | principle | episodic-memory, 재개, 세션복원 | knowledge/claude-code-platform.md |
| 74 | JSON 설정 파일 수정은 텍스트 편집 대신 json.load/json.dump 라운드트립 (2026-06-12) | tactical | json, settings, python, 안전편집 | knowledge/claude-code-platform.md |
| 75 | GitHub Actions schedule cold-start trap — 파일이 없던 시각의 크론은 소급 발화하지 않는다 (2026-06-14) | principle | github-actions, schedule, cron, cold-start | knowledge/deployment.md |
| 76 | NEXT_PUBLIC_ anon key를 서버 전용 route에서 쓰면 RLS에 silently 차단된다 (2026-06-14) | principle | supabase, anon-key, service-role, RLS, nextjs | knowledge/deployment.md |
| 77 | fp_logs unique index를 분산 뮤텍스로 활용 — Redis 없이 serverless 하루 1회 실행 보장 (2026-06-14) | principle | mutex, unique-index, serverless, fp_logs, sentinel | knowledge/data-sync-db.md |
| 78 | 멀티-phase 서버리스 함수는 phase 경계마다 wall-clock 예산 점검을 삽입한다 (2026-06-14) | principle | serverless, budget-guard, maxDuration, partial-response | knowledge/deployment.md |
| 79 | curl에 --max-time 없이 GitHub Actions에서 hang 시 SIGKILL — 에러 원인 알 수 없음 (2026-06-14) | tactical | curl, max-time, github-actions, timeout | knowledge/deployment.md |
| 80 | GitHub Actions run: 블록에서 secrets는 env: 블록으로 분리해야 shell injection 방지 (2026-06-14) | principle | github-actions, secrets, env-block, shell-injection | knowledge/deployment.md |
| 81 | Windows 플랫폼 기능은 React/TS/Rust 3-레이어 동시 점검 필수 (2026-06-14) | principle | tauri, windows, platform, isWindows, cfg! | knowledge/tauri-windows.md |
| 82 | spawn_wt_cmd — Windows Terminal(wt.exe) 없을 때 cmd.exe 폴백 패턴 (2026-06-14) | tactical | tauri, windows, terminal, spawn, wt.exe | knowledge/tauri-windows.md |
| 83 | 빌드 아티팩트 unstaged → git pull --rebase 실패 (2026-06-14) | tactical | git, pull, rebase, unstaged, build-artifact | knowledge/git-worktree.md |
| 84 | 멀티기기 build-number 역행 방지 — 빌드 전 pull 필수 (2026-06-14) | tactical | tauri, build-number, multi-device, pull | knowledge/tauri-windows.md |
| 85 | minified 번들에서 배포 반영 검증은 property name / JS 패턴으로 (2026-06-17) | tactical | vercel, minify, bundle, 배포검증, property-name | 인라인 |
| 86 | 세그먼트별 컬럼 있을 때 전체 합계 fallback은 세그먼트값 NULL 조건에만 (2026-06-17) | principle | cus_type, fallback, 집계, segment, data-modeling | 인라인 |
| 87 | 구조화 JSON 추출 태스크에는 소형 LLM + 출력 토큰 상한 축소가 충분하다 (2026-06-30) | tactical | llm, gpt-4o-mini, token, latency, structured-output | 인라인 |
| 88 | 단일 LLM 호출에서 다중 엔티티를 동시 추출하여 복합 발화를 처리한다 (2026-06-30) | principle | llm, schema, multi-entity, voice-order, response-design | 인라인 |
| 89 | 멀티에이전트 오케스트레이션 벤치마크 — CrewAI/AutoGen/ChatDev → P1~P5 이식 (2026-07-02) | principle | orchestration, crewai, autogen, chatdev, speaker-selection, termination, chain-manifest, role-play, persona | knowledge/multi-agent-orchestration.md |
| 90 | Next.js API route의 준-정적 데이터는 모듈-레벨 TTL 캐시로 요청당 반복 DB 조회를 제거한다 (2026-07-03) | principle | nextjs, cache, ttl, serverless, supabase, latency | knowledge/deployment.md |
| 91 | 대시보드 미해결처럼 보이는 값 — snapshot 필드 vs live-computed 필드 구분 (2026-07-03) | principle | dashboard, snapshot-field, netting, ux, debugging | knowledge/debugging.md |
| 92 | 이중 로그인 아키텍처에서 세션 게이트 API는 다수 유저에게 상시 401을 낼 수 있다 (2026-07-05) | principle | auth, nextauth, session, localstorage, dual-login, 401 | knowledge/debugging.md |
| 93 | 이름/식별자 퍼지 매칭은 substring 포함 대신 Levenshtein 거리만 사용 (2026-07-05) | principle | fuzzy-match, levenshtein, substring, 오매칭, string-matching | knowledge/debugging.md |
| 94 | 공유 렌더 함수의 early-return 순서가 서브플로우 상태를 가릴 수 있다 (2026-07-05) | principle | react, early-return, render-order, sub-flow, softlock | knowledge/react-frontend.md |

> 참고: #7-9, #12-71은 프로젝트-특화 학습으로 `knowledge/` 파일에 이관됨 (2026-06 재구조화).
> 과거 어긋났던 #8의 배치 순서도 이관 시 번호순으로 정렬 수정됨. 번호는 전역 유일하며 재사용하지 않는다.

### 오케스트레이터 도메인 학습 (인라인: #1-6, #10-11)

### 1. version-up은 학습 캡처 + 디렉토리 복사 두 단계여야 한다 (2026-04-11)
<!-- tier: principle -->

- **상황**: 초기 version-up이 디렉토리 복사 + VERSION 번호 증가만 수행
- **발견**: 단순 cp는 파일 내용이 동일하므로 "경험 저장소"가 아니라 "버전 스냅샷"에 불과함. 새 VERSION 디렉토리에 이번 세션에서 배운 내용이 없으면 버전 증가의 의미가 없다.
- **교훈**: version-up 실행 시 반드시 AskUserQuestion으로 학습 내용을 받아 SKILL.md 노하우 섹션에 추가한 뒤 cp 실행. 학습 없이 버전만 올리는 것은 의미 없음.

### 2. `all` 키워드로 3개 도메인 한번에 버전업 (2026-04-11)
<!-- tier: principle -->

- **상황**: 도메인별로 version-up을 3번 따로 실행해야 했음
- **발견**: `test` → `plan` → `review` 순서로 순차 처리하면 한 번의 명령으로 모두 처리 가능
- **교훈**: `/cs-experiencing version-up all` 지원으로 워크플로우 간소화. 각 도메인마다 학습 캡처 인터랙션이 뜨므로 3번의 입력 기회가 생김.

### 3. AI 자동 학습 추출 — 수동 입력보다 먼저 시도 (2026-04-14)
<!-- tier: principle -->

- **상황**: version-up 시 항상 수동으로 학습 내용을 입력해야 했음. 세션이 길면 무엇을 배웠는지 직접 요약하기 번거로움.
- **발견**: AI가 세션 컨텍스트를 먼저 분석하면 핵심 발견사항(버그 원인, 해결 패턴, 예상 외 동작 등)을 자동 추출 가능. 사용자는 제안을 확인만 하면 됨.
- **교훈**: STEP 1을 "AI 분석 → 제안 → 확인" 순서로 바꾸면 마찰 최소화. 발견사항이 없을 때만 기존 수동 입력 fallback.

### 4. 외부 소스 학습 통합 — bkit·Karpathy·gstack 패턴 (2026-04-20)
<!-- tier: principle -->

- **상황**: bkit-claude-code, Karpathy-skills, gstack 3개 외부 레포 분석 후 cs-experiencing 및 4개 도메인에 적용 가능한 패턴을 발견함
- **발견**: bkit → Evaluator-Optimizer 루프(등급 미달 자동 재실행), Checkpoint 패턴(단계 간 사용자 확인 게이트). Karpathy → Think-Before-Coding(모호성 선제 해소), Goal-Driven Execution(성공 기준 명시). gstack → 선형 파이프라인(review→design→test), CSS/JSX 리스크 버짓 분리, 크로스 모델 듀얼 리뷰.
- **교훈**: 외부 패턴 학습은 각 도메인 SKILL.md 노하우에 직접 추가. 오케스트레이터(experiencing)에는 파이프라인 커맨드 + experiencing-lead/preflight-checker 신규 에이전트로 반영. 학습 후 즉시 version-up 실행.
- 2026-07-05 addendum: CS-plugin 자기개선 외에, **클라이언트 프로젝트 코드 개선**을 위해 사용자가 건넨 외부 교육자료(대학원 실습 .ipynb 등)를 분석하는 경우도 같은 메커니즘이 적용됨. 이때 CEO는 자료 속 구성요소(예: function calling, RAG, 세션 메모리)를 프로젝트의 실제 코드 아키텍처에 1:1로 매핑해 "어떤 기능을 말하는지"부터 명확히 하고(먹고공부하자 세션: "채팅 기능"을 팀채팅이 아닌 AI 봇으로 정확히 재해석), Mode A 직접 분석 + 우선순위별 개선안 제시로 이어감. 외부지식게이트(Phase -3) 호출 없이도 자료가 이미 제공된 경우 바로 분석 가능.

### 5. bkit btw 패턴 — 세션 중 아이디어 즉시 캡처 (2026-04-20)
<!-- tier: principle -->

- **상황**: version-up 시 "이번 세션에서 뭘 개선해야 할지" 기억이 흐릿함. 작업 중 발견한 개선점이 세션 끝에 사라짐.
- **발견**: bkit의 btw(By-The-Way) 패턴: 작업 중 즉시 캡처 → JSON 파일에 pending 상태로 저장 → version-up 시 pending 항목을 먼저 보여주고 반영 여부 결정.
- **교훈**: `/cs-experiencing btw [idea]` 명령 추가. 세션 중 발견사항을 즉시 캡처하면 version-up의 AI 분석 단계를 보완할 수 있음.

### 6. gstack Iron Law — version-up 루프 실패 상한 (2026-04-20)
<!-- tier: principle -->

- **상황**: version-up all 실행 중 특정 도메인에서 오류가 생기면 전체가 중단되거나 무한 재시도 가능성 있음.
- **발견**: gstack Iron Law: "동일 문제에 3회 실패 시 강제 중단 + STUCK 리포트." version-up에도 동일 원칙 적용 — 도메인 처리 실패 2회 시 해당 도메인 스킵 + 경고 출력 후 다음 도메인으로.
- **교훈**: `version-up all` 프로토콜에 도메인별 retry 상한(2회) 추가. 실패 도메인은 스킵하고 `⚠️ [DOMAIN] 스킵됨 — 수동 확인 필요` 출력 후 계속 진행.
- ✅ 반영됨 (2026-06) — experiencing-lead.md Phase 2 bounded re-run loop(도메인당 상한 2라운드 + STUCK 리포트)로 코드화

### 10. `/compact`는 스킬에서 직접 호출 불가 — 생성된 요약을 제안하는 패턴으로 우회 (2026-05-01)
<!-- tier: principle -->

- **상황**: cs-end가 세션 종결 자동화를 담당하지만 `/compact`(context 압축)는 별도로 실행해야 했음. 사용자가 "원커맨드 종결"을 원했으나 cs-end가 compact를 수행하지 않았음.
- **발견**: `/compact`는 Claude Code 내장 명령으로, 스킬/커맨드에서 프로그래밍적으로 호출이 불가능함. allowed-tools에도 invoke-command 같은 도구가 없음.
- **교훈**: 자동 호출이 불가능한 명령이 필요한 경우, 해당 명령의 인자를 AI가 생성하여 사용자가 복사-실행할 수 있도록 제안하는 패턴이 최선. cs-end Phase 6: Phase 1 분석 결과로 세션 요약 1-2줄 생성 → `/compact [요약]` 형식으로 출력 → 사용자가 그대로 실행. `--no-compact` 플래그로 생략 가능.

### 11. Claude Code 훅 exit code — non-zero는 UI를 블로킹한다 (2026-05-02)
<!-- tier: principle -->

- **상황**: CS볼트V5(Obsidian vault) 등 `.env`가 없는 폴더에서 작업할 때마다 Claude Code 입력창이 회색으로 굳어버림
- **발견**: `notification-hook.sh`, `stop-hook.sh` 모두 `.env` 없을 시 `exit 1` 반환 → Claude Code는 훅 비정상 종료를 UI 블로킹으로 처리. 훅이 "해당 없음"인 경우에도 `exit 1`이면 입력창이 그레이아웃됨
- **교훈**: 훅의 전제조건(`.env`, 토큰 등)이 충족되지 않을 때는 반드시 `exit 0`으로 종료. `exit 1`은 의도적으로 사용자를 멈춰야 할 진짜 오류에만 사용. "이 훅은 여기에 해당 없음" = `exit 0`

### 12. Korean 파일에서 Edit 툴 실패 — Python writelines 패턴 (2026-06-12)
<!-- tier: principle -->

- **상황**: Next.js 대시보드(`app/mau/page.tsx`)에서 한국어 문자열이 포함된 라인을 Edit 툴로 수정하려 하자 old_string 매칭이 반복 실패함.
- **발견**: Edit 툴은 멀티바이트(한국어) 문자 포함 문자열 매칭에 신뢰할 수 없음. Python `readlines()` + 0-index 행 번호 직접 지정 후 `writelines()`가 안정적 대안.
- **교훈**: 한국어가 포함된 파일 수정 시 Edit 툴 먼저 시도하지 말고 즉시 Python `readlines/writelines` + 행 번호 패턴으로 처리하라.

### 13. Derived slice 재사용으로 다수 sparkline 데이터 생성 (2026-06-12)
<!-- tier: principle -->

- **상황**: MAU 히어로 카드에 세그먼트별(신규방문자, Returning, Resurrecting, 기존→해외첫거래) 스파크라인을 추가해야 했으나, 각 세그먼트마다 별도 DB 쿼리나 state를 만들 뻔했음.
- **발견**: 이미 계산된 `heroSnapSlice = snapshots.slice(0, selectedMonthIdx + 1)`를 재사용하고, 각 세그먼트가 `.map(s => ({ name: s.label, value: s.traders.returning }))` 처럼 다른 필드만 매핑하면 N개 스파크라인 데이터를 1개 slice에서 도출 가능.
- **교훈**: 새 데이터 파이프라인 전에 기존 derived slice/computed 데이터를 다른 필드 매핑으로 재활용할 수 있는지 먼저 확인하라. 대시보드에서 하나의 base slice → 여러 시리즈 파생 패턴은 state 폭발 없이 확장 가능.

### 14. HeroSparkline optional height prop — 컴포넌트 복제 없이 크기 변형 흡수 (2026-06-12)
<!-- tier: tactical -->

- **상황**: 히어로 카드 전체(36px)와 세그먼트 셀 인라인(24px) 두 크기로 동일 HeroSparkline 컴포넌트를 써야 했음.
- **발견**: `height?: number = 36` optional prop 추가로 새 컴포넌트 없이 해결. `<HeroSparkline data={...} color={...} height={24} />`.
- **교훈**: 기존 컴포넌트 복제보다 optional prop으로 변형을 흡수하는 것이 먼저. 렌더 조건: `spark.length > 1` 가드 필수.

### 15. git cat-file + branch --contains — 특정 커밋의 브랜치 추적 2-step 패턴 (2026-06-17)
<!-- tier: tactical -->

- **상황**: 사용자가 특정 커밋 해시(defd9c1...)를 로컬에 pull 요청 시, 해당 커밋이 어느 원격 브랜치에 속하는지 먼저 확인해야 했음.
- **발견**: `git fetch origin` → `git cat-file -t <hash>`로 객체 존재 확인 → `git branch -r --contains <hash>`로 포함 브랜치 특정 → `git merge --ff-only <remote-branch>` 순으로 안전하게 적용. fetch 없이는 `unknown revision` 오류 발생.
- **교훈**: 알 수 없는 커밋 해시 merge 요청: (1) fetch → (2) cat-file -t 존재 확인 → (3) branch -r --contains 브랜치 특정 → (4) ff-only merge. 이 순서를 생략하면 중단됨.
- **근거**: `git merge --ff-only origin/claude/csncompany-plugin-auto-install-am7h2x` → "Fast-forward / 6 files changed, 175 insertions(+)" (2026-06-17 세션)

### 16. CSnCompany 공식 플러그인 헬스 게이트 — preflight(-3.5)에서 의존성 조기 차단 (2026-06-17)
<!-- tier: tactical -->

- **상황**: cs-ceo, CS-test, CS-codebase-review가 serena/playwright/hookify 등 공식 플러그인에 의존하지만 런타임 진입 후에야 누락을 감지해 비용이 낭비되었음.
- **발견**: pre_pass.py에 `_find_official_plugin()` + `_find_mcp_server()` 헬퍼를 추가하고 ceo.md Phase -3.5에서 preflight 단계에 감지·차단. CS-test는 playwright 미설치 시 Install/Skip/Abort AskUserQuestion 제공. OFFICIAL-PLUGINS.md가 설치 명령어 단일 진실.
- **교훈**: 공식 플러그인 의존성은 멀티에이전트 워크플로우 진입 전 preflight 단계(-3.5)에서 차단하는 것이 비용 효율적. context7 패턴(누락 감지 → AskUserQuestion 설치 유도)을 공식 플러그인에 동일 적용.
- **근거**: `defd9c1 feat: serena 통합 + 공식 플러그인 자동설치 유도 시스템 추가` — ceo.md +56줄, pre_pass.py +64줄, OFFICIAL-PLUGINS.md 신규 (2026-06-17)

### 85. minified 번들에서 배포 반영 검증은 property name / JS 패턴으로 (2026-06-17)
<!-- tier: tactical -->

- **상황**: Vercel에 코드 픽스가 반영됐는지 확인하기 위해 minified JS 번들에서 변경 흔적을 탐색해야 했음.
- **발견**: minified JS는 지역 변수명(rollingTraderTotal 등)을 단축 식별자로 치환하므로 원본 변수명으로 grep해도 검색 불가. 반면 객체 property name(`d8_total_uv`), 문자열 리터럴, 특징적인 연산자 패턴(`??` + 삼항 조합)은 minify 후에도 보존되어 배포 여부 판별 지표로 사용 가능.
- **교훈**: 배포 검증 시 변수명 대신 property name, 문자열 리터럴, 로직 패턴(??/삼항 조합)을 grep 대상으로 사용한다.
- **근거**: `rollingTraderTotal` grep → 검색 불가, `d8_total_uv` property name + `??` 패턴으로 Before/After 구분 성공 (page-7236727e66aef288.js, dash1-v2 세션 2026-06-17)

### 87. 구조화 JSON 추출 태스크에는 소형 LLM + 출력 토큰 상한 축소가 충분하다 (2026-06-30)
<!-- tier: tactical -->

- **상황**: voice-order API의 응답 지연 문제 해결 중 (gpt-5.5, max_completion_tokens=1000 사용)
- **발견**: 음식/커피 이름 매칭처럼 '후보 목록에서 선택 → 고정 포맷 JSON 반환'만 하는 태스크에서 대형 모델은 과도하다. gpt-4o-mini + 출력 토큰 200으로 교체했을 때 속도 3-5배 개선, 품질 동일.
- **교훈**: LLM 호출 설계 시 "패턴 매칭 → 고정 포맷 JSON 출력" 태스크라면 사용 가능한 최소 모델 + 예상 최대 출력 길이로 토큰 상한을 설정한다. 대형 모델은 자유 생성·다단계 추론이 필요한 경우에만 사용한다.
- **근거**: `route.ts line 84-89: model "gpt-5.5" → "gpt-4o-mini", max_completion_tokens 1000 → 200` (2026-06-30 세션, 속도 3-5배 개선 확인)

### 88. 단일 LLM 호출에서 다중 엔티티를 동시 추출하여 복합 발화를 처리한다 (2026-06-30)
<!-- tier: principle -->

- **상황**: "알탕에 카페라테아이스" 같은 rice+coffee 복합 발화가 rice만 추출되고 coffee는 버려지는 UX 문제 발견
- **발견**: rice/restaurant step의 system prompt에 coffeeMatched·coffeeTemp 보조 필드를 추가하자, 기존 GPT 호출 1회로 두 엔티티를 동시 추출할 수 있었다. 별도 coffee step 호출 없이 confirm으로 즉시 이동 가능.
- **교훈**: 사용자 발화에 여러 엔티티가 섞일 가능성이 있는 step은 system prompt JSON 스키마에 보조 엔티티 필드를 미리 정의한다. LLM 추가 호출 없이 응답 스키마 확장만으로 복합 입력을 처리할 수 있다 — per-invocation overhead >> per-token cost이므로 스키마 확장이 항상 추가 호출보다 싸다.
- **근거**: `buildSystemPrompt() rice step: coffeeMatched/coffeeTemp 필드 추가 → voice-order-bot.tsx coffeeResult로 즉시 confirm 이동` (app/api/voice-order/route.ts + components/voice-order-bot.tsx, 2026-06-30)

### 86. 세그먼트별 컬럼 있을 때 전체 합계 fallback은 세그먼트값 NULL 조건에만 (2026-06-17)
<!-- tier: principle -->

- **상황**: 퍼널 D8 체결완료 카드가 신규고객(M0) 선택 시 전체 거래고객수(312,218)를 표시. D5(22,851)보다 큰 비정상 값으로 발현.
- **발견**: 버그 원인: `rollingTraderTotal`(mau_transaction_rolling.total_cus_cnt = 전체 합계)을 cus_type 분기 없이 모든 케이스에 적용. `funnel_rolling.total_ose_trd_cus_cnt`는 cus_type별로 분리된 실제 값을 가짐. DB에 세그먼트별 컬럼과 전체 합계 컬럼이 공존할 때, 전체 합계를 기본값으로 쓰면 세그먼트 모드에서 전체값이 세그먼트값을 무음으로 대체한다.
- **교훈**: 세그먼트(cus_type)별로 분리된 컬럼이 있을 때, 전체 합계 fallback은 세그먼트별 값이 NULL인 경우에만 적용한다. `segmentCol ?? aggregateFallback` 패턴이 정준(canonical) 형태. 어떤 스택에서도 "세그먼트 컬럼 우선, 전체 합계는 마지막 fallback" 원칙이 적용된다.
- **근거**: Before: `val: (period === 'rolling' ? rollingTraderTotal : ...)` → 신규고객 D8=312,218 / After: `val: (d.d8_total_uv ?? (period === 'rolling' ? rollingTraderTotal : ...))` → 신규고객 D8=1,829 (app/mau/page.tsx line 3433, 2026-06-17)

### 95. macOS 앱 샌드박스 컨테이너 파일은 Full Disk Access/Automation 권한 없는 터미널에서 접근 불가 (2026-07-08)
<!-- tier: principle, error-ref: ERR-2026-07-08-001 -->

- **상황**: Claude Code 세션에서 Shottr(샌드박스 배포 스크린샷 앱)가 저장한 스크린샷 파일(`~/Library/Containers/cc.ffitch.shottr/Data/tmp/.../*.png`)을 Read/Bash cp/osascript로 접근 시도.
- **발견**: Read 도구 EPERM, `cp` EPERM("Operation not permitted"), `osascript ... tell application "Finder"` -1743("Not authorized to send Apple events to Finder") — 세 가지 방식 모두 실패. macOS TCC가 다른 앱의 `~/Library/Containers/<bundle-id>/...` 트리에 대한 접근을 Full Disk Access로, Finder 등 타 앱 자동화를 Automation 권한으로 별도 게이팅하기 때문. 이는 호출 프로세스(터미널)의 TCC 권한 부여 여부에 달린 조건부 차단이며 — Full Disk Access가 부여된 터미널이라면 접근 가능하므로 "무조건 불가"가 아니라 "권한 미부여 시 불가"로 이해해야 함(verifier 지적).
- **교훈**: 경로가 `~/Library/Containers/<bundle-id>/...` 형태로 보이면 즉시 접근 실패를 예상하고, Read/cp/osascript 재시도로 시간 쓰지 말고 바로 사용자에게 파일을 비샌드박스 위치(Desktop, 프로젝트 디렉토리 등)로 옮겨달라고 요청하는 것으로 전환한다.
- **근거**: Derivative1 프로젝트 세션 2026-07-08 — Read tool `EPERM: operation not permitted, open '/Users/gwanli/Library/Containers/cc.ffitch.shottr/...'`, `cp` → `Operation not permitted`, `osascript` → `29:202: execution error: Not authorized to send Apple events to Finder. (-1743)` (동일 파일에 3가지 방식 모두 실패, skeptic verifier CONFIRMED)

### 96. React 클로저 stale state + Playwright ref 재사용은 querySelector 재조회 + 별도 evaluate 호출 + 클릭 간 지연으로 우회 (2026-07-08)
<!-- tier: principle -->

- **상황**: Playwright로 React 상태 기반 UI(수량 스테퍼, 빠른 화면 전환)를 자동 테스트하던 중 두 가지 문제 발생.
- **발견**: (1) `onClick={() => setQty(qty+1)}` 형태 핸들러에 동기 루프로 `.click()`을 연속 호출하면, 각 호출이 마지막 렌더 시점의 동일한 stale `qty`를 클로저로 캡처하고 있어 리렌더 전에 여러 번 호출해도 1회분만 반영됨 — React 업데이트 배칭 + 클로저의 조합으로 발생하는 표준적 현상(함수형 업데이터 `setQty(q => q+1)`을 쓰지 않는 한 재현됨). (2) 빠른 네비게이션 후 이전 스냅샷에서 얻은 element ref가 stale해져 엉뚱한 DOM에 반응함 — Playwright ref는 캡처 시점 스냅샷에 종속되는 것이 정상 동작.
- **교훈**: React 상태 UI를 Playwright `browser_evaluate`로 빠르게 조작할 때는 (1) 저장된 ref 재사용 대신 매번 `document.querySelector`로 재조회, (2) 클릭 직후 상태 확인은 같은 evaluate 호출이 아닌 별도의 후속 evaluate 호출로 분리(리렌더가 비동기이므로), (3) 연속 클릭 사이에 `await new Promise(r => setTimeout(r, 30))` 등 짧은 지연을 넣어 클로저 stale-state 언더카운트를 방지한다.
- **근거**: Derivative1 프로젝트 세션 2026-07-08 — 수량 스테퍼 동기 클릭 루프가 1회분만 반영, `async` evaluate + 클릭 간 30ms 지연으로 해결 확인; 화면 전환 후 stale ref로 인한 의도치 않은 화면 점프를 `document.querySelector` 기반 클릭 + 별도 evaluate 결과 조회로 해결 확인 (skeptic verifier CONFIRMED, React 배칭/클로저 시맨틱스는 버전 무관 안정 지식으로 판정)

### 97. worktree가 main을 점유 중이면 `gh pr merge`가 로컬 브랜치 동기화 실패로 막힌다 — `gh api PUT merge`로 우회 (2026-07-09)
<!-- tier: tactical, error-ref: ERR-2026-07-09-001 -->

- **상황**: portmanagement 프로젝트에서 `.claude/worktrees/last-run-sort` 워크트리로 작업한 PR을 사용자가 "메인에 머지해"라고 지시해 병합 시도.
- **발견**: 동일 레포의 다른 워크트리(원래 체크아웃 디렉토리)가 이미 `main`을 체크아웃하고 있으면, 일반 `gh pr merge`는 병합 후 로컬 main 브랜치를 갱신하려다 `fatal: 'main' is already used by worktree` 에러로 실패한다. `gh api repos/<owner>/<repo>/pulls/<N>/merge -X PUT -f merge_method=squash`로 GitHub API를 직접 호출하면 로컬 체크아웃 상태와 무관하게 원격에서 병합된다.
- **교훈**: worktree를 상시 여러 개 운용하는 리포에서 `gh pr merge`가 이 에러로 실패하면 재시도하지 말고 즉시 `gh api .../merge -X PUT`으로 전환한다.
- **근거**: `gh pr merge 3 --squash --delete-branch` → `failed to run git: fatal: 'main' is already used by worktree at '/Users/gwanli/product_2026/portmanagement'` / `gh api repos/intenet1001-commits/AgentsToZ_byCS/pulls/3/merge -X PUT -f merge_method=squash` → `{"merged":true}` (2026-07-09 세션)

### 98. 웹·앱이 같은 머신에서 동시 접근하는 상태는 localStorage 대신 공유 파일 + 이중 접근 경로로 관리한다 (2026-07-09)
<!-- tier: tactical -->

- **상황**: Tauri 앱(포트 관리 프로그램)에 "마지막 방문 시각" 라벨을 추가했는데, 사용자가 웹 브라우저 탭과 데스크톱 앱을 같이 써도 값이 같이 관리돼야 한다고 지적.
- **발견**: `localStorage`는 브라우저 오리진/Tauri webview별로 완전히 분리된 저장소라 웹에서 기록한 값이 앱에서 보이지 않고 그 반대도 마찬가지다. 이 프로젝트가 주 데이터(`ports.json`)에 이미 쓰던 패턴 — 앱 데이터 디렉토리의 공유 JSON 파일을 웹은 HTTP 엔드포인트(Bun api-server)로, 데스크톱 앱은 Tauri `invoke` 커맨드로 각각 읽고 쓰는 이중 접근 경로 — 를 그대로 적용해 해결했다. 동시 기록 충돌은 "더 최신 타임스탬프만 반영"으로 단순 해결 가능.
- **교훈**: 웹+데스크톱을 동시 지원하는 앱에서 여러 실행 표면(브라우저 탭, 웹뷰)이 공유해야 하는 새 상태를 추가할 때는 `localStorage`를 기본값으로 쓰지 말고, 처음부터 "공유 파일 + (HTTP 엔드포인트, 네이티브 invoke 커맨드) 이중 접근" 패턴을 채택한다. 이는 이 앱만의 관례가 아니라 하나의 머신에서 여러 JS 런타임(브라우저 vs 웹뷰)이 상태를 공유해야 하는 모든 dual-surface 앱에 적용되는 일반 원칙이다 — 구체적 저장 형식(JSON 파일 vs sqlite vs IPC)은 프로젝트마다 다를 수 있다 (skeptic verifier: 저장 형식 자체는 project-specific이라 tactical로 판정, 다만 "동일 머신 내 분리된 JS 런타임은 localStorage를 공유하지 않는다"는 근본 사실 자체는 안정적).
- **근거**: `last-visits.json`을 `~/Library/Application Support/com.portmanager.portmanager/`에 신설, `POST /api/last-visits`(웹) + `save_last_visit` Tauri invoke(앱) 양쪽 구현 → 브라우저에서 실행한 포트가 앱에서도 동일한 "마지막 실행" 시각으로 표시됨 확인 (2026-07-09 세션, PR #4)

### 99. "왜 반영이 안 됐지" 류 버그는 로직보다 표시 계층이 참조하는 데이터 소스가 최신 상태와 다른 경우가 많다 — 재시작/저장소 범위/이벤트 커버리지부터 점검 (2026-07-09)
<!-- tier: tactical -->

- **상황**: 한 세션 안에서 "반영이 안 된 것 같다"는 취지의 사용자 지적이 연속 3회 발생 — ① PR 머지 후에도 동작이 그대로였음 ② 웹/앱 간 값 불일치 ③ 실제 작업일보다 오래된 "마지막 실행" 표시.
- **발견**: 세 사례의 근본 원인이 각각 달랐다 — ① `--watch` 없이 떠 있던 Bun API 서버가 git pull 이후에도 프로세스 재시작 전까지 새 라우트를 인식하지 못함 ② `localStorage`가 웹/앱 실행 표면별로 분리된 저장소임 ③ UI 버튼 클릭 로그만으로는 터미널/에디터로 직접 한 작업을 감지하지 못함. 셋 다 "표시되는 값을 계산하는 로직"이 아니라 "그 값이 읽어오는 소스가 실제 최신 상태와 다른 곳"이 원인이었다.
- **교훈**: 사용자가 "반영이 안 됐다/이상하다"고 지적하면 로직을 먼저 의심하기 전에 (1) 관련 프로세스가 최신 코드로 재시작됐는지 (2) 값을 읽는 위치가 여러 실행 표면(웹/앱, 여러 프로세스)에서 동일한 소스를 가리키는지 (3) 기록되는 이벤트가 실제 활동 전체를 커버하는지를 먼저 점검한다. (skeptic verifier: 이 세션 3건만으로 "대부분"을 통계적으로 입증하진 못하나, 세 원인이 모두 "read path가 최신 소스를 안 보고 있다"는 동일 카테고리로 수렴한다는 점에서 재사용 가능한 디버깅 체크리스트로 유효 — 다만 새로운 발견이 아니라 기존 캐시/stale-state 디버깅 상식의 재확인이라 principle이 아닌 tactical로 판정)
- **근거**: "그대로인거같은데"(서버 미재시작, 재기동 후 해결) / "웹,앱을 동시에 적용한거같지는 않음"(localStorage 분리, last-visits.json 공유로 해결) / "11일전 이라고 뜬거자체가 이상함"(클릭 로그 vs git 커밋시각, git log 병합으로 해결) — 2026-07-09 portmanagement 세션, PR #3~#5
