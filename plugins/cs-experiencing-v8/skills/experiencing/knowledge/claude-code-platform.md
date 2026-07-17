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
- **addendum (2026-07-17)**: 무거운 플러그인/훅이 다수 설치된 OAuth 계정에서는 `claude -p` 서브프로세스 스폰 자체가 CLI 부팅 오버헤드(hooks/plugin sync/CLAUDE.md 자동탐색)로 수십 초가 걸릴 수 있다. `claude --help`의 경량 모드 중 `--bare`는 API 키 인증만 지원해 OAuth 계정에서 즉시 로그인 실패하지만, `--safe-mode`는 OAuth 인증을 유지하면서 동일한 부팅 오버헤드를 스킵한다 — 실측 42~47s → 13~18s. 서브프로세스로 반복 스폰할 때는 인증 방식과 호환되는 경량 모드를 `--help`로 먼저 확인한다 (플래그명은 버전마다 바뀔 수 있어 tactical로 취급). (skeptic verifier: CLI 플래그명 자체는 버전 종속이라 principle 승격 안 함).
- **addendum (2026-07-17)**: "suggest-batch는 N개를 단일 호출로 묶어 O(N)→O(1) 최적화"라는 위 발견은 배치 크기가 무한정 커질 수 있다는 전제가 빠져 있었다 — 실측 결과 미완료 항목 62개를 단일 호출로 묶으면 응답 생성 시간이 60s 고정 서버 타임아웃을 넘겨 결과 없이 조용히 실패했다(호출부는 "완료: 0개"로 성공처럼 보이는 메시지만 띄움). 가변 크기 입력을 단일 API 호출로 배치 처리할 때는 고정 청크 크기(예: 15개)로 나눠 순차 호출하고, 청크마다 즉시 결과를 저장해 부분 실패에도 진행분을 보존해야 한다 — O(N)→O(1) 최적화는 N이 유계일 때만 안전하다. (skeptic verifier CONFIRM — 숫자를 뺀 일반형 아키텍처 위험 원칙으로 생존, portmanagement commit 6203c1d). <!-- error-ref: ERR-2026-07-17-003 -->

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
- ✅ 반영됨 (2026-06-12): plugins/CLAUDE.md "통합 제거 규칙" — REFUTED 사유 해소: 스코프를 'marketplace.json plugins 배열 + plugins/shared/ + plugins/CLAUDE.md'로 기계적으로 정의, 실행성 참조/문서적 언급 구분, 목표 진술+증거 요건 형태(리터럴 grep 레시피 제거)

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

### 72. 하드코딩 시크릿 제거 ≠ 완료 — provider 측 rotation이 별도 필수 단계 (2026-06-12)
<!-- tier: principle -->
- **상황**: ~/.claude/settings.local.json permissions.allow에 Supabase 토큰(`sbp_...`)이 하드코딩되어 있어 harness-diet 후속 작업으로 제거. 파일에서는 삭제했지만 plaintext로 수개월 노출된 상태였음.
- **발견**: 파일 수정과 시크릿 무효화(rotation)는 독립 작업이다. 파일에서 지워도 토큰 자체는 provider 측에서 여전히 유효하며, 백업·sync 도구가 이미 옛 파일 내용을 복제했을 수 있어 노출은 비가역적.
- **교훈**: 시크릿 노출 대응의 SUCCESS CRITERIA는 (1) 파일 제거 + (2) provider 대시보드에서 rotation 두 단계 모두를 포함해야 한다. 에이전트는 (1)만 수행 가능하므로 (2)를 사용자 액션으로 명시 전달하기 전에는 완료 선언이 false-complete가 된다.

### 73. 컨텍스트 없는 재개 요청 — episodic memory 검색을 첫 단계로 (2026-06-12)
<!-- tier: principle -->
- **상황**: 사용자가 ".claude 작업 시작"이라고만 입력했고 태스크 설명이 전혀 없었음.
- **발견**: episodic-memory 검색 에이전트 1회로 2026-06-07 harness-diet 세션의 미완료 항목 2건(토큰 제거 + README 삭제)을 정확히 복원, 사용자에게 질문하지 않고 즉시 실행으로 이어짐.
- **교훈**: 태스크 컨텍스트 없는 재개성 요청("X 작업 시작", "이어서 해줘")은 사용자에게 묻기 전에 과거 대화 검색을 기본 첫 단계로 삼는다. "무엇을 할까요?" 질문은 메모리 검색이 실패한 뒤의 fallback이다.

### 74. JSON 설정 파일 수정은 텍스트 편집 대신 json.load/json.dump 라운드트립 (2026-06-12)
<!-- tier: tactical -->
- **상황**: settings.local.json permissions.allow 배열에서 항목 1개를 제거해야 했음.
- **발견**: python3 `json.load` → 리스트 필터 → `json.dump(indent=2)`가 구조적 유효성을 보장. 텍스트 치환·라인 삭제는 trailing comma 등으로 파일을 깨뜨릴 수 있고, settings 파일이 깨지면 전체 권한 규칙이 조용히 무효화됨.
- **교훈**: .json 설정 수정은 언어 내장 파서로 라운드트립하고, 수정 직후 `json.load` 재검증 1줄을 덧붙인다 (#36 Python conflict 파싱, #41 Python 수술적 교체와 같은 계열 — JSON 특화).

### 115. 구조 리팩터는 다른 파일의 지시문을 조용히 깨뜨린다 — 에이전트는 아무것도 등록하지 않고 "성공"을 보고한다 (2026-07-16)
<!-- tier: principle -->

- **상황**: 위 #114의 읽기 경로 분할로 레지스트리를 `LEADER.md`에서 `INDEX/LEDGER/CORE/COMMON`으로 옮긴 뒤, 사용자가 "이제 이 스킬로 학습할 준비된 건가?"라고 물었다.
- **발견**: 분할을 참조하는 다른 파일들이 여전히 옛 구조를 가리키고 있었다. `figma-learn-all-pages/SKILL.md`는 "도메인의 `LEADER.md`에 등록하라"고 지시했는데 — 분할 전엔 참이었지만 지금은 거짓이다. **이를 따르는 에이전트는 존재하지 않는 섹션에 쓰려 하고, 아무것도 등록하지 못한 채 성공을 보고했을 것이다.** 처음엔 1건인 줄 알았으나, 스윕을 반복하자 총 **13건**이 나왔다(프로젝트 노트 8건, 라우팅 tiebreaker 1건, 승격 대상 3건, CORE 상호참조 1건).
- **교훈**: 파일 분할/역할 이동 후에는 그 구조를 이름으로 참조하는 **모든** 문서를 grep으로 전수 스윕한다 — 1건을 고치고 끝났다고 가정하지 않는다(이번엔 1 → 5 → 13으로 늘었다). 근본 예방책은 지시문을 **폴더/파일 이름이 아니라 구조 유형**("분할 도메인 vs 단일 파일 도메인")으로 분기시키고, 권위 있는 단일 출처(각 도메인의 Mode 1)로 위임하는 것이다. 또한 **아무 지시문도 갱신을 명령하지 않는 표/매니페스트**(고아 문서)를 함께 찾아 소유자를 명시적으로 지정한다.
- **근거**: `figma-learn-all-pages/SKILL.md` — "register into the domain's `LEADER.md`" (분할 후 거짓). 탐지에 가장 효과적이었던 것은 **읽기 전용 리허설/verifier 서브에이전트**였다: 저자가 놓친 고아 매니페스트(`nds/LEADER.md`의 `## Learned files` — 갱신 지시문이 어디에도 없음)를 찾아냈고, 이후 cold-read verifier가 남은 8건을 스스로 추가 발굴했다. (skeptic verifier CONFIRM — "프로즈 지시문이 여러 파일에 분산된 시스템의 불변 속성; 참조된 구조를 옮겨도 모든 포인터가 자동 갱신되지 않고, 낡은 포인터를 따르는 실행자는 대상이 사라졌다는 신호를 받지 못한다".)

### 117. 우선순위 규칙에는 "무엇이 tie-breaker가 아닌지"를 명시해야 한다 — 정렬 순서와 인용 횟수는 그럴듯한 함정 (2026-07-16)
<!-- tier: tactical -->

- **상황**: 가이드 도메인과 프로젝트 도메인을 페어로 읽어 화면을 만드는 BUILD 경로를, 실제 실행 전에 읽기 전용 리허설 에이전트로 점검.
- **발견**: 리허설 에이전트가 자기 추론을 그대로 노출했다 — 이름이 같은 두 컴포넌트 중 하나를 "목록에 먼저 나오고 6번 corroborate됐다"는 이유만으로 조용히 골랐을 것이라고. 문서들은 그런 기준을 지지한 적이 없다. 즉 **문서가 침묵하는 지점에서 모델은 그럴듯한 근거를 스스로 발명**하고, 그 발명은 눈에 띄지 않는다.
- **교훈**: 우선순위/precedence 규칙을 쓸 때 적용 규칙만 쓰지 말고 **명시적 비적용(non-application) 케이스**를 함께 박는다. 이번엔 3개를 추가했다: (1) 가이드가 자기 자신과 충돌하면 우선순위로 고르지 말고 에스컬레이션 — 실재하는 두 컴포넌트가 같은 이름을 쓰는 것은 "주장의 충돌"이 아니다, (2) 신뢰성 주장(이 import가 실제로 되는가)과 디자인 주장(무엇처럼 보여야 하는가)은 다른 축이라 둘 다 참일 수 있다, (3) 양쪽 도메인이 모두 침묵하면 그 값을 **갖고 있지 않은 것**이므로 목업에서 추론하지 말고 에스컬레이션. 리허설 에이전트에게 판단 **근거를 말하게** 하는 것이 이 함정 탐지에 효과적이었다.
- **근거**: 리허설 에이전트 원문 — "I would have silently picked Core's incumbent purely because it's listed first and 'corroborated 6×' — a plausible but ungrounded tie-breaker the files never actually endorse." (skeptic verifier DOWNGRADE — "관측된 실패가 아니라 서브에이전트의 자기보고 반사실(counterfactual)이며 한 파일의 모호성에 대한 단일 일화 → 지시문 설계 위생으로는 타당하나 principle 근거로는 부족".)

### 124. Korean 파일에서 Edit 툴 실패 — Python writelines 패턴 (2026-06-12)
<!-- tier: principle -->
<!-- renumbered 2026-07-17: 구 인라인 #12 — knowledge/ 이관 항목 #12과 번호 충돌로 재부여 -->

- **상황**: Next.js 대시보드(`app/mau/page.tsx`)에서 한국어 문자열이 포함된 라인을 Edit 툴로 수정하려 하자 old_string 매칭이 반복 실패함.
- **발견**: Edit 툴은 멀티바이트(한국어) 문자 포함 문자열 매칭에 신뢰할 수 없음. Python `readlines()` + 0-index 행 번호 직접 지정 후 `writelines()`가 안정적 대안.
- **교훈**: 한국어가 포함된 파일 수정 시 Edit 툴 먼저 시도하지 말고 즉시 Python `readlines/writelines` + 행 번호 패턴으로 처리하라.

### 138. EnterWorktree가 "Already in a worktree session"으로 막히면 디렉터리 존재를 의심하기 전에 ExitWorktree(remove)부터 시도한다 (2026-07-17)
<!-- tier: principle -->
- **상황**: 세션 내에서 이전 라운드에 만든 워크트리가 (이전 `ExitWorktree(action:'remove')` 호출 등으로) 이미 디스크에서 사라진 상태에서, 다음 라운드 작업을 위해 새 워크트리를 만들려고 `EnterWorktree`를 호출.
- **발견**: 세션 내부 상태가 여전히 그 워크트리 안에 있다고 믿고 있어 `ls`/`cd`는 실패하는데도 `EnterWorktree`는 "Already in a worktree session" 오류로 새 워크트리 생성을 거부한다. `ExitWorktree({action:'remove', discard_changes:true})`를 먼저 호출하면 — 대상 디렉터리가 이미 없어도 안전하게 처리되고 — 세션 상태가 리셋되어 이후 `EnterWorktree`가 정상 동작한다. 이 시퀀스는 한 세션 안에서 최소 3회 반복 관측됐다(매 라운드 작업 종료 후 워크트리가 정리되고, 다음 라운드 시작 시 동일 패턴 재발).
- **교훈**: `EnterWorktree`가 "Already in a worktree session"으로 실패하면 디렉터리 존재 여부를 조사하는 대신 바로 `ExitWorktree({action:'remove', discard_changes:true})` → `EnterWorktree` 재시도 패턴을 적용한다. 이 도구 조합의 재현 가능한 계약(디렉터리가 없어도 remove가 안전하게 세션 상태를 리셋함)으로 취급한다.
- **근거**: 세션 중 "Already in a worktree session" 오류 발생 → `ExitWorktree(action:'remove', discard_changes:true)` 호출 시 "Exited and removed worktree at ... Session is now back in ..." 응답(대상 디렉터리가 이미 없었음에도 성공) → 곧이은 `EnterWorktree` 정상 생성, 총 3회 반복 재현 (2026-07-17 portmanagement 세션).

### 139. Workflow 스크립트의 agent 프롬프트 안에 리터럴 `${...}`를 쓰면 sandbox가 즉시 평가해 "process is not defined"로 전체 런을 크래시시킨다 (2026-07-17)
<!-- tier: principle -->
<!-- error-ref: ERR-2026-07-17-005 -->
- **상황**: Workflow 도구용 스크립트를 작성하며, 구현 에이전트에게 실제 코드 수정 내용을 설명하기 위해 agent(`...`) 프롬프트 문자열 안에 `http://localhost:${Number(process.env.API_PORT) || 3001}` 같은 예시 코드를 (백틱을 이스케이프해서) 그대로 적어 넣었다.
- **발견**: 이 리터럴 `${...}` 시퀀스는 서브에이전트에게 전달되기 전에, 워크플로 스크립트 자체를 실행하는 sandbox JS 엔진이 즉시 템플릿 리터럴 치환으로 평가해버린다. 그 sandbox에는 Node의 `process` 전역이 없어 워크플로가 런칭 즉시 "Error: process is not defined"로 전체가 크래시했다 — 서브에이전트가 하나도 실행되기 전에 발생하는 실패라 원인 파악이 까다롭다. `Workflow` 도구가 항상 스크립트를 디스크에 persist하고 경로를 반환하므로, 그 파일을 `${` 로 grep해 정확한 라인을 찾아 `Edit`으로 수정한 뒤 `Workflow({scriptPath, resumeFromRunId})`로 재개하면 이미 완료된 `agent()` 호출은 캐시에서 그대로 재생되고 수정된 지점부터만 재실행된다.
- **교훈**: Workflow 스크립트의 agent 프롬프트 안에서 실제 코드에 있는 `${...}` 문법 자체를 "설명"해야 할 때는 리터럴로 쓰지 말고 프로즈로 풀어쓴다(예: "PORT는 `Number(process.env.API_PORT) || 3001`로 읽는다"처럼 표현하되 그 표현 자체가 외부 템플릿 리터럴 안에 `${`로 나타나지 않게 한다). 워크플로가 launch 직후 크래시하면 persisted 스크립트 경로를 grep해 `${` 시퀀스부터 의심하고, 고치면 `resumeFromRunId`로 캐시 재사용 재개가 가능하다.
- **근거**: 워크플로 launch 직후 "Error: process is not defined at workflow.js:32:413" 크래시 → persisted 스크립트 파일에서 `\${Number(process.env.API_PORT) || 3001}` 라인 발견 → 리터럴 표현으로 교체 후 `Workflow({scriptPath, resumeFromRunId})` 재개, 이전 완료 agent 결과는 캐시에서 재생되고 정상 완주 (2026-07-17 portmanagement 세션, cs-end Workflow 스크립트 저작 중).
