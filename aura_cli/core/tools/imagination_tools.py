"""
Imagination Engine Tools - Python wrapper for the Nim-based filesystem scanner.

This module provides Python bindings for the ultra-fast Imagination Engine,
enabling AI agents to rapidly scan and understand project structures.

Features:
    - Async subprocess execution for non-blocking scans
    - Pydantic models for type-safe data handling
    - Intelligent caching to avoid redundant scans
    - Real-time file watching with watchdog integration
    - Graceful fallback to pure Python when Nim binary unavailable

Architecture:
    ImaginationScanner -> NimBinary (fast) or PurePython (fallback)
                       -> ScanResult (Pydantic model)
                       -> Cache (TTL-based)
"""

from __future__ import annotations

import asyncio
from datetime import datetime
from enum import Enum
import json
import os
from pathlib import Path
import time
from typing import Any, ClassVar, Dict, List, Optional, Union

from pydantic import BaseModel, Field

from aura_cli.core.logger import get_logger
from aura_cli.core.nim_runtime import (
    resolve_nim_binary,
    run_nim_process,
)

logger = get_logger(__name__)


PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
NIM_BINARY_PATH_DEFAULT = PROJECT_ROOT / "bin" / "imagination"
CACHE_TTL_SECONDS = 60  # Cache results for 1 minute
MAX_CACHE_SIZE = 10  # Keep up to 10 cached scans


def _get_nim_binary_path() -> Path:
    """
    Get Nim binary path from user config or fallback to default.

    Returns:
        Path to Nim binary
    """
    resolved = resolve_nim_binary(
        "imagination", extra_candidates=[NIM_BINARY_PATH_DEFAULT]
    )
    if resolved:
        return resolved
    return NIM_BINARY_PATH_DEFAULT


class FileCategory(str, Enum):
    """File category classification."""

    CODE = "code"
    CONFIG = "config"
    DOC = "doc"
    STYLE = "style"
    DATA = "data"
    BINARY = "binary"
    OTHER = "other"


class FileInfo(BaseModel):
    """Information about a single file."""

    path: str = Field(description="Relative path from project root")
    name: str = Field(description="File name")
    extension: str = Field(default="", description="File extension including dot")
    size: int = Field(default=0, description="File size in bytes")
    lines: int = Field(default=0, description="Number of lines (0 for binary)")
    last_modified: float = Field(description="Unix timestamp of last modification")
    category: FileCategory = Field(default=FileCategory.OTHER)
    preview: List[str] = Field(default_factory=list, description="First few lines")
    is_directory: bool = Field(default=False)

    @property
    def last_modified_datetime(self) -> datetime:
        """Get last modified as datetime object."""
        return datetime.fromtimestamp(self.last_modified)

    @property
    def size_human(self) -> str:
        """Get human-readable file size."""
        size: float = self.size
        for unit in ["B", "KB", "MB", "GB"]:
            if size < 1024:
                return f"{size:.1f} {unit}"
            size /= 1024
        return f"{size:.1f} TB"

    @property
    def age_human(self) -> str:
        """Get human-readable time since last modification."""
        seconds = time.time() - self.last_modified
        if seconds < 60:
            return f"{int(seconds)}s ago"
        minutes = seconds / 60
        if minutes < 60:
            return f"{int(minutes)}m ago"
        hours = minutes / 60
        if hours < 24:
            return f"{int(hours)}h ago"
        days = hours / 24
        return f"{int(days)}d ago"


class ScanResult(BaseModel):
    """Result of a filesystem scan."""

    root_path: str = Field(description="Absolute path that was scanned")
    total_files: int = Field(default=0)
    total_directories: int = Field(default=0)
    total_lines: int = Field(default=0)
    total_size: int = Field(default=0, description="Total size in bytes")
    scan_duration_ms: int = Field(
        default=0, description="Scan duration in milliseconds"
    )
    files: List[FileInfo] = Field(default_factory=list)
    by_category: Dict[str, int] = Field(default_factory=dict)
    by_extension: Dict[str, int] = Field(default_factory=dict)
    recently_modified: List[FileInfo] = Field(default_factory=list)
    timestamp: float = Field(default_factory=time.time)

    @property
    def total_size_human(self) -> str:
        """Get human-readable total size."""
        size: float = self.total_size
        for unit in ["B", "KB", "MB", "GB"]:
            if size < 1024:
                return f"{size:.1f} {unit}"
            size /= 1024
        return f"{size:.1f} TB"

    @property
    def age(self) -> float:
        """Seconds since this scan was performed."""
        return time.time() - self.timestamp

    def is_stale(self, ttl: float = CACHE_TTL_SECONDS) -> bool:
        """Check if this scan result is stale."""
        return self.age > ttl

    def get_files_by_category(self, category: FileCategory) -> List[FileInfo]:
        """Get files filtered by category."""
        return [f for f in self.files if f.category == category]

    def get_files_by_extension(self, ext: str) -> List[FileInfo]:
        """Get files filtered by extension."""
        if not ext.startswith("."):
            ext = f".{ext}"
        return [f for f in self.files if f.extension == ext]

    def search_files(self, query: str) -> List[FileInfo]:
        """Search files by name or path."""
        query = query.lower()
        return [
            f for f in self.files if query in f.path.lower() or query in f.name.lower()
        ]


class ScanOptions(BaseModel):
    """Options for filesystem scanning."""

    include_preview: bool = Field(default=True, description="Include file previews")
    max_depth: int = Field(default=0, description="Max depth (0 = unlimited)")
    include_hidden: bool = Field(default=False, description="Include hidden files")
    respect_gitignore: bool = Field(default=True, description="Respect .gitignore")
    max_file_size: int = Field(
        default=10_000_000, description="Skip files larger than this"
    )


class PurePythonScanner:
    """
    Fallback scanner using pure Python when Nim binary is unavailable.

    Slower than Nim but provides identical functionality.
    """

    IGNORE_DIRS: ClassVar[set] = {
        ".git",
        ".svn",
        ".hg",
        "node_modules",
        "__pycache__",
        ".pytest_cache",
        ".mypy_cache",
        ".ruff_cache",
        ".tox",
        ".nox",
        "venv",
        ".venv",
        "env",
        ".env",
        "dist",
        "build",
        ".build",
        "target",
        ".idea",
        ".vscode",
        "coverage",
        ".coverage",
        "htmlcov",
        ".eggs",
    }

    CODE_EXTS: ClassVar[set] = {
        ".py",
        ".js",
        ".ts",
        ".jsx",
        ".tsx",
        ".go",
        ".rs",
        ".nim",
        ".c",
        ".cpp",
        ".h",
        ".hpp",
        ".java",
        ".kt",
        ".swift",
        ".rb",
        ".php",
        ".cs",
        ".scala",
        ".clj",
        ".ex",
        ".exs",
        ".hs",
        ".ml",
    }

    CONFIG_EXTS: ClassVar[set] = {
        ".json",
        ".yaml",
        ".yml",
        ".toml",
        ".ini",
        ".cfg",
        ".conf",
        ".env",
        ".xml",
    }
    DOC_EXTS: ClassVar[set] = {".md", ".markdown", ".rst", ".txt", ".adoc", ".org"}
    STYLE_EXTS: ClassVar[set] = {".css", ".scss", ".sass", ".less", ".tcss", ".styl"}
    DATA_EXTS: ClassVar[set] = {".csv", ".tsv", ".sql", ".db", ".sqlite"}
    BINARY_EXTS: ClassVar[set] = {
        ".pyc",
        ".pyo",
        ".so",
        ".dylib",
        ".dll",
        ".exe",
        ".bin",
        ".png",
        ".jpg",
        ".jpeg",
        ".gif",
        ".webp",
        ".svg",
        ".ico",
        ".mp3",
        ".mp4",
        ".wav",
        ".pdf",
        ".zip",
        ".tar",
        ".gz",
    }

    @classmethod
    def categorize(cls, ext: str) -> FileCategory:
        """Categorize a file by extension."""
        ext = ext.lower()
        if ext in cls.CODE_EXTS:
            return FileCategory.CODE
        if ext in cls.CONFIG_EXTS:
            return FileCategory.CONFIG
        if ext in cls.DOC_EXTS:
            return FileCategory.DOC
        if ext in cls.STYLE_EXTS:
            return FileCategory.STYLE
        if ext in cls.DATA_EXTS:
            return FileCategory.DATA
        if ext in cls.BINARY_EXTS:
            return FileCategory.BINARY
        return FileCategory.OTHER

    @classmethod
    def analyze_file(
        cls, path: str, max_preview_lines: int = 8
    ) -> tuple[int, List[str]]:
        """Count lines and extract preview in a single pass."""
        lines_count = 0
        preview: list[Any] = []
        chars_preview = 0

        try:
            with open(path, encoding="utf-8", errors="ignore") as f:
                for line in f:
                    lines_count += 1

                    if len(preview) < max_preview_lines and chars_preview < 500:
                        stripped = line.strip()
                        if stripped:
                            preview.append(stripped[:100])
                            chars_preview += len(stripped)
        except Exception as _e:
            logger.debug(f"Ignorado: {_e}")

        return lines_count, preview

    @classmethod
    def _should_ignore(cls, name: str, is_dir: bool, include_hidden: bool) -> bool:
        """Check if file/directory should be ignored."""
        if not include_hidden and name.startswith(".") and name != ".gitignore":
            return True
        return bool(is_dir and name in cls.IGNORE_DIRS)

    @classmethod
    def scan(cls, root_path: Path, options: ScanOptions) -> ScanResult:
        """Scan directory using pure Python with os.scandir optimization."""
        start_time = time.time()
        root_path = root_path.resolve()
        root_path_str = str(root_path)

        files: List[FileInfo] = []
        by_category: Dict[str, int] = {cat.value: 0 for cat in FileCategory}
        by_extension: Dict[str, int] = {}
        total_dirs = 0
        total_lines = 0
        total_size: int = 0
        recently_modified: List[FileInfo] = []
        recent_threshold = time.time() - (24 * 60 * 60)

        def should_ignore(name: str, is_dir: bool) -> bool:
            return cls._should_ignore(name, is_dir, options.include_hidden)

        def walk_dir(current_path: str, depth: int = 0):
            """Recursively walk directory tree using os.scandir."""
            nonlocal total_dirs, total_lines, total_size

            if options.max_depth > 0 and depth > options.max_depth:
                return

            try:
                with os.scandir(current_path) as it:
                    entries = list(
                        it
                    )  # Consume iterator to close file handle earlier if recursing

                for entry in entries:
                    name = entry.name
                    is_dir = entry.is_dir(follow_symlinks=False)

                    if should_ignore(name, is_dir):
                        continue

                    if is_dir:
                        total_dirs += 1
                        walk_dir(entry.path, depth + 1)
                    elif entry.is_file(follow_symlinks=False):
                        try:
                            stat = entry.stat()
                            size = stat.st_size

                            if (
                                options.max_file_size > 0
                                and size > options.max_file_size
                            ):
                                continue
                            ext = os.path.splitext(name)[1]
                            category = cls.categorize(ext)
                            rel_path = os.path.relpath(entry.path, root_path_str)

                            file_info = FileInfo(
                                path=rel_path,
                                name=name,
                                extension=ext,
                                size=size,
                                last_modified=stat.st_mtime,
                                category=category,
                                is_directory=False,
                            )
                            if category != FileCategory.BINARY:
                                flines, fpreview = cls.analyze_file(entry.path)
                                file_info.lines = flines
                                total_lines += flines

                                if options.include_preview and size < 50_000:
                                    file_info.preview = fpreview

                            files.append(file_info)
                            total_size += int(size)

                            by_category[category.value] += 1
                            if ext:
                                by_extension[ext] = by_extension.get(ext, 0) + 1

                            if file_info.last_modified >= recent_threshold:
                                recently_modified.append(file_info)

                        except (PermissionError, OSError):
                            continue
            except (PermissionError, OSError) as _e:
                logger.debug(f"Ignorado: {_e}")

        walk_dir(root_path_str)
        files.sort(key=lambda f: f.last_modified, reverse=True)
        recently_modified.sort(key=lambda f: f.last_modified, reverse=True)
        recently_modified = recently_modified[:20]

        duration_ms = int((time.time() - start_time) * 1000)

        return ScanResult(
            root_path=root_path_str,
            total_files=len(files),
            total_directories=total_dirs,
            total_lines=total_lines,
            total_size=total_size,
            scan_duration_ms=duration_ms,
            files=files,
            by_category=by_category,
            by_extension=by_extension,
            recently_modified=recently_modified,
        )


class ImaginationScanner:
    """
    High-performance filesystem scanner with Nim acceleration.

    Uses the Nim binary when available for maximum performance,
    falling back to pure Python when necessary.

    Features:
    - Async scanning for non-blocking TUI integration
    - Intelligent caching with TTL
    - Real-time file watching (optional)
    """

    def __init__(self):
        """Initialize the scanner with an empty cache and unresolved Nim availability."""
        self._cache: Dict[str, ScanResult] = {}
        self._nim_available: Optional[bool] = None
        self._lock = asyncio.Lock()

    @property
    def nim_available(self) -> bool:
        """Check if Nim binary is available."""
        if self._nim_available is None:
            nim_path = _get_nim_binary_path()
            self._nim_available = nim_path.exists() and os.access(nim_path, os.X_OK)
            if self._nim_available:
                logger.info(f"Imagination Engine: Using Nim binary at {nim_path}")
            else:
                logger.info("Imagination Engine: Using pure Python fallback")
        return self._nim_available

    def _cache_key(self, path: Path, options: ScanOptions) -> str:
        """Generate cache key for a scan."""
        return f"{path.resolve()}:{hash(str(options.model_dump()))}"

    def _get_cached(
        self, key: str, ttl: float = CACHE_TTL_SECONDS
    ) -> Optional[ScanResult]:
        """Get cached result if still valid."""
        if key in self._cache:
            result = self._cache[key]
            if not result.is_stale(ttl):
                logger.debug(f"Cache hit for {key}")
                return result
            else:
                del self._cache[key]
        return None

    def _set_cached(self, key: str, result: ScanResult):
        """Cache a scan result."""
        while len(self._cache) >= MAX_CACHE_SIZE:
            oldest_key = min(self._cache, key=lambda k: self._cache[k].timestamp)
            del self._cache[oldest_key]

        self._cache[key] = result

    def clear_cache(self):
        """Clear all cached scan results."""
        self._cache.clear()
        logger.info("Imagination cache cleared")

    async def scan_async(
        self,
        path: Union[str, Path],
        options: Optional[ScanOptions] = None,
        use_cache: bool = True,
        cache_ttl: float = CACHE_TTL_SECONDS,
    ) -> ScanResult:
        """
        Asynchronously scan a directory.

        Args:
            path: Directory to scan
            options: Scan options
            use_cache: Whether to use cached results
            cache_ttl: Cache time-to-live in seconds

        Returns:
            ScanResult with file information
        """
        path = Path(path).expanduser().resolve()
        options = options or ScanOptions()

        if not path.exists():
            raise FileNotFoundError(f"Caminho não encontrado: {path}")
        if not path.is_dir():
            raise NotADirectoryError(f"Not a directory: {path}")
        cache_key = self._cache_key(path, options)
        if use_cache:
            cached = self._get_cached(cache_key, cache_ttl)
            if cached:
                return cached
        async with self._lock:
            if self.nim_available:
                result = await self._scan_nim(path, options)
            else:
                result = await self._scan_python(path, options)
        self._set_cached(cache_key, result)

        return result

    def scan(
        self,
        path: Union[str, Path],
        options: Optional[ScanOptions] = None,
        use_cache: bool = True,
    ) -> ScanResult:
        """
        Synchronously scan a directory.

        For TUI/async contexts, prefer scan_async().
        Creates a new event loop if called from a thread without one.
        """
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                import concurrent.futures

                with concurrent.futures.ThreadPoolExecutor() as executor:
                    future = executor.submit(
                        lambda: asyncio.run(self.scan_async(path, options, use_cache))
                    )
                    return future.result()
            else:
                return loop.run_until_complete(
                    self.scan_async(path, options, use_cache)
                )
        except RuntimeError:
            return asyncio.run(self.scan_async(path, options, use_cache))

    async def _scan_nim(self, path: Path, options: ScanOptions) -> ScanResult:
        """Scan using Nim binary."""
        nim_path = _get_nim_binary_path()
        cmd = [str(nim_path), str(path), "--json"]

        if not options.include_preview:
            cmd.append("--no-preview")
        if options.max_depth > 0:
            cmd.append(f"--max-depth={options.max_depth}")
        if options.include_hidden:
            cmd.append("--include-hidden")
        if not options.respect_gitignore:
            cmd.append("--no-gitignore")
        if options.max_file_size > 0:
            cmd.append(f"--max-size={options.max_file_size}")

        try:
            result = await asyncio.to_thread(
                run_nim_process,
                cmd,
                cwd=PROJECT_ROOT,
                timeout=60.0,
                max_output_bytes=4 * 1024 * 1024,
            )

            if result.timed_out:
                logger.warning("Nim scanner timed out, falling back to Python")
                return await self._scan_python(path, options)
            if result.output_limited:
                logger.warning(
                    "Nim scanner output exceeded limit, falling back to Python"
                )
                return await self._scan_python(path, options)
            if result.returncode != 0:
                logger.warning(
                    "Nim scanner failed with code %s, falling back to Python",
                    result.returncode,
                )
                return await self._scan_python(path, options)

            data = json.loads(result.stdout.decode("utf-8"))
            if not isinstance(data, dict):
                raise ValueError("Nim scanner output must be a JSON object")
            files_data = data.get("files", [])
            recent_data = data.get("recently_modified", [])
            if not isinstance(files_data, list) or not isinstance(recent_data, list):
                raise ValueError("Nim scanner file lists are invalid")
            files = [FileInfo(**item) for item in files_data if isinstance(item, dict)]
            recently_modified = [
                FileInfo(**item) for item in recent_data if isinstance(item, dict)
            ]

            return ScanResult(
                root_path=str(path),
                total_files=int(data.get("total_files", 0)),
                total_directories=int(data.get("total_directories", 0)),
                total_lines=int(data.get("total_lines", 0)),
                total_size=int(data.get("total_size", 0)),
                scan_duration_ms=int(data.get("scan_duration_ms", 0)),
                files=files,
                by_category=data.get("by_category", {})
                if isinstance(data.get("by_category", {}), dict)
                else {},
                by_extension=data.get("by_extension", {})
                if isinstance(data.get("by_extension", {}), dict)
                else {},
                recently_modified=recently_modified,
            )

        except (OSError, ValueError, json.JSONDecodeError) as e:
            logger.warning(f"Nim scanner error: {e}, falling back to Python")
            return await self._scan_python(path, options)

    async def _scan_python(self, path: Path, options: ScanOptions) -> ScanResult:
        """Scan using pure Python (fallback)."""
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        return await loop.run_in_executor(None, PurePythonScanner.scan, path, options)


_scanner: Optional[ImaginationScanner] = None


def get_imagination_scanner() -> ImaginationScanner:
    """Get the global ImaginationScanner instance."""
    global _scanner
    if _scanner is None:
        _scanner = ImaginationScanner()
    return _scanner


async def scan_filesystem(
    path: str = ".",
    include_preview: bool = True,
    max_depth: int = 0,
    include_hidden: bool = False,
) -> Dict[str, Any]:
    """
    Scan a directory and return structured information about all files.

    This is an ultra-fast filesystem scanner that provides comprehensive
    information about project structure, file categories, and recent changes.

    Args:
        path: Directory path to scan (default: current directory)
        include_preview: Include first few lines of each file
        max_depth: Maximum directory depth (0 = unlimited)
        include_hidden: Include hidden files and directories

    Returns:
        Dictionary with scan results including:
        - total_files: Total number of files
        - total_lines: Total lines of code
        - total_size: Total size in bytes
        - by_category: File counts by category (code, config, doc, etc.)
        - by_extension: File counts by extension
        - recently_modified: Files modified in last 24 hours
        - files: List of all file information
    """
    scanner = get_imagination_scanner()
    options = ScanOptions(
        include_preview=include_preview,
        max_depth=max_depth,
        include_hidden=include_hidden,
    )

    result = await scanner.scan_async(path, options)
    return result.model_dump()


def scan_filesystem_sync(path: str = ".") -> Dict[str, Any]:
    """Synchronous version of scan_filesystem for non-async contexts."""
    scanner = get_imagination_scanner()
    result = scanner.scan(path)
    return result.model_dump()


async def get_project_summary(path: str = ".") -> str:
    """
    Get a human-readable summary of a project's structure.

    Returns a formatted string describing the project's files,
    categories, and recent activity.
    """
    scanner = get_imagination_scanner()
    result = await scanner.scan_async(path)

    lines = [
        f"📁 Project: {result.root_path}",
        "",
        "📊 Statistics:",
        f"   Files: {result.total_files:,}",
        f"   Directories: {result.total_directories:,}",
        f"   Lines of Code: {result.total_lines:,}",
        f"   Total Size: {result.total_size_human}",
        f"   Scan Time: {result.scan_duration_ms}ms",
        "",
        "📚 By Category:",
    ]

    for cat, count in sorted(result.by_category.items(), key=lambda x: -x[1]):
        if count > 0:
            lines.append(f"   {cat}: {count}")

    lines.append("")
    lines.append("🔥 Top Extensions:")

    top_exts = sorted(result.by_extension.items(), key=lambda x: -x[1])[:10]
    for ext, count in top_exts:
        lines.append(f"   {ext}: {count}")

    if result.recently_modified:
        lines.append("")
        lines.append("⏰ Recently Modified:")
        for f in result.recently_modified[:5]:
            lines.append(f"   {f.path} ({f.age_human})")

    return "\n".join(lines)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Imagination Engine - Filesystem Scanner"
    )
    parser.add_argument("path", nargs="?", default=".", help="Path to scan")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    parser.add_argument("--no-preview", action="store_true", help="Skip file previews")
    args = parser.parse_args()

    async def main():
        """Main entry point."""
        scanner = get_imagination_scanner()
        options = ScanOptions(include_preview=not args.no_preview)
        result = await scanner.scan_async(args.path, options)

        if args.json:
            print(json.dumps(result.model_dump(), indent=2))
        else:
            print(await get_project_summary(args.path))

    asyncio.run(main())
