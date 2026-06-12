# knowledge/claude-code-platform — Claude Code 플랫폼 (CLI, marketplace, settings)

cs-experiencing 오케스트레이터 SKILL.md에서 이관된 프로젝트-특화 학습.
번호는 전역 INDEX(skills/experiencing/SKILL.md) 번호를 유지한다. 신규 항목은 INDEX의 max+1 번호를 부여받아 이 파일 끝에 추가된다.
cs-end Forget Gate(Phase 2.5)가 이 파일의 `<!-- tier: tactical -->` 항목도 30일 decay 스캔 대상으로 포함한다.

### 22. ~/.claude/settings.json extraKnownMarketplaces는 객체 shape 필수 (2026-05-17)
<!-- tier: tactical -->
- **상황**: 마켓플레이스 entry를 문자열(경로)로 추가 → `/doctor`에서 "Expected object, but received string" 에러 13건.
- **발견**: 유일하게 작동하는 entry(`karpathy-skills`)가 `{ source: { source: "github", repo: "owner/repo" } }` 중첩 객체 형태였음. 문자열 path는 invalid 스키마.
- **교훈**: 새 known marketplace 추가 시 반드시 객체 shape 사용. 스키마 불확실하면 기존 작동 entry 먼저 참고. 자동 설치 스크립트가 string으로 저장하면 같은 에러 재발 — 설치 스크립트 측 패치도 검토.

### 37. Claude Code CLI를 Bun 서버 서브프로세스로 AI 추론 백엔드로 활용 (2026-05-23)
<!-- tier: principle -->
- **상황**: portmanagement 앱에서 AI 이름 추천 기능(`/api/suggest-batch`) 원리를 분석. Anthropic API 키 없이 로컬에서 AI 기능을 서버사이드로 구현하는 방식이 궁금했음.
- **발견**: `claude -p <prompt>` (-p = print/non-interactive 모드)를 `Bun.spawn([CLAUDE_PATH, '-p', prompt])` 로 서브프로세스 실행하여 stdout에서 응답을 수집. CLAUDE_PATH는 서버 시작 시 1회 탐지(`zsh -l -c 'which claude'` → 하드코딩 경로 fallback). CLAUDE_PATH 미탐지 시 503 반환. suggest-batch는 N개 포트를 단일 프롬프트로 묶어 CLI 1회 호출 → O(N) 호출을 O(1)로 최적화.
- **교훈**: Anthropic API 키가 없어도 로컬에 Claude Code CLI가 설치·로그인된 환경이라면 Bun/Node 서버에서 서브프로세스로 AI 추론을 수행할 수 있다. 503 vs 500 구분으로 "CLI 미설치"와 "런타임 오류"를 의미론적으로 분리하는 것이 디버깅에 유리.

### 45. 마켓플레이스 플러그인 폴더명 vs 캐노니컬 이름 — 항상 manifest 우선 (2026-05-23)
<!-- tier: principle -->
- **상황**: skill-manager의 CSnCompany_2-0 플러그인이 14개 스킬 중 3개만 감지하는 버그. 인덱스 빌더가 marketplaceDefinedPlugins 집합을 폴더 이름(cs-ceo-v13)으로 채웠는데 캐시 키는 캐노니컬 이름(cs-ceo)이라 집합 조회가 항상 false였다.
- **발견**: 마켓플레이스 플러그인 폴더는 버전 suffix가 붙은 배포 아티팩트(cs-ceo-v13)이고, marketplace.json의 plugins[].name이 의미적 캐노니컬 이름이다. 단일 버전 폴더 안에 여러 플러그인이 있을 수도 있다. 해결: marketplace.json 먼저 읽어 Map(folderName@mkt → canonicalName)을 만들고, 이후 모든 집합 조회를 캐노니컬 이름으로 수행.
- **교훈**: 파일시스템에서 읽은 플러그인 식별자는 절대 캐노니컬로 취급하지 말 것. 마켓플레이스에 marketplace.json이 있으면 반드시 먼저 읽어 이름을 해소한 뒤 비교. 폴더명→캐노니컬 매핑은 first-write-wins.

### 46. claude --bg 플래그: CLI 내장 백그라운드 에이전트 실행 (2026-05-23)
<!-- tier: principle -->
- **상황**: skill-manager AI 추천의 "bg" 모드를 OS 레벨 detached spawn으로 구현했으나 Claude 에이전트가 실제로 실행되지 않았다.
- **발견**: Claude Code CLI에는 --bg 플래그가 있다. `execFile('claude', ['--bg', prompt], { cwd, env })`로 호출하면 클로드가 내부적으로 백그라운드 에이전트를 생성하고 즉시 종료한다. 터미널 창 없이 프롬프트를 실행하는 공식 방법이다. shell을 거치지 않으므로 execFile(shell: false)과 args 배열을 사용해야 한다.
- **교훈**: 백그라운드 Claude 에이전트 실행 = --bg 플래그. OS 프로세스 detach(detached: true, stdio: ignore)와 혼동 금지. 특수문자 보호를 위해 execFile에 args 배열로 전달.

### 49. known_marketplaces.json은 신뢰할 만한 source-of-truth가 아니다 — 자동 기록된 URL은 잘못될 수 있음 (2026-05-23)
<!-- tier: principle -->
- **상황**: /doctor가 ~/.claude/settings.json의 extraKnownMarketplaces 14개 항목에 대해 "source 필드 누락" 오류를 보고했다. known_marketplaces.json의 source URL을 참조해 객체 형태(`{source: "github", repo: "owner/name"}`)로 복원하려는데, `claude-code-plugins → anthropics/claude-code`(CLI 본체 레포)와 `cli → googleworkspace/cli`(Claude 마켓플레이스 아님) 두 항목이 명백히 틀린 값을 가리키고 있었다.
- **발견**: known_marketplaces.json의 `source` 필드는 최초 설치 시 사용자가 전달한 URL을 그대로 기록한다 — 마켓플레이스의 실제 정체성을 검증하지 않는다. enabledPlugins에서 실제로 쓰이는 prefix(예: `frontend-design@claude-code-plugins`)와 source URL이 가리키는 repo의 일치 여부는 별도 확인이 필요하다. CLAUDE.md의 "GitHub 마켓플레이스 플러그인 자동 설치" 루틴처럼 사용자 입력을 그대로 기록하는 경로일수록 잘못된 값이 잠복하기 쉽다.
- **교훈**: known_marketplaces.json을 복원/마이그레이션 source로 쓰기 전에 각 entry를 검증하라. ① enabledPlugins prefix와 marketplace name이 매칭되는지, ② source repo가 실제 `.claude-plugin/marketplace.json`을 가진 마켓플레이스인지, ③ 의심스러우면 AskUserQuestion으로 사용자에게 표면화. 일괄 변환 스크립트는 검증 게이트 없이 절대 돌리지 말 것.

### 69. 의존성 제거 결정의 커플링 드리프트 — 원칙 기록 ≠ 실행, repo-wide grep 통과 후에만 ✅ 반영됨 (2026-06-12)
<!-- tier: principle -->
- **상황**: cs-ceo 노하우 #18(2026-05-30)이 "플러그인 시스템은 외부 볼트에 의존하지 않는다"를 선언하고 cs-ceo의 CS_V7 READ 경로(Phase -3.5)를 제거했으나, 커플링된 cs-end의 WRITE 경로(Phase 2.1 → $HOME/CS_V7/raw/)는 다른 플러그인 디렉토리에 있어 같은 커밋에서 누락됨. 사용자가 /cs-end 실행 시 CS_V7에 실파일이 기록되며 2026-06-12에 발견.
- **발견**: `grep -rn "CS_V7" plugins/` 한 줄로 즉시 탐지 가능했던 드리프트였음. 원칙 선언 커밋은 자기 플러그인 내부에서만 일관적이었고, 같은 원칙이 요구하는 타 플러그인 변경은 포함되지 않았다 (commit c5c032e에서 해소).
- **교훈**: 외부 시스템 통합을 제거하는 결정은 같은 커밋에서 커플링된 반대편(READ↔WRITE)까지 수정해야 한다. ✅ 반영됨 표시는 `grep -rn "<외부시스템명>"`이 활성 파일에서 0건일 때만 붙인다. "원칙이 기록됐다"는 "실행됐다"의 보증이 아니다.
- **근거**: cs-end-v3/commands/cs-end.md:205-258 Phase 2.1 잔존 → c5c032e 삭제; cs-ceo-v15 SKILL.md:248 #18 본문이 cs-end Phase 2.1을 문제의 일부로 명시
- ⏸ DEFER (2026-06-12): plugins/CLAUDE.md 패치가 verifier에 REFUTED('활성 파일' 미정의 + Prescription Policy 위반) — goal-statement 형태로 재작성하여 다음 세션 적용 (.experiencing-btw.json pending-patch)

### 70. 외부 소스 원칙 추출 — 생성(generative)과 기각(adversarial refuter) 단계 분리 (2026-06-12)
<!-- tier: tactical -->
- **상황**: 공개된 Fable 5 시스템 프롬프트에서 이식 가능한 원칙을 추출하는 60-에이전트 감사 (commit 01ceddf).
- **발견**: 후보 27건 중 적대적 refuter가 15건(55.6%)을 기각("이미 있음" / "이 시스템에 부적합" / "원칙이 아닌 구현 세부사항"), 확정 12건은 전부 구현으로 이어짐. 기각률 수치는 이 1회 관찰값이며 처방이 아님.
- **교훈**: 외부 고품질 소스(시스템 프롬프트, 레포, 문서)에서 원칙을 추출할 때 후보 생성과 기각을 별도 에이전트 단계로 분리하면 구현 가치 있는 것만 남는다. 기각 사유를 로그로 남겨 다음 추출에서 중복 작업을 방지한다.
- **근거**: wf_448e5949 감사: 27 후보 → 2-refuter 검증 → 12 확정 → 01ceddf 전부 구현

### 71. 새 프로토콜은 grep 1줄로 준수 확인 가능한 아티팩트 문자열과 함께 설계한다 (2026-06-12)
<!-- tier: principle -->
- **상황**: LOOP-PROTOCOL을 13개 리드 파일이 참조하지만 에이전트가 실제로 Read했는지 확인할 방법이 없었음.
- **발견**: 리포트 헤더에 `protocol: LOOP-PROTOCOL [a-f] loaded (round budget N)` 표준 문자열을 의무화(없으면 프로토콜 미적용 간주)하니 준수 여부가 grep 1줄로 검증 가능해짐 (LOOP-PROTOCOL.md:4).
- **교훈**: "프로토콜이 문서에 있다"와 "에이전트가 따른다"는 별개다. 새 프로토콜/규칙을 추가할 때 실행 증거가 되는 표준 아티팩트 문자열(헤더 1줄)을 같은 커밋에서 함께 설계해 검증 가능성을 빌드인한다.
- **근거**: plugins/shared/LOOP-PROTOCOL.md:4 + commit 01ceddf 13개 캐리어 파일
- ✅ 반영됨 (2026-06): LOOP-PROTOCOL.md:4 헤더 아티팩트 의무화로 이미 운영 중
