---
description: "CS 작업 시작 — 대상 프로젝트에 격리된 git worktree + 브랜치를 생성하고 매니페스트에 기록해 cs-end --merge-worktree가 나중에 찾아 머지할 수 있게 한다 (/cs-start)"
allowed-tools: Bash, Read, Write, Edit, AskUserQuestion
---

# /cs-start — CS Worktree Launcher

특정 프로젝트에서 작업을 시작할 때, 프로젝트 저장소를 직접 건드리지 않고
**격리된 git worktree + 브랜치**를 만들어 그 안에서 작업하게 한다.
생성 사실을 전역 매니페스트에 기록하므로, 나중에 `/cs-end --merge-worktree`가
그 워크트리를 찾아 base 브랜치로 머지(또는 PR)할 수 있다.

`/cs-end`와 대칭을 이루는 **시작(start) 명령**이다.

> **비파괴 원칙:** 이 명령은 새 워크트리/브랜치를 **추가**하기만 한다.
> 기존 브랜치를 삭제하거나 force-push 하지 않으며, 대상 저장소의 워킹 트리를 리셋하지 않는다.

검증 프로토콜 (BLOCKING 첫 단계): fan-out 전 첫 행동으로 plugins/shared/LOOP-PROTOCOL.md를 Read하고, 리포트 헤더에 `protocol: LOOP-PROTOCOL [a-f] loaded (round budget N)` 한 줄을 출력한다. (런타임 경로: `${CLAUDE_PLUGIN_ROOT}/../shared/`)

## 사용법

```
/cs-start                                 # 현재 디렉토리(cwd)의 git repo 기준 워크트리 생성
/cs-start /path/to/project                # 대상 프로젝트 경로 명시
/cs-start /path/to/project --base develop # base 브랜치 지정 (기본: repo 기본 브랜치)
/cs-start /path/to/project --name hotfix  # 브랜치/워크트리 슬러그 커스텀
/cs-start --list                          # 활성 cs-worktree 목록만 출력하고 종료
```

## 인자 규약

| 인자 | 의미 | 기본값 |
|------|------|--------|
| `[path]` (positional) | 대상 프로젝트 git repo 경로 | 현재 디렉토리(`$PWD`) |
| `--base <branch>` | 워크트리가 분기할 base 브랜치 | repo 기본 브랜치 (아래 감지 로직) |
| `--name <slug>` | 브랜치/워크트리 슬러그의 사람이 읽는 부분 | `cs`(고정 접두사만 사용) |
| `--list` | 매니페스트의 active 워크트리만 출력하고 종료 | — |

## 네이밍 규칙 (결정적)

- **슬러그**: `<name-part>-<YYYYMMDD-HHMMSS>`
  - `name-part`는 `--name` 값(있으면) 또는 프로젝트 디렉토리명을 소문자·영숫자·하이픈으로 정규화한 값.
  - 타임스탬프로 충돌을 방지한다 (같은 프로젝트에서 여러 워크트리 허용).
- **브랜치 이름**: `cs-work/<슬러그>`
- **워크트리 경로**: `<project>/.cs-worktrees/<슬러그>/`
  - 프로젝트 저장소 안의 `.cs-worktrees/` 하위. 사용자에게 `.gitignore`에 `.cs-worktrees/` 추가를 권장한다.

## 매니페스트 (cs-end 연동의 핵심)

전역 매니페스트 파일에 생성 사실을 기록한다:

```
~/.claude/state/cs-worktree/manifest.json
```

스키마:

```json
{
  "worktrees": [
    {
      "id": "myproject-20260702-153000",
      "project": "/abs/path/to/project",
      "project_name": "myproject",
      "branch": "cs-work/myproject-20260702-153000",
      "worktree_path": "/abs/path/to/project/.cs-worktrees/myproject-20260702-153000",
      "base_branch": "main",
      "created_at": "2026-07-02T15:30:00",
      "status": "active"
    }
  ]
}
```

- `status`는 `active` → (cs-end 머지 성공 시) `merged` → 또는 `abandoned`.
- cs-end는 이 파일에서 `project`가 대상 프로젝트와 일치하고 `status == "active"`인 항목을 찾는다.

## 실행 순서

### Phase 0 — 인자 파싱 + 대상 저장소 검증

```bash
STATE_DIR="$HOME/.claude/state/cs-worktree"
MANIFEST="$STATE_DIR/manifest.json"
mkdir -p "$STATE_DIR"
[ -f "$MANIFEST" ] || echo '{"worktrees": []}' > "$MANIFEST"
```

`--list` 플래그가 있으면 매니페스트의 `active` 항목을 표로 출력하고 즉시 종료한다.

대상 프로젝트 경로(`$TARGET`)를 확정한다 (positional 인자 또는 `$PWD`). 검증:

```bash
# 1) git 저장소인지 확인 (아니면 중단)
git -C "$TARGET" rev-parse --is-inside-work-tree >/dev/null 2>&1 || {
  echo "❌ '$TARGET' 는 git 저장소가 아닙니다. /cs-start 중단."
  exit 1
}
# 2) 저장소 루트로 정규화
TARGET=$(git -C "$TARGET" rev-parse --show-toplevel)
PROJECT_NAME=$(basename "$TARGET")
```

**base 브랜치 감지** (`--base` 미지정 시):

```bash
# origin/HEAD 가 가리키는 기본 브랜치 → 없으면 main → master 순
BASE=$(git -C "$TARGET" symbolic-ref --quiet refs/remotes/origin/HEAD 2>/dev/null | sed 's@^refs/remotes/origin/@@')
[ -z "$BASE" ] && git -C "$TARGET" show-ref --verify --quiet refs/heads/main && BASE=main
[ -z "$BASE" ] && git -C "$TARGET" show-ref --verify --quiet refs/heads/master && BASE=master
[ -z "$BASE" ] && BASE=$(git -C "$TARGET" rev-parse --abbrev-ref HEAD)
```

### Phase 1 — 슬러그·경로 계산 (결정적)

```bash
TS=$(date +%Y%m%d-%H%M%S)
NAME_PART="${CUSTOM_NAME:-$PROJECT_NAME}"
# 소문자·영숫자·하이픈만 남기고 정규화
SLUG=$(printf '%s' "$NAME_PART" | tr '[:upper:]' '[:lower:]' | tr -cs 'a-z0-9' '-' | sed 's/^-//;s/-$//')-"$TS"
BRANCH="cs-work/$SLUG"
WT_PATH="$TARGET/.cs-worktrees/$SLUG"
```

브랜치가 이미 존재하면 (타임스탬프 충돌은 사실상 없지만 방어적으로) 중단하고 안내한다.

### Phase 2 — 워크트리 생성 (git worktree add)

```bash
mkdir -p "$TARGET/.cs-worktrees"
git -C "$TARGET" worktree add -b "$BRANCH" "$WT_PATH" "$BASE"
```

- 실패 시 (예: `.cs-worktrees` 가 더러운 상태, base 브랜치 없음) → 오류 원문을 출력하고 매니페스트에 기록하지 않은 채 중단한다.
- 성공 시 `.gitignore` 에 `.cs-worktrees/` 가 없으면 추가를 **권장하는 한 줄**만 출력한다 (자동 편집하지 않음 — 사용자 저장소 파일을 임의로 바꾸지 않는다).

### Phase 3 — 매니페스트 기록

Phase 2 성공 시에만 매니페스트에 새 항목을 append 한다 (inline python3):

```bash
python3 - "$MANIFEST" "$SLUG" "$TARGET" "$PROJECT_NAME" "$BRANCH" "$WT_PATH" "$BASE" <<'PY'
import json, sys, datetime
manifest, slug, project, pname, branch, wt, base = sys.argv[1:8]
d = json.load(open(manifest))
d.setdefault("worktrees", []).append({
    "id": slug,
    "project": project,
    "project_name": pname,
    "branch": branch,
    "worktree_path": wt,
    "base_branch": base,
    "created_at": datetime.datetime.now().isoformat(timespec="seconds"),
    "status": "active",
})
json.dump(d, open(manifest, "w"), ensure_ascii=False, indent=2)
print("manifest updated:", slug)
PY
```

### Phase 4 — 완료 리포트

출력에 반드시 포함 (포맷 자유):

1. 생성된 **브랜치명**, **워크트리 경로**, **base 브랜치**
2. 이제 그 워크트리 경로에서 작업하면 된다는 안내 (예: `cd <worktree_path>`)
3. 작업이 끝나면 `/cs-end --merge-worktree`(선택적으로 `--validate`)로 머지할 수 있다는 안내
4. `.cs-worktrees/` 를 `.gitignore` 에 추가 권장 (아직 없을 때만)
5. 매니페스트 위치(`~/.claude/state/cs-worktree/manifest.json`)

## 안전 규칙 (요약)

- git 저장소가 아니면 중단. 워크트리 생성 실패 시 매니페스트를 오염시키지 않는다.
- 기존 브랜치 삭제/force-push/워킹트리 리셋 등 파괴적 동작 없음.
- 대상 저장소 파일(`.gitignore` 포함)을 자동 편집하지 않는다 — 권장만 한다.
- 실제 머지·정리는 `/cs-end --merge-worktree` 가 담당한다 (이 명령은 생성·기록만).
