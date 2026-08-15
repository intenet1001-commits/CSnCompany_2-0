# cs-end CHANGELOG

## 3.2.0 — 2026-08-15

- Phase 1.5의 구형 전역 core-memory writer를 제거했다.
- 프로젝트에 `.agent-memory/config.json`이 있으면 AgentsToZ가 설치한 로컬 `remember-session` 어댑터에 저장을 한 번만 위임한다.
- 기억 저장 뒤 cs-memory collector가 새 entry-version 포인터만 무토큰으로 수집하며 원본 기억은 수정하지 않는다.
- 어댑터가 없거나 수집이 실패해도 직접 폴백 저장하지 않고 명시적인 비블로킹 경고를 남긴다.

## 3.1.1

- Session Digest, Learning Gate, error note capture, selective versioning, compact handoff를 운영했다.
