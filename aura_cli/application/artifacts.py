"""Canonical filesystem layout for artifacts owned by Aura."""

from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path


def get_aura_home() -> Path:
    """Return the configurable Aura user data directory."""
    configured = os.environ.get("AURA_HOME")
    if configured:
        return Path(configured).expanduser().resolve()
    return Path.home() / ".aura"


def _safe_parts(parts: tuple[str, ...]) -> tuple[str, ...]:
    for part in parts:
        candidate = Path(part)
        if candidate.is_absolute() or ".." in candidate.parts:
            raise ValueError(f"Artifact path must be relative and contained: {part!r}")
    return parts


@dataclass(frozen=True)
class ArtifactLayout:
    """Authority for user-global and project-local Aura artifacts."""

    project_root: Path | None = None
    user_root: Path | None = None

    def user(self, *parts: str) -> Path:
        root = self.user_root.resolve() if self.user_root else get_aura_home()
        return root.joinpath(*_safe_parts(parts))

    def project(self, *parts: str) -> Path:
        configured = os.environ.get("AURA_PROJECT_ROOT")
        root = (
            self.project_root
            if self.project_root is not None
            else Path(configured).expanduser()
            if configured
            else Path.cwd()
        ).resolve()
        return root.joinpath(".aura", *_safe_parts(parts))


def aura_path(*parts: str) -> Path:
    """Build a path below Aura's user data directory."""
    return ArtifactLayout().user(*parts)
