"""Notebook service — Python bridge for the Nim notebook library.

Stores conversation context as discrete pages under
.aura/notebooks/<session>/pagina_NNN.txt with an auto-generated index.md.
Uses the same Nim library singleton as memory_manager.py to avoid multiple
Nim-runtime loads. Falls back to pure Python when the library is unavailable.

On-disk layout:
    .aura/notebooks/
    └── YYYYMMDD_HHMMSS/          ← one dir per session
        ├── index.md
        ├── pagina_001.txt
        └── ...
"""

import ctypes
from datetime import datetime
import json
import os
from pathlib import Path
import tempfile
import threading
from typing import Any, Dict, List, Optional

from aura_cli.core.logger import get_logger
from aura_cli.core.memory.memory_manager import (
    _get_nim_library,
    _nim_is_safe_for_current_thread,
)

logger = get_logger(__name__)
MAX_PAGE_LINES = 1000


def _atomic_write_text(path: Path, content: str) -> None:
    """Replace a UTF-8 text file atomically within its parent directory."""
    temporary_path: Optional[Path] = None
    file_descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{path.name}.", suffix=".tmp", dir=path.parent
    )
    temporary_path = Path(temporary_name)
    try:
        with os.fdopen(file_descriptor, "w", encoding="utf-8") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary_path, path)
        temporary_path = None
    finally:
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)


def _resolve_contained_path(base_path: Path, raw_path: str | Path) -> Path:
    """Resolve a notebook path and require containment below ``base_path``."""
    raw = os.fspath(raw_path)
    if "\x00" in raw:
        raise ValueError("Notebook path contains null bytes")
    base = base_path.expanduser().resolve()
    candidate = Path(raw).expanduser()
    if ".." in candidate.parts:
        raise ValueError("Notebook path contains traversal components")
    if candidate.is_absolute():
        resolved = candidate.resolve(strict=False)
    elif candidate.parts and candidate.parts[0] == ".aura":
        project_root = base.parent.parent
        resolved = (project_root / candidate).resolve(strict=False)
    else:
        resolved = (base / candidate).resolve(strict=False)
    try:
        resolved.relative_to(base)
    except ValueError as exc:
        raise ValueError(
            "Notebook path resolves outside the notebook workspace"
        ) from exc
    if resolved == base:
        raise ValueError(
            "Notebook path must identify a file below the notebook workspace"
        )
    return resolved


class NotebookService:
    """
    Singleton service for managing the agent's notebook memory.

    The notebook is a collection of text "pages" storing conversation
    context snapshots, allowing the agent to maintain long-term memory
    without exceeding the LLM's context window.

    IMPORTANT: This service uses the SAME Nim library singleton as
    NotebookManager to avoid SIGSEGV from loading Nim runtime multiple times.

    Attributes:
        base_path: Root directory for all notebooks
        session_id: Current session identifier
        session_path: Path to current session's notebook
        page_counter: Current page number in session
    """

    _instance: Optional["NotebookService"] = None

    def __new__(cls, *args, **kwargs):
        """Enforce singleton pattern — only one NotebookService instance exists."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self, base_path: Optional[Path] = None):
        """
        Initialize the notebook service.

        Args:
            base_path: Base directory for storing notebooks.
                      Default: .aura/notebooks in current directory
        """
        if hasattr(self, "_initialized") and self._initialized:  # type: ignore[has-type]
            return

        from aura_cli.core.paths import ArtifactLayout

        self.base_path = (
            Path(base_path)
            if base_path is not None
            else ArtifactLayout().project("notebooks")
        ).resolve()
        self.session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.session_path = self.base_path / self.session_id
        self.page_counter = 0
        # Initialize before any worker thread can call write_page().
        self._page_counter_lock = threading.Lock()
        self._nim_state_lock = threading.Lock()
        self._lib = self._get_shared_library()
        self._nim_enabled = self._lib is not None
        self._initialized = True
        logger.info(f"NotebookService initialized: {self.session_path}")

    def _get_shared_library(self) -> Optional[ctypes.CDLL]:
        """Get the shared Nim library singleton.

        Uses the same library instance as NotebookManager to avoid
        loading the Nim runtime multiple times, which causes SIGSEGV.

        Returns:
            ctypes.CDLL instance or None if not available
        """
        try:
            # Do not load Nim from a foreign Python worker thread.
            if not _nim_is_safe_for_current_thread():
                return None
            lib = _get_nim_library()
            if lib is not None:
                logger.info("NotebookService using shared Nim library singleton")
            return lib
        except FileNotFoundError:
            logger.warning(
                "Nim notebook library not found. "
                "Using Python fallback implementation. "
                "Compile the Nim notebook module and check 'nim_binary_path' in settings."
            )
        except Exception as e:
            logger.error(f"Error loading shared Nim library: {e}")

        return None

    def _use_nim(self) -> bool:
        """Return whether this service may enter the Nim runtime safely.

        If a worker thread touches the service, permanently switch this
        instance to the Python implementation. This avoids re-entering Nim's
        runtime from a foreign thread and then switching back to Nim later.
        """
        with self._nim_state_lock:
            if not _nim_is_safe_for_current_thread():
                self._nim_enabled = False
            return self._nim_enabled

    def _nim(self) -> ctypes.CDLL:
        """Return the loaded library after the caller selected the Nim path."""
        if self._lib is None:
            raise RuntimeError("Nim notebook library is not available")
        return self._lib

    def _init_directory(self) -> None:
        """Initialize the notebook directory structure."""
        try:
            self.session_path.mkdir(parents=True, exist_ok=True)

            if self._use_nim():
                from aura_cli.core.memory.memory_manager import _nim_access_lock

                with _nim_access_lock:
                    result = self._nim().notebookInit(
                        str(self.session_path).encode("utf-8")
                    )
                if result != 0:
                    raise OSError(
                        f"Failed to initialize notebook session: {self.session_path}"
                    )
        except Exception as e:
            logger.error(f"Error creating notebook directory: {e}")
            raise

    def _get_next_page_path(self) -> Path:
        """Get the path for the next page."""
        with self._page_counter_lock:
            self.page_counter += 1
            return self.session_path / f"pagina_{self.page_counter:03d}.txt"

    def write_page(
        self, content: str, summary: Optional[str] = None, auto_backup: bool = True
    ) -> str:
        """
        Write a new page to the notebook.

        Args:
            content: Text content for the page
            summary: Optional summary for the index

        Returns:
            Path to the created page

        Raises:
            IOError: If writing fails
        """
        from aura_cli.core.memory.memory_manager import _nim_access_lock

        MAX_PAGE_SIZE = 10 * 1024 * 1024  # 10MB limit
        content_bytes = content.encode("utf-8")

        if len(content_bytes) > MAX_PAGE_SIZE:
            raise ValueError(
                f"Page too large: {len(content_bytes)} bytes (max: {MAX_PAGE_SIZE} bytes)"
            )

        if len(content.splitlines()) > MAX_PAGE_LINES:
            raise ValueError(f"Page exceeds the {MAX_PAGE_LINES}-line limit")

        page_path = self._get_next_page_path()

        try:
            page_path.parent.mkdir(parents=True, exist_ok=True)
            self._init_directory()
            if not content.strip():
                raise ValueError("Empty notebook pages are not allowed")
            if self._use_nim():
                # Use Nim library with thread-safety lock
                with _nim_access_lock:
                    result = self._nim().notebookWritePage(
                        str(page_path).encode("utf-8"), content.encode("utf-8")
                    )
                if result != 0:
                    raise OSError(f"Failed to write page: {page_path}")
            else:
                page_path.parent.mkdir(parents=True, exist_ok=True)
                _atomic_write_text(page_path, content)

            self._update_index(page_path, summary or f"Page {self.page_counter}")
            self._save_page_checksum(str(page_path), content)
            if auto_backup:
                self._check_and_backup()

            logger.info(f"Page written: {page_path}")
            return str(page_path)
        except Exception:
            if page_path.exists():
                try:
                    page_path.unlink()
                except Exception as _e:
                    logger.debug(f"Ignored cleanup error: {_e}")
            raise

    def _check_and_backup(self) -> None:
        """Return True if a backup is needed and create it if so."""
        try:
            from aura_cli.core.memory.notebook_backup import get_backup_manager

            backup_manager = get_backup_manager(self.session_path)
            current_count = self.get_page_count()

            if backup_manager.should_backup(current_count):
                backup_path = backup_manager.create_backup(self.session_id)
                if backup_path:
                    logger.info(f"Auto-backup created: {backup_path}")
        except Exception as e:
            logger.warning(f"Error creating auto-backup: {e}")

    def _save_page_checksum(self, page_path: str, content: str) -> None:
        """Save the checksum for a page."""
        try:
            from aura_cli.core.memory.notebook_checksum import get_checksum_manager

            checksum_manager = get_checksum_manager(self.session_path)
            checksum = checksum_manager.calculate_checksum(content)
            checksum_manager.save_checksum(page_path, checksum)
        except Exception as e:
            logger.error(f"Error saving page checksum: {e}")
            raise OSError(f"Failed to save page checksum: {page_path}") from e

    def _verify_page_checksum(self, page_path: str, content: str) -> bool:
        """Verify the checksum for a page."""
        try:
            from aura_cli.core.memory.notebook_checksum import get_checksum_manager

            checksum_manager = get_checksum_manager(self.session_path)
            return checksum_manager.verify_page(
                str(_resolve_contained_path(self.base_path, page_path)), content
            )
        except Exception as e:
            logger.error(f"Error verifying page checksum: {e}")
            return False

    def _try_recover_from_backup(self, page_path: str) -> Optional[str]:
        """Attempt to recover a page from backup."""
        try:
            from aura_cli.core.memory.notebook_backup import get_backup_manager

            backup_manager = get_backup_manager(self.session_path)
            backups = backup_manager.list_backups()

            if not backups:
                return None

            latest_backup = backups[0]
            page_name = Path(page_path).name
            import tarfile

            with tarfile.open(latest_backup["backup_path"], "r:gz") as tar:
                try:
                    member = tar.getmember(f"{self.session_id}/{page_name}")
                    extracted = tar.extractfile(member)
                    if extracted:
                        return extracted.read().decode("utf-8")
                except KeyError:
                    logger.warning(f"Page {page_name} not found in backup")

            return None
        except Exception as e:
            logger.warning(f"Error attempting backup recovery: {e}")
            return None

    def read_page(self, page_path: str, verify_integrity: bool = True) -> str:
        """
        Read content from a notebook page.

        Args:
            page_path: Path to the page file

        Returns:
            Page content as string
        """
        from aura_cli.core.memory.memory_manager import _nim_access_lock

        try:
            safe_page_path = _resolve_contained_path(self.base_path, page_path)
        except ValueError as exc:
            return f"ERRO: {exc}"

        if self._use_nim():
            with _nim_access_lock:
                result = self._nim().notebookReadPage(
                    str(safe_page_path).encode("utf-8")
                )
            content = result.decode("utf-8") if result else ""
            if content.startswith("ERRO:"):
                logger.warning(content)
        else:
            try:
                content = safe_page_path.read_text(encoding="utf-8")
            except FileNotFoundError:
                return f"ERROR: Page not found: {safe_page_path}"
            except Exception as e:
                return f"ERRO: {e}"

        if (
            verify_integrity
            and content
            and not content.startswith("ERRO:")
            and not self._verify_page_checksum(str(safe_page_path), content)
        ):
            logger.warning(
                f"Page integrity check failed for {page_path} — possible corruption"
            )
            recovered = self._try_recover_from_backup(str(safe_page_path))
            if recovered:
                content = recovered
        return content

    def list_pages(self) -> List[str]:
        """
        List all pages in the current session.

        Returns:
            List of page filenames
        """
        from aura_cli.core.memory.memory_manager import _nim_access_lock

        if self._use_nim():
            with _nim_access_lock:
                result = self._nim().notebookListPages(
                    str(self.session_path).encode("utf-8")
                )
            pages_json = result.decode("utf-8") if result else "[]"
            try:
                payload = json.loads(pages_json)
                return (
                    payload
                    if isinstance(payload, list)
                    and all(isinstance(item, str) for item in payload)
                    else []
                )
            except json.JSONDecodeError:
                logger.warning("Resposta inválida do notebookListPages")
                return []
        else:
            return sorted([f.name for f in self.session_path.glob("pagina_*.txt")])

    def get_page_count(self) -> int:
        """
        Get the number of pages in the current session.

        Returns:
            Page count
        """
        from aura_cli.core.memory.memory_manager import _nim_access_lock

        if self._use_nim():
            with _nim_access_lock:
                return self._nim().notebookGetPageCount(
                    str(self.session_path).encode("utf-8")
                )
        else:
            return len(list(self.session_path.glob("pagina_*.txt")))

    def _update_index(self, page_path: Path, summary: str) -> None:
        """Update the index file with a new page entry."""
        from aura_cli.core.memory.memory_manager import _nim_access_lock

        index_content = self.read_index()

        new_entry = f"\n## Page {self.page_counter}\n"
        new_entry += f"- **Arquivo:** `{page_path.name}`\n"
        new_entry += f"- **Data:** {datetime.now().isoformat()}\n"
        new_entry += f"- **Resumo:** {summary}\n"

        index_content += new_entry

        if self._use_nim():
            with _nim_access_lock:
                result = self._nim().notebookUpdateIndex(
                    str(self.session_path).encode("utf-8"),
                    index_content.encode("utf-8"),
                )
                if result != 0:
                    raise OSError(f"Failed to update index: {self.session_path}")
        else:
            index_path = self.session_path / "index.md"
            _atomic_write_text(index_path, index_content)

    def read_index(self) -> str:
        """
        Read the notebook index file.

        Returns:
            Index content as Markdown string
        """
        from aura_cli.core.memory.memory_manager import _nim_access_lock

        if self._use_nim():
            with _nim_access_lock:
                result = self._nim().notebookReadIndex(
                    str(self.session_path).encode("utf-8")
                )
            content = result.decode("utf-8") if result else "# Índice do Caderno\n\n"
            if content.startswith("ERRO:"):
                logger.warning(content)
                return "# Índice do Caderno\n\n"
            return content
        else:
            index_path = self.session_path / "index.md"
            if index_path.exists():
                return index_path.read_text(encoding="utf-8")
            return "# Índice do Caderno\n\n"

    def get_session_info(self) -> Dict[str, Any]:
        """
        Get information about the current session.

        Returns:
            Dictionary with session metadata
        """
        from aura_cli.core.memory.memory_manager import _nim_access_lock

        if self._use_nim():
            with _nim_access_lock:
                result = self._nim().notebookGetSessionInfo(
                    str(self.session_path).encode("utf-8")
                )
            try:
                payload = json.loads(result.decode("utf-8"))
                if isinstance(payload, dict):
                    payload.setdefault("session_id", self.session_id)
                    payload.setdefault("session_path", str(self.session_path))
                    return payload
            except (json.JSONDecodeError, AttributeError, UnicodeDecodeError):
                logger.warning("Resposta inválida do notebookGetSessionInfo")

        pages = list(self.session_path.glob("pagina_*.txt"))
        total_size = sum(p.stat().st_size for p in pages) if pages else 0

        return {
            "exists": self.session_path.exists(),
            "page_count": len(pages),
            "total_size_bytes": total_size,
            "session_id": self.session_id,
            "session_path": str(self.session_path),
        }

    def create_snapshot(
        self,
        conversation_history: List[Dict],
        use_cognitive_refinement: bool = True,
        refinement_threshold_tokens: int = 8000,
    ) -> str:
        """
        Create a snapshot of the conversation history with optional cognitive refinement.

        This method is called by AppLoop when the context limit is reached,
        saving the current conversation state to a notebook page.

        Args:
            conversation_history: Current conversation messages
            use_cognitive_refinement: If True, uses cognitive refiner before saving
            refinement_threshold_tokens: Token threshold to trigger refinement

        Returns:
            Path to the created snapshot page
        """
        from aura_cli.core.memory.cognitive_refiner import get_cognitive_refiner

        estimated_tokens = (
            sum(len(str(msg.get("content", ""))) for msg in conversation_history) // 4
        )
        if use_cognitive_refinement and estimated_tokens > refinement_threshold_tokens:
            logger.info(
                f"Refinando contexto antes de salvar ({estimated_tokens} tokens > {refinement_threshold_tokens})"
            )
            try:
                refiner = get_cognitive_refiner()
                refined = refiner.refine_context(
                    conversation_history,
                    max_tokens=refinement_threshold_tokens,
                    mode="auto",
                )

                if refined.get("refined", True):
                    content = self._format_refined_snapshot(
                        refined, conversation_history
                    )
                    summary = (
                        refined.get("summary", "")[:100]
                        or f"Snapshot refinado ({len(conversation_history)} → {refined.get('metadata', {}).get('preserved_messages', len(conversation_history))} mensagens)"
                    )
                else:
                    content = self._format_snapshot(conversation_history)
                    summary = f"Snapshot com {len(conversation_history)} mensagens"
            except Exception as e:
                logger.warning(
                    f"Erro no refinamento cognitivo, usando snapshot padrão: {e}"
                )
                content = self._format_snapshot(conversation_history)
                summary = f"Snapshot com {len(conversation_history)} mensagens"
        else:
            content = self._format_snapshot(conversation_history)
            summary = f"Snapshot com {len(conversation_history)} mensagens"

        return self.write_page(content, summary)

    def _format_snapshot(self, conversation_history: List[Dict]) -> str:
        """Format a standard page snapshot."""
        lines = ["# Snapshot de Contexto", ""]
        lines.append(f"**Data:** {datetime.now().isoformat()}")
        lines.append(f"**Mensagens:** {len(conversation_history)}")
        lines.append(f"**Sessão:** {self.session_id}")
        lines.append("")
        lines.append("---")
        lines.append("")

        for i, msg in enumerate(conversation_history):
            role = msg.get("role", "unknown").upper()
            content = msg.get("content", "")

            if content:
                lines.append(f"### [{i + 1}] {role}")
                lines.append("")

                if len(content) > 2000:
                    content = content[:2000] + "\n\n[... truncado ...]"

                lines.append(content)
                lines.append("")

        return "\n".join(lines)

    def _format_refined_snapshot(
        self, refined: Dict[str, Any], original_history: List[Dict]
    ) -> str:
        """Formata snapshot refinado cognitivamente."""
        lines = ["# Snapshot de Contexto (Refinado Cognitivamente)", ""]
        lines.append(f"**Data:** {datetime.now().isoformat()}")
        lines.append(f"**Sessão:** {self.session_id}")
        lines.append(f"**Mensagens Originais:** {len(original_history)}")

        metadata = refined.get("metadata", {})
        if metadata.get("preserved_messages"):
            lines.append(f"**Mensagens Preservadas:** {metadata['preserved_messages']}")

        lines.append("")
        lines.append("---")
        lines.append("")

        summary = refined.get("summary", "")
        if summary:
            lines.append("## 📋 Resumo Executivo")
            lines.append("")
            lines.append(summary)
            lines.append("")
            lines.append("---")
            lines.append("")

        key_points = refined.get("key_points", [])
        if key_points:
            lines.append("## 🔑 Pontos-Chave")
            lines.append("")
            for point in key_points[:10]:
                lines.append(f"- {point}")
            lines.append("")
            lines.append("---")
            lines.append("")

        decisions = refined.get("important_decisions", [])
        if decisions:
            lines.append("## ⚖️ Key Decisions")
            lines.append("")
            for decision in decisions[:10]:
                lines.append(f"- {decision}")
            lines.append("")
            lines.append("---")
            lines.append("")

        file_refs = refined.get("file_references", [])
        if file_refs:
            lines.append("## 📁 Arquivos Referenciados")
            lines.append("")
            for file_ref in list(set(file_refs))[:20]:
                lines.append(f"- `{file_ref}`")
            lines.append("")
            lines.append("---")
            lines.append("")

        refined_content = refined.get("refined_content", "")
        if refined_content:
            lines.append("## 📝 Full Refined Content")
            lines.append("")
            lines.append(refined_content)

        return "\n".join(lines)

    def delete_page(self, page_path: str) -> bool:
        """
        Delete a notebook page.

        Args:
            page_path: Path to the page file

        Returns:
            True if successful, False otherwise
        """
        from aura_cli.core.memory.memory_manager import _nim_access_lock

        try:
            safe_page_path = _resolve_contained_path(self.base_path, page_path)
        except ValueError as exc:
            logger.warning("Notebook delete bloqueado: %s", exc)
            return False

        if self._use_nim():
            with _nim_access_lock:
                result = self._nim().notebookDeletePage(
                    str(safe_page_path).encode("utf-8")
                )
            return result == 0
        else:
            try:
                safe_page_path.unlink(missing_ok=True)
                return True
            except Exception as _e:
                logger.debug("Failed to delete notebook page %s: %s", safe_page_path, _e)
                return False

    def reset_session(self) -> None:
        """
        Start a new session, resetting page counter.

        Creates a new session directory with a fresh timestamp.
        """
        self.session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.session_path = self.base_path / self.session_id
        self.page_counter = 0
        self._init_directory()
        logger.info(f"New notebook session: {self.session_id}")


_notebook_service_instance: Optional[NotebookService] = None
_notebook_service_lock = threading.Lock()


def get_notebook_service(base_path: Optional[Path] = None) -> NotebookService:
    """Get the global NotebookService singleton.

    This function provides lazy initialization of the NotebookService,
    ensuring the Nim library is only loaded when actually needed.

    Args:
        base_path: Optional base path for notebooks

    Returns:
        The global NotebookService instance
    """
    global _notebook_service_instance
    requested_path = Path(base_path).resolve() if base_path is not None else None
    current_path = (
        _notebook_service_instance.base_path
        if _notebook_service_instance is not None
        else None
    )
    if _notebook_service_instance is None or (
        requested_path is not None and current_path != requested_path
    ):
        with _notebook_service_lock:
            current_path = (
                _notebook_service_instance.base_path
                if _notebook_service_instance is not None
                else None
            )
            if _notebook_service_instance is None or (
                requested_path is not None and current_path != requested_path
            ):
                NotebookService._instance = None
                _notebook_service_instance = NotebookService(requested_path)
    return _notebook_service_instance


def reset_notebook_service() -> None:
    """Discard notebook singleton state between runtime workspaces."""
    global _notebook_service_instance
    with _notebook_service_lock:
        _notebook_service_instance = None
        NotebookService._instance = None


class _LazyNotebookService:
    """Lazy proxy for NotebookService singleton.

    Delays creation of the actual service until first attribute access,
    avoiding Nim library loading during module import.
    """

    def __getattr__(self, name: str):
        """Proxy attribute access to the real NotebookService instance."""
        return getattr(get_notebook_service(), name)

    def __repr__(self) -> str:
        """Return a descriptive string for debugging."""
        return "<LazyNotebookService proxy>"


notebook_service = _LazyNotebookService()
