# knowledge/misc-tooling — 기타 도구·워크플로우

cs-experiencing 오케스트레이터 SKILL.md에서 이관된 프로젝트-특화 학습.
번호는 전역 INDEX(skills/experiencing/SKILL.md) 번호를 유지한다. 신규 항목은 INDEX의 max+1 번호를 부여받아 이 파일 끝에 추가된다.
cs-end Forget Gate(Phase 2.5)가 이 파일의 `<!-- tier: tactical -->` 항목도 30일 decay 스캔 대상으로 포함한다.

### 16. Node.js native `fs.watch({ recursive: true })` macOS에서 chokidar 없이 동작 (2026-05-17)
<!-- tier: principle -->
- **상황**: 플러그인 디렉토리 변경 감시 스크립트 작성 시 chokidar 의존성 추가가 필요한지 검토.
- **발견**: Node.js 18+ 에서 macOS는 `fs.watch(dir, { recursive: true }, callback)` 네이티브 지원(FSEvents 기반). `filename`이 null일 수 있으므로 반드시 가드 필요. `rename`/`change` 두 이벤트만 구분 가능. 단일 파일 감시는 `fs.watchFile()`(polling)이 더 안정적.
- **교훈**: macOS 전용 Node.js 스크립트라면 chokidar 없이 native recursive watch 사용 가능. Linux는 chokidar 필요. `if (!filename) return` 가드 필수.

### 38. 사이드바 버튼 중복 — 메인 영역이 primary, 사이드바는 secondary (2026-05-23)
<!-- tier: tactical -->
- **상황**: portmanagement 사이드바 헤더에 "+ 프로젝트" 버튼이 생김. 메인 영역에 이미 "New project" 버튼 존재.
- **발견**: 동일 기능 버튼이 사이드바와 메인 영역 두 곳에 존재할 때, 메인 영역 버튼이 canonical primary. 사이드바 버튼은 컨텍스트 특정(선택된 항목 기준)이면 존치, 전역 동작 중복이면 제거 대상.
- **교훈**: 새 기능 추가 시 사이드바에 편의 버튼을 반사적으로 붙이는 패턴이 이 코드베이스에서 반복됨. 버튼 추가 전 메인 영역 동일 기능 여부를 먼저 확인할 것.

### 39. SVG 일러스트로 스크린샷 완전 대체 전략 (2026-05-23)
<!-- tier: principle -->
- **상황**: GCP 콘솔 가이드에서 잘못 캡처된 PNG 스크린샷 11개를 교체해야 했으나 재캡처 환경(OAuth 미설정 프로젝트, 브라우저 제어 권한)이 없었다.
- **발견**: SVG 코드로 GCP 콘솔 UI를 직접 모사하면 실제 스크린샷보다 정확한 시각 자료를 만들 수 있다. `ScreenshotPlaceholder` 컴포넌트가 `.svg` 확장자 감지 시 `<img>` 태그로 렌더링 — Next.js `<Image>`는 SVG를 static import 없이 최적화 불가하므로 반드시 `<img>` fallback 처리 필요. SVG는 git diff가 텍스트로 추적되고, 다크모드 CSS filter(`dark:brightness-[0.85]`)로 조정 가능하며, UI 변경이 있어도 코드만 수정하면 되어 PNG보다 유지보수성이 높다.
- **교훈**: 기술 문서 가이드에서 스크린샷 캡처 환경이 없거나 UI가 자주 바뀌는 경우 SVG 일러스트가 PNG보다 우월한 대안. 800×500 viewBox + Google 브랜드 팔레트(#1a73e8, #ea4335, #34a853, #5f6368, #202124, #dadce0) + 3-layer 구조(헤더+사이드바+메인)로 일관된 GCP 콘솔 UI 모사 가능.

### 44. ScreenshotPlaceholder 점진적 fallback 설계 패턴 (2026-05-23)
<!-- tier: tactical -->
- **상황**: GCP 콘솔 가이드 페이지를 개발할 때 스크린샷/SVG가 아직 준비되지 않은 상태에서도 레이아웃 완성이 필요했다.
- **발견**: `src` prop이 없으면 "Screenshot coming soon" placeholder를 렌더링하고, `.svg` 확장자면 `<img>` 태그, `.png`면 `next/image`로 라우팅하는 단일 컴포넌트 패턴. 에셋 준비 단계와 페이지 구조 완성 단계를 분리할 수 있어 병렬 작업이 가능하다.
- **교훈**: 문서 가이드 페이지 개발 시 `ScreenshotPlaceholder src={undefined}`로 먼저 레이아웃을 완성하고 에셋를 나중에 추가하는 워크플로우가 효율적. 이 컴포넌트는 그대로 다른 Next.js 가이드 프로젝트(vibe2 등)에 이식 가능.

### 60. 기능 구현 전 코드베이스에서 기존 구현 탐색 필수 (2026-05-30)
<!-- tier: principle -->
- **상황**: CEO 에이전트가 "앱 내 실시간 채팅방" 구현을 시작하려 했음. 실제로는 `components/chat-bubble.tsx`에 Supabase Realtime 채팅이 이미 구현되어 있었음.
- **발견**: 도메인 명사(chat, message, realtime)로 `components/`와 `lib/`를 grep했더라면 370줄짜리 기존 구현을 즉시 발견했을 것. 실제 작업은 기존 파일에 ~20줄 추가가 전부.
- **교훈**: 새 기능 구현 전 `grep -rn "도메인명사" components/ lib/`로 기존 구현 여부를 반드시 확인. false-negative 시 중복 테이블 생성 + 충돌 RLS 정책 리스크. 이 프로젝트는 `meokgo_` prefix 테이블이 여러 앱과 공존하므로 특히 중요.
