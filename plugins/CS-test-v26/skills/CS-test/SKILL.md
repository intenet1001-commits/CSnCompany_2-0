---
name: CS-test
user-invocable: true
description: |
  15-agent AI Teams web testing skill. Use when user types "/CS-test", "웹 테스트", "playwright test",
  "테스트 실행", "사이트 테스트", or wants comprehensive web app testing covering security, SEO,
  performance, DB, touch interaction, and image optimization with AI agent teams.
version: 26.0.0
---

# Playwright Test v5 - AI Agent Teams 기반 종합 웹 테스트

## 개요

15개의 전문 Claude AI 에이전트로 구성된 팀이 대상 웹 앱을 심층 테스트합니다.
v5에서는 **터치 인터랙션 검증** + **이미지 최적화 분석**이 추가됩니다.
(MWC 2026 세션에서 발견된 실제 버그 패턴 기반)

검증 프로토콜: plugins/shared/LOOP-PROTOCOL.md + plugins/shared/agents/verifier.md를 따른다. (verdict 산출 플러그인 — plugins/shared/GATE-LOOP.md 추가 적용)

## 사용법

```
/playwright-test [URL]
```

## 에이전트 팀 구성

| 에이전트 | 역할 | Phase | v5 변경 |
|----------|------|-------|---------|
| **build-validator** | 빌드/보안/의존성 사전 검증 | 0 | v4 유지 |
| **test-lead** | 팀 리더 - 오케스트레이션 및 리포트 생성 | 전체 | 15개 에이전트 관리 |
| **page-explorer** | 페이지 탐색 및 구조 분석 | 1 | v4 유지 |
| **functional-tester** | 기능/인터랙션 + DB 반영 테스트 | 2 | v4 유지 |
| **visual-inspector** | UI/접근성/반응형 검사 | 2 | v4 유지 |
| **api-interceptor** | API/네트워크 분석 + og:image 검증 | 2 | v4 유지 |
| **perf-auditor** | 성능 측정 및 감사 | 2 | v4 유지 |
| **social-share-auditor** | OG·og:image·KakaoTalk·PWA 검증 | 2 | v4 유지 |
| **db-validator** | DB CRUD 실제 동작 검증 | 2 | v4 유지 |
| **touch-interaction-validator** | 터치/스와이프 인터랙션 검증 | 2 | **v5 신규** |
| **image-optimizer** | 이미지 용량·WebP·Next.js Image 검증 | 2 | **v5 신규** |
| **security-auditor** | HTTP 보안 헤더·쿠키 플래그·민감정보 노출 감사 | 2 | **v5 신규** |
| **seo-auditor** | 메타태그·canonical·sitemap·구조화 데이터 분석 | 2 | **v5 신규** |
| **error-resilience** | 404 페이지·콘솔에러·깨진링크·에러바운더리 검사 | 2 | **v5 신규** |
| **finding-verifier** | critical/high finding 적대적 재검증 (confirmed/refuted/unreproducible) | 2.5 | **신규** |

## 실행 프로토콜

이 스킬이 실행되면, 당신(실행 에이전트)이 **test-lead 역할**을 수행합니다.

### 환경 감지 — cmux vs Playwright 자동 선택

실행 시작 시 브라우저 자동화 환경을 감지한다:

```bash
if [ -n "$CMUX_SOCKET_PATH" ]; then
  BROWSER_MODE="cmux"
  cmux set-status "cs-test" "running" --icon "gear"
  cmux set-progress 0.0 --label "CS-test 시작..."
else
  BROWSER_MODE="playwright"
fi
```

| 환경 | 감지 조건 | 브라우저 도구 | Playwright 필요 |
|------|----------|-------------|----------------|
| **cmux** | `$CMUX_SOCKET_PATH` 존재 | `cmux browser` 명령어 | ❌ 불필요 |
| **Playwright** | MCP 툴 발견됨 | `mcp__playwright__browser_*` | ✅ 필요 |
| **없음** | 둘 다 없음 | Phase 0만 실행 | — |

**cmux 브라우저 명령어 대응표** (Playwright → cmux):

| Playwright MCP | cmux 명령어 |
|---------------|------------|
| `browser_navigate(url)` | `cmux browser open [URL]` |
| `browser_snapshot()` | `cmux browser snapshot -i` |
| `browser_screenshot()` | `cmux browser screenshot --out file.png` |
| `browser_click(selector)` | `cmux browser click "selector"` |
| `browser_fill(selector, value)` | `cmux browser fill "selector" "value"` |
| `browser_wait_for(text)` | `cmux browser wait --text "string" --timeout-ms 5000` |
| `browser_network_requests()` | `cmux browser snapshot -i` (DOM + network 포함) |

### 사전 준비

1. URL 인자 확인. 없으면 사용자에게 요청.
2. **서빙 대상 검증 (localhost/127.0.0.1 URL인 경우만)**: 해당 포트가 실제 dev 서버를 서빙 중인지, 구버전 production build인지 확인 — 방법 자유 (예: lsof, ps). 불일치 의심 시(예: 포트는 살아있는데 dev 프로세스가 다른 포트) 사용자에게 1회 확인. (노하우 #23)
3. **성공 기준 1문장 출력 (필수)**: 사용자가 기준·중점 라우트·인증 정보를 제공했으면 그대로 사용, 없으면 기본값을 추론해 출력하고 진행 — 예: "성공 기준: P0 에러 0건, 성능 점수 70+, SEO 등급 B 이상". 원격 URL이면 추가 질문 없이 기본 기준으로 시작한다(불필요한 인터랙션 방지). (노하우 #21)
4. 결과 디렉토리 생성:

```bash
mkdir -p tests/results tests/screenshots
```

> 📐 **성공 기준 전파 (필수)**: Phase 1·2의 **모든** Task() 프롬프트 템플릿에 한 줄 추가 —
> "성공 기준: [기준 문장] — 리포트 JSON에 `\"passFail\": \"pass|fail\"` 필드로 이 기준 대비 판정을 포함하세요."
> Phase 3에서 test-lead가 REPORT.md 상단에 선언된 성공 기준과 종합 pass/fail을 명시한다.

### 브라우저 사전 검증 (Phase 1-2용)

**cmux 환경** (`$BROWSER_MODE == "cmux"`):
- `cmux browser open [URL]` 실행 가능 확인
- Playwright MCP 탐색 불필요 — Phase 1-2 전체 실행 가능

**일반 환경** (`$BROWSER_MODE == "playwright"`):
```
ToolSearch(query: "+playwright navigate")
```
- `mcp__playwright__browser_navigate` 발견 → 정상
- 없음 → Phase 0 (build-validator)는 실행 가능, Phase 1-2는 경고 후 건너뜀

### Phase 0: 빌드/배포 사전 검증 (Playwright 불필요)

```bash
# cmux 환경: 진행 상황 업데이트
[ -n "$CMUX_SOCKET_PATH" ] && cmux set-progress 0.1 --label "Phase 0: 빌드 검증"
```

```
TeamCreate(team_name: "playwright-test-v5", description: "AI 웹 테스트 팀 v5")

TaskCreate(
  subject: "빌드/보안/의존성 사전 검증",
  description: "npm audit, tsconfig, Tailwind 호환성, 미커밋 파일, TypeScript 컴파일 체크",
  activeForm: "빌드 사전 검증 중"
)

Task(
  subagent_type: "general-purpose",
  name: "build-validator",
  team_name: "playwright-test-v5",
  prompt: """당신은 playwright-test-v5의 build-validator입니다.
현재 디렉토리의 Next.js/React 프로젝트를 분석하여 배포 전 문제를 탐지하세요.
agents/build-validator.md의 프로토콜을 따르세요.
결과를 tests/results/build-report.json에 저장하세요.
완료 후 test-lead에게 결과 요약을 SendMessage로 전송하세요."""
)
```

build-validator 완료 후:
- build-report.json 읽기
- grade가 F면: "⚠️ 빌드 검증 F등급: [이슈]" 를 사용자에게 표시
- 계속 진행 (배포 문제가 있어도 테스트는 유용)

### Phase 1: 팀 생성 및 탐색

```bash
[ -n "$CMUX_SOCKET_PATH" ] && cmux set-progress 0.3 --label "Phase 1: 페이지 탐색"
```

```
TaskCreate(
  subject: "웹 앱 구조 탐색 및 page-map 생성",
  description: "대상 URL을 방문하여 페이지 구조, OG 메타태그, PWA 정보 분석",
  activeForm: "웹 앱 구조 탐색 중"
)

Task(
  subagent_type: "general-purpose",
  name: "page-explorer",
  team_name: "playwright-test-v5",
  prompt: """당신은 playwright-test-v5의 page-explorer입니다.
[URL]을 탐색하고 tests/results/page-map.json을 생성하세요.
OG 메타태그(og:image 포함)와 PWA 정보도 수집하세요.
agents/page-explorer.md의 프로토콜을 따르세요."""
)
```

page-explorer 완료 대기 (SendMessage 수신)

### Phase 2: 병렬 테스트 (11개 에이전트 동시)

```bash
[ -n "$CMUX_SOCKET_PATH" ] && cmux set-progress 0.5 --label "Phase 2: 병렬 테스트 (11 agents)"
```

> ⚡ **병렬 실행 필수**: 아래 11개 Task() 호출을 **하나의 응답 블록에서 동시에** 실행해야 진정한 병렬 처리입니다.
> 순차 실행(하나 완료 후 다음 실행)은 처리 시간이 11x slower 길어집니다.
> Claude Code Agent Teams에서 병렬성은 단일 응답의 여러 Tool call로 구현됩니다.

```
Task(name: "functional-tester", ...)              # 기능 + DB 반영 확인
Task(name: "visual-inspector", ...)               # UI/접근성
Task(name: "api-interceptor", ...)                # 네트워크 + og:image
Task(name: "perf-auditor", ...)                   # 성능
Task(name: "social-share-auditor", ...)           # OG/KakaoTalk/PWA
Task(name: "db-validator", ...)                   # DB CRUD
Task(name: "touch-interaction-validator", ...)    # 터치/스와이프 (v5 신규)
Task(name: "image-optimizer", ...)                # 이미지 최적화 (v5 신규)
Task(name: "security-auditor", ...)   # 보안 헤더/쿠키/민감정보 (v5 신규)
Task(name: "seo-auditor", ...)        # SEO 메타/sitemap/구조화데이터 (v5 신규)
Task(name: "error-resilience", ...)   # 404/콘솔에러/에러바운더리 (v5 신규)
```

> 💡 **에이전트 실패 처리**: 개별 에이전트가 타임아웃(10분) 또는 오류로 실패하면,
> 해당 에이전트의 결과 파일을 `{"grade": "N/A", "error": "에이전트 실패 또는 타임아웃"}` 으로 생성 후 계속 진행.
> 단, 에이전트 이름을 `incomplete_agents` 리스트에 기록 — Phase 3가 커버리지 라인과 등급 상한 계산에 반드시 사용한다.

**touch-interaction-validator 프롬프트**:
```
당신은 playwright-test-v5의 touch-interaction-validator입니다.
대상 URL: [URL]
출력 파일: tests/results/touch-report.json

agents/touch-interaction-validator.md의 프로토콜을 따르세요.
주요 작업:
1. onTouchStart/onTouchEnd 핸들러가 있는 파일 탐지
2. touch-action CSS 미설정 탐지 (스와이프 무반응 원인)
3. 동적 src img에 key prop 누락 탐지
4. 100vh vs 100dvh 사용 현황 확인
5. 스와이프 임계값 패턴 분석
6. Playwright로 실제 스와이프 시뮬레이션 (가능한 경우)
```

**image-optimizer 프롬프트**:
```
당신은 playwright-test-v5의 image-optimizer입니다.
대상 URL: [URL]
출력 파일: tests/results/image-report.json

agents/image-optimizer.md의 프로토콜을 따르세요.
주요 작업:
1. public/ 디렉토리 이미지 용량 스캔 (1MB+ 탐지)
2. WebP/AVIF 사용 현황 확인
3. Next.js <Image> vs <img> 직접 사용 탐지
4. Next.js Image sizes prop 설정 검증
5. 실제 URL 이미지 응답 크기 확인 (curl)
6. WebP 변환 가이드 생성
```

### Phase 2.5: 발견 검증 (finding-verifier)

```bash
[ -n "$CMUX_SOCKET_PATH" ] && cmux set-progress 0.8 --label "Phase 2.5: 발견 검증"
```

11개 병렬 에이전트 완료 후, 13개 결과 JSON에서 critical/high finding 존재 여부 확인:

- **0건이면 Phase 2.5 전체 건너뜀** — REPORT.md에 "검증 생략 — critical/high 발견 없음" 표기 (클린 사이트 경로 비용 0)
- 1건 이상이면 finding-verifier 단일 에이전트 스폰 (동일 Task 템플릿):

```
Task(
  subagent_type: "general-purpose",
  name: "finding-verifier",
  team_name: "playwright-test-v5",
  prompt: """당신은 playwright-test-v5의 finding-verifier입니다.
tests/results/*.json 의 critical/high finding을 원본 증거를 무시하고 처음부터 재현하세요.
agents/finding-verifier.md의 프로토콜을 따르세요 (최대 15건, 10분 타임아웃, $BROWSER_MODE 준수).
결과를 tests/results/verification-report.json에 저장하세요.
완료 후 test-lead에게 confirmed/refuted/unreproducible 요약을 SendMessage로 전송하세요."""
)
```

### Phase 3: 결과 취합 및 REPORT.md 생성

```bash
[ -n "$CMUX_SOCKET_PATH" ] && cmux set-progress 0.9 --label "Phase 3: 리포트 생성"
```

13개 JSON 파일 + `verification-report.json`(Phase 2.5 실행 시) 읽기 후 REPORT.md 생성 (touch + image 섹션 포함).

**검증 결과 반영**: confirmed + unverified finding만 등급에 반영. refuted finding은 등급에서 제외하고
부록 "검증에서 기각된 항목"에 반증 증거와 함께 나열. 등급 섹션에 한 줄 추가: "검증: N건 확인 / N건 기각 / N건 미검증".

**등급 산정 규칙** (LOOP-PROTOCOL [d] COVERAGE HONESTY — agents/test-lead.md Phase 3과 동일):
- 커버리지 = 완료 에이전트 / 13. REPORT.md 헤더에 `**커버리지**: N/13 에이전트 완료 (X%)` 출력 + `incomplete_agents` 목록 표기
- N/A 1-2개 → 최대 B / 3-5개 → 최대 C / 6개 이상 → **Incomplete** (cmux 알림에도 등급 대신 Incomplete)
- confirmed critical finding 1건 이상 → 종합 등급 상한 C (노하우 #17)
- REPORT.md 상단에 선언된 성공 기준 + 종합 pass/fail 명시
- 증거 위생: 비-N/A JSON이 유효하고 >200 bytes인지, functional/visual pass 시 tests/screenshots/ 비어있지 않은지 확인. 빈/깨진 파일은 N/A 취급

팀 종료: shutdown_request → shutdown_response 확인 → TeamDelete.

```bash
# cmux 환경: 완료 알림
if [ -n "$CMUX_SOCKET_PATH" ]; then
  GRADE=$(cat tests/results/REPORT.md | grep -oE "등급: ([A-F]|Incomplete)" | head -1 || echo "등급: -")
  cmux set-progress 1.0 --label "CS-test 완료"
  cmux notify --title "CS-test 완료" --body "REPORT.md 생성됨 — $GRADE"
  cmux set-status "cs-test" "done" --icon "checkmark"
fi
```

---

## v5 핵심 노하우 (MWC 2026 세션 학습)

### 1. touch-action 미설정 → 스와이프 무반응 (Critical)
- **증상**: `onTouchStart`/`onTouchEnd` 핸들러가 있는데 스와이프가 동작 안 함
- **원인**: `touch-action` CSS 미설정 → 브라우저가 수평 제스처를 가로채서 핸들러 미호출
- **해결**: 스와이프 컨테이너에 `style={{ touchAction: 'pan-y' }}` 추가
- **핀치줌+스와이프**: `touchAction: 'pan-x pan-y pinch-zoom'`
- **탐지**: `grep -rn "onTouchStart" src/` → 같은 파일에 `touchAction` 없으면 위험

### 2. React modal 이미지 교체 불가 (key prop 누락)
- **증상**: `modalPage` state 변경 → 페이지 번호는 증가하지만 이미지가 안 바뀜
- **원인**: React가 같은 `<img>` DOM 요소 재사용 → src 변경만으로는 브라우저 줌 상태 미리셋
- **해결**: `<img key={modalPage} src={...} />` → 강제 리마운트

### 3. PDF/대용량 이미지 최적화
- **발견**: PDF 9페이지 JPG 변환 → 페이지당 2.4~3.7MB, 총 ~26MB
- **영향**: 느린 네트워크(MWC 현장 Wi-Fi)에서 수십 초 로딩
- **해결**: WebP 변환 시 ~60% 절감 (페이지당 ~1MB)
  ```python
  pix.save(f'page-{i+1:02d}.webp')  # PyMuPDF WebP 저장
  ```

### 4. 100vh vs 100dvh (iOS Safari)
- **증상**: iOS Safari에서 모달이 주소창에 가려짐
- **해결**: `100dvh` (dynamic viewport height) 사용

### 5. 스와이프 임계값 최적값
```typescript
// 탭 네비게이션 (낮은 임계값 - 빠른 반응)
if (dt < 500 && Math.abs(dx) > 40 && Math.abs(dx) > Math.abs(dy)) { ... }

// 풀스크린 모달 뷰어 (높은 임계값 - 핀치줌과 구별)
if (dt < 400 && Math.abs(dx) > 60 && Math.abs(dx) > Math.abs(dy) * 1.5) { ... }
```

### 6. landscape 모드 이미지 클리핑 방지
- **해결**: `maxHeight: calc(100dvh - 96px)` → 헤더 높이를 제외한 실제 뷰포트

## v4 핵심 노하우 (계승)

### 7. Vercel 배포 차단: CVE-2025-66478
- Next.js 15.1.7 이하 → Vercel 배포 차단
- **해결**: `npm install next@latest`

### 8. tsconfig path alias 오류
- `"@/*": ["./*"]` → `"@/*": ["./src/*"]` 로 수정

### 9. Tailwind v4 CSS 호환성
- `@tailwind base` → `@import "tailwindcss"` 교체

### 10. og:image content-length: 0 버그
- **탐지**: `curl -sI [og:image URL] | grep content-length` → 0
- **해결**: 정적 PNG + 절대 URL

---

## 출력 파일 목록

| 파일 | 담당 에이전트 | 내용 |
|------|-------------|------|
| `tests/results/build-report.json` | build-validator | 빌드/보안/의존성 검증 |
| `tests/results/page-map.json` | page-explorer | 페이지 구조 + OG/PWA |
| `tests/results/functional-report.json` | functional-tester | 기능 + DB 반영 |
| `tests/results/visual-report.json` | visual-inspector | 시각/접근성 |
| `tests/results/api-report.json` | api-interceptor | 네트워크 + og:image |
| `tests/results/performance-report.json` | perf-auditor | Core Web Vitals |
| `tests/results/social-share-report.json` | social-share-auditor | OG/KakaoTalk/PWA |
| `tests/results/db-report.json` | db-validator | DB CRUD 검증 |
| `tests/results/touch-report.json` | touch-interaction-validator | 터치/스와이프 검증 *(v5)* |
| `tests/results/image-report.json` | image-optimizer | 이미지 최적화 분석 *(v5)* |
| `tests/results/security-report.json` | security-auditor | 보안 감사 *(v5 신규)* |
| `tests/results/seo-report.json` | seo-auditor | SEO 분석 *(v5 신규)* |
| `tests/results/error-resilience-report.json` | error-resilience | 오류 복원력 *(v5 신규)* |
| `tests/results/verification-report.json` | finding-verifier | critical/high finding 재검증 결과 *(Phase 2.5)* |
| `tests/results/REPORT.md` | test-lead | 종합 리포트 |

---

## 플러그인 개발 노하우 (2026-04-11 세션)

> 이 섹션은 playwright-test-v5 개선 작업에서 발견된 실제 이슈와 교훈입니다.

### 11. test-lead 버전 문자열 불일치 버그 (Critical)

- **증상**: v5 플러그인인데 test-lead.md가 `playwright-test-v4`, `team_name: "playwright-test-v4"` 를 참조
  → Phase 2에서 touch-interaction-validator와 image-optimizer(2개 신규 에이전트)가 미등록
- **원인**: 이전 버전(v4)에서 파일을 복사할 때 버전 문자열 일괄 교체 누락
- **탐지**: `grep -rn "playwright-test-v4" agents/` → 잔존 참조 즉시 발견
- **해결**: 버전 업그레이드 시 반드시 `grep -rn "v[이전버전]" agents/ skills/ commands/` 로 전체 확인

### 12. Agent Teams 진정한 병렬 실행 조건

- **핵심**: Phase 2의 모든 Task() 호출은 **단일 응답 블록**에서 동시에 실행해야 진정한 병렬 처리
- **직렬 실행 오류**: 에이전트가 Task()를 하나씩 순서대로 실행하면 11 에이전트 × 15분 = 165분 소요
- **병렬 실행**: 단일 블록에서 동시 실행하면 이론상 15분 내 완료
- **SKILL.md 명시 필수**: 에이전트가 이 규칙을 모르면 자연스럽게 직렬 실행함
- **callout 위치**: Phase 2 Task() 코드블록 바로 위에 ⚡ CRITICAL 경고 배치

### 13. 에이전트 역할 경계 미설정 → 3가지 중복 작업 발견

실제 발견된 중복 (2026-04-11):
- **og:image 검증**: api-interceptor(Step 4) + social-share-auditor → api-interceptor에서 제거
- **DB 반영 검증**: functional-tester(Step 4) + db-validator → functional-tester에서 제거, UI 레벨만 담당
- **이미지 lazy-load 검사**: perf-auditor(Step 3 imageOptimization) + image-optimizer → perf-auditor에서 제거

**원칙**: 하나의 검증 항목 = 하나의 에이전트만 담당. 각 에이전트 파일 상단에 `📌 역할 경계` 노트 필수.

### 14. 플러그인 설치 후 활성화 지연

- **증상**: 새 플러그인 파일 생성 완료 후 즉시 `/plugin-skill` 실행 → `Unknown command` 오류
- **원인**: Claude Code는 세션 **시작 시**에만 플러그인을 로드함. 런타임 핫로드 불가
- **해결**: `/clear` 입력 후 새 세션 시작 → 플러그인이 인식됨
- **확인**: `known_marketplaces.json` 및 `settings.json`의 `enabledPlugins`에 등록되어 있어야 함

### 16. 테스트 + 자동 수정 워크플로우 (gstack /qa 학습, 2026-04-13)

- **상황**: CS-test는 버그 발견 후 리포트 생성에서 멈춤. 사용자가 수동으로 수정해야 함.
- **발견**: gstack `/qa`는 버그 발견 즉시 코드를 수정하고 atomic commit → 재검증 루프를 실행. Before/after 헬스 스코어로 개선 측정.
- **교훈**: CS-test에 `--fix` 플래그 추가 고려. 활성화 시 test-lead가 각 에이전트 완료 후 수정 루프 실행. 3가지 티어(Quick/Standard/Exhaustive) 도입으로 테스트 깊이 조절 가능.

### 17. 리포트 항목 위험도 분류 (antigravity 패턴 학습, 2026-04-13)

- **상황**: 현재 리포트는 모든 이슈를 동등하게 나열. 사용자가 우선순위 파악 어려움.
- **발견**: antigravity-awesome-skills의 9-section SKILL.md 템플릿에서 `risk: safe|warn|critical` 레이블링 패턴 발견. 각 발견 항목에 위험도를 명시하면 test-lead의 등급화(A/B/C/D)가 더 정밀해짐.
- **교훈**: 각 에이전트 JSON 리포트에 `"risk": "critical|warn|safe"` 필드 추가. test-lead가 critical 이슈 수를 기반으로 최종 등급 결정하도록 프로토콜 업데이트.
- → ✅ 반영됨 (2026-06): Phase 3 등급 산정 규칙 (confirmed critical → 등급 상한 C) + finding-verifier의 critical/high 필터 기준으로 적용.

### 18. 에이전트 역할 경계 명세 강화 (2026-04-13)

- **상황**: 노하우 #13에서 3개 중복 작업이 발견됨. 이후 중복 방지 메커니즘 부재로 재발 가능성 높음.
- **발견**: 각 agent .md 파일에 `📌 OWNS` / `❌ DOES NOT OWN` 섹션을 상단에 고정하면 중복 방지 효과가 명확해짐. impeccable의 "명시적 경계 문서화" 철학과 동일.
- **교훈**: 새 에이전트 추가 시 반드시 OWNS/DOES NOT OWN 섹션 작성. version-up 시 이 섹션들을 검토하여 중복 없음 확인.

### 19. Windows WSL 환경 — `wsl --list` hang과 API 응답시간 급변 패턴 (2026-04-19)

- **상황**: Windows 앱의 `/api/check-wsl` 엔드포인트가 Docker Desktop 실행 여부에 따라 응답시간이 0.7초 ↔ 4초 이상으로 급변함
- **발견**: `wsl --list --quiet`는 Docker Desktop이 WSL 서비스를 점유하면 hang. 테스트 환경에 Docker Desktop이 있으면 WSL 관련 API가 일관성 없는 응답 시간을 보임. 올바른 구현은 Windows Registry에서 직접 distro 목록을 읽는 방식.
- **교훈**: Windows 앱 테스트 시 WSL 관련 API는 `time_total > 2s`이면 hang 패턴 의심. Docker Desktop 동시 실행 상태와 미실행 상태 두 가지로 반드시 테스트. playwright로 API 응답시간도 assertion 추가 권장 (`expect(duration).toBeLessThan(2000)`).

### 15. cs-sync 이중 레포 구조 충돌 처리

이 플러그인의 작업 흐름에서 발견된 git 충돌 패턴:
- **구조**: 소스 레포(`~/cs_plugins`) + 로컬 마켓플레이스(`~/.claude/plugins/marketplaces/CSnCompany_2-0`) 두 곳이 동일 remote를 바라봄
- **충돌 시나리오**: 마켓플레이스 레포에서 직접 commit/push → 소스 레포에는 같은 파일이 untracked로 존재 → pull 시 "untracked file overwrite" 오류
- **해결**: `rm -rf [충돌 파일]` 후 `git pull` → 파일 내용이 동일하면 안전
- **정석 흐름**: 항상 소스 레포(`~/cs_plugins`)에서 편집 → commit/push → 마켓플레이스에서 pull

### 20. Next.js 서브 페이지 OG 메타데이터 페이지별 검증 필요 (2026-04-20)

- **상황**: scrum 페이지 Notion 북마크에서 MAU 페이지 제목/설명이 노출됨
- **발견**: 'use client' 페이지는 metadata export 불가 → layout.tsx 없으면 루트 OG 메타데이터 상속. CS-test social-share-auditor가 페이지별 og:title 검증 미수행으로 미탐지됨.
- **교훈**: social-share-auditor가 각 라우트 URL별 og:title/og:description을 실제 fetch로 검증해야 함. 루트 layout과 동일한 값이면 버그 플래그.

### 21. 테스트 실행 전 성공 기준 정의 (Karpathy goal-driven execution, 2026-04-20)

- **상황**: 14-agent 팀을 실행했지만 "성공"이 무엇인지 불명확해 결과 판단이 어려웠음
- **발견**: Karpathy의 "goal-driven execution" — 실행 전 `[Step] → verify: [check]` 형태의 성공 기준을 명시하면 에이전트가 목표 지향적으로 동작하고 결과 판단이 명확해짐
- **교훈**: test-lead가 URL 확인 직후 "성공 기준: [1문장]"을 출력하고 시작. 예: "P0 에러 0건, 성능 점수 70+, SEO 등급 B 이상"
- → ✅ 반영됨 (2026-06): 실행 프로토콜 사전 준비 3단계 + 전 에이전트 프롬프트 `passFail` 필드 전파로 승격 (중복 승격 방지).

### 22. 수정 후 핵심 경로 재검증 패턴 (gstack canary 학습, 2026-04-20)

- **상황**: 테스트 완료 후 수정 사항을 적용했으나 수정이 다른 페이지에 영향을 줬는지 검증하지 않음
- **발견**: gstack `/canary`는 수정 후 핵심 페이지들을 재방문하며 console 에러·성능 회귀·페이지 실패를 재확인함. full re-run보다 훨씬 빠르게 회귀 감지 가능.
- **교훈**: 수정 사항이 생겼을 때 test-lead가 "영향 범위 내 핵심 3-5개 경로" 미니 재테스트 단계를 옵션으로 제공할 것.

### 23. Playwright 테스트 시 dev 서버 포트 vs production 포트 구분 (2026-04-21)

- **상황**: port 9000 앱을 Playwright로 테스트했는데 V3 디자인 변경이 반영 안 됨
- **발견**: port 9000은 구버전 production build를 서빙, 실제 개발 서버는 vite --port 10089로 별도 실행 중. `ps aux | grep vite`로 실제 dev 포트 확인 필요. lsof -ti로 PID 확인 후 포트 특정.
- **교훈**: 테스트 전 항상 dev server 포트 확인 (`lsof -ti :포트` 또는 `ps aux | grep vite`). production build와 dev server가 공존하는 프로젝트에서 특히 주의.
- → ✅ 반영됨 (2026-06): 실행 프로토콜 사전 준비 2단계(서빙 대상 검증)로 승격 (중복 승격 방지).

### 24. Vercel 빌드 로그 warning을 테스트 신호로 검사 (2026-04-21)

- **상황**: Vercel 배포가 성공(exit 0)했지만 실제로는 `"PortalActions" is not exported by "src/PortalManager.tsx"` 경고가 빌드 로그에 존재. 런타임에서 해당 액션 호출 시 undefined 참조 오류 발생.
- **발견**: Rollup/Vite가 named re-export 오류를 warning으로 처리하면 빌드 exit 0 + 런타임 undefined. Vercel deploy 성공 = 빌드 warning 없음이 아님. 로컬 빌드와 Vercel 원격 빌드의 warning 기준도 다를 수 있음.
- **교훈**: Vercel 배포 테스트 시 deploy status뿐 아니라 빌드 로그의 `[plugin] ... is not exported by` 패턴도 검사. CI 파이프라인에 `--reporter=verbose`로 warning을 exit 1로 처리하거나, 배포 후 핵심 액션(버튼 클릭 등)을 Playwright로 스모크 테스트하여 런타임 undefined를 조기 감지.

### 25. Playwright waitUntil 전략 — Next.js dev 서버에서 networkidle 타임아웃 (2026-04-22)

- **상황**: Next.js dev 서버(node_modules가 Google Drive에 마운트된 환경)에서 Playwright `waitUntil: 'networkidle'` 사용 시 타임아웃 발생.
- **발견**: `networkidle`은 네트워크 요청이 500ms 동안 없어야 완료로 판단. I/O가 느린 환경(Google Drive, 원격 파일시스템)에서는 Next.js dev 서버가 계속 백그라운드 요청을 발생시켜 조건을 만족하지 못함.
- **교훈**: Next.js dev 서버 테스트 시 `waitUntil: 'domcontentloaded'`로 변경. networkidle은 정적 사이트나 production 빌드에만 사용.

### 26. Playwright MCP 브라우저 컨텍스트 반복 실패 시 API 직접 테스트로 대체 (2026-04-24)

- **상황**: navigate/browser_tabs 호출 시 'Target page, context or browser has been closed' 에러가 반복되어 UI 테스트 불가.
- **발견**: Playwright MCP 브라우저가 닫혀있으면 새 탭 생성도 동일 에러 발생. 단, API 서버(localhost:3001)가 살아있으면 curl로 핵심 엔드포인트를 직접 호출해 기능 검증 가능. ports 저장/조회, create-folder, pick-folder 엔드포인트를 순서대로 curl 테스트하면 UI 없이도 CRUD 로직 검증 완료.
- **교훈**: UI 자동화가 막히면 Playwright 재시도 대신 API 레이어 직접 검증으로 전환. 핵심 비즈니스 로직(저장·조회·생성)은 HTTP API로 충분히 검증 가능하며, UI 테스트는 별도 세션에서 Playwright 재시작 후 시도.

### 27. Fixed-position 드롭다운 테스트 패턴 (2026-04-24)

- **상황**: 포트관리기 ⌄ 드롭다운 메뉴 항목을 playwright로 추출해야 했음
- **발견**: `page.locator('[style*="fixed"]').locator('button').allTextContents()`로 fixed-position 메뉴 항목 텍스트 일괄 추출 가능. `detectDevServers()`가 port 9000 Vite 서버를 여러 서버(3001/5173/5000/9000) 중 자동 감지함.
- **교훈**: fixed-position 컨텍스트 메뉴/드롭다운은 `[style*="fixed"]` 로케이터로 빠르게 접근. detectDevServers 결과가 여러 개면 사용자에게 확인 후 target 지정.

### 28. 모바일 가로 오버플로우 — VIEWPORT env + scrollWidth/clientWidth 단순 비교 (2026-04-28)

- **상황**: Vercel 배포 portal이 iPhone 세로(375px)에서 UI 잘림. 사용자 신고 후 5개 구체 원인(maxWidth:460/440 모달, scrollbar-none pills, 절대 위치 드롭다운 등) 식별 + 회귀 방지 필요.
- **발견**: 한 smoke.mjs 안에 `VIEWPORT=mobile` 환경변수 분기 추가 → `chromium.launch + newContext({viewport:{width:375,height:812}, isMobile:true})` 로 동일 시나리오 재실행. 핵심 검증: `await page.evaluate(() => ({ scrollWidth: document.documentElement.scrollWidth, clientWidth: document.documentElement.clientWidth }))` → `scrollWidth ≤ clientWidth + 1` (1px 여유). 한 줄 assertion이 5개 overflow 버그 모두 잡음.
- **교훈**: 모바일 회귀 테스트는 Lighthouse나 풀스크린샷 비교 같은 무거운 도구 없이도 **scrollWidth 비교 1줄**로 80% 가치 확보. 비밀번호 게이트 같은 가드가 있으면 게이트 자체에서도 이 검증을 실행해 두면 deploy 후 즉시 회귀 감지. package.json scripts 에 `"test:smoke:mobile": "VIEWPORT=mobile TARGET=vercel node tests/smoke.mjs"` 같은 한 줄 별칭 표준화.

### 29. Vercel 자동 배포 미트리거 시 CLI 강제 배포 (2026-04-28)

- **상황**: GitHub push 후 Vercel 배포 버전이 갱신되지 않음. 코드 수정 후 push를 여러 번 해도 프로덕션이 구버전 유지.
- **발견**: GitHub ↔ Vercel webhook 연동이 끊기면 push 트리거가 무시됨. `npx vercel --prod --yes` 로 CLI에서 직접 프로젝트 루트에서 실행하면 `.vercel/project.json` 의 projectId/orgId를 읽어 즉시 빌드·배포. 배포 URL이 `Aliased: https://xxx.vercel.app` 으로 출력되면 성공.
- **교훈**: 배포 이후 UI 변경이 없거나 placeholder 텍스트가 구버전으로 보이면 자동 배포 미트리거를 의심. 확인법: 로컬 placeholder와 배포 버전 비교. 해결: 프로젝트 루트에서 `npx vercel --prod --yes` 실행.

### 30. formidable allowEmptyFiles + minFileSize 동시 설정 필수 + Radix UI 탭 셀렉터 (2026-05-01)

- **상황**: Next.js 업로드 라우트에서 `allowEmptyFiles: false` → 0바이트 파일 업로드 시 에러. `allowEmptyFiles: true`로 변경해도 "minFileSize (1 bytes) inferior" 에러 지속. Playwright에서 Radix UI 탭을 `[data-value="xxx"]`로 찾으면 항상 0개 반환.
- **발견**: formidable v3은 `allowEmptyFiles`와 `minFileSize`를 독립적으로 체크. `allowEmptyFiles: true`만으로는 `minFileSize` 기본값(1 byte) 검사가 여전히 적용됨. `minFileSize: 0`도 함께 설정해야 0바이트 파일이 통과. Radix UI `TabsTrigger`는 `data-value` 대신 `id="radix-xxx-trigger-youtube"` 패턴으로 렌더링 — `[role="tab"]` + `.filter({hasText: "레이블"})` 조합만 안정적으로 작동.
- **교훈**: formidable 빈 파일 허용 시 `allowEmptyFiles: true, minFileSize: 0` 쌍으로 설정. 서버에서 `file.size === 0` 추가 필터링도 병행. Radix UI 컴포넌트 테스트 시 내부 DOM 속성(data-value, data-state 등)보다 aria role + text 조합 사용.
