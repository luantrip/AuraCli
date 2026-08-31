"""Low-level memory manager using shared memory and FFI for cross-process state."""

import ctypes
import os
import tempfile

from aura_cli.core.logger import get_logger

logger = get_logger(__name__)
from datetime import datetime
import json
from pathlib import Path
import platform
import re
import threading
from typing import Any, Dict, List, Optional

from aura_cli.core.context.imagination_manager import (
    ImaginationManager as ImaginationBridge,
)
from aura_cli.core.nim_runtime import (
    build_nim_candidates,
    nim_library_filename,
    resolve_nim_library,
)

if platform.system() == "Windows":
    LIB_EXT = ".dll"
elif platform.system() == "Darwin":
    LIB_EXT = ".dylib"
else:
    LIB_EXT = ".so"
LIB_NAME = nim_library_filename("notebook")
MAX_PAGE_LINES = 1000

_NOTEBOOK_SYMBOLS = {
    "notebookGetVersion": ([], ctypes.c_char_p),
    "notebookInit": ([ctypes.c_char_p], ctypes.c_int),
    "notebookWritePage": ([ctypes.c_char_p, ctypes.c_char_p], ctypes.c_int),
    "notebookReadPage": ([ctypes.c_char_p], ctypes.c_char_p),
    "notebookListPages": ([ctypes.c_char_p], ctypes.c_char_p),
    "notebookGetPageCount": ([ctypes.c_char_p], ctypes.c_int),
    "notebookUpdateIndex": ([ctypes.c_char_p, ctypes.c_char_p], ctypes.c_int),
    "notebookReadIndex": ([ctypes.c_char_p], ctypes.c_char_p),
    "notebookDeletePage": ([ctypes.c_char_p], ctypes.c_int),
    "notebookGetSessionInfo": ([ctypes.c_char_p], ctypes.c_char_p),
}

_nim_lib: Optional[ctypes.CDLL] = None
_nim_lib_lock = threading.Lock()
_nim_access_lock = threading.Lock()
_nim_lib_configured = False


def _nim_is_safe_for_current_thread() -> bool:
    """Return whether the Nim FFI may be called from the current thread.

    The shared library is loaded by ctypes, while worker threads are created
    by Python. Nim's runtime/GC is initialized for the loading thread but is
    not safe to enter from arbitrary foreign Python threads. Those callers use
    the equivalent pure-Python implementation instead.
    """
    return threading.current_thread() is threading.main_thread()


def _configure_nim_library(lib: ctypes.CDLL) -> None:
    """Configure and validate the complete Notebook FFI ABI."""
    try:
        for name, (argtypes, restype) in _NOTEBOOK_SYMBOLS.items():
            function = getattr(lib, name)
            function.argtypes = argtypes
            function.restype = restype
    except (AttributeError, TypeError) as exc:
        raise OSError(f"Notebook FFI ABI incompleto: {exc}") from exc


def _get_nim_library() -> Optional[ctypes.CDLL]:
    """Load and return the Nim shared library, or None if unavailable."""
    global _nim_lib, _nim_lib_configured

    if not _nim_is_safe_for_current_thread():
        return None

    if _nim_lib_configured:
        return _nim_lib  # may be None if not found

    with _nim_lib_lock:
        if _nim_lib_configured:
            return _nim_lib

        default_library_path = Path(__file__).parent / LIB_NAME
        lib_path = resolve_nim_library(
            LIB_NAME, extra_candidates=[default_library_path]
        )

        if lib_path is None:
            searched = ", ".join(
                str(p) for p in build_nim_candidates(LIB_NAME, [default_library_path])
            )
            logger.warning(
                f"Biblioteca Nim notebook não encontrada (procurado em: {searched}). "
                "Usando fallback Python puro para operações de memória. "
                "Execute ./scripts/build_nim.sh para compilar os binários."
            )
            _nim_lib_configured = True
            return None

        try:
            loaded = ctypes.CDLL(str(lib_path))
            _configure_nim_library(loaded)
        except (OSError, AttributeError, TypeError) as exc:
            logger.warning(
                "Biblioteca Nim notebook rejeitada por ABI/carga (%s). Usando fallback Python.",
                exc,
            )
            _nim_lib = None
            _nim_lib_configured = True
            return None

        _nim_lib = loaded
        _nim_lib_configured = True
        return _nim_lib


def _resolve_manager_path(base_path: Path, *parts: str) -> Path:
    """Resolve manager components below the configured memory root."""
    base = base_path.expanduser().resolve()
    resolved = base
    for raw_part in parts:
        raw = os.fspath(raw_part)
        if "\x00" in raw:
            raise ValueError("Notebook path contains null bytes")
        part = Path(raw)
        if part.is_absolute() or ".." in part.parts:
            raise ValueError("Notebook path must remain below the memory root")
        resolved = resolved / part
    resolved = resolved.resolve(strict=False)
    try:
        resolved.relative_to(base)
    except ValueError as exc:
        raise ValueError("Notebook path resolves outside the memory root") from exc
    return resolved


class NotebookManager:
    """Notebook manager backed by the Nim library with Python fallback."""

    def __init__(self, base_path: str):
        """Initialize the instance. Uses Python fallback if Nim lib unavailable."""
        self.lib = _get_nim_library() if _nim_is_safe_for_current_thread() else None
        self.base_path = Path(base_path).expanduser().resolve()
        self.base_path.mkdir(parents=True, exist_ok=True)
        if self.lib is not None:
            with _nim_access_lock:
                result = self.lib.notebookInit(self._c_str(str(self.base_path)))
            if result != 0:
                logger.warning("Nim notebookInit falhou; usando fallback Python.")
                self.lib = None

    # Python fallback helpers (used when self.lib is None)

    def _fallback_write(self, full_path: Path, content: str) -> bool:
        """Escreve arquivo diretamente (fallback sem Nim)."""
        temporary_path: Optional[Path] = None
        try:
            full_path.parent.mkdir(parents=True, exist_ok=True)
            descriptor, temporary_name = tempfile.mkstemp(
                prefix=f".{full_path.name}.", suffix=".tmp", dir=full_path.parent
            )
            temporary_path = Path(temporary_name)
            with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
                handle.write(content)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary_path, full_path)
            temporary_path = None
            return True
        except Exception as e:
            logger.error(f"Fallback write error {full_path}: {e}")
            return False
        finally:
            if temporary_path is not None:
                temporary_path.unlink(missing_ok=True)

    def _fallback_read(self, full_path: Path) -> Optional[str]:
        """Read arquivo diretamente (fallback sem Nim)"""
        try:
            if full_path.exists():
                content = full_path.read_text(encoding="utf-8")
                return content if content else None
            return None
        except Exception as e:
            logger.error(f"Fallback read error {full_path}: {e}")
            return None

    @staticmethod
    def _c_str(py_str: str) -> bytes:
        """Convert a Python string to a C-compatible bytes string."""
        return py_str.encode("utf-8")

    @staticmethod
    def _py_str(c_str) -> str:
        """Convert C bytes to a Python string."""
        if c_str is None:
            return ""
        try:
            if isinstance(c_str, bytes):
                return c_str.decode("utf-8")
            elif isinstance(c_str, str):
                return c_str
            else:
                return str(c_str)
        except (UnicodeDecodeError, AttributeError):
            return ""

    def create_page_name(self, title: str) -> str:
        """Generate a unique page name for a notebook entry."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        slug = re.sub(r"[^a-z0-9_]+", "", title.lower().replace(" ", "_"))
        slug = slug[:50]
        return f"{timestamp}_{slug}.txt"

    def get_version(self) -> str:
        """Return the current notebook version string."""
        if self.lib is None or not _nim_is_safe_for_current_thread():
            return "python-fallback"
        with _nim_access_lock:
            return self._py_str(self.lib.notebookGetVersion())

    def write_page(self, session_path: str, page_name: str, content: str) -> bool:
        """Write content to a notebook page."""
        if len(content.splitlines()) > MAX_PAGE_LINES:
            logger.warning(
                "Notebook write rejeitado: limite de %s linhas", MAX_PAGE_LINES
            )
            return False
        try:
            full_path = _resolve_manager_path(self.base_path, session_path, page_name)
        except ValueError as exc:
            logger.warning("Notebook write bloqueado: %s", exc)
            return False
        if self.lib is None or not _nim_is_safe_for_current_thread():
            return self._fallback_write(full_path, content)
        with _nim_access_lock:
            return (
                self.lib.notebookWritePage(
                    self._c_str(str(full_path)), self._c_str(content)
                )
                == 0
            )

    def read_page(self, session_path: str, page_name: str) -> Optional[str]:
        """Read content from a notebook page."""
        try:
            full_path = _resolve_manager_path(self.base_path, session_path, page_name)
        except ValueError as exc:
            logger.warning("Notebook read bloqueado: %s", exc)
            return None
        if self.lib is None or not _nim_is_safe_for_current_thread():
            return self._fallback_read(full_path)
        with _nim_access_lock:
            result = self._py_str(
                self.lib.notebookReadPage(self._c_str(str(full_path)))
            )
            if result.startswith("ERRO:"):
                if "não encontrada" not in result.lower():
                    logger.warning(f"Erro no NotebookManager: {result}")
                return None
            return result

    def list_pages(self, session_path: str) -> List[str]:
        """List all notebook pages for the current session."""
        try:
            dir_path = _resolve_manager_path(self.base_path, session_path)
        except ValueError as exc:
            logger.warning("Notebook list bloqueado: %s", exc)
            return []
        if self.lib is None or not _nim_is_safe_for_current_thread():
            try:
                if dir_path.exists():
                    return [
                        f.name
                        for f in dir_path.iterdir()
                        if f.is_file() and f.name.endswith(".txt")
                    ]
                return []
            except Exception:
                return []
        with _nim_access_lock:
            json_str = self._py_str(
                self.lib.notebookListPages(self._c_str(str(dir_path)))
            )
            try:
                payload = json.loads(json_str)
                return (
                    payload
                    if isinstance(payload, list)
                    and all(isinstance(item, str) for item in payload)
                    else []
                )
            except json.JSONDecodeError:
                logger.warning("Notebook list_pages returned invalid JSON")
                return []

    def get_session_info(self, session_path: str) -> Dict[str, Any]:
        """Return session metadata as a dict."""
        try:
            dir_path = _resolve_manager_path(self.base_path, session_path)
        except ValueError as exc:
            logger.warning("Notebook session info bloqueado: %s", exc)
            return {
                "session": session_path,
                "pages": [],
                "backend": "rejected",
                "exists": False,
                "page_count": 0,
                "total_size_bytes": 0,
            }
        if self.lib is None or not _nim_is_safe_for_current_thread():
            page_paths: List[Path] = []
            try:
                if dir_path.exists():
                    page_paths = [
                        path
                        for path in dir_path.iterdir()
                        if path.is_file() and path.suffix == ".txt"
                    ]
            except OSError:
                pass
            total_size = sum(path.stat().st_size for path in page_paths)
            return {
                "session": session_path,
                "pages": [path.name for path in page_paths],
                "backend": "python-fallback",
                "exists": dir_path.exists(),
                "page_count": len(page_paths),
                "total_size_bytes": total_size,
                "session_id": dir_path.name,
                "session_path": str(dir_path),
            }
        with _nim_access_lock:
            json_str = self._py_str(
                self.lib.notebookGetSessionInfo(self._c_str(str(dir_path)))
            )
            try:
                payload = json.loads(json_str)
            except json.JSONDecodeError:
                logger.warning("Notebook session info returned invalid JSON")
                return {
                    "session": session_path,
                    "pages": [],
                    "backend": "invalid",
                    "exists": False,
                    "page_count": 0,
                    "total_size_bytes": 0,
                }
            if isinstance(payload, dict):
                payload.setdefault("session", session_path)
                payload.setdefault("pages", [])
                payload.setdefault("backend", "nim")
                payload.setdefault("session_id", dir_path.name)
                payload.setdefault("session_path", str(dir_path))
                return payload
            return {
                "session": session_path,
                "pages": [],
                "backend": "invalid",
                "exists": False,
                "page_count": 0,
                "total_size_bytes": 0,
            }


class ImaginationManager:
    """Compatibility adapter for the Imagination bridge."""

    def __init__(self, project_root: Path):
        """Initialize the instance."""
        self.project_root = project_root
        self._bridge = ImaginationBridge(project_root)
        self.executable_path = self._bridge.executable_path
        self.available = self._bridge.available
        self.last_error = self._bridge.last_error

    def _sync_bridge_state(self) -> None:
        """Synchronize bridge state with the underlying store."""
        self.executable_path = self._bridge.executable_path
        self.available = self._bridge.available
        self.last_error = self._bridge.last_error

    def scan(
        self,
        target_path: str,
        no_preview: bool = True,
        context_keywords: Optional[List[str]] = None,
        limit: int = 5,
    ) -> Optional[Dict[str, Any]]:
        """Scan the workspace and return a structured index."""
        result = self._bridge.scan(
            target_path=target_path,
            no_preview=no_preview,
            context_keywords=context_keywords,
            limit=limit,
        )
        self._sync_bridge_state()
        return result

    def get_relevant_context(
        self, target_path: str, user_prompt: str, limit: int = 5
    ) -> Optional[str]:
        """Return context snippets relevant to a query."""
        words = re.findall(r"\b\w{4,}\b", user_prompt.lower())
        stop_words = {
            "this",
            "that",
            "with",
            "from",
            "have",
            "will",
            "would",
            "should",
            "could",
        }
        keywords = [w for w in words if w not in stop_words][:10]

        if not keywords:
            return None

        result = self.scan(
            target_path, no_preview=True, context_keywords=keywords, limit=limit
        )

        if not result or "relevant_pages" not in result:
            return None

        relevant_pages = result.get("relevant_pages", [])
        if not relevant_pages:
            return None

        context_parts = [
            f"**Contexto Relevante do Projeto ({len(relevant_pages)} arquivos):**\n"
        ]

        for page in relevant_pages:
            file_path = page.get("path", "")
            score = page.get("relevance_score", 0)
            snippet = page.get("content_snippet", "")

            context_parts.append(f"\n**{file_path}** (relevância: {score}%)")
            if snippet:
                context_parts.append(f"```\n{snippet}\n```")

        return "\n".join(context_parts)


if __name__ == "__main__":
    project_root = Path(__file__).parent.parent.parent.parent
    memory_root = project_root / "memory"

    print(f"Raiz da memória: {memory_root}")

    try:
        constitution_manager = NotebookManager(str(memory_root / "notebook"))
        print(f"Versão da Lib: {constitution_manager.get_version()}")

        rule_content = "O projeto deve usar a biblioteca 'requests' para chamadas HTTP."
        constitution_manager.write_page(
            "main_constitution", "regra_http.txt", rule_content
        )

        read_rule = constitution_manager.read_page(
            "main_constitution", "regra_http.txt"
        )
        print(f"Regra lida: {read_rule}")

        pages = constitution_manager.list_pages("main_constitution")
        print(f"Páginas da Constituição: {pages}")

    except FileNotFoundError as e:
        print(e)
    except Exception as e:
        print(f"Um erro ocorreu: {e}")
