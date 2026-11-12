"""Filesystem manager for installed Aura skills."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
import logging
from pathlib import Path
import shutil
import tempfile
import zipfile

from .packager import pack_skill
from .registry import SkillRegistry
from .validator import SkillDocument, parse_skill

logger = logging.getLogger(__name__)


class SkillIntegrityError(ValueError):
    """Raised when a packaged skill fails its manifest.json checksum verification."""


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
        # Local registry of installed skill metadata, kept in sync by install/remove.
        self.registry = SkillRegistry(self.skills_dir / "registry.json")

    def install(self, source: str | Path) -> SkillInfo:
        source_path = Path(source)
        temporary: Path | None = None
        verified = False
        if source_path.is_file() and source_path.suffix == ".aura-skill":
            temporary = Path(tempfile.mkdtemp(prefix="aura-skill-"))
            with zipfile.ZipFile(source_path) as archive:
                for member in archive.infolist():
                    target = (temporary / member.filename).resolve()
                    if not str(target).startswith(str(temporary.resolve()) + "/"):
                        raise ValueError("skill archive contains unsafe path")
                archive.extractall(temporary)
            # A packaged skill carries manifest.json with a sha256 per file; verify
            # every entry before trusting the contents. Fail closed on any mismatch.
            self._verify_manifest(temporary)
            verified = True
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
        self._record(document, destination, verified)
        return self.status(document.name)

    def remove(self, name: str) -> None:
        target = self.skills_dir / name
        if not target.exists():
            raise FileNotFoundError(name)
        shutil.rmtree(target)
        self.registry.remove(name)

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
    def _verify_manifest(root: Path) -> None:
        """Validate every file against ``manifest.json`` sha256 digests.

        An unpackaged source (installed from a plain directory) has no manifest and
        is left unverified by design. A packaged skill with a manifest must match
        exactly: any missing file or digest mismatch raises ``SkillIntegrityError``.
        """
        manifest_path = root / "manifest.json"
        if not manifest_path.is_file():
            logger.warning(
                "Skill has no manifest.json; installing without checksum verification"
            )
            return
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            entries = manifest["files"]
        except (json.JSONDecodeError, KeyError, OSError) as exc:
            raise SkillIntegrityError(f"unreadable skill manifest: {exc}") from exc
        for entry in entries:
            relative = entry["path"]
            expected = entry["sha256"]
            file_path = (root / relative).resolve()
            if not str(file_path).startswith(str(root.resolve()) + "/"):
                raise SkillIntegrityError(
                    f"manifest path escapes skill root: {relative}"
                )
            if not file_path.is_file():
                raise SkillIntegrityError(
                    f"missing file listed in manifest: {relative}"
                )
            actual = hashlib.sha256(file_path.read_bytes()).hexdigest()
            if actual != expected:
                raise SkillIntegrityError(f"checksum mismatch for {relative}")

    def _record(self, document: SkillDocument, path: Path, verified: bool) -> None:
        """Persist installed-skill metadata in the registry (best-effort)."""
        manifest_path = path / "manifest.json"
        manifest_digest = None
        if manifest_path.is_file():
            manifest_digest = hashlib.sha256(manifest_path.read_bytes()).hexdigest()
        try:
            self.registry.update(
                document.name,
                {
                    "version": document.version,
                    "description": document.description,
                    "installed_at": datetime.now(timezone.utc).isoformat(),
                    "verified": verified,
                    "manifest_sha256": manifest_digest,
                },
            )
        except OSError as exc:
            logger.warning("Could not update skill registry: %s", exc)

    @staticmethod
    def _info(document: SkillDocument, path: Path) -> SkillInfo:
        return SkillInfo(document.name, document.version, document.description, path)
