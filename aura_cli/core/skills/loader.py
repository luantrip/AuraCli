"""Load builtin and installed skill documents with conflict handling."""

from __future__ import annotations

from pathlib import Path

from .validator import SkillDocument, parse_skill


class SkillLoader:
    def __init__(self, directories: list[Path]) -> None:
        self.directories = [Path(directory) for directory in directories]

    def load(self) -> list[SkillDocument]:
        loaded: dict[str, SkillDocument] = {}
        for directory in self.directories:
            if not directory.exists():
                continue
            for document_path in sorted(directory.glob("*/SKILL.md")):
                document = parse_skill(document_path)
                loaded.setdefault(document.name, document)
        return list(loaded.values())
