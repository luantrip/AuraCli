#!/usr/bin/env python3
"""Run a command and report filesystem artifacts it creates or changes."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
from typing import Any

IGNORED_DIRS = {".git", ".venv", "__pycache__"}


def file_record(path: Path) -> dict[str, Any]:
    stat = path.stat()
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return {"size": stat.st_size, "sha256": digest.hexdigest()}


def snapshot(root: Path) -> dict[str, dict[str, Any]]:
    if not root.exists():
        return {}
    records: dict[str, dict[str, Any]] = {}
    for current_root, dirs, files in os.walk(root):
        dirs[:] = sorted(
            directory for directory in dirs if directory not in IGNORED_DIRS
        )
        current = Path(current_root)
        for name in sorted(files):
            path = current / name
            try:
                records[str(path.relative_to(root))] = file_record(path)
            except (FileNotFoundError, PermissionError, OSError):
                continue
    return records


def diff(before: dict[str, Any], after: dict[str, Any]) -> dict[str, list[str]]:
    before_paths = set(before)
    after_paths = set(after)
    return {
        "created": sorted(after_paths - before_paths),
        "modified": sorted(
            path for path in before_paths & after_paths if before[path] != after[path]
        ),
        "deleted": sorted(before_paths - after_paths),
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Execute a command with isolated Aura data and report artifacts."
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="Report directory (default: a temporary directory).",
    )
    parser.add_argument(
        "--project-root",
        type=Path,
        default=Path.cwd(),
        help="Project tree to monitor.",
    )
    parser.add_argument("command", nargs=argparse.REMAINDER)
    args = parser.parse_args()
    command = args.command[1:] if args.command[:1] == ["--"] else args.command
    if not command:
        parser.error("a command is required after --")

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    output = (
        args.output or Path(tempfile.gettempdir()) / "aura-artifact-audit" / timestamp
    ).resolve()
    aura_home = output / "aura-home"
    output.mkdir(parents=True, exist_ok=True)

    project_root = args.project_root.resolve()
    before_project = snapshot(project_root)
    before_aura = snapshot(aura_home)

    environment = os.environ.copy()
    environment["AURA_HOME"] = str(aura_home)
    environment["PYTHONDONTWRITEBYTECODE"] = "1"
    started = datetime.now(timezone.utc)
    completed = subprocess.run(command, cwd=project_root, env=environment, check=False)
    finished = datetime.now(timezone.utc)

    after_project = snapshot(project_root)
    after_aura = snapshot(aura_home)
    report = {
        "command": command,
        "exit_code": completed.returncode,
        "started_at": started.isoformat(),
        "finished_at": finished.isoformat(),
        "project_root": str(project_root),
        "aura_home": str(aura_home),
        "project": diff(before_project, after_project),
        "aura_home_artifacts": diff(before_aura, after_aura),
        "aura_home_files": after_aura,
    }
    report_path = output / "artifact-report.json"
    report_path.write_text(
        json.dumps(report, indent=2, sort_keys=True), encoding="utf-8"
    )
    print(f"Artifact report: {report_path}")
    return completed.returncode


if __name__ == "__main__":
    sys.exit(main())
