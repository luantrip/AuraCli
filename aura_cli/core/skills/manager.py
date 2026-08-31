"""Filesystem manager for installed Aura skills."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import shutil
import tempfile
import zipfile

from .packager import pack_skill
from .validator import SkillDocument, parse_skill


@dataclass(frozen=True)
class SkillInfo:
    name: str
    version: str
    description: str
    path: Path


class SkillManager:
    def __init__(self, skills_dir: Path) -> None:
        self.skills_dir = Path(skills_dir)
        self.skills_dir.mkdir(parents=True, exist_ok=True)

    def install(self, source: str | Path) -> SkillInfo:
        source_path = Path(source)
        temporary: Path | None = None
        if source_path.is_file() and source_path.suffix == ".aura-skill":
            temporary = Path(tempfile.mkdtemp(prefix="aura-skill-"))
            with zipfile.ZipFile(source_path) as archive:
                for member in archive.infolist():
                    target = (temporary / member.filename).resolve()
                    if not str(target).startswith(str(temporary.resolve()) + "/"):
                        raise ValueError("skill archive contains unsafe path")
                archive.extractall(temporary)
            source_path = temporary
        if not source_path.is_dir():
            raise FileNotFoundError(source)
        document = parse_skill(source_path / "SKILL.md")
        destination = self.skills_dir / document.name
        if destination.exists():
            shutil.rmtree(destination)
        shutil.copytree(source_path, destination)
        if temporary:
            shutil.rmtree(temporary)
        return self.status(document.name)

    def remove(self, name: str) -> None:
        target = self.skills_dir / name
        if not target.exists():
            raise FileNotFoundError(name)
        shutil.rmtree(target)

    def list_installed(self) -> list[SkillInfo]:
        result = []
        for path in sorted(self.skills_dir.iterdir()):
            document_path = path / "SKILL.md"
            if path.is_dir() and document_path.is_file():
                result.append(self._info(parse_skill(document_path), path))
        return result

    def status(self, name: str) -> SkillInfo:
        path = self.skills_dir / name
        return self._info(parse_skill(path / "SKILL.md"), path)

    def pack(self, skill_dir: Path, output: Path) -> Path:
        return pack_skill(skill_dir, output)

    @staticmethod
    def _info(document: SkillDocument, path: Path) -> SkillInfo:
        return SkillInfo(document.name, document.version, document.description, path)
