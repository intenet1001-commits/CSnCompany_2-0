
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
