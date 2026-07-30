# CSnCompany_2-0 — Claude Code 안에서 바로 쓰는 AI 팀

> 🇰🇷 한국어 · [🇺🇸 English](./README.md)

**한 줄 요약 — 마켓플레이스 하나에 AI 팀원 11명.** 한 번만 설치하면 Claude Code 안에서 CEO, PM, 아키텍트, 디자이너, QA, 코드 리뷰어, DevOps를 슬래시 명령(`/cs-ceo`, `/CS-test` 등) 하나로 호출할 수 있습니다.

> ⚡ **선택 사항: [uv](https://docs.astral.sh/uv/) 설치 시 코드 분석 토큰 70%+ 절감** — `brew install uv` 또는 `curl -LsSf https://astral.sh/uv/install.sh | sh`. 없어도 동작합니다 (자동 fallback).

---

## 🤔 이게 뭔가요? (처음 보시는 분들께)

[Claude Code](https://docs.claude.com/en/docs/claude-code)는 Anthropic이 만든 공식 AI 코딩 CLI입니다. 여기에는 **플러그인** 시스템이 있어서, 슬래시 명령·에이전트·스킬을 묶어서 추가로 설치할 수 있어요.

**CSnCompany_2-0**은 **11개 플러그인**을 한 번에 묶어둔 마켓플레이스입니다. 각 플러그인은 가상의 AI 회사 안에서 한 명의 전문가 역할을 합니다:

```
사용자 ──▶ /cs-ceo "대시보드 만들고 싶어"
                │
                ▼
        🧭 CEO  필요한 팀원을 자동으로 부름
                │
   ┌────────────┼────────────┬────────────┐
   ▼            ▼            ▼            ▼
🏗️ 플랜      🎨 디자인     🧪 테스트     🚢 배포
```

어떤 명령을 써야 할지 모르겠다면 `/cs-ceo "하고 싶은 일"`이라고만 입력하세요. CEO가 알아서 적절한 팀원을 호출합니다. 직접 부르고 싶으면 슬래시 명령을 골라 쓰면 되고요.

---

## 🎨 디자인 레퍼런스 샘플

내 Next.js/Tailwind 페이지에 그대로 `--audit` / `--apply` 할 수 있는, 실제로 캡처된 디자인 언어 두 가지입니다.

| `cs-design-sample1` — CS Archive (paper↔dark 토큰) | `cs-design-sample2` — 다크 에디토리얼/터미널 |
|:---:|:---:|
| ![cs-design-sample1 미리보기](plugins/cs-design-sample1/preview/preview.png) | ![cs-design-sample2 미리보기](plugins/cs-design-sample2/preview/preview.png) |
| 기본은 누런 종이(`#F4EFE3`) + 딥 틸 액센트, dark 토글은 근흑색 + 사이언 — `--cs-accent` 토큰 하나로 전체 재스킨. 고스트 넘버, IBM Plex Mono + Noto Serif KR | 근흑색 네이비(`#05070d`) 배경, 사이언 액센트, IBM Plex Mono + Noto Serif KR, 그리드 오버레이 + 글로우 장식 — 다크 콘텐츠/에디토리얼 사이트 |

---

## 👥 팀 멤버

| 멤버 | 플러그인 | 슬래시 명령 | 하는 일 |
|------|----------|------------|---------|
| 🧭 **CEO** | `cs-ceo` | `/cs-ceo "목표"` | 공수 추정 → 팀원 선정 → 배분. **헷갈리면 일단 여기서 시작하세요.** |
| 💬 **PM** | `cs-clarify` | `/cs-clarify` | 소크라테스식 질문으로 숨겨진 가정을 드러내고 과잉 설계 방지 |
| 🏗️ **아키텍트** | `CS-plan` | `/CS-plan "기능"` | TDD + Clean Architecture 플랜: 도메인 분석, 아키텍처, 테스트 전략, 체크리스트 |
| 🎨 **디자이너** | `cs-design` | `/cs-design <url>` | 5-에이전트 디자인 리뷰: 비주얼 계층, 인터랙션, 디자인 시스템, 반응형/접근성, 안티 패턴 |
| 🎨 **디자인 레퍼런스** | `cs-design-sample1` | `/cs-design-sample1` | CS Archive 토큰 시스템 (paper 기본/dark 토글), Next.js 스터디·콘텐츠 앱용 |
| 🎨 **디자인 레퍼런스** | `cs-design-sample2` | `/cs-design-sample2` | 다크 에디토리얼/터미널 스타일 가이드 (Next.js 다크 콘텐츠 사이트) |
| 🧪 **QA 엔지니어** | `CS-test` | `/CS-test <url>` | 14-에이전트 웹 테스트: 보안, SEO, 성능, 접근성, DB, PWA, 터치, 이미지 |
| 🔍 **코드 리뷰어** | `CS-codebase-review` | `/CS-codebase-review ./src` | 5-에이전트 리뷰: 아키텍처, 품질, 보안, 성능, 유지보수성 |
| 🚢 **DevOps** | `cs-ship` | `/cs-ship` | PR 직전 검증: 스펙 준수, 커버리지, 커밋 메시지 |
| ⚡ **팀 리더** | `cs-smart-run` | `/cs-smart-run "작업"` | Opus로 계획 → Sonnet 에이전트로 병렬 실행 |
| 📚 **지식 저장소** | `cs-experiencing` | `/cs-experiencing` | 버전별 학습 관리 + `/cs-end` 세션 마무리 *(GitHub push는 플러그인 작성자 전용)* |
| 🗣️ **언어 코치** | `convo-maker` | `/convo-maker` | 세션 Q&A를 자연스러운 미국식 영어 대화로 변환 |

---

## 🚀 60초 안에 설치하기

### 사전 준비

[Claude Code 설치](https://docs.claude.com/en/docs/claude-code/setup):

```bash
npm install -g @anthropic-ai/claude-code
```

실행:

```bash
claude
```

### 1단계 — 마켓플레이스 추가

Claude Code 안에서 입력:

```
/plugin marketplace add intenet1001-commits/CSnCompany_2-0
```

### 2단계 — 원하는 플러그인 설치

골라서 설치하거나, 전부 설치하세요:

```
/plugin install cs-ceo@CSnCompany_2-0
/plugin install cs-clarify@CSnCompany_2-0
/plugin install CS-plan@CSnCompany_2-0
/plugin install cs-design@CSnCompany_2-0
/plugin install cs-design-sample1@CSnCompany_2-0
/plugin install cs-design-sample2@CSnCompany_2-0
/plugin install CS-test@CSnCompany_2-0
/plugin install CS-codebase-review@CSnCompany_2-0
/plugin install cs-ship@CSnCompany_2-0
/plugin install cs-smart-run@CSnCompany_2-0
/plugin install cs-experiencing@CSnCompany_2-0
/plugin install convo-maker@CSnCompany_2-0
```

### 3단계 — Claude Code 재시작

끝입니다. Claude Code에서 `/`만 입력하면 새 명령어가 보입니다.

---

## 🧭 어디서부터 시작해야 할지 모르겠다면?

CEO에게 맡기세요:

```
/cs-ceo "사용자 인증 포함된 대시보드 만들고 싶어"
```

CEO가 공수를 추정하고, 어떤 팀원을 어떤 순서로 부를지 결정합니다(PM → 아키텍트 → 디자이너 등). 사용자는 팀원이 질문할 때만 답하면 됩니다.

---

## 💡 자주 쓰는 워크플로우

### 새 기능을 처음부터 만들기

```
/cs-clarify "Stripe 결제 추가"        # PM: 가정 드러내기
   ↓
/CS-plan "Stripe checkout + webhook"  # 아키텍트: TDD 플랜
   ↓
… 직접 구현 …
   ↓
/CS-test https://staging.example.com  # QA: 14-에이전트 웹 테스트
   ↓
/CS-codebase-review ./src             # 리뷰어: 5-에이전트 코드 리뷰
   ↓
/cs-ship                              # DevOps: PR 직전 게이트
```

### 기존 사이트 점검

```
/cs-design https://example.com    # 비주얼 + UX 리뷰
/CS-test https://example.com      # 보안/SEO/성능/접근성
```

### 그냥 CEO한테 다 맡기기

```
/cs-ceo "랜딩 페이지 점검하고 뭐부터 고쳐야 하는지 알려줘"
```

---

## 🏛️ 아키텍처 — Lead-Agent 패턴 + Python Pre-Pass

모든 멀티 에이전트 플러그인은 **lead-agent 패턴**을 사용합니다. 메인 대화에서 **lead 에이전트 1개**만 생성하고, lead가 내부에서 N명의 워커를 오케스트레이션합니다. 워커의 원시 출력은 메인 컨텍스트를 오염시키지 않고, 최종 합성된 리포트만 반환됩니다.

```
메인 Claude Code 대화
  └─ SKILL.md (얇은 래퍼: 인자 파싱 + lead Task 1개 생성)
       └─ lead 에이전트 (자체 컨텍스트: N명 워커 오케스트레이션)
            ├─ worker-1 → 결과 파일
            ├─ worker-2 → 결과 파일
            └─ worker-N → 결과 파일
            → 최종 문서 합성 → 메인 컨텍스트로 반환
```

이 구조 덕분에 메인 대화는 깔끔하게 유지되면서도 뒤에서는 대규모 병렬 작업이 돌아갑니다.

### Python Pre-Pass (선택 사항, uv 또는 python3 필요)

코드 분석 플러그인은 에이전트를 스폰하기 **전에** Python 스크립트로 구조 데이터를 결정론적으로 추출합니다. 에이전트가 원시 파일 전체를 읽는 대신 컴팩트한 JSON 요약을 받아 토큰을 70%+ 절감합니다.

```
plugins/shared/
├── _bootstrap.sh          ← uv/python3 감지 + graceful fallback
└── scripts/
    ├── extract_summary.py ← 파일 구조 + import 그래프 → JSON
    ├── ts_rust_diff.py    ← TypeScript ↔ Rust struct 필드 불일치 감지
    └── abspath_check.py   ← 하드코딩 절대경로 감지
```

**uv/python3 없을 때**: 플러그인이 그대로 동작합니다 (에이전트가 직접 파일 읽기).
**uv/python3 있을 때**: 에이전트가 사전 추출된 JSON을 받아 더 빠르고 정확하게 분석합니다.

### 플러그인별 에이전트 수

| 플러그인 | 에이전트 | 모드 |
|----------|----------|------|
| CS-test | 14 | Phase 1 순차 (빌드, 페이지 탐색) → Phase 2 병렬 (12명 전문가) |
| CS-plan | 4 | 병렬: 도메인, 아키텍처, TDD, 체크리스트 |
| CS-codebase-review | 5 | 병렬: 아키텍처, 품질, 보안, 성능, 유지보수성 |
| cs-design | 5 | 병렬: 비주얼, 인터랙션, 디자인 시스템, 반응형/a11y, 안티 패턴 |
| cs-clarify | 4 | 순차 소크라테스식 질문 |
| cs-ship | 4 | 병렬 PR 직전 검증 |
| cs-ceo | 1명 lead → 다른 팀원으로 라우팅 | 적응형 |

---

## 📁 폴더 구조

```
CSnCompany_2-0/
├── .claude-plugin/
│   └── marketplace.json           # 마켓플레이스 매니페스트
├── plugins/
│   ├── shared/                    # 🔧 공유 Python 스크립트 (토큰 최적화)
│   │   ├── _bootstrap.sh          #    uv/python3 감지 + graceful fallback
│   │   └── scripts/
│   │       ├── extract_summary.py #    파일 구조 + import 그래프 → JSON
│   │       ├── ts_rust_diff.py    #    TS ↔ Rust struct 필드 불일치
│   │       └── abspath_check.py   #    하드코딩 절대경로 감지
│   ├── cs-ceo-v11/                # 🧭 CEO 오케스트레이터
│   ├── cs-clarify-v1/             # 💬 PM
│   ├── CS-plan-v21/               # 🏗️ 아키텍트
│   ├── cs-design-v19/             # 🎨 디자이너
│   ├── cs-design-sample1/         # 🎨 디자인 레퍼런스 (CS Archive 토큰, paper/dark)
│   ├── cs-design-sample2/         # 🎨 디자인 레퍼런스 (다크 에디토리얼)
│   ├── CS-test-v26/               # 🧪 QA
│   ├── CS-codebase-review-v29/    # 🔍 리뷰어 (Python pre-pass 지원)
│   ├── cs-ship-v1/                # 🚢 DevOps
│   ├── cs-smart-run/              # ⚡ 팀 리더
│   ├── cs-experiencing-v8/        # 📚 지식 저장소
│   └── convo-maker/               # 🗣️ 언어 코치
├── docs/                          # 추가 문서
├── README.md                      # 영문 README
└── README.ko.md                   # 이 문서
```

각 플러그인 폴더에는 자체 `.claude-plugin/plugin.json`이 있고, 필요에 따라 `agents/`, `commands/`, `skills/`가 들어 있습니다. 이 하위 디렉토리들은 파일시스템에서 자동 발견(auto-discovery)되므로, `plugin.json` 안에 `agents`/`commands`/`skills`를 배열 필드로 선언하면 안 됩니다 — 매니페스트 검증에서 `Invalid input` 에러가 발생합니다.

---

## 🧠 학습 시스템 쉬운 가이드

이 팀은 세션을 거듭할수록 똑똑해집니다. 전체 사이클을 쉬운 말로 설명하면:

```
 작업 세션 ──▶ 1. 캡처 ──▶ 2. 저장 ──▶ 3. 회상 ──▶ 다음 세션은 더 똑똑하게
                  ▲                                     │
                  └───────── 4. 게이트 (기계 검증) ◀─────┘
```

1. **캡처** — 세션을 마무리(`/cs-end`)하거나 버전업을 실행하면, AI가 이번 세션에서 배운 것(버그 패턴, 우회법, 디자인 규칙)을 추출해 번호가 붙은 학습(#1 … #128, 계속 증가)으로 저장합니다. 저장 전 반박(skeptic) 검증을 먼저 통과해야 합니다.
2. **저장** — 모든 학습은 순수 마크다운입니다: `cs-experiencing` SKILL.md의 **학습 INDEX**에 1줄 + 본문은 `knowledge/` 주제 파일(`react-frontend.md`, `git-worktree.md`, `deployment.md`, `figma-design-system.md` 등)에 기록됩니다. 오케스트레이터 자체 학습만 인라인으로 남습니다.
3. **회상** — 팀을 가동하기 직전(`/CS-test`, `/CS-plan`, `/cs-design` 등)에 오케스트레이터가 현재 태스크의 키워드로 INDEX를 grep해서, 매칭된 상위 2-3건을 에이전트 프롬프트에 그대로 주입합니다. 에이전트가 0에서 시작하지 않고 과거 경험을 가지고 출발합니다.
4. **게이트** — 결정론적 게이트(`bash plugins/shared/run_prepass.sh index-check`)가 저장·버전업 때마다 INDEX↔본문 무결성을 기계 검증합니다: INDEX 누락 없음, 위치 포인터 정상, 번호 전역 유일·연속, 인라인 상한 준수. LLM 체크리스트는 드리프트하지만 이 게이트는 안 합니다.

**왜 DB가 아니라 파일인가요?**

| | 마크다운+git (현재) | 호스팅 DB (예: Supabase) |
|---|---|---|
| 지식을 받는 사람 | **플러그인을 설치한 모든 사용자** — 학습이 레포 안에 들어있어 `git pull` = 전체 동기화 | DB 접속 키를 가진 사람만 |
| 런타임 의존성 | 없음 — 오프라인 동작, 키 불필요 | 회상할 때마다 네트워크 + 인증 |
| 검토·롤백 | `git diff` / `git revert` | 별도 도구 필요 |
| 회상 속도 | ~120KB grep = 밀리초 | 네트워크 왕복 |

2026-07의 10-에이전트 분석 결과, 관계형 DB로 옮기면 회상은 오히려 *느려지고* 공유는 *어려워진다*는 결론이었습니다. 지식 베이스가 플러그인 자체에 실려 다니기 때문에, **이 마켓플레이스를 설치하는 누구나 누적 학습 전체를 자동으로 받게 되고**, 이후 학습도 업데이트 한 번으로 도착합니다 — 계정도, 키도, 설정도 필요 없습니다.

---

## ❓ 자주 묻는 질문

**Q. 11개 다 설치해야 하나요?**
A. 아니요. 필요한 것만 설치하세요. `cs-ceo` 하나만 있어도 대부분 처리되지만, CEO가 다른 팀원을 호출하려면 그 팀원이 설치돼 있어야 합니다.

**Q. 추가 비용이 드나요?**
A. 플러그인 자체는 무료(MIT)입니다. 기존 Claude Code 구독/API 사용량 위에서 그대로 동작합니다.

**Q. 자동 업데이트되나요?**
A. 마켓플레이스에 새 버전이 올라오면 Claude Code가 업데이트 여부를 물어봅니다. git 기반 설치라면 마켓플레이스 폴더에서 `git pull`만 해도 됩니다.

**Q. 설치했는데 슬래시 명령이 안 보여요.**
A. Claude Code를 재시작하세요(Ctrl-C 후 `claude` 다시). 새 플러그인은 시작 시 로드됩니다.

**Q. 토큰 70% 절감은 어떻게 하나요?**
A. [uv](https://docs.astral.sh/uv/)를 설치하세요. `brew install uv`(Mac) 또는 `curl -LsSf https://astral.sh/uv/install.sh | sh`. Python 사전 설치 불필요. 플러그인이 uv를 자동 감지하여 사용하고, 없으면 조용히 기존 방식으로 동작합니다.

**Q. `/cs-end`도 쓸 수 있나요?**
A. `/cs-end`는 플러그인 작성자용입니다. 실행하면 Phase 4(마켓플레이스 repo에 git push)는 자동으로 건너뜁니다. 로컬 세션 학습 저장은 정상적으로 됩니다. `--project /경로`로 본인 프로젝트의 push 상태도 리포트에 포함할 수 있습니다.

**Q. 누적된 학습은 작성자만 쓸 수 있나요?**
A. 아닙니다, 설치한 모두가 받습니다. 학습 베이스(~128건)는 플러그인 레포 안의 순수 마크다운이라 마켓플레이스 설치와 함께 배포되고, 업데이트하면 새 학습도 함께 옵니다. 위의 "학습 시스템 쉬운 가이드" 참조.

**Q. 버그가 있어요 / 기여하고 싶어요.**
A. [github.com/intenet1001-commits/CSnCompany_2-0](https://github.com/intenet1001-commits/CSnCompany_2-0)에서 이슈/PR 환영합니다.

---

## 📜 라이선스

MIT — [LICENSE](LICENSE) 참고.

## 🔗 링크

- [English README](./README.md)
- [GitHub 저장소](https://github.com/intenet1001-commits/CSnCompany_2-0)
- [Claude Code 공식 문서](https://docs.claude.com/en/docs/claude-code)
