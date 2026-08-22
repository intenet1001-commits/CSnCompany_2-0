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
- **추가 (2026-07-26)**: durable store를 새로 만들기 전에는 known project-local locations도 탐지한다. 기존 user-authored 문서가 있으면 이동·정규화·재작성하지 말고 relative source pointer를 config에 저장한 뒤 tool-owned metadata/adapters만 idempotently regenerate/upgrade한다. 실제 문서 migration은 별도 backup/confirmation 절차로 분리한다.
<!-- provenance: candidate=btw-provenance-4785741f27807b8505ff557d; run=9eed3fbd-5a8b-4a10-91ff-32dd357c4cdc; memory=884575df-63c4-407c-8b43-860d1295e663; range=git:8b4bc0ae03bf556eebe0a76f694c7f7a950d4fc7..beecbff7a96de131a08553d4e195c90d036c84b7;dirty:9c216341282624b328db07058c32ca6cad3d7f0176f0426aa70ebb575f49de6a;truncated=true -->

### 95. macOS 앱 샌드박스 컨테이너 파일은 Full Disk Access/Automation 권한 없는 터미널에서 접근 불가 (2026-07-08)
<!-- tier: principle, error-ref: ERR-2026-07-08-001 -->

- **상황**: Claude Code 세션에서 Shottr(샌드박스 배포 스크린샷 앱)가 저장한 스크린샷 파일(`~/Library/Containers/cc.ffitch.shottr/Data/tmp/.../*.png`)을 Read/Bash cp/osascript로 접근 시도.
- **발견**: Read 도구 EPERM, `cp` EPERM("Operation not permitted"), `osascript ... tell application "Finder"` -1743("Not authorized to send Apple events to Finder") — 세 가지 방식 모두 실패. macOS TCC가 다른 앱의 `~/Library/Containers/<bundle-id>/...` 트리에 대한 접근을 Full Disk Access로, Finder 등 타 앱 자동화를 Automation 권한으로 별도 게이팅하기 때문. 이는 호출 프로세스(터미널)의 TCC 권한 부여 여부에 달린 조건부 차단이며 — Full Disk Access가 부여된 터미널이라면 접근 가능하므로 "무조건 불가"가 아니라 "권한 미부여 시 불가"로 이해해야 함(verifier 지적).
- **교훈**: 경로가 `~/Library/Containers/<bundle-id>/...` 형태로 보이면 즉시 접근 실패를 예상하고, Read/cp/osascript 재시도로 시간 쓰지 말고 바로 사용자에게 파일을 비샌드박스 위치(Desktop, 프로젝트 디렉토리 등)로 옮겨달라고 요청하는 것으로 전환한다.
- **근거**: Derivative1 프로젝트 세션 2026-07-08 — Read tool `EPERM: operation not permitted, open '/Users/gwanli/Library/Containers/cc.ffitch.shottr/...'`, `cp` → `Operation not permitted`, `osascript` → `29:202: execution error: Not authorized to send Apple events to Finder. (-1743)` (동일 파일에 3가지 방식 모두 실패, skeptic verifier CONFIRMED)

### 130. 검증 중 실측된 신규 데이터가 유효한 결과물이면 테스트 데이터처럼 되돌리지 않는다 (2026-07-17)
<!-- tier: tactical -->

- **상황**: 버그 수정 후 실제 프로덕션 데이터(100개 프로젝트)에 대해 기능을 실행해 62개 항목의 값을 실기기에서 생성·검증했다.
- **발견**: 이 생성 결과는 정리해야 할 테스트 데이터가 아니라 사용자의 실제 운영 데이터였다.
- **교훈**: 검증 과정에서 실제 프로덕션 데이터를 변경한 경우, 그것이 유효한 결과물이라면(순수 테스트 목적이 아니라면) 되돌리지 않고 그대로 반영한다 — "테스트 데이터는 원복한다"는 습관을 무조건 적용하지 않는다.
- **근거**: portmanagement 세션 로그 — "이 AI 생성 결과는 테스트 데이터가 아니라 사용자의 실제 데이터라 되돌리지 않고 반영." (실기기 검증: category 0/100 → 62/100 전원 성공).

### 137. 상태 정리/마이그레이션 수정은 실제 프로덕션 데이터에 합성 케이스를 주입해 전후 id-set diff로 검증하면 더 강한 확신을 준다 — 단, 격리 포트 + 왕복 클린업이 전제 (2026-07-17)
<!-- tier: tactical -->
- **상황**: 앱 밖에서 삭제된 워크트리의 유령 UI 카드를 정리하는 수정을 검증해야 했는데, 스크래치 프로젝트만으로는 실제 사용자의 101개 항목짜리 공유 `ports.json`(+ Supabase 동기화) 규모/형태에서도 의도한 항목만 정리되는지 확신하기 어려웠다.
- **발견**: 합성 fake stale 카드 1개를 실제 공유 상태 파일에 API로 주입한 뒤, 완전히 격리된 인스턴스(사용자가 이미 쓰고 있는 포트와 절대 겹치지 않는, 사전에 비어있음을 확인한 포트)에서 앱을 로드해 정리 로직을 실행시키고, 전후 id-set diff로 "합성 카드 + 실제로 이미 스테일했던 카드"만 제거되고 나머지 100개는 완전히 무변경임을 확인했다. 이 과정에서 로컬 파일과 Supabase 동기화 사본 양쪽에서 주입한 행을 모두 되돌리는 왕복 클린업까지 수행했다.
- **교훈**: 상태 정리/마이그레이션류 수정은 (1) 사용자의 기존 실행 인스턴스가 점유한 포트는 절대 쓰지 않고 사전 확인된 미사용 포트에서만 검증하고, (2) 실제 프로덕션 규모의 공유 상태 파일에 합성 케이스를 주입해 전후 id-set diff로 "의도한 항목만 바뀌었는가"를 확인하며, (3) 클라우드 동기화가 있다면 로컬+클라우드 양쪽 모두 왕복 클린업한다 — 스크래치 데이터만으로는 실제 스케일/형태에서의 부작용을 놓칠 수 있다.
- **근거**: 실제 101개 항목 `ports.json`에 합성 카드 주입 → Playwright로 앱 로드 → 정리 후 100개로 감소, id-set diff로 합성 카드 + 기존 실제 스테일 카드(`:10136`)만 제거되고 나머지 100개 무변경 확인 → 로컬+Supabase 양쪽 왕복 클린업 후 재확인 (portmanagement PR #14).

### 148. WebFetch가 클라이언트 렌더링(Next.js RSC) 페이지에서 실제 콘텐츠를 누락시킨다 — curl+grep/python 파싱으로 폴백 (2026-07-19)
<!-- tier: principle -->
- **상황**: Eagle MCP 서버 설정법을 알아내려고 공식 지원 문서(en.eagle.cool)를 WebFetch로 가져왔다.
- **발견**: WebFetch의 요약 패스가 페이지의 실제 JSON 설정 내용을 두 번의 시도에서도 누락시켰다 — 페이지가 클라이언트 렌더링되는 Next.js 페이지였고, 진짜 콘텐츠는 `self.__next_f.push([1,"..."])` 형태의 임베디드 RSC payload 스크립트 청크 안에 JSON-escape된 문자열로 들어있었다. `curl`로 raw HTML을 받아 `grep`/`python3`로 해당 청크를 직접 추출하자 전체 설정(JSON 스니펫 포함)을 얻을 수 있었다.
- **교훈**: WebFetch 결과가 예상보다 빈약하거나 핵심 정보(코드 블록/JSON/설정값)가 누락되어 있으면, 재시도 대신 즉시 그 페이지가 클라이언트 사이드 렌더링(Next.js RSC, SPA 등)인지 의심하고 `curl` raw HTML + `grep`/`python3`로 `__next_f.push`/`__NEXT_DATA__` 같은 임베디드 payload를 직접 파싱하는 방식으로 전환한다.
- **근거**: WebFetch 2회 연속 "the actual body content ... wasn't included" 응답 → `curl -sL <url> | grep -o 'mcpServers...'`로 실제 JSON 설정(`"transport": "http", "url": "http://localhost:41596/mcp"`) 직접 추출 성공 (Eagle_mcp 프로젝트 세션, 2026-07-19).

### 149. GUI 전용 설치 단계를 자동화 불가로 단정하기 전에, 설치 대상 산출물이 이미 디스크에 존재하는지 먼저 확인한다 (2026-07-19)
<!-- tier: principle -->
- **상황**: Eagle Skill 공식 설치 가이드가 Eagle 앱 내부의 GUI 파일 피커("+ Install Skill" 버튼 클릭 → 폴더 선택)를 필수 단계로 요구했다.
- **발견**: 문서상 절차는 GUI 조작이 필수였지만, 실제로는 해당 스킬 패키지(SKILL.md + scripts/ + references/)가 이미 Eagle 앱 지원 폴더(`~/Library/Application Support/Eagle/Plugins/mcp-server/skills/eagle-skill/`)에 설치되어 있었다. 이를 대상 프로젝트의 `.claude/skills/`로 직접 복사하는 것만으로 GUI 단계 전체를 대체할 수 있었다.
- **교훈**: 설치/등록 절차가 GUI 전용이라 자동화 불가처럼 보이면, 먼저 그 GUI 동작이 만들어내는 최종 산출물(파일/폴더)이 이미 디스크의 예측 가능한 위치(앱 지원 폴더, 플러그인 디렉토리 등)에 존재하는지 탐색한다. 존재하면 파일 복사로 GUI 단계를 생략할 수 있다.
- **근거**: `find / -iname "eagle-skill"` → `~/Library/Application Support/Eagle/Plugins/mcp-server/skills/eagle-skill/SKILL.md` 발견 → `cp -R`로 프로젝트 `.claude/skills/`에 복사 → `/reload-skills`로 정상 인식 확인 (Eagle_mcp 프로젝트 세션, 2026-07-19).
<!-- addendum (2026-07-19): 동일 패턴 재확인 — WordPress Studio에서 `studio` CLI가 PATH에 없어 wp-cli 작업이 막혔을 때, 앱을 열거나 PATH를 고치는 대신 앱 번들 내 동봉 스크립트(`/Applications/Studio.app/Contents/Resources/bin/studio-cli.sh`)를 절대경로로 직접 실행해 `wp post create`를 성공시켰다. GUI 전용 도구를 만나면 "산출물이 이미 있는지" 뿐 아니라 "`.app/Contents/Resources/bin/` 하위에 동봉 CLI 스크립트가 있는지"도 함께 확인할 것 (portmanagement/WordPress Studio 세션). -->
<!-- error-ref: ERR-2026-07-19-004 -->

### 157. Claude Artifact 안에서 외부 라이브러리 없이 PDF 다운로드 구현 — print-media CSS + window.print() (2026-07-21)
<!-- tier: tactical -->
- **상황**: NH투자증권 사실조회 프로토타입(Artifact)에 "통신사기정보 제공 확인서" PDF 다운로드 버튼을 추가해야 했다. Artifact CSP는 외부 스크립트 CDN(jsPDF 등)을 막는다.
- **발견**: 화면에는 `#pdf-doc { display:none; }`으로 숨겨둔 별도 인쇄 전용 레이아웃 div를 만들고, `@media print { body * { visibility:hidden } #pdf-doc, #pdf-doc * { visibility:visible } ... }` 규칙으로 인쇄 시에만 그 레이아웃이 전체 페이지를 차지하도록 했다. 버튼 클릭 시 `window.print()`만 호출하면 브라우저 네이티브 인쇄 대화상자가 뜨고, 사용자가 "PDF로 저장"을 선택해 실제 PDF 파일을 받을 수 있었다.
- **교훈**: Artifact/프로토타입에서 "PDF 다운로드" 요구가 나오면 jsPDF 같은 라이브러리 도입을 먼저 검토하지 말고, `display:none` 인쇄 전용 레이아웃 + `@media print` + `window.print()` 조합이 CSP 제약 없이 되는지부터 확인한다.
- **근거**: `#pdf-doc { display:none } + @media print { ... }` + `downloadPdf(){ window.print(); }` 구현 후 인쇄 미리보기에서 화면 UI 없이 확인서 레이아웃만 단독 렌더링되는 것을 확인.

### 166. 외부 CLI 자동화는 기억한 플래그가 아니라 실제 설치된 command의 help와 비대화형 실행으로 검증한다 (2026-07-26)
<!-- tier: tactical -->
- **상황**: 외부 CLI(supabase 등)를 스크립트/서버에서 자동 호출하도록 감쌀 때, 모델이 기억하고 있던 플래그 조합을 그대로 사용했다.
- **발견**: 설치된 버전에 따라 서브커맨드·플래그·대화형 프롬프트 동작이 달라진다. 기억한 플래그는 조용히 무시되거나, TTY가 없는 실행 경로에서 프롬프트를 띄운 채 무한 대기한다.
- **교훈**: 외부 CLI를 자동화 경로에 넣기 전에 (1) `<cmd> --help` / `<cmd> <sub> --help`를 **실제로 실행**해 플래그 존재를 확인하고, (2) 비대화형(no-TTY) 조건에서 1회 실행해 프롬프트 대기·exit code를 확인한다. 두 검증 전에는 해당 호출을 기본 경로로 승격하지 않는다.
- **근거**: portmanagement `.agent-memory/CORE.md:99-106,140-149`; Claude/Codex 실행 이력
<!-- provenance: candidate=btw-provenance-db03bdb2aa3aa12f423113db; memory=884575df-63c4-407c-8b43-860d1295e663 -->

### 177. 화면 표시용 표현과 음성 낭독용 원고는 같은 의미의 별도 필드로 모델링한다 (2026-07-26)
<!-- tier: principle -->
- **상황**: 수식을 화면에 렌더링하면서 같은 문자열을 TTS 낭독에도 그대로 넘겼다.
- **발견**: 표시용 표기(수식 기호, 약물, 마크업)와 낭독용 원고는 같은 의미를 담지만 요구 형태가 다르다. 하나의 문자열로 둘을 겸하면 어느 한쪽이 반드시 열화되고, 낭독 품질 개선이 화면 표기를 훼손하는 결합이 생긴다.
- **교훈**: 표시 표현과 낭독 원고를 타입 수준에서 별도 필드로 분리하고 각각 독립적으로 개선한다. 접근성·음성 출력이 붙는 모든 콘텐츠 타입에 적용되는 일반 패턴이다.
- **근거**: final-study-web `content/types.ts:8-10,62-63`, `README.md:88-97`; `CORE.md:33-40` (gimal)
<!-- provenance: candidate=btw-provenance-9bff7158289f1b218ff123c5 -->
