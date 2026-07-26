# 다운로드 파이프라인 학습

### 158. yt-dlp --cookies-from-browser는 프로필 미지정 시 여러 Chrome 프로필 중 무작위로 선택한다 — Local State JSON으로 폴더명↔표시이름 매핑 필요 (2026-07-22)
<!-- tier: tactical -->

- **상황**: 외부 프로젝트(easyconversion_web1)의 YouTube 다운로드 탭에 쿠키 인증 기능을 추가하던 중, 같은 코드·같은 요청인데도 실행마다 성공/실패가 들쭉날쭉한 버그를 디버깅했다.
- **발견**: yt-dlp에 `--cookies-from-browser <browser>`만 주면(프로필 미지정) 여러 Chrome 프로필이 동시에 열려있을 때 매 실행마다 다른 프로필을 무작위로 골랐다. 원인 중 하나는 `chrome://version` 표시 이름("chunsung")과 yt-dlp가 요구하는 실제 폴더명("Profile 1")이 달라 사용자가 표시 이름을 그대로 입력한 것. Chrome의 `Local State` JSON(`profile.info_cache`)을 읽으면 폴더명↔표시이름 매핑을 정확히 얻을 수 있어, UI를 자유입력 대신 드롭다운으로 바꿔 해결했다.
- **교훈**: 브라우저 프로필을 이름으로 지정하는 CLI 옵션은 반드시 프로필까지 명시해야 하며, 표시 이름이 아니라 브라우저의 내부 상태 파일(Local State 등)에서 얻은 실제 폴더명을 써야 한다. 자유입력 필드는 이런 이름 불일치 버그의 근원이므로 검증된 값만 고를 수 있는 드롭다운으로 대체하는 게 안전하다.
- **근거**: 실측 — `/Users/gwanli/Library/Application Support/Google/Chrome/Local State`의 `profile.info_cache["Profile 1"].name == "chunsung"`, 폴더명은 `Profile 1`. 프로필 비워두고 반복 실행 시 쿠키 개수가 2930개(다른 프로필)와 3189개(Profile 1)로 왔다갔다 함을 확인.

### 159. yt-dlp 쿠키 인증 시 로그인 가능한 클라이언트(tv/web)로 전환되며 JS 런타임 + --remote-components ejs:github 둘 다 필요 (2026-07-22)
<!-- tier: tactical -->

- **상황**: yt-dlp 쿠키 인증 다운로드가 계속 "Requested format is not available"로 실패하는 것을 디버깅했다 (일반 공개 영상까지 실패).
- **발견**: yt-dlp가 쿠키를 붙이면 로그인 미지원 클라이언트(android_vr 등, 서명챌린지 불필요)를 건너뛰고 로그인 가능한 tv/web 클라이언트로 전환하는데, 이 클라이언트들은 YouTube의 n-challenge(서명 해독)를 풀 JS 런타임이 필요했다. `deno` 설치만으로는 부족했고 `--remote-components ejs:github` 옵션까지 줘야 실제 챌린지 솔버 스크립트를 받아와서 동작했다.
- **교훈**: 도구가 인증 상태에 따라 내부적으로 다른 실행 경로(클라이언트)로 전환할 수 있으며, 그 경로는 별도의 숨은 의존성(JS 런타임 + 원격 컴포넌트)을 요구할 수 있다. 인증 관련 실패는 단일 원인이 아니라 복수 전제조건의 조합으로 봐야 한다.
- **근거**: `deno --version` 설치 확인 후에도 동일 에러 재현 → `-v --list-formats`로 `WARNING: [youtube] [jsc] Remote components challenge solver script (deno) and NPM package (deno) were skipped... --remote-components ejs:github` 확인 → 해당 플래그 추가 후 포맷 목록 정상 반환.

### 160. Radix ScrollArea의 display:table 내부 래퍼는 자식의 truncate를 무력화한다 — w-px min-w-full로 강제 필요 (2026-07-22)
<!-- tier: tactical -->
<!-- skeptic verifier DOWNGRADE from principle: "Radix 내부 구현(display:table)에 의존하는 지식이라 공개 API 계약이 아님. min-width>width CSS 스펙 자체는 안정적이나 실측이 특정 버전 조합에서만 검증됨" -->

- **상황**: Radix UI ScrollArea 안에서 파일명 텍스트가 truncate(ellipsis) 돼야 하는데 오른쪽이 잘려 보이는 레이아웃 버그를 디버깅했다.
- **발견**: ScrollArea는 내부적으로 `display: table` 래퍼 div(`min-width: 100%; display: table;`)를 쓰는데, 이 레이아웃은 자식의 "줄바꿈 없는 원본 크기" 기준으로 폭을 계산해 truncate(overflow:hidden+ellipsis+nowrap)를 무력화시켰다. `w-full`만으로는 해결이 안 됐고, `w-px min-w-full`(width:1px + min-width:100%, CSS 스펙상 min-width가 width보다 우선순위 높음을 이용) 조합을 자식 콘텐츠 div에 줘야 정확히 부모 폭으로 강제됐다.
- **교훈**: display:table 기반 레이아웃(Radix ScrollArea 포함)에서 truncate가 안 먹히면, w-full이 아니라 width:1px + min-width:100% 트릭이 필요할 수 있다. 또한 이런 레이아웃 버그는 육안 스크린샷 추측(스크롤바 겹침, padding 부족 등 이번에도 두 차례 오판)보다, 브라우저 자동화 도구로 `getBoundingClientRect()`/`scrollWidth`를 직접 측정해 확인하는 것이 훨씬 빠르고 정확했다.
- **근거**: 실측 — 수정 전 `{"vpWidth": 582, "wrapperWidth": 757.3, "mineScrollWidth": 757}`, `w-px min-w-full` 적용 후 `{"vpWidth": 582, "wrapperWidth": 582, "mineScrollWidth": 582}`.

### 161. 파일명에 '#' 포함 시 인코딩 없이 URL에 넣으면 브라우저가 프래그먼트로 해석해 요청 경로가 잘려 404 (2026-07-22)
<!-- tier: tactical -->

- **상황**: 강좌 회차 번호("#23." 등)가 포함된 파일명만 골라서 다운로드가 404로 실패하는 버그를 디버깅했다.
- **발견**: 파일명에 `#`이 포함된 상태로 서버가 만든 URL을 인코딩 없이 `/downloads/{session}/{filename}`에 넣어 내려주면, 브라우저의 fetch/URL 파서가 `#` 이후를 URL 프래그먼트로 해석해 요청 경로에서 잘라버려 실제 존재하는 파일도 404가 났다. `#`이 없는 파일명은 정상 동작하고 `#` 포함 파일명만 실패하는 패턴이 특징적 시그니처였다. 서버에서 `encodeURIComponent`로 경로를 인코딩해서 내려주고, 삭제 등 그 경로를 다시 받는 API에서는 `decodeURIComponent`로 되돌려 해결했다.
- **교훈**: 사용자 생성 파일명을 그대로 URL 경로에 넣을 때는 반드시 `encodeURIComponent`를 거쳐야 하며, 특히 `#`(프래그먼트)·`?`(쿼리) 같은 URL 예약 문자가 포함될 수 있는 입력은 특별히 취약하다. "특정 문자를 포함한 항목만 골라서 실패"하는 패턴은 URL 예약 문자 인코딩 누락을 의심하는 신호다.
- **근거**: `#` 없는 파일명은 "선택 다운로드"가 전부 성공, `#` 포함 파일명만 `HTTP 404` (lib/download.ts:4 `throw new Error('HTTP ' + response.status)`) → `encodeURIComponent`/`decodeURIComponent` 왕복 추가 후 전부 성공.

### 162. for 루프 순차 처리에서 아이템별 try/catch 없으면 하나만 실패해도 나머지 전체가 스킵된다 (2026-07-22)
<!-- tier: tactical -->

- **상황**: 재생목록 일괄 다운로드/저장 기능에서 "N개 중 일부만 처리됐다"는 애매한 사용자 보고를 두 차례(다른 기능에서) 조사했다.
- **발견**: `for (const item of items) { await doSomething(item) }` 형태에서 개별 아이템에 try/catch가 없으면, 42개 중 하나만 실패해도 그 지점에서 루프 전체가 멈춰버려 나머지가 통째로 스킵된다.
- **교훈**: 일괄 처리 루프에서 await를 쓸 때는 각 아이템을 try/catch로 감싸 개별 실패가 나머지 처리를 막지 않도록 해야 한다. "N개 중 일부만 처리됨" 버그 보고를 받으면 루프 중단 여부부터 의심한다.
- **근거**: `ProjectFilesDialog.tsx`의 `downloadSelected` 반복문에 try/catch 없음 확인 → 개별 try/catch + 성공/실패 카운트 추가 후 "몇 개 중 몇 개 성공" 정상 보고로 재현 종료.

### 163. Electron fetch+blob 다운로드에서 revokeObjectURL을 너무 빨리 호출하면 큰 파일에서 실패 — 서버가 이미 로컬 저장한 파일은 blob 재다운로드 자체가 불필요 (2026-07-22)
<!-- tier: tactical -->

- **상황**: Electron 데스크톱 앱에서 서버가 다운로드한 결과 파일을 사용자에게 전달하는 기능을 구현/디버깅했다.
- **발견**: 브라우저 fetch+blob(`URL.createObjectURL` → 앵커 클릭 → `URL.revokeObjectURL`) 방식으로 파일을 "다운로드"시킬 때, revoke를 너무 빨리(1초) 하면 큰 파일(수십MB 영상)에서 다운로드 매니저가 blob을 다 읽어가기 전에 참조가 사라져 "File wasn't available on site" 에러가 났다. 더 근본적으로는, 서버(Node)가 이미 로컬 디스크에 파일을 저장해둔 Electron 앱에서는 이 브라우저 blob "재다운로드" 단계 자체가 불필요했다 — `exec('open', folderPath)` 같은 네이티브 폴더 열기가 훨씬 안정적이었다.
- **교훈**: blob URL을 즉시 revoke하면 큰 파일일수록 레이스 컨디션으로 실패할 수 있다(임시방편이면 지연을 넉넉히 늘릴 것). 더 근본적으로, Electron처럼 서버와 클라이언트가 같은 파일시스템을 공유하는 데스크톱 앱에서는 브라우저의 blob "재다운로드" 우회 자체를 없애고 네이티브 파일시스템 API(폴더 열기 등)로 대체하는 게 더 안정적인 설계다.
- **근거**: revoke 지연 1000ms → 60000ms로 늘려도 재발 가능성 있어, 결국 fetch+blob 호출 자체를 제거하고 `/api/open-folder`(기존에 다른 다이얼로그가 쓰던 `exec('open', ...)` 방식)로 대체 후 문제 재발 없음.

### 165. 배치 TTS 자막 경계는 글자수 추정이 아니라 문장별 합성 오디오의 실측 길이를 누적해 생성한다 (2026-07-26)
<!-- tier: tactical -->
<!-- provenance: candidate=btw-provenance-daa1f54e70fe34717fdcb4db; run=8388c4ae-0c29-40c0-9a9b-849e524ca316; memory=94de0f94-73ec-43df-8dc0-dedf3a1749c9; range=git:4093de09c0d28a4179cade33b33a31d7720e6fef;untracked:69cb1e5d01ff8ab76b809dc2cdce0d9080236890736201386271c01db354138a;linked:042a2dbe011b5e6a24c8b2b043025251ef5ad022..7abbdfb4d96b82c2f65d0103d6d6ea10e9fbeba7;linked-dirty:69e2f0fad485c2aa8ccfa4201492f5059926fe7e1f149c03e50e1cd395cb64c0;linked-untracked:1e2f40714ed05c5164777b4d00acb3de6a88bd9abe8f2055527acaf5a332e160;truncated=true -->

- **상황**: 여러 문장을 별도 TTS chunk로 합성한 뒤 하나의 오디오와 SRT/VTT 자막으로 묶는 배치 파이프라인을 검토했다.
- **발견**: 글자수나 고정 발화율로 구간을 추정하면 voice·문장부호·합성 결과에 따라 drift가 누적된다. 각 생성 media의 authoritative timing(`ffprobe` duration 또는 engine timing event)을 읽어 `start_i = sum(previous durations)`, `end_i = start_i + d_i`로 같은 segment list를 만들면 오디오 concat과 자막이 한 기준을 공유한다.
- **교훈**: concat/re-encode/삽입 silence가 있으면 그 의미와 같은 timing source를 사용하고 최종 audio/subtitle pair를 다시 검증한다. 포맷을 바꾸면 컨테이너별 duration이 미세하게 다를 수 있으므로 한 포맷의 수치를 다른 포맷에 완전 일치한다고 가정하지 않는다.
- **근거**: Learning 샘플에서 MP3 chunk `3.480 + 5.544 + 5.400 = 14.424s`, manifest/SRT/VTT 경계가 `0 → 3.480 → 9.024 → 14.424`, concat MP3도 `14.424s`로 일치했다. WAV는 `14.401958s`로 약 22ms 차이가 있었고, 현재 unit test는 hard-coded segment만 검사해 `ffprobe` integration은 아직 부채다.
