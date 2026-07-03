# knowledge/debugging — 디버깅 전략 (레이어 격리, 메모리, 정규식)

cs-experiencing 오케스트레이터 SKILL.md에서 이관된 프로젝트-특화 학습.
번호는 전역 INDEX(skills/experiencing/SKILL.md) 번호를 유지한다. 신규 항목은 INDEX의 max+1 번호를 부여받아 이 파일 끝에 추가된다.
cs-end Forget Gate(Phase 2.5)가 이 파일의 `<!-- tier: tactical -->` 항목도 30일 decay 스캔 대상으로 포함한다.

### 7. osascript 디버깅 — 레이어 격리로 root cause 빠르게 찾기 (2026-04-25)
<!-- tier: tactical -->

- **상황**: `GET /api/pick-folder`가 즉시 `{"error":"cancelled"}` 반환 — 브라우저에서 폴더 선택 다이얼로그가 열리지 않음.
- **발견**: 문제 레이어를 3단계로 격리해서 빠르게 원인 특정: ① `curl` → API 응답 ② `osascript -e '...'` 직접 실행 → OS/스크립트 문법 ③ `bun -e "Bun.spawn..."` → 런타임. 직접 실행이 성공하면 서버 코드(문법 오류 또는 stale 프로세스) 안에 원인이 있음. 실제 원인: `choose folder with prompt "..." invisibles shown true` — `invisibles shown true`는 `choose folder`에 없는 파라미터로 error -2741 발생 → `on error` → 빈 반환. 추가 원인: `bun --watch`가 Claude Code Edit 도구의 파일 변경을 감지 못해 old 코드가 계속 실행됨.
- **교훈**: ① `choose folder`에 `invisibles shown true` 사용 금지 — 올바른 문법: `choose folder with prompt "..."` 만. ② API 서버 코드 수정 후 curl 테스트 전 반드시 프로세스 재시작 확인 — `bun --watch` 미감지 가능. ③ osascript는 temp 파일(`Bun.write + osascript path`) 방식이 stdin Blob보다 안정적.

### 17. HTML 목록 스크래핑 — 복합 정규식 대신 분리 추출 후 index 매칭 (2026-05-17)
<!-- tier: tactical -->
- **상황**: `carSearch.cs` 200 응답 HTML에서 `<tr onclick="onclick_Car('pKey')">` + `<img src="/Images/CH_DATE_PLATE.JPG">` 구조를 단일 정규식으로 동시 추출 시도. HTML 변동(추가 속성, 개행)으로 매칭 실패.
- **발견**: 각 값을 독립 패턴으로 추출 후 위치 매칭(index alignment)이 안정적. (1) `onclick_Car\('([^']+)'\)` pKey 배열 (2) `/Images/.+\.JPG` 이미지경로 배열 → 동일 인덱스로 zip → 번호판 일치 행의 pKey 선택.
- **교훈**: DOM 파서 없이 HTML에서 "같은 행의 복수 값"을 추출할 때는 단일 블록 정규식보다 속성별 독립 추출 후 배열 위치 매칭이 HTML 변동에 더 강인하다.

### 18. `[^"']*` 정규식 — 혼합 따옴표 HTML 속성에서 조기 종료 (2026-05-17)
<!-- tier: tactical -->
- **상황**: `onclick="javascript:onclick_Car('pKey')"` 에서 pKey 추출 시 `[^"']*onclick_Car\('([^"']*)'\)` 패턴 사용.
- **발견**: `[^"']*`는 큰따옴표·단따옴표 둘 다를 종료 조건으로 취급. 외부 구분자가 `"` 이어도 값 내부의 `'` 에서 매칭 중단 → pKey 빈 문자열. 수정: `onclick_Car\('([^']+)'\)` (내부 단따옴표만 배제).
- **교훈**: HTML attribute 추출 시 `[^"']*`는 "어떤 따옴표도 없는 값"에만 쓴다. 외부/내부 따옴표 종류가 다르면 내부 값에 쓰인 따옴표 종류만 배제하는 `[^']` 또는 `[^"]`를 사용해야 한다.

### 61. 메모리 불만 시 먼저 어느 프로세스가 RSS를 소유하는지 확인 (2026-05-30)
<!-- tier: principle -->
- **상황**: 사용자가 30GB+ 메모리 사용 보고 → React/Bun 포트 매니저 앱을 의심하고 adversarial 워크플로우로 19개 후보 조사.
- **발견**: 앱 JS heap은 15-18MB로 안정적. 실제 주범은 cmux + `claude agents` 외부 Swift 프로세스. `ps aux | sort -k6 -rn | head -20`으로 즉시 확인 가능했던 사실.
- **교훈**: 메모리 디버깅 첫 번째 단계는 `ps aux | sort -k6 -rn | head -10`으로 RSS 기준 프로세스 순위 확인. 앱이 spawn하는 외부 CLI(Swift, Python, Node 서브프로세스)는 webview/JS heap과 별도로 측정해야 함. 의심 프로세스를 확정하기 전에 React 코드를 뒤지지 말 것.

### 65. Playwright adversarial 워크플로우로 메모리 누수 후보 기각 (2026-05-30)
<!-- tier: tactical -->
- **상황**: 19개 메모리 누수 후보 중 실제 문제가 얼마나 되는지 체계적으로 검증 필요.
- **발견**: `performance.memory.usedJSHeapSize`로 heap 스냅샷 + `page.on('request', ...)`로 API 호출 수 카운트하는 Playwright 스크립트가 19개 중 18개를 객관적으로 기각. 힙 증가 -3MB(GC), 백그라운드 폴링 0회로 확인.
- **교훈**: 메모리 감사 시 전용 Playwright 스크립트 작성: 시나리오 전후 heap 측정 + 시간창 내 API 요청 수 카운트 + 임계값(예: 2MB) 초과 여부 플래그. DevTools 수동 세션보다 빠르고 재현 가능.

### 66. 포트 매니저 앱 JS heap 기준값 — 15-18MB 안정 (2026-05-30)
<!-- tier: tactical -->
- **상황**: Tauri+React 포트 매니저 앱의 실제 메모리 사용량 기준값 측정 필요.
- **발견**: Playwright 30초 측정: 초기 heap ~17MB, 30초 후 heap 증가 -3MB (GC 정상). 폴링/로그/포털 모든 시나리오에서 누수 없음.
- **교훈**: 이 앱의 JS heap 정상 범위는 15-18MB. 30GB+ 불만은 앱이 아닌 외부 프로세스(cmux). 추후 메모리 이슈 제기 시 이 기준값으로 먼저 비교.

### 68. 대형 JSX 파일에서 `</>}` vs `})()}` 구조 추적 패턴 (2026-06-09)
<!-- tier: principle -->
- **상황**: 4000줄짜리 React 컴포넌트에서 조건부 fragment(`{cond && <>...</>}`)와 IIFE(`{(() => {...})()}`)가 중첩된 구조의 JSX 무결성 검증 필요.
- **발견**: 두 패턴의 닫는 토큰이 비슷하게 생겼지만 의미가 다름 — `</>}` 는 조건부 fragment를 닫고, `})()}` 는 IIFE를 닫는다. tsc가 통과해도 구조 오해 가능.
- **교훈**: 대형 JSX 디버깅 시 (1) 인덴테이션 레벨과 (2) 닫는 토큰 종류(`</>}` vs `})()}`)를 함께 추적한다. 괄호 개수만 세면 오독하기 쉽다.

### 91. 대시보드에 "미해결처럼 보이는" 값이 남아있다고 곧 파이프라인이 고장난 것은 아니다 — snapshot 필드 vs live-computed 필드를 먼저 구분한다 (2026-07-03)
<!-- tier: principle -->
- **상황**: 챗봇 자기개선(self-improvement) 대시보드에서 사용자가 "왜 미분류(unknown)가 계속 남아있냐"고 문의. 실제로는 직전 세션에서 RLS 버그를 고쳐 자기개선 파이프라인이 정상 동작 중이었다.
- **발견**: 대시보드에 세 군데가 같은 `detected_intent` 값을 다르게 보여주고 있었다. (1) 상단 통계 카드는 `total_unknown - pattern_approved`를 계산해 실질 미해결 건수를 정확히 0으로 넷팅해 보여줌. (2) 인텐트 분포 차트는 `by_intent`(수집 시점에 기록된 raw 값)를 그대로 집계해 "unknown 96건"을 표시 — 해결 여부와 무관. (3) 개별 로그 행도 `detected_intent` 배지를 항상 렌더링하고, `improvement_status` 배지("패턴등록" 등)는 그 옆에 별도로 추가될 뿐 원래 배지를 대체하지 않음. 즉 "unknown" 라벨은 그 행이 나중에 해결돼도 영원히 사라지지 않는 게 의도된 설계(감사 추적)였는데, 이게 "여전히 미해결"로 오독됐다.
- **교훈**: 대시보드/로그 UI에서 "값이 여전히 문제 상태로 보인다"는 리포트를 받으면, 코드부터 고치려 하지 말고 먼저 그 필드가 (a) 수집 시점에 한 번 쓰이고 다시 안 바뀌는 snapshot 필드인지, (b) 별도 필드(해결 상태)와 넷팅해서 보여주는 live-computed 집계인지 구분한다. (a)라면 파이프라인은 정상일 수 있고, 문제는 "해결 여부를 시각적으로 어떻게 드러낼지"라는 UX 이슈로 바뀐다. 원본 필드를 지우지 말고, 해결된 항목을 dim 처리하거나 차트에 넷팅 서브라벨을 추가하는 식으로 감사 추적은 유지하면서 오독을 없앤다.
- **근거**: `app/bot-dashboard/page.tsx:802-815`(넷팅된 통계 카드, `realUnknown = Math.max(0, totalUnknown - resolved)`) vs `page.tsx:848-873`(넷팅 없는 raw `by_intent` 차트) vs `page.tsx:885-918`(`log.detected_intent` 배지 고정 렌더 + `statusCfg` 배지는 별도 추가) — 세 곳 모두 sonnet verifier가 직접 파일을 재확인해 CONFIRMED 판정
