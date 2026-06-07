---
name: CS-codebase-review
user-invocable: false
description: 5-agent parallel codebase review
version: 1.0.0
---

# CS-codebase-review 실행 프로토콜

## Phase 0 — Python Pre-Pass (선택적, 토큰 절감)

5-agent를 스폰하기 전에 Python 스크립트로 구조 데이터를 추출한다.
Python이 없으면 이 Phase를 건너뛰고 기존 방식(Read+Grep)으로 진행한다.

```bash
BASE="$HOME/.claude/plugins/marketplaces/CSnCompany_2-0/plugins"
export CSN_SHARED_DIR="$BASE/shared"
source "$CSN_SHARED_DIR/_bootstrap.sh" 2>/dev/null
TARGET_DIR="${1:-$PWD}"

if [ "$CSN_USE_PYTHON" = "true" ]; then
  # 파일 구조 + import 그래프 추출 (LLM Read 대체)
  SUMMARY=$(csn_run "extract_summary.py" "$TARGET_DIR" --depth 4)

  # TS interface ↔ Rust struct 필드 불일치 탐지 (노하우 #16 자동화)
  TS_RUST=$(csn_run "ts_rust_diff.py" "$TARGET_DIR")

  # 하드코딩 절대경로 탐지 (노하우 #15 자동화)
  ABSPATH=$(csn_run "abspath_check.py" "$TARGET_DIR")

  echo "📊 Python pre-pass 완료:"
  echo "$SUMMARY" | python3 -c "import sys,json; d=json.load(sys.stdin); print(f'  파일 {d[\"total_files\"]}개 | {d[\"total_lines\"]}줄 분석')" 2>/dev/null
  echo "$TS_RUST"  | python3 -c "import sys,json; d=json.load(sys.stdin); print(f'  TS↔Rust 불일치: {d[\"high_risk_count\"]}건 HIGH')" 2>/dev/null
  echo "$ABSPATH"  | python3 -c "import sys,json; d=json.load(sys.stdin); print(f'  절대경로: {d[\"high_risk\"]}건 HIGH')" 2>/dev/null
else
  SUMMARY='{"fallback":true}'
  TS_RUST='{"fallback":true}'
  ABSPATH='{"fallback":true}'
fi
```

## Phase 1 — 5-Agent 병렬 리뷰

각 에이전트에게 Python pre-pass 결과(JSON)를 컨텍스트로 전달한다.
`fallback:true`이면 에이전트가 직접 Read+Grep으로 분석한다.

**Agent 목록 (단일 블록 병렬 스폰):**

| Agent | 담당 | Python 결과 활용 |
|-------|------|----------------|
| architecture-reviewer | 의존성 구조, 레이어 분리 | SUMMARY (import 그래프) |
| quality-reviewer | 코드 품질, 복잡도 | SUMMARY (함수 목록, LoC) |
| security-reviewer | 취약점, 하드코딩 | ABSPATH (절대경로 hit) |
| performance-reviewer | 병목, 비효율 패턴 | SUMMARY (파일 크기, LoC) |
| maintainability-reviewer | 유지보수성, struct 동기화 | TS_RUST (필드 불일치) |

**각 에이전트 프롬프트 템플릿:**
```
당신은 [ROLE] 전문 리뷰어입니다.

## 대상 프로젝트
경로: [TARGET_DIR]

## Python Pre-Pass 결과 (결정론적 추출)
[SUMMARY / TS_RUST / ABSPATH JSON — fallback:true이면 직접 분석]

## 노하우 참고
[관련 SKILL.md 노하우 항목]

5점 척도(A~F)로 평가하고 우선순위별 수정사항을 제시하세요.
```

## Phase 2 — 종합 리포트

5개 에이전트 결과를 취합:
- 전체 등급 (A~F)
- 발견된 이슈 (HIGH/MEDIUM/LOW)
- 우선순위 상위 5개 액션 아이템
- Python 자동 탐지 이슈 (TS↔Rust, 절대경로) 별도 강조

---

# CS-codebase-review 노하우

### 1. Bun.spawn()에서 bare 'bash' ENOENT — 항상 /bin/bash 전체 경로 사용 (2026-04-24)

- **상황**: macOS에서 Bun.spawn() / spawn()으로 bash 명령을 실행 시 `ENOENT: no such file or directory, posix_spawn 'bash'` 에러 발생
- **발견**: Bun이 spawn할 때 PATH 환경변수가 없어 bare `bash`를 찾지 못함. 특히 api-server.ts가 Vite dev 서버 또는 Tauri에서 indirect하게 실행될 때 발생.
- **교훈**: `Bun.spawn()`/`spawn()` 커맨드 배열에는 항상 `"/bin/bash"` 전체 경로 사용. WSL 관련 spawn(`bash -c bashCmd`)은 예외 — Windows CMD에서 WSL로 넘기는 경우라 그대로 둬도 됨.

### 2. macOS 폴더 선택 다이얼로그 — 숨은 폴더 표시 + 상대 경로 자동 확장 (2026-04-24)

- **상황**: 프로젝트 폴더 열기에서 `.claude/...` 경로가 열리지 않음. Finder 다이얼로그에서 dot 폴더(.git, .claude 등)도 안 보임.
- **발견**: (1) AppleScript `choose folder`에 `invisibles shown true` 옵션 추가하면 숨은 폴더 표시. (2) open-folder API에서 `~`로 시작하거나 `/`로 시작하지 않는 경로는 `HOME + '/' + path`로 자동 확장하면 `.claude/`, `~/` 같은 편의 경로 모두 처리 가능.
- **교훈**: macOS 폴더 관련 API 구현 시 두 패턴 세트를 함께 적용. 입력 경로 정규화는 API 진입점에서 처리해야 클라이언트 측 버그를 방지할 수 있음.

### 3. AJPark 세션 기반 HTTP 자동화: form action 파싱 + manual redirect + Base64 인코딩 (2026-04-26)

- **상황**: JS onClick으로 form submit하는 레거시 파킹 시스템(AJPark)을 Playwright 없이 plain fetch로 자동화
- **발견**: form action에 jsessionid 포함(`login;jsessionid=XXX`), j_username=Base64(ID), j_password=plain text(SHA256 주석 처리됨). `redirect: 'manual'`로 각 redirect hop에서 쿠키를 개별 수집해야 세션 유지됨. `getSetCookie()` API(Node 18.14+)가 다중 Set-Cookie 헤더를 올바르게 처리함.
- **교훈**: 레거시 시스템 HTTP 자동화 시 ① HTML에서 form action 파싱(URL에 jsessionid 포함 여부 확인) ② `redirect: 'manual'`로 hop별 쿠키 수집 ③ 브라우저 DevTools로 실제 전송되는 필드와 인코딩 방식 확인 — 이 3단계를 먼저 수행할 것.

### 4. Electron osascript 자식 프로세스에서 keystroke silent fail — click menu item 사용 (2026-04-27)

- **상황**: Electron 글로벌 단축키로 스니펫 실행 시 `osascript -e 'keystroke "v" using command down'`이 exit 0을 반환하지만 텍스트가 삽입되지 않음.
- **발견**: Electron 자식 프로세스(exec)에서 System Events keystroke "v" using command down은 sandbox/권한 문제로 silent fail. `click menu item "Paste" of menu "Edit" of menu bar item "Edit" of menu bar 1`이 유일하게 신뢰 가능한 대안. 또한 런처 창이 열릴 때 frontmost app을 미리 캡처(previousApp)하지 않으면 창 활성화 후 CS-all 자신이 target이 되는 문제 발생.
- **교훈**: Electron에서 클립보드 → 붙여넣기 자동화: ① showLauncher() 시점에 osascript로 frontmost 저장(previousApp) ② 스니펫 실행 시 autoPaste(value, previousApp) 전달 ③ 붙여넣기는 click menu item "Paste" 방식 사용. keystroke "v" using command down은 Electron 자식 프로세스에서 사용 금지.

### 5. React useState stale closure — async chain의 setData 직후 동일 클로저 data 참조 금지 (2026-04-28)

- **상황**: PortalManager `saveSettings()`에서 `persist(next)` (내부 `setData(next)` + `await PortalAPI.save(next)`) 직후, 같은 onConfirm 클로저의 `syncSupabase()` 실행. devices 테이블 upsert 라인 `name: data.deviceName ?? deviceName ?? null` — React 배칭 때문에 `data.deviceName`은 옛 값, 사용자가 새로 입력한 useState `deviceName`은 신값인데 `??` 순서가 거꾸로라 옛 값이 이김 → Supabase에 새 이름이 영영 안 올라감.
- **발견**: `setX(next)` 는 마이크로태스크 큐에 들어가지만 같은 함수 스코프의 closure 변수는 await 후에도 갱신되지 않음. async chain에서 데이터 흐름은 항상 명시적으로 전달(인자 또는 ref)하거나, 새로 입력된 useState 값을 우선 참조해야 함.
- **교훈**: 코드 리뷰 시 `setX(...)` 직후 같은 함수에서 `x` 또는 `data` 같은 closure-captured 상태를 참조하는 패턴은 **반드시 의심**. 검토 체크리스트에 추가: "async fn 내 setData → 같은 함수 후속 분기가 data 참조? → 직접 인자 전달 또는 fresh useState 사용으로 대체". 비슷한 자기-덮어쓰기 패턴: `fetchKnownDevices()` 가 Supabase 응답으로 로컬 deviceName을 force-overwrite 했던 case도 동일한 클래스 — local-first 정책 명시 필요.

### 6. Next.js App Router createPortal → position:fixed 직접 사용 (2026-04-28)

- **상황**: MentionInput 드롭다운을 `createPortal(dropdown, document.body)` 로 구현. 로컬(npm run dev)에서는 정상, Vercel 프로덕션 빌드에서만 드롭다운 미표시.
- **발견**: Next.js App Router는 "use client" 컴포넌트도 초기 HTML을 서버에서 렌더링. `createPortal`은 `document.body`가 필요해 `mounted` state 체크로 SSR 방지했으나, hydration 타이밍 차이로 프로덕션에서 portal이 조용히 실패. `overflow:hidden` 부모 탈출이 목적이라면 `position:fixed`만으로 충분 — fixed는 CSS spec상 `overflow:hidden` 부모에 영향 받지 않음 (transform 없을 때).
- **교훈**: Next.js App Router에서 드롭다운/툴팁의 `overflow` 탈출은 `position:fixed + getBoundingClientRect()` 로 해결. `createPortal`은 SSR과 충돌 위험이 있어 꼭 필요한 경우(모달 배경 등)만 사용. 로컬과 프로덕션 차이가 있으면 hydration 타이밍 문제를 1순위로 의심.

### 7. iCloud Drive + Tauri 빌드 ETIMEDOUT + 크로스 디바이스 절대경로 버그 (2026-05-01)

- **상황**: macOS `~/Documents/`(iCloud 동기화 경로) 안의 Tauri 프로젝트에서 `bun run tauri:build:dmg` 실행 시 `os error 60 (ETIMEDOUT)` 발생. 또 `.cargo/config.toml`에 `target-dir = "/Users/gwanli/..."` 절대경로가 있어 다른 Mac에서 빌드 실패. 로그 뷰어의 `offset` 파라미터가 bytes이나 `text.slice(chars)`로 처리해 한글 로그에서 중복 append 발생.
- **발견**: ① iCloud `brctl status`에서 `needs-sync`/`orphan.live` 에러 시 파일 I/O 간헐 타임아웃. `brctl download <path>`로 로컬 강제 다운로드 후 재시도. ② `.cargo/config.toml` 절대경로 → `build-macos.ts` 래퍼로 `CARGO_TARGET_DIR=$HOME/cargo-targets/portmanager` 동적 설정. ③ `text.slice(offset)` → `Buffer.from(text,'utf-8').slice(offset).toString()`으로 byte 기반 슬라이싱 통일. Rust `&content[offset..]` → `is_char_boundary()` safe slicing.
- **교훈**: Tauri 프로젝트가 iCloud 경로에 있으면 빌드 전 `brctl download` 실행 또는 프로젝트를 iCloud 밖으로 이동. `.cargo/config.toml`에 절대경로 사용 금지 — 항상 동적 환경변수로 대체. 로그 offset은 byte/char 일관성 반드시 검증.

### 8. killall -9 node / rm -rf .next 가 Next.js dev 서버를 자살시키는 패턴 (2026-05-01)

- **상황**: Next.js API 라우트(`/api/build-dmg`)에서 빌드 전 `killall -9 node`를 실행했더니 SSE 스트림이 즉시 끊겨 빌드가 실패처럼 보임. 빌드 npm 스크립트에 `rm -rf .next`가 포함돼 있어 빌드 실행 중 dev 서버가 불능 상태가 됨.
- **발견**: `killall -9 node`는 OS 전체 node 프로세스를 종료 — Next.js 개발 서버, VS Code, 모든 node 기반 앱 포함. API 라우트는 dev 서버 내에서 실행되므로 자기 자신도 종료됨 → SSE 스트림 즉시 단절. `rm -rf .next`는 dev 서버가 읽는 컴파일 캐시 디렉토리를 삭제 → 서버가 응답 불능 상태로 전환. `next.config.js`의 `distDir: NODE_ENV=production ? '.next-build' : '.next'` 설정으로 production 빌드는 `.next-build`에 출력되므로 `rm -rf .next`가 불필요함.
- **교훈**: API 라우트에서 프로세스 종료 시 `pkill -f "AppName"`으로 특정 앱만 종료. `killall -9 node` 절대 사용 금지. 빌드 스크립트에서 `rm -rf .next` 제거 — next.config.js의 distDir 분리로 대체. production 빌드가 별도 디렉토리를 사용하면 dev 서버 캐시 삭제 불필요.
