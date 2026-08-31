"""Local registry of installed skill metadata."""

from __future__ import annotations

import json
from pathlib import Path


class SkillRegistry:
    def __init__(self, path: Path) -> None:
        self.path = Path(path)

    def list(self) -> dict[str, dict]:
        if not self.path.exists():
            return {}
        return json.loads(self.path.read_text(encoding="utf-8"))

    def update(self, name: str, metadata: dict) -> None:
        data = self.list()
        data[name] = metadata
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(data, indent=2, sort_keys=True), encoding="utf-8")
