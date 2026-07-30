# cs-design-sample1 Design Guide

토큰 기반 "CS Archive" 디자인 시스템 — paper(기본) ↔ dark 듀얼 테마, 단일 파생 액센트로
전체 사이트를 재스킨하는 구조. Next.js(App Router) 모바일 스터디 앱에 최적화.
(원본: `/Users/gwanli/product_2026/designguide for cs`의 `tokens.css`+`system.css` —
기계학습과포트폴리오최적화 기말고사 스터디 앱 `final-study-web/`에 그대로 복사되어 적용됨)

> 한 문단 요약: 근흑색(또는 누런 종이) 위에 인쇄된 계기판. 넓은 자간의 대문자 모노스페이스가
> 기계 라벨처럼 동작하고, 무거운 세리프가 모든 헤드라인을 담당하며, 본문은 둘 중 어느 쪽과도
> 경쟁하지 않는 차분한 중간 회색에 앉는다. 표면은 8% 화이트 그라디언트 + 헤어라인으로만
> 구분되어 층이 아니라 새겨진 것처럼 읽힌다. 액센트는 하나, 모션은 느리고 항상 같은 방향
> (콘텐츠는 위로 떠오른다).

---

## 1. 색상 시스템 (Color System) — 토큰

**단일 소스**: `--cs-accent` 하나만 바꾸면 글로우·호버 섀도·하이라이트·LED·포커스가 전부
`color-mix(in oklab, var(--ac) N%, transparent)`로 파생되어 함께 움직인다. 두 번째 액센트
색상을 하드코딩하는 것이 시스템이 무너지는 가장 흔한 방식이다.

```css
--cs-accent: #67e8f9;         /* dark 테마 기본 — cyan */
--ac: var(--cs-accent);       /* color-mix() 안에서 쓰는 짧은 별칭 */
```

### 표면 (Surfaces) — dark (alt 테마)
| 토큰 | 값 |
|------|-----|
| `--cs-bg` | `#05070d` 근흑색, 옅은 블루 틴트 |
| `--cs-bg-raised` | `#0a0d14` |
| `--cs-bg-device` | `#12161f` |

### 표면 (Surfaces) — paper (기본 테마, `[data-theme="paper"]`)
긴 논술형 답안을 어두운 배경에서 읽기 힘들다는 요청으로 재스킨한 실제 적용 사례.
가이드의 "밝은 면은 종이에만"(원칙 9)을 의도적으로 뒤집되, 나머지 원칙은 그대로 지킨다 —
**토큰만 교체하고 컴포넌트 클래스는 건드리지 않는 것**이 이 시스템의 재스킨 방식.

```css
:root[data-theme="paper"] {
  --cs-accent: #146b74;        /* 딥 틸 — 크림 배경 위 대비 5.41:1 */
  --cs-bg: #f4efe3;            /* 누런 종이 */
  --cs-bg-raised: #fbf8f0;
  --cs-bg-device: #e9e2d2;
}
```
사이언(`#67e8f9`)은 크림 배경에서 대비 1.3:1로 사실상 안 보이므로, 재스킨 시 액센트도
반드시 함께 교체한다 — 파생 틴트가 전부 따라오도록.

### 텍스트 사다리 (Text Ladder) — 9단계, 용도로 고른다 (취향 아님)
| 토큰 | dark 값 | paper 값 | 용도 |
|------|---------|----------|------|
| `--cs-text` | `#e6eaf2` | `#2b2721` | 기본 본문 |
| `--cs-text-strong` | `#f1f5fb` | `#17140f` | `<strong>`, 강조 |
| `--cs-text-card` | `#d7dee9` | `#332e26` | 카드 타이틀, 리스트 타이틀 |
| `--cs-text-body` | `#aeb7c7` | `#464036` | 장문 문단 (본문은 흰색이 **아니다**) |
| `--cs-text-muted` | `#8b94a6` | `#5c5648` | 리드 문단, 보조 내비 |
| `--cs-text-label` | `#5b6577` | `#6f6757` | 모노 eyebrow, 메타, 비활성 탭 — 방향성 표시 전용, 읽기용 아님 |
| `--cs-text-ghost` | `#4a5364` | `#7d7565` | 티커 텍스트 |
| `--cs-text-faint` | `#414b5c` | `#857c6c` | 풋터 |
| `--cs-text-disabled` | `#39414f` | `#a89f8e` | 비활성 컨트롤 |

**규칙**: paper 테마의 사다리 아래쪽(label 이하)은 dark보다 한 단계씩 진하게 잡는다 — 크림
배경은 흰 배경보다 밝기가 낮아 같은 회색이 더 흐리게 보이기 때문. `label`(4.88:1)은 비활성
탭에도 쓰이므로 장식 기준이 아니라 AA 기준으로 잡아야 한다.

### 헤어라인 & 표면 채움
| 토큰 | dark 값 | paper 값 |
|------|---------|----------|
| `--cs-line` (기본 보더) | `rgba(255,255,255,.08)` | `rgba(74,58,30,.18)` (따뜻한 갈색) |
| `--cs-line-soft` (풋터 룰) | `rgba(255,255,255,.06)` | `rgba(74,58,30,.11)` |
| `--cs-line-strong` (고스트 버튼) | `rgba(255,255,255,.14)` | `rgba(74,58,30,.32)` |
| `--cs-line-grid` (배경 그리드) | `rgba(255,255,255,.028)` | `rgba(90,72,40,.055)` |
| `--cs-fill-card` | `linear-gradient(160deg, rgba(255,255,255,.035), rgba(255,255,255,.012))` | `linear-gradient(160deg, rgba(255,253,247,.95), rgba(255,253,247,.55))` |
| `--cs-ghost-num` (초대형 배경 숫자) | `rgba(235,240,250,.05)` | `rgba(74,58,30,.08)` |

**160° 그라디언트 각도는 테마와 무관하게 항상 고정** — 암시된 광원 방향이 카드마다 달라지면
안 되기 때문. paper 테마의 그림자는 훨씬 옅어야 한다 (검정 60% 그림자는 종이 위에서 얼룩처럼
보인다) — `--cs-shadow-panel`을 `rgba(74,58,30,.35)` 기준으로 재정의.

### 라이트 인셋 (Light Insets)
`--cs-paper` (`#f5f2ea`) / `--cs-paper-warm` (`#f7f5f0`) — dark 테마에서 **종이 그 자체인
콘텐츠**(다이어그램, 스캔, 만화 페이지)에만 쓰는 유일한 밝은 표면. 카드·모달·섹션에 쓰면 안
된다 — 레이아웃 속 밝은 패널은 버그처럼 읽힌다.

---

## 2. 테마 시스템 (Paper ↔ Dark 토글)

- 기본 테마는 **paper** (`data-theme="paper"`, 또는 속성 없음). `dark`는 `<html
  data-theme="dark">`로 전환.
- **FOUC 방지**: `<head>` 인라인 스크립트로 첫 페인트 전에 저장된 테마를 `<html>`에 칠한다
  (`layout.tsx`의 `NO_FLASH` 스크립트 참고) — 없으면 종이 테마 사용자가 로드마다 검은 화면을
  한 프레임 본다.
- 토글 버튼 클래스 `.themetoggle` — pill 보더, 현재 테마의 반대쪽 라벨("DARK"/"PAPER")을
  표시. 전환 시 `<meta name="theme-color">`도 함께 갱신 (`paper` → `#f4efe3`, `dark` →
  `#05070d`).
- 하드코딩된 흰색/검정 값(예: `a:hover`의 `#fff` 방향)은 토큰이 아니므로 자동으로 따라오지
  않는다 — `:root[data-theme="paper"] a:hover { color: color-mix(in oklab, var(--ac) 70%,
  #000); }`처럼 테마별로 되돌려야 한다. 글로우(`.cs-glow`)와 LED 섀도도 paper에서는 각각
  옅게/제거해야 한다 (밝은 배경 위 블룸은 얼룉처럼 보임).
- **재스킨 규칙**: 새 테마를 추가할 때 컴포넌트 클래스(`system.css`)는 절대 건드리지 않는다.
  `tokens.css`의 `:root[data-theme="..."]` 블록 안에서 토큰 값만 재정의한다.

---

## 3. 컴포넌트 패턴 (Component Patterns)

### 씬 래퍼 (모든 풀페이지 화면의 시작점)
```html
<div class="cs-scene">
  <div class="cs-grid-overlay"></div>
  <div class="cs-glow cs-glow--tl"></div>   <!-- 랜딩만: 드리프팅. 내부 페이지는 cs-glow--tr(고정, 더 옅음) -->
  <div class="cs-wrap"><!-- 또는 cs-wrap--read --></div>
</div>
```

### 헤더 (LED + 우측 테마 토글)
```html
<header class="cs-header cs-fade-up">
  <div style="display:flex;align-items:center;gap:12px">
    <span class="cs-led"></span>
    <span>ML × PORTFOLIO OPT</span>
  </div>
  <ThemeToggle />
</header>
```

### 히어로 — 라인 리빌
마스크 래퍼(`cs-reveal__line`)는 반드시 `overflow:hidden`, 안쪽 `<span>`이 애니메이션 대상.
래퍼당 한 줄만 — 마스크가 곧 효과.
```html
<p class="cs-eyebrow cs-eyebrow--accent cs-fade-up" style="--cs-d:.1s">기말시험 — 생각해볼 점</p>
<h1 class="cs-display">
  <span class="cs-reveal__line"><span style="--cs-d:.15s">추정오차와 상관구조가</span></span>
  <span class="cs-reveal__line"><span style="--cs-d:.28s"><em>최적화</em>를 무너뜨릴 때</span></span>
</h1>
<p class="cs-lede cs-fade-up" style="--cs-d:.5s">11문항을 두 판본과 짜집기 특강으로 합쳤습니다.</p>
```
`<em>`은 `.cs-display` 안에서 이탤릭 해제 + 액센트 컬러 — 헤드라인 한 단어 강조 방법.

### 스탯 로우
```html
<div class="cs-stats cs-fade-up" style="--cs-d:.62s">
  <div><div class="cs-stat__value">11</div><div class="cs-stat__label">QUESTIONS</div></div>
  <div><div class="cs-stat__value cs-stat__value--accent">74′</div><div class="cs-stat__label">LISTEN TIME</div></div>
</div>
```
숫자는 두 자리 zero-pad. 마지막 스탯만 액센트로 마침표처럼 강조 가능.

### 티커
트랙은 콘텐츠를 **반드시 두 번** 포함 — marquee 키프레임이 정확히 -50% 이동하므로 한 번만
넣으면 빈 구간이 보인다.
```html
<div class="cs-ticker cs-fade-up" style="--cs-d:.75s">
  <div class="cs-ticker__track"><span>키워드 · 키워드 ·&nbsp;</span><span>키워드 · 키워드 ·&nbsp;</span></div>
</div>
```

### 카드 그리드 + 고스트 넘버 (`cs-card` / `q-card`)
```html
<div class="cs-card-grid cs-stagger" style="--cs-d0:.85s">
  <a class="cs-card" href="/week/1">
    <div class="cs-ghost-num cs-card__num">01</div>
    <div class="cs-card__label">WEEK 01</div>
    <div class="cs-card__title">카드 제목</div>
    <div class="cs-card__meta"><span>■ 요약</span><span>▶ 쇼츠</span></div>
  </a>
</div>
```
제목 길이가 다양하면 `.cs-card__title`에 `min-height`를 줘 메타 행이 그리드 전체에서 같은
베이스라인에 오도록 한다. 스터디 앱 변형(`q-card`)은 문제 번호/유형 배지 + 축 라벨 + 재생
시간을 카드 메타에 추가한다.

### 섹션 헤딩 (accent tick)
```html
<div class="cs-section-head"><span class="cs-tick"></span><h2 class="cs-display cs-display--sub">제목</h2></div>
```

### 프로즈 (신뢰되지 않은/생성된 HTML 래퍼)
```html
<div class="cs-prose"><p>본문은 <strong>강조</strong>와 <mark>하이라이트</mark>를 지원합니다.</p></div>
```
마크다운/CMS 출력물을 감쌀 때 사용 — 내부 노드에 클래스를 달 필요 없이 `p/ul/ol/li/strong/mark`를 스타일링.

### 탭
```html
<div class="cs-tabs">
  <button class="cs-tab is-active" aria-selected="true"><span class="cs-tab__sub">DIGEST</span>요약</button>
  <button class="cs-tab"><span class="cs-tab__sub">ON AIR</span>쇼츠</button>
</div>
```
모노 서브라벨(영문, 대문자, 1~2단어)이 있어야 "계기판 스위치"처럼 읽힌다.

### 디바이스 프레임 (비디오/데모)
```html
<div class="cs-device">
  <div class="cs-device__screen">
    <video controls src="..."></video>
    <div class="cs-device__scanlines"></div>
    <div class="cs-device__sheen"></div>
  </div>
  <div class="cs-device__bar"><span>CHANNEL</span><span class="cs-led cs-led--live"></span><span>CH 01</span></div>
</div>
<div class="cs-device__stand"><div class="cs-device__neck"></div><div class="cs-device__foot"></div><div class="cs-device__pool"></div></div>
```

### 페이지 헤더 (대형 고스트 넘버)
```html
<div style="position:relative;padding:64px 0 8px">
  <div class="cs-ghost-num" style="top:-10px;right:-14px;font-size:230px">01</div>
  <p class="cs-eyebrow cs-eyebrow--accent">WEEK 01</p>
  <h1 class="cs-display cs-display--title" style="max-width:780px">제목</h1>
</div>
```

### 풋터
```html
<footer class="cs-footer"><span>PROJECT NAME</span><span>PART / PART / PART</span></footer>
```

### 스터디 앱 전용 확장 (app 레이어 — `globals.css`)
- **수식 (`.fx` 블록 / `.fi` 인라인)**: KaTeX 대신 유니코드로 조합한 모노 텍스트. `.fx--boxed`는
  문제의 핵심 결과값을 액센트 보더로 강조. 긴 수식은 자체 박스 안에서만 스크롤 — 페이지가
  가로로 스크롤되면 안 된다.
- **독(dock) 오디오 플레이어 (`.player`)**: 화면 하단 고정, `backdrop-filter: blur(18px)`,
  엄지로 누르기 쉬운 46px 재생 버튼, 3px 시크바에 ±11px 보이지 않는 히트 영역을 더해 실제
  터치 타깃 확보.
- **메모리 카드 (`.memory-card`)**: 암기 코드(세리프 900, 42px) + 의미 + 배경 우상단 대형
  워터마크(`V2` 등) — 고스트 넘버 패턴의 변형.
- **티어 선택 (`.tier-pick` / `.tier`)**: 3열 선택형 카드, 선택 시 액센트 보더+배경 틴트로
  전환.
- **체크리스트 (`.checklist`)**: 좌측 `✓`(또는 가산점 행은 `+`) 글리프, 액센트 색.
- **표 (`.cs-table` / `.tablewrap`)**: 360px에서 유일하게 리플로우 불가능한 요소 — 항상
  `.tablewrap`으로 감싸 가로 스크롤, 페이지 자체는 절대 가로 스크롤되지 않게.

---

## 4. 타이포그래피 (Typography) — 세 서체, 세 역할, 절대 교차 금지

| 서체 | 역할 | 절대 쓰지 말 것 |
|------|------|----------------|
| **Noto Serif KR, weight 900** | 헤딩, 숫자, 스탯 값 | 본문, 라벨 |
| **IBM Plex Sans KR** | 문단, 카드 타이틀, 탭, UI | 헤딩, eyebrow |
| **IBM Plex Mono** | eyebrow, 메타, 풋터, 티커, 상태 | 8단어 넘는 어떤 것도 |

```css
--cs-font-display: "Noto Serif KR", serif;
--cs-font-body: "IBM Plex Sans KR", sans-serif;
--cs-font-mono: "IBM Plex Mono", monospace;
```

### 모노는 항상 대문자 + 항상 넓은 자간
합법적 tracking 값은 이 넷뿐: `.3em`(히어로 eyebrow) · `.24em`(섹션 메타, 탭 서브라벨) ·
`.2em`(풋터, 티커) · `.14em`(밀도 높은 카드 메타). 모노를 좁게, 소문자로, 문장 안에 쓰는 것이
스타일을 깨는 가장 빠른 방법.

### 타입 스케일 토큰
| 토큰 | 값 | 용도 |
|------|-----|------|
| `--cs-size-hero` | `clamp(44px,7.2vw,86px)` (모바일: `clamp(30px,8.6vw,44px)`) | 랜딩 H1 |
| `--cs-size-title` | `clamp(28px,4.4vw,44px)` (모바일: `clamp(21px,6vw,28px)`) | 상세 페이지 H1 |
| `--cs-size-h2` / `--cs-size-h3` | `26px` / `23px` (모바일 `21px`/`18px`) | 섹션/서브 헤딩 |
| `--cs-size-lede` | `17px` | 히어로 설명 |
| `--cs-size-prose` | `16.5px` | 본문 |
| `--cs-size-card` | `15.5px` | 카드 타이틀 |
| `--cs-size-eyebrow` / `--cs-size-meta` | `11.5px` / `10.5px` | eyebrow / 메타 |

---

## 5. 간격 / 레이아웃 (Spacing & Layout)

너비는 **딱 두 가지**만 쓴다: `--cs-w-wide`(1160px, 인덱스/랜딩) / `--cs-w-read`(960px, 지속
읽기용 — 내부 prose는 780px로 추가 제한). 미디어는 `--cs-w-media`(820px).

| 항목 | 값 |
|------|-----|
| 섹션 리듬 | 아티클 섹션 간 64px, 풋터 앞 90px, 리드 아래 52px |
| 카드 그리드 | `repeat(auto-fill, minmax(310px,1fr))`, gap 14px |
| 반경 | 카드 16px · 패널 14px · 디바이스 22px · 스크린 11px · 필 999px |
| 모바일 패딩 | `--cs-pad-wide: 20px`(≥720px에서 32px), `--cs-pad-read: 20px`(≥720px에서 28px) |

---

## 6. 안티패턴 — 10 Laws 위반 여부로 감사

클래스를 재사용하는 것보다 이 10개 법칙을 지키는 것이 더 중요하다 — 클래스를 하나도 안 써도
법칙만 지키면 이 패밀리에 속한다.

1. ❌ 세 서체의 역할을 교차 — 헤딩에 sans, 본문에 serif, 라벨에 body 폰트 사용
2. ❌ 모노를 좁은 자간/소문자/문장형으로 사용 — 항상 위 4개 tracking 값 + 대문자만
3. ❌ 취향으로 텍스트 컬러 선택 — 9단계 사다리에서 **역할**로만 고른다 (본문은 흰색이 아니라 `--cs-text-body`)
4. ❌ 두 번째 액센트 색 하드코딩 — 모든 틴트는 `color-mix(in oklab, var(--ac) N%, transparent)`로만 파생
5. ❌ 카드/패널에 단색 배경 — 항상 `linear-gradient(160deg, ...)` + 1px 헤어라인, 160° 각도 고정
6. ❌ 고스트 넘버에 `pointer-events`/`user-select` 누락 — 항상 `none`
7. ❌ 진입 애니메이션을 옆에서 슬라이드/스케일/바운스로 — 오직 `fadeUp`(26px) / `lineUp`(마스크), 카드 0.06s·섹션 0.1s stagger
8. ❌ 화면에 LED 펄스 2개 이상 — 화면당 정확히 하나 (사이언 or 라이브 상태는 red)
9. ❌ 카드·모달·섹션에 라이트 표면 사용 — `--cs-paper`는 다이어그램/스캔/만화 페이지 전용
10. ❌ 정적 패널에 hover 애니메이션 부여, 또는 인터랙티브 요소에 hover 없음 — lift(`translateY(-6px)` + accent 보더 + accent 섀도, 0.35s)는 클릭 가능한 것에만
11. ❌ (테마 추가 시) 컴포넌트 클래스를 직접 수정 — 재스킨은 `tokens.css`의 토큰 재정의로만

---

## 7. 실제 적용 사례

### 적용된 프로젝트
- `/Users/gwanli/product_2026/designguide for cs/` — 캐노니컬 배포본 (`tokens.css`,
  `system.css`, `preview.html`, `PATTERNS.md`, `react/`)
- `기계학습과포트폴리오최적화/기말/final-study-web/` — 실사용처. `app/design/`에 토큰·시스템을
  수정 없이 복사, `app/globals.css`에서 모바일 우선 app 레이어(수식/표/플레이어/paper 테마)를
  추가. 기본 테마를 **paper**로 재정의(긴 논술 답안 가독성 요청), dark는 토글로 유지.
- 원본 디자인 언어의 최초 출처: AI 신용평가 강의 아카이브 (`class-delta-blond.vercel.app`,
  `cs-design-sample2` 참고 — 두 샘플은 같은 계보의 dark 변형/paper 재스킨 관계)

### 재스킨 예시
```css
:root { --cs-accent: #a3e635; }   /* lime으로 전체 사이트 재스킨 */
```
