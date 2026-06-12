---
description: "경험 지식 저장소 - 도메인별 학습 조회/실행/버전업 (/cs-experiencing [test|plan|review|update|version-up|status])"
allowed-tools: Bash, Read, Write, Edit, Glob, Grep, Agent, AskUserQuestion
---

# /cs-experiencing [subcommand] [args]

누적된 경험 지식을 도메인별로 관리하고 실행합니다.

## 서브커맨드

| 커맨드 | 설명 |
|--------|------|
| `/cs-experiencing` | 도메인 목록 + 버전 현황 |
| `/cs-experiencing test [URL]` | CS-test 실행 (멀티 에이전트 웹 테스트) |
| `/cs-experiencing plan [task]` | CS-plan 실행 |
| `/cs-experiencing review [path] [--focus aspect]` | CS-codebase-review 실행 (5-관점 코드 리뷰) |
| `/cs-experiencing update` | **모든 도메인 버전업** (= version-up all) |
| `/cs-experiencing version-up test` | CS-test 버전 증가 → 새 버전 디렉토리 생성 |
| `/cs-experiencing version-up plan` | CS-plan 버전 증가 |
| `/cs-experiencing version-up review` | CS-codebase-review 버전 증가 |
| `/cs-experiencing version-up design` | cs-design 버전 증가 |
| `/cs-experiencing version-up clarify` | cs-clarify 버전 증가 |
| `/cs-experiencing version-up smart-run` | cs-smart-run VERSION 증가 (디렉토리 버전 suffix 없음) |
| `/cs-experiencing version-up ceo` | cs-ceo 버전 증가 |
| `/cs-experiencing version-up all` | 7개 도메인 한번에 버전 증가 (test→plan→review→design→clarify→smart-run→ceo) |
| `/cs-experiencing status` | 모든 도메인 버전 현황 |
| `/cs-experiencing btw [idea]` | **[v4 신규]** 세션 중 개선 아이디어 즉시 캡처 |
| `/cs-experiencing checkpoint` | **[v4 신규]** WIP 체크포인트 커밋 생성 |

## 도메인 현황

버전은 디렉토리명이 단일 진실 — `ls -d "$BASE/<도메인>-v"* | sort -V | tail -1`로 항상 최신을 해석한다.

| 도메인 | 버전 | 내용 |
|--------|------|------|
| CS-test | CS-test-v* (latest via sort -V) | playwright 멀티 에이전트 웹 테스트 팀 (에이전트 구성·개수의 단일 진실은 `$LATEST_TEST/commands/CS-test.md` 로스터) |
| CS-plan | CS-plan-v* (latest via sort -V) | TDD+CleanArch 4-agent 플랜 |
| CS-codebase-review | CS-codebase-review-v* (latest via sort -V) | 5-관점 병렬 코드 리뷰 (Architecture/Quality/Security/Performance/Maintainability) |
| cs-design | cs-design-v* (latest via sort -V) | 디자인 리뷰/UI 감사 |
| cs-clarify | cs-clarify-v* (latest via sort -V) | 요구사항 명확화 |
| cs-smart-run | cs-smart-run (단일 디렉토리, VERSION 파일로 버전 관리) | Opus 플랜 + 병렬 Sonnet 실행 |
| cs-ceo | cs-ceo-v* (latest via sort -V) | 목표 설정/멀티스텝 오케스트레이션 |

## 실행 흐름

`skills/experiencing/SKILL.md` 참고
