"""Dependency-free validation for SKILL.md documents."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re


@dataclass(frozen=True)
class SkillDocument:
    name: str
    version: str
    description: str
    body: str
    metadata: dict[str, str]


def parse_skill(path: Path) -> SkillDocument:
    content = Path(path).read_text(encoding="utf-8")
    if not content.startswith("---\n"):
        raise ValueError("SKILL.md must start with YAML frontmatter")
    end = content.find("\n---", 4)
    if end < 0:
        raise ValueError("SKILL.md has unterminated frontmatter")
    metadata: dict[str, str] = {}
    for line in content[4:end].splitlines():
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        key, separator, value = line.partition(":")
        if not separator or not re.fullmatch(r"[A-Za-z][A-Za-z0-9_-]*", key.strip()):
            raise ValueError(f"invalid frontmatter line: {line}")
        metadata[key.strip()] = value.strip().strip("\"'")
    for required in ("name", "description"):
        if not metadata.get(required):
            raise ValueError(f"missing required field: {required}")
    if Path(path).name != "SKILL.md":
        raise ValueError("skill document must be named SKILL.md")
    return SkillDocument(metadata["name"], metadata.get("version", "0.1.0"), metadata["description"], content[end + 4:].lstrip(), metadata)
