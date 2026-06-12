#!/usr/bin/env python3
"""
CSnCompany: abspath_check.py — 노하우 #15 자동화
코드베이스에서 하드코딩된 절대경로(특히 /Users/<name>/...)를 탐지하여 JSON으로 출력.
크로스 디바이스 빌드 실패의 근본 원인을 결정론적으로 탐지.

Usage: python3 abspath_check.py <project_root>
"""

import sys
import re
import json
from pathlib import Path

SKIP_DIRS = {'.git', 'node_modules', '.next', 'dist', 'build', 'target',
             '__pycache__', 'cargo-targets', '.bkit', '.omc', 'shared'}

# 하드코딩 절대경로 패턴
ABSPATH_PATTERNS = [
    # macOS/Linux 유저 홈
    (re.compile(r'/Users/([^/\s"\']+)/[^\s"\']*'), 'hardcoded_home_macos'),
    (re.compile(r'/home/([^/\s"\']+)/[^\s"\']*'), 'hardcoded_home_linux'),
    # Windows 경로
    (re.compile(r'[Cc]:\\[Uu]sers\\([^\\]+)\\[^\s"\']*'), 'hardcoded_home_windows'),
    # /tmp, /var 절대경로 (설정 파일에서)
    (re.compile(r'"(/(?:tmp|var|opt|usr)/[^"]+)"'), 'hardcoded_system_path'),
]

# 검사 대상 파일 확장자
TARGET_EXTS = {
    '.toml', '.yaml', '.yml', '.json', '.env',
    '.sh', '.bash', '.zsh',
    '.cmake', '', '.mk', '.makefile',
    '.ts', '.js', '.py', '.rs', '.go',
    '.md'
}
TARGET_NAMES = {'Makefile', 'makefile', 'CMakeLists.txt', 'Dockerfile', 'docker-compose.yml'}

# 무시할 패턴 (false positive 방지)
IGNORE_PATTERNS = [
    re.compile(r'^\s*#'),        # 전체 라인 주석만 스킵 (라인 중간 '#'는 스킵하지 않음)
    re.compile(r'https?://'),    # URL
    re.compile(r'example\.com'), # 예시 URL
]
# 라인 중간 주석은 주석 부분만 잘라내고 코드 부분은 검사한다
INLINE_COMMENT = re.compile(r'\s#\s.*$')


def should_ignore(line: str) -> bool:
    for pat in IGNORE_PATTERNS:
        if pat.search(line):
            return True
    return False


def check_file(path: Path, root: Path) -> list:
    hits = []
    try:
        text = path.read_text(encoding='utf-8', errors='ignore')
        for lineno, line in enumerate(text.splitlines(), 1):
            if should_ignore(line.strip()):
                continue
            scan_line = INLINE_COMMENT.sub('', line)
            for pattern, ptype in ABSPATH_PATTERNS:
                for match in pattern.finditer(scan_line):
                    safe_match = match.group(0)[:80].replace('\\', '/').replace('"', "'")
                    hits.append({
                        'file': str(path.relative_to(root)),
                        'line': lineno,
                        'match': safe_match,
                        'type': ptype,
                        'severity': 'HIGH' if 'home' in ptype else 'MEDIUM',
                        'fix': '환경변수($HOME, $CARGO_TARGET_DIR 등)로 대체 권장'
                    })
    except Exception:
        pass
    return hits


def scan(root: Path) -> list:
    hits = []
    for path in root.rglob('*'):
        if any(p in SKIP_DIRS for p in path.parts):
            continue
        if not path.is_file():
            continue
        if path.name in TARGET_NAMES or path.suffix.lower() in TARGET_EXTS:
            hits.extend(check_file(path, root))
    return hits


def main():
    if len(sys.argv) < 2:
        print(json.dumps({'error': 'Usage: abspath_check.py <project_root>'}))
        sys.exit(1)

    root = Path(sys.argv[1]).expanduser().resolve()
    if not root.exists():
        print(json.dumps({'error': f'Path not found: {root}'}))
        sys.exit(1)

    hits = scan(root)

    output = {
        'total_hits': len(hits),
        'high_risk': sum(1 for h in hits if h['severity'] == 'HIGH'),
        'medium_risk': sum(1 for h in hits if h['severity'] == 'MEDIUM'),
        'hits': hits[:50],  # 상위 50개만 (LLM 컨텍스트 보호)
        'summary': f"절대경로 {len(hits)}개 발견 (HIGH:{sum(1 for h in hits if h['severity']=='HIGH')}, MEDIUM:{sum(1 for h in hits if h['severity']=='MEDIUM')})"
    }
    print(json.dumps(output, ensure_ascii=False, indent=None))


if __name__ == '__main__':
    main()
