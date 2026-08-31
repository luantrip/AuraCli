"""
Specific Cache for Code Analysis.

This module implements a specialized cache for code analysis results,
automatically invalidating when files are modified.

Features:
    - Cache based on file mtime (modification time)
    - Automatic invalidation when file changes
    - Configurable TTL for analyses
    - Support for partial and complete analyses

Usage:
    >>> from aura_cli.core.cache.analysis_cache import get_analysis_cache
    >>> cache = get_analysis_cache()
    >>> analysis = cache.get_analysis("src/main.py")
    >>> if not analysis:
    ...     analysis = analyze_code("src/main.py")
    ...     cache.set_analysis("src/main.py", analysis)
"""

import os
from typing import Any, Dict, List, Optional

from aura_cli.core.cache_advanced.persistent_cache import PersistentCache
from aura_cli.core.logger import get_logger

logger = get_logger(__name__)


class AnalysisCache:
    """
    Specialized cache for code analysis.

    Uses file mtime as part of the key, ensuring that
    analyses are invalidated when the file is modified.
    """

    def __init__(self, ttl: int = 86400):
        """
        Initialize analysis cache.

        Args:
            ttl: Time to live in seconds (default: 24 hours)
        """
        self.cache = PersistentCache(name="analysis", max_size_mb=500, compress=True)
        self.ttl = ttl

    def _get_file_key(
        self, file_path: str, analysis_type: str = "full"
    ) -> Optional[str]:
        """Return a cache key for a file path."""
        try:
            abs_path = os.path.abspath(file_path)
            if not os.path.exists(abs_path):
                return None

            stat = os.stat(abs_path)
            mtime = stat.st_mtime
            size = stat.st_size

            return f"analysis:{analysis_type}:{abs_path}:{mtime}:{size}"
        except Exception as e:
            logger.debug(f"Error generating key for {file_path}: {e}")
            return None

    def get_analysis(
        self, file_path: str, analysis_type: str = "full"
    ) -> Optional[Dict[str, Any]]:
        """Get cached analysis for a file. Returns None if missing or stale."""
        key = self._get_file_key(file_path, analysis_type)
        if not key:
            return None

        result = self.cache.get(key)
        if result:
            logger.debug(f"Cache hit para análise de {file_path} ({analysis_type})")
        return result

    def set_analysis(
        self, file_path: str, analysis: Dict[str, Any], analysis_type: str = "full"
    ):
        """Cache an analysis result for a file."""
        key = self._get_file_key(file_path, analysis_type)
        if not key:
            logger.warning(
                f"Não foi possível cachear análise: arquivo {file_path} não existe"
            )
            return

        self.cache.set(key, analysis, ttl=self.ttl)
        logger.debug(f"Análise de {file_path} ({analysis_type}) cacheada")

    def invalidate(self, file_path: str):
        """Invalidate the cache for a specific file."""
        abs_path = os.path.abspath(file_path)

        # Find and remove all entries for this file
        keys_to_remove = []
        for key in list(self.cache.index.keys()):
            if f":{abs_path}:" in key:
                keys_to_remove.append(key)

        for key in keys_to_remove:
            self.cache.delete(key)

        if keys_to_remove:
            logger.debug(f"Invalidadas {len(keys_to_remove)} análises de {file_path}")

    def invalidate_directory(self, directory: str):
        """Invalidate all cached entries under a directory."""
        abs_dir = os.path.abspath(directory)

        keys_to_remove = []
        for key in list(self.cache.index.keys()):
            if abs_dir in key:
                keys_to_remove.append(key)

        for key in keys_to_remove:
            self.cache.delete(key)

        if keys_to_remove:
            logger.debug(f"Invalidadas {len(keys_to_remove)} análises em {directory}")

    def get_cached_files(self) -> List[str]:
        """Return a list of files with valid cache entries."""
        files = set()
        for key in self.cache.index:
            if key.startswith("analysis:"):
                parts = key.split(":")
                if len(parts) >= 3:
                    # The path is in the third part
                    file_path = parts[2]
                    files.add(file_path)

        return list(files)

    def get_stats(self) -> Dict[str, Any]:
        """Return cache statistics as a dict."""
        base_stats = self.cache.get_stats()

        # Count by analysis type
        analysis_types: dict[str, int] = {}
        for key in self.cache.index:
            if key.startswith("analysis:"):
                parts = key.split(":")
                if len(parts) >= 2:
                    atype = parts[1]
                    analysis_types[atype] = analysis_types.get(atype, 0) + 1

        return {
            **base_stats,
            "cached_files": len(self.get_cached_files()),
            "analysis_types": analysis_types,
            "ttl_hours": self.ttl / 3600,
        }


_analysis_cache: Optional[AnalysisCache] = None


def get_analysis_cache() -> AnalysisCache:
    """Return the global analysis cache singleton."""
    global _analysis_cache
    if _analysis_cache is None:
        _analysis_cache = AnalysisCache()
    return _analysis_cache
