"""Safe .aura-skill archive creation."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any
import zipfile

from .validator import parse_skill


def pack_skill(skill_dir: Path, output: Path) -> Path:
    root = Path(skill_dir).resolve()
    document = parse_skill(root / "SKILL.md")
    files = sorted(path for path in root.rglob("*") if path.is_file() and path.name != ".DS_Store")
    manifest: dict[str, Any] = {
        "name": document.name,
        "version": document.version,
        "files": [],
    }
    with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as archive:
        for path in files:
            relative = path.relative_to(root).as_posix()
            data = path.read_bytes()
            archive.writestr(relative, data)
            manifest["files"].append({"path": relative, "sha256": hashlib.sha256(data).hexdigest()})
        archive.writestr("manifest.json", json.dumps(manifest, indent=2))
    return Path(output)
