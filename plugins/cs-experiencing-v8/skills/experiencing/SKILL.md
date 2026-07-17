---
name: cs-experiencing
user-invocable: true
description: |
  경험 지식 저장소 오케스트레이터.
  도메인별 누적 학습 조회, 실행, 버전 관리.
  Use when invoked via /cs-experiencing, or when user says "경험", "학습 실행", "버전업".
version: 8.2.4
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
   - 인라인 본문은 오케스트레이터 자체 도메인 학습에만 허용 — index-check 게이트가 인라인 개수 상한(15)을 강제하므로 프로젝트-특화 본문은 반드시 knowledge/로 라우팅한다
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

8. **무결성 게이트 (결정론적, 저장 직후 필수)**:
   ```bash
   bash "$BASE_PATH/shared/run_prepass.sh" index-check
   ```
   INDEX↔본문 정합성(C1 INDEX 누락 / C2 위치 포인터 / C3·C4 번호 유일성 / C5 연속성 / C6 인라인 상한 15)을
   기계 검증한다. `"ok": false`면 위반 항목을 수정한 뒤 재실행 — ok가 될 때까지 STEP 3으로 진행하지 않는다.
   (LLM 반박 패스 (a)~(d)는 내용 품질용이고, 구조 불변식은 이 게이트가 단일 진실.)

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

cs-experiencing 학습 INDEX 무결성도 같은 게이트에서 검증한다:

```bash
bash "$BASE_PATH/shared/run_prepass.sh" index-check
```

`"ok": false`면 commit/push로 진행하지 않는다.

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

### 학습 INDEX (1줄/항목, 단일 진실)

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
| 85 | minified 번들에서 배포 반영 검증은 property name / JS 패턴으로 (2026-06-17) | tactical | vercel, minify, bundle, 배포검증, property-name | knowledge/deployment.md |
| 86 | 세그먼트별 컬럼 있을 때 전체 합계 fallback은 세그먼트값 NULL 조건에만 (2026-06-17) | principle | cus_type, fallback, 집계, segment, data-modeling | knowledge/data-sync-db.md |
| 87 | 구조화 JSON 추출 태스크에는 소형 LLM + 출력 토큰 상한 축소가 충분하다 (2026-06-30) | tactical | llm, gpt-4o-mini, token, latency, structured-output | knowledge/llm-patterns.md |
| 88 | 단일 LLM 호출에서 다중 엔티티를 동시 추출하여 복합 발화를 처리한다 (2026-06-30) | principle | llm, schema, multi-entity, voice-order, response-design | knowledge/llm-patterns.md |
| 89 | 멀티에이전트 오케스트레이션 벤치마크 — CrewAI/AutoGen/ChatDev → P1~P5 이식 (2026-07-02) | principle | orchestration, crewai, autogen, chatdev, speaker-selection, termination, chain-manifest, role-play, persona | knowledge/multi-agent-orchestration.md |
| 90 | Next.js API route의 준-정적 데이터는 모듈-레벨 TTL 캐시로 요청당 반복 DB 조회를 제거한다 (2026-07-03) | principle | nextjs, cache, ttl, serverless, supabase, latency | knowledge/deployment.md |
| 91 | 대시보드 미해결처럼 보이는 값 — snapshot 필드 vs live-computed 필드 구분 (2026-07-03) | principle | dashboard, snapshot-field, netting, ux, debugging | knowledge/debugging.md |
| 92 | 이중 로그인 아키텍처에서 세션 게이트 API는 다수 유저에게 상시 401을 낼 수 있다 (2026-07-05) | principle | auth, nextauth, session, localstorage, dual-login, 401 | knowledge/debugging.md |
| 93 | 이름/식별자 퍼지 매칭은 substring 포함 대신 Levenshtein 거리만 사용 (2026-07-05) | principle | fuzzy-match, levenshtein, substring, 오매칭, string-matching | knowledge/debugging.md |
| 94 | 공유 렌더 함수의 early-return 순서가 서브플로우 상태를 가릴 수 있다 (2026-07-05) | principle | react, early-return, render-order, sub-flow, softlock | knowledge/react-frontend.md |
| 95 | macOS 앱 샌드박스 컨테이너 파일은 Full Disk Access/Automation 권한 없는 터미널에서 접근 불가 (2026-07-08) | principle | macos, tcc, sandbox, containers, full-disk-access | knowledge/misc-tooling.md |
| 96 | React 클로저 stale state + Playwright ref 재사용 — querySelector 재조회 + 별도 evaluate + 클릭 간 지연으로 우회 (2026-07-08) | principle | react, playwright, stale-state, closure, evaluate | knowledge/react-frontend.md |
| 97 | worktree가 main을 점유 중이면 gh pr merge 실패 — gh api PUT merge로 우회 (2026-07-09) | tactical | git-worktree, gh, pr-merge, api | knowledge/git-worktree.md |
| 98 | 웹·앱 동시 접근 상태는 localStorage 대신 공유 파일 + 이중 접근 경로로 관리 (2026-07-09) | tactical | localstorage, dual-surface, tauri, shared-file | knowledge/data-sync-db.md |
| 99 | "왜 반영이 안 됐지" 버그는 표시 계층이 참조하는 데이터 소스부터 점검 (2026-07-09) | tactical | stale-state, read-path, restart, debugging | knowledge/debugging.md |
| 100 | git worktree prune는 locked 항목을 설계상 조용히 건너뛴다 — remove 전 unlock 선행 필수 (2026-07-11) | principle | git-worktree, locked, prune, unlock | knowledge/git-worktree.md |
| 101 | git 계산값 0은 여러 실제 히스토리를 뭉갤 수 있다 — UI 라벨은 측정값을 설명해야지 이유를 단언하면 안 된다 (2026-07-11) | principle | git, ui-label, ambiguity, rev-list | knowledge/git-worktree.md |
| 102 | 심볼릭 링크를 지나는 경로에서 문자열 prefix 필터가 조용히 실패할 수 있다 (2026-07-11) | principle | symlink, realpath, path-filter, macos | knowledge/git-worktree.md |
| 103 | git add로 스테이징한 파일도 커밋 전에 내용을 직접 열어 확인해야 한다 — PII/실데이터 유출 방지 (2026-07-11) | principle | git, pii, data-safety, staging, commit-review | knowledge/git-worktree.md |
| 104 | OpenAI 추론형(reasoning-tier) 모델은 temperature 기본값(1) 외 다른 값을 거부한다 (2026-07-11) | tactical | openai, temperature, reasoning-model, api-error, gpt-5 | knowledge/llm-patterns.md |
| 105 | `{false && <JSX>}` 같은 리터럴 하드 비활성화 블록은 grep `"{false &&"`로만 발견됨 (2026-07-11) | tactical | react, jsx, dead-code, hard-disable, grep | knowledge/react-frontend.md |
| 106 | 실결제 앱은 adb 입력 인젝션을 보안 위협으로 감지해 자체 종료할 수 있다 (2026-07-14) | tactical | adb, android, security-sdk, mobile-automation, anti-tampering | knowledge/mobile-automation.md |
| 107 | 동일 화이트라벨 벤더의 패키지명 prefix가 adb 자동화 안정성을 예측하는 신호가 될 수 있다 (2026-07-14) | tactical | adb, android, package-name, whitelabel, heuristic | knowledge/mobile-automation.md |
| 108 | OCR로 저신뢰도 탐지된 아이콘의 바운딩박스 중심이 실제 탭 타겟과 어긋날 수 있다 (2026-07-14) | tactical | ocr, vision-framework, bounding-box, tap-coordinate, ui-automation | knowledge/mobile-automation.md |
| 109 | 안드로이드 하이브리드 앱에서 뒤로가기 도달 화면은 진입 경로에 따라 비결정적일 수 있다 (2026-07-14) | tactical | android, back-navigation, hybrid-app, ui-automation | knowledge/mobile-automation.md |
| 110 | NDS 감사 결과의 '지적된 노드 리스트'만 믿으면 안 됨 — 전체 프레임 색상 스윕 필요 (2026-07-15) | principle | design-system, audit, figma, sweep, nds | knowledge/figma-design-system.md |
| 111 | 재작성 시 토큰 값을 추측하지 말고 원본 컴포넌트에서 직접 샘플링 (2026-07-15) | principle | design-token, figma, sampling, code-generation, migration | knowledge/figma-design-system.md |
| 112 | 회귀 수정 시 임의값이 아니라 파일 내 형제 요소의 기존 컨벤션을 따른다 (2026-07-15) | principle | regression, convention, layout, figma, sibling | knowledge/figma-design-system.md |
| 113 | 디자인 파일이 시스템을 준수해도 코드 프로토타입은 완전히 별개 테마로 드리프트할 수 있다 (2026-07-15) | tactical | design-system, drift, figma, html, audit | knowledge/figma-design-system.md |
| 114 | 지식 축적 스킬은 주제가 아니라 "읽기 경로(read path)"로 분할해야 학습이 쌓일수록 강해진다 (2026-07-16) | principle | skill-design, context, scaling, read-path, knowledge-base | 인라인 |
| 115 | 구조 리팩터는 다른 파일의 지시문을 조용히 깨뜨린다 — 에이전트는 아무것도 등록하지 않고 "성공"을 보고한다 (2026-07-16) | principle | refactor, stale-docs, registry-sync, rehearsal, verifier | knowledge/claude-code-platform.md |
| 116 | Figma 커버리지는 파일의 목차나 get_metadata가 아니라 figma.root.children으로만 인증한다 (2026-07-16) | tactical | figma, coverage, enumeration, get_libraries, mcp | knowledge/figma-design-system.md |
| 117 | 우선순위 규칙에는 "무엇이 tie-breaker가 아닌지"를 명시해야 한다 — 정렬 순서와 인용 횟수는 그럴듯한 함정 (2026-07-16) | tactical | precedence, tie-breaker, instruction-design, rehearsal | knowledge/claude-code-platform.md |
| 118 | N개 서브에이전트의 합의는 진실이 아니다 — 각자 참인 국소 관찰이 거짓 전역 주장으로 굳는다 (2026-07-16) | principle | multi-agent, consensus, 일반화, 부정주장, verification | knowledge/multi-agent-orchestration.md |
| 119 | 리드가 주입한 잘못된 전제는 워커의 오류가 되어 돌아온다 — 브리핑은 지시가 아니라 검증 대상이다 (2026-07-16) | principle | multi-agent, briefing, 반박채널, fan-out, 계약 | knowledge/multi-agent-orchestration.md |
| 120 | Figma get_metadata는 depth 제한이 없다 — 얕은 열거는 use_figma로만 (2026-07-17) | principle | figma, get_metadata, token-cap, use_figma | knowledge/figma-design-system.md |
| 121 | CSS 블록 주석 속 리터럴 `*/`는 뒤따르는 규칙 전체를 조용히 삭제한다 (2026-07-17) | principle | css, comment, custom-property, silent-failure | knowledge/css-design.md |
| 122 | 병렬 에이전트 공유 tmp 고정 파일명 충돌 — job 스코프 mktemp 필수 (2026-07-17) | principle | multi-agent, tmp, mktemp, concurrency | knowledge/multi-agent-orchestration.md |
| 123 | 지식베이스 감사에서 row-presence는 콘텐츠 깊이를 은폐한다 (2026-07-17) | principle | knowledge-base, audit, coverage, content-depth | 인라인 |
| 124 | Korean 파일에서 Edit 툴 실패 — Python writelines 패턴 (2026-06-12, 구 인라인 #12) | principle | claude-code, edit-tool, korean, python-writelines | knowledge/claude-code-platform.md |
| 125 | Derived slice 재사용으로 다수 sparkline 데이터 생성 (2026-06-12, 구 인라인 #13) | principle | react, derived-slice, sparkline, dashboard | knowledge/react-frontend.md |
| 126 | HeroSparkline optional height prop — 컴포넌트 복제 없이 크기 변형 흡수 (2026-06-12, 구 인라인 #14) | tactical | react, optional-prop, variant | knowledge/react-frontend.md |
| 127 | git cat-file + branch --contains — 특정 커밋의 브랜치 추적 2-step 패턴 (2026-06-17, 구 인라인 #15) | tactical | git, cat-file, branch-contains, ff-only | knowledge/git-worktree.md |
| 128 | CSnCompany 공식 플러그인 헬스 게이트 — preflight(-3.5) 의존성 조기 차단 (2026-06-17, 구 인라인 #16) | tactical | preflight, official-plugins, dependency-gate, pre_pass | 인라인 |
| 129 | AI 서브에이전트의 성능/원인 진단은 가설이다 — 코드 반영 전 실측 재검증 (2026-07-17) | principle | agent-diagnosis, empirical-verification, time-measurement | knowledge/multi-agent-orchestration.md |
| 130 | 검증 중 실측된 신규 데이터가 유효한 결과물이면 테스트 데이터처럼 되돌리지 않는다 (2026-07-17) | tactical | verification, production-data, test-cleanup | knowledge/misc-tooling.md |
| 131 | 라이브 참조 없는 화면/유형은 발명하지 않고 스코프 제외 또는 reference-weak로 명시 플래그한다 (2026-07-17) | principle | figma, reference-gap, scope, anti-invention | knowledge/figma-design-system.md |
| 132 | Figma 빌드 완료 선언 전 라이브 사이트/템플릿 스크린샷 대조 게이트는 육안 검수로 못 잡는 버그를 반복적으로 잡아낸다 (2026-07-17) | tactical | figma, screenshot-gate, quality-gate, verification | knowledge/figma-design-system.md |
| 133 | dev 오케스트레이터 스크립트의 하드코딩 포트 + 무조건 kill이 "자기 자신의 워크트리 실행" 시나리오에서 메인 앱을 죽인다 (2026-07-17) | tactical | tauri, dev-server, port-env, self-referential | knowledge/tauri-windows.md |
| 134 | Workflow의 parallel adversarial review가 "cleanup 완전 비활성화"라는 스코프 오류를 잡아낸 사례 (2026-07-17) | principle | workflow-tool, adversarial-review, code-review, scope | knowledge/multi-agent-orchestration.md |
| 135 | 프로세스/포트 cwd 매칭에 느슨한 ancestor-path 비교를 쓰면 무관한 프로세스와 오탐 — 코드리뷰가 놓치고 Playwright 라이브 검증이 잡아낸 사례 (2026-07-17) | tactical | process-matching, false-positive, playwright, live-verification | knowledge/debugging.md |
| 136 | git worktree remove는 그 디렉터리를 cwd로 쓰는 실행 중 프로세스를 멈추지 않는다 — 삭제 전 명시적 stop 필요 (2026-07-17) | tactical | git-worktree, orphan-process, cwd, cleanup | knowledge/tauri-windows.md |
| 137 | 상태 정리/마이그레이션 수정은 실제 프로덕션 데이터에 합성 케이스를 주입해 전후 id-set diff로 검증하면 더 강한 확신을 준다 — 단, 격리 포트 + 왕복 클린업이 전제 (2026-07-17) | tactical | verification, production-data, isolated-testing, cleanup-protocol | knowledge/misc-tooling.md |
| 138 | EnterWorktree가 "Already in a worktree session"으로 막히면 디렉터리 존재를 의심하기 전에 ExitWorktree(remove)부터 시도한다 (2026-07-17) | principle | claude-code, enterworktree, exitworktree, session-recovery | knowledge/claude-code-platform.md |
| 139 | Workflow 스크립트의 agent 프롬프트 안에 리터럴 ${...}를 쓰면 sandbox가 즉시 평가해 "process is not defined"로 전체 런을 크래시시킨다 (2026-07-17) | principle | workflow-tool, template-literal, sandbox, scripting-pitfall | knowledge/claude-code-platform.md |
| 140 | 표시 이름과 권한 플래그가 분리된 인증 구조에서는 이름 충돌이 사일런트 권한 오판을 만든다 (2026-07-17) | principle | auth, display-name, permission, reserved-name, react | knowledge/react-frontend.md |
| 141 | 서브에이전트가 idle_notification만 반복하고 도구 호출이 전혀 없으면 데드락 신호로 보고 직접 실행으로 전환한다 (2026-07-17) | tactical | multi-agent, idle-loop, deadlock, delegation, escalation | knowledge/multi-agent-orchestration.md |

> 참고: #7-9, #12-71은 프로젝트-특화 학습으로 `knowledge/` 파일에 이관됨 (2026-06 재구조화).
> 과거 어긋났던 #8의 배치 순서도 이관 시 번호순으로 정렬 수정됨. 번호는 전역 유일하며 재사용하지 않는다.
> 2026-07-17 무결성 복구: INDEX 누락분 #95-99·#120-123 백필, 인라인 #12-16(2026-06 작성분)은 knowledge/ 이관 항목과의 번호 충돌로 #124-128 재부여, 프로젝트-특화 인라인 본문을 knowledge/로 오프로드. 이후 정합성은 `bash plugins/shared/run_prepass.sh index-check`가 커밋 게이트에서 기계 검증한다 (C1 INDEX 누락 / C2 위치 포인터 / C3·C4 번호 유일성 / C5 연속성 / C6 인라인 상한 15).

### 오케스트레이터 도메인 학습 (인라인: #1-6, #10-11, #114, #123, #128)

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

### 114. 지식 축적 스킬은 주제가 아니라 "읽기 경로(read path)"로 분할해야 학습이 쌓일수록 강해진다 (2026-07-16)
<!-- tier: principle -->

- **상황**: `csdesign/nds`(Figma 디자인시스템 가이드 학습 저장소)에 3개 파일(총 77페이지)을 학습시킨 뒤, BUILD 패스가 "가장 먼저 읽어라"고 지시받은 `LEADER.md` 자체를 물리적으로 읽지 못하는 상태에 도달했다.
- **발견**: `LEADER.md`가 ~36–45k 토큰까지 커져 단일 Read가 컨텍스트 캡을 초과했다 — 학습 파일이 하나 늘 때마다 단조 악화되는 구조였다(= 학습할수록 못 쓰게 되는 anti-scaling). 이를 `LEADER.md`(모드 전용) + 상시 로드 베이스(`CORE.md`/`COMMON.md`) + `INDEX.md`(노트당 1줄) + `LEDGER.md`(쟁점, 해결되며 축소) + `sources/*.md`(빌드 시 비로드)로 **읽는 목적별로** 재분할하자, N번째 학습 파일이 새 행을 추가하기보다 기존 행을 corroborate만 하게 되어 읽기 비용은 유계로 유지되면서 신뢰도만 올라갔다.
- **교훈**: 지식이 계속 쌓이는 스킬을 설계할 때 "이 항목을 **어떤 목적으로** 읽는가(빌드 vs 감사 vs 포렌식)"로 파일을 나눈다. 주제별 분류는 항목 수에 비례해 읽기 비용이 선형 증가하지만, 읽기 경로별 분류는 유계로 만든다. 단, 균일성을 위해 전 도메인에 일괄 적용하지 말고(작은 도메인 2개는 의도적으로 미분할 유지) **측정된 트리거**(~25k 토큰, 또는 레지스트리가 더 이상 스캔되지 않는 시점)를 문서에 남겨 조건 충족 시에만 적용한다.
- **근거**: 실측 — nds BUILD 읽기 비용 36,201 → 12,098 토큰, asset 20,742 → 1,859. (skeptic verifier CONFIRM — "아키텍처 수준 주장이며 캐시 지역성/점진적 공개와 같은 논리, 특정 수치나 캡이 바뀌어도 원칙은 생존". 함께 제출된 "토큰 캡 초과" 후보는 이 항목의 근거일 뿐 독립 원칙이 아니라는 이유로 REJECT되어 여기 병합됨.)

### 123. 지식베이스 감사에서 row-presence는 콘텐츠 깊이를 은폐한다 — row-count 커버리지만으로는 거짓 확신이 생긴다 (2026-07-17)
<!-- tier: principle -->

- **상황**: 지식베이스(DB)가 "충분히 채워졌는가"를 감사하며, 열거된 항목의 100%가 DB 행을 갖고 있다는 사실만으로 완성도를 1차 판단.
- **발견**: row가 존재한다고 표시된 페이지 중 하나를 열어보니, 그 페이지 자신의 gap-notes 필드에 **약 15~25%만 필사(transcribe)됐다고 명시적으로 기록**돼 있었다 — row-presence는 100%였지만 실제 콘텐츠 깊이는 매우 낮았다. 이는 추론이 아니라 해당 행 자신이 남긴 1차 기록이다.
- **교훈**: 지식베이스/DB 완성도를 감사할 때는 row-count 커버리지(있음/없음)뿐 아니라 **콘텐츠 깊이**(글자수, 필드 채움률, 혹은 각 행 자신의 gap-notes)를 별도 지표로 반드시 함께 확인한다. row-count만 보고 "N/N 완료"라 선언하는 것은 #116("커버리지 주장은 권위 있는 분모로만 인증")의 사촌 함정이다 — 분모는 맞아도 분자 안의 밀도가 거짓 확신을 만든다.
- **근거**: 특정 페이지 행의 `content_md` 자체 서술 — "a page marked as having a row was actually only ~15-25% transcribed". (skeptic verifier CONFIRMED — 1차 문서화된 사실이며 추정이 아님, 주장이 요구하는 정확한 현상을 직접 예시함.)

### 128. CSnCompany 공식 플러그인 헬스 게이트 — preflight(-3.5)에서 의존성 조기 차단 (2026-06-17)
<!-- tier: tactical -->
<!-- renumbered 2026-07-17: 구 인라인 #16 — knowledge/ 이관 항목 #16과 번호 충돌로 재부여 -->

- **상황**: cs-ceo, CS-test, CS-codebase-review가 serena/playwright/hookify 등 공식 플러그인에 의존하지만 런타임 진입 후에야 누락을 감지해 비용이 낭비되었음.
- **발견**: pre_pass.py에 `_find_official_plugin()` + `_find_mcp_server()` 헬퍼를 추가하고 ceo.md Phase -3.5에서 preflight 단계에 감지·차단. CS-test는 playwright 미설치 시 Install/Skip/Abort AskUserQuestion 제공. OFFICIAL-PLUGINS.md가 설치 명령어 단일 진실.
- **교훈**: 공식 플러그인 의존성은 멀티에이전트 워크플로우 진입 전 preflight 단계(-3.5)에서 차단하는 것이 비용 효율적. context7 패턴(누락 감지 → AskUserQuestion 설치 유도)을 공식 플러그인에 동일 적용.
- **근거**: `defd9c1 feat: serena 통합 + 공식 플러그인 자동설치 유도 시스템 추가` — ceo.md +56줄, pre_pass.py +64줄, OFFICIAL-PLUGINS.md 신규 (2026-06-17)
