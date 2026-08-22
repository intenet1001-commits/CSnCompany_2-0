---
name: cs-experiencing
description: |
  CS 에이전트가 참조하는 내부 경험 지식 저장소.
  Use for relevant prior-lesson recall or when invoked internally by cs-memory upgrade.
  Do not use it as a public test/plan/review/design wrapper or unconditional version-up command.
version: 9.1.2
allowed-tools:
  - Read
  - Write
  - Edit
  - Bash
---

# Experiencing Knowledge Backend

공통 경험지식의 조회·검증·저장만 담당한다. 사용자용 실행 명령은 제공하지 않는다.

## 공개 진입점

- 장기기억 수집: `/cs-memory:learn`
- 관련 에이전트 개선: `/cs-memory:upgrade`
- 통합 상태: `/cs-memory:status`
- 세션에서만 알 수 있는 경험 보충: `/cs-end`

테스트·플랜·리뷰·디자인은 각각의 도메인 스킬을 직접 호출한다. `update`,
`version-up all`, `checkpoint`, `pipeline`을 이 백엔드에서 실행하지 않는다.

## 저장소 위치

```text
plugins/cs-experiencing-v*/skills/experiencing/
├── SKILL.md              # INDEX와 소수의 오케스트레이터 원칙
└── knowledge/*.md        # 주제별 경험 본문
```

최신 디렉터리는 `ls -d plugins/cs-experiencing-v* | sort -V | tail -1`로 찾는다.
후보 큐의 단일 위치는 `~/.claude/.experiencing-btw.json`이다.

## 조회 프로토콜

1. 현재 태스크의 기술 스택과 도메인 명사를 추출한다.
2. 아래 학습 INDEX에서 키워드가 맞는 상위 2~3건만 고른다.
3. INDEX의 위치 포인터가 가리키는 본문만 읽는다.
4. 관련 항목이 없으면 질문이나 추가 분석 없이 생략한다.
5. 전체 SKILL 또는 모든 `knowledge/*.md`를 한 번에 로드하지 않는다.

## 업그레이드 쓰기 계약

`cs-memory:upgrade`만 후보를 소비한다.

1. novelty·impact·reuse를 각각 0~2점으로 평가한다.
2. 0~1점은 reject, 2~3점은 pending, 4~6점은 promote 또는 기존 항목에 병합한다.
3. `principle` 후보는 배치당 한 번의 skeptic pass를 거친다.
4. 프로젝트 특화 내용은 프로젝트 기억에 남기고 공통 INDEX에 넣지 않는다.
5. 새 본문은 관련 `knowledge/<topic>.md`에 저장하고 INDEX 행은 정확히 하나만 추가한다.
6. 에이전트 행동이 달라지는 교훈만 담당 도메인의 SKILL·command·agent 규칙에 반영한다.
7. 영향받지 않은 도메인은 수정하거나 버전업하지 않는다.
8. 성공 후에만 `learn-update-status`로 후보 상태를 바꾼다.

## 필수 게이트

쓰기 전후에 다음을 실행한다.

```bash
bash plugins/shared/run_prepass.sh index-check
bash plugins/shared/run_prepass.sh version-check "<changed-plugin-dir>"
```

게이트가 실패하면 이번 업그레이드의 편집만 되돌리고 후보는 pending으로 유지한다.
학습만 추가된 경우 기존 디렉터리에서 patch 버전을 올린다. 새 `-vN` 디렉터리는
실제 스키마·구조 세대가 바뀔 때만 만든다.

---

## 버전 철학

- **도메인 디렉토리명** (`CS-test-v2`): 스키마/구조 버전 — 큰 구조 변경 시에만 변경
- **VERSION 파일**: 콘텐츠 버전 — 새 학습이 추가될 때마다 증가
- **plugin.json version**: 전체 플러그인 버전 — semver (major.minor.patch)
- **cs-experiencing 자체 버전업 시**: `plugin.json version` + SKILL.md frontmatter `version` + `VERSION` 파일을
  **반드시 같은 커밋에서 함께** 갱신한다 (세 값의 불일치 = 버전 드리프트, 약한 모델이 잘못된 경로를 따르는 원인)

---

## experiencing 노하우

### 학습 INDEX (1줄/항목, 단일 진실)

**검색 프로토콜 (read-side):** 과거 경험을 소비하는 도메인 스킬은 실행 전에 이 INDEX를
현재 태스크의 키워드(기술 스택·도메인 명사)로 grep하고,
매칭된 상위 2-3건의 본문을 해당 위치(인라인 또는 `knowledge/<topic>.md`)에서 읽어
**디스패치 프롬프트에 그대로 주입**한다. 매칭 없으면 주입 생략 (질문/지연 금지).

```bash
# 예: 태스크 키워드가 "worktree vite" 인 경우
grep -i -E "worktree|vite" skills/experiencing/SKILL.md | grep "^|" | head -3
```

신규 학습 추가 시: INDEX에 1줄 추가(번호 = 현재 max+1) + 본문은 매칭되는 `knowledge/<topic>.md`에 append
(주제 파일이 없으면 새로 생성). 백엔드 자체 무결성·라우팅 원칙만 아래 인라인 섹션에 둔다.

| # | 제목 | tier | 태그 | 위치 |
|---|------|------|------|------|
| 1 | version-up은 학습 캡처 + 디렉토리 복사 두 단계여야 한다 (2026-04-11) | principle | orchestrator, version-up | 인라인 |
| 2 | `all` 키워드로 3개 도메인 한번에 버전업 (2026-04-11) | principle | orchestrator, version-up, all | 인라인 |
| 3 | AI 자동 학습 추출 — 수동 입력보다 먼저 시도 (2026-04-14) | principle | orchestrator, 학습추출, AI분석 | 인라인 |
| 4 | 외부 소스 학습 통합 — bkit·Karpathy·gstack 패턴 (2026-04-20) | principle | orchestrator, bkit, karpathy, gstack | 인라인 |
| 5 | bkit btw 패턴 — 세션 중 아이디어 즉시 캡처 (2026-04-20) | principle | orchestrator, btw, 캡처 | 인라인 |
| 6 | gstack Iron Law — version-up 루프 실패 상한 (2026-04-20) | principle | orchestrator, iron-law, retry, STUCK | 인라인 |
| 7 | osascript 디버깅 — 레이어 격리로 root cause 빠르게 찾기 (2026-04-25) | tactical | osascript, 디버깅, bun, 레이어격리 | knowledge/debugging.md |
| 8 | Tauri webview에서 `window.open()` silent 실패 — 외부 URL은 항상 API.openInChrome (2026-04-26) | tactical | tauri, window.open, 외부URL | knowledge/react-frontend.md |
| 9 | ClipboardItem text/html+text/plain 이중 포맷으로 Slack 하이퍼링크 복사 (2026-04-28) | tactical | clipboard, slack, html, 하이퍼링크 | knowledge/react-frontend.md |
| 10 | `/compact`는 스킬에서 직접 호출 불가 — 생성된 요약을 제안하는 패턴으로 우회 (2026-05-01) | principle | claude-code, compact, 내장명령 | 인라인 |
| 11 | Claude Code 훅 exit code — non-zero는 UI를 블로킹한다 (2026-05-02) | principle | claude-code, hooks, exit-code, 블로킹 | 인라인 |
| 12 | Git worktree base ref: local branch vs. remote tracking — unpushed commits invisible (2026-05-17) | principle | git-worktree, base-ref, origin | knowledge/git-worktree.md |
| 13 | Browser cache busting: `?t=Date.now()` + `cache: 'no-store'` 둘 다 필요 (2026-05-17) | principle | fetch, cache, no-store, 캐시버스팅 | knowledge/react-frontend.md |
| 14 | Build "unchanged" ≠ 파일 미재기록 — onRefresh는 항상 호출해야 (2026-05-17) | principle | build, refresh, unchanged | knowledge/react-frontend.md |
| 15 | React 부모→자식 이벤트: 모노토닉 카운터 증가 패턴 (2026-05-17) | tactical | react, counter, props, 이벤트 | knowledge/react-frontend.md |
| 16 | Node.js native `fs.watch({ recursive: true })` macOS에서 chokidar 없이 동작 (2026-05-17) | principle | nodejs, fs.watch, macos, chokidar | knowledge/misc-tooling.md |
| 17 | HTML 목록 스크래핑 — 복합 정규식 대신 분리 추출 후 index 매칭 (2026-05-17) | tactical | 정규식, 스크래핑, html | knowledge/debugging.md |
| 18 | `[^"']*` 정규식 — 혼합 따옴표 HTML 속성에서 조기 종료 (2026-05-17) | tactical | 정규식, html-attribute, 따옴표 | knowledge/debugging.md |
| 19 | SSE 이벤트 핸들러에서 연관 React state 동시 호출 필요 (2026-05-17) | tactical | react, sse, state, 배칭 | knowledge/react-frontend.md |
| 20 | Pull merge: 동일 폴더 다른 ID 중복 방지 — 결정적 ID + folderPath dedup (2026-05-17) | principle | supabase, dedup, sync, deterministic-id | knowledge/data-sync-db.md |
| 21 | Merge 전략: 사용자 직접 편집 필드는 local-first (2026-05-17) | principle | merge, local-first, 동기화 | knowledge/data-sync-db.md |
| 22 | ~/.claude/settings.json extraKnownMarketplaces는 객체 shape 필수 (2026-05-17) | tactical | claude-code, marketplace, settings.json | knowledge/claude-code-platform.md |
| 23 | 배포 웹 UI 버그는 빌드 설정 먼저 확인 — `vercel.json` / `vite.*.config.ts` 추적 (2026-05-17) | principle | vercel, vite, 빌드설정, 진입점 | knowledge/deployment.md |
| 24 | 멀티 entry Vite 프로젝트는 entry별 분리 모델 (2026-05-17) | tactical | vite, multi-entry, config | knowledge/deployment.md |
| 25 | globals.css element selector vs 인라인 스타일 명시도 충돌 (2026-05-19) | principle | css, 명시도, tailwind, globals | knowledge/css-design.md |
| 26 | sticky 헤더 대응 스크롤 오프셋 패턴 (2026-05-19) | tactical | scroll, sticky, offset | knowledge/css-design.md |
| 27 | aria-selected CSS selector 기반 chip 상태 패턴 (2026-05-19) | tactical | aria-selected, chip, css | knowledge/css-design.md |
| 28 | CSS 디자인 토큰 통일 — bg-white/bg-slate-900 교체 전략 (2026-05-19) | principle | css-token, 다크모드, tailwind | knowledge/css-design.md |
| 29 | Git Worktree 파일 격리 — 수정은 해당 브랜치에만 적용 (2026-05-20) | principle | git-worktree, 격리, 파일 | knowledge/git-worktree.md |
| 30 | Vite Dev Server는 자신의 소스 디렉토리만 Watch (2026-05-20) | principle | vite, watch, worktree, hmr | knowledge/git-worktree.md |
| 31 | Object Spread 시 commandPath 등 상위 속성 상속 차단 패턴 (2026-05-20) | tactical | spread, commandPath, undefined | knowledge/react-frontend.md |
| 32 | Worktree base ref mismatch — origin/main vs 로컬 main (2026-05-22) | tactical | git-worktree, origin, mismatch | knowledge/git-worktree.md |
| 33 | 단일 레코드 반복 태스크의 done 리셋 패턴 (2026-05-22) | principle | supabase, recurring, done-리셋 | knowledge/data-sync-db.md |
| 34 | 완료 후 즉시 재등장: virtual spread 패턴으로 다음 주기 표현 (2026-05-22) | principle | react, virtual-spread, 주기UI | knowledge/react-frontend.md |
| 35 | done_at UTC timestamptz → 로컬 날짜 변환 비교 (2026-05-22) | tactical | timezone, timestamptz, utc | knowledge/data-sync-db.md |
| 36 | Python으로 merge conflict marker를 즉석 파싱·해결 (2026-05-22) | tactical | merge-conflict, python, marker | knowledge/git-worktree.md |
| 37 | Claude Code CLI를 Bun 서버 서브프로세스로 AI 추론 백엔드로 활용 (2026-05-23) | principle | claude-cli, bun, subprocess, -p | knowledge/claude-code-platform.md |
| 38 | 사이드바 버튼 중복 — 메인 영역이 primary, 사이드바는 secondary (2026-05-23) | tactical | ui, 사이드바, 버튼중복 | knowledge/misc-tooling.md |
| 39 | SVG 일러스트로 스크린샷 완전 대체 전략 (2026-05-23) | principle | svg, 스크린샷, 일러스트 | knowledge/misc-tooling.md |
| 40 | Bash heredoc으로 멀티라인 파일 생성 (Write 도구 차단 우회) (2026-05-23) | principle | heredoc, bash, write-차단 | knowledge/git-worktree.md |
| 41 | Python 인라인 스크립트로 TSX 수술적 문자열 교체 (Edit 도구 차단 우회) (2026-05-23) | principle | python, edit-차단, str.replace | knowledge/git-worktree.md |
| 42 | useState + onChange 정규화 → live CodeBlock 주입 패턴 (2026-05-23) | tactical | react, input, 정규화, codeblock | knowledge/react-frontend.md |
| 43 | Git worktree 삭제 후에도 세션 도구 차단 상태 유지 (2026-05-23) | tactical | worktree, 도구차단, 세션 | knowledge/git-worktree.md |
| 44 | ScreenshotPlaceholder 점진적 fallback 설계 패턴 (2026-05-23) | tactical | placeholder, fallback, 스크린샷 | knowledge/misc-tooling.md |
| 45 | 마켓플레이스 플러그인 폴더명 vs 캐노니컬 이름 — 항상 manifest 우선 (2026-05-23) | principle | marketplace, canonical-name, manifest | knowledge/claude-code-platform.md |
| 46 | claude --bg 플래그: CLI 내장 백그라운드 에이전트 실행 (2026-05-23) | principle | claude-cli, bg, 백그라운드 | knowledge/claude-code-platform.md |
| 47 | Next.js에서 useState 초기화에 localStorage 사용 금지 — useEffect 패턴 필수 (2026-05-23) | principle | nextjs, localstorage, ssr, useeffect | knowledge/react-frontend.md |
| 48 | 터미널 선택자 UI — TYPE(라디오)과 MODE(토글) 분리 패턴 (2026-05-23) | tactical | ui, radio, toggle, type-mode | knowledge/react-frontend.md |
| 49 | known_marketplaces.json은 신뢰할 만한 source-of-truth가 아니다 — 자동 기록된 URL은 잘못될 수 있음 (2026-05-23) | principle | known_marketplaces, 검증, source | knowledge/claude-code-platform.md |
| 50 | 아이콘 Morph — absolute+scale/opacity 토글 패턴 (2026-05-23) | tactical | icon, transition, morph | knowledge/react-frontend.md |
| 51 | Tailwind v4 `@theme inline` — CSS 변수 → 유틸리티 브리지 필수 (2026-05-23) | principle | tailwind-v4, theme-inline, css변수 | knowledge/css-design.md |
| 52 | `navigator.clipboard` 비보안 컨텍스트 Fallback 패턴 (2026-05-23) | tactical | clipboard, fallback, securecontext | knowledge/react-frontend.md |
| 53 | fp_logs 복원 시 failed 상태는 silent drop — stale 실패 기록을 오류 배지로 부활 금지 (2026-05-30) | principle | 로그복원, 상태, failed | knowledge/data-sync-db.md |
| 54 | Git 워크트리의 node_modules — Turbopack은 심링크 거부, npm install 필수 (2026-05-30) | principle | worktree, node_modules, turbopack | knowledge/git-worktree.md |
| 55 | 시스템 공통 데이터는 임의 대표 엔트리에서 읽어도 안전 (2026-05-30) | tactical | quota, system-wide, 대표엔트리 | knowledge/data-sync-db.md |
| 56 | vercel --prod는 Claude Code auto-mode에서 항상 차단됨 (2026-05-30) | tactical | vercel, prod, auto-mode, 차단 | knowledge/deployment.md |
| 57 | content 컬럼 센티넬 접두사로 스키마 마이그레이션 없이 새 콘텐츠 타입 추가 (2026-05-30) | principle | sentinel, schema, content컬럼 | knowledge/data-sync-db.md |
| 58 | window CustomEvent로 React 레이어 밖에서 컴포넌트 간 느슨한 결합 (2026-05-30) | principle | customevent, pub-sub, react | knowledge/react-frontend.md |
| 59 | Next.js App Router에서 인증 사용자 전용 UI는 (main)/layout에 마운트 (2026-05-30) | tactical | nextjs, layout, auth, 라우트그룹 | knowledge/react-frontend.md |
| 60 | 기능 구현 전 코드베이스에서 기존 구현 탐색 필수 (2026-05-30) | principle | grep, 기존구현, 탐색 | knowledge/misc-tooling.md |
| 61 | 메모리 불만 시 먼저 어느 프로세스가 RSS를 소유하는지 확인 (2026-05-30) | principle | 메모리, ps, rss, 프로세스 | knowledge/debugging.md |
| 62 | manualChunks는 캐시 효율이지 런타임 메모리 감소가 아니다 (2026-05-30) | principle | manualchunks, 캐시, react-lazy | knowledge/react-frontend.md |
| 63 | document.hidden으로 setInterval 폴링 게이팅 — Playwright로 검증 (2026-05-30) | principle | polling, document.hidden, setinterval | knowledge/react-frontend.md |
| 64 | React.lazy + Suspense는 Tauri WebKit 웹뷰에서 정상 동작 (2026-05-30) | tactical | react-lazy, suspense, tauri | knowledge/react-frontend.md |
| 65 | Playwright adversarial 워크플로우로 메모리 누수 후보 기각 (2026-05-30) | tactical | playwright, 메모리검증, heap | knowledge/debugging.md |
| 66 | 포트 매니저 앱 JS heap 기준값 — 15-18MB 안정 (2026-05-30) | tactical | heap, 기준값, 포트매니저 | knowledge/debugging.md |
| 67 | 배포 직후 화면 깨짐 — Vercel CDN 번들 mismatch artifact (2026-06-09) | tactical | vercel, cdn, 재배포 | knowledge/deployment.md |
| 68 | 대형 JSX 파일에서 `</>}` vs `})()}` 구조 추적 패턴 (2026-06-09) | principle | jsx, 구조추적, fragment, iife | knowledge/debugging.md |
| 69 | 의존성 제거 결정의 커플링 드리프트 — repo-wide grep 통과 후에만 ✅ 반영됨 (2026-06-12) | principle | 커플링, 드리프트, grep, 반영됨 | knowledge/claude-code-platform.md |
| 70 | 외부 소스 원칙 추출 — 생성/기각(adversarial refuter) 단계 분리 (2026-06-12) | tactical | 원칙추출, refuter, 기각률 | knowledge/claude-code-platform.md |
| 71 | 새 프로토콜은 grep 가능한 준수 아티팩트 문자열과 함께 설계 (2026-06-12) | principle | 프로토콜, 아티팩트, 검증가능성 | knowledge/claude-code-platform.md |
| 72 | 하드코딩 시크릿 제거 ≠ 완료 — provider 측 rotation이 별도 필수 단계 (2026-06-12) | principle | 보안, 시크릿, rotation, settings | knowledge/claude-code-platform.md |
| 73 | 컨텍스트 없는 재개 요청 — episodic memory 검색을 첫 단계로 (2026-06-12) | principle | episodic-memory, 재개, 세션복원 | knowledge/claude-code-platform.md |
| 74 | JSON 설정 파일 수정은 텍스트 편집 대신 json.load/json.dump 라운드트립 (2026-06-12) | tactical | json, settings, python, 안전편집 | knowledge/claude-code-platform.md |
| 75 | GitHub Actions schedule cold-start trap — 파일이 없던 시각의 크론은 소급 발화하지 않는다 (2026-06-14) | principle | github-actions, schedule, cron, cold-start | knowledge/deployment.md |
| 76 | NEXT_PUBLIC_ anon key를 서버 전용 route에서 쓰면 RLS에 silently 차단된다 (2026-06-14) | principle | supabase, anon-key, service-role, RLS, nextjs | knowledge/deployment.md |
| 77 | fp_logs unique index를 분산 뮤텍스로 활용 — Redis 없이 serverless 하루 1회 실행 보장 (2026-06-14) | principle | mutex, unique-index, serverless, fp_logs, sentinel | knowledge/data-sync-db.md |
| 78 | 멀티-phase 서버리스 함수는 phase 경계마다 wall-clock 예산 점검을 삽입한다 (2026-06-14) | principle | serverless, budget-guard, maxDuration, partial-response | knowledge/deployment.md |
| 79 | curl에 --max-time 없이 GitHub Actions에서 hang 시 SIGKILL — 에러 원인 알 수 없음 (2026-06-14) | tactical | curl, max-time, github-actions, timeout | knowledge/deployment.md |
| 80 | GitHub Actions run: 블록에서 secrets는 env: 블록으로 분리해야 shell injection 방지 (2026-06-14) | principle | github-actions, secrets, env-block, shell-injection | knowledge/deployment.md |
| 81 | Windows 플랫폼 기능은 React/TS/Rust 3-레이어 동시 점검 필수 (2026-06-14) | principle | tauri, windows, platform, isWindows, cfg! | knowledge/tauri-windows.md |
| 82 | spawn_wt_cmd — Windows Terminal(wt.exe) 없을 때 cmd.exe 폴백 패턴 (2026-06-14) | tactical | tauri, windows, terminal, spawn, wt.exe | knowledge/tauri-windows.md |
| 83 | 빌드 아티팩트 unstaged → git pull --rebase 실패 (2026-06-14) | tactical | git, pull, rebase, unstaged, build-artifact | knowledge/git-worktree.md |
| 84 | 멀티기기 build-number 역행 방지 — 빌드 전 pull 필수 (2026-06-14) | tactical | tauri, build-number, multi-device, pull | knowledge/tauri-windows.md |
| 85 | minified 번들에서 배포 반영 검증은 property name / JS 패턴으로 (2026-06-17) | tactical | vercel, minify, bundle, 배포검증, property-name | knowledge/deployment.md |
| 86 | 세그먼트별 컬럼 있을 때 전체 합계 fallback은 세그먼트값 NULL 조건에만 (2026-06-17) | principle | cus_type, fallback, 집계, segment, data-modeling | knowledge/data-sync-db.md |
| 87 | 구조화 JSON 추출 태스크에는 소형 LLM + 출력 토큰 상한 축소가 충분하다 (2026-06-30) | tactical | llm, gpt-4o-mini, token, latency, structured-output | knowledge/llm-patterns.md |
| 88 | 단일 LLM 호출에서 다중 엔티티를 동시 추출하여 복합 발화를 처리한다 (2026-06-30) | principle | llm, schema, multi-entity, voice-order, response-design | knowledge/llm-patterns.md |
| 89 | 멀티에이전트 오케스트레이션 벤치마크 — CrewAI/AutoGen/ChatDev → P1~P5 이식 (2026-07-02) | principle | orchestration, crewai, autogen, chatdev, speaker-selection, termination, chain-manifest, role-play, persona | knowledge/multi-agent-orchestration.md |
| 90 | Next.js API route의 준-정적 데이터는 모듈-레벨 TTL 캐시로 요청당 반복 DB 조회를 제거한다 (2026-07-03) | principle | nextjs, cache, ttl, serverless, supabase, latency | knowledge/deployment.md |
| 91 | 대시보드 미해결처럼 보이는 값 — snapshot 필드 vs live-computed 필드 구분 (2026-07-03) | principle | dashboard, snapshot-field, netting, ux, debugging | knowledge/debugging.md |
| 92 | 이중 로그인 아키텍처에서 세션 게이트 API는 다수 유저에게 상시 401을 낼 수 있다 (2026-07-05) | principle | auth, nextauth, session, localstorage, dual-login, 401 | knowledge/debugging.md |
| 93 | 이름/식별자 퍼지 매칭은 substring 포함 대신 Levenshtein 거리만 사용 (2026-07-05) | principle | fuzzy-match, levenshtein, substring, 오매칭, string-matching | knowledge/debugging.md |
| 94 | 공유 렌더 함수의 early-return 순서가 서브플로우 상태를 가릴 수 있다 (2026-07-05) | principle | react, early-return, render-order, sub-flow, softlock | knowledge/react-frontend.md |
| 95 | macOS 앱 샌드박스 컨테이너 파일은 Full Disk Access/Automation 권한 없는 터미널에서 접근 불가 (2026-07-08) | principle | macos, tcc, sandbox, containers, full-disk-access | knowledge/misc-tooling.md |
| 96 | React 클로저 stale state + Playwright ref 재사용 — querySelector 재조회 + 별도 evaluate + 클릭 간 지연으로 우회 (2026-07-08) | principle | react, playwright, stale-state, closure, evaluate | knowledge/react-frontend.md |
| 97 | worktree가 main을 점유 중이면 gh pr merge 실패 — gh api PUT merge로 우회 (2026-07-09) | tactical | git-worktree, gh, pr-merge, api | knowledge/git-worktree.md |
| 98 | 웹·앱 동시 접근 상태는 localStorage 대신 공유 파일 + 이중 접근 경로로 관리 (2026-07-09) | tactical | localstorage, dual-surface, tauri, shared-file | knowledge/data-sync-db.md |
| 99 | "왜 반영이 안 됐지" 버그는 표시 계층이 참조하는 데이터 소스부터 점검 (2026-07-09) | tactical | stale-state, read-path, restart, debugging | knowledge/debugging.md |
| 100 | git worktree prune는 locked 항목을 설계상 조용히 건너뛴다 — remove 전 unlock 선행 필수 (2026-07-11) | principle | git-worktree, locked, prune, unlock | knowledge/git-worktree.md |
| 101 | git 계산값 0은 여러 실제 히스토리를 뭉갤 수 있다 — UI 라벨은 측정값을 설명해야지 이유를 단언하면 안 된다 (2026-07-11) | principle | git, ui-label, ambiguity, rev-list | knowledge/git-worktree.md |
| 102 | 심볼릭 링크를 지나는 경로에서 문자열 prefix 필터가 조용히 실패할 수 있다 (2026-07-11) | principle | symlink, realpath, path-filter, macos | knowledge/git-worktree.md |
| 103 | git add로 스테이징한 파일도 커밋 전에 내용을 직접 열어 확인해야 한다 — PII/실데이터 유출 방지 (2026-07-11) | principle | git, pii, data-safety, staging, commit-review | knowledge/git-worktree.md |
| 104 | OpenAI 추론형(reasoning-tier) 모델은 temperature 기본값(1) 외 다른 값을 거부한다 (2026-07-11) | tactical | openai, temperature, reasoning-model, api-error, gpt-5 | knowledge/llm-patterns.md |
| 105 | `{false && <JSX>}` 같은 리터럴 하드 비활성화 블록은 grep `"{false &&"`로만 발견됨 (2026-07-11) | tactical | react, jsx, dead-code, hard-disable, grep | knowledge/react-frontend.md |
| 106 | 실결제 앱은 adb 입력 인젝션을 보안 위협으로 감지해 자체 종료할 수 있다 (2026-07-14) | tactical | adb, android, security-sdk, mobile-automation, anti-tampering | knowledge/mobile-automation.md |
| 107 | 동일 화이트라벨 벤더의 패키지명 prefix가 adb 자동화 안정성을 예측하는 신호가 될 수 있다 (2026-07-14) | tactical | adb, android, package-name, whitelabel, heuristic | knowledge/mobile-automation.md |
| 108 | OCR로 저신뢰도 탐지된 아이콘의 바운딩박스 중심이 실제 탭 타겟과 어긋날 수 있다 (2026-07-14) | tactical | ocr, vision-framework, bounding-box, tap-coordinate, ui-automation | knowledge/mobile-automation.md |
| 109 | 안드로이드 하이브리드 앱에서 뒤로가기 도달 화면은 진입 경로에 따라 비결정적일 수 있다 (2026-07-14) | tactical | android, back-navigation, hybrid-app, ui-automation | knowledge/mobile-automation.md |
| 110 | NDS 감사 결과의 '지적된 노드 리스트'만 믿으면 안 됨 — 전체 프레임 색상 스윕 필요 (2026-07-15) | principle | design-system, audit, figma, sweep, nds | knowledge/figma-design-system.md |
| 111 | 재작성 시 토큰 값을 추측하지 말고 원본 컴포넌트에서 직접 샘플링 (2026-07-15) | principle | design-token, figma, sampling, code-generation, migration | knowledge/figma-design-system.md |
| 112 | 회귀 수정 시 임의값이 아니라 파일 내 형제 요소의 기존 컨벤션을 따른다 (2026-07-15) | principle | regression, convention, layout, figma, sibling | knowledge/figma-design-system.md |
| 113 | 디자인 파일이 시스템을 준수해도 코드 프로토타입은 완전히 별개 테마로 드리프트할 수 있다 (2026-07-15) | tactical | design-system, drift, figma, html, audit | knowledge/figma-design-system.md |
| 114 | 지식 축적 스킬은 주제가 아니라 "읽기 경로(read path)"로 분할해야 학습이 쌓일수록 강해진다 (2026-07-16) | principle | skill-design, context, scaling, read-path, knowledge-base | 인라인 |
| 115 | 구조 리팩터는 다른 파일의 지시문을 조용히 깨뜨린다 — 에이전트는 아무것도 등록하지 않고 "성공"을 보고한다 (2026-07-16) | principle | refactor, stale-docs, registry-sync, rehearsal, verifier | knowledge/claude-code-platform.md |
| 116 | Figma 커버리지는 파일의 목차나 get_metadata가 아니라 figma.root.children으로만 인증한다 (2026-07-16) | tactical | figma, coverage, enumeration, get_libraries, mcp | knowledge/figma-design-system.md |
| 117 | 우선순위 규칙에는 "무엇이 tie-breaker가 아닌지"를 명시해야 한다 — 정렬 순서와 인용 횟수는 그럴듯한 함정 (2026-07-16) | tactical | precedence, tie-breaker, instruction-design, rehearsal | knowledge/claude-code-platform.md |
| 118 | N개 서브에이전트의 합의는 진실이 아니다 — 각자 참인 국소 관찰이 거짓 전역 주장으로 굳는다 (2026-07-16) | principle | multi-agent, consensus, 일반화, 부정주장, verification | knowledge/multi-agent-orchestration.md |
| 119 | 리드가 주입한 잘못된 전제는 워커의 오류가 되어 돌아온다 — 브리핑은 지시가 아니라 검증 대상이다 (2026-07-16) | principle | multi-agent, briefing, 반박채널, fan-out, 계약 | knowledge/multi-agent-orchestration.md |
| 120 | Figma get_metadata는 depth 제한이 없다 — 얕은 열거는 use_figma로만 (2026-07-17) | principle | figma, get_metadata, token-cap, use_figma | knowledge/figma-design-system.md |
| 121 | CSS 블록 주석 속 리터럴 `*/`는 뒤따르는 규칙 전체를 조용히 삭제한다 (2026-07-17) | principle | css, comment, custom-property, silent-failure | knowledge/css-design.md |
| 122 | 병렬 에이전트 공유 tmp 고정 파일명 충돌 — job 스코프 mktemp 필수 (2026-07-17) | principle | multi-agent, tmp, mktemp, concurrency | knowledge/multi-agent-orchestration.md |
| 123 | 지식베이스 감사에서 row-presence는 콘텐츠 깊이를 은폐한다 (2026-07-17) | principle | knowledge-base, audit, coverage, content-depth | 인라인 |
| 124 | Korean 파일에서 Edit 툴 실패 — Python writelines 패턴 (2026-06-12, 구 인라인 #12) | principle | claude-code, edit-tool, korean, python-writelines | knowledge/claude-code-platform.md |
| 125 | Derived slice 재사용으로 다수 sparkline 데이터 생성 (2026-06-12, 구 인라인 #13) | principle | react, derived-slice, sparkline, dashboard | knowledge/react-frontend.md |
| 126 | HeroSparkline optional height prop — 컴포넌트 복제 없이 크기 변형 흡수 (2026-06-12, 구 인라인 #14) | tactical | react, optional-prop, variant | knowledge/react-frontend.md |
| 127 | git cat-file + branch --contains — 특정 커밋의 브랜치 추적 2-step 패턴 (2026-06-17, 구 인라인 #15) | tactical | git, cat-file, branch-contains, ff-only | knowledge/git-worktree.md |
| 128 | CSnCompany 공식 플러그인 헬스 게이트 — preflight(-3.5) 의존성 조기 차단 (2026-06-17, 구 인라인 #16) | tactical | preflight, official-plugins, dependency-gate, pre_pass | 인라인 |
| 129 | AI 서브에이전트의 성능/원인 진단은 가설이다 — 코드 반영 전 실측 재검증 (2026-07-17) | principle | agent-diagnosis, empirical-verification, time-measurement | knowledge/multi-agent-orchestration.md |
| 130 | 검증 중 실측된 신규 데이터가 유효한 결과물이면 테스트 데이터처럼 되돌리지 않는다 (2026-07-17) | tactical | verification, production-data, test-cleanup | knowledge/misc-tooling.md |
| 131 | 라이브 참조 없는 화면/유형은 발명하지 않고 스코프 제외 또는 reference-weak로 명시 플래그한다 (2026-07-17) | principle | figma, reference-gap, scope, anti-invention | knowledge/figma-design-system.md |
| 132 | Figma 빌드 완료 선언 전 라이브 사이트/템플릿 스크린샷 대조 게이트는 육안 검수로 못 잡는 버그를 반복적으로 잡아낸다 (2026-07-17) | tactical | figma, screenshot-gate, quality-gate, verification | knowledge/figma-design-system.md |
| 133 | dev 오케스트레이터 스크립트의 하드코딩 포트 + 무조건 kill이 "자기 자신의 워크트리 실행" 시나리오에서 메인 앱을 죽인다 (2026-07-17) | tactical | tauri, dev-server, port-env, self-referential | knowledge/tauri-windows.md |
| 134 | Workflow의 parallel adversarial review가 "cleanup 완전 비활성화"라는 스코프 오류를 잡아낸 사례 (2026-07-17) | principle | workflow-tool, adversarial-review, code-review, scope | knowledge/multi-agent-orchestration.md |
| 135 | 프로세스/포트 cwd 매칭에 느슨한 ancestor-path 비교를 쓰면 무관한 프로세스와 오탐 — 코드리뷰가 놓치고 Playwright 라이브 검증이 잡아낸 사례 (2026-07-17) | tactical | process-matching, false-positive, playwright, live-verification | knowledge/debugging.md |
| 136 | git worktree remove는 그 디렉터리를 cwd로 쓰는 실행 중 프로세스를 멈추지 않는다 — 삭제 전 명시적 stop 필요 (2026-07-17) | tactical | git-worktree, orphan-process, cwd, cleanup | knowledge/tauri-windows.md |
| 137 | 상태 정리/마이그레이션 수정은 실제 프로덕션 데이터에 합성 케이스를 주입해 전후 id-set diff로 검증하면 더 강한 확신을 준다 — 단, 격리 포트 + 왕복 클린업이 전제 (2026-07-17) | tactical | verification, production-data, isolated-testing, cleanup-protocol | knowledge/misc-tooling.md |
| 138 | EnterWorktree가 "Already in a worktree session"으로 막히면 디렉터리 존재를 의심하기 전에 ExitWorktree(remove)부터 시도한다 (2026-07-17) | principle | claude-code, enterworktree, exitworktree, session-recovery | knowledge/claude-code-platform.md |
| 139 | Workflow 스크립트의 agent 프롬프트 안에 리터럴 ${...}를 쓰면 sandbox가 즉시 평가해 "process is not defined"로 전체 런을 크래시시킨다 (2026-07-17) | principle | workflow-tool, template-literal, sandbox, scripting-pitfall | knowledge/claude-code-platform.md |
| 140 | 표시 이름과 권한 플래그가 분리된 인증 구조에서는 이름 충돌이 사일런트 권한 오판을 만든다 (2026-07-17) | principle | auth, display-name, permission, reserved-name, react | knowledge/react-frontend.md |
| 141 | 서브에이전트가 idle_notification만 반복하고 도구 호출이 전혀 없으면 데드락 신호로 보고 직접 실행으로 전환한다 (2026-07-17) | tactical | multi-agent, idle-loop, deadlock, delegation, escalation | knowledge/multi-agent-orchestration.md |
| 142 | Claude Code plugin.json은 skills/agents/commands를 문자열 배열로 선언하면 안 된다 — auto-discovery 방식이라 선언 시 Invalid input 에러 (2026-07-17) | principle | claude-code, plugin.json, auto-discovery, invalid-input | 인라인 |
| 143 | Figma 노드의 `.x`/`.y`는 절대좌표가 아니라 부모 프레임 기준 상대좌표다 (2026-07-18) | principle | figma, coordinates, parent-relative, plugin-api | knowledge/figma-design-system.md |
| 144 | Claude Code 플러그인 캐시는 plugin.json version bump + `claude plugin marketplace update`/`claude plugin update` 명시적 실행이 모두 있어야 갱신된다 (2026-07-19) | principle | claude-code, plugin-cache, version-bump, marketplace-update | knowledge/claude-code-platform.md |
| 145 | 글로벌 설정/플러그인 수정의 타 프로젝트 반영 검증은 새 `claude -p` 헤드리스 프로세스로 한다 (2026-07-19) | principle | claude-code, verification, headless, claude-p, restart-simulation | knowledge/claude-code-platform.md |
| 146 | 이름 기반 UI 요소 검색은 정확 일치를 전체 스크롤에서 먼저 시도하고, 없을 때만 부분 일치로 폴백해야 한다 (2026-07-19) | principle | ui-automation, substring-match, exact-match, search-order, ocr | knowledge/mobile-automation.md |
| 147 | dumpsys 등 상태 덤프에서 상태를 판정할 때는 관련 라인만 파싱해야 한다 — 전체 텍스트에 마커 문자열이 있는지로 판단하면 안 된다 (2026-07-19) | principle | android, dumpsys, state-parsing, stale-state, mobile-automation | knowledge/mobile-automation.md |
| 148 | WebFetch가 클라이언트 렌더링(Next.js RSC) 페이지에서 실제 콘텐츠를 누락시킨다 — curl+grep/python 파싱으로 폴백 (2026-07-19) | principle | webfetch, nextjs, rsc, client-render, fallback, curl | knowledge/misc-tooling.md |
| 149 | GUI 전용 설치 단계를 자동화 불가로 단정하기 전에, 설치 대상 산출물이 이미 디스크에 존재하는지 먼저 확인한다 (2026-07-19) | principle | installation, gui-workaround, disk-artifact, automation | knowledge/misc-tooling.md |
| 150 | Figma Plugin API에서 `clone()` 후 `appendChild()`는 항상 최상위 z-order로 붙는다 (2026-07-21) | principle | figma, clone, appendChild, z-order, insertChild | knowledge/figma-design-system.md |
| 151 | Figma Plugin API에는 자동 리플로우가 없다 — 행 삽입 시 하위 요소 좌표를 전부 수동 시프트해야 한다 (2026-07-21) | principle | figma, absolute-position, manual-reflow, resize | knowledge/figma-design-system.md |
| 152 | GROUP 노드는 FRAME과 달리 고정 선택 경계가 없어 콘텐츠 변경 시 플로팅 선택-핸들 아티팩트를 유발한다 (2026-07-21) | principle | figma, group-vs-frame, selection-bounds, bounding-box | knowledge/figma-design-system.md |
| 153 | clipsContent=true인 프레임은 스크린샷이 정상으로 보여도 자식이 부모보다 크면 바운딩박스 오버플로우를 숨긴다 (2026-07-21) | principle | figma, clipsContent, overflow, backdrop, hidden-bug | knowledge/figma-design-system.md |
| 154 | 구조 변경(컨테이너 타입 전환 등) 직후 좌표가 우연히 일치하면 실제로는 상대좌표가 아닌 버그가 가려질 수 있다 — 이동시켜 스트레스 테스트해야 드러난다 (2026-07-21) | principle | debugging, coincidental-match, coordinate-bug, stress-test | knowledge/debugging.md |
| 155 | 여러 항목에 동일 패턴의 오차가 의심되면 먼저 read-only로 전수 진단해 상수-델타 여부를 확인한 뒤 단일 배치 연산으로 고친다 (2026-07-21) | principle | debugging, diagnose-fix-verify, multi-agent, batch-shift | knowledge/multi-agent-orchestration.md |
| 156 | 그럴듯한 원인을 고쳤다고 끝내지 말고, 사용자가 최초에 보고한 정확한 증상과 대조해 진짜 원인을 특정했는지 재확인한다 (2026-07-21) | principle | debugging, root-cause, symptom-match, verification | knowledge/debugging.md |
| 157 | Claude Artifact 안에서 외부 라이브러리 없이 PDF 다운로드 구현 — print-media CSS + window.print() (2026-07-21) | tactical | claude-artifact, pdf, print-css, window.print | knowledge/misc-tooling.md |
| 158 | yt-dlp --cookies-from-browser는 프로필 미지정 시 여러 Chrome 프로필 중 무작위로 선택한다 — Local State JSON으로 폴더명↔표시이름 매핑 필요 (2026-07-22) | tactical | yt-dlp, cookies, chrome-profile, local-state | knowledge/download-pipeline.md |
| 159 | yt-dlp 쿠키 인증 시 로그인 가능한 클라이언트(tv/web)로 전환되며 JS 런타임 + --remote-components ejs:github 둘 다 필요 (2026-07-22) | tactical | yt-dlp, cookies, youtube, deno, ejs | knowledge/download-pipeline.md |
| 160 | Radix ScrollArea의 display:table 내부 래퍼는 자식의 truncate를 무력화한다 — w-px min-w-full로 강제 필요 (2026-07-22) | tactical | radix, scrollarea, truncate, display-table, css | knowledge/download-pipeline.md |
| 161 | 파일명에 '#' 포함 시 인코딩 없이 URL에 넣으면 브라우저가 프래그먼트로 해석해 요청 경로가 잘려 404 (2026-07-22) | tactical | url, filename, encodeURIComponent, fragment, 404 | knowledge/download-pipeline.md |
| 162 | for 루프 순차 처리에서 아이템별 try/catch 없으면 하나만 실패해도 나머지 전체가 스킵된다 (2026-07-22) | tactical | batch, for-loop, try-catch, partial-failure | knowledge/download-pipeline.md |
| 163 | Electron fetch+blob 다운로드에서 revokeObjectURL을 너무 빨리 호출하면 큰 파일에서 실패 — 서버가 이미 로컬 저장한 파일은 blob 재다운로드 자체가 불필요 (2026-07-22) | tactical | electron, blob, revokeObjectURL, filesystem, download | knowledge/download-pipeline.md |
| 164 | `.git`을 재귀 삭제·재초기화하는 엔드포인트는 절대 경로와 호출별 확인만으로 부족하다 — canonical root와 no-follow entry 분류가 필요 (2026-07-26) | principle | git, destructive-action, worktree, symlink, lstat | knowledge/git-worktree.md |
| 165 | 배치 TTS 자막 경계는 글자수 추정이 아니라 문장별 합성 오디오의 실측 길이를 누적해 생성한다 (2026-07-26) | tactical | tts, ffprobe, subtitles, srt, vtt | knowledge/download-pipeline.md |
| 166 | 외부 CLI 자동화는 기억한 플래그가 아니라 실제 설치된 command의 help와 비대화형 실행으로 검증한다 (2026-07-26) | tactical | cli, automation, flag-drift, non-interactive, verification | knowledge/misc-tooling.md |
| 167 | Loopback bind는 authorization이 아니다 — 민감한 로컬 API는 Origin 검증 + 설치별 capability + canonical root allowlist가 모두 필요하다 (2026-07-26) | principle | localhost, loopback, authorization, origin, allowlist, local-api | knowledge/deployment.md |
| 168 | 복제 문서의 충돌 안전성은 local expected-hash CAS와 remote expected-parent CAS를 모두 요구하며 첫 동기화는 명시적 adoption이어야 한다 (2026-07-26) | principle | sync, cas, conflict, adoption, replication | knowledge/data-sync-db.md |
| 169 | 파생·복원 콘텐츠는 출처 상태를 타입 필드로 보존하고 최종 UI까지 노출해 원문 오인을 막는다 (2026-07-26) | principle | provenance, derived-content, type-field, ui-disclosure | knowledge/react-frontend.md |
| 170 | Next.js 16.2.11 Turbopack은 macOS NFD 한글 경로에서 UTF-8 경계 패닉 — 경로/upstream 수정 전까지 webpack parity 유지 (2026-07-26) | tactical | nextjs, turbopack, macos, nfd, unicode, panic | knowledge/debugging.md |
| 171 | AgentsToZ project-memory 마커 블록은 기계 관리 영역 — 계약을 의도적으로 바꿀 때만 마커 안을 편집한다 (2026-08-18) | tactical | agentstoz, project-memory, marker, generated-block, claude-md | knowledge/claude-code-platform.md |
| 172 | 텔레메트리성 UserPromptSubmit 훅은 메타데이터만 기록하고 프롬프트 본문은 절대 담지 않는다 (2026-08-18) | principle | hooks, userpromptsubmit, telemetry, token-free, privacy | knowledge/claude-code-platform.md |
| 173 | 체크인된 정책 SQL은 의도이고 배포 상태가 아니다 — 접근제어 시행은 라이브 프로브로만 확정된다 (2026-08-22) | principle | rls, access-control, live-probe, deployed-state, postgrest, supabase | knowledge/deployment.md |
| 174 | 외부 origin anchor의 target="_blank"는 rel="noopener noreferrer"와 한 쌍이다 (2026-08-22) | tactical | anchor, target-blank, noopener, tabnabbing, outbound-link | knowledge/react-frontend.md |
| 175 | 콘텐츠 주소형 revision 복원은 검증한 바로 그 바이트를 써야 한다 (2026-07-26) | principle | content-addressed, restore, hash-verify, lineage, toctou | knowledge/data-sync-db.md |
| 176 | 비대해진 API route table은 기능군 모듈로 분리하고 동기화 충돌은 409로 표면화한다 (2026-07-26) | tactical | api-route, module-split, thin-router, 409, conflict | knowledge/data-sync-db.md |
| 177 | 화면 표시용 표현과 음성 낭독용 원고는 같은 의미의 별도 필드로 모델링한다 (2026-07-26) | principle | tts, accessibility, content-modeling, dual-representation | knowledge/misc-tooling.md |
| 178 | 없는 커버리지는 없다고 보고한다 — 미룬 작업은 구조화된 revisit 트리거와 함께 남긴다 (2026-08-22) | principle | coverage-honesty, deferred-work, revisit-trigger, reporting, absent-coverage | knowledge/multi-agent-orchestration.md |

> 참고: #7-9, #12-71은 프로젝트-특화 학습으로 `knowledge/` 파일에 이관됨 (2026-06 재구조화).
> 과거 어긋났던 #8의 배치 순서도 이관 시 번호순으로 정렬 수정됨. 번호는 전역 유일하며 재사용하지 않는다.
> 2026-07-17 무결성 복구: INDEX 누락분 #95-99·#120-123 백필, 인라인 #12-16(2026-06 작성분)은 knowledge/ 이관 항목과의 번호 충돌로 #124-128 재부여, 프로젝트-특화 인라인 본문을 knowledge/로 오프로드. 이후 정합성은 `bash plugins/shared/run_prepass.sh index-check`가 커밋 게이트에서 기계 검증한다 (C1 INDEX 누락 / C2 위치 포인터 / C3·C4 번호 유일성 / C5 연속성 / C6 인라인 상한 15).

### 오케스트레이터 도메인 학습 (인라인: #1-6, #10-11, #114, #123, #128, #142)

### 1. version-up은 학습 캡처 + 디렉토리 복사 두 단계여야 한다 (2026-04-11)
<!-- tier: principle -->

- **상황**: 초기 version-up이 디렉토리 복사 + VERSION 번호 증가만 수행
- **발견**: 단순 cp는 파일 내용이 동일하므로 "경험 저장소"가 아니라 "버전 스냅샷"에 불과함. 새 VERSION 디렉토리에 이번 세션에서 배운 내용이 없으면 버전 증가의 의미가 없다.
- **교훈**: version-up 실행 시 반드시 AskUserQuestion으로 학습 내용을 받아 SKILL.md 노하우 섹션에 추가한 뒤 cp 실행. 학습 없이 버전만 올리는 것은 의미 없음.

### 2. `all` 키워드로 3개 도메인 한번에 버전업 (2026-04-11)
<!-- tier: principle -->

- **상황**: 도메인별로 version-up을 3번 따로 실행해야 했음
- **발견**: `test` → `plan` → `review` 순서로 순차 처리하면 한 번의 명령으로 모두 처리 가능
- **교훈**: `/cs-experiencing version-up all` 지원으로 워크플로우 간소화. 각 도메인마다 학습 캡처 인터랙션이 뜨므로 3번의 입력 기회가 생김.

### 3. AI 자동 학습 추출 — 수동 입력보다 먼저 시도 (2026-04-14)
<!-- tier: principle -->

- **상황**: version-up 시 항상 수동으로 학습 내용을 입력해야 했음. 세션이 길면 무엇을 배웠는지 직접 요약하기 번거로움.
- **발견**: AI가 세션 컨텍스트를 먼저 분석하면 핵심 발견사항(버그 원인, 해결 패턴, 예상 외 동작 등)을 자동 추출 가능. 사용자는 제안을 확인만 하면 됨.
- **교훈**: STEP 1을 "AI 분석 → 제안 → 확인" 순서로 바꾸면 마찰 최소화. 발견사항이 없을 때만 기존 수동 입력 fallback.

### 4. 외부 소스 학습 통합 — bkit·Karpathy·gstack 패턴 (2026-04-20)
<!-- tier: principle -->

- **상황**: bkit-claude-code, Karpathy-skills, gstack 3개 외부 레포 분석 후 cs-experiencing 및 4개 도메인에 적용 가능한 패턴을 발견함
- **발견**: bkit → Evaluator-Optimizer 루프(등급 미달 자동 재실행), Checkpoint 패턴(단계 간 사용자 확인 게이트). Karpathy → Think-Before-Coding(모호성 선제 해소), Goal-Driven Execution(성공 기준 명시). gstack → 선형 파이프라인(review→design→test), CSS/JSX 리스크 버짓 분리, 크로스 모델 듀얼 리뷰.
- **교훈**: 외부 패턴 학습은 각 도메인 SKILL.md 노하우에 직접 추가. 오케스트레이터(experiencing)에는 파이프라인 커맨드 + experiencing-lead/preflight-checker 신규 에이전트로 반영. 학습 후 즉시 version-up 실행.
- 2026-07-05 addendum: CS-plugin 자기개선 외에, **클라이언트 프로젝트 코드 개선**을 위해 사용자가 건넨 외부 교육자료(대학원 실습 .ipynb 등)를 분석하는 경우도 같은 메커니즘이 적용됨. 이때 CEO는 자료 속 구성요소(예: function calling, RAG, 세션 메모리)를 프로젝트의 실제 코드 아키텍처에 1:1로 매핑해 "어떤 기능을 말하는지"부터 명확히 하고(먹고공부하자 세션: "채팅 기능"을 팀채팅이 아닌 AI 봇으로 정확히 재해석), Mode A 직접 분석 + 우선순위별 개선안 제시로 이어감. 외부지식게이트(Phase -3) 호출 없이도 자료가 이미 제공된 경우 바로 분석 가능.

### 5. bkit btw 패턴 — 세션 중 아이디어 즉시 캡처 (2026-04-20)
<!-- tier: principle -->

- **상황**: version-up 시 "이번 세션에서 뭘 개선해야 할지" 기억이 흐릿함. 작업 중 발견한 개선점이 세션 끝에 사라짐.
- **발견**: bkit의 btw(By-The-Way) 패턴: 작업 중 즉시 캡처 → JSON 파일에 pending 상태로 저장 → version-up 시 pending 항목을 먼저 보여주고 반영 여부 결정.
- **교훈**: `/cs-experiencing btw [idea]` 명령 추가. 세션 중 발견사항을 즉시 캡처하면 version-up의 AI 분석 단계를 보완할 수 있음.

### 6. gstack Iron Law — version-up 루프 실패 상한 (2026-04-20)
<!-- tier: principle -->

- **상황**: version-up all 실행 중 특정 도메인에서 오류가 생기면 전체가 중단되거나 무한 재시도 가능성 있음.
- **발견**: gstack Iron Law: "동일 문제에 3회 실패 시 강제 중단 + STUCK 리포트." version-up에도 동일 원칙 적용 — 도메인 처리 실패 2회 시 해당 도메인 스킵 + 경고 출력 후 다음 도메인으로.
- **교훈**: `version-up all` 프로토콜에 도메인별 retry 상한(2회) 추가. 실패 도메인은 스킵하고 `⚠️ [DOMAIN] 스킵됨 — 수동 확인 필요` 출력 후 계속 진행.
- ✅ 반영됨 (2026-06) — experiencing-lead.md Phase 2 bounded re-run loop(도메인당 상한 2라운드 + STUCK 리포트)로 코드화

### 10. `/compact`는 스킬에서 직접 호출 불가 — 생성된 요약을 제안하는 패턴으로 우회 (2026-05-01)
<!-- tier: principle -->

- **상황**: cs-end가 세션 종결 자동화를 담당하지만 `/compact`(context 압축)는 별도로 실행해야 했음. 사용자가 "원커맨드 종결"을 원했으나 cs-end가 compact를 수행하지 않았음.
- **발견**: `/compact`는 Claude Code 내장 명령으로, 스킬/커맨드에서 프로그래밍적으로 호출이 불가능함. allowed-tools에도 invoke-command 같은 도구가 없음.
- **교훈**: 자동 호출이 불가능한 명령이 필요한 경우, 해당 명령의 인자를 AI가 생성하여 사용자가 복사-실행할 수 있도록 제안하는 패턴이 최선. cs-end Phase 6: Phase 1 분석 결과로 세션 요약 1-2줄 생성 → `/compact [요약]` 형식으로 출력 → 사용자가 그대로 실행. `--no-compact` 플래그로 생략 가능.

### 11. Claude Code 훅 exit code — non-zero는 UI를 블로킹한다 (2026-05-02)
<!-- tier: principle -->

- **상황**: CS볼트V5(Obsidian vault) 등 `.env`가 없는 폴더에서 작업할 때마다 Claude Code 입력창이 회색으로 굳어버림
- **발견**: `notification-hook.sh`, `stop-hook.sh` 모두 `.env` 없을 시 `exit 1` 반환 → Claude Code는 훅 비정상 종료를 UI 블로킹으로 처리. 훅이 "해당 없음"인 경우에도 `exit 1`이면 입력창이 그레이아웃됨
- **교훈**: 훅의 전제조건(`.env`, 토큰 등)이 충족되지 않을 때는 반드시 `exit 0`으로 종료. `exit 1`은 의도적으로 사용자를 멈춰야 할 진짜 오류에만 사용. "이 훅은 여기에 해당 없음" = `exit 0`

### 114. 지식 축적 스킬은 주제가 아니라 "읽기 경로(read path)"로 분할해야 학습이 쌓일수록 강해진다 (2026-07-16)
<!-- tier: principle -->

- **상황**: `csdesign/nds`(Figma 디자인시스템 가이드 학습 저장소)에 3개 파일(총 77페이지)을 학습시킨 뒤, BUILD 패스가 "가장 먼저 읽어라"고 지시받은 `LEADER.md` 자체를 물리적으로 읽지 못하는 상태에 도달했다.
- **발견**: `LEADER.md`가 ~36–45k 토큰까지 커져 단일 Read가 컨텍스트 캡을 초과했다 — 학습 파일이 하나 늘 때마다 단조 악화되는 구조였다(= 학습할수록 못 쓰게 되는 anti-scaling). 이를 `LEADER.md`(모드 전용) + 상시 로드 베이스(`CORE.md`/`COMMON.md`) + `INDEX.md`(노트당 1줄) + `LEDGER.md`(쟁점, 해결되며 축소) + `sources/*.md`(빌드 시 비로드)로 **읽는 목적별로** 재분할하자, N번째 학습 파일이 새 행을 추가하기보다 기존 행을 corroborate만 하게 되어 읽기 비용은 유계로 유지되면서 신뢰도만 올라갔다.
- **교훈**: 지식이 계속 쌓이는 스킬을 설계할 때 "이 항목을 **어떤 목적으로** 읽는가(빌드 vs 감사 vs 포렌식)"로 파일을 나눈다. 주제별 분류는 항목 수에 비례해 읽기 비용이 선형 증가하지만, 읽기 경로별 분류는 유계로 만든다. 단, 균일성을 위해 전 도메인에 일괄 적용하지 말고(작은 도메인 2개는 의도적으로 미분할 유지) **측정된 트리거**(~25k 토큰, 또는 레지스트리가 더 이상 스캔되지 않는 시점)를 문서에 남겨 조건 충족 시에만 적용한다.
- **근거**: 실측 — nds BUILD 읽기 비용 36,201 → 12,098 토큰, asset 20,742 → 1,859. (skeptic verifier CONFIRM — "아키텍처 수준 주장이며 캐시 지역성/점진적 공개와 같은 논리, 특정 수치나 캡이 바뀌어도 원칙은 생존". 함께 제출된 "토큰 캡 초과" 후보는 이 항목의 근거일 뿐 독립 원칙이 아니라는 이유로 REJECT되어 여기 병합됨.)
- **추가 (2026-07-26)**: 읽기 경로는 파일을 나누는 데서 끝나지 않는다. 런타임/에이전트 입력으로 선언한 저장소는 실제 소비 쿼리와, 부하를 지탱하는 각 검색 방식에 대한 현실적인 golden-query 회귀 검증을 함께 가져야 한다. `231e4bf` 직전 nhdesign4 proposal 경로에는 topic/component SELECT가 없었고 ledger는 홈페이지 anchor 1곳만 소비했다. 이후 preamble이 topic/component/conflict 소비자를 추가하고 golden set이 page/component anchor 12개와 memory recall을 검증했다. 다만 topic-array lookup과 ledger sweep golden은 아직 부채이므로 모든 구조화 저장소가 완전히 검증됐다고 과장하지 않는다. 런타임 입력으로 선언되지 않은 순수 archive는 이 요구에서 제외한다.
<!-- provenance: candidate=btw-provenance-1e54b2646acd3c7e9d831164; run=9eed3fbd-5a8b-4a10-91ff-32dd357c4cdc; memory=1eb621cd-79c2-46fa-bf38-dd6c2a9a9657; range=git:231e4bfd61d91ceb623edfbe62055fa7b55106e9..51e68d3b5a5639b6cb90d0ecfc7cab94d0315b19;truncated=true -->

### 123. 지식베이스 감사에서 row-presence는 콘텐츠 깊이를 은폐한다 — row-count 커버리지만으로는 거짓 확신이 생긴다 (2026-07-17)
<!-- tier: principle -->

- **상황**: 지식베이스(DB)가 "충분히 채워졌는가"를 감사하며, 열거된 항목의 100%가 DB 행을 갖고 있다는 사실만으로 완성도를 1차 판단.
- **발견**: row가 존재한다고 표시된 페이지 중 하나를 열어보니, 그 페이지 자신의 gap-notes 필드에 **약 15~25%만 필사(transcribe)됐다고 명시적으로 기록**돼 있었다 — row-presence는 100%였지만 실제 콘텐츠 깊이는 매우 낮았다. 이는 추론이 아니라 해당 행 자신이 남긴 1차 기록이다.
- **교훈**: 지식베이스/DB 완성도를 감사할 때는 row-count 커버리지(있음/없음)뿐 아니라 **콘텐츠 깊이**(글자수, 필드 채움률, 혹은 각 행 자신의 gap-notes)를 별도 지표로 반드시 함께 확인한다. row-count만 보고 "N/N 완료"라 선언하는 것은 #116("커버리지 주장은 권위 있는 분모로만 인증")의 사촌 함정이다 — 분모는 맞아도 분자 안의 밀도가 거짓 확신을 만든다.
- **근거**: 특정 페이지 행의 `content_md` 자체 서술 — "a page marked as having a row was actually only ~15-25% transcribed". (skeptic verifier CONFIRMED — 1차 문서화된 사실이며 추정이 아님, 주장이 요구하는 정확한 현상을 직접 예시함.)

### 128. CSnCompany 공식 플러그인 헬스 게이트 — preflight(-3.5)에서 의존성 조기 차단 (2026-06-17)
<!-- tier: tactical -->
<!-- renumbered 2026-07-17: 구 인라인 #16 — knowledge/ 이관 항목 #16과 번호 충돌로 재부여 -->

- **상황**: cs-ceo, CS-test, CS-codebase-review가 serena/playwright/hookify 등 공식 플러그인에 의존하지만 런타임 진입 후에야 누락을 감지해 비용이 낭비되었음.
- **발견**: pre_pass.py에 `_find_official_plugin()` + `_find_mcp_server()` 헬퍼를 추가하고 ceo.md Phase -3.5에서 preflight 단계에 감지·차단. CS-test는 playwright 미설치 시 Install/Skip/Abort AskUserQuestion 제공. OFFICIAL-PLUGINS.md가 설치 명령어 단일 진실.
- **교훈**: 공식 플러그인 의존성은 멀티에이전트 워크플로우 진입 전 preflight 단계(-3.5)에서 차단하는 것이 비용 효율적. context7 패턴(누락 감지 → AskUserQuestion 설치 유도)을 공식 플러그인에 동일 적용.
- **근거**: `defd9c1 feat: serena 통합 + 공식 플러그인 자동설치 유도 시스템 추가` — ceo.md +56줄, pre_pass.py +64줄, OFFICIAL-PLUGINS.md 신규 (2026-06-17)

### 142. Claude Code plugin.json은 skills/agents/commands를 문자열 배열로 선언하면 안 된다 — auto-discovery 방식이라 선언 시 Invalid input 에러 (2026-07-17)
<!-- tier: principle -->
<!-- error-ref: ERR-2026-07-17-007 -->

- **상황**: `cs-core-memory` 플러그인 설치 시 마켓플레이스 installer가 "agents: Invalid input, skills: Invalid input" 검증 에러로 설치를 거부. `.claude-plugin/plugin.json`을 읽어보니 `skills`/`agents`/`commands` 필드가 문자열 배열로 선언되어 있었음. 작동 중인 다른 플러그인(cs-end-v3, cs-clarify-v1)의 plugin.json에는 이 필드들이 아예 없었고, 대신 author/repository/license/keywords만 있었음. `find`로 확인한 결과 `agents/memory-keeper.md`와 `skills/cs-core-memory/SKILL.md` 파일은 실제로 디스크에 존재했다.
- **발견**: Claude Code 플러그인 로더는 skills/agents/commands를 plugin.json에 문자열 배열로 선언하는 방식이 아니라, 플러그인 폴더 내 실제 디렉토리 구조(`agents/*.md`, `skills/*/SKILL.md`, `commands/*.md`)를 스캔해 자동 발견(auto-discovery)한다. plugin.json에 이 키들을 배열로 넣으면 installer의 스키마 검증에 걸려 "Invalid input" 에러가 난다. 추가로 cs-core-memory-v1은 `.claude-plugin/plugin.json` 외에 플러그인 루트에도 중복 `plugin.json`이 있었고(다른 모든 플러그인 중 유일), 이것도 같은 무효 필드를 갖고 있어 별도 커밋으로 삭제함 — 표준 위치(`.claude-plugin/plugin.json`) 하나만 유지.
- **교훈**: 새 Claude Code 플러그인(특히 마켓플레이스 배포용) plugin.json을 작성/디버깅할 때, skills/agents/commands 키를 수동으로 선언하지 말 것 — 디렉토리 구조만으로 충분하다. "Invalid input" 검증 에러가 나면 같은 레포의 이미 설치 가능한 plugin.json들과 필드 셋을 diff하여 스키마 불일치를 확인한다.
- **근거**: `cs-core-memory-v1/.claude-plugin/plugin.json`: `"skills": ["cs-core-memory"], "agents": ["memory-keeper"], "commands": []` → 설치 에러 "Plugin ... has an invalid manifest file ... Validation errors: agents: Invalid input, skills: Invalid input". `cs-end-v3/.claude-plugin/plugin.json`에는 해당 필드들이 전혀 없이 author/repository/license/keywords만 존재 (정상 설치됨). 수정: 커밋 d4dfac7 (필드 제거) + 6741a11 (중복 루트 plugin.json 삭제), PR #4.
