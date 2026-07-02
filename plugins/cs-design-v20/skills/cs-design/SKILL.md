---
name: cs-design
user-invocable: true
description: |
  v2: Design review (5-agent) + Design generation (--gen, claude.ai/design quality).
  Review triggers: "/cs-design", "디자인 리뷰", "UI 감사", "design audit", "UX 분석".
  Generation triggers: "/cs-design --gen", "디자인 만들어줘", "UI 생성", "design generate",
  "make a design", "create UI", "디자인 생성".
  Generation produces ec-* namespaced CSS, oklch() colors, self-contained HTML or Next.js TSX.
version: 20.1.0
---

# CS-design v2 — 디자인 리뷰 + claude.ai/design급 생성

## 개요

**두 가지 모드**:

1. **리뷰 모드** (기본): `design-lead` 에이전트가 5개의 전문 분석 에이전트를 조율하여 UI/UX 종합 리뷰 리포트를 생성합니다.
2. **생성 모드** (`--gen`): `design-generator` 에이전트가 claude.ai/design과 동등한 품질의 디자인 아티팩트를 생성합니다. oklch() 색상, ec-* CSS 네임스페이스, 자립 HTML 또는 Next.js TSX 출력.

## 사용법

### 리뷰 모드 (기존)
```
/cs-design                              # 현재 디렉토리 전체 디자인 분석
/cs-design [path]                       # 특정 경로 분석
/cs-design --focus visual               # 시각 계층만 분석
/cs-design --focus interaction          # 인터랙션 품질만 분석
/cs-design --focus consistency          # 디자인 시스템 일관성만 분석
/cs-design --focus responsive           # 반응형/접근성만 분석
/cs-design --focus antipatterns         # 안티패턴 탐지만 실행
/cs-design --fix                        # 발견된 안티패턴 자동 수정
/cs-design --hitl=auto                  # 무인 실행 — direction-choice 체크포인트에서 묻지 않음
```

### 생성 모드 (v2 신규 — claude.ai/design 동등)
```
/cs-design --gen "brief"                # 자립형 HTML 프로토타입 생성
/cs-design --gen --dark "brief"         # 다크 모드 우선 생성
/cs-design --gen --next "brief"         # React TSX + globals.css 블록 출력
/cs-design --gen --palette-only "brief" # 색상/타이포 시스템만 출력
```

**생성 예시**:
```
/cs-design --gen "SaaS 분석 대시보드 — 스타트업 창업자용"
/cs-design --gen --dark "AI 스타트업 랜딩 페이지"
/cs-design --gen --next "회원가입 폼 컴포넌트"
```

## 5개 분석 관점

역할 상세·분석 항목·출력 스키마는 각 에이전트 카드(`agents/<name>.md`)가 **단일 소스**다
(plugins/shared/AGENT-CARD.md 표준 — 여기에 중복 기술하지 않는다).

| 관점 | 한 줄 | 카드 |
|------|------|------|
| **visual-hierarchy** | 폰트 스케일·색상 대비·공간 계층 감사 | agents/visual-hierarchy.md |
| **interaction-quality** | 8대 컴포넌트 상태, focus, loading, error | agents/interaction-quality.md |
| **design-system-consistency** | 토큰 일관성·재사용률·명명 규칙 | agents/design-system-consistency.md |
| **responsive-accessibility** | 모바일 우선, WCAG AA, 4pt 간격 | agents/responsive-accessibility.md |
| **anti-pattern-detector** | 24개 AI slop 지표 탐지 (+ --fix) | agents/anti-pattern-detector.md |

## 실행 프로토콜

### Step 1: 인자 파싱 및 모드 분기

```
GEN_MODE    = --gen 플래그 존재 여부
BRIEF       = --gen 뒤의 인용문 (생성 모드 전용)
OUTPUT_FMT  = --next → "next" | --palette-only → "palette" | 기본 → "html"
DARK_MODE   = --dark 플래그 존재 여부

DESIGN_PATH = 지정 경로 (미지정 시 현재 작업 디렉토리, 리뷰 모드 전용)
FOCUS       = --focus [aspect] (선택: visual/interaction/consistency/responsive/antipatterns)
FIX_MODE    = --fix (선택: 안티패턴 자동 수정 활성화)
OUTPUT_DIR  = "design-results"
HITL        = --hitl [auto|gate|always] (미지정 시 "gate"; --auto는 --hitl=auto 별칭 — plugins/shared/HITL-POLICY.md [1])
```

> **GEN_MODE = true 이면 → Step 2-GEN-0으로 분기. 리뷰 프로토콜(Step 2~4) 건너뜀.**

---

### Step 2-GEN-0: 생성 컨텍스트 게이트

GEN_MODE가 true일 때만 실행. (리뷰 모드 Step 2와 동일한 impeccable 원칙 — 생성도 컨텍스트 없이는 제네릭한 결과만 나옴)

1. `design-results/design-context.md`가 있으면 읽고 대상 사용자 / 핵심 작업 / 브랜드 톤을 재사용 — 다시 묻지 않는다.
2. 없으면 BRIEF에서 3가지 신호 확인: (a) 대상 사용자, (b) 사용자가 수행할 핵심 액션, (c) 브랜드 톤(형용사 ~3개).
   BRIEF에 **빠진** 신호만 AskUserQuestion 1회로 질문 (최대 1-3개 질문; BRIEF가 이미 답한 것은 건너뜀 —
   예: "SaaS 분석 대시보드 — 스타트업 창업자용"은 대상 사용자가 이미 명시됨).
   각 질문에 "잘 모름 — 알아서 추론" 선택지를 포함해 사용자가 추론에 위임할 수 있게 한다.
3. 답변을 design-generator Task 프롬프트의 `TARGET_USER` / `PRIMARY_ACTION` / `BRAND_WORDS` 필드로 주입
   (위임 시 "infer"). 선택적으로 `design-results/design-context.md`를 작성/갱신해 다음 실행 시 게이트를 건너뛴다.

---

### Step 2-GEN: 생성 모드 — design-generator 에이전트 스폰

GEN_MODE가 true일 때만 실행.

시작 안내를 출력한다 (형식 자유, 다음 필드 필수): Brief / 모드(다크 우선 vs 라이트) / 출력 형식 / 저장 위치(design-results/) / design-generator 스폰 예고.

```
Task(
  subagent_type: "general-purpose",
  name: "design-generator",
  model: "sonnet",
  prompt: "당신은 cs-design v2의 design-generator입니다.
agents/design-generator.md 프로토콜을 따라 아래 brief로 디자인을 생성하세요.

BRIEF: [BRIEF]
MODE: [DARK_MODE ? 'dark' : 'light']
OUTPUT_FORMAT: [OUTPUT_FMT]
OUTPUT_DIR: design-results
TARGET_USER: [Step 2-GEN-0 답변 또는 'infer']
PRIMARY_ACTION: [Step 2-GEN-0 답변 또는 'infer']
BRAND_WORDS: [Step 2-GEN-0 답변 또는 'infer']

반드시 references/generation-spec.md의 모든 규칙을 따르세요:
- oklch() 색상 필수 (hex/rgb 팔레트 금지)
- ec-* CSS 네임스페이스 필수
- Google Fonts에서 비-제네릭 폰트 선택 (Inter/Roboto/DM Sans 금지)
- 4pt 간격 그리드만 사용
- 모든 인터랙티브 요소에 8가지 컴포넌트 상태 구현
- 출력 전 anti-patterns.md 체크리스트 0건 위반 확인"
)
```

design-generator 완료 후 생성 결과 요약을 main context에 출력하고 종료.
**Step 3, 4는 실행하지 않는다.**

---

### Step 2: 디자인 컨텍스트 수집 (리뷰 모드, 중요!)

> **impeccable 원칙**: 코드베이스를 읽어도 "누가 사용하는지", "어떤 느낌이어야 하는지"는 알 수 없음.
> 디자인 리뷰는 컨텍스트 없이는 제네릭한 결과만 나옴.

`design-results/design-context.md` 파일이 있으면 읽고 진행.
없으면 다음 3가지 확인:
1. **대상 사용자**: 누가 이 제품을 사용하는가?
2. **핵심 작업**: 사용자가 주로 수행하는 작업은?
3. **브랜드 톤**: 인터페이스가 어떤 느낌이어야 하는가? (3단어로)

컨텍스트 없이도 진행 가능 (안티패턴 탐지는 컨텍스트 불필요).

### Step 3: 시작 안내 출력

시작 안내를 출력한다 (형식 자유, 다음 필드 필수): 분석 대상 경로 / 분석 범위(FOCUS 또는 "전체 5관점") / 수정 모드 활성 여부 / 결과 저장 경로 / 조율할 분석 에이전트 수.

### Step 4: design-lead 에이전트 스폰

```
Task(
  subagent_type: "general-purpose",
  name: "design-lead",
  model: "opus",
  prompt: "당신은 CS-design의 design-lead입니다. 아래 컨텍스트로 디자인 리뷰를 수행하세요.

DESIGN_PATH: [DESIGN_PATH]
FOCUS: [FOCUS 또는 "none"]
FIX_MODE: [true/false]
OUTPUT_DIR: [OUTPUT_DIR]
DESIGN_CONTEXT: [컨텍스트 내용 또는 "not provided"]
HITL: [HITL]

agents/design-lead.md 프로토콜을 따라 분석 에이전트 팀을 오케스트레이션하고 DESIGN-REVIEW.md를 생성하세요.
SKILL.md의 'CS-design v1 노하우' 섹션 중 분석에 적용 가능한 패턴(특히 5, 6, 12번)을 에이전트 프롬프트에 반영하세요."
)
```

design-lead가 5개 에이전트 조율, 결과 수집, DESIGN-REVIEW.md 합성을 모두 처리합니다.

### Step 4.5: 체크포인트 버블링 (plugins/shared/HITL-POLICY.md [3])

design-lead의 Task 결과가 `type: "CHECKPOINT"` JSON이면 (HITL=gate|always에서 direction-choice 발생 — visual-hierarchy가 방향 A/B/C를 제시한 경우):

1. AskUserQuestion 1회: payload의 `question` + `options`(방향 A/B/C, 각 label에 consequence 병기) + **"작업 취소" 옵션 필수**. "작업 취소" → `resume.artifacts`(생성된 분석 리포트 경로)를 알리고 종료.
2. design-lead를 **재스폰** — Step 4의 원래 프롬프트에 `CHECKPOINT_ANSWER: [선택 방향]` + `RESUME: [payload의 resume 블록 원문]`을 추가. 재스폰된 design-lead는 분석 에이전트를 다시 돌리지 않고 Step 5(DESIGN-REVIEW.md 생성)부터 진행한다.
3. **경계 (BOUNDED)**: 재스폰은 checkpoint_id당 최대 1회, 런당 체크포인트 총 3회 — 재스폰된 design-lead가 같은 checkpoint_id를 다시 반환하면 재스폰 없이 종료 사유(`checkpoint direction-choice re-raised after resume`)와 부분 산출물 경로를 보고한다.

CHECKPOINT가 아닌 정상 완료(방향 제시가 없었거나 HITL=auto)면 이 단계를 조용히 스킵한다.

## 에러 처리

- **design-lead 실패**: 에러 메시지와 함께 수동 실행 방법 안내
- **UI 파일 없음**: "CSS/JSX 파일을 찾을 수 없습니다. 경로를 확인해주세요."

---

## CS-design v1 노하우

### 1. 컨텍스트 없이 디자인 리뷰 불가 (impeccable 원칙, 2026-04-13)

- **상황**: 코드베이스를 읽고 즉시 디자인 평가를 시작하면 제네릭한 결과만 나옴.
- **발견**: impeccable의 핵심 원칙: "Code tells you what was built, not who it's for or what it should feel like." 대상 사용자, 작업 목적, 브랜드 톤 없이는 "모든 디자인이 나쁘다"고만 말하게 됨.
- **교훈**: design-context.md 파일 또는 AskUserQuestion으로 3가지 컨텍스트를 먼저 수집. 안티패턴 탐지(references/anti-patterns.md)는 컨텍스트 없이도 실행 가능.

### 2. 스킬 미로드 원인 — installed_plugins.json SHA 불일치 (2026-04-14)

- **상황**: cs-design 플러그인이 enabledPlugins에 활성화되어 있고 캐시 파일도 정상인데 CC가 스킬을 로드하지 않음.
- **발견**: CC는 `installed_plugins.json`의 `gitCommitSha`를 현재 marketplace HEAD와 대조해서 플러그인 유효성을 검증함. marketplace에서 `git pull`로 파일이 업데이트되어도 `installed_plugins.json`의 SHA가 갱신되지 않으면 불일치 발생 → 로드 거부. orphaned 캐시 디렉토리(`.orphaned_at` 파일 포함)도 동반 문제로 나타남.
- **교훈**: 플러그인 스킬 미로드 시 `installed_plugins.json`의 해당 항목 `gitCommitSha`를 `git rev-parse HEAD`로 확인 후 최신 SHA로 교체. orphaned 캐시 디렉토리 삭제 후 CC 재시작.

### 3. 멀티라인 텍스트 표시 — split+넘버링 패턴이 pre-line보다 유연 (2026-04-20)

- **상황**: 사용자가 textarea에 줄바꿈으로 항목을 입력했을 때 카드 UI에서 그대로 렌더링 필요.
- **발견**: `white-space: pre-line`은 줄바꿈만 보존하고 maxLines 제한이나 빈 줄 필터링이 불가능. `split('\n').filter(Boolean)` 후 인덱스 넘버링 방식이 더 유연하며, `maxLines`/`small` prop으로 컨텍스트(카드 요약 vs 히스토리 상세)별 재사용 가능.
- **교훈**: 사용자 입력 멀티라인 표시 시 `PlanLines` 같은 컴포넌트로 추출. 줄 분리 → 빈 줄 제거 → 번호 + 텍스트 렌더링 패턴을 디자인 시스템에 등록할 것.

### 4. next/og Edge Runtime 한글 깨짐 해결법 (2026-04-20)

- **상황**: scrum opengraph-image.tsx에서 한글 텍스트가 깨져 보임
- **발견**: fontFamily: "monospace" 지정 시 Edge Runtime에서 한글 미지원으로 글씨 깨짐. MAU/problems OG 이미지는 fontFamily 미지정으로 문제 없음.
- **교훈**: next/og Edge Runtime 한글 텍스트에 fontFamily 명시 금지(특히 monospace). 한글 필요 시 fetch()로 Noto Sans KR 로드 후 fonts 옵션 전달. MAU/problems 스타일 전체너비 레이아웃이 렌더링 안정적.

### 5. 디자인 방향 결정 시 3가지 변형 제시 패턴 (gstack design-shotgun 학습, 2026-04-20) ✅ 반영됨 (2026-06 부분: visual-hierarchy 3선택지 제시 → 2026-07 완전 구현: design-lead Step 4.8 direction-choice CHECKPOINT + SKILL Step 4.5 버블링으로 "사용자가 선택" 루프 폐합, plugins/shared/HITL-POLICY.md)

- **상황**: design-lead가 단일 방향 권장안만 제시하여 사용자가 비교 선택 기회가 없음
- **발견**: gstack `/design-shotgun`은 3가지 시각적 변형(현재 스타일 개선 / 대안 스타일 / 최소 개입)을 생성하고 사용자가 비교 선택하게 함. 승인 패턴 학습으로 이후 제안을 편향시킴.
- **교훈**: 새 디자인 방향 요청 시 visual-hierarchy 에이전트가 "방향 A/B/C" 3선택지를 명시. 선택 후 해당 방향으로 집중.

### 6. CSS vs JS 수정 리스크 버짓 분리 (gstack risk-budget 학습, 2026-04-20) ✅ 반영됨 (2026-06)

- **상황**: --fix 모드에서 CSS 변경과 JS 컴포넌트 변경을 동일 비중으로 처리해 불필요한 리스크 발생
- **발견**: gstack `/design-review`는 CSS-only 수정은 "free-pass"(무조건 실행), JSX/컴포넌트 변경은 20% 리스크 버짓 차감, 전체 30건 하드캡 적용.
- **교훈**: anti-pattern-detector가 수정 제안 시 [CSS] / [JSX] / [COMPONENT] 레이블 부착. --fix 모드에서 CSS 수정 먼저 일괄 적용 후 JSX는 사용자 확인 후 진행.

### 7. 좁은 영역 버튼 과다 시 2-row layout 패턴 (2026-04-21)

- **상황**: 워크트리 패널 행에 버튼 6개(실행/열기/폴더/커밋/푸시/머지/삭제)를 한 행에 배치 → 이름이 찌그러지거나 버튼이 잘림
- **발견**: flex-wrap으로 버튼을 넘기면 어느 워크트리의 버튼인지 구분 불가. 이름을 상단 행에, 버튼을 하단 행에 분리(2-row)하면 이름이 항상 보이고 버튼도 여유롭게 배치됨.
- **교훈**: 단일 행에 버튼이 4개 이상이고 라벨도 표시해야 하면 2-row layout 우선 검토. flex-wrap은 버튼 소속이 불명확해져 UX 저하.

### 8. design 토큰 적용 시 Tailwind 대신 inline style (2026-04-21)

- **상황**: V3 디자인 시스템 토큰(bg #15120f, panel #1c1916, accent #e8a557 등)을 Tailwind로 적용하려 했으나 정확한 hex 값 보장 안 됨
- **발견**: Tailwind arbitrary value([#15120f])는 purge/JIT 설정에 따라 누락될 수 있고, 팀 내 커스텀 토큰과 충돌 가능. inline style={{ background:'#15120f' }}는 항상 정확한 값 보장.
- **교훈**: 디자인 토큰 시스템 적용 시 CSS 변수 또는 inline style 사용. Tailwind arbitrary value는 one-off 레이아웃에만 허용.

### 9. 다중 코호트 라인차트 가독성 패턴 (2026-04-23)

- **상황**: 70개 코호트 주차를 단일 라인차트에 표시하면 색상 구분이 불가능하고 완성/미완성 데이터 혼재로 혼란.
- **발견**: (1) 연도별 색상 계열 분리(2026년 blue 계열, 2025년 slate 계열), (2) 명도 그라데이션으로 최신→과거 구분(`hsl(215, 75%, 20~75%)`), (3) d30 null인 미완성 코호트는 `strokeDasharray="4 2"` 점선 처리, (4) 연도 필터 토글로 표시량 제어.
- **교훈**: 다중 시계열 라인차트 설계 시 (1) 그룹별 색상 계열 분리, (2) 명도 그라데이션으로 시간 흐름 표현, (3) 데이터 미완성 시리즈는 점선 구분, (4) 필터 토글로 밀도 조절. 70개 이상 시리즈는 기본값을 최근 1년으로 제한.

### 10. 웹앱 osascript 다이얼로그 비노출 — Finder activate 선행 패턴 (2026-04-24)

- **상황**: choose folder / NSOpenPanel 등 macOS 네이티브 다이얼로그를 Bun API 서버에서 osascript로 실행 시 Chrome 등 다른 앱 뒤에 숨어 사용자에게 보이지 않음. 클릭해도 아무 반응 없는 것처럼 느껴짐.
- **발견**: osascript 프로세스는 포커스를 가져오지 않아 다이얼로그가 백그라운드에 생성됨. `tell application "Finder" to activate` + `delay 0.2`를 choose folder 앞에 실행하면 Finder가 전면으로 올라오며 다이얼로그도 함께 노출됨.
- **교훈**: macOS 네이티브 다이얼로그를 백그라운드 서버 프로세스에서 띄울 때는 항상 `tell application "Finder" to activate` 선행. 또한 다이얼로그 실패 시 "경로를 직접 입력하세요" 안내 토스트를 추가해 UX 단절 방지.

### 11. 메인/서브 영역 시각 분리 패턴 (2026-04-24)

- **상황**: 포트 관리 카드에서 메인 영역과 워크트리 패널이 시각적으로 구분되지 않아 UX 혼란 발생
- **발견**: 수평 구분선(`height:1px`) + 가운데 텍스트 레이블("main") + 서브 패널에 좌측 amber 보더(`borderLeft: 2px solid`)로 두 섹션을 명확히 분리. 중복 버튼은 실행 방식 차이(Terminal vs tmux)를 레이블에 직접 반영하면 혼동 제거.
- **교훈**: 카드 내 두 영역 분리는 heavy modal 없이 얇은 구분선 + 레이블로 충분. 동일 기능 버튼이 두 개 이상이면 반드시 수행 방식 차이를 레이블에 표시.

### 12. 모바일 모달 5개 잘림 패턴 — width:'calc(100vw-24px)' + flex-wrap + max-w-[calc(100vw-32px)] (2026-04-28)

- **상황**: Vercel portal이 iPhone 세로(375px)에서 5개 위치 잘림. ① modal `maxWidth:460/440` (343px 가용 초과) ② category pills `overflow-x-auto + scrollbar-none` (시각적으로 잘려보임, 사용자가 스크롤 가능 인지 못함) ③ device picker `absolute w-60` (절대 위치 우측 오버플로우) ④ 검색 행 `flexShrink:0` 요소가 wrap 깨뜨림 ⑤ 헤더 좌측 그룹 `min-w-0` 누락.
- **발견**: 5건 모두 **타깃 1줄 패치**로 해결 — ① `width: 'calc(100vw - 24px)', maxWidth:460` 동시 지정 (큰 화면 maxWidth, 작은 화면 100vw-여백) ② `overflow-x-auto scrollbar-none` → `flex-wrap` (1-2줄 차지하지만 잘림 0) ③ 절대 드롭다운에 `max-w-[calc(100vw-32px)]` 1개 클래스 ④ 검색 input `flex:'1 1 200px', minWidth:0`, device pill `maxWidth:140 + textOverflow:ellipsis` ⑤ 헤더 컨테이너 `min-w-0 flex-shrink`.
- **교훈**: 모바일 잘림 진단은 `scrollWidth>clientWidth` 1줄로 빠르게 잡고(test 도메인 #28), 수정은 ① 모달 width 패턴 ② 가로 스크롤 영역은 `flex-wrap` 또는 가시 스크롤바 둘 중 하나 (scrollbar-none 단독 금지) ③ 절대 위치 드롭다운은 항상 `max-w-[calc(100vw-Npx)]` ④ flex 행 내 모든 자식 `minWidth:0` + truncate. 이 4-패턴이 모바일 overflow의 90%.

### 13. Claude Design handoff → ec-* 네임스페이스로 Tailwind 공존 구현 (2026-05-01)

- **상황**: Claude Design(claude.ai/design)에서 내보낸 HTML/CSS 프로토타입을 실제 Next.js + Tailwind CSS 프로젝트에 적용할 때, 기존 Tailwind 코드를 건드리지 않고 디자인 시스템을 통합해야 했음.
- **발견**: 프로토타입이 `ec-*` 프리픽스로 모든 CSS 클래스를 네임스페이스화했기 때문에 Tailwind 클래스와 충돌이 없음. `globals.css` 끝에 디자인 CSS를 추가하면 별도 파일 없이 공존 가능. page.tsx의 쉘(레이아웃 구조)만 교체하면 기존 tab 컴포넌트 내부(FileUploader, Zustand store, API 호출 등)는 그대로 재사용됨. Claude Design bundle은 gzip tar로 내려오며 `chats/` 디렉토리의 대화 내역이 디자인 의도를 설명함 — 반드시 먼저 읽어야 함.
- **교훈**: Claude Design handoff 구현 순서: ① README.md 읽기 ② chats/ 대화 내역으로 의도 파악 ③ HTML/CSS/JSX 파일 읽기 ④ CSS를 globals.css 끝에 추가(ec-* 네임스페이스 확인) ⑤ page.tsx 쉘만 교체, 기존 컴포넌트 내부 재사용. oklch() 색상 함수는 Chrome/Safari 지원 — 구형 브라우저 대응 필요 시 fallback 추가.
