"""
codebase_traversal — filesystem traversal with Imagination (Nim) acceleration.

Functions traverse_and_filter_codebase, quick_scan_with_imagination,
_load_gitignore_spec and _is_path_excluded support codebase_analysis.py.
"""

from __future__ import annotations

import fnmatch
import os
from pathlib import Path
from typing import Any, Dict, Generator, List, Optional

from aura_cli.core.logger import get_logger

logger = get_logger(__name__)

# Imagination (Nim binary) optional fast-path
IMAGINATION_AVAILABLE = False
try:
    from aura_cli.core.tools.imagination_tools import (
        get_imagination_scanner,
    )

    IMAGINATION_AVAILABLE = True
except Exception:
    pass

try:
    import pathspec

    _PATHSPEC_AVAILABLE = True
except ImportError:
    pathspec = None  # type: ignore[assignment]
    _PATHSPEC_AVAILABLE = False


# Public types


class ScanOptions:
    """Options for filesystem traversal."""

    __slots__ = ("follow_symlinks", "include_hidden", "max_depth")

    def __init__(
        self,
        max_depth: int = 20,
        follow_symlinks: bool = False,
        include_hidden: bool = False,
    ) -> None:
        self.max_depth = max_depth
        self.follow_symlinks = follow_symlinks
        self.include_hidden = include_hidden


class ScanResult:
    """Single file result from traversal. Supports both attribute and dict access."""

    __slots__ = (
        "extension",
        "full_path",
        "last_modified",
        "name",
        "path",
        "relative",
        "size",
        "size_kb",
    )

    def __init__(self, path: str, relative: str, size: int = 0) -> None:
        # `path` and `relative` are both the relative path (test-contract).
        # `full_path` is the absolute path for I/O operations.
        self.path = relative  # relative path — dict r['path'] returns relative
        self.full_path = path  # absolute path for open() / os.path operations
        self.relative = relative
        self.size = size
        self.extension = Path(path).suffix.lower()
        self.name = Path(path).name
        self.size_kb = round(size / 1024, 2) if size else 0.0
        try:
            self.last_modified = os.path.getmtime(path)
        except OSError:
            self.last_modified = 0.0

    # Dict-like access for backward compatibility
    def __getitem__(self, key: str) -> Any:
        return getattr(self, key)

    def __contains__(self, key: str) -> bool:
        return key in self.__slots__

    def get(self, key: str, default: Any = None) -> Any:
        return getattr(self, key, default)


# .gitignore support


def _load_gitignore_spec(root: str) -> Optional[Any]:
    """Load a pathspec from .gitignore in *root*, or None."""
    if not _PATHSPEC_AVAILABLE:
        return None
    gitignore = os.path.join(root, ".gitignore")
    if not os.path.isfile(gitignore):
        return None
    try:
        with open(gitignore, encoding="utf-8", errors="replace") as fh:
            return pathspec.PathSpec.from_lines("gitwildmatch", fh)
    except Exception:
        return None


def _is_path_excluded(
    path: str,
    root: str,
    spec: Optional[Any],
    excluded_dirs: Optional[List[str]] = None,
) -> bool:
    """Return True if *path* should be excluded from scan."""
    rel = os.path.relpath(path, root)
    if spec is not None and spec.match_file(rel):
        return True
    if excluded_dirs:
        parts = set(Path(rel).parts)
        for excl in excluded_dirs:
            if excl in parts:
                return True
    return False


# Core traversal

_DEFAULT_EXCLUDED_DIRS = {
    "__pycache__",
    ".git",
    ".hg",
    ".svn",
    ".venv",
    "venv",
    ".mypy_cache",
    ".pytest_cache",
    ".tox",
}
# Note: node_modules, build, dist are NOT auto-excluded — callers pass them
# via exclude_paths when needed so tests can control traversal explicitly.

_DEFAULT_EXCLUDED_EXTS = {
    ".pyc",
    ".pyo",
    ".pyd",
    ".so",
    ".dll",
    ".dylib",
    ".jpg",
    ".jpeg",
    ".png",
    ".gif",
    ".bmp",
    ".ico",
    ".svg",
    ".mp3",
    ".mp4",
    ".wav",
    ".avi",
    ".mkv",
    ".zip",
    ".tar",
    ".gz",
    ".bz2",
    ".7z",
    ".pdf",
    ".doc",
    ".docx",
    ".xls",
    ".xlsx",
    ".db",
    ".sqlite",
    ".sqlite3",
}


def traverse_and_filter_codebase(
    root_path: str,
    include_extensions: Optional[List[str]] = None,
    excluded_dirs: Optional[List[str]] = None,
    options: Optional[ScanOptions] = None,
    respect_gitignore: bool = True,
    exclude_paths: Optional[List[str]] = None,
    min_size_kb: Optional[float] = None,
    max_size_kb: Optional[float] = None,
    max_depth: Optional[int] = None,
) -> Generator[ScanResult, None, None]:
    """
    Walk *root_path* and yield ScanResult for each matching file.

    Args:
        root_path: Directory to scan.
        include_extensions: Only include files with these extensions (e.g. ['.py']).
        excluded_dirs: Additional directory names to skip.
        options: ScanOptions instance.
        respect_gitignore: If True, honour .gitignore rules.
        exclude_paths: Glob patterns or relative paths to exclude.
        min_size_kb: Minimum file size in KB.
        max_size_kb: Maximum file size in KB.
        max_depth: Maximum directory depth to recurse.
    """
    opts = options or ScanOptions()
    if max_depth is not None:
        opts.max_depth = max_depth
    spec = _load_gitignore_spec(root_path) if respect_gitignore else None
    excl_dirs = _DEFAULT_EXCLUDED_DIRS | set(excluded_dirs or [])

    def _should_exclude_dir(name: str) -> bool:
        return name in excl_dirs or name.startswith(".")

    ext_filter: set = set()
    if include_extensions is not None:
        for e in include_extensions:
            if e == "" or e == ".":
                ext_filter.add("")
            elif e.startswith("."):
                ext_filter.add(e.lower())
            else:
                ext_filter.add(f".{e.lower()}")

    min_bytes = int(min_size_kb * 1024) if min_size_kb is not None else None
    max_bytes = int(max_size_kb * 1024) if max_size_kb is not None else None
    excl_path_set = set(exclude_paths or [])
    root_depth = root_path.rstrip(os.sep).count(os.sep)

    for dirpath, dirnames, filenames in os.walk(
        root_path, followlinks=opts.follow_symlinks
    ):
        current_depth = dirpath.count(os.sep) - root_depth
        if opts.max_depth is not None and current_depth >= opts.max_depth:
            dirnames.clear()
            if current_depth > opts.max_depth:
                continue

        dirnames[:] = [
            d
            for d in dirnames
            if not _should_exclude_dir(d)
            and not _is_path_excluded(os.path.join(dirpath, d), root_path, spec)
        ]

        for fname in filenames:
            fpath = os.path.join(dirpath, fname)
            result = _check_file_filters(
                fpath,
                fname,
                root_path,
                spec,
                ext_filter,
                excl_path_set,
                min_bytes,
                max_bytes,
                opts.include_hidden,
            )
            if result is not None:
                yield result


def _check_file_filters(
    fpath: str,
    fname: str,
    root_path: str,
    spec: Any,
    ext_filter: set,
    excl_path_set: set,
    min_bytes: Optional[int],
    max_bytes: Optional[int],
    include_hidden: bool,
) -> Optional[ScanResult]:
    """Return a ScanResult if the file passes all filters, or None to skip it."""
    ext = Path(fname).suffix.lower()
    is_hidden = fname.startswith(".")

    if not include_hidden and is_hidden:
        hidden_allowed = bool(
            ext_filter
            and (
                ext in ext_filter
                or fname in (e for e in ext_filter if e.startswith("."))
            )
        )
        if not hidden_allowed:
            return None

    if ext in _DEFAULT_EXCLUDED_EXTS:
        return None
    if ext_filter and ext not in ext_filter and not (ext == "" and "" in ext_filter):
        return None
    if _is_path_excluded(fpath, root_path, spec):
        return None

    rel = os.path.relpath(fpath, root_path)
    if excl_path_set and any(
        fnmatch.fnmatch(rel, pat) or rel.startswith(pat.rstrip("/") + "/")
        for pat in excl_path_set
    ):
        return None

    try:
        size = os.path.getsize(fpath)
    except OSError:
        size = 0

    if min_bytes is not None and size < min_bytes:
        return None
    if max_bytes is not None and size > max_bytes:
        return None

    return ScanResult(path=fpath, relative=rel, size=size)


def quick_scan_with_imagination(
    root_path: str,
    include_extensions: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """
    Fast scan using Imagination Nim binary when available,
    falling back to traverse_and_filter_codebase.

    Returns a dict with 'files' (list of path strings) and 'stats'.
    """
    if IMAGINATION_AVAILABLE:
        try:
            scanner = get_imagination_scanner()
            result = scanner.scan(root_path)
            files = [file.path for file in result.files]
            if include_extensions:
                files = [
                    path
                    for path in files
                    if any(path.endswith(ext) for ext in include_extensions)
                ]
            if files:
                logger.debug("quick_scan_with_imagination: used Nim scanner")
                return {"files": files, "stats": {"file_count": len(files)}}
        except Exception as e:
            logger.debug(f"Imagination scanner failed ({e}), falling back to Python")

    files = [
        r.path for r in traverse_and_filter_codebase(root_path, include_extensions)
    ]
    return {"files": files, "stats": {"file_count": len(files)}}


# Default extension set (used by codebase_analysis re-exports)
_DEFAULT_CODE_EXTENSIONS = {
    ".py",
    ".js",
    ".ts",
    ".jsx",
    ".tsx",
    ".java",
    ".kt",
    ".scala",
    ".go",
    ".rs",
    ".cpp",
    ".c",
    ".h",
    ".hpp",
    ".cs",
    ".rb",
    ".php",
    ".swift",
    ".m",
    ".sh",
    ".bash",
    ".zsh",
    ".fish",
    ".html",
    ".css",
    ".scss",
    ".sass",
    ".less",
    ".json",
    ".yaml",
    ".yml",
    ".toml",
    ".ini",
    ".cfg",
    ".conf",
    ".sql",
    ".md",
    ".rst",
    ".txt",
    ".xml",
    ".nim",
    ".lua",
    ".r",
    ".jl",
}
