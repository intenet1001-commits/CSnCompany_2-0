# Figma·디자인시스템 학습

cs-experiencing 학습 INDEX가 참조하는 본문 모음. 신규 학습은 끝에 append.

### 110. NDS 감사 결과의 '지적된 노드 리스트'만 믿으면 안 됨 — 전체 프레임 색상 스윕 필요 (2026-07-15)
<!-- tier: principle -->

- **상황**: Figma 파일 + 페어링된 HTML 프로토타입을 NDS(디자인 시스템) 규칙에 맞춰 정합화하는 세션. 병렬 2-agent 감사(HTML용/Figma용)가 구체적인 위반 노드 리스트를 만들었고, 그 리스트만 고쳤다.
- **발견**: 이후 사용자의 타겟 육안 스팟체크("퀵바가 Figma처럼 검정색이 아니다")로, 리디자인 이전부터 남아있던 잔여 hex 색상들(entry-hub 프레임의 행 라벨/섹션 헤더, 계좌 수량 텍스트 등)이 드러났다 — 원래 감사의 flagged-node 리스트에 없었다는 이유만으로 손대지 않은 채 방치되어 있었다. 프레임 전체에 대한 전수 `fills` 스윕을 돌려서야 잡혔다.
- **교훈**: 감사→수정 워크플로우에서, 최초 감사가 찾아낸 위반 목록을 "전체 문제 목록"으로 오인하지 않는다. 감사는 특정 시점·특정 관점의 스냅샷일 뿐이므로, 색상/폰트/토큰처럼 전역적으로 적용돼야 하는 속성은 타겟 수정 완료 후에도 전체 프레임/파일에 대한 별도의 전수 스윕 검증 단계를 반드시 둔다.
- **근거**: 사용자 지적 "아티팩트하단의 퀵바는 피그마처럼 검은색이 아닌데" → `figma.currentPage.query`/`findAllWithCriteria`로 5개 프레임 전체 `fills`를 스캔해서야 entry-hub 프레임의 `#17231d`(구버전 잉크색)/`#4a5952`(구버전 뮤트색), 목록화면의 `#666b70`(4번째 미통일 그레이) 등 원래 감사 리스트에 없던 색상들을 발견 (skeptic verifier CONFIRM — 특정 도구/버전에 종속되지 않는, 감사-then-수정 워크플로우 일반에 적용 가능한 원칙).

### 111. 재작성 시 토큰 값을 추측하지 말고 원본 컴포넌트에서 직접 샘플링 (2026-07-15)
<!-- tier: principle -->

- **상황**: HTML 프로토타입을 Figma 소스의 NDS 토큰에 맞춰 재작성하는 서브에이전트 작업 (색상/폰트/캔버스 크기 이식).
- **발견**: 서브에이전트가 Figma `quickmenu_basic` 컴포넌트의 배경색을 이식하면서, 실제 Figma 컴포넌트 인스턴스의 자식 rectangle fill을 조회하지 않고 짐작으로 `#457c12`(짙은 초록)를 새 CSS 토큰(`--nav-bg`)에 넣었다. 나중에 Plugin API로 해당 인스턴스(`I11:636;369:7407`)의 fill을 직접 샘플링해보니 실제 값은 `#222222`(검정에 가까움)였다.
- **교훈**: 디자인 소스(Figma 등)에서 코드로 값을 이식할 때 색상/치수 같은 구체적 값은 절대 기억이나 추측에 의존하지 않는다. 항상 소스 컴포넌트에서 실제 속성(fill/size/font 등)을 직접 조회해 그대로 반영한다 — 추측값은 그럴듯해 보여서 육안 검수에서도 잘 걸러지지 않고, 사용자가 명시적으로 원본과 대조하기 전까지 드러나지 않는다.
- **근거**: HTML 재작성 서브에이전트가 도입한 `--nav-bg: #457c12` (Figma 근거 없음) vs. `figma.getNodeByIdAsync('11:636')` 순회로 확인한 실제 배경 rectangle fill `{r:0.134,g:0.134,b:0.134}` = `#222222` (skeptic verifier CONFIRM — Figma 토큰에 국한되지 않는, 스펙 기반 코드 생성/이식 작업 전반에 적용 가능한 원칙).

### 112. 회귀 수정 시 임의값이 아니라 파일 내 형제 요소의 기존 컨벤션을 따른다 (2026-07-15)
<!-- tier: principle -->
<!-- error-ref: ERR-2026-07-15-001 -->

- **상황**: Figma 프레임의 아이콘/폰트 크기를 NDS 스펙에 맞춰 키우는 수정(터치 타겟 확대 등) 중, 목록 프레임의 콘텐츠가 자체 하단 경계를 넘어가면서 퀵메뉴 네비게이션 바가 잘리는 자체 회귀가 발생했고, 같은 서브에이전트가 이를 스크린샷으로 잡아냈다.
- **발견**: 근본 원인은 해당 프레임(`layoutSizingVertical`)만 유일하게 `FIXED`였고, 형제 프레임 4개는 전부 `HUG`였다는 것 — 콘텐츠가 늘어나도 프레임이 따라 늘어나지 않아 하단이 잘렸다. 임의의 고정 높이값을 계산해 늘리는 대신, 형제 프레임들이 이미 쓰고 있는 컨벤션(`HUG`)으로 맞춰서 해결했다.
- **교훈**: 레이아웃 회귀/버그를 고칠 때는 먼저 같은 계층의 형제 요소들이 어떤 설정(오토레이아웃 sizing mode, 컴포넌트 variant 등)을 쓰는지 확인한다. 그 파일/코드베이스가 이미 쓰고 있는 컨벤션에 맞추는 수정이, 임의 수치를 계산해 하드코딩하는 것보다 안전하고 일관성 있다.
- **근거**: `2:2052`(목록 프레임)만 `layoutSizingVertical: FIXED`, 나머지 4개 형제 프레임(`32:229`/`2:2054`/`2:2055`/`2:2056`)은 모두 `HUG` — `HUG`로 전환해 598→638px로 자동 확장, 재스크린샷으로 클리핑 해소 확인 (skeptic verifier CONFIRM — Figma에 국한되지 않는, "회귀 수정 시 기존 컨벤션 우선" 원칙은 코드베이스 전반에 일반화 가능).

### 113. 디자인 파일이 시스템을 준수해도 코드 프로토타입은 완전히 별개 테마로 드리프트할 수 있다 (2026-07-15)
<!-- tier: tactical -->

- **상황**: HTML 프로토타입과 페어링된 Figma 파일을 동시에 NDS 규칙으로 병렬 감사하는 단계.
- **발견**: Figma 파일은 대체로 NDS를 따르되 구체적 버그들(디스클레이머 배경 위반, CTA 버튼 폰트/사이즈 불일치, 그린/그레이 hex 3종 혼용, 아이콘 오버플로우 등)만 있었던 반면, HTML 프로토타입은 NDS 토큰을 단 하나도 쓰지 않는 완전히 별개의 "cream/jade/rust" 독자 테마(시스템 폰트, 고정 375px 프레임)를 쓰고 있었다 — 두 산출물이 같은 기능을 나타냄에도 준수 수준이 완전히 갈렸다.
- **교훈**: 디자인 소스와 그 코드 구현을 함께 감사할 때, 디자인 파일이 시스템을 잘 지킨다고 해서 코드 쪽도 그럴 것이라 가정하지 않는다. 둘은 서로 다른 시점에, 서로 다른 세션에서 만들어졌을 수 있으므로 항상 독립적으로 병렬 감사한다.
- **근거**: HTML 감사 에이전트 보고 — "None of these hex values match the NDS reference palette at all... a bespoke 'paper/jade/rust' editorial theme... zero relationship to NDS Core tokens" vs. Figma 감사 에이전트 보고 — CTA 그린 컬러는 정확히 일치, 다만 소수의 구체적 버그만 존재 (skeptic verifier 대상 아님 — tactical 등급으로 사전 분류, 이 프로젝트/유사 페어드 워크플로우 계열에 재사용 가능).
- **추가 (2026-07-17)**: 같은 패턴이 신뢰 방향을 반대로 뒤집어 재확인됐다 — NDS "본인정보 사실조회" 빌드에서 소스 HTML 프로토타입은 임시 블루(#1171D2)를 쓰고 있었지만, 에이전트는 이를 구조/콘텐츠의 소스 오브 트루스로만 삼고 색상은 NDS 브랜드 그린을 따르도록 명시적으로 분리했다("treating HTML as structural/content source of truth, not color source of truth"). 즉 "코드 프로토타입은 디자인 시스템과 별개 테마로 드리프트할 수 있다"는 원 교훈에서 한 걸음 더 나아가, **속성별로(구조 vs 색상) 어느 쪽이 진실인지 사전에 각각 결정**해야 한다는 것이 이번 사례의 추가 교훈이다.

### 116. Figma 커버리지는 파일의 목차나 get_metadata가 아니라 figma.root.children으로만 인증한다 (2026-07-16)
<!-- tier: tactical -->

- **상황**: NDS_UX Guide 등 다수 페이지 Figma 파일을 전수 학습하고 "N/N 완료"를 선언하는 중.
- **발견**: 앞서 낸 "17/17 complete"가 실제로는 **17/18**이었다 — 커버리지를 파일 자체의 목차(TOC)로 인증했는데, 그 TOC가 다른 모든 페이지가 의존하는 `- Principles` 페이지를 조용히 누락하고 있었다(수작업 유지되는 문서라 드리프트함). 또한 nodeId 없는 `get_metadata`는 28페이지 파일에서 **1페이지**만 보고한다(데스크톱 세션에 로드된 페이지만 반환). 유사 함정: `p.children.length`는 현재 페이지가 아닌 곳에서 신뢰 불가(6페이지 중 5페이지가 거짓으로 0 보고), 레이어 이름은 파일이 아니라 **페이지 단위로** 신뢰도가 갈린다.
- **교훈**: 커버리지/완전성 주장은 `use_figma` → `figma.root.children`이라는 단일 분모로만 인증한다. 더 일반적으로 — **"목록을 반환하는 편한 API"가 세션 상태에 의존해 조용히 부분 답을 주는지** 의심하고, 권위 있는 열거 경로를 하나 정해 문서화한다. 값 불일치를 "충돌"로 단정하기 전에 그 파일이 참조 라이브러리를 실제로 구독하는지(`get_libraries`) 먼저 확인한다 — 구독하지 않는 파일의 키는 충돌이 아니라 문서 사본이다(이 확인으로 Core 오염을 2회 방지).
- **근거**: `get_metadata`(nodeId 없음) → 1페이지 vs `figma.root.children` → 28페이지. TOC 17개 vs 실제 콘텐츠 18페이지. 5개 에이전트가 "key가 Core와 다르다"고 보고했으나 `get_libraries`로 NDS_M.web이 NDS_Library를 구독하지 않음이 드러나 오탐으로 판명. (skeptic verifier DOWNGRADE — "특정 MCP 버전의 툴 현재 동작이므로 principle 아님; 향후 릴리스에서 `get_metadata`가 전체 목록을 반환하면 이 워크어라운드는 죽은 조언이 된다".)
- **추가 (2026-07-16)**: `get_metadata`의 부분-응답은 nodeId 없는 호출만의 문제가 아니다 — **nodeId를 주고 호출해도 자식이 `GROUP`이면 그 서브트리를 통째로 누락하고 부모를 self-closing으로 직렬화한다.** 한 페이지에서 **populated 프레임 241개 중 105개가 빈 것으로 보고**됐고, 그 페이지의 코드→기관 매핑 전체가 GROUP 자식에 살고 있어 metadata 읽기로는 100% 안 보였다. 카운트도 오염된다(자산 2,941 vs 실제 2,948, 최악의 이름 충돌 6건이 통째로 비가시). **⇒ `get_metadata`는 내비게이션/TEXT 전용. `.length`는 반드시 `findAllWithCriteria`로. "비어 있음"은 Plugin API(`setCurrentPageAsync` 후 `children.length`)로 재확인하기 전까지 증거가 아니다.** 이 세션에서 5개 페이지를 metadata-empty 근거로 스킵했고 전부 재확인 결과 실제로 비어 있었다 — **커버리지는 지켜졌지만 방법이 아니라 운 덕분이었다.**

### 120. Figma `get_metadata`는 depth 제한이 없다 — 큰 서브트리는 하드 에러, 얕은 열거는 `use_figma`로만 가능 (2026-07-17)
<!-- tier: principle -->

- **상황**: Figma 페이지의 자식 노드를 저비용으로 먼저 파악하려고 `get_metadata`를 노드 최상위에 바로 호출.
- **발견**: `get_metadata`는 depth/limit 파라미터가 아예 없고 노드의 서브트리 전체를 재귀 직렬화한다 — 서브트리가 대략 500K~1M자를 넘으면 툴 출력 토큰 한도를 넘겨 **무조건 하드 에러**로 실패한다. 이 실패는 여러 개의 서로 다른 Figma 파일에서 반복 재현됐고, 툴 스키마 자체에도 depth 파라미터가 없어 구조적으로 우회 불가함이 확인됐다. 메타데이터만으로는 큰 페이지의 직계 자식 ID를 저비용으로 알아낼 방법이 없다 — 유일한 경로는 `use_figma`로 `page.children`/`figma.root.children`을 얕게 열거한 뒤, 필요한 서브트리에만 `get_metadata`를 거는 것.
- **교훈**: 큰 Figma 페이지를 다룰 때는 `get_metadata`를 최상위 노드에 바로 쓰지 말고, 먼저 `use_figma`로 자식만 얕게 열거해 크기를 가늠한 다음 필요한 서브트리만 `get_metadata`/`get_screenshot`으로 조회한다.
- **근거**: 여러 파일에서 "exceeds tool output token cap" 하드 에러 재현(500K~1M자 초과 서브트리), `use_figma`의 `page.children`/`figma.root.children`만이 실제로 동작한 우회 경로였음. (skeptic verifier CONFIRMED — 재현된 패턴 + 툴 스키마의 구조적 결함이 근거로 확인됨.)

### 131. 라이브 참조 없는 화면/유형은 발명하지 않고 스코프 제외 또는 reference-weak로 명시 플래그한다 (2026-07-17)
<!-- tier: principle -->

- **상황**: 같은 세션에서 진행된 두 독립 Figma 제안서 빌드(NDS 모바일 앱 버전 / web-proposal 데스크톱 웹 버전) 모두, 대상 기능(통신사기 본인정보 공유여부 사실조회)의 일부 화면 유형에 대해 매칭되는 기존 참조 라이브러리·라이브 캡처가 없었다.
- **발견**: 두 빌드 에이전트 모두 참조 공백을 감추지 않고 서로 다른 방식으로 명시했다 — NDS 빌드는 신원확인/고객홈페이지 흐름과 매칭되는 project-kind 소스가 없다는 사실을 빌드 완료 후 "reference-weak build"로 자체 플래그했고, web-proposal 빌드는 소스 아티팩트에 포함돼 있던 내부 백오피스 관리자 화면 2개를 "라이브 참조가 전혀 없는 채로 만들면 없는 디자인 언어를 발명하는 것"이라며 처음부터 빌드 대상에서 제외했다.
- **교훈**: 참조 라이브러리/라이브 캡처가 없는 화면 유형을 만나면, (a) 빌드에 꼭 필요하지 않다면 스코프에서 명시적으로 제외하고 사유를 보고서에 남기거나, (b) 꼭 필요해 빌드를 진행한다면 결과물에 "reference-weak/저신뢰"로 명시 플래그해 후속 리뷰가 검증 강도를 높이도록 유도한다. 조용히 그럴듯하게 채워 넣는 것(silent invention)이 가장 나쁜 선택지다.
- **근거**: NDS 빌드 보고 — "Reference-weak build (no project-kind source matches an identity-verification customer-homepage flow) — fell back to NDS_Templates/Library conventions." / web-proposal 빌드 보고 — "building them would have meant inventing an entire back-office design language with zero live reference... correctly flagged as out-of-scope rather than silently built anyway." (skeptic verifier CONFIRMED — 같은 세션 내 두 독립 에이전트가 서로 다른 화면 세트에서 같은 행동으로 수렴한 것은 특정 도구/버전에 종속되지 않는 디자인-빌드 방법론 일반에 적용 가능한 근거로 인정됨.)

### 132. Figma 빌드 완료 선언 전 라이브 사이트/템플릿 스크린샷 대조 게이트는 육안 검수로 못 잡는 버그를 반복적으로 잡아낸다 (2026-07-17)
<!-- tier: tactical -->

- **상황**: 같은 세션의 두 Figma 제안서 빌드(NDS/web-proposal) 각각이, 빌드 완료 선언 전 필수 품질 게이트로 완성 화면을 라이브 사이트 스크린샷 및 Figma 템플릿 파일과 대조하는 단계를 실행했다.
- **발견**: 두 빌드 모두 이 게이트에서 실제 버그를 잡아 수정했다 — NDS 빌드는 탭행 텍스트 오버플로우·테이블 컬럼 오버플로우·브랜치 화살표 스크립트의 잘못된 노드 참조 3건, web-proposal 빌드는 NEW뱃지-탭라벨 겹침·여러 화면에서 누락된 LNB 서브아이템·우측 레일과 스티키 티커바 누락(실측 좌표로 수정)·Closing 슬라이드의 템플릿 대비 잘못된 배경색 4건을 각각 찾아 고쳤다. 두 경우 모두 스크린샷 대조 이전에는 발견되지 않았던 버그였다.
- **교훈**: Figma 빌드(제안서/화면 흐름 등)를 완료로 선언하기 전에는 항상 (1) 완성 화면 vs 라이브 사이트/원본 스크린샷, (2) 완성 산출물 vs 참조 템플릿 파일이라는 두 축의 스크린샷 대조 게이트를 실행한다. 오버플로우, 컴포넌트 누락, 잘못된 노드 참조, 색상 불일치 같은 결함은 빌드 로그나 코드 리뷰가 아니라 육안 스크린샷 비교에서만 드러나는 경우가 많다.
- **근거**: NDS 빌드 보고 — "screenshotted every screen... fixed two real bugs found this way — a tab-row text overflow and a table-column overflow, plus a wrong-node reference." / web-proposal 빌드 보고 — "This caught real bugs I fixed: NEW badge overlapping the 5th tab label, LNB sub-items stripped from screens 2–4, and missing right rail + ticker... my Closing was white, template's is #12233D navy."

### 143. Figma 노드의 `.x`/`.y`는 절대좌표가 아니라 부모 프레임 기준 상대좌표다 (2026-07-18)
<!-- tier: principle -->

- **상황**: nhdesign3 PPT 빌드에서 실측 target-element 좌표로 재계산한 9개 numbered callout badge를 각 배지 노드의 `.x`/`.y`에 대입해 재배치하는 중.
- **발견**: 계산해 둔 좌표는 페이지 기준 절대좌표였는데, 배지 노드의 실제 부모가 페이지가 아니라 Slide 프레임이었다. 그 절대좌표를 그대로 `node.x`/`node.y`에 대입하자 Figma가 이를 **부모(Slide) 기준 로컬좌표**로 해석해, Slide 자신의 페이지-오프셋만큼 조용히 이중으로 밀려나갔다 — 배지가 엉뚱한 슬라이드의 좌표 범위로 사라지는 형태로 나타났다. `SceneNode.x`/`.y`가 부모 좌표계 기준이라는 것은 Figma Plugin API 타입 정의에 명시된 안정적 플랫폼 동작이며 API 버전에 걸쳐 바뀌지 않는다.
- **교훈**: Figma Plugin API로 노드 위치를 절대(페이지) 좌표 기준으로 계산했다면, 대입 직전에 반드시 `localX = absX - node.parent.absoluteBoundingBox.x`(y도 동일)로 부모-로컬 좌표로 변환한다. 노드를 읽을 때(`absoluteBoundingBox`)는 항상 절대좌표라 안전하지만, 쓸 때(`node.x =`)는 부모 기준이라는 이 비대칭성 때문에 발생하는 함정이며, 대상 노드의 부모가 페이지인지 프레임/그룹/Slide인지부터 먼저 확인해야 한다.
- **근거**: "assigning an absolute page coordinate directly to a Figma node's `.x`/`.y` when that node's parent is NOT the page (e.g. a Slide frame) silently double-offsets it, because node.x is interpreted as parent-local, not absolute — this caused badges to briefly vanish off-slide." (skeptic verifier CONFIRMED — `SceneNode.x`/`.y`가 부모-상대 좌표라는 것은 문서화된 안정적 Plugin API 동작이며 특정 버전/설정에 종속되지 않는다고 판단.)
