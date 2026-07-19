# knowledge/tauri-windows — Tauri Windows 빌드·플랫폼 분기 패턴

cs-experiencing 오케스트레이터 SKILL.md에서 이관된 프로젝트-특화 학습.
번호는 전역 INDEX(skills/experiencing/SKILL.md) 번호를 유지한다. 신규 항목은 INDEX의 max+1 번호를 부여받아 이 파일 끝에 추가된다.
cs-end Forget Gate(Phase 2.5)가 이 파일의 `<!-- tier: tactical -->` 항목도 30일 decay 스캔 대상으로 포함한다.

### 81. Windows 플랫폼 기능은 React/TS/Rust 3-레이어 동시 점검 필수 (2026-06-14)
<!-- tier: principle -->
- **상황**: Windows에서 "agents" 버튼 클릭 시 "cmux Agent View 실패: cmux는 맥에서만 가능합니다" 에러 토스트가 나타났다. Rust의 `cfg!(windows)` 가드는 있었으나 React 버튼 조건에 `terminalApp === 'wsl'` 예외 케이스가 누락되어 macOS 전용 함수가 호출됐다.
- **발견**: Tauri 앱에서 플랫폼별 기능은 (1) React 버튼 렌더 조건 `{!isWindows() && ...}`, (2) TypeScript 함수 내 `if (isWindows()) { ... }` 분기, (3) Rust `#[cfg(target_os = "windows")]` 구현 — 3개 레이어 모두에 동시에 반영해야 한다. 어느 하나가 빠지면 Rust 가드가 에러 문자열을 반환하고 그게 UI 토스트로 노출된다.
- **교훈**: 플랫폼 기능 추가/수정 체크리스트 3항목: ① `isWindows()` React conditional render, ② TS 함수 분기, ③ Rust `cfg!` guard. 셋 중 하나라도 빠지면 엣지 케이스(WSL terminalApp, 특정 설정값 등)에서 노출됨.
- **근거**: `terminalApp === 'wsl'` 케이스에서 React 조건 없이 `openCmuxAgentView`가 호출 → Rust `open_cmux_agent_view`의 Windows 가드가 Err 반환 → 에러 토스트 노출 확인.

### 82. spawn_wt_cmd — Windows Terminal(wt.exe) 없을 때 cmd.exe 폴백 패턴 (2026-06-14)
<!-- tier: tactical -->
- **상황**: Windows에서 `claude agents`를 새 터미널 창으로 열어야 했다. wt.exe(Windows Terminal)가 있는 환경(최신 Windows 11)과 없는 환경(구형 또는 비설치) 모두 커버해야 함.
- **발견**: `where wt.exe` exit code로 존재 여부 판단 후 분기. 있으면 `cmd /c start wt --title <TITLE> -- cmd /k <CMD>`, 없으면 `cmd /c start <TITLE> cmd /k <CMD>` 패턴이 안정적. Rust와 Bun api-server.ts 양쪽에 동일 로직을 미러링해야 Tauri 앱/웹 모드를 모두 커버한다.
- **교훈**: Windows 터미널 실행 시 항상 wt.exe → cmd.exe 폴백 2단계. Rust(`spawn_wt_cmd`)와 TypeScript(`/api/open-terminal-agent-view`) 양쪽에 미러링. Bun: `Bun.spawnSync(['where', 'wt.exe']).exitCode === 0`으로 판정.
- **근거**: `spawn_wt_cmd` (lib.rs:1314-1336) + `/api/open-terminal-agent-view` 엔드포인트(api-server.ts)에 동일 2단계 폴백 패턴 적용 후 v103 빌드 정상 동작 확인.

### 84. 멀티기기 build-number 역행 방지 — 빌드 전 pull 필수 (2026-06-14)
<!-- tier: tactical -->
- **상황**: 로컬에서 v97→v98 빌드 후 push하지 않은 상태에서 remote에 이미 v102가 존재했다. `git pull --rebase` 중 stash pop에서 build-number.json conflict 발생. `--ours`(v98)로 해결하면 다음 빌드가 v99가 되어 remote v103과 다시 충돌 위험.
- **발견**: Tauri build 스크립트는 마지막 git 커밋의 build-number +1로 번호를 결정한다. 빌드 전 `git pull`을 하지 않으면 로컬 HEAD가 뒤처져 있어 번호가 역행한다. 안전한 순서: `git pull --rebase` → `bun run tauri:build:win` → 빌드 아티팩트 커밋 → push.
- **교훈**: 멀티기기 Tauri 빌드 시 반드시 `git pull --rebase` 먼저. build-number.json과 tauri.conf.json은 빌드 스크립트가 자동 변경하므로 빌드 후 즉시 커밋해야 다음 pull에서 conflict 방지. 번호 역행 발생 시 재빌드가 가장 빠른 해결책.
- **근거**: local v98 stash vs remote v102 conflict → `git checkout --ours` → 재빌드로 v103 생성 + push로 해결.

### 133. dev 오케스트레이터 스크립트의 하드코딩 포트 + 무조건 kill이 "자기 자신의 워크트리 실행" 시나리오에서 메인 앱을 죽인다 (2026-07-17)
<!-- tier: tactical -->
<!-- error-ref: ERR-2026-07-17-004 -->
- **상황**: 포트관리기의 메인 포트는 9000인데, 앱 자신의 워크트리 기능으로 자기 자신의 워크트리를 "실행"하면 이미 떠 있던 메인 앱이 다운되는 현상 개선 요청.
- **발견**: 워크트리 "실행" 버튼이 할당된 포트를 어떤 코드 경로(Rust `spawn_process`/`execute_command`, api-server.ts 웹모드)에서도 자식 프로세스에 `PORT` env로 전달하지 않았고, vite/next로 인식된 커맨드만 `--port` CLI 플래그를 받았다. 게다가 이 프로젝트 자신의 `dev.ts`가 `VITE_PORT=9000`/`API_PORT=3001`을 하드코딩한 채 시작 시 해당 포트의 기존 리스너를 무조건 SIGKILL했다 — 자기 자신의 워크트리를 실행하면 메인 앱의 개발서버를 죽이는 자기 참조적 크래시였다.
- **교훈**: 다중 인스턴스/워크트리를 지원해야 하는 dev 오케스트레이터 스크립트는 (1) `PORT`류 env override를 최우선으로 존중하고, (2) "기존 리스너 정리" cleanup은 무조건 비활성화가 아니라 이번 세션이 실제로 바인딩하려는 포트로만 범위를 좁혀야 한다(override 세션도 크래시 후 재시작 시 자기 자신의 orphan 리스너는 정리해야 하므로). 자체 도구가 자기 자신을 대상으로 실행되는 시나리오는 최우선 회귀 테스트로 넣는다.
- **근거**: `dev.ts`가 `const VITE_PORT = 9000` / `const API_PORT = 3001`을 하드코딩하고 시작 시 무조건 두 포트의 리스너를 SIGKILL하는 코드 확인 → `PORT`/`API_PORT` env override 지원 + cleanup을 실제 타겟 포트로 한정하는 수정으로 재현 안 됨을 확인 (portmanagement PR #12).

### 136. git worktree remove는 그 디렉터리를 cwd로 쓰는 실행 중 프로세스를 멈추지 않는다 — 삭제 전 명시적 stop 필요 (2026-07-17)
<!-- tier: tactical -->
- **상황**: 워크트리를 "실행"(dev 서버 기동) 상태에서 그대로 삭제(또는 머지 후 정리 플로우, 동일 삭제 핸들러 재사용)하면 어떻게 되는지 점검.
- **발견**: `git worktree remove --force`는 디렉터리를 삭제할 뿐, 그 디렉터리를 cwd로 쓰는 실행 중 자식 프로세스는 멈추지 않는다. 결과적으로 포트에는 여전히 바인딩돼 있지만 cwd가 사라진 orphan 프로세스가 남는다 — OS 파일 삭제가 프로세스를 자동으로 정리해준다는 암묵적 가정은 틀렸다.
- **교훈**: 디렉터리 기반 리소스(워크트리, 임시 작업 폴더 등)를 삭제하는 플로우에는 그 디렉터리에서 실행 중인 프로세스를 먼저 정지시키는 단계를 명시적으로 포함해야 한다. 삭제 직전 해당 포트의 실제 실행 여부를 재확인(캐시된 isRunning 플래그를 신뢰하지 않고)한 뒤 정지 → 삭제 순서로 진행한다.
- **근거**: 워크트리를 실행 상태로 두고 삭제 → `git worktree list`에서는 사라졌지만 `lsof -i:<port>`에는 여전히 리스너가 남아있음을 Playwright로 재현 확인 → 삭제 전 `checkPortStatus`로 재확인 후 정지하는 수정 적용 뒤 동일 시나리오에서 orphan 프로세스 없음을 재검증 (portmanagement PR #13).
