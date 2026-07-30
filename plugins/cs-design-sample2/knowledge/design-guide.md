# cs-design-sample2 Design Guide

다크 에디토리얼 × 터미널 무드의 강의 아카이브 랜딩 디자인 시스템.
Tailwind CSS v4 + Next.js(App Router) 기반 콘텐츠형 다크 사이트에 최적화.
(원본: 신용평가모델 강의 아카이브 홈페이지 — `class/` Next.js 프로젝트)

---

## 1. 색상 시스템 (Color System)

### 배경 (Background)
```css
/* globals.css :root */
--background: #05070d;   /* near-black navy, 순수 #000 아님 */
--foreground: #e6eaf2;
--ac: #67e8f9;            /* primary accent — cyan */
```
```tsx
// inline style 사용 프로젝트이므로 style={{ background: "#05070d" }} 형태
```

### 주요 액센트 (Primary Accent) — Cyan
| 용도 | 값 |
|------|-----|
| 링크, 라벨 강조, 진행 표시 | `var(--ac, #67E8F9)` |
| 링크 hover | `#A5F3FC` |
| 헤딩 내 강조 단어 (`<em>`) | `var(--ac, #67E8F9)` |
| LED pulse 점 (라이브 인디케이터) | `background: var(--ac,#67E8F9)` + `ledPulse` 애니메이션 |
| 드리프팅 글로우 오브 | `radial-gradient(circle, color-mix(in oklab, var(--ac,#67E8F9) 10~14%, transparent), transparent 65%)` |
| 카드 hover 보더/섀도 | `color-mix(in oklab, var(--ac,#67E8F9) 45%, transparent)` |
| 탭 활성 밑줄 | `2px solid var(--ac,#67E8F9)` |
| 섹션 제목 좌측 바 | `background: var(--ac,#67E8F9)` |
| mark 하이라이트 | `color-mix(in oklab, var(--ac,#67E8F9) 16%, transparent)` 배경 |

### 텍스트 계층 (Text Hierarchy) — 밝기 내림차순
| 역할 | 값 |
|------|-----|
| 최상위 헤딩/화이트 텍스트 | `#FFFFFF` / `#e6eaf2` (foreground) |
| 카드 타이틀 | `#D7DEE9` |
| 본문 서브텍스트 | `#AEB7C7` (sec-body 텍스트) |
| 히어로 설명 문단 | `#8B94A6` |
| 라벨/모노 캡션 | `#5B6577` |
| 티커/마퀴 텍스트 | `#4A5364` |
| 최저 명도 (풋터) | `#414B5C` |
| 비활성 상태 (webtoon nav 비활성) | `#39414F` |

### 보더 & 서페이스 (White-opacity system)
| 용도 | 값 |
|------|-----|
| 카드 보더 | `1px solid rgba(255,255,255,.08)` |
| 카드 배경 그라디언트 | `linear-gradient(160deg, rgba(255,255,255,.035), rgba(255,255,255,.012))` |
| 얇은 구분선 (헤더/풋터/티커) | `1px solid rgba(255,255,255,.06~.09)` |
| 고스트 필 버튼 보더 | `1px solid rgba(255,255,255,.14)`, hover 시 accent 컬러 |
| 그리드 오버레이 라인 | `rgba(255,255,255,.028)` |
| 대형 넘버 워터마크 | `rgba(235,240,250,.045~.05)` |

### 기능성 색상 (유지)
| 용도 | 값 |
|------|-----|
| LIVE/ON AIR 점 | `#F87171` (red) + `ledPulse` |
| 웹툰 뷰어 페이지 배경 (라이트 파트) | `#F7F5F0`, 섹션 다이어그램 박스 `#F5F2EA` — 다크 사이트 안의 유일한 라이트 서페이스, 인쇄물/종이 질감 표현용으로만 사용 |
| 쇼츠 TV 프레임 | `linear-gradient(175deg, #12161F, #0A0D14)` |

---

## 2. 컴포넌트 패턴 (Component Patterns)

### 그리드 오버레이 + 드리프팅 글로우 (배경 장식)
```tsx
<div style={{
  position: "absolute", inset: 0,
  backgroundImage: "linear-gradient(rgba(255,255,255,.028) 1px,transparent 1px),linear-gradient(90deg,rgba(255,255,255,.028) 1px,transparent 1px)",
  backgroundSize: "72px 72px",
  maskImage: "radial-gradient(ellipse 90% 70% at 50% 0%,#000 40%,transparent 100%)",
  pointerEvents: "none",
}} />
<div style={{
  position: "absolute", width: 640, height: 640, borderRadius: "50%",
  background: "radial-gradient(circle,color-mix(in oklab,var(--ac,#67E8F9) 14%,transparent),transparent 65%)",
  animation: "glowDrift 9s ease-in-out infinite",
}} />
```

### 헤더 (LED 라이브 인디케이터)
```tsx
<div style={{ display: "flex", alignItems: "center", gap: 12 }}>
  <span style={{
    width: 8, height: 8, borderRadius: "50%",
    background: "var(--ac,#67E8F9)", animation: "ledPulse 2.4s infinite",
  }} />
  <span>LABEL</span>
</div>
```

### 히어로 헤드라인 (라인 단위 슬라이드업)
```tsx
<h1 style={{ fontFamily: SERIF, fontWeight: 900, fontSize: "clamp(44px,7.2vw,86px)", lineHeight: 1.14 }}>
  <span style={{ display: "block", overflow: "hidden" }}>
    <span style={{ display: "block", animation: "lineUp .9s cubic-bezier(.2,.75,.2,1) .15s both" }}>
      첫 줄
    </span>
  </span>
</h1>
```

### 키워드 마퀴/티커
```tsx
<div style={{ overflow: "hidden", borderTop: "1px solid rgba(255,255,255,.07)", borderBottom: "1px solid rgba(255,255,255,.07)" }}>
  <div style={{ display: "flex", width: "max-content", animation: "marquee 38s linear infinite", fontFamily: MONO }}>
    <span>{TICKER}</span><span>{TICKER}</span>
  </div>
</div>
```

### 카드 (week-card)
```tsx
<Link className="week-card" style={{
  border: "1px solid rgba(255,255,255,.08)",
  borderRadius: 16,
  background: "linear-gradient(160deg,rgba(255,255,255,.035),rgba(255,255,255,.012))",
  padding: "26px 24px 22px",
}}>
  {/* 우상단 대형 번호 워터마크 */}
  <div style={{ position: "absolute", top: -24, right: 2, fontFamily: SERIF, fontWeight: 900, fontSize: 110, color: "rgba(235,240,250,.05)" }}>
    {num}
  </div>
  {/* mono 라벨 (accent) */}
  <div style={{ fontFamily: MONO, fontSize: 11, letterSpacing: ".26em", color: "var(--ac,#67E8F9)" }}>WEEK {num}</div>
  {/* 타이틀 */}
  <div style={{ fontWeight: 500, fontSize: 15.5, color: "#D7DEE9" }}>{title}</div>
</Link>
```
```css
/* globals.css — hover 물리감 */
.week-card { transition: transform .35s cubic-bezier(.2,.75,.3,1), border-color .35s, box-shadow .35s; }
.week-card:hover {
  transform: translateY(-6px);
  border-color: color-mix(in oklab, var(--ac,#67E8F9) 45%, transparent);
  box-shadow: 0 30px 70px -28px color-mix(in oklab, var(--ac,#67E8F9) 25%, transparent);
}
```

### 고스트 필 버튼 (뒤로가기 등)
```tsx
<Link className="ghost-pill" style={{
  background: "none", border: "1px solid rgba(255,255,255,.14)", borderRadius: 999,
  color: "#AEB7C7", fontSize: 13, padding: "9px 18px",
}}>
  ← 전체 커리큘럼
</Link>
```
```css
.ghost-pill { transition: border-color .3s, color .3s; }
.ghost-pill:hover { border-color: var(--ac,#67E8F9); color: #fff; }
```

### 탭 (밑줄 인디케이터 + mono 서브라벨)
```tsx
<button style={{
  background: "none", border: "none", padding: "10px 22px 16px",
  fontSize: 16, fontWeight: 700, color: active ? "#FFFFFF" : "#5B6577",
  borderBottom: active ? "2px solid var(--ac,#67E8F9)" : "2px solid transparent",
}}>
  <span style={{ fontFamily: MONO, fontSize: 10, letterSpacing: ".24em", display: "block", opacity: .65 }}>SUB</span>
  라벨
</button>
```

### 섹션 헤딩 (좌측 accent 바)
```tsx
<div style={{ display: "flex", alignItems: "baseline", gap: 16 }}>
  <span style={{ width: 26, height: 3, background: "var(--ac,#67E8F9)", borderRadius: 2 }} />
  <h2 style={{ fontFamily: SERIF, fontWeight: 900, fontSize: 23 }}>{title}</h2>
</div>
```

### 오디오 브리핑 바
```tsx
<div style={{
  display: "flex", alignItems: "center", gap: 18,
  border: "1px solid rgba(255,255,255,.09)", borderRadius: 14,
  background: "linear-gradient(160deg,rgba(255,255,255,.04),rgba(255,255,255,.01))",
  padding: "16px 20px",
}}>
  <div style={{ fontFamily: MONO, fontSize: 10.5, letterSpacing: ".22em", color: "var(--ac,#67E8F9)" }}>AUDIO<br/>BRIEFING</div>
  <audio controls src={audio} preload="none" />
</div>
```

### 다이어그램 박스 (라이트 서페이스, 다크 페이지 내 유일 예외)
```tsx
<div style={{
  background: "#F5F2EA", borderRadius: 14, padding: "30px 26px", textAlign: "center",
  boxShadow: "0 24px 60px -30px rgba(0,0,0,.6)",
}} dangerouslySetInnerHTML={{ __html: svg }} />
```

### 쇼츠 "TV" 목업 (video + CRT 오버레이)
```tsx
<div style={{
  background: "linear-gradient(175deg,#12161F,#0A0D14)",
  border: "1px solid rgba(255,255,255,.1)", borderRadius: 22,
  boxShadow: "0 50px 130px -35px rgba(0,0,0,.9),inset 0 1px 0 rgba(255,255,255,.06)",
}}>
  <div style={{ position: "relative", borderRadius: 11, overflow: "hidden", background: "#000", aspectRatio: "16/9" }}>
    <video style={{ position: "absolute", inset: 0, width: "100%", height: "100%", objectFit: "contain" }} />
    {/* CRT scanline */}
    <div style={{ position: "absolute", inset: 0, pointerEvents: "none",
      background: "repeating-linear-gradient(rgba(255,255,255,.028) 0 1px,transparent 1px 3px)", opacity: .7 }} />
  </div>
  {/* 하단 채널 바: FINTECH·GRAD TV / ● ON AIR / CH {num} · SHORTS */}
</div>
```

### 웹툰 플립북 (3D 페이지 넘김)
```tsx
<div style={{ perspective: 2600 }}>
  <div style={{ position: "relative", filter: "drop-shadow(0 60px 60px rgba(0,0,0,.55))" }}>
    {/* 좌/우 정적 페이지 pageStyle(), 넘어가는 페이지 faceStyle() + rotateY 3D transform */}
  </div>
</div>
{/* nav: 원형 버튼(44px, rgba(255,255,255,.28) 보더) + "01 / 03" mono 카운터 */}
```

### 이전/다음 네비게이션 (링크형)
```tsx
<Link className="week-nav-link" style={{ color: "#8B94A6", fontSize: 14 }}>← {prev.label}</Link>
```
```css
.week-nav-link { transition: color .3s; }
.week-nav-link:hover { color: var(--ac,#67E8F9); }
```

### 애니메이션 진입 (스태거)
```tsx
style={{ animation: "fadeUp .7s both", animationDelay: `${0.85 + i * 0.06}s` }}
```
```css
@keyframes fadeUp { from { opacity:0; transform: translateY(26px); } to { opacity:1; transform: translateY(0); } }
```

---

## 3. 타이포그래피 (Typography)

3-폰트 시스템 (Next.js `next/font/google`, CSS 변수로 주입):
- `IBM_Plex_Mono` → `--font-mono-plex` (라벨/캡션/모노 데이터)
- `IBM_Plex_Sans_KR` → `--font-sans-kr` (본문/탭/UI 텍스트)
- `Noto_Serif_KR` weight 600/900 → `--font-serif-kr` (헤딩/큰 숫자, 항상 900 사용)

```tsx
const MONO = "var(--font-mono-plex), monospace";
const SERIF = "var(--font-serif-kr), serif";
```

| 역할 | 스펙 |
|------|------|
| 히어로 H1 | `SERIF`, `font-weight:900`, `clamp(44px,7.2vw,86px)`, `line-height:1.14`, `letter-spacing:-.01em` |
| 상세 페이지 H1 | `SERIF`, `900`, `clamp(28px,4.4vw,44px)`, `line-height:1.32` |
| 섹션 H2 | `SERIF`, `900`, `23~26px` |
| 오버라인/eyebrow 라벨 | `MONO`, `12~12.5px`, `letter-spacing:.3em`, 색상 accent |
| 카드/헤더 mono 캡션 | `MONO`, `10.5~11.5px`, `letter-spacing:.22em~.26em`, 색상 `#5B6577` |
| 탭 서브라벨 | `MONO`, `10px`, `letter-spacing:.24em`, `opacity:.65` |
| 대형 스탯 숫자 | `SERIF`, `900`, `34px`, `tabular-nums` 아님(디자인상 미사용, 필요시 추가) |
| 본문 히어로 설명 | `sans`, `17px`, `line-height:1.8`, 색상 `#8B94A6` |
| sec-body 본문 (요약) | `16.5px`, `line-height:1.9`, 색상 `#AEB7C7` |
| 풋터/카피라이트 | `MONO`, `10.5px`, `letter-spacing:.2em`, 색상 `#414B5C` |

**규칙**: 모든 mono 텍스트는 넓은 `letter-spacing`(.14em~.3em)과 함께 사용하고, 통상 대문자/영문 라벨에만 적용한다. Serif는 항상 `font-weight:900`(볼드 헤딩 전용), 500~700 굵기의 serif 사용은 지양.

---

## 4. 간격 / 레이아웃 (Spacing & Layout)

| 항목 | 값 |
|------|-----|
| 랜딩 최대 너비 | `max-width: 1160px; margin: 0 auto; padding: 0 32px;` |
| 상세 페이지 최대 너비 | `max-width: 960px; padding: 0 28px 90px;` |
| 히어로 섹션 패딩 | `88px 0 56px` |
| 카드 그리드 | `grid-template-columns: repeat(auto-fill, minmax(310px, 1fr)); gap: 14px;` |
| 카드 내부 패딩 | `26px 24px 22px` |
| 섹션 간 마진(상세 페이지) | `margin-bottom: 64px` |
| 풋터 상단 여백 | `margin-top: 90px; padding-top: 26px; border-top: 1px solid rgba(255,255,255,.06)` |
| 코너 반경 (카드/버튼) | 카드 `16px`, 오디오바/토글 `14px`, 필 버튼 `999px`(완전 원형) |

---

## 5. 적용하지 말아야 할 것 (Anti-patterns)

- ❌ 배경에 순수 `#000000` → `#05070d` (near-black navy) 사용
- ❌ 링크/액센트에 표준 `blue-500` 계열 → `var(--ac,#67E8F9)` cyan 사용
- ❌ 카드 보더에 불투명 회색(`#e5e7eb` 등) → `rgba(255,255,255,.08)` 저채도 화이트 보더 사용
- ❌ 헤딩에 sans-serif 사용 → `Noto_Serif_KR` weight 900 (SERIF 변수) 사용
- ❌ 라벨/캡션에 `letter-spacing` 생략 → mono 라벨은 항상 `.18em` 이상의 넓은 자간
- ❌ 카드 hover에 accent 없는 단순 `box-shadow` → `color-mix(in oklab, var(--ac,...) N%, transparent)` 기반 글로우 섀도 사용
- ❌ 진입 애니메이션 없이 즉시 렌더 → `fadeUp`/`lineUp` + stagger `animationDelay` 사용
- ❌ 코너 반경 임의 값(`8px`, `12px` 혼용) → 카드는 `16px`로 통일, 필 버튼만 `999px`
- ❌ 다이어그램/문서 이미지 박스를 다크 배경 그대로 사용 → `#F5F2EA` 등 웜 라이트 서페이스로 분리(가독성)
- ❌ 정적 배경 → 그리드 오버레이(`backgroundSize: 72px 72px`) + 드리프팅 글로우 오브 최소 1개 유지

---

## 6. 실제 적용 사례

### 적용된 페이지 (원본)
- `class/src/app/page.tsx` — 랜딩(히어로 + 주차 카드 그리드 + 키워드 티커)
- `class/src/components/WeekDetail.tsx` — 상세 페이지(요약/쇼츠/웹툰 3-탭)
- `class/src/app/globals.css` — 전역 배경·애니메이션 키프레임·hover 클래스
- `class/src/app/layout.tsx` — 3-폰트 시스템 등록 (IBM Plex Mono/Sans KR, Noto Serif KR)

### 참고 디자인
- 대학원 신용평가모델 강의 아카이브 홈페이지("아홉 번의 강의를 요약/쇼츠/웹툰으로 재구성")
- 핵심 요소: 딥네이비 배경, 사이언 단일 액센트, 모노스페이스 오버라인 + 세리프 900 헤딩, 그리드 오버레이 + 글로우 오브, 라인업 애니메이션 히어로, 넘버 워터마크 카드
