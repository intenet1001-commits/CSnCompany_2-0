# knowledge/deployment — 배포 (Vercel/Vite 빌드설정·CDN)

cs-experiencing 오케스트레이터 SKILL.md에서 이관된 프로젝트-특화 학습.
번호는 전역 INDEX(skills/experiencing/SKILL.md) 번호를 유지한다. 신규 항목은 INDEX의 max+1 번호를 부여받아 이 파일 끝에 추가된다.
cs-end Forget Gate(Phase 2.5)가 이 파일의 `<!-- tier: tactical -->` 항목도 30일 decay 스캔 대상으로 포함한다.

### 23. 배포 웹 UI 버그는 빌드 설정 먼저 확인 — `vercel.json` / `vite.*.config.ts` 추적 (2026-05-17)
<!-- tier: principle -->
- **상황**: 사용자가 모바일/Vercel에서 UI 변경이 안 보인다고 보고. App.tsx에 모바일 반응형/Quick Add 모달/큰 수정 버튼을 4커밋(058ca39, e14cc01, 34a8fae, b9170d8) 푸시했지만 Vercel에 전혀 반영 안 됨.
- **발견**: `vercel.json`에 `"buildCommand": "npx vite build --config vite.portal.config.ts"` 와 `rewrites: [{ source: "/(.*)", destination: "/portal.html" }]`. Vercel은 `portal.html` → `src/portal-main.tsx` → `PortsView` 컴포넌트만 빌드/서빙. `App.tsx`는 Tauri 전용 `index.html` 진입점. 4커밋이 잘못된 파일을 건드림.
- **교훈**: 배포 웹 UI 버그를 다루기 전에 `vercel.json`(또는 `netlify.toml`, `next.config.js`, `vite.config.*`)을 **먼저 읽어** (1) 실제 buildCommand, (2) HTML 진입점, (3) rewrite/routing 규칙을 확인. 진입 HTML → main TSX → 렌더 컴포넌트까지 추적. 멀티 진입(Tauri 데스크톱 + 웹 portal) repo는 데스크톱 entry와 웹 entry가 보통 다른 파일. 진단 신호: 로컬 dev/Tauri는 보이는데 deployed 웹은 안 보임 — 빌드 에러도 없음(잘못된 파일이 그대로 컴파일됐기 때문).

### 24. 멀티 entry Vite 프로젝트는 entry별 분리 모델 (2026-05-17)
<!-- tier: tactical -->
- **상황**: portmanagement repo는 `vite.config.ts`(Tauri, `index.html` → `App.tsx`)와 `vite.portal.config.ts`(Vercel, `portal.html` → `portal-main.tsx`) 두 개 보유. 같은 components 폴더지만 두 개의 독립 렌더 트리, 다른 feature set.
- **발견**: `PortsView`(portal-main.tsx 내)는 port-management UI의 슬림 재구현 — App.tsx와 JSX 공유 안 함. App.tsx 수정은 데스크톱만 영향. Vercel UI 변경하려면 portal-main.tsx 편집 필수.
- **교훈**: Vite 프로젝트에 config 파일이 여러 개면 각각을 독립 앱으로 취급. 대체 config의 `build.rollupOptions.input` 또는 `root`를 grep해서 진짜 진입점 확인. 공유 UI는 `src/shared/`로 추출 검토 — 단, 이미 돼 있다고 가정 금지.

### 56. vercel --prod는 Claude Code auto-mode에서 항상 차단됨 (2026-05-30)
<!-- tier: tactical -->
- **상황**: freeparking-1 프로젝트 배포를 위해 auto-mode 세션에서 `vercel --prod --yes`를 여러 차례 시도했으나 매번 안전 분류기에 차단되었다.
- **발견**: Claude Code auto-mode의 안전 분류기는 `vercel --prod`를 "프로덕션 외부 서비스 변경"으로 분류해 자동 차단한다. 이는 허용 목록이나 권한 설정으로 우회 불가능한 hard block이다.
- **교훈**: Vercel 프로덕션 배포는 반드시 사용자가 직접 실행해야 함. `! cd <project> && vercel --prod --yes` 형태로 Claude Code 프롬프트에서 직접 실행하거나 별도 터미널 사용. 에이전트 세션에서 자동화 불가 — 세션 마무리 시 항상 사용자에게 배포 명령을 전달할 것.

### 67. 배포 직후 화면 깨짐 — Vercel CDN 번들 mismatch artifact (2026-06-09)
<!-- tier: tactical -->
- **상황**: Next.js 프로젝트를 `npx vercel --prod`로 배포 후 사용자가 카드 배경이 사라진 "깨진 화면" 보고. tsc + npm run build 모두 오류 없음.
- **발견**: HTML과 CSS 번들이 CDN 전파 타이밍에 따라 일시적으로 불일치할 수 있음. 새 배포는 content-addressed CSS 파일명을 사용하므로 재배포 시 강제로 새 번들 로딩됨.
- **교훈**: 빌드/타입 검사가 통과하는데도 배포 후 시각적 버그가 생기면 CDN artifact를 먼저 의심하고 `npx vercel --prod` 재배포로 빠르게 확인할 것.
