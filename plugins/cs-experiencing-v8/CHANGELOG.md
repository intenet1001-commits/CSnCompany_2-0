
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
