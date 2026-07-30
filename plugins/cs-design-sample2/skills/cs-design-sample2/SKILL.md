---
name: cs-design-sample2
user-invocable: true
description: |
  다크 에디토리얼×터미널 디자인 가이드 스킬 (near-black #05070d + cyan #67E8F9 액센트).
  신용평가모델 강의 아카이브 홈페이지(랜딩 + 상세 3탭)에 적용된 디자인 시스템을 공식화한 레퍼런스.

  Use when user types:
  - "/cs-design-sample2"
  - "디자인 가이드 보여줘"
  - "다크 에디토리얼 스타일 적용"
  - "--audit [file]" to check a file
  - "--apply [file]" to apply the design
version: 1.0.0
allowed-tools:
  - Read
  - Edit
  - Glob
  - Grep
  - Write
---

# cs-design-sample2 — Dark Editorial / Terminal Design Guide

이 세션에서 확립된 디자인 언어를 캡처한 재사용 가능한 레퍼런스 스킬.

**참조 파일**: `knowledge/design-guide.md` (이 스킬과 같은 플러그인 내)

---

## Usage

```bash
/cs-design-sample2                        # 디자인 가이드 전체 출력
/cs-design-sample2 --audit [file]         # 파일이 가이드를 따르는지 검사
/cs-design-sample2 --apply [file]         # 파일에 디자인 가이드 적용
```

---

## Protocol

### Mode 1: 가이드 출력 (args 없음)

1. `knowledge/design-guide.md`를 Read
2. 전체 디자인 가이드를 사용자에게 출력
3. 주요 섹션: 색상 시스템, 컴포넌트 패턴, 타이포그래피, 간격, 안티패턴

### Mode 2: `--audit [file]`

**목적**: 지정된 파일이 이 디자인 가이드를 따르는지 검사하고 위반 사항 리포트

**실행 절차**:

1. `knowledge/design-guide.md`를 Read (가이드 로드 — 검사 기준의 단일 소스)
2. 지정된 `[file]`을 Read
3. 가이드에서 검사 규칙을 추출:
   - **섹션 5 (안티패턴)**: 모든 ❌ 항목을 필수 검사 규칙으로 변환 (예: 순수 `#000` 배경 발견 → 위반)
   - **섹션 1 (색상)**: 표의 모든 용도→값 매핑. 해당 용도의 요소가 파일에 있는데 다른 색을 쓰면 위반 (예: 링크 색이 `var(--ac)` cyan이 아님)
   - **섹션 3 (타이포그래피) / 섹션 4 (간격)**: 해당 역할의 요소가 존재할 때 정의된 폰트/스펙과 다르면 위반 (예: 헤딩에 SERIF 900 미사용, mono 라벨에 letter-spacing 누락)
   - **섹션 2 (컴포넌트 패턴)**: 참고용 — 해당 컴포넌트가 존재할 때만 구조 비교, 없으면 N/A로 표기 (위반 아님)
4. 각 위반에 대해: 위치(라인/스니펫), 위반한 가이드 규칙(섹션 번호), 수정 값 제안을 리포트. 검사한 규칙 수를 분모로 준수율 계산:
   ```
   ✅ 통과: [항목 목록]
   ⚠️ 위반: [항목 + 위치 + 위반 가이드 규칙(섹션 번호) + 수정 제안]
   📊 준수율: X/Y 항목 (XX%)
   ```

### Mode 3: `--apply [file]`

**목적**: 지정된 파일에 이 디자인 가이드를 자동 적용

**실행 절차**:

1. `knowledge/design-guide.md`를 Read (가이드 로드 — 치환 기준의 단일 소스)
2. 지정된 `[file]`을 Read
3. `--audit` 방식으로 위반 항목 파악
4. `--audit`에서 발견된 각 위반에 대해, 가이드가 정의한 올바른 값으로의 치환 계획 수립 (old value → guide value). 안티패턴 섹션(섹션 5)의 → 화살표가 1차 치환 소스이고, 색상/타이포/간격 표(섹션 1·3·4)의 정의 값이 2차 소스
5. 수정 사항을 Edit 도구로 적용 (각 변경마다 정확한 old/new string 사용)
   - 같은 값 문자열이 파일에 여러 번 나타나면 `replace_all: true`를 사용하거나 occurrence별로 개별 확인 (부분 적용이 가장 흔한 실패 원인)
6. **적용 검증 (필수)**: 수정된 `[file]`을 다시 Read하고 Mode 2의 `--audit` 검사를 전부 재실행
   - 위반이 남아 있으면 (Edit가 첫 번째 occurrence만 바꿨거나, 누락된 항목이 있는 경우) 해당 항목을 수정하고 다시 검증
   - 최대 3회 반복. 한 라운드가 델타(새 수정/새 통과)를 만들지 못하면 즉시 중단. 3회 후에도 위반이 남으면 실패로 보고
7. 최종 재검사 결과를 기준으로 요약 출력 (모델의 기억이 아닌, 재검사에서 실제 측정된 수치 사용):
   ```
   ✅ 적용 완료: X개 항목 수정 (재검사 통과 Y/Z 항목)
   📝 변경 내역: [목록]
   ⚠️ 미해결 위반: [있을 경우 항목 + 위치, 없으면 생략]
   ```

---

## 디자인 언어 요약

> 아래 표는 빠른 참조용 요약이다. 검사 기준은 `knowledge/design-guide.md`가 단일 소스.

| 요소 | 값 |
|------|-----|
| 배경 | `#05070d` near-black navy |
| Primary accent | `var(--ac, #67E8F9)` cyan |
| 텍스트 | `#e6eaf2` (foreground) / `#8B94A6` (secondary) / `#5B6577` (label) |
| 폰트 | `IBM Plex Mono`(라벨) / `IBM Plex Sans KR`(본문) / `Noto Serif KR 900`(헤딩) |
| 카드 스타일 | `rgba(255,255,255,.08)` 보더 + `rounded-16px` + 미세 그라디언트 |
| 버튼 | 고스트 필(`border-radius:999px`, 투명 배경, hover 시 accent) |
| 배경 장식 | 그리드 오버레이 + 드리프팅 글로우 오브 |
| 진입 애니메이션 | `fadeUp` / `lineUp` stagger |

---

## 참조 디자인

- 대학원 신용평가모델 강의 아카이브 홈페이지 (`class/` Next.js 프로젝트)
- 적용 페이지: `src/app/page.tsx`(랜딩), `src/components/WeekDetail.tsx`(상세 3탭)
