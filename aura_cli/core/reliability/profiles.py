"""Profile-scoped, permission-restricted credential storage."""

from __future__ import annotations

import json
import os
from pathlib import Path
import re
import tempfile
import threading
from typing import Mapping

_PROFILE_NAME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$")


def validate_profile_name(name: str) -> str:
    """Validate and return a profile name suitable for filesystem namespaces."""
    if not _PROFILE_NAME.fullmatch(name):
        raise ValueError(f"invalid profile name: {name!r}")
    return name


class ProfileStore:
    """Isolate credentials and run metadata by profile under one directory."""

    def __init__(self, root: Path) -> None:
        self.root = Path(root).expanduser()
        self._lock = threading.RLock()

    def _path(self, name: str) -> Path:
        validate_profile_name(name)
        return self.root / name / "profile.json"

    def _validate_existing(self, path: Path) -> None:
        if path.is_symlink():
            raise PermissionError(f"profile path must not be a symlink: {path}")
        if path.is_dir() and path.stat().st_mode & 0o077:
            raise PermissionError(f"profile directory is too permissive: {path}")
        if path.is_file() and path.stat().st_mode & 0o077:
            raise PermissionError(f"profile file is too permissive: {path}")

    def save(self, name: str, values: Mapping[str, str]) -> Path:
        path = self._path(name)
        with self._lock:
            root_existed = self.root.exists()
            self.root.mkdir(parents=True, exist_ok=True)
            if root_existed:
                self._validate_existing(self.root)
            else:
                self.root.chmod(0o700)
            if path.parent.exists():
                self._validate_existing(path.parent)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.parent.chmod(0o700)
            fd, temporary = tempfile.mkstemp(prefix=".profile-", dir=path.parent)
            try:
                os.fchmod(fd, 0o600)
                with os.fdopen(fd, "w", encoding="utf-8") as handle:
                    json.dump(dict(values), handle, indent=2, sort_keys=True)
                    handle.flush()
                    os.fsync(handle.fileno())
                os.replace(temporary, path)
                path.chmod(0o600)
            finally:
                if os.path.exists(temporary):
                    os.unlink(temporary)
        return path

    def load(self, name: str) -> dict[str, str]:
        path = self._path(name)
        if not path.exists():
            return {}
        with self._lock:
            self._validate_existing(self.root)
            self._validate_existing(path.parent)
            self._validate_existing(path)
            return {str(key): str(value) for key, value in json.loads(path.read_text(encoding="utf-8")).items()}

    def delete(self, name: str) -> None:
        path = self._path(name)
        with self._lock:
            if path.exists():
                self._validate_existing(self.root)
                self._validate_existing(path.parent)
                self._validate_existing(path)
                path.unlink()

    def list_profiles(self) -> list[str]:
        if not self.root.exists():
            return []
        with self._lock:
            self._validate_existing(self.root)
            profiles = []
            for path in self.root.iterdir():
                if path.is_dir() and _PROFILE_NAME.fullmatch(path.name):
                    self._validate_existing(path)
                    profiles.append(path.name)
            return sorted(profiles)

    def path_for(self, name: str) -> Path:
        return self._path(name)
