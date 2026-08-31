"""Unified memory service for Aura CLI — single source of truth for memory.

Wraps NotebookManager (Nim-backed) and NotebookService (Python) into one API.
Manages constitution, conventions, context snapshots and scratchpad rules.
Thread-safe singleton via get_memory_service().
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
import hashlib
import json
import logging
import os
from pathlib import Path
import tempfile
import threading
from typing import (
    Any,
    Dict,
    List,
    Optional,
    Tuple,
)

from aura_cli.core.logger import get_logger
from aura_cli.core.memory.constitution_validator import ConstitutionValidator
from aura_cli.core.memory.memory_manager import NotebookManager
from aura_cli.core.memory.notebook_service import NotebookService
from aura_cli.core.paths import aura_path
from aura_cli.core.patterns.error_handling import handle_exceptions

logger = get_logger(__name__)


def _default_project_root() -> Path:
    """Resolve the canonical project root used by memory defaults."""
    from aura_cli.core.tools.file_system import get_allowed_base_dir

    return Path(get_allowed_base_dir()).expanduser().resolve()


def _atomic_write_json(path: Path, data: Any, **dump_options: Any) -> None:
    """Replace a JSON file atomically within its parent directory."""
    temporary_path: Optional[Path] = None
    file_descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{path.name}.", suffix=".tmp", dir=path.parent
    )
    temporary_path = Path(temporary_name)
    try:
        with os.fdopen(file_descriptor, "w", encoding="utf-8") as handle:
            json.dump(data, handle, **dump_options)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary_path, path)
        temporary_path = None
    finally:
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)


@dataclass
class LearnedRule:
    """Represents a rule learned during agent execution."""

    rule: str
    context: str = ""
    learned_at: str = field(default_factory=lambda: datetime.now().isoformat())
    source: str = "agi"  # agi, ops, manual

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "rule": self.rule,
            "context": self.context,
            "learned_at": self.learned_at,
            "source": self.source,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> LearnedRule:
        """Create from dictionary."""
        return cls(
            rule=data.get("rule", ""),
            context=data.get("context", ""),
            learned_at=data.get("learned_at", datetime.now().isoformat()),
            source=data.get("source", "agi"),
        )


class MemoryService:
    """Unified memory service — single source of truth for all memory ops.

    Wraps NotebookManager (Nim-backed) and NotebookService (Python) into
    one API covering constitution, conventions, context snapshots, scratchpad
    rules and session-based memory. Thread-safe singleton via
    get_memory_service().

    Memory layout::

        memory/
        ├── notebook/
        │   ├── constitution.md
        │   └── conventions.md
        ├── scratchpad/rules.json
        └── sessions/[snapshots]
    """

    def __init__(self, project_root: Optional[Path] = None):
        """
        Initialize the unified memory service with centralized storage.

        Args:
            project_root: Project root directory (default: current directory)
        """
        resolved_root = (
            Path(project_root).expanduser().resolve()
            if project_root is not None
            else _default_project_root()
        )
        self.project_root = resolved_root
        self.central_memory_root = aura_path("project_memories")
        project_path_str = str(self.project_root)
        self.project_id = hashlib.sha1(
            project_path_str.encode("utf-8"), usedforsecurity=False
        ).hexdigest()
        self.memory_path = self.central_memory_root / self.project_id
        self._ensure_directories()
        self._notebook_manager: Optional[NotebookManager] = None
        self._notebook_service: Optional[NotebookService] = None
        self._constitution_validator: Optional[ConstitutionValidator] = None
        self._constitution_cache: Optional[str] = None
        self._constitution_loaded = False
        self._constitution_mtime: Optional[float] = None
        self._constitution_lock = threading.RLock()
        self._notebook_manager_lock = threading.Lock()
        self._notebook_service_lock = threading.Lock()

        logger.info(
            f"MemoryService initialized for project {self.project_id} at {self.memory_path}"
        )

    def _ensure_directories(self) -> None:
        """Ensure all memory directories and essential files exist."""
        dirs = [
            self.memory_path,
            self.memory_path / "notebook",
            self.memory_path / "scratchpad",
            self.memory_path / "sessions",
        ]
        for dir_path in dirs:
            dir_path.mkdir(parents=True, exist_ok=True)
        essential_files = [
            self.memory_path / "notebook" / "constitution.md",
            self.memory_path / "notebook" / "conventions.md",
            self.memory_path / "scratchpad" / "rules.json",
        ]
        for file_path in essential_files:
            if not file_path.exists():
                try:
                    if file_path.suffix == ".json":
                        file_path.write_text('{"rules": []}', encoding="utf-8")
                    else:
                        file_path.write_text("", encoding="utf-8")
                    logger.info(f"Created essential memory file: {file_path}")
                except Exception as e:
                    logger.error(
                        f"Failed to create essential memory file {file_path}: {e}"
                    )

    @property
    def notebook_manager(self) -> NotebookManager:
        """Get or create NotebookManager instance."""
        if self._notebook_manager is None:
            with self._notebook_manager_lock:
                if self._notebook_manager is None:
                    self._notebook_manager = NotebookManager(str(self.memory_path))
        return self._notebook_manager

    @property
    def notebook_service(self) -> NotebookService:
        """Get or create NotebookService instance for sessions."""
        if self._notebook_service is None:
            with self._notebook_service_lock:
                if self._notebook_service is None:
                    self._notebook_service = NotebookService(
                        base_path=self.memory_path / "sessions"
                    )
        return self._notebook_service

    @property
    def constitution_validator(self) -> Optional[ConstitutionValidator]:
        """Get constitution validator (loads constitution if needed)."""
        if self._constitution_validator is None and not self._constitution_loaded:
            constitution = self.get_constitution()
            if constitution:
                self._constitution_validator = ConstitutionValidator(constitution)
        return self._constitution_validator

    def get_constitution(self, force_reload: bool = False) -> Optional[str]:
        """
        Get project constitution.

        Args:
            force_reload: Force reload from disk (ignore cache)

        Returns:
            Constitution content or None if not found
        """
        with self._constitution_lock:
            # Check if file has changed since last load
            if not force_reload and self._constitution_loaded:
                constitution_file = self.memory_path / "notebook" / "constitution.md"
                try:
                    if constitution_file.exists():
                        current_mtime = constitution_file.stat().st_mtime
                        if self._constitution_mtime != current_mtime:
                            force_reload = True
                    elif self._constitution_cache is not None:
                        force_reload = True
                except OSError:
                    pass

            if not force_reload and self._constitution_loaded:
                return self._constitution_cache

            try:
                content = self.notebook_manager.read_page("notebook", "constitution.md")
                self._constitution_cache = content
                self._constitution_loaded = True

                # Track file mtime for cache invalidation
                constitution_file = self.memory_path / "notebook" / "constitution.md"
                try:
                    if constitution_file.exists():
                        self._constitution_mtime = constitution_file.stat().st_mtime
                except OSError:
                    pass

                if content:
                    self._constitution_validator = ConstitutionValidator(content)
                    logger.debug("Constitution loaded and validator updated")
                else:
                    logger.debug("No constitution found")

                return content
            except Exception as e:
                logger.warning(f"Error loading constitution: {e}")
                self._constitution_loaded = True
                return None

    def save_constitution(self, content: str) -> bool:
        """
        Save project constitution.

        Args:
            content: Constitution content to save

        Returns:
            True if saved successfully
        """
        try:
            result = self.notebook_manager.write_page(
                "notebook", "constitution.md", content
            )

            if result:
                with self._constitution_lock:
                    self._constitution_cache = content
                    self._constitution_loaded = True
                self._constitution_validator = ConstitutionValidator(content)
                logger.info("Constitution saved successfully")

            return result
        except Exception as e:
            logger.error(f"Error saving constitution: {e}")
            return False

    def has_constitution(self) -> bool:
        """Check if constitution exists."""
        return self.get_constitution() is not None

    def validate_prompt(self, prompt: str) -> Tuple[bool, List[str], Optional[str]]:
        """
        Validate a prompt against the constitution.

        Args:
            prompt: User prompt to validate

        Returns:
            Tuple of (is_valid, violations, sanitized_prompt)
        """
        validator = self.constitution_validator
        if validator is None:
            return True, [], None

        return validator.validate_prompt(prompt)

    def get_conventions(self) -> Optional[str]:
        """
        Get project conventions.

        Returns:
            Conventions content or None if not found
        """
        try:
            return self.notebook_manager.read_page("notebook", "conventions.md")
        except Exception as e:
            logger.warning(f"Error loading conventions: {e}")
            return None

    def save_conventions(self, content: str) -> bool:
        """
        Save project conventions.

        Args:
            content: Conventions content to save

        Returns:
            True if saved successfully
        """
        try:
            result = self.notebook_manager.write_page(
                "notebook", "conventions.md", content
            )

            if result:
                logger.info("Conventions saved successfully")

            return result
        except Exception as e:
            logger.error(f"Error saving conventions: {e}")
            return False

    @handle_exceptions(
        OSError, json.JSONDecodeError, log_level=logging.WARNING, default=[]
    )
    def get_learned_rules(self) -> List[LearnedRule]:
        """
        Get all learned rules from scratchpad.

        Returns:
            List of learned rules
        """
        rules_file = self.memory_path / "scratchpad" / "rules.json"

        if not rules_file.exists():
            return []

        with open(rules_file, encoding="utf-8") as f:
            data = json.load(f)

        return [LearnedRule.from_dict(r) for r in data.get("rules", [])]

    def add_learned_rule(
        self,
        rule: str,
        context: str = "",
        source: str = "agi",
    ) -> bool:
        """
        Add a new learned rule to scratchpad.

        Args:
            rule: The rule text
            context: Context in which the rule was learned
            source: Source of the rule (agi, ops, manual)

        Returns:
            True if added successfully
        """
        rules = self.get_learned_rules()
        if any(r.rule == rule for r in rules):
            logger.debug(f"Rule already exists: {rule[:50]}...")
            return False

        new_rule = LearnedRule(rule=rule, context=context, source=source)
        rules.append(new_rule)

        # Cap rules to prevent unbounded growth
        _MAX_RULES = 500
        if len(rules) > _MAX_RULES:
            rules = rules[-_MAX_RULES:]
            logger.warning(
                f"rules.json capped to {_MAX_RULES} entries (oldest removed)"
            )

        return self._save_learned_rules(rules)

    @handle_exceptions(OSError, log_level=logging.ERROR, default=False)
    def _save_learned_rules(self, rules: List[LearnedRule]) -> bool:
        """Save learned rules to disk."""
        rules_file = self.memory_path / "scratchpad" / "rules.json"

        data = {
            "rules": [r.to_dict() for r in rules],
            "updated_at": datetime.now().isoformat(),
        }

        _atomic_write_json(rules_file, data, indent=2, ensure_ascii=False)

        logger.debug(f"Saved {len(rules)} learned rules")
        return True

    def consolidate_rules(self) -> bool:
        """
        Consolidate learned rules into constitution.

        This should be called periodically or manually to merge
        valuable learned rules into the main constitution.

        Returns:
            True if consolidation was performed
        """
        rules = self.get_learned_rules()
        if not rules:
            logger.info("No rules to consolidate")
            return False

        constitution = self.get_constitution() or ""
        rules_section = "\n\n## Regras Aprendidas\n\n"
        for i, rule in enumerate(rules, 1):
            rules_section += f"{i}. {rule.rule}\n"
        if "## Regras Aprendidas" in constitution:
            import re

            constitution = re.sub(
                r"## Regras Aprendidas.*?(?=##|$)",
                rules_section,
                constitution,
                flags=re.DOTALL,
            )
        else:
            constitution += rules_section
        if self.save_constitution(constitution):
            self._save_learned_rules([])
            logger.info(f"Consolidated {len(rules)} rules into constitution")
            return True

        return False

    @handle_exceptions(Exception, log_level=logging.ERROR, default="")
    def create_context_snapshot(
        self,
        conversation_history: List[Dict[str, Any]],
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Create a snapshot of conversation context.

        Args:
            conversation_history: List of message dictionaries
            metadata: Optional metadata for the snapshot

        Returns:
            Snapshot ID
        """
        snapshot_id = self.notebook_service.create_snapshot(conversation_history)
        if metadata:
            meta_file = self.memory_path / "sessions" / f"{snapshot_id}_meta.json"
            _atomic_write_json(meta_file, metadata, indent=2)

        logger.debug(f"Created context snapshot: {snapshot_id}")
        return snapshot_id

    @handle_exceptions(Exception, log_level=logging.WARNING, default=None)
    def get_context_snapshot(self, snapshot_id: str) -> Optional[List[Dict[str, Any]]]:
        """
        Retrieve a context snapshot.

        Args:
            snapshot_id: Snapshot ID to retrieve

        Returns:
            Conversation history or None if not found
        """
        return self.notebook_service.get_snapshot(snapshot_id)  # type: ignore[attr-defined]

    def list_snapshots(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        List recent context snapshots for the current project.

        Args:
            limit: Maximum number of snapshots to return.

        Returns:
            List of snapshot info dictionaries for the current project.
        """
        return MemoryService.query_snapshots(project_id=self.project_id, limit=limit)

    @staticmethod
    def query_snapshots(
        project_id: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: int = 20,
    ) -> List[Dict[str, Any]]:
        """
        Query snapshots across one or all projects with date filters.

        Args:
            project_id: The specific project ID to query. If None, queries all projects.
            start_date: The start of the date range to filter snapshots.
            end_date: The end of the date range to filter snapshots.
            limit: The maximum number of snapshots to return.

        Returns:
            A list of snapshot metadata dictionaries, sorted by date descending.
        """
        central_root = aura_path("project_memories")
        if not central_root.exists():
            return []

        target_dirs = []
        if project_id:
            project_path = central_root / project_id
            if project_path.exists() and project_path.is_dir():
                target_dirs.append(project_path)
        else:
            target_dirs = [d for d in central_root.iterdir() if d.is_dir()]

        all_snapshots = []
        for proj_dir in target_dirs:
            sessions_path = proj_dir / "sessions"
            if not sessions_path.exists():
                continue

            for session_dir in sessions_path.iterdir():
                if not session_dir.is_dir():
                    continue
                try:
                    session_dt = datetime.strptime(session_dir.name, "%Y%m%d_%H%M%S")
                    if start_date and session_dt < start_date:
                        continue
                    if end_date and session_dt > end_date:
                        continue
                    snapshot_info = {
                        "project_id": proj_dir.name,
                        "session_id": session_dir.name,
                        "session_date": session_dt.isoformat(),
                        "path": str(session_dir),
                    }
                    all_snapshots.append(snapshot_info)

                except ValueError:
                    continue
        all_snapshots.sort(key=lambda x: x["session_date"], reverse=True)

        return all_snapshots[:limit]

    def get_memory_info(self) -> Dict[str, Any]:
        """
        Get information about memory storage.

        Returns:
            Dictionary with memory statistics
        """
        info = {
            "memory_path": str(self.memory_path),
            "has_constitution": self.has_constitution(),
            "has_conventions": self.get_conventions() is not None,
            "learned_rules_count": len(self.get_learned_rules()),
            "snapshots_count": len(self.list_snapshots(limit=100)),
        }
        try:
            notebook_path = self.memory_path / "notebook"
            if notebook_path.exists():
                info["notebook_size_bytes"] = sum(
                    f.stat().st_size for f in notebook_path.glob("*") if f.is_file()
                )
        except Exception as _e:
            logger.debug(f"Ignorado: {_e}")

        return info

    def clear_scratchpad(self) -> bool:
        """Clear all learned rules in scratchpad."""
        return self._save_learned_rules([])

    def reset(self) -> None:
        """Reset cached data (useful for testing)."""
        with self._constitution_lock:
            self._constitution_cache = None
            self._constitution_loaded = False
        self._constitution_validator = None
        self._notebook_manager = None
        self._notebook_service = None

    @property
    def vector_storage(self) -> Optional[Any]:
        """Get or create VectorStorage instance (lazy loaded)."""
        if not hasattr(self, "_vector_storage"):
            self._vector_storage = None

        if self._vector_storage is None:
            try:
                from aura_cli.core.memory.vector_store import create_vector_store

                storage_path = self.memory_path / "vectors"
                self._vector_storage = create_vector_store(
                    collection_name="main", persist_path=str(storage_path)
                )
            except Exception as e:
                logger.error(f"Error initializing VectorStorage: {e}")
                self._vector_storage = None

        return self._vector_storage

    def _resolve_project_file(self, raw_path: Any) -> Optional[Path]:
        """Resolve a memory source file and enforce the project boundary."""
        candidate = Path(str(raw_path)).expanduser()
        if not candidate.is_absolute():
            candidate = self.project_root / candidate
        resolved = candidate.resolve()
        try:
            resolved.relative_to(self.project_root)
        except ValueError:
            return None
        return resolved

    def remember(self, content: str, metadata: Optional[Dict[str, Any]] = None) -> bool:
        """
        Store a memory with semantic embedding.

        Args:
            content: Text content to remember
            metadata: Optional metadata (if 'file_path' is present, uses Prism chunking)

        Returns:
            True if successful
        """
        storage = self.vector_storage
        if not storage:
            return False
        try:
            metadata = dict(metadata or {})
            file_path_key = "file_path" if metadata.get("file_path") else "path"
            raw_file_path = metadata.get("file_path") or metadata.get("path")
            file_path = None
            if raw_file_path:
                file_path = self._resolve_project_file(raw_file_path)
                if file_path is None:
                    logger.warning(
                        "Memory source path is outside the project workspace"
                    )
                    return False
                metadata[file_path_key] = str(file_path)
            chunks_added = False
            if file_path and file_path.exists():
                try:
                    from aura_cli.core.memory.prism_bridge import PrismManager

                    prism = PrismManager()

                    if prism.available:
                        chunks = prism.chunk_file(str(file_path))
                        if chunks:
                            for chunk in chunks:
                                chunk_meta = metadata.copy()
                                chunk_meta.update(
                                    {
                                        "chunk_kind": chunk.kind,
                                        "chunk_name": chunk.name,
                                        "start_line": chunk.start_line,
                                        "end_line": chunk.end_line,
                                    }
                                )
                                storage.add(content=chunk.content, metadata=chunk_meta)
                            chunks_added = True
                            logger.debug(
                                f"Stored {len(chunks)} chunks using Prism for {file_path}"
                            )
                except Exception as e:
                    logger.warning(f"Prism chunking failed for {file_path}: {e}")
            if not chunks_added:
                storage.add(content=content, metadata=metadata)

            return True
        except Exception as e:
            logger.error(f"Error storing memory: {e}")
            return False

    @handle_exceptions(Exception, log_level=logging.ERROR, default=[])
    def recall(self, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        """
        Retrieve relevant memories semantically.

        Args:
            query: Search query
            limit: Max results

        Returns:
            List of relevant memory items
        """
        storage = self.vector_storage
        if not storage:
            return []

        results = storage.search(query=query, limit=limit)

        formatted_results = []
        for result in results:
            formatted_results.append(
                {
                    "content": result.content,
                    "relevance": result.score,
                    "metadata": result.metadata,
                    "created_at": result.metadata.get("timestamp"),
                }
            )

        return formatted_results


def get_memory_service(project_root: Optional[Path] = None) -> MemoryService:
    """
    Get the memory service instance for a specific project via DI container.

    This factory ensures that each project has its own separate, memoized
    MemoryService instance.

    Args:
        project_root: The root directory of the project. If None, uses CWD.

    Returns:
        A MemoryService instance specific to the given project.
    """
    try:
        from aura_cli.core.di import Services, get_container

        container = get_container()
        if container.has(Services.MEMORY_SERVICE_REGISTRY):
            registry = container.resolve(Services.MEMORY_SERVICE_REGISTRY)
            return registry.get(project_root)
    except Exception:
        pass  # DI container unavailable at import time — fall through to direct instantiation
    # Simple fallback (no globals needed — container handles thread safety)
    resolved_root = (
        Path(project_root).expanduser().resolve()
        if project_root is not None
        else _default_project_root()
    )
    return MemoryService(resolved_root)


def reset_memory_service(project_root: Optional[Path] = None) -> None:
    """
    Reset the memory instance for a specific project or all instances.

    Args:
        project_root: If specified, resets only the memory for that project.
                      If None, resets the DI registry if available.
    """
    try:
        from aura_cli.core.di import Services, get_container

        container = get_container()
        if container.has(Services.MEMORY_SERVICE_REGISTRY) and container.is_resolved(
            Services.MEMORY_SERVICE_REGISTRY
        ):
            registry = container.resolve(Services.MEMORY_SERVICE_REGISTRY)
            if project_root:
                resolved_root = Path(project_root).resolve()
                project_id = hashlib.sha1(
                    str(resolved_root).encode("utf-8"), usedforsecurity=False
                ).hexdigest()
                if project_id in registry._instances:
                    registry._instances[project_id].reset()
                    del registry._instances[project_id]
                    logger.info(f"Reset memory for project {project_id}")
            else:
                for instance in registry._instances.values():
                    instance.reset()
                registry._instances.clear()
                logger.info("Reset all memory instances.")
    except Exception as _e:
        # DI registry unavailable — nothing to reset at this level.
        logger.debug("reset_memory_service: DI registry unavailable: %s", _e)
