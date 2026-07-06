# knowledge/react-frontend — React/프론트엔드 패턴 (state, 이벤트, lazy, clipboard)

cs-experiencing 오케스트레이터 SKILL.md에서 이관된 프로젝트-특화 학습.
번호는 전역 INDEX(skills/experiencing/SKILL.md) 번호를 유지한다. 신규 항목은 INDEX의 max+1 번호를 부여받아 이 파일 끝에 추가된다.
cs-end Forget Gate(Phase 2.5)가 이 파일의 `<!-- tier: tactical -->` 항목도 30일 decay 스캔 대상으로 포함한다.

### 8. Tauri webview에서 `window.open()` silent 실패 — 외부 URL은 항상 API.openInChrome (2026-04-26)
<!-- tier: tactical -->

- **상황**: deployUrl/githubUrl 카드 버튼에 `window.open(url, '_blank')`를 사용했더니 Tauri 앱에서 아무 반응 없음. 에러도 없고 브라우저도 안 열림.
- **발견**: Tauri webview는 외부 URL 네비게이션을 sandbox로 차단. DOM API(`window.open`)는 silent 실패. Rust 커맨드 `open_in_chrome`을 통해야 동작. 실패가 조용해서 개발 중 발견이 어려움.
- **교훈**: Tauri 앱에서 외부 URL 여는 버튼은 무조건 `API.openInChrome(url).catch(()=>{})`. `window.open` 사용 금지. 새 UI 요소 추가 체크리스트: 기능 코드 → `data-help-key` → `guideContent.ts` 항목 — 세 가지를 같은 커밋에 포함.

### 9. ClipboardItem text/html+text/plain 이중 포맷으로 Slack 하이퍼링크 복사 (2026-04-28)
<!-- tier: tactical -->

- **상황**: "Slack 공유용 복사" 버튼 구현 시 URL이 그대로 노출되지 않고 "백로그 바로가기" 같은 라벨 텍스트가 클릭 가능한 링크로 표시되길 원했음.
- **발견**: Slack mrkdwn `<url|label>` 포맷은 Slack Web API 전송 전용 — 클립보드 붙여넣기에서는 리터럴 문자열로 표시됨. 정답은 `navigator.clipboard.write()`에 `ClipboardItem({ "text/html": Blob([html]), "text/plain": Blob([plain]) })`를 동시에 담는 것. Slack 리치텍스트 에디터는 `text/html`을 우선 소비하여 `<a href="url">label</a>`를 클릭 가능한 하이퍼링크로 렌더링. HTML 미지원 앱은 `text/plain` fallback 사용.
- **교훈**: Slack 공유용 클립보드 복사는 mrkdwn이 아닌 HTML ClipboardItem을 기본으로 설계. `try/catch`로 감싸고 실패 시 `writeText()` fallback 필수 (Firefox 등 미지원 브라우저 대응). `navigator.clipboard.write()`는 HTTPS 또는 localhost + 사용자 제스처(클릭) 핸들러 내에서만 동작.

### 13. Browser cache busting: `?t=Date.now()` + `cache: 'no-store'` 둘 다 필요 (2026-05-17)
<!-- tier: principle -->
- **상황**: Next.js에서 `/api/build-index` POST로 `public/skills-index.json` 재빌드 후 `fetch('/skills-index.json')` 해도 구버전 데이터 노출. 삭제된 플러그인이 UI에 계속 보임.
- **발견**: `cache: 'no-store'` 단독으로는 브라우저/CDN edge cache를 완전히 우회하지 못함. 쿼리 파라미터 `?t=Date.now()`로 URL을 유니크하게 만들어야 캐시 항목 자체를 건너뜀. 두 메커니즘이 상호보완적.
- **교훈**: 서버사이드 빌드가 쓰는 `/public/` 정적 파일을 클라이언트가 즉시 읽어야 하면 `fetch(\`\${url}?t=\${Date.now()}\`, { cache: 'no-store' })` 패턴 사용. 하나만으로는 부족.

### 14. Build "unchanged" ≠ 파일 미재기록 — onRefresh는 항상 호출해야 (2026-05-17)
<!-- tier: principle -->
- **상황**: StatsBar의 `↺` 버튼이 `unchanged: true`일 때 `onRefresh()`를 호출 안 함. rebuild 후 UI가 갱신 안 돼 새로고침 기능이 작동 안 하는 것처럼 보임.
- **발견**: build-index 스크립트는 스킬 목록 변화가 없어도 `skills-index.json`을 항상 덮어씀. `unchanged`는 "논리적 diff 없음"이지 "파일 미수정"이 아님. 파일이 항상 재기록되므로 클라이언트는 항상 새 응답을 받아야 함.
- **교훈**: 빌드 파이프라인 결과물을 polling하는 UI는 build 완료 후 reload callback을 `unchanged` 여부와 무관하게 항상 호출. "no change → no reload" 최적화는 파일이 조건부로 쓰일 때만 유효.

### 15. React 부모→자식 이벤트: 모노토닉 카운터 증가 패턴 (2026-05-17)
<!-- tier: tactical -->
- **상황**: Dashboard rebuild 이벤트를 SourcesPanel에 전달해 자동 재조회시켜야 함. prop callback 전달은 자식 내부 구현에 의존하게 됨.
- **발견**: `const [rebuildCount, setRebuildCount] = useState(0)` + `setRebuildCount(c => c + 1)` 를 prop으로 전달. 자식은 `useEffect(() => { if (rebuildCount === 0) return; fetchData() }, [rebuildCount])`. 초기 마운트는 `=== 0` 가드로 스킵. 카운터가 증가할 때마다 effect 재실행.
- **교훈**: 부모→자식 one-time 이벤트 알림(이유 불문)은 모노토닉 카운터 prop으로 처리. Context/EventEmitter 없이 깔끔하게 해결. `key` reset trick의 변형.

### 19. SSE 이벤트 핸들러에서 연관 React state 동시 호출 필요 (2026-05-17)
<!-- tier: tactical -->
- **상황**: 차량 등록 SSE 핸들러 `applyLogUpdate`에서 `setLogs`만 호출. `statusMap`(UI 배지)은 별도 state여서 갱신되지 않음 → 등록 완료 후 배지가 "입차중"으로 남음.
- **발견**: SSE/비동기 이벤트 핸들러는 React 자동 배칭 범위 밖일 수 있으며, 파생 state가 독립 useState일 경우 이벤트 핸들러에서 명시 `setState`를 함께 호출해야 같은 렌더에 반영.
- **교훈**: 이벤트 핸들러에서 연관 display state가 여러 개라면 모든 연관 `setState`를 함께 호출한다. useEffect 의존성 기반 파생 업데이트는 렌더 후 다음 사이클에 실행되어 즉각 UI 반응에 부적합.

### 31. Object Spread 시 commandPath 등 상위 속성 상속 차단 패턴 (2026-05-20)
<!-- tier: tactical -->
- **상황**: 워크트리 실행 버튼에서 `{...portItem, port:wtPort, folderPath:wt.path}`로 임시 객체 생성. portItem의 `commandPath`(메인 프로젝트의 `실행.command`)가 상속되어 실행 시 9000 포트를 kill하고 새 서버를 기동하는 버그 발생.
- **발견**: `{...portItem}`은 `commandPath`, `terminalCommand` 등 메인 포트의 모든 필드를 복사한다. `executeCommand`/`forceRestartCommand`는 `item.commandPath`를 우선 사용하므로 폴더 경로만 바꿔도 원래 실행 스크립트가 실행됨.
- **교훈**: 다른 역할의 객체를 스프레드로 생성할 때 불필요한 필드는 명시적으로 `undefined`로 차단: `{...portItem, commandPath:undefined, terminalCommand:undefined, folderPath:wt.path}`. 이후 auto-detect 로직이 올바른 폴더에서 실행 명령을 탐지.

### 34. 완료 후 즉시 재등장: virtual spread 패턴으로 다음 주기 표현 (2026-05-22)
<!-- tier: principle -->
- **상황**: myschedule에서 weekly 반복 태스크를 오늘 완료하면 `!t.done` 가드 때문에 즉시 예정 탭에서 사라져 다음 주기가 보이지 않는 UX 문제 발생.
- **발견**: `weeklyOffDay` 필터에서 `(recurring_days.includes(todayDow) ? t.done : !t.done)` 조건을 사용한다. 당일 요일이고 done=true면 다음 주기를 표현하기 위해 `{ ...t, done: false, _nextDate: nextOccurrenceISO(t.recurring_days) }` spread로 virtual 객체를 생성해 예정 탭에 표시. 원본 DB 레코드는 변경하지 않고 렌더링 파생 데이터에서만 상태를 조작한다.
- **교훈**: DB 레코드를 건드리지 않고 렌더링 시점에 `{ ...original, overrides }` spread로 virtual 상태 객체를 만드는 패턴은 반복/주기 UI에서 매우 강력하다. `_nextDate` 같은 `_` prefix로 파생 필드임을 명시하는 것이 좋다. 이 패턴은 캘린더, 할 일 앱, 예약 시스템 등 모든 주기 반복 UI에 재사용 가능.

### 42. useState + onChange 정규화 → live CodeBlock 주입 패턴 (2026-05-23)
<!-- tier: tactical -->
- **상황**: CLI 가이드 탭에서 사용자가 GCP 프로젝트 ID를 입력하면 아래 `gcloud` 명령어가 즉시 반영되어야 했다.
- **발견**: `onChange`에 `e.target.value.toLowerCase().replace(/[^a-z0-9-]/g, "")` 정규화를 인라인으로 넣으면 controlled input이 항상 유효 상태를 유지한다. 별도 validation state/error UI 없이 유효하지 않은 문자가 입력 자체가 안 된다. 정규화된 값을 template literal로 CodeBlock `code` prop에 주입하면 타이핑과 동시에 명령어가 업데이트된다.
- **교훈**: 기술 문서에서 사용자 고유값(프로젝트 ID, 도메인, 사용자명 등)을 CLI 명령어 스니펫에 반영해야 할 때 이 패턴 재사용. GCP 프로젝트 ID 규칙: 소문자+숫자+하이픈. 이메일, slug, DB 이름 등 다른 형식도 regex만 교체하면 즉시 적용 가능.

### 47. Next.js에서 useState 초기화에 localStorage 사용 금지 — useEffect 패턴 필수 (2026-05-23)
<!-- tier: principle -->
- **상황**: Next.js 클라이언트 컴포넌트에서 `useState(() => localStorage.getItem('key'))` 패턴으로 로컬스토리지 기본값을 로드하려 했으나 토글들이 기본값으로 초기화되지 않았다.
- **발견**: Next.js는 'use client' 컴포넌트도 서버에서 초기 렌더링을 수행한다. Node.js 환경에는 localStorage가 없어 ReferenceError가 발생하거나 조용히 실패한다. 올바른 패턴: `useState(defaultValue)` + `useEffect(() => { const v = localStorage.getItem('key'); if (v !== null) setValue(...) }, [])`.
- **교훈**: Next.js에서 localStorage, window, navigator 등 브라우저 전용 API는 반드시 useEffect 안에서만 접근. useState 지연 초기화, 컴포넌트 최상위에서 직접 호출 모두 금지. 기본값은 항상 SSR-safe한 하드코딩 값으로.

### 48. 터미널 선택자 UI — TYPE(라디오)과 MODE(토글) 분리 패턴 (2026-05-23)
<!-- tier: tactical -->
- **상황**: skill-manager AI 패널에서 cmux/iterm/terminal/bg/tmux를 하나의 라디오 그룹으로 구현했는데, bg와 tmux는 터미널 앱 선택이 아니라 실행 방식 수정자라 UX가 혼란스러웠다.
- **발견**: portmanagement의 패턴: 터미널 TYPE(어느 앱에서 열 것인가 — 배타적 라디오)과 실행 MODE(어떻게 실행할 것인가 — 독립 토글)를 분리. 상호작용 규칙(cmux에서는 tmux 무시)은 실행 시점에 한 줄로 처리(`if (tmuxMode && terminalType !== 'cmux')`).
- **교훈**: 선택지가 "어디서"(exclusive)와 "어떻게"(composable)로 구분될 때 단일 라디오 그룹보다 TYPE+MODE 분리가 훨씬 명확하다. 상호배제 규칙은 UI state에 묶지 말고 실행 로직에 배치.

### 50. 아이콘 Morph — absolute+scale/opacity 토글 패턴 (2026-05-23)
<!-- tier: tactical -->
- **상황**: GWC-Help-Site CopyButton에서 Copy 아이콘이 Checkmark로 교체되는 상태 전환을 자연스럽게 표현해야 했다. 단순 조건부 렌더링(`{copied ? <Check/> : <Copy/>}`)은 애니메이션 없이 순간 교체된다.
- **발견**: 두 아이콘을 `position: absolute; inset: 0`으로 같은 공간에 쌓고, `scale-0 opacity-0` ↔ `scale-100 opacity-100`을 `transition-all duration-200`으로 전환하면 Cross-fade 없이 부드러운 아이콘 교체가 된다. 부모 `<span>`에 `size-*`로 공간을 명시적으로 예약해야 레이아웃 시프트가 없다.
- **교훈**: boolean 상태(copied/saved/liked)에 따라 아이콘이 교체되어야 하는 모든 버튼에 적용. Save/Saved, Star/Unstar, Send/Sent 패턴 모두 동일. 부모 크기 예약 누락 시 레이아웃 시프트 발생 주의.

### 52. `navigator.clipboard` 비보안 컨텍스트 Fallback 패턴 (2026-05-23)
<!-- tier: tactical -->
- **상황**: CopyButton 구현 시 `navigator.clipboard.writeText()`가 개발 환경 http에서 실패하는 케이스를 처리해야 했다.
- **발견**: `navigator.clipboard`는 `window.isSecureContext`(HTTPS 또는 localhost)에서만 동작. 비보안 컨텍스트나 iframe에서는 `document.execCommand('copy')` fallback이 필요. 패턴: `if (navigator.clipboard && window.isSecureContext) { await navigator.clipboard.writeText(v) } else { /* textarea + execCommand fallback */ }`. textarea를 `position: fixed`로 해야 스크롤 위치 변화 없음.
- **교훈**: clipboard API를 쓰는 모든 컴포넌트에 isSecureContext 분기 추가. `execCommand`는 deprecated이지만 모든 브라우저에서 여전히 동작.

### 58. window CustomEvent로 React 레이어 밖에서 컴포넌트 간 느슨한 결합 (2026-05-30)
<!-- tier: principle -->
- **상황**: BirthdayPopup과 ChatBubble이 서로 독립적으로 레이아웃에 마운트. 팝업이 채팅창을 열고 메시지를 프리필해야 했지만 두 컴포넌트가 서로를 import하면 순환 의존성 발생.
- **발견**: `window.dispatchEvent(new CustomEvent('open-chat', {detail:{prefill:'...'}}))` + `window.addEventListener('open-chat', handler)` 패턴. 두 컴포넌트가 서로 모른 채 통신 가능. useEffect cleanup으로 리스너 해제 필수.
- **교훈**: 공통 부모 state를 올리기 비용이 큰 leaf 컴포넌트 간 통신에는 window CustomEvent가 최경량 pub/sub. 상태 관리 라이브러리나 Context 오버엔지니어링 없이 해결. 단, 남용 시 이벤트 추적이 어려우므로 컴포넌트 2개 내외의 단방향 트리거에만 사용.

### 59. Next.js App Router에서 인증 사용자 전용 UI는 (main)/layout에 마운트 (2026-05-30)
<!-- tier: tactical -->
- **상황**: BirthdayPopup을 `app/page.tsx`(로그인 랜딩)에 마운트했더니 Google OAuth 로그인 후 즉시 `/order`로 리다이렉트되어 팝업이 보이지 않는 문제.
- **발견**: NextAuth 세션 있는 사용자는 `app/page.tsx`를 지나치지 않고 바로 `(main)/layout`으로 진입. 팝업을 `(main)/layout.tsx`로 옮기니 `/order`, `/today`, `/my`, `/where` 모든 인증 라우트에서 정상 표시.
- **교훈**: Next.js App Router에서 "로그인 후 모든 페이지에 보여야 하는 UI"는 route-group layout에 마운트. `page.tsx`에 마운트하면 해당 URL을 실제로 렌더링하는 경우에만 표시됨.

### 62. manualChunks는 캐시 효율이지 런타임 메모리 감소가 아니다 (2026-05-30)
<!-- tier: principle -->
- **상황**: vite manualChunks로 react-vendor/supabase/icons 청크를 분리해 메모리를 줄이려 시도.
- **발견**: manualChunks는 바이트를 여러 파일로 분산하지만 모든 청크가 시작 시 eager-evaluate됨. 총 런타임 메모리는 단일 번들과 동일. 실제 메모리 감소는 React.lazy (dynamic import + 지연 평가)만 가능.
- **교훈**: 두 목표를 구분: (1) 캐시 효율 → manualChunks; (2) 런타임 메모리 감소 → React.lazy. 메모리가 목표라면 manualChunks는 관련 없음. lazy loading만이 heap을 줄임.

### 63. document.hidden으로 setInterval 폴링 게이팅 — Playwright로 검증 (2026-05-30)
<!-- tier: principle -->
- **상황**: 10초 포트 상태 폴링이 창이 숨겨져 있을 때도 실행되어 불필요한 CPU/네트워크 소비.
- **발견**: setInterval 콜백 첫 줄에 `if (document.hidden) return;` 추가로 완전 차단. Playwright로 검증: visible 12초 → 34회 API 호출, hidden 12초 → 0회.
- **교훈**: 모든 폴링 루프(포트 상태, 로그 테일링, 빌드 상태)는 콜백 상단에 `if (document.hidden) return;` 추가. `visibilitychange` 이벤트로 재포커스 시 즉시 복구. 5줄 미만의 무비용 최적화.

### 64. React.lazy + Suspense는 Tauri WebKit 웹뷰에서 정상 동작 (2026-05-30)
<!-- tier: tactical -->
- **상황**: Tauri 내장 WebKit이 dynamic import()를 지원하는지 불확실. 코드 스플리팅 호환성 우려.
- **발견**: `React.lazy(() => import('./SetupWizard'))` + `<Suspense fallback={null}>` 패턴이 Tauri WebKit에서 정상 동작. SetupWizard가 초기 번들에서 제외되고 필요 시 로드됨.
- **교훈**: Tauri/WebKit이 최신 JS 기능과 비호환이라 가정하지 말 것. React.lazy + Suspense는 위저드 플로우, 설정 패널, 무거운 탭 등 큰 컴포넌트의 초기 번들 축소에 안전하게 사용 가능. Playwright로 lazy 청크가 초기 network 요청에 없는지 확인하면 됨.

### 94. 공유 렌더 함수의 early-return 순서가 서브플로우 상태를 가릴 수 있다 (2026-07-05)
<!-- tier: principle -->
- **상황**: 음성 주문 봇에 "대신 주문" 기능을 새 진입 버튼으로 추가. 대상자 이름 확인 후 메뉴/커피까지 GPT 매칭은 정상 완료됐는데, 최종 확인 카드가 화면에 전혀 나타나지 않아 주문을 제출할 방법이 없는 소프트락 상태가 됨.
- **발견**: 하나의 `renderChips()` 함수가 메인 플로우 상태(`step`)와 서브플로우 상태(`proxyStep`)를 순차적 `if (...) return (...)` 체인으로 함께 렌더링하고 있었다. 서브플로우의 "확인 카드" 분기(`proxyStep === "confirm"`)가 메인 플로우의 `step === "greeting"` 분기보다 코드상 아래에 있어, 새로 추가한 진입 버튼처럼 메인 `step`이 계속 "greeting"으로 남아있는 상태에서 서브플로우를 시작하면 그 확인 카드 분기에 도달하기도 전에 greeting 분기가 먼저 return 해버림. 기존에는 서브플로우가 항상 `step === "after-confirm"`(메인 주문 완료 후)에서만 시작돼서 이 순서 문제가 드러나지 않았을 뿐, 근본적으로 순서에 의존하는 취약한 구조였다.
- **교훈**: 한 컴포넌트가 서로 독립적인 두 개 이상의 상태 머신(메인 플로우 + 서브플로우)을 하나의 렌더 함수에서 순차 early-return으로 처리하고 있다면, 서브플로우가 "활성 상태"일 때의 분기를 메인 플로우 분기보다 먼저 체크하도록 최상단에 둔다. 특히 서브플로우로의 새 진입 경로를 추가할 때는, 그 경로가 메인 플로우의 default/초기 상태("greeting" 등)와 동시에 존재할 수 있는지 반드시 확인 — 기존에 한 가지 트리거 경로만 있었다는 사실이 순서 안전성을 보장하지 않는다.
- **근거**: `components/voice-order-bot.tsx` `renderChips()` — Playwright로 재현: 신규 "대신주문" 버튼 클릭 → 메뉴/커피 GPT 매칭 성공(API 200 응답 확인) → 확인 카드 미표시. `proxyStep === "confirm"` 분기를 `step === "greeting"` 분기보다 위로 이동 후 재현 안 됨 확인.
