# CSnCompany 공식 플러그인 레지스트리

모든 공식 플러그인은 `anthropics/claude-plugins-official` 한 곳에서 설치한다.

마켓플레이스 등록 (최초 1회):
```
/plugin marketplace add anthropics/claude-plugins-official
```

## 플러그인 목록

| 플러그인 | 위치 | 설치 명령어 | 용도 |
|---------|------|-----------|------|
| playwright | `external_plugins/` | `/plugin install playwright@claude-plugins-official` | 브라우저 자동화 (CS-test Phase 1-2) |
| serena | `external_plugins/` | `/plugin install serena@claude-plugins-official` | 코드 인텔리전스 (심볼 탐색, 정의·참조 찾기) |
| hookify | `plugins/` | `/plugin install hookify@claude-plugins-official` | 훅 생성, 동작 차단 (Anthropic 공식) |

## 감지 전략 (`pre_pass.py`)

1. `~/.claude/plugins/marketplaces/claude-plugins-official/{plugins|external_plugins}/{name}/` 디렉토리 존재 여부
2. fallback: `~/.claude/settings.json` `mcpServers` 키에서 name 검색 (수동 MCP 설치 대응)

## 미설치 처리 패턴

각 스킬에서 공식 플러그인이 필요하지만 없을 경우 — context7 Phase -3 패턴과 동일:

```
AskUserQuestion — 선택지: Install (권장) / Skip once / Abort
- Install → 설치 명령어 안내 + (필요 시) 재시작 안내
- Skip → 해당 기능 없이 계속 (결과에 "⚠️ [플러그인] 미설치로 [기능] 생략" 표기)
- Abort → 즉시 종료
```

**주의**: PREFLIGHT 실패 시 게이트를 건너뜀 — 블로킹 금지.
