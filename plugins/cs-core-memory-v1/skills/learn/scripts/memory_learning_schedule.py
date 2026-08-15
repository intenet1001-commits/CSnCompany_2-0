#!/usr/bin/env python3
"""Install a native, model-free periodic project-memory collector."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import plistlib
import shlex
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple


LABEL = "com.csncompany.memory-learning"
SYSTEMD_NAME = "csncompany-memory-learning"
WINDOWS_TASK = "CSnCompany Memory Learning"
MAX_LEARNING_SCRIPT_BYTES = 2 * 1024 * 1024


class ScheduleError(RuntimeError):
    pass


def default_state_path() -> Path:
    return Path.home() / ".csncompany/state/memory-learning.json"


def default_learning_script() -> Path:
    return Path(__file__).resolve().with_name("memory_learning.py")


def stable_learning_script(home: Path) -> Path:
    return home.expanduser().resolve() / ".csncompany/bin/memory_learning.py"


def regular_file_payload(path: Path) -> bytes:
    candidate = path.expanduser()
    if (
        not candidate.is_absolute()
        or not candidate.is_file()
        or candidate.is_symlink()
    ):
        raise ScheduleError("learning script must be an absolute regular file")
    if candidate.stat().st_size > MAX_LEARNING_SCRIPT_BYTES:
        raise ScheduleError("learning script exceeds its bounded size")
    return candidate.read_bytes()


def regular_file_hash(path: Path) -> Optional[str]:
    try:
        return hashlib.sha256(regular_file_payload(path)).hexdigest()
    except (OSError, ScheduleError):
        return None


def resolve_executable(value: Optional[str], name: str) -> Path:
    candidate = Path(value).expanduser() if value else Path(shutil.which(name) or "")
    if not str(candidate) or not candidate.is_absolute() or not candidate.is_file():
        raise ScheduleError("required executable was not found: %s" % name)
    return candidate.resolve()


def build_collect_command(
    uv: Path,
    learning_script: Path,
    state_file: Path,
    scope: str,
    root: Optional[Path],
    home: Path,
) -> List[str]:
    if scope not in {"registry", "pc", "folder"}:
        raise ScheduleError("scope must be registry, pc, or folder")
    uv_path = uv.expanduser()
    script_path = learning_script.expanduser()
    state_path = state_file.expanduser()
    if not uv_path.is_absolute() or not script_path.is_absolute() or not state_path.is_absolute():
        raise ScheduleError("scheduler paths must be absolute")
    command = [
        str(uv_path.resolve()),
        "run",
        "--quiet",
        "--no-project",
        "python",
        str(script_path.resolve()),
        "collect",
        "--state-file",
        str(state_path),
        "--no-cwd",
        "--quiet",
    ]
    if scope == "pc":
        home_path = home.expanduser()
        if not home_path.is_absolute() or not home_path.is_dir():
            raise ScheduleError("PC discovery home must be an absolute directory")
        command.extend(["--root", str(home_path.resolve()), "--max-depth", "8"])
    elif scope == "folder":
        if root is None or not root.is_absolute():
            raise ScheduleError("folder scope requires an absolute --root")
        folder = root.expanduser()
        if not folder.is_dir():
            raise ScheduleError("folder scope root does not exist")
        command.extend([
            "--root",
            str(folder.resolve()),
            "--max-depth",
            "8",
            "--no-registry",
        ])
    return command


def launchd_plist(command: Sequence[str], interval_hours: int, error_log: Path) -> bytes:
    if not 1 <= interval_hours <= 168:
        raise ScheduleError("interval must be between 1 and 168 hours")
    payload = {
        "Label": LABEL,
        "ProgramArguments": list(command),
        "RunAtLoad": True,
        "StartInterval": interval_hours * 60 * 60,
        "ProcessType": "Background",
        "LowPriorityIO": True,
        "StandardOutPath": str(error_log),
        "StandardErrorPath": str(error_log),
    }
    return plistlib.dumps(payload, fmt=plistlib.FMT_XML, sort_keys=True)


def systemd_units(command: Sequence[str], interval_hours: int) -> Tuple[str, str]:
    if not 1 <= interval_hours <= 168:
        raise ScheduleError("interval must be between 1 and 168 hours")
    # systemd performs percent-specifier expansion even inside quoted arguments.
    quoted = " ".join(shlex.quote(value.replace("%", "%%")) for value in command)
    service = "\n".join([
        "[Unit]",
        "Description=CSnCompany project-memory change collector",
        "",
        "[Service]",
        "Type=oneshot",
        "Environment=UV_CACHE_DIR=%h/.csncompany/uv-cache",
        "ExecStart=%s" % quoted,
        "Nice=10",
        "IOSchedulingClass=idle",
        "",
    ])
    timer = "\n".join([
        "[Unit]",
        "Description=Collect CSnCompany project-memory changes periodically",
        "",
        "[Timer]",
        "OnBootSec=5m",
        "OnUnitActiveSec=%dh" % interval_hours,
        "Persistent=true",
        "RandomizedDelaySec=15m",
        "Unit=%s.service" % SYSTEMD_NAME,
        "",
        "[Install]",
        "WantedBy=timers.target",
        "",
    ])
    return service, timer


def atomic_write(path: Path, payload: bytes, mode: int = 0o600) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(prefix=path.name + ".", dir=str(path.parent))
    try:
        if hasattr(os, "fchmod"):
            os.fchmod(descriptor, mode)
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
        os.chmod(path, mode)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def run_checked(command: Sequence[str], *, allow_failure: bool = False) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(
        list(command),
        check=False,
        capture_output=True,
        text=True,
        timeout=30,
    )
    if result.returncode != 0 and not allow_failure:
        detail = (result.stderr or result.stdout).strip().replace("\n", " ")[:300]
        raise ScheduleError("scheduler command failed: %s" % (detail or command[0]))
    return result


def schedule_paths(platform: str, home: Path) -> Dict[str, Path]:
    if platform == "darwin":
        return {"definition": home / ("Library/LaunchAgents/%s.plist" % LABEL)}
    if platform.startswith("linux"):
        base = home / ".config/systemd/user"
        return {
            "service": base / ("%s.service" % SYSTEMD_NAME),
            "timer": base / ("%s.timer" % SYSTEMD_NAME),
        }
    return {}


def definition_references_script(
    platform: str,
    paths: Dict[str, Path],
    query_output: str,
    learning_script: Path,
) -> bool:
    expected = str(learning_script)
    try:
        if platform == "darwin":
            definition = paths["definition"]
            if definition.is_symlink() or definition.stat().st_size > 1024 * 1024:
                return False
            payload = plistlib.loads(definition.read_bytes())
            arguments = payload.get("ProgramArguments", []) if isinstance(payload, dict) else []
            return isinstance(arguments, list) and expected in arguments
        if platform.startswith("linux"):
            service = paths["service"]
            if service.is_symlink() or service.stat().st_size > 1024 * 1024:
                return False
            return expected in service.read_text(encoding="utf-8")
        if platform == "win32":
            return expected.casefold() in query_output.casefold()
    except (KeyError, OSError, ValueError, plistlib.InvalidFileException):
        return False
    return False


def install(args: argparse.Namespace) -> Dict[str, Any]:
    home = Path(args.home).expanduser().resolve()
    uv = resolve_executable(args.uv, "uv")
    source_learning = Path(args.learning_script).expanduser()
    learning_payload = regular_file_payload(source_learning)
    learning = stable_learning_script(home)
    state = Path(args.state_file).expanduser()
    if not state.is_absolute():
        raise ScheduleError("state file must be absolute")
    root = Path(args.root).expanduser() if args.root else None
    command = build_collect_command(uv, learning, state, args.scope, root, home)
    interval = int(args.interval_hours)
    if not 1 <= interval <= 168:
        raise ScheduleError("interval must be between 1 and 168 hours")

    platform = args.platform or sys.platform
    if args.dry_run:
        return {
            "ok": True,
            "installed": False,
            "dryRun": True,
            "platform": platform,
            "scope": args.scope,
            "intervalHours": interval,
            "command": command,
            "sourceLearningScript": str(source_learning.resolve()),
            "stableLearningScript": str(learning),
        }

    if platform not in {"darwin", "win32"} and not platform.startswith("linux"):
        raise ScheduleError("unsupported scheduler platform: %s" % platform)
    if learning.parent.is_symlink():
        raise ScheduleError("stable learning-script parent must not be a symlink")
    atomic_write(learning, learning_payload)
    created: List[str] = []

    if platform == "darwin":
        paths = schedule_paths(platform, home)
        log = home / ".csncompany/logs/memory-learning.error.log"
        log.parent.mkdir(parents=True, exist_ok=True)
        definition = paths["definition"]
        atomic_write(definition, launchd_plist(command, interval, log))
        domain = "gui/%d" % os.getuid()
        run_checked(["launchctl", "bootout", domain, str(definition)], allow_failure=True)
        run_checked(["launchctl", "bootstrap", domain, str(definition)])
        run_checked(["launchctl", "enable", "%s/%s" % (domain, LABEL)])
        created = [str(definition)]
    elif platform.startswith("linux"):
        paths = schedule_paths(platform, home)
        service, timer = systemd_units(command, interval)
        atomic_write(paths["service"], service.encode("utf-8"))
        atomic_write(paths["timer"], timer.encode("utf-8"))
        run_checked(["systemctl", "--user", "daemon-reload"])
        run_checked(["systemctl", "--user", "enable", "--now", "%s.timer" % SYSTEMD_NAME])
        created = [str(paths["service"]), str(paths["timer"])]
    elif platform == "win32":
        if interval < 24:
            schedule = "HOURLY"
            multiple = interval
        elif interval % 24 == 0:
            schedule = "DAILY"
            multiple = interval // 24
        else:
            raise ScheduleError("Windows intervals above 23 hours must be whole days")
        task_command = subprocess.list2cmdline(command)
        task = ["schtasks", "/Create", "/F", "/TN", WINDOWS_TASK, "/TR", task_command, "/SC", schedule]
        task.extend(["/MO", str(multiple)])
        run_checked(task)
        created = [WINDOWS_TASK]
    return {
        "ok": True,
        "installed": True,
        "platform": platform,
        "scope": args.scope,
        "intervalHours": interval,
        "definitions": created,
        "stateFile": str(state),
        "sourceLearningScript": str(source_learning.resolve()),
        "stableLearningScript": str(learning),
        "modelCallsPerTick": 0,
    }


def status(args: argparse.Namespace) -> Dict[str, Any]:
    home = Path(args.home).expanduser().resolve()
    platform = args.platform or sys.platform
    source_learning = Path(args.learning_script).expanduser()
    stable_learning = stable_learning_script(home)
    paths = schedule_paths(platform, home)
    query = subprocess.CompletedProcess([], 1, "", "")
    if platform == "darwin":
        definition = paths["definition"]
        query = run_checked(["launchctl", "print", "gui/%d/%s" % (os.getuid(), LABEL)], allow_failure=True)
        installed = definition.is_file() and query.returncode == 0
        definitions = [str(definition)]
    elif platform.startswith("linux"):
        query = run_checked(["systemctl", "--user", "is-enabled", "%s.timer" % SYSTEMD_NAME], allow_failure=True)
        installed = all(path.is_file() for path in paths.values()) and query.returncode == 0
        definitions = [str(path) for path in paths.values()]
    elif platform == "win32":
        query = run_checked(
            ["schtasks", "/Query", "/TN", WINDOWS_TASK, "/XML"],
            allow_failure=True,
        )
        installed = query.returncode == 0
        definitions = [WINDOWS_TASK]
    else:
        installed = False
        definitions = []
    source_hash = regular_file_hash(source_learning)
    stable_hash = regular_file_hash(stable_learning)
    script_current = bool(source_hash and stable_hash and source_hash == stable_hash)
    definition_current = bool(
        installed
        and definition_references_script(
            platform,
            paths,
            query.stdout or "",
            stable_learning,
        )
    )
    needs_reinstall = bool(
        installed and (not script_current or not definition_current)
    )
    return {
        "ok": True,
        "installed": installed,
        "platform": platform,
        "definitions": definitions,
        "stableLearningScript": str(stable_learning),
        "scriptCurrent": script_current,
        "definitionCurrent": definition_current,
        "needsReinstall": needs_reinstall,
        "repairAction": "install" if needs_reinstall else None,
    }


def remove(args: argparse.Namespace) -> Dict[str, Any]:
    home = Path(args.home).expanduser().resolve()
    platform = args.platform or sys.platform
    paths = schedule_paths(platform, home)
    removed: List[str] = []
    if platform == "darwin":
        definition = paths["definition"]
        run_checked(["launchctl", "bootout", "gui/%d" % os.getuid(), str(definition)], allow_failure=True)
        if definition.is_file() and not definition.is_symlink():
            definition.unlink()
            removed.append(str(definition))
    elif platform.startswith("linux"):
        run_checked(["systemctl", "--user", "disable", "--now", "%s.timer" % SYSTEMD_NAME], allow_failure=True)
        for path in paths.values():
            if path.is_file() and not path.is_symlink():
                path.unlink()
                removed.append(str(path))
        run_checked(["systemctl", "--user", "daemon-reload"], allow_failure=True)
    elif platform == "win32":
        result = run_checked(["schtasks", "/Delete", "/F", "/TN", WINDOWS_TASK], allow_failure=True)
        if result.returncode == 0:
            removed.append(WINDOWS_TASK)
    else:
        raise ScheduleError("unsupported scheduler platform: %s" % platform)
    stable_learning = stable_learning_script(home)
    if stable_learning.is_file() and not stable_learning.is_symlink():
        stable_learning.unlink()
        removed.append(str(stable_learning))
    return {"ok": True, "installed": False, "platform": platform, "removed": removed}


def common_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--platform", choices=["darwin", "linux", "win32"])
    parser.add_argument("--home", default=str(Path.home()))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Install the zero-model-call CSnCompany memory collector.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    install_parser = subparsers.add_parser("install")
    common_arguments(install_parser)
    install_parser.add_argument("--scope", choices=["registry", "pc", "folder"], default="registry")
    install_parser.add_argument("--root")
    install_parser.add_argument("--interval-hours", type=int, default=6)
    install_parser.add_argument("--uv")
    install_parser.add_argument("--learning-script", default=str(default_learning_script()))
    install_parser.add_argument("--state-file", default=str(default_state_path()))
    install_parser.add_argument("--dry-run", action="store_true")
    install_parser.set_defaults(func=install)

    status_parser = subparsers.add_parser("status")
    common_arguments(status_parser)
    status_parser.add_argument("--learning-script", default=str(default_learning_script()))
    status_parser.set_defaults(func=status)

    remove_parser = subparsers.add_parser("remove")
    common_arguments(remove_parser)
    remove_parser.set_defaults(func=remove)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    try:
        print(json.dumps(args.func(args), ensure_ascii=False, indent=2))
        return 0
    except (OSError, ValueError, ScheduleError, subprocess.TimeoutExpired) as exc:
        print(json.dumps({"ok": False, "error": str(exc)[:500]}, ensure_ascii=False, indent=2), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
