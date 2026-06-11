---
description: "에러노트 관리자 — 상황/문제점/시도/원인/해결점 5-필드 구조로 에러를 기록하고, cs-end Phase 2.2에서 자동 연동. (/cs-error-notes)"
allowed-tools: Bash, Read, Write, Edit, Glob, Grep, AskUserQuestion
---

# /cs-error-notes — Error Note Manager

세션 중 발생한 에러·버그를 5-필드 구조로 저장하고, 패턴 분석과 cs-end 학습에 활용합니다.

**저장 위치**: `~/.claude/error-notes/`
**인덱스 파일**: `~/.claude/error-notes/INDEX.md`
**ID 형식**: `ERR-YYYY-MM-DD-NNN` (날짜별 자동 증가)

---

## 사용법

```
/cs-error-notes                           # 최근 10개 노트 목록
/cs-error-notes capture "[에러 제목]"     # 새 에러노트 캡처 (대화형)
/cs-error-notes list                      # 전체 목록
/cs-error-notes list --open               # 미해결 에러만
/cs-error-notes list --domain cs-ceo      # 도메인별 필터
/cs-error-notes search "[키워드]"         # 키워드 검색 (대화형)
/cs-error-notes recall "[에러 메시지/키워드]"  # 디버깅 전 기존 해결 노트 회상 (비대화형, 에이전트용)
/cs-error-notes view ERR-2026-05-20-001   # 특정 노트 상세 보기
/cs-error-notes resolve ERR-xxx           # 해결 완료 마킹
/cs-error-notes patterns                  # 반복 에러 패턴 분석
```

---

## 에러노트 포맷

각 에러노트는 `~/.claude/error-notes/ERR-YYYY-MM-DD-NNN.md`로 저장됩니다.

```markdown
---
id: ERR-YYYY-MM-DD-NNN
title: [에러 제목]
date: YYYY-MM-DD
status: open|resolved
severity: critical|major|minor
domain: [cs-ceo|cs-end|cs-test|cs-plan|cs-design|cs-codebase-review|general]
project: [프로젝트명 또는 "-"]
tags: []
---

## 상황 (Context)
[어떤 작업 중에 발생했는지 — 작업 목표, 환경, 진행 상황]

## 문제점 (Problem)
[구체적인 오류 내용, 에러 메시지, 스택트레이스]

## 시도한 해결책들 (Attempts)
- 시도 1: [내용] → [결과]
- 시도 2: [내용] → [결과]

## 원인 (Root Cause)
[근본 원인 분석]

## 해결점 (Solution)
[실제 해결 방법 + 핵심 코드/명령어]

## 관련 학습
[→ cs-experiencing #N: 제목 (있는 경우)]
```

---

## 인덱스 포맷

`~/.claude/error-notes/INDEX.md` — 모든 노트의 한 줄 요약:

```markdown
# Error Notes Index

| ID | 날짜 | 제목 | 도메인 | 심각도 | 상태 |
|----|------|------|--------|--------|------|
| ERR-2026-05-20-001 | 2026-05-20 | [제목] | cs-ceo | major | resolved |
```

---

## 실행 프로토콜

### `/cs-error-notes` (인수 없음)

초기화:
```bash
ERROR_NOTES_DIR="$HOME/.claude/error-notes"
INDEX="$ERROR_NOTES_DIR/INDEX.md"
mkdir -p "$ERROR_NOTES_DIR"
```

INDEX.md가 없으면 헤더만 있는 빈 인덱스를 생성합니다.
INDEX.md를 읽어 최근 10개 노트를 출력합니다:

```
📋 Error Notes (최근 10개)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

 🔴 ERR-2026-05-20-001  [open]     major  cs-ceo
    "cs-ceo Phase -3 외부지식 게이트 silent fail"

 ✅ ERR-2026-05-19-001  [resolved] minor  cs-end
    "cs-end DOMAINS_USED 탐지 누락"

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
총 [N]개 | open: [M]개 | resolved: [K]개
```

---

### `/cs-error-notes capture "[에러 제목]"`

새 에러노트를 대화형으로 캡처합니다.

#### Step 1 — ID 생성

```bash
ERROR_NOTES_DIR="$HOME/.claude/error-notes"
TODAY=$(date +%Y-%m-%d)
LAST_NUM=$(ls "$ERROR_NOTES_DIR"/ERR-${TODAY}-*.md 2>/dev/null \
  | grep -oE '[0-9]+\.md$' | grep -oE '[0-9]+' | sort -n | tail -1)
NEXT_NUM=$(printf "%03d" $((${LAST_NUM:-0} + 1)))
NOTE_ID="ERR-${TODAY}-${NEXT_NUM}"
```

#### Step 2 — 심각도 선택

```
AskUserQuestion(
  question: "심각도를 선택하세요 (${NOTE_ID})",
  options: [
    "critical — 작업 완전 차단",
    "major — 주요 기능 저해, 우회 가능",
    "minor — 불편하지만 진행 가능"
  ]
)
```

#### Step 3 — 도메인 선택

```
AskUserQuestion(
  question: "어느 도메인에서 발생했나요?",
  options: [
    "cs-ceo / cs-end / cs-experiencing",
    "cs-test / cs-plan / cs-design",
    "cs-codebase-review / cs-ship",
    "general (플러그인 외 프로젝트)"
  ]
)
```

#### Step 4 — 5-필드 초안 자동 작성 (증거 규칙)

현재 세션 컨텍스트와 "[에러 제목]" 인수를 참고해 5개 필드 초안을 작성합니다.
단, 모델이 기억으로 재구성한 내용이 아니라 **세션에 남은 증거**가 근거여야 합니다:

1. **문제점 (Problem)** — 세션 트랜스크립트에 실제로 남은 에러 텍스트(도구 출력, exit code, 스택트레이스)를
   **verbatim 그대로** fenced code block 안에 복사하고, 그 에러를 발생시킨 정확한 명령/액션을 함께 기록한다.
   컨텍스트에 verbatim 출력이 없으면 사용자에게 붙여넣어 달라고 요청한다 (요약·재작성 금지).
2. **원인 (Root Cause)** — 반드시 `확인됨`(이 세션의 증거로 확인) 또는 `가설` 라벨을 붙인다.
   `가설`인 경우 "무엇을 확인하면 검증되는지"를 한 줄 명시한다.
3. **해결점 (Solution)** — 검증 증거(실패했던 명령의 재실행 + 통과 출력)를 포함한다.
   검증하지 못했으면 `검증 안 됨`으로 명시하고, 이 경우 status는 `open`으로 유지한다.

확인 단계:

```
AskUserQuestion(
  question: "아래 초안을 확인해주세요.",
  options: [
    "확인 — 저장",
    "시도한 해결책 추가 필요",
    "원인/해결점 보완 필요"
  ]
)
```

#### Step 5 — 저장

노트 파일을 Write 도구로 저장하고 INDEX.md 마지막 행에 추가합니다.

```
✅ 에러노트 저장: ${NOTE_ID}
   → ~/.claude/error-notes/${NOTE_ID}.md
```

---

### `/cs-error-notes list [--open] [--resolved] [--domain X]`

INDEX.md를 읽어 필터 적용 후 테이블로 출력합니다.
INDEX.md가 없으면 "에러노트 없음" 안내 후 종료합니다.

---

### `/cs-error-notes search "[키워드]"`

```bash
ERROR_NOTES_DIR="$HOME/.claude/error-notes"
# 인덱스에서 빠른 검색
grep -i "[키워드]" "$ERROR_NOTES_DIR/INDEX.md"
# 본문 상세 검색
grep -rl "[키워드]" "$ERROR_NOTES_DIR"/*.md 2>/dev/null | head -10
```

제목 히트 → 원인 히트 → 본문 히트 순으로 관련성 정렬 출력합니다.

---

### `/cs-error-notes recall "[에러 메시지 또는 키워드]"`

**용도**: 새 에러를 디버깅하기 전, 같은 에러를 이미 해결한 적이 있는지 확인하는 **비대화형** 회상.
`search`와 달리 다른 에이전트/스킬이 디버깅 도중 자동 호출하는 것을 전제로 설계되었습니다.
(plugins/CLAUDE.md의 "에러 회상" 규칙이 이 서브커맨드를 가리킵니다.)

프로토콜:

1. **토큰 추출**: 에러 메시지에서 변별력 있는 토큰 2-4개를 추출 — 식별자, 에러 코드, 라이브러리/함수 이름.
   타임스탬프, 절대 경로, 줄번호 등 세션마다 달라지는 부분은 제거한다.
2. **매칭**: 각 토큰을 `grep -i`로 `~/.claude/error-notes/INDEX.md`와 노트 본문(`*.md`)에 대조한다.
   ```bash
   ERROR_NOTES_DIR="$HOME/.claude/error-notes"
   grep -i "[토큰]" "$ERROR_NOTES_DIR/INDEX.md"
   grep -ril "[토큰]" "$ERROR_NOTES_DIR"/ERR-*.md 2>/dev/null
   ```
3. **랭킹**: `status: resolved` 노트 우선, 토큰 매칭 수가 많은 순.
4. **출력**: 상위 **최대 3건**만, 각 한 줄 — `ID | 제목 | 해결점 한 줄 요약(상황/원인 포함 가능)`.
   매칭 노트가 있으면 새로 디버깅하기 전에 해당 노트의 상황/원인/해결점을 먼저 제시한다.
5. **히트 없음**: 아무것도 출력하지 않고 그대로 진행한다. **recall은 절대 디버깅을 블로킹하지 않는다**
   (질문 금지, 에러 시에도 조용히 통과).

---

### `/cs-error-notes view ERR-xxx`

해당 노트 파일을 Read로 읽어 포맷된 형태로 출력합니다.

---

### `/cs-error-notes resolve ERR-xxx`

```bash
NOTE_FILE="$HOME/.claude/error-notes/ERR-xxx.md"
```

status를 바꾸기 전에 검증 근거를 1회 확인합니다:

```
AskUserQuestion(
  question: "어떤 확인으로 해결을 검증했나요? (한 줄 근거)",
  options: [
    "재실행 통과 — 근거를 입력/붙여넣기",
    "다른 방식으로 확인 — 근거를 입력",
    "검증 없이 마킹 — 미검증 상태로 기록"
  ]
)
```

- 근거가 제공되면 노트의 `해결점 (Solution)` 섹션 끝에 `검증: [근거 한 줄]`로 append.
- "검증 없이 마킹" 선택 시에도 resolve는 진행하되, `해결점`에 `검증: 검증 없이 마킹됨 (YYYY-MM-DD)`을 append해
  미검증 상태를 노트에 남깁니다 (크로스 세션 resolve 허용).

이후 Edit 도구로 frontmatter `status: open` → `status: resolved` 변경.
INDEX.md 해당 행도 동일하게 갱신합니다.

```
✅ ERR-xxx 해결 완료로 마킹됨
```

---

### `/cs-error-notes patterns`

반복 에러 패턴을 분석해 요약 리포트를 생성합니다.

분석 기준:
1. **도메인별 빈도** — 어느 도메인에서 가장 많이 발생하는가
2. **반복 태그** — 자주 등장하는 키워드
3. **미해결 노트** — open 상태로 오래된 항목
4. **해결 패턴** — 같은 root cause 계열

```
📊 Error Patterns 분석 (총 [N]개 노트)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

 도메인별:  cs-ceo (3)  cs-end (2)  general (1)
 자주 등장: PATH (2)  serde (2)  css-specificity (1)
 미해결:    [N]개 open

 반복 패턴 감지:
 ⚠️  PATH 관련 에러 2건 — ERR-xxx, ERR-yyy
     → cs-experiencing #17 "GUI 앱 PATH Desert" 참고

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

---

## cs-end Phase 2.2 연동

`/cs-end` 실행 시 **Phase 2.2**가 에러→해결 시퀀스를 감지해 에러노트 저장을 제안합니다.
자세한 프로토콜은 `cs-end-v3/commands/cs-end.md`의 Phase 2.2 참조.

---

## cs-experiencing 연결

에러노트 저장 시 `관련 학습` 필드에 cs-experiencing 노하우 번호를 연결합니다.
cs-end Learning Gate PASS 항목이 에러 해결에서 나온 경우, 해당 노하우에 error-ref 태그를 추가합니다:

```markdown
### [N]. [학습 제목] ([YYYY-MM-DD])
<!-- tier: principle -->
<!-- error-ref: ERR-2026-05-20-001 -->
- **상황**: ...
- **발견**: ...
- **교훈**: ...
```
