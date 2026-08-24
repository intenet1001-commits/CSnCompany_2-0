---
description: "CS 전 단계 SDLC 파이프라인 — 한 문장 요청을 CLARIFY→PLAN→IMPLEMENT→REVIEW→TEST→SHIP으로 배달. 아티팩트 게이트 + 경계 있는 cross-phase 리워크 + 세션 사망 재개(--from) + 인간 체크포인트. (/cs-company [요청])"
allowed-tools: Task, Skill, Bash, Read, Write, AskUserQuestion
---

# /cs-company [요청]

한 문장을 넣으면 CS 팀 전체가 순서대로 일한다: CLARIFY(PM) → PLAN(Architect) → IMPLEMENT(Team Lead) → REVIEW(Reviewer) → TEST(QA) → SHIP(DevOps). 각 단계는 독립 플러그인 그대로이며, conductor는 게이트·순서·상태만 소유한다 (plugins/shared/PIPELINE-PROTOCOL.md).

## 사용법

```
/cs-company 결제 기능 만들어서 배포 준비까지 해줘
/cs-company --auto 밤새 이 기능 전체 파이프라인 돌려줘          # 무인 실행 — 중간 체크포인트 0회
/cs-company --skip clarify,test 유틸 캐시 레이어 추가해줘      # 명시 생략
/cs-company --from review                                    # 세션 사망 후 REVIEW부터 재개 (pipeline.json 기반)
/cs-company --checkpoint plan,review,ship 관리자 대시보드 추가  # 체크포인트 지점 변경
```

## 플래그

| 플래그 | 의미 |
|--------|------|
| `--auto` | `--hitl=auto` 별칭 — 중간 체크포인트 0회, 모든 질문에서 default 채택 (plugins/shared/HITL-POLICY.md [1]) |
| `--hitl [auto\|gate\|always]` | HITL 모드 (미지정 시 `gate`). phase 리드 스폰 시 동일 값 전파 |
| `--skip <phase,...>` | 지정 phase 생략 (pipeline.json에 skipped + 사유 기록). SHIP은 이 플래그로만 생략 가능 |
| `--from <phase>` | `.cs-artifacts/pipeline.json`을 읽어 passed phase는 건너뛰고 지정 phase부터 재개 |
| `--checkpoint <phase,...>` | AskUserQuestion 체크포인트 지점 (기본: `plan,ship`) |

phase 이름: `clarify` `plan` `implement` `review` `test` `ship` (대소문자 무관).

## 실행 방식

```bash
BASE="$HOME/.claude/plugins/marketplaces/CSnCompany_2-0/plugins"
LATEST_CEO=$(ls -d "$BASE/cs-ceo-v"* 2>/dev/null | sort -V | tail -1)
```

conductor 스킬 파일: `$LATEST_CEO/skills/cs-company/SKILL.md`

이 SKILL은 **main context에서 직접 실행**한다 (서브에이전트 스폰 금지) — 체크포인트의 AskUserQuestion과 phase 리드들의 CHECKPOINT payload 버블링(HITL-POLICY [3])이 여기서 종결되어야 하기 때문이다. 플래그 파싱 결과(`HITL` / `SKIP` / `FROM` / `CHECKPOINT`)를 SKILL 프로토콜의 P0 입력으로 전달한다.
