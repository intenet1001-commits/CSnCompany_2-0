# knowledge/css-design — CSS/Tailwind 디자인 토큰·명시도·레이아웃

cs-experiencing 오케스트레이터 SKILL.md에서 이관된 프로젝트-특화 학습.
번호는 전역 INDEX(skills/experiencing/SKILL.md) 번호를 유지한다. 신규 항목은 INDEX의 max+1 번호를 부여받아 이 파일 끝에 추가된다.
cs-end Forget Gate(Phase 2.5)가 이 파일의 `<!-- tier: tactical -->` 항목도 30일 decay 스캔 대상으로 포함한다.

### 25. globals.css element selector vs 인라인 스타일 명시도 충돌 (2026-05-19)
<!-- tier: principle -->
- **상황**: `globals.css`에 `button { cursor: pointer; }` 전역 규칙 존재. 특정 버튼에 `cursor-default` Tailwind 클래스를 적용해도 클릭 불가 항목에서 손 모양 커서가 사라지지 않음.
- **발견**: CSS 명시도 계층: 인라인 스타일 > Tailwind utility class ≥ element selector (순서 의존). globals.css element selector가 Tailwind 클래스보다 명시도에서 이기는 경우 Tailwind만으로는 override 불가. `style={{ cursor: "default" }}` 인라인 스타일은 항상 최우선 적용.
- **교훈**: 전역 element 규칙(`button {}`, `a {}`)을 override해야 할 때는 Tailwind 클래스보다 인라인 스타일 또는 `!cursor-default`(important)가 확실함. globals.css 전역 element 규칙은 클래스 selector(`.btn`)로 좁히는 것이 충돌 예방 최선책.

### 26. sticky 헤더 대응 스크롤 오프셋 패턴 (2026-05-19)
<!-- tier: tactical -->
- **상황**: 배너 클릭 시 `scrollIntoView({ block: "center" })`로 테이블 행으로 이동하는 기능 구현. sticky DashNav 헤더(60px) + sticky 탭(45px)에 의해 목표 행이 헤더 뒤로 가려지는 버그 발생.
- **발견**: `scrollIntoView`는 sticky/fixed 헤더를 인식하지 못함. `element.getBoundingClientRect().top + window.scrollY - offset`으로 절대 위치를 계산한 뒤 `window.scrollTo({ top, behavior: "smooth" })`에 헤더 높이 offset을 빼는 방식으로 해결.
- **교훈**: sticky 레이아웃에서 특정 요소로 스크롤할 때는 `scrollIntoView` 대신 `window.scrollTo + 수동 offset` 패턴 기본 사용. offset = 앱 헤더 높이 합산(이 프로젝트: 120px). 상수로 추출해두면 헤더 높이 변경 시 한 곳만 수정.

### 27. aria-selected CSS selector 기반 chip 상태 패턴 (2026-05-19)
<!-- tier: tactical -->
- **상황**: Scorer 선택기와 필터 버튼을 하드코딩된 조건부 스타일(`bg-stone-100`, `bg-blue-600`)에서 통일된 디자인 시스템 패턴으로 교체.
- **발견**: `globals.css`에 `.chip[aria-selected="true"] { ... }` 규칙을 정의하고, 컴포넌트에서 `aria-selected={isSelected ? "true" : "false"}`만 토글하면 스타일이 자동으로 적용됨. 접근성(aria) + 스타일 단일화를 동시에 달성.
- **교훈**: 선택 상태 스타일링은 aria 속성 + CSS selector 패턴이 조건부 className 문자열 조합보다 우월. 스타일 로직이 CSS로 단일화되어 디자인 시스템 변경 시 CSS 한 곳만 수정. Tailwind arbitrary value에서 CSS 변수 사용 시 동적 조합 금지(purge됨) — 완전한 리터럴 문자열로 작성.

### 28. CSS 디자인 토큰 통일 — bg-white/bg-slate-900 교체 전략 (2026-05-19)
<!-- tier: principle -->
- **상황**: Next.js 프로젝트에서 `bg-slate-900`(테이블 헤더), `bg-white`(카드 배경), `bg-blue-600`(버튼) 등 Tailwind 하드코딩 색상과 CSS 변수(`var(--bg-elev)`) 기반 컴포넌트가 혼재해 다크모드 대응 불가.
- **발견**: `globals.css`에 정의된 `.card`, `.chip`, `.banner`, `.btn` 유틸 클래스를 재사용하면 하드코딩 색상을 제거하고 라이트/다크 테마 자동 대응 가능. Tailwind arbitrary value(`bg-[var(--bg-subtle)]`)는 완전한 문자열 리터럴로만 써야 purge 방지.
- **교훈**: UI 작업 시 `globals.css` 유틸 클래스 목록을 먼저 확인 후 재사용. 하드코딩 색상보다 CSS 변수 토큰이 테마/다크모드 대응에 우월. 동적 클래스 조합(`bg-[var(--${var})]`)은 Tailwind purge 대상이 되므로 금지.

### 51. Tailwind v4 `@theme inline` — CSS 변수 → 유틸리티 브리지 필수 (2026-05-23)
<!-- tier: principle -->
- **상황**: GWC-Help-Site globals.css에서 `--primary: 217 91% 50%`로 Google Blue를 주입했는데 `bg-primary` 유틸리티가 반응하지 않았다. `@layer base`에 변수 선언만으로는 Tailwind v4에서 부족하다.
- **발견**: Tailwind v4는 CSS 변수와 유틸리티 클래스 사이에 `@theme inline { --color-primary: hsl(var(--primary)); }` 브리지 블록이 필수다. 이 블록 없이는 커스텀 CSS 변수가 Tailwind 유틸리티 생성 파이프라인에 포함되지 않는다. 표준 패턴: `@layer base`에 raw 값(`217 91% 50%`), `@theme inline`에서 `hsl(var(...))`로 변환.
- **교훈**: Tailwind v4 프로젝트에서 커스텀 색상 토큰이 `bg-*`/`text-*`로 안 잡힐 때 첫 번째로 `@theme inline` 블록 유무를 확인하라. AGENTS.md의 "This is NOT the Next.js you know" 경고와 직결되는 v4 breaking change.

### 121. CSS 블록 주석 속 리터럴 `*/`는 뒤따르는 규칙 전체를 조용히 삭제한다 — 스크린샷으로는 안 보인다 (2026-07-17)
<!-- tier: principle -->
<!-- error-ref: ERR-2026-07-17-001 -->

- **상황**: 출처 추적용 설명 주석을 CSS `/* ... */` 블록에 넣으면서, 문장 중간에 "--rust*/--nav-bg have no dedicated token..." 같은 문구를 그대로 씀.
- **발견**: 이 문구 안의 `*/`가 블록 주석을 그 지점에서 조기 종료시켰고, 뒤따르던 실제 `:root{...}` 규칙의 셀렉터가 깨지면서 **커스텀 프로퍼티 블록 전체가 파서에서 조용히 드롭**됐다. 커스텀 프로퍼티에 의존하지 않는 다른 CSS 규칙은 그대로 렌더링돼서 **스크린샷만으로는 버그가 전혀 보이지 않았다**. `getComputedStyle(el).getPropertyValue('--custom-prop')`이 빈 문자열을 반환하고, `document.styleSheets`를 직접 순회해도 `:root` 규칙 자체가 존재하지 않는 것으로만 발견 가능했다. 주석 문구를 고쳐(`*/` 리터럴 제거) 재확인하니 프로퍼티가 정상 해석됐다.
- **교훈**: CSS/JS 등 블록 주석 안에 자유 텍스트(특히 경로·변수명처럼 슬래시-별표 조합이 우연히 생길 수 있는 문자열)를 쓸 때는 종결 시퀀스(`*/`)가 섞여 있는지 반드시 검사한다. 커스텀 프로퍼티 관련 버그가 의심되면 스크린샷이 아니라 `getComputedStyle` + `document.styleSheets` 직접 조회로 규칙 존재 여부를 확인한다.
- **근거**: 수정 전 `getComputedStyle(...).getPropertyValue('--jade-strong')` → 빈 문자열, `document.styleSheets` 순회해도 `:root` 규칙 없음. 주석에서 `*/` 리터럴 제거 후 동일 조회 → `#3c9800` 정상 반환. (skeptic verifier CONFIRMED — 수정 전/후 격리된 원인-결과 확인, 단일 변수만 바꾼 통제된 비교.)
