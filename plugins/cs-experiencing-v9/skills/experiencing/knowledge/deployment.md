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

### 75. GitHub Actions schedule cold-start trap — 파일이 없던 시각의 크론은 소급 발화하지 않는다 (2026-06-14)
<!-- tier: principle -->
- **상황**: freeparking-1의 `.github/workflows/weekly-parking.yml`을 일요일 당일(2026-06-14) 12시 이후에 main 브랜치에 푸시했다. 12시 KST 크론이 실행되지 않아 수기 처리가 필요했다.
- **발견**: GitHub Actions `schedule:` 트리거는 워크플로우 파일이 **이미 default branch에 존재해야** 인식된다. 12시 이후에 파일이 생겼으므로 그날 12시 발화는 처음부터 불가능했다. 소급 발화 없음, 에러·알림도 없음(단순히 조건 미충족).
- **교훈**: 새 `schedule:` 워크플로우를 배포한 직후에는 반드시 `workflow_dispatch`로 즉시 수동 실행 검증. 기존 스케줄러에서 마이그레이션할 때는 파일이 merge된 시점이 다음 발화 이전인지 확인하고, 확신이 없으면 한 사이클은 기존 스케줄러와 병행 운영.
- **근거**: `weekly-parking.yml` 커밋이 12:00 KST 이후 — 사용자 "오늘 오후 12시에 자동으로 주차등록이 안돼서 수기로 방금 처리했다" + ultracode 22-agent 분석 "오늘 실패 원인: 워크플로우 파일이 당일 12시 이후에 푸시됨 (타이밍 이슈)"
- **addendum (2026-07-19)**: cold-start(파일이 아직 없던 시각) 없이도, 이미 몇 주째 정상 동작 중인 `schedule:` 워크플로우가 특정 날 슬롯의 대부분을 그냥 드롭할 수 있음을 확인. `cron: '0 0-6 * * 0'`(KST 09-15시 매시 7회 시도 — "지연되면 다음 시간에 재시도"라는 가정으로 설계된 안전장치)인데, 실제로는 7회 중 2회(10:29, 14:00 KST)만 발화하고 나머지 5개 슬롯(09/11/12/13/15시)은 각 슬롯의 실행 가능 시간대가 완전히 지나도록 단 한 번도 발화하지 않음. "몇 분 늦게라도 결국 돈다"는 지연 가정이 아니라 "그날은 아예 안 돌 수도 있다"는 완전 누락 가정으로 설계해야 함 — 매시 재시도만으로는 나쁜 날(bad day)에 불충분하므로, 마지막 성공 실행 시각이 임계치를 넘으면 알림을 보내는 워치독이나 외부 cron 서비스발 `workflow_dispatch` 이중 트리거를 추가 검토 (skeptic verifier CONFIRMED — `gh run list --json ... | event=schedule` 재실행으로 2건만 존재 재확인).
- **근거(addendum)**: `gh run list --workflow=weekly-parking.yml --limit 50 --json databaseId,status,conclusion,createdAt,event` 결과를 2026-07-19로 필터링 → event="schedule" 레코드가 `createdAt: "2026-07-19T01:29:16Z"`, `"2026-07-19T05:00:14Z"` 2건뿐 (예상 7개 슬롯 UTC 00/01/02/03/04/05/06시 중 5개 없음), 재검증 시각 2026-07-19T07:23:23Z(16:23 KST) 기준 마지막 슬롯 실행 가능 시간대도 이미 지남

### 76. NEXT_PUBLIC_ anon key를 서버 전용 route에서 사용하면 RLS에 silently 차단된다 (2026-06-14)
<!-- tier: principle -->
<!-- error-ref: ERR-2026-07-03-001 -->
- **상황**: `app/api/cron/auto-register/route.ts`에서 `NEXT_PUBLIC_SUPABASE_ANON_KEY`로 Supabase 클라이언트를 생성했다. RLS가 활성화된 `fp_cars`/`fp_logs` 테이블을 읽고 insert했다.
- **발견**: `NEXT_PUBLIC_` 접두사는 "브라우저 안전 공개값" 신호다. anon key로 만든 클라이언트는 RLS 정책의 제약을 받아 쓰기 권한이 없거나 service role이 필요한 행을 읽지 못한다. 배포 에러 없이 HTTP 200이 오지만 실제 DB 작업이 실패하거나 빈 결과를 반환하는 silent failure.
- **교훈**: 서버 전용 route(API route, Server Action, cron)는 `SUPABASE_SERVICE_ROLE_KEY`로 `createClient()` 생성 필수. `NEXT_PUBLIC_` key는 클라이언트 브라우저 코드에서만 사용. lint rule로 서버 파일에 `NEXT_PUBLIC_SUPABASE_` 문자열을 금지하면 재발 방지.
- **근거**: `app/api/cron/auto-register/route.ts` L30-33 — `process.env.SUPABASE_SERVICE_ROLE_KEY!` + 주석 "서버 전용 route — anon key 대신 service role key 사용 (RLS 우회)"
- **addendum (2026-07-03)**: 같은 프로젝트(먹고공부하자) 내 서로 다른 파일에서 이 패턴이 두 번째로 재현됨. `app/api/bot-improve/route.ts`가 anon 클라이언트 + `void anonSupabase.update(...)`(fire-and-forget, unawaited)로 `improvement_status`를 쓰고 있었는데, API 응답은 "1개 오분류 감지" 성공을 보고했지만 DB 컬럼은 계속 null이었다 — RLS UPDATE 정책 부재로 조용히 거부됐기 때문. `getServerSupabase()`(service role) + `await`로 교체 후 `curl`로 실제 DB 반영 확인. **동시에 같은 코드베이스의 `app/api/bot-patterns/route.ts`도 동일한 anon+`void`+`.update()` 패턴을 그대로 갖고 있음을 발견 (아직 미수정)** — 이 항목이 이미 문서화돼 있었음에도 재발했다는 것 자체가 교훈: `void`로 감싼 Supabase write는 실패해도 아무 신호가 없으므로, "성공 응답 = 실제 반영"이라고 가정하지 말고 (1) write 성공이 중요한 모든 `.update()`/`.delete()`는 항상 `await`할 것, (2) 결과를 curl/DB 조회로 별도 검증할 것. lint rule 제안만으로는 재발을 막지 못했다 — 실제로 lint rule을 CI에 넣거나, 매 세션 종료 시 `grep -rn "void.*\.update(\|void.*\.delete("` 로 전체 API route를 스캔하는 게 더 신뢰할 수 있는 방어선이다.
- **근거(addendum)**: `app/api/bot-improve/route.ts:245,310-314,321-324` (fixed: awaited service-role update) / `app/api/bot-patterns/route.ts:8-14,99` (`void markResolvedLogs(pattern_regex);` — 여전히 anon+fire-and-forget, 미수정)
- **addendum (2026-07-26, 로컬 설치 저장소)**: anon key + RLS 비활성 조합을 "trusted local installation이니 괜찮다"로 두는 구성은 보안 설계가 아니라 **호환성 부채**다. 로컬 전용 동안은 동작하지만, 같은 프로젝트가 공유·다중 사용자·원격 노출로 넘어가는 순간 그대로 권한 없는 전면 접근이 된다. 노출 범위를 넓히기 **전에** authenticated RLS로 전환하고, 그 전까지는 해당 저장소를 신뢰 경계 안에서만 유지한다는 점을 문서에 명시한다. 검증: RLS를 켠 상태에서 anon 클라이언트가 실제로 거부되는지 확인한 뒤 전환을 완료로 본다.
- **근거(addendum 2026-07-26)**: portmanagement `.agent-memory/CORE.md:152-156`; `supabase/migrations/20260726000100_project_memory_revisions.sql:21` <!-- provenance: candidate=btw-provenance-7d574f9ef6b6224e51d1ee89; memory=884575df-63c4-407c-8b43-860d1295e663 -->

### 78. 멀티-phase 서버리스 함수는 phase 경계마다 wall-clock 예산 점검을 삽입한다 (2026-06-14)
<!-- tier: principle -->
- **상황**: freeparking-1 크론 route가 현황조회(phase 1) + 등록(phase 2) 순서로 최대 60s 안에 실행해야 했다. 조회 단계가 오래 걸리면 Vercel이 mid-flight kill해 fp_logs에 미기록 등록이 발생할 수 있었다.
- **발견**: `START_MS = Date.now()`, `BUDGET_MS = 45_000`(60s - 15s 마진) 상수를 선언하고 phase 2 진입 직전 `if (Date.now() - START_MS > BUDGET_MS - 15_000)` 체크로 조기 반환. 이렇게 하면 "등록은 됐는데 로그 없음" 상황 대신 structured partial response를 반환해 운영자가 상황을 파악할 수 있다.
- **교훈**: 서버리스 함수에 순차 단계와 hard deadline이 공존하면 phase 경계마다 `Date.now() - START_MS` 체크를 삽입하고 clean partial response를 반환하라. runtime kill보다 명시적 조기 반환이 fp_logs 일관성과 운영 가시성 모두에서 우월하다.
- **근거**: `app/api/cron/auto-register/route.ts` L26-27 `START_MS`, `BUDGET_MS = 45_000` + L155-164 budget 점검 조기 반환

### 79. curl에 --max-time 없이 GitHub Actions에서 hang 시 SIGKILL — 에러 원인 알 수 없음 (2026-06-14)
<!-- tier: tactical -->
- **상황**: 초기 `.github/workflows/weekly-parking.yml`의 curl이 `--max-time` 없이 Vercel 함수를 호출했다.
- **발견**: Vercel 함수가 hang하면 curl이 무한 대기하다 GitHub Actions의 `timeout-minutes` SIGKILL에 죽는다. 이 경우 curl exit code가 없어서 "Vercel가 응답 안 함" vs "Vercel가 에러 반환" vs "연결 불가"를 구분 불가. `--max-time 70 --connect-timeout 10`을 추가하면 curl이 exit code 28(timeout)로 명확히 종료.
- **교훈**: GitHub Actions에서 외부 서비스를 호출하는 curl에는 항상 `--max-time <fn_maxDuration + 10>` + `--connect-timeout 10`을 추가. `--max-time`이 job `timeout-minutes`보다 약간 짧아야 curl error body를 캡처할 수 있다.
- **근거**: `.github/workflows/weekly-parking.yml` L35-36 `--max-time 70 --connect-timeout 10` 수정

### 80. GitHub Actions run: 블록에서 secrets는 env: 블록으로 분리해야 shell injection을 방지한다 (2026-06-14)
<!-- tier: principle -->
- **상황**: `workflow.yml`의 `run:` 블록에서 `${{ secrets.CRON_SECRET }}`을 직접 쓰는 초안이 security hook에 의해 경고됨.
- **발견**: `${{ secrets.* }}`를 `run:` 문자열 내에 직접 보간하면 secret 값에 shell 메타문자가 포함될 경우 injection이 가능하다. `env:` 블록에서 환경변수로 바인딩하고 `${VAR_NAME}` 형태로 참조하면 서브프로세스에 값이 직접 전달되어 shell이 값을 파싱하지 않는다.
- **교훈**: GitHub Actions에서 secrets를 shell command에 넘길 때는 항상 `env:` 블록 바인딩 패턴 사용. lint rule: `run:` 블록 내 `${{ secrets.` 패턴은 곧 injection 위험 신호.
- **근거**: `.github/workflows/weekly-parking.yml` L15-17, L31-33 `env: CRON_SECRET: ${{ secrets.CRON_SECRET }}` + `run:` 내 `${CRON_SECRET}` 참조

### 90. Next.js API route의 준-정적 데이터는 모듈-레벨 TTL 캐시로 요청당 반복 DB 조회를 제거한다 (2026-07-03)
<!-- tier: principle -->
- **상황**: 팀 점심/커피 주문 챗봇(`app/api/bot-chat/route.ts`, `app/api/voice-order/route.ts`)의 응답이 느리다는 신고. 원인 분석 결과 모델 크기·토큰 상한 문제([87]번과 별개 원인)뿐 아니라, 요청마다 거의 안 바뀌는 데이터(메뉴 목록, 팀원 목록, 사이트 컨텍스트)를 매번 새로 Supabase에서 조회하고 있었다 — `voice-order`는 요청당 최대 3-4개 쿼리, `bot-chat`은 미분류 쿼리마다 4개 쿼리.
- **발견**: 서버리스 함수라도 warm instance 사이에는 모듈 스코프 변수가 유지된다. `let cache: {data, ts} | null` + `Date.now() - ts < TTL_MS` 체크만으로 별도 인프라(Redis 등) 없이 반복 조회를 제거할 수 있다. 데이터 성격에 맞춰 TTL을 다르게 줬다: 메뉴/팀원처럼 하루 중 거의 안 바뀌는 데이터는 5분, "오늘 팀 현황" 같은 좀 더 자주 바뀔 수 있는 요약 컨텍스트는 2분.
- **교훈**: Next.js API route(또는 임의의 서버리스 함수)에서 "요청마다 거의 동일한 결과가 나오는 DB 조회"를 발견하면, 먼저 모듈-레벨 `{data, ts}` + TTL 체크 캐시를 시도한다. 캐시 무효화 정책 설계보다 "몇 분 stale 해도 무방한가"만 판단하면 되므로 구현 비용이 매우 낮다. userId처럼 요청별로 달라지는 파라미터가 있으면 그 경로는 캐시를 우회시킨다 (예: `if (!userId && cache && ...)`).
- **근거**: `app/api/bot-chat/route.ts` — `siteContextCache`(2분 TTL) 추가 (git diff: `+let siteContextCache: { context: string; ts: number } | null = null;`); `app/api/voice-order/route.ts` — `teamCache`/`allMenusCache`(5분 TTL, `CACHE_TTL = 5 * 60 * 1000`) 추가해 `fetchCoffeeCandidates`/`fetchAllFoodMenus`/`fetchCandidates` 3개 함수를 단일 캐시 조회로 통합

### 85. minified 번들에서 배포 반영 검증은 property name / JS 패턴으로 (2026-06-17)
<!-- tier: tactical -->

- **상황**: Vercel에 코드 픽스가 반영됐는지 확인하기 위해 minified JS 번들에서 변경 흔적을 탐색해야 했음.
- **발견**: minified JS는 지역 변수명(rollingTraderTotal 등)을 단축 식별자로 치환하므로 원본 변수명으로 grep해도 검색 불가. 반면 객체 property name(`d8_total_uv`), 문자열 리터럴, 특징적인 연산자 패턴(`??` + 삼항 조합)은 minify 후에도 보존되어 배포 여부 판별 지표로 사용 가능.
- **교훈**: 배포 검증 시 변수명 대신 property name, 문자열 리터럴, 로직 패턴(??/삼항 조합)을 grep 대상으로 사용한다.
- **근거**: `rollingTraderTotal` grep → 검색 불가, `d8_total_uv` property name + `??` 패턴으로 Before/After 구분 성공 (page-7236727e66aef288.js, dash1-v2 세션 2026-06-17)

### 167. Loopback bind는 authorization이 아니다 — 민감한 로컬 API는 Origin 검증 + 설치별 capability + canonical root allowlist가 모두 필요하다 (2026-07-26)
<!-- tier: principle -->
- **상황**: 로컬 전용 API 서버를 `127.0.0.1`에 바인드하고, 그 사실만으로 접근 통제가 끝났다고 가정한 채 파일시스템을 건드리는 엔드포인트를 노출했다.
- **발견**: loopback bind가 막는 것은 원격 네트워크 도달성뿐이다. 같은 머신의 브라우저에서 열린 아무 웹페이지나 해당 포트로 요청을 보낼 수 있고(DNS rebinding·CSRF 포함), 같은 머신의 다른 프로세스도 자유롭게 호출한다.
- **교훈**: 민감한 로컬 API는 세 가지를 **모두** 요구한다 — (1) `Origin`/`Host` 검증으로 브라우저발 교차 출처 호출 차단, (2) 설치별 비밀 토큰/capability로 프로세스 신원 확인, (3) 경로 파라미터는 canonical하게 resolve한 뒤 등록된 root allowlist에 대조. 셋 중 하나라도 빠지면 "로컬이니 안전"은 성립하지 않는다. 검증: 브라우저 콘솔에서 교차 출처 `fetch`가 거부되는지, allowlist 밖 경로가 거부되는지 실제로 확인한다.
- **근거**: portmanagement `project-memory-server.ts:63-75`, `api-server.ts:848-867,934-1094`; `CORE.md:270-273`
<!-- provenance: candidate=btw-provenance-e8f843cfc3e75d86bbb5a28c; memory=884575df-63c4-407c-8b43-860d1295e663 -->

### 173. 체크인된 정책 SQL은 의도이고 배포 상태가 아니다 — 접근제어 시행은 라이브 프로브로만 확정된다 (2026-08-22)
<!-- tier: principle -->
- **상황**: 저장소에 RLS 정책 SQL과 마이그레이션이 들어 있어 "접근제어가 걸려 있다"고 간주한 상태에서, 실제 배포본을 클라이언트와 같은 등급의 anon key로 프로브했다.
- **발견**: 프로브 결과 대상 테이블이 읽기/쓰기 모두 열려 있었고 다른 동종 테이블도 읽혔다. 체크인된 SQL은 목표 상태를 서술할 뿐 배포된 데이터베이스의 시행 상태를 증명하지 않는다. 또한 포털·UI 측 이메일 필터링은 PostgREST 같은 직접 접근 경로를 전혀 제약하지 못한다.
- **교훈**: 접근제어(RLS·GRANT·row policy)를 "적용됨"으로 선언하기 전에 클라이언트가 쓰는 키 등급으로 라이브 엔드포인트를 직접 프로브하고, 동시에 인증된 앱 세션이 여전히 동작하는지 확인한다. 정책을 켜는 변경과 앱의 read/write 경로를 보존하는 변경은 분리된 두 작업이 아니라 하나의 변경이다. UI 계층 필터링을 시행 근거로 인정하지 않는다.
- **근거**: portmanagement 2026-08-11 anon-key 프로브 — `portmgr_ports` readable/writable, 기타 `portmgr_*` readable; memory entry `9cf62fbdd48820f80f8342f5@23e563c4ae1ce8de34bfba8c59d23fab`
<!-- provenance: candidate=btw-memory-4799e9d64c619bf2bda899bd; memory=884575df-63c4-407c-8b43-860d1295e663 -->
