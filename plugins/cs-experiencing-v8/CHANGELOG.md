## 8.2.8 (2026-07-19)

- 학습 2건 신규 추가 (모두 knowledge/misc-tooling.md, 근거 인용 포함, novelty 재검증 완료 — SKILL.md+knowledge/ 전체 grep 결과 유사 항목 없음):
  - #148 WebFetch가 클라이언트 렌더링(Next.js RSC) 페이지에서 실제 콘텐츠를 누락시킨다 — curl+grep/python 파싱으로 폴백 (principle)
  - #149 GUI 전용 설치 단계를 자동화 불가로 단정하기 전에, 설치 대상 산출물이 이미 디스크에 존재하는지 먼저 확인한다 (principle)
- PENDING 2건 (저장 안 함, Learning Gate 2-3점): "HTTP transport MCP 서버는 user-scope 등록 후 `claude mcp get`으로 연결 확인" (3점 — 유용하나 이미 자명한 검증 습관, impact 낮음) / "번들 스킬 CLI(`eagle-api-cli.js`)로 라이브러리 조회/태깅" (2점 — 특정 프로젝트/스킬에 국한, 재사용성 낮음)
- Core Memory 갱신: cs-core-memory-v1 memory-keeper가 CORE.md Recurring Issues에 2건 신규 기록 (WebFetch RSC 누락 패턴, GUI 설치 전 디스크 산출물 확인 패턴 — Session Count 6→7)
- CHANGELOG 정리: 이전 "미배포" pending 블록(freeparking-1 세션의 #75/#99 addendum)이 실제로는 commit d79b9fd(2026-07-19, VERSION 8.2.6 상태)에서 이미 파일에 반영·커밋되었음을 확인 — 버전업만 누락된 채 pending 헤더가 8.2.7 이후에도 정리되지 않고 남아있던 것으로, 이번 8.2.8에 소급 포함하여 정리함
- 출처: `/Users/gwanli/product_2026/Eagle_mcp` (Eagle MCP 서버 + Eagle Skill 설치) 세션 — domains_used는 fallback값 experiencing이었고 실제로는 cs-plugin 도메인 밖(Eagle 앱 연동) 작업. cs-experiencing 자체는 모든 세션의 학습 캡처 대상이므로 버전업 진행.

## 8.2.7 (2026-07-19)

- 학습 2건 신규 추가 (모두 knowledge/mobile-automation.md, skeptic CONFIRM):
  - #146 이름 기반 UI 요소 검색은 정확 일치를 전체 스크롤에서 먼저 시도하고, 없을 때만 부분 일치로 폴백해야 한다 (principle)
  - #147 dumpsys 등 상태 덤프에서 상태를 판정할 때는 관련 라인만 파싱해야 한다 (principle)
- Addendum 1건 (기존 #108 확장, knowledge/mobile-automation.md, 신규 번호 미부여): OCR 삭제 아이콘 매칭 실패의 두 가지 추가 원인 — (1) OCR이 실제로는 ASCII 'x'가 아니라 유니코드 곱셈기호 '×'(U+00D7)를 반환 (skeptic CONFIRM), (2) 동일 정적 스크린샷에서도 OCR이 일부 행의 아이콘 글리프를 비결정적으로 누락 → 좌표 기반 탭으로 폴백 (skeptic DOWNGRADE, tactical)
- PENDING 1건 (3점, 저장 안 함): "동일 퍼블리셔/화이트라벨 앱이라도 UI 관례(아이콘 위치·문구)는 자동 상속되지 않는다" — 기존 #107(퍼블리셔 prefix가 안정성 신호가 될 수 있음)과 관련 있으나 impact/reusability가 낮아 게이트 미통과
- 또한 이번 버전에 이전 세션의 미커밋 학습 2건 포함(별도 세션에서 이미 파일에는 반영됐으나 버전업 전이었음): #144 Claude Code 플러그인 캐시 갱신은 version bump + `claude plugin marketplace update`/`update` 모두 필요 (principle) / #145 글로벌 설정 반영 검증은 새 `claude -p` 헤드리스 프로세스로 한다 (principle) — knowledge/claude-code-platform.md
- Core Memory 갱신: cs-core-memory-v1 memory-keeper가 CORE.md Recurring Issues에 4건 신규 기록 (OCR 유니코드 불일치, OCR 비결정적 글리프 누락→좌표 폴백, 이름 검색 부분일치 오탐, 퍼블리셔 UI 관례 미상속 — Session Count 5→6). "잠금화면 판정 dumpsys 전체스캔" 후보는 episodic으로 판정되어 CORE.md에는 미기록(SKILL.md #147로는 저장됨 — CORE.md와 SKILL.md는 게이트 기준이 다름).
- 출처: `/Users/gwanli/product_2026/Ordering1` (Mega Coffee/Mammoth Coffee/Twosome Place 다중 카페 주문 자동화 프로젝트) 실기기 라이브 테스트 세션 — adb+Vision OCR 기반 UI 자동화 중 발견한 OCR 매칭/디바이스 상태 파싱 버그들. 프로젝트 자체는 cs-plugin 도메인 밖(coffee-ordering side project)이라 domains_used는 fallback값 experiencing.

## 8.2.6 (2026-07-18)

- 학습 1건 신규 추가: #143 Figma 노드의 `.x`/`.y`는 절대좌표가 아니라 부모 프레임 기준 상대좌표다 (principle, figma-design-system.md, skeptic CONFIRM)
- PENDING 1건 (2점, 저장 안 함): "생성형 UI 마커(화살표/뱃지)는 임의 균등배치가 아니라 실측 요소 좌표로 앵커해야 함" — 기존 #111("추측 대신 실측 샘플링") 원칙의 위치(position) 도메인 파생 적용으로 판정, 신규성 낮음
- Core Memory 갱신: cs-core-memory-v1 memory-keeper가 CORE.md Recurring Issues 섹션에 2건 신규 기록 (Session Count 1→2) — 부모-로컬 좌표 이중 오프셋 + 실측 좌표 앵커링 원칙
- 출처: nhdesign3(별도 Figma/Postgres 스킬 생태계, CSnCompany_2-0 마켓플레이스 밖) PPT 기획서 넘버링 배지 오배치 수정 세션 — 9개 배지를 실측 좌표로 재배치하는 도중 절대좌표를 Slide 프레임 자식 노드에 그대로 대입해 이중 오프셋되는 버그를 발견/수정. nhdesign3 자체의 세부 교훈(화살표 레시피, PPT 템플릿 특이사항)은 이미 별도의 nhdesign3 knowhow DB에 저장되어 있어 여기 중복 반영하지 않음 — 이 항목만 CS 도메인 전반에 재사용 가능한 Figma Plugin API 일반 원칙으로 판단해 승격.

## 8.2.5 (2026-07-17)

- 학습 1건 신규 추가: #142 Claude Code plugin.json은 skills/agents/commands를 문자열 배열로 선언하면 안 된다 — auto-discovery 방식이라 선언 시 Invalid input 에러 (principle, cs-core-memory-v1/.claude-plugin/plugin.json 직접 수정 사례)
- PENDING 1건 (2점, 저장 안 함): "마켓플레이스 플러그인 manifest 수정은 격리된 워크트리에서 브랜치+draft PR로 처리" — 기존 워크트리 격리 원칙(#138)의 재확인 사례로 판정, 신규성 낮음
- Core Memory 갱신: cs-core-memory-v1 memory-keeper가 CORE.md Recurring Issues 섹션에 동일 패턴을 신규 항목으로 기록 (Session Count 0→1)
- 출처: cs-core-memory 플러그인 설치 실패("agents: Invalid input, skills: Invalid input") 디버깅 세션 — `.claude-plugin/plugin.json`의 무효 skills/agents/commands 배열 필드 제거 + 표준 위치 밖 중복 루트 plugin.json 삭제, PR #4 (미머지)

## 8.2.4 (2026-07-17)

- 학습 2건 신규 추가: #140 표시 이름과 권한 플래그가 분리된 인증 구조에서는 이름 충돌이 사일런트 권한 오판을 만든다 (principle, react-frontend.md, skeptic CONFIRM) / #141 서브에이전트가 idle_notification만 반복하고 도구 호출이 전혀 없으면 데드락 신호로 보고 직접 실행으로 전환한다 (tactical, multi-agent-orchestration.md)
- REJECT 2건 (skeptic 반박): "pseudo-account 문자열 ID가 UUID 컬럼 쿼리를 400으로 깨뜨려도 .data ?? [] 패턴이 조용히 은폐한다" — 근거가 400 에러 로그 한 줄뿐이고 은폐 메커니즘(.data ?? [] 코드 인용, 화면이 실제로 조용히 빈 목록을 보였다는 증거) 자체는 미입증으로 판정 / "관리자/특권 토글이 함께 렌더링된 화면에서 텍스트 매칭 클릭은 프로덕션 설정을 실수로 변경할 수 있다" — 발견 서술이 "클릭했을 가능성이 있었고"로 헤징돼 있고 인과관계를 뒷받침할 트레이스가 없어 REJECT
- PENDING 2건 (3점, 저장 안 함): "새 플로팅 UI 도입 후 좌표충돌 QA는 position:fixed/sticky 필터링 없이 하면 오탐 폭주" (실용적이나 특별히 새롭지 않은 상식적 기법으로 판정) / "MCP playwright 스크린샷이 샌드박스 폰트로딩으로 타임아웃되면 DOM assertion 또는 로컬 스크린샷 실행기로 전환" (환경 특정적이라 재사용성 제한)
- Prompt Patch 시도 1건 → REVERT: idle-notification 루프 감지를 cs-end.md Phase 1에 즉시 반영 시도했으나, Phase 2.7 verifier가 "판정 라벨은 CONFIRMED이나 실제 사유는 명백한 반박"(존재하지 않는 도구명 "shutdown_request" 사용, 자기 인용 근거와 수치 불일치, 발송수단/판별기준 미지정, 파일 실행시점과 선언된 스코프 불일치)임을 지적 — 라벨보다 실제 사유 내용을 우선해 REFUTED로 재해석, 패치를 revert하고 `.experiencing-btw.json`에 pending-patch로 강등
- 프로세스 노트: marketplace.json의 cs-experiencing version 필드가 실제 VERSION 파일(8.2.3)보다 뒤처진 "8.2.1"로 드리프트돼 있던 것을 이번 버전업 중 함께 발견해 동기화함
- 출처: 먹고공부하자(Next.js 팀 점심주문 앱) 리디자인 + QA 회귀테스트 세션 — cs-ceo:ceo 서브에이전트가 idle_notification만 반복하며 무진행 상태에 빠져 직접 실행으로 전환한 뒤 Playwright로 다수의 실제 버그를 발견/수정

## 8.2.3 (2026-07-17)

- 학습 6건 신규 추가: #133 dev 오케스트레이터 스크립트의 하드코딩 포트 + 무조건 kill이 "자기 자신의 워크트리 실행" 시 메인 앱을 죽인다 (tactical, tauri-windows.md) / #134 Workflow parallel adversarial review가 "cleanup 완전 비활성화" 스코프 오류를 잡아낸 사례 (principle, multi-agent-orchestration.md, skeptic CONFIRMED) / #135 느슨한 ancestor-path 매칭이 오탐을 유발 — 코드리뷰가 놓치고 Playwright 라이브 검증이 잡아낸 사례 (tactical, debugging.md, skeptic DOWNGRADE) / #136 git worktree remove는 그 디렉터리를 cwd로 쓰는 실행 중 프로세스를 멈추지 않는다 (tactical, tauri-windows.md) / #137 상태 정리 수정은 실제 프로덕션 데이터에 합성 케이스를 주입해 전후 id-set diff로 검증 — 격리 포트 + 왕복 클린업 전제 (tactical, misc-tooling.md, skeptic DOWNGRADE) / #138 EnterWorktree "Already in a worktree session" 오류 시 ExitWorktree(remove)부터 시도 (principle, claude-code-platform.md, skeptic CONFIRM) / #139 Workflow 스크립트 프롬프트 안 리터럴 `${...}`가 sandbox에서 즉시 평가돼 크래시 (principle, claude-code-platform.md, skeptic CONFIRM)
- PENDING 5건 (2-3점, 저장 안 함, 리포트에만 노출): 워크트리 실행 시 PORT env 미전파로 인한 크래시 근본원인 / lsof 스캔 범위 미갱신으로 워크트리 서버 감지 무력화(기존 #115 "구조 리팩터 전수 스윕" 원칙과 실질적 중복) / 워크트리 삭제 시 orphan 프로세스(→ #136으로 재평가 후 승격) / vite dev-proxy 타깃 하드코딩(#115와 동일 계열 원인, 낮은 재사용성)
- 중복-갱신 규칙 적용 1건: 외부에서 삭제된 워크트리가 UI 카드로 무기한 잔존하는 문제는 독립 항목 대신 #99(debugging.md, portmanagement "표시 계층 데이터 소스" 체크리스트) 하단에 7번째 체크리스트 항목으로 addendum 병합
- 출처: portmanagement(포트관리기 Tauri 앱) 세션 — 워크트리 "실행" 크래시 수정(PR #12) → 워크트리 패널 UX + Playwright 검증(PR #13) → 사용자가 직접 지적한 스테일 UI 카드(":10136 이미 삭제된거 아닌가?") 정리(PR #14), 3개 draft PR 모두 cs-end 세션 시점 기준 미병합
- 프로세스 노트: version-scout가 마켓플레이스 레포 git diff로 확인한 실제 도메인 변경은 0건(모든 코드 변경은 별도 프로젝트 레포)이었으나, 세션 내용 자체가 cs-end/cs-experiencing 도메인 밖의 harness/tooling 지식(EnterWorktree, Workflow 스크립트 sandbox)과 일반화 가능한 프로세스 관리 지식을 다수 포함해 learning-extractor 위임 대신 오케스트레이터가 직접 세션 요약을 작성해 주입하는 방식으로 진행함

## 8.2.2 (2026-07-17)

- 학습 2건 신규 추가: #131 라이브 참조 없는 화면/유형은 발명 대신 스코프 제외 또는 reference-weak 명시 플래그 (principle, figma-design-system.md, skeptic CONFIRMED) / #132 Figma 빌드 완료 선언 전 라이브/템플릿 스크린샷 대조 게이트가 육안 검수로 못 잡는 버그를 반복 확인 (tactical, figma-design-system.md)
- REJECT 1건: "브라우저 자동화 다중 탭 evals — list_tabs 재확인 없인 탭 인덱스 드리프트로 엉뚱한 도메인에 착지" 후보는 skeptic이 "탭 인덱스 드리프트가 실제로 일어났다는 직접 증거(전/후 list_tabs 비교) 없이, 모순된 관측을 설명하려는 사후 추정에 불과하다"고 판정 → 저장하지 않고 드롭
- addendum 1건: #113(figma-design-system.md)에 반대 방향 재확인 사례 추가 — HTML 프로토타입의 임시 색상을 신뢰하지 않고 구조/콘텐츠만 소스로 삼은 사례, "속성별로 진실 축을 사전에 분리 결정" 교훈 보강
- 출처: 통신사기 본인정보 공유여부 사실조회 기능의 NDS(모바일)·web-proposal(데스크톱 웹 N2) 두 Figma 제안서 병렬 빌드 세션 — nhsec.com/mynamuh.com 브랜드 공존 재발견(원장 `mynamuh-nhsec-rebrand-flap-2026-07` 4차 정정)이 트리거. 브랜드 공존 재발견 자체는 검증 가능한 관측(같은 세션·같은 분에 두 도메인 동시 로드)이므로 nhdesign3 ledger에는 그대로 기록되지만, 그 원인으로 지목된 "탭 드리프트" 메커니즘은 미검증 추정이라 cs-experiencing 학습으로는 승격하지 않음

## 8.2.1 (2026-07-17)

- 학습 2건 신규 추가 (모두 skeptic 검증 완료): #129 AI 서브에이전트의 성능/원인 진단은 실측 재검증 없이 신뢰하지 않는다 (principle, multi-agent-orchestration.md) / #130 검증 중 실측된 신규 데이터가 유효한 결과물이면 테스트 데이터처럼 되돌리지 않는다 (tactical, misc-tooling.md)
- DOWNGRADE 1건: "claude CLI --bare vs --safe-mode" 후보는 skeptic이 "구체적 플래그명에 종속된 지식이라 tactical이 적절"로 판정 → 독립 항목화하지 않고 #37(claude-code-platform.md) addendum으로 병합
- 중복-갱신 규칙 적용 2건 (독립 항목 대신 기존 항목 addendum으로 병합):
  - #37에 addendum 2건 — `--safe-mode`(OAuth 유지) vs `--bare`(API 키 전용) 경량 부팅 모드 차이 / "배치를 단일 호출로 묶어 O(N)→O(1)" 최적화가 배치 크기 무한정 커질 때 60s 타임아웃으로 조용히 전체 실패하는 반례(청크 분할 필요)
  - #99(debugging.md)에 addendum 2건 — 웹+네이티브 이중 구현 드리프트의 두 번째 확인 사례(같은 portmanagement 프로젝트, 다른 필드) / "표시 계층 데이터 소스" 체크리스트 6번째 항목 신설(쓰기 경로가 존재해도 실행 중 조용히 실패하는 경우)
- 프로세스 노트: learning-extractor가 SKILL.md 인라인 본문만 grep해 노벨티를 사전 채점했으나, 실제 중복은 knowledge/*.md로 이관된 본문에 있었음(발견은 cs-end 세션 중 직접 grep 확장으로 이루어짐) — 향후 세션의 노벨티 체크는 SKILL.md뿐 아니라 knowledge/ 전체를 대상으로 해야 함
- 출처: portmanagement(포트 관리 Tauri+React 앱) 세션 — 기존 폴더 등록 검색 버그, AI 별명짓기 속도 개선(`--safe-mode --model haiku`), AI 배치 호출 60초 타임아웃으로 인한 카테고리 데이터 전무 문제의 근본 원인 발견·수정(청크 분할), Tauri 데스크톱 앱의 category 미지원 버그 수정, 카테고리 태그 아코디언 UI (PR #12, https://github.com/intenet1001-commits/AgentsToZ_byCS/pull/12)

## 8.2.0 (2026-07-17)

- **무결성 게이트 신설**: `plugins/shared/scripts/pre_pass.py`에 `index-check` 서브커맨드 추가 — 학습 INDEX↔본문 정합성(C1 INDEX 누락 / C2 위치 포인터 해석 / C3·C4 번호 전역 유일성 / C5 연속성 / C6 인라인 본문 상한 15)을 결정론적으로 검증. version-up STEP 2(저장 직후)와 STEP 4b(commit 게이트)에 배선. LLM 반박 패스가 3회 놓친 드리프트 클래스를 기계적으로 차단한다.
- **드리프트 일제 복구** (게이트 도입 전 축적분): INDEX 누락 #95-99·#120-123 백필(9건) / #100·#102 위치 포인터 오염 수정 / #89 앵커를 knowledge/multi-agent-orchestration.md에 추가 / 인라인 #12-16(2026-06 작성분)이 knowledge/ 이관 항목 #12-16과 번호 충돌 → #124-128 재부여(본문에 renumbered 주석으로 감사 추적).
- **본문 오프로드**: 프로젝트-특화 인라인 본문 35건을 knowledge/ 12개 파일로 이동 (figma-design-system.md·llm-patterns.md·mobile-automation.md 신설). SKILL.md 982줄→730줄, 인라인 본문 46건→11건(#1-6, #10-11, #114, #123, #128 — 오케스트레이터 도메인만). 상시 로드 비용 감소, INDEX grep 기반 recall 경로는 불변.
- **인프라 수정**: pre_pass.py가 macOS 시스템 python3(3.9)에서 `Path | None` 문법으로 즉사하던 잠재 버그 수정(`from __future__ import annotations`) — run_prepass.sh가 python3를 uv보다 먼저 시도하므로 이 머신에서 모든 게이트가 조용히 깨져 있었음.
- 배경: Supabase RDB 이관 검토(ultracode 10-agent 분석) 결론 "이관 불가/불요, 진짜 병목은 LLM-집행 불변식의 드리프트" → 저비용 개선 1-3번 즉시 실행분.

## 8.1.12 (2026-07-17)

- 학습 4건 추가 (모두 principle, skeptic CONFIRMED): #120 Figma `get_metadata`는 depth 제한 없이 큰 서브트리에서 하드 에러 — 얕은 열거는 `use_figma`로만 가능 / #121 CSS 블록 주석 속 리터럴 `*/`가 뒤따르는 규칙 전체를 조용히 삭제(스크린샷으로는 안 보임) / #122 병렬 에이전트의 공유 tmp 고정 파일명은 서로의 stale 콘텐츠와 충돌 위험 / #123 지식베이스 감사에서 row-presence는 콘텐츠 깊이를 은폐 — row-count만으로는 거짓 확신
- REJECT: "Figma read-only 오류가 동시성에 의해 트리거된다"는 후보 — skeptic REFUTED (단일 관측, 통제 재시험 없음, 원 제안자도 "possibly"로 헤징한 인과 주장이라 살리지 않고 드롭)
- 출처: nhdesign3(개인 스킬, NH 계열 Figma→Supabase 디자인 지식 학습) 세션 + 라이브 프로토타입(prototype-flame-five.vercel.app) 색상 토큰 수정 세션 — 이번 세션은 cs-* 플러그인 도메인 작업이 전혀 없었음(version-scout/doc-updater가 marketplace git diff로 확인, 실제 변경 파일 0건); DOMAINS_USED=["experiencing"]는 digest 폴백 아티팩트로 판단되어 신뢰하지 않고 세션 실제 내용으로 대체 검증함 (2026-07-17)

## 8.1.11 (2026-07-16)

- 학습 2건 추가: #118 N개 서브에이전트의 합의는 진실이 아니다 (principle) / #119 리드가 주입한 잘못된 전제는 워커의 오류가 되어 돌아온다 (principle)
- #116에 addendum: `get_metadata`는 nodeId를 줘도 GROUP 자식 서브트리를 통째로 누락한다 (241 프레임 중 105개가 빈 것으로 오보고) — 카운트는 `findAllWithCriteria`로만
- marketplace.json의 cs-experiencing 버전이 8.1.9로 뒤처져 있던 drift 동반 수정 (v8.1.10 커밋이 marketplace.json을 갱신하지 않음)

## 8.1.10 — 2026-07-16
- 학습 #114 추가: 지식 축적 스킬은 주제가 아니라 "읽기 경로(read path)"로 분할해야 학습이 쌓일수록 강해진다 (principle, skeptic CONFIRM — 함께 제출된 "토큰 캡 초과" 후보는 이 항목의 근거일 뿐이라는 이유로 REJECT되어 병합)
- 학습 #115 추가: 구조 리팩터는 다른 파일의 지시문을 조용히 깨뜨린다 — 에이전트는 아무것도 등록하지 않고 "성공"을 보고한다 (principle, skeptic CONFIRM — 리허설 탐지 기법 후보를 이 항목에 병합)
- 학습 #116 추가: Figma 커버리지는 목차나 get_metadata가 아니라 figma.root.children으로만 인증한다 (tactical — skeptic DOWNGRADE: 특정 MCP 버전의 툴 동작이라 principle 아님)
- 학습 #117 추가: 우선순위 규칙에는 "무엇이 tie-breaker가 아닌지"를 명시해야 한다 (tactical — skeptic DOWNGRADE: 관측된 실패가 아닌 서브에이전트 자기보고 반사실)
- REJECT: "토큰 캡 초과 실측"(#114로 병합), "리허설이 고아 문서를 잡는다"(#115로 병합 — 단독으로는 "테스트가 버그를 잡는다"와 구별 불가)
- Decay check: stale 3건(#7/#8/#9) 검토, deprecated 0건 — 이번 세션에 구식임을 입증할 증거 없음


## 8.1.9 — 2026-07-15
- 학습 #110 추가: NDS 감사 결과의 '지적된 노드 리스트'만 믿으면 안 됨 — 전체 프레임 색상 스윕 필요 (principle, skeptic CONFIRM)
- 학습 #111 추가: 재작성 시 토큰 값을 추측하지 말고 원본 컴포넌트에서 직접 샘플링 (principle, skeptic CONFIRM)
- 학습 #112 추가: 회귀 수정 시 임의값이 아니라 파일 내 형제 요소의 기존 컨벤션을 따른다 (principle, skeptic CONFIRM)
- 학습 #113 추가: 디자인 파일이 시스템을 준수해도 코드 프로토타입은 완전히 별개 테마로 드리프트할 수 있다 (tactical)
- 학습 #99에 addendum 추가: "반영 안 됨" 체크리스트 5번째 항목 — 사용자가 보는 화면 자체가 최신 소스를 가리키는지(브라우저 캐시/미재배포) 확인
- PENDING (미저장, 3점): "감사 결과 스코프 확대는 AskUserQuestion으로 사용자 확인" — novelty 낮음(이미 표준 운영 관행에 가까움), impact/reusability 보통
- DROPPED (pre-score 2/6): "독립적인 수정 트랙은 순차 대신 병렬 named 서브에이전트로 위임" — 이미 하네스 기본 지침(병렬화 극대화)에 내장된 관행이라 novelty 없음
- 출처: Right1(NH투자증권 해외주식 의결권 투표 MTS 프로토타입) 세션 — Figma 파일 + HTML 프로토타입 병렬 NDS 감사, 발견된 위반 수정(디스클레이머 배경/CTA 폰트/색상 통일/아이콘 오버플로우), 자동 감사 리스트 밖에 있던 잔여 색상 후속 발견·수정(퀵바 배경, 진입허브 구버전 잉크색), Figma 회귀 자가 수정, HTML/Figma 동기화 유지 (2026-07-15)

## 8.1.8 — 2026-07-14
- 학습 #106 추가: 실결제 앱은 adb 입력 인젝션을 보안 위협으로 감지해 자체 종료할 수 있다 (tactical — skeptic DOWNGRADE: 단일 기기·단일 앱 관찰)
- 학습 #107 추가: 동일 화이트라벨 벤더의 패키지명 prefix가 adb 자동화 안정성을 예측하는 신호가 될 수 있다 (tactical — skeptic DOWNGRADE: 표본 1쌍)
- 학습 #108 추가: OCR로 저신뢰도 탐지된 아이콘의 바운딩박스 중심이 실제 탭 타겟과 어긋날 수 있다 (tactical — skeptic DOWNGRADE: 단일 아이콘·앱 레이아웃 종속 수치)
- 학습 #109 추가: 안드로이드 하이브리드 앱에서 뒤로가기 도달 화면은 진입 경로에 따라 비결정적일 수 있다 (tactical)
- 출처: Ordering1(스타벅스/메가커피 주문 자동화 스킬) 세션 — 실기기(SM-G950N) adb+OCR 라이브 테스트로 Starbucks 앱의 입력 인젝션 탐지 발견(자동화 중단), Mega Coffee 앱 cart add/remove 자동화 실기기 검증 완료, OCR 아이콘 탭 좌표 버그 발견/수정 (2026-07-14)

## 8.1.7 — 2026-07-11
- 학습 #105 추가: `{false && <JSX>}` 같은 리터럴 하드 비활성화 블록은 grep `"{false &&"`로만 발견됨 (tactical — skeptic이 principle에서 downgrade: 단일 코드베이스·단일 사례로만 확인된 기법)
- PENDING (미저장, 2-3점): "read-write 불일치 필드는 grep으로 read-site 0건 확인해야 '죽은 기능' 확정 가능" / "resolved wrapper 명령 텍스트로 framework 추정하면 coordinator 스크립트를 오분류함" / "중첩 워크트리 + Vite/Node 표준 모듈 해석은 node_modules 없이도 동작 — Turbopack은 예외" — 3건 모두 기존 #99/#54 계열과 상당 부분 겹쳐 addendum 자격에도 못 미치는 점수
- DROPPED (pre-score 0-1/6): "회귀 위험 있는 라이브 테스트는 실행하지 말고 명시적으로 리스크를 기록하고 건너뛴다" — 일반론 수준, 재사용성 낮음
- 출처: portmanagement(포트 관리 프로그램) 세션 계속 — 프로젝트 메모 검색/표시, 빈 포트 추천 확대, 카테고리 브라우징 기능 복구(`{false &&`}` 죽은 코드 발견), 워크트리 실행 버튼이 프레임워크 무관하게 vite로 강제 덮어쓰던 버그 수정(Bun+Rust 양쪽) (2026-07-11)

## 8.1.6 — 2026-07-11
- 학습 #103 추가: git add로 스테이징한 파일도 커밋 전에 내용을 직접 열어 확인해야 한다 — PII/실데이터 유출 방지 (principle, skeptic CONFIRM)
- 학습 #104 추가: OpenAI 추론형(reasoning-tier) 모델은 temperature 기본값(1) 외 다른 값을 거부한다 (tactical — skeptic이 principle에서 downgrade: 벤더 API/모델-버전 종속 사실)
- PENDING (미저장, 2-3점): "다운스케일 스크린샷 텍스트는 크롭 확대·DOM 대조 전엔 버그로 단정 금지" / "browse 도구 자체 커서 오버레이를 앱 UI로 오인 주의" / "browse fill 실패 시 js 서브커맨드로 네이티브 setter 우회" / "CLAUDE.md 스킬 라우팅이 무관 스킬의 사전조건(클린 트리)을 강제할 수 있음" — 4건 모두 노벨티는 있으나 impact/reusability가 낮아 게이트 미통과
- DROPPED (pre-score 1/6): "bun이 ~/.bun/bin에 있어도 기본 PATH에 없음" — 특정 로컬 환경 설정 이슈, 범용성 없음
- 출처: meokgo-study(먹고공부하자, Next.js 팀 점심/커피 주문 앱) `/qa` 세션 — CS 플러그인 도메인 작업 없음(gstack 마켓플레이스의 `/qa` 스킬만 사용). PII 포함 DB export 파일 커밋 직전 발견·제외, AI 추천 502 버그(reasoning 모델 temperature 미지원) 발견·수정·검증 (2026-07-11)

## 8.1.5 — 2026-07-11
- 학습 #100 추가: git worktree prune는 locked 항목을 설계상 조용히 건너뛴다 — remove 전 unlock 선행 필수 (principle, skeptic CONFIRM, error-ref: ERR-2026-07-11-001)
- 학습 #101 추가: git 계산값 0은 여러 실제 히스토리를 뭉갤 수 있다 — UI 라벨은 측정값을 설명해야지 이유를 단언하면 안 된다 (principle, skeptic CONFIRM)
- 학습 #102 추가: 심볼릭 링크를 지나는 경로에서 문자열 prefix 필터가 조용히 실패할 수 있다 (principle, skeptic CONFIRM)
- 학습 #99 addendum ×2: (1) 웹/네이티브 이중 백엔드는 한쪽만 고쳐선 안 되고 양쪽 다 별도 빌드/체크로 검증해야 한다 (2) "표시 계층 데이터 소스" 체크리스트에 "쓰기 경로가 실제로 존재하는가" 4번째 항목 추가 (둘 다 skeptic CONFIRM, #99와 상황 인접해 addendum 처리)
- REJECTED (skeptic): "'머지 에러' 리포트 조사 시 먼저 미해결 merge 상태부터 확인" — 인과관계가 정황적 추정에 그쳐 원칙으로 확정 불가 판정
- DROPPED (pre-score 1/6): "네이티브 파일 피커 버튼 추가(osascript/OpenFileDialog/tauri dialog)" — 범용 인사이트 없는 구현 요약
- 출처: portmanagement(포트 관리 프로그램) 세션 — CS 플러그인 도메인 작업 없음. 워크트리 lock/prune 버그, Rust/TS 이중 백엔드 drift, UI 카운터 dead-write-path, git 계산값 라벨 모호성, symlink 경로 필터 버그를 disposable 테스트 repo로 직접 재현·검증 후 채집 (2026-07-11)

## 8.1.4 — 2026-07-09
- 학습 #97 추가: worktree가 main을 점유 중이면 `gh pr merge`가 로컬 브랜치 동기화 실패로 막힌다 — `gh api PUT merge`로 우회 (tactical, skeptic 검증 대상 아님)
- 학습 #98 추가: 웹·앱이 같은 머신에서 동시 접근하는 상태는 localStorage 대신 공유 파일 + 이중 접근 경로로 관리한다 (tactical — skeptic이 principle에서 downgrade: 저장 형식은 project-specific)
- 학습 #99 추가: "왜 반영이 안 됐지" 류 버그는 표시 계층의 데이터 소스 불일치가 원인인 경우가 많다 — 재시작/저장소 범위/이벤트 커버리지부터 점검 (tactical — skeptic이 principle에서 downgrade: 기존 디버깅 상식의 재확인)
- PENDING (미저장, 2-3점): "클릭 로그만으론 실제 git 활동 미반영" 학습 후보 — 노벨티 있으나 impact/reusability 낮아 게이트 미통과
- 출처: portmanagement(포트 관리 프로그램) 세션 — CS 플러그인 도메인 작업 없음, 도메인 무관 범용 운영 패턴 3건 채집 (2026-07-09)

## 8.1.3 — 2026-07-08
- 학습 #95 추가: macOS 앱 샌드박스 컨테이너 파일은 Full Disk Access/Automation 권한 없는 터미널에서 접근 불가 (principle, skeptic CONFIRM)
- 학습 #96 추가: React 클로저 stale state + Playwright ref 재사용은 querySelector 재조회 + 별도 evaluate 호출 + 클릭 간 지연으로 우회 (principle, skeptic CONFIRM)
- 출처: Derivative1(쉬운 해외파생 프로토타입) 세션 — CS 플러그인 도메인 작업 없음, 도메인 무관 범용 운영 패턴 2건만 채집 (2026-07-08)

## 8.1.2 — 2026-07-05
- 학습 #92 추가: 이중 로그인 아키텍처에서 세션 게이트 API는 다수 유저에게 상시 401을 낼 수 있다 (principle, error-ref: ERR-2026-07-05-001)
- 학습 #93 추가: 이름/식별자 퍼지 매칭은 substring 포함 대신 Levenshtein 거리만 사용 (principle)
- 학습 #94 추가: 공유 렌더 함수의 early-return 순서가 서브플로우 상태를 가릴 수 있다 (principle)
- 학습 #4 addendum: CS-plugin 자기개선 외에 클라이언트 프로젝트 코드 개선을 위한 외부 교육자료(.ipynb) 분석에도 동일 패턴 적용 확인
- 출처: 먹고공부하자 대신주문(proxy-order) 기능 401 버그 + 오매칭 버그 + 렌더 소프트락 버그 수정 세션 (2026-07-05)

## 8.1.1 — 2026-07-03
- 학습 #90 추가: Next.js API route 준-정적 데이터는 모듈-레벨 TTL 캐시로 반복 DB 조회 제거 (principle)
- 학습 #91 추가: 대시보드 미해결처럼 보이는 값 — snapshot 필드 vs live-computed 필드 구분 (principle, skeptic CONFIRM)
- 학습 #76 addendum: anon-client + `void` fire-and-forget UPDATE가 문서화 이후에도 같은 코드베이스 내 다른 파일에서 재발함을 확인 (skeptic CONFIRM) — 재발 방지책으로 grep 스캔/lint 강제 필요성 기록
- frontmatter/plugin.json version 표기 drift 수정 (SKILL.md 8.0.7 → 실제 plugin.json 8.1.0에 동기화 후 8.1.1로 통합 bump)
- 출처: 먹고공부하자 챗봇 응답 지연 + 자기개선 RLS silent-failure 버그 수정 + 대시보드 미분류 표시 조사 세션 (2026-07-03)

## 8.1.0 — 2026-07-02
- 멀티에이전트 오케스트레이션 벤치마크(CrewAI/AutoGen/ChatDev) 이식
- 학습 #89 추가 + knowledge/multi-agent-orchestration.md 신규 (P1~P5 요약, 근거 포함)
- experiencing-lead: Pipeline Decision Matrix → 선언적 chain 매니페스트(P3) 연동, 재실행 루프 종료식(P2) 정식화
- 출처: cs-ceo Fable5 업그레이드 세션 (shared/ORCHESTRATION-PATTERNS.md)

## 8.0.6 (2026-06-17)
- 학습 #85 추가: minified 번들 배포 검증 패턴 (tactical)
- 학습 #86 추가: 세그먼트 컬럼 우선 / 전체 합계 fallback 원칙 (principle, skeptic CONFIRM)

## 8.0.7 — 2026-06-30
- 학습 #87 추가: 구조화 JSON 추출 태스크에는 소형 LLM + 출력 토큰 상한 축소가 충분하다 (tactical)
- 학습 #88 추가: 단일 LLM 호출에서 다중 엔티티를 동시 추출하여 복합 발화를 처리한다 (principle)
- 출처: 먹고공부하자 voice-order 복합 입력 처리 + gpt-4o-mini 교체 세션
