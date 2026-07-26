# knowledge/data-sync-db — 데이터 동기화·DB·타임존

cs-experiencing 오케스트레이터 SKILL.md에서 이관된 프로젝트-특화 학습.
번호는 전역 INDEX(skills/experiencing/SKILL.md) 번호를 유지한다. 신규 항목은 INDEX의 max+1 번호를 부여받아 이 파일 끝에 추가된다.
cs-end Forget Gate(Phase 2.5)가 이 파일의 `<!-- tier: tactical -->` 항목도 30일 decay 스캔 대상으로 포함한다.

### 20. Pull merge: 동일 폴더 다른 ID 중복 방지 — 결정적 ID + folderPath dedup (2026-05-17)
<!-- tier: principle -->
- **상황**: Supabase Pull 시 같은 폴더가 여러 행으로 중복 나타남. `mergePorts`는 `id` 기준 dedup만 수행.
- **발견**: 기기/마이그레이션 경로에 따라 같은 폴더가 다른 ID로 저장되어 있었음. 두 가지 동시 적용으로 해결: (a) port가 없는 항목은 `folderPath`를 dedup 보조키로 추가, (b) 마이그레이션 시 ID를 `path hash`로 결정적으로 생성 → 모든 기기가 동일 폴더에 대해 동일 ID 산출.
- **교훈**: 분산/멀티기기 동기화에서 경로가 동일 identity namespace 안에서 안정적일 때는 `folderPath` 같은 natural key를 dedup 보조키로 사용하고, 마이그레이션의 deterministic hash(path)로 idempotency를 확보할 수 있다. 경로 자체가 기기마다 달라지는 객체에는 이 규칙을 그대로 적용하지 않는다.
- **추가 (2026-07-26, 범위 수정)**: 기기마다 path/port가 달라질 수 있는 논리 객체는 portable config에 opaque stable UUID를 보존하고 path/port는 mutable locator로 취급한다. Pull/restore는 원격 lineage의 UUID를 채택해야 한다. 다만 현재 관찰된 구현은 로컬에서 먼저 새 UUID로 초기화하면 기존 원격 lineage 탐색을 막을 수 있어, 이 원칙이 모든 신규 기기 경로에서 완결됐다고 보지는 않는다.
<!-- provenance: candidate=btw-provenance-c62accb589be42fa4d21d469; run=9eed3fbd-5a8b-4a10-91ff-32dd357c4cdc; memory=884575df-63c4-407c-8b43-860d1295e663; range=git:8b4bc0ae03bf556eebe0a76f694c7f7a950d4fc7..beecbff7a96de131a08553d4e195c90d036c84b7;dirty:9c216341282624b328db07058c32ca6cad3d7f0176f0426aa70ebb575f49de6a;truncated=true -->

### 21. Merge 전략: 사용자 직접 편집 필드는 local-first (2026-05-17)
<!-- tier: principle -->
- **상황**: Pull 직후 방금 편집한 `deployUrl`이 stale 원격 값으로 덮어써짐. `mergePorts`가 `{ ...local, ...remote }` 단순 스프레드 사용.
- **발견**: `folderPath`/`commandPath`는 이미 local-first였으나 사용자 직접 입력 필드(`deployUrl`, `githubUrl`, `description`)는 누락. 같은 local-first 규칙 적용으로 해결.
- **교훈**: 동기화 merge에서 "사용자가 UI로 직접 입력하는 필드"와 "시스템 자동 계산 필드"를 구분. 전자는 항상 local-first(원격이 빈 값일 때만 채움). 새 사용자 편집 필드 추가할 때마다 merge 정책 재검토 필수.
- **추가 (2026-07-26)**: local-first는 merge precedence와 durability write-order를 구분한다. 전자는 사용자 편집값을 로컬 우선으로 유지하고, 후자는 authoritative local copy를 먼저 원자적으로 저장한 뒤 remote revision을 best-effort로 시도한다. 두 결과를 따로 보고하며 remote 실패·충돌은 local 성공을 rollback하지 않는다. divergence는 conflict로 반환하고, 별도의 명시적 force에서만 덮어쓴다.
<!-- provenance: candidate=btw-provenance-462aa8508e41bd0114f3b510; run=9eed3fbd-5a8b-4a10-91ff-32dd357c4cdc; memory=884575df-63c4-407c-8b43-860d1295e663; range=git:8b4bc0ae03bf556eebe0a76f694c7f7a950d4fc7..beecbff7a96de131a08553d4e195c90d036c84b7;dirty:9c216341282624b328db07058c32ca6cad3d7f0176f0426aa70ebb575f49de6a;truncated=true -->

### 33. 단일 레코드 반복 태스크의 done 리셋 패턴 (2026-05-22)
<!-- tier: principle -->
- **상황**: myschedule 앱에서 반복 태스크(daily/weekly)는 DB에 레코드 1개만 존재한다. done=true로 마킹 후 다음 날 앱에 진입하면 완료된 것처럼 보여 새 주기에 태스크가 뜨지 않는 문제 발생.
- **발견**: 앱 진입 시 `loadTasks`에서 `t.recurring && t.done && localISO(new Date(t.done_at)) !== todayISO()` 조건으로 이전 날 완료된 반복 태스크를 탐지하고, 일괄 `done=false, done_at=null` UPDATE 후 메모리 상태도 동기 반영. `data = data.map(t => ids.includes(t.id) ? { ...t, done: false, done_at: null } : t)`
- **교훈**: 단일 레코드 반복 패턴에서 '완료' 상태는 영구가 아닌 일시적이다. 리셋 로직은 데이터 로드 시점(앱 진입)에 배치해야 서버와 클라이언트 상태를 일관되게 유지할 수 있다. done_at 비교는 반드시 `localISO()`로 타임존 변환 후 수행 (UTC timestamptz vs 로컬 날짜 불일치 방지).

### 35. done_at UTC timestamptz → 로컬 날짜 변환 비교 (2026-05-22)
<!-- tier: tactical -->
- **상황**: Supabase에서 done_at을 timestamptz(UTC)로 저장한다. 자정 이후 `done_at`을 단순 `.slice(0,10)`으로 자르면 UTC 기준 날짜가 반환되어 한국 시간(UTC+9)과 불일치 발생 가능.
- **발견**: `localISO(new Date(t.done_at)) !== todayISO()` 패턴 사용. `localISO()`는 `new Date()`를 로컬 타임존 기준으로 YYYY-MM-DD 형식으로 변환. `todayISO()`도 동일 방식. 양쪽을 모두 로컬 기준으로 변환한 후 비교해야 자정 경계 버그 없음.
- **교훈**: timestamptz 컬럼을 날짜 단위로 비교할 때는 항상 클라이언트 로컬 타임존 기준으로 변환해야 한다. 서버 저장은 UTC, 비교는 로컬이라는 원칙. `slice(0,10)` 방식은 UTC 기준이므로 UTC+9 환경에서 자정~09:00 사이 비교 시 오동작.

### 53. fp_logs 복원 시 failed 상태는 silent drop — stale 실패 기록을 오류 배지로 부활 금지 (2026-05-30)
<!-- tier: principle -->
- **상황**: freeparking-1 앱의 loadLastStatus에서 fp_logs의 failed 행을 "error" 상태로 매핑했다. 그 결과 어젯밤 "종일권 잔여 매수 없음"으로 실패했던 차량들이 새로고침 후에도 빨간 "오류" 배지로 표시돼 사용자가 현재 시스템 오류라고 혼동했다.
- **발견**: 로그 DB에서 UI 상태를 복원할 때 terminal failure(등록 실패, 할당량 없음 등)는 현재 상태가 아니다. `continue`로 skip하면 해당 차량에 배지가 뜨지 않아 실제 현황조회 결과가 나올 때까지 중립 상태를 유지한다.
- **교훈**: 로그 기반 상태 복원 시 'failed/error' 구분 필수 — `failed`(사용자 등록 실패)는 skip, `error`(시스템 오류)만 surface. 과거 실패를 현재 오류로 보여주는 것은 UX 노이즈이자 혼란의 원인.

### 55. 시스템 공통 데이터는 임의 대표 엔트리에서 읽어도 안전 (2026-05-30)
<!-- tier: tactical -->
- **상황**: AJPark 주차 시스템의 잔여 매수(quotaAllDay/quotaHourly)는 차량별이 아니라 시스템 전체 공통값이다. statusMap에 차량별 엔트리가 있는데 어느 차량의 quota를 보여줄지 결정해야 했다.
- **발견**: 실시간 조회(isLast=false) 엔트리 중 첫 번째에서 quota를 읽으면 충분하다. 시스템 공통 필드는 어느 차량 엔트리든 동일한 값을 가지므로 대표 엔트리 1개가 전체를 대표한다.
- **교훈**: 필드가 per-entity가 아니라 system-wide인 경우, `Object.values(map).find(st => condition)?.field` 패턴으로 첫 번째 해당 엔트리를 읽는 게 루프/집계보다 간단하고 충분하다.

### 57. content 컬럼 센티넬 접두사로 스키마 마이그레이션 없이 새 콘텐츠 타입 추가 (2026-05-30)
<!-- tier: principle -->
- **상황**: 기존 `meokgo_chat_messages.content TEXT` 컬럼만 있는 채팅 테이블에 스티커 기능을 추가해야 했음. DB 컬럼 추가 시 RLS 정책 업데이트 + Realtime 스키마 리프레시 필요.
- **발견**: `content`에 `:sticker:🎂` 센티넬 접두사로 저장하면 DB/RLS/Realtime 파이프라인을 전혀 건드리지 않아도 됨. `isSticker()` 한 줄 + 렌더 분기만 추가로 구현 완료.
- **교훈**: 새 콘텐츠 타입이 "여전히 문자열이고 메시지당 하나"인 경우 센티넬 접두사로 기존 컬럼을 재사용한다. 컬럼 추가는 진짜 직교적 데이터(외래키·숫자·boolean 플래그)일 때만 사용.

### 77. fp_logs unique index를 분산 뮤텍스로 활용 — Redis 없이 serverless 하루 1회 실행 보장 (2026-06-14)
<!-- tier: principle -->
- **상황**: freeparking-1 크론이 GitHub Actions workflow_dispatch(수동) + schedule(자동)에서 동시에 실행될 경우 같은 차량에 중복 등록이 발생할 수 있었다. Redis/Upstash 등 외부 lock store는 없었다.
- **발견**: `fp_logs` 테이블에 `CREATE UNIQUE INDEX fp_logs_cron_lock_date ON fp_logs (plate, (created_at::date)) WHERE plate = '__cron_lock__'`를 만들면, `INSERT { plate: '__cron_lock__' }` 자체가 atomic lock acquisition이 된다. 두 번째 호출은 unique constraint violation으로 즉시 409 반환. `finally` 블록에서 `UPDATE status='done'`으로 audit trail 유지(DELETE 대신).
- **교훈**: "하루 1회 실행 보장"이 필요한 serverless job에서 외부 lock store가 없을 때, conditional unique index + sentinel row INSERT = 분산 뮤텍스의 가장 저렴한 구현. `finally`에서 delete 대신 status update를 사용해야 해당 날의 실행 이력(run_id, 시각)이 남는다.
- **근거**: `app/api/cron/auto-register/route.ts` L77-79 DDL 주석 + L83-91 insert-as-lock + L219-226 finally update

### 86. 세그먼트별 컬럼 있을 때 전체 합계 fallback은 세그먼트값 NULL 조건에만 (2026-06-17)
<!-- tier: principle -->

- **상황**: 퍼널 D8 체결완료 카드가 신규고객(M0) 선택 시 전체 거래고객수(312,218)를 표시. D5(22,851)보다 큰 비정상 값으로 발현.
- **발견**: 버그 원인: `rollingTraderTotal`(mau_transaction_rolling.total_cus_cnt = 전체 합계)을 cus_type 분기 없이 모든 케이스에 적용. `funnel_rolling.total_ose_trd_cus_cnt`는 cus_type별로 분리된 실제 값을 가짐. DB에 세그먼트별 컬럼과 전체 합계 컬럼이 공존할 때, 전체 합계를 기본값으로 쓰면 세그먼트 모드에서 전체값이 세그먼트값을 무음으로 대체한다.
- **교훈**: 세그먼트(cus_type)별로 분리된 컬럼이 있을 때, 전체 합계 fallback은 세그먼트별 값이 NULL인 경우에만 적용한다. `segmentCol ?? aggregateFallback` 패턴이 정준(canonical) 형태. 어떤 스택에서도 "세그먼트 컬럼 우선, 전체 합계는 마지막 fallback" 원칙이 적용된다.
- **근거**: Before: `val: (period === 'rolling' ? rollingTraderTotal : ...)` → 신규고객 D8=312,218 / After: `val: (d.d8_total_uv ?? (period === 'rolling' ? rollingTraderTotal : ...))` → 신규고객 D8=1,829 (app/mau/page.tsx line 3433, 2026-06-17)

### 98. 웹·앱이 같은 머신에서 동시 접근하는 상태는 localStorage 대신 공유 파일 + 이중 접근 경로로 관리한다 (2026-07-09)
<!-- tier: tactical -->

- **상황**: Tauri 앱(포트 관리 프로그램)에 "마지막 방문 시각" 라벨을 추가했는데, 사용자가 웹 브라우저 탭과 데스크톱 앱을 같이 써도 값이 같이 관리돼야 한다고 지적.
- **발견**: `localStorage`는 브라우저 오리진/Tauri webview별로 완전히 분리된 저장소라 웹에서 기록한 값이 앱에서 보이지 않고 그 반대도 마찬가지다. 이 프로젝트가 주 데이터(`ports.json`)에 이미 쓰던 패턴 — 앱 데이터 디렉토리의 공유 JSON 파일을 웹은 HTTP 엔드포인트(Bun api-server)로, 데스크톱 앱은 Tauri `invoke` 커맨드로 각각 읽고 쓰는 이중 접근 경로 — 를 그대로 적용해 해결했다. 동시 기록 충돌은 "더 최신 타임스탬프만 반영"으로 단순 해결 가능.
- **교훈**: 웹+데스크톱을 동시 지원하는 앱에서 여러 실행 표면(브라우저 탭, 웹뷰)이 공유해야 하는 새 상태를 추가할 때는 `localStorage`를 기본값으로 쓰지 말고, 처음부터 "공유 파일 + (HTTP 엔드포인트, 네이티브 invoke 커맨드) 이중 접근" 패턴을 채택한다. 이는 이 앱만의 관례가 아니라 하나의 머신에서 여러 JS 런타임(브라우저 vs 웹뷰)이 상태를 공유해야 하는 모든 dual-surface 앱에 적용되는 일반 원칙이다 — 구체적 저장 형식(JSON 파일 vs sqlite vs IPC)은 프로젝트마다 다를 수 있다 (skeptic verifier: 저장 형식 자체는 project-specific이라 tactical로 판정, 다만 "동일 머신 내 분리된 JS 런타임은 localStorage를 공유하지 않는다"는 근본 사실 자체는 안정적).
- **근거**: `last-visits.json`을 `~/Library/Application Support/com.portmanager.portmanager/`에 신설, `POST /api/last-visits`(웹) + `save_last_visit` Tauri invoke(앱) 양쪽 구현 → 브라우저에서 실행한 포트가 앱에서도 동일한 "마지막 실행" 시각으로 표시됨 확인 (2026-07-09 세션, PR #4)
- **추가 (2026-07-26)**: 여러 runtime/agent가 소비하지만 host `PortInfo` lifecycle과 독립적인 project-scoped state는 host mega DTO에 편입하기보다 project-local canonical document와 작은 config로 둘 수 있다. runtime별 adapter/bridge는 projection이며 authority가 아니고 marker/version과 idempotent upgrader로 갱신한다. 이번 관찰의 localhost bridge는 local dev/API-server에서만 검증됐고 packaged Tauri에는 backend 번들·기동이 빠져 있으므로 cross-runtime 완성으로 일반화하지 않는다.
<!-- provenance: candidate=btw-provenance-085ef3d96d757c84af6e55fd; run=9eed3fbd-5a8b-4a10-91ff-32dd357c4cdc; memory=884575df-63c4-407c-8b43-860d1295e663; range=git:8b4bc0ae03bf556eebe0a76f694c7f7a950d4fc7..beecbff7a96de131a08553d4e195c90d036c84b7;dirty:9c216341282624b328db07058c32ca6cad3d7f0176f0426aa70ebb575f49de6a;truncated=true -->
