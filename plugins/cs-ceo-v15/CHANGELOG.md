# cs-ceo CHANGELOG

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
