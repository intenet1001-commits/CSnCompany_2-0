# cs-ceo CHANGELOG

## 15.2.0 — 2026-08-15
- AgentsToZ 프로젝트 기억을 임무 분할 전 Phase G.5에서 읽기 전용 recall한다.
- 최대 2개 active constraints + 목표 관련 항목으로 총 5개 이하의 two-budget 컨텍스트를 사용한다.
- `memoryId`/`memoryAgent`/`memoryAgentId`를 임무 맥락에 보존하고, 각 하위 임무에는 관련 항목 최대 2개만 전달한다.
- Claude marketplace뿐 아니라 Codex-only versioned cache에서도 `cs-memory` recall helper를 찾는다.
- `cs-ceo` 진입 Skill 자체도 Codex-only versioned cache에서 최신 CEO agent를 실행 가능하게 찾는다.
- 종료 시 `actionablePending`이 있을 때만 같은 CEO 세션에서 `/cs-memory:learn pending`을 1회 처리해 무인 모델 호출 없이 정기 수집→컴팩트 학습 루프를 닫는다.
- 본문 시점과 파일 관측 mtime을 분리하고 contested/오래된 기억은 현재 저장소 증거로 재검증한다.
- 구형 전역 `~/.claude/core-memory` 폴백을 제거했다.

## 15.1.0 — 2026-07-02
- **Mode D (Dynamic Chain)** 신규 — CrewAI/AutoGen/ChatDev 벤치마크 이식
  - 다중 도메인이 순서·의존·조건부 분기·재작업 루프로 얽힐 때 선언적 chain 매니페스트를 walk
  - P1 speaker selection (parallel/round_robin/auto/manual + transition table)
  - P2 termination conditions (max_turns | sentinel | no_delta ... , AND/OR 결합)
  - P3 declarative chain manifest (plugins/shared/chains/)
  - P4 instructor↔assistant 역할극 루프 (composed phase, cycleNum 하드 캡, opt-in 코드 수정)
- Phase 3 라우팅 표 + Phase 4 리포트 템플릿에 Mode D 반영
- 근거: plugins/shared/ORCHESTRATION-PATTERNS.md (P1~P5), plugins/shared/chains/CHAIN-SCHEMA.md
- 정직성: 정적 fan-out(모드 A/B)으로 충분하면 켜지 않음 (Simplicity First)

## 15.0.1
- Dynamic Resolve v2 (파트너 타입 자동 감지), Goal Gate, External Knowledge Gate, Core Memory 연동
