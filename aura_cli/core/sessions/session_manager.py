"""
Persistent Session Manager for Aura CLI.

This module implements a complete session system that allows
saving and restoring application state between executions.

Features:
    - Session creation and management
    - Conversation history persistence
    - Agent and workflow state
    - Session export/import
    - Configurable auto-save

Usage:
    >>> from aura_cli.core.sessions import get_session_manager
    >>> manager = get_session_manager()
    >>> session = manager.create_session("my_project")
    >>> session.add_message("user", "Hello!")
    >>> manager.save_session(session)
"""

from dataclasses import dataclass, field
from datetime import datetime
import json
import os
from pathlib import Path
import tempfile
from typing import Any, Dict, List, Optional
import uuid

from aura_cli.core.logger import get_logger

logger = get_logger(__name__)


def _atomic_write_json(path: Path, data: Any) -> None:
    """Write JSON atomically while preserving the destination on failure."""
    temporary_path: Optional[Path] = None
    file_descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{path.name}.", suffix=".tmp", dir=path.parent
    )
    temporary_path = Path(temporary_name)
    try:
        with os.fdopen(file_descriptor, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
            f.flush()
            os.fsync(f.fileno())
        os.replace(temporary_path, path)
        temporary_path = None
    finally:
        if temporary_path is not None:
            try:
                temporary_path.unlink(missing_ok=True)
            except OSError:
                logger.debug(
                    "Não foi possível remover exportação temporária", exc_info=True
                )


@dataclass
class SessionMessage:
    """Message in a session."""

    role: str
    content: str
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Session:
    """
    Represents a work session in Aura CLI.

    A session captures all interaction state, including
    conversation history, context, agent states and more.
    """

    id: str
    name: str
    created_at: str
    updated_at: str
    conversation_history: List[Dict[str, Any]] = field(default_factory=list)
    context: Dict[str, Any] = field(default_factory=dict)
    agent_states: Dict[str, Any] = field(default_factory=dict)
    open_files: List[str] = field(default_factory=list)
    current_directory: str = field(default_factory=os.getcwd)
    model: str = ""
    tags: List[str] = field(default_factory=list)
    description: str = ""

    def add_message(self, role: str, content: str, metadata: Optional[Dict] = None):
        """Add a message to the session history."""
        self.conversation_history.append(
            {
                "role": role,
                "content": content,
                "timestamp": datetime.now().isoformat(),
                "metadata": metadata or {},
            }
        )
        self.updated_at = datetime.now().isoformat()

    def get_messages(self, limit: Optional[int] = None) -> List[Dict]:
        """Return messages, optionally limited to the last n."""
        if limit:
            return self.conversation_history[-limit:]
        return self.conversation_history

    def set_context(self, key: str, value: Any):
        """Set a context key-value pair."""
        self.context[key] = value
        self.updated_at = datetime.now().isoformat()

    def get_context(self, key: str, default: Any = None) -> Any:
        """Get a context value by key."""
        return self.context.get(key, default)

    def set_agent_state(self, agent_id: str, state: Dict):
        """Save an agent state snapshot."""
        self.agent_states[agent_id] = {
            "state": state,
            "saved_at": datetime.now().isoformat(),
        }
        self.updated_at = datetime.now().isoformat()

    def get_agent_state(self, agent_id: str) -> Optional[Dict]:
        """Get an agent state entry."""
        if agent_id in self.agent_states:
            return self.agent_states[agent_id].get("state")
        return None

    def add_open_file(self, file_path: str):
        """Add a file path to the open-files list."""
        abs_path = os.path.abspath(file_path)
        if abs_path not in self.open_files:
            self.open_files.append(abs_path)
            self.updated_at = datetime.now().isoformat()

    def remove_open_file(self, file_path: str):
        """Remove a file path from the open-files list."""
        abs_path = os.path.abspath(file_path)
        if abs_path in self.open_files:
            self.open_files.remove(abs_path)
            self.updated_at = datetime.now().isoformat()

    def add_tag(self, tag: str):
        """Add a tag to the session."""
        if tag not in self.tags:
            self.tags.append(tag)
            self.updated_at = datetime.now().isoformat()

    def to_dict(self) -> Dict:
        """Serialise session to a dict."""
        return {
            "id": self.id,
            "name": self.name,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "conversation_history": self.conversation_history,
            "context": self.context,
            "agent_states": self.agent_states,
            "open_files": self.open_files,
            "current_directory": self.current_directory,
            "model": self.model,
            "tags": self.tags,
            "description": self.description,
        }

    @classmethod
    def from_dict(
        cls, data: Dict, default_directory: Optional[str] = None
    ) -> "Session":
        """Deserialise session from a dict."""
        return cls(
            id=data.get("id", str(uuid.uuid4())[:8]),
            name=data.get("name", "Unnamed Session"),
            created_at=data.get("created_at", datetime.now().isoformat()),
            updated_at=data.get("updated_at", datetime.now().isoformat()),
            conversation_history=data.get("conversation_history", []),
            context=data.get("context", {}),
            agent_states=data.get("agent_states", {}),
            open_files=data.get("open_files", []),
            current_directory=(
                default_directory or data.get("current_directory") or os.getcwd()
            ),
            model=data.get("model", ""),
            tags=data.get("tags", []),
            description=data.get("description", ""),
        )

    def get_summary(self) -> Dict[str, Any]:
        """Return a short session summary."""
        return {
            "id": self.id,
            "name": self.name,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "message_count": len(self.conversation_history),
            "open_files_count": len(self.open_files),
            "agents_with_state": list(self.agent_states.keys()),
            "tags": self.tags,
            "model": self.model,
        }


class SessionManager:
    """Persistent session manager."""

    def __init__(
        self,
        storage_path: Optional[Path] = None,
        workspace_root: Optional[Path] = None,
    ):
        """Initialise the session manager with a storage path."""
        self.workspace_root = (
            Path(workspace_root).expanduser()
            if workspace_root is not None
            else None
        )
        self._validate_workspace_root()
        if storage_path:
            self.storage_path = Path(storage_path)
        else:
            from aura_cli.core.paths import aura_path

            self.storage_path = aura_path("sessions")

        self.storage_path.mkdir(parents=True, exist_ok=True)
        self._harden_storage_permissions()

        self.current_session: Optional[Session] = None
        self.auto_save: bool = True
        self.auto_save_interval: int = 60  # segundos

        logger.info(f"SessionManager initialized: {self.storage_path}")

    def _validate_workspace_root(self) -> None:
        """Reject an invalid or symlinked workspace before using it."""
        if self.workspace_root is None:
            return
        if self.workspace_root.is_symlink() or (
            self.workspace_root.exists() and not self.workspace_root.is_dir()
        ):
            raise ValueError(
                f"Workspace root must be a real directory: {self.workspace_root}"
            )

    def _harden_storage_permissions(self) -> None:
        """Keep session metadata private to the current OS user."""
        try:
            self.storage_path.chmod(0o700)
            for session_path in self.storage_path.glob("*.json"):
                session_path.chmod(0o600)
        except OSError as exc:
            logger.warning("Could not harden session storage permissions: %s", exc)

    def set_workspace_root(self, workspace_root: Path) -> None:
        """Switch workspace context without carrying over its active session."""
        resolved_root = Path(workspace_root).expanduser()
        if resolved_root == self.workspace_root:
            return
        previous_root = self.workspace_root
        self.workspace_root = resolved_root
        try:
            self._validate_workspace_root()
        except Exception:
            self.workspace_root = previous_root
            raise
        self.current_session = None
        logger.info("Session workspace switched to %s", resolved_root)

    def create_session(
        self, name: str, description: str = "", tags: Optional[List[str]] = None
    ) -> Session:
        """Create a new session and return it."""
        now = datetime.now().isoformat()

        session = Session(
            id=str(uuid.uuid4())[:8],
            name=name,
            created_at=now,
            updated_at=now,
            description=description,
            tags=tags or [],
            current_directory=str(self.workspace_root or Path.cwd().resolve()),
        )

        self.current_session = session
        self.save_session(session)

        logger.info(f"Session '{name}' created with ID {session.id}")
        return session

    def save_session(self, session: Optional[Session] = None):
        """Persist the given session to disk."""
        session = session or self.current_session
        if not session:
            logger.warning("No session to save")
            return

        session.updated_at = datetime.now().isoformat()

        file_path = self.storage_path / f"{session.id}.json"

        temporary_path: Optional[Path] = None
        try:
            file_descriptor, temporary_name = tempfile.mkstemp(
                prefix=f".{session.id}.", suffix=".tmp", dir=self.storage_path
            )
            temporary_path = Path(temporary_name)
            with os.fdopen(file_descriptor, "w", encoding="utf-8") as f:
                json.dump(session.to_dict(), f, indent=2, ensure_ascii=False)
                f.flush()
                os.fsync(f.fileno())
            os.replace(temporary_path, file_path)
            file_path.chmod(0o600)
            temporary_path = None

            logger.debug(f"Session {session.id} saved atomically")
        except Exception as e:
            logger.error(f"Error saving session: {e}")
            raise
        finally:
            if temporary_path is not None:
                try:
                    temporary_path.unlink(missing_ok=True)
                except OSError:
                    logger.debug(
                        "Não foi possível remover snapshot temporário", exc_info=True
                    )

    def load_session(self, session_id: str) -> Optional[Session]:
        """Load a session by ID from disk. Returns None if not found."""
        file_path = self.storage_path / f"{session_id}.json"

        if not file_path.exists():
            logger.warning(f"Session {session_id} not found")
            return None

        try:
            with open(file_path, encoding="utf-8") as f:
                data = json.load(f)

            session = Session.from_dict(
                data,
                default_directory=(
                    str(self.workspace_root) if self.workspace_root else None
                ),
            )
            self.current_session = session

            logger.info(f"Session '{session.name}' loaded")
            return session
        except Exception as e:
            logger.error(f"Error loading session: {e}")
            return None

    def delete_session(self, session_id: str) -> bool:
        """Delete a session from disk. Returns True if found."""
        file_path = self.storage_path / f"{session_id}.json"

        if not file_path.exists():
            return False

        try:
            file_path.unlink()

            if self.current_session and self.current_session.id == session_id:
                self.current_session = None

            logger.info(f"Session {session_id} removed")
            return True
        except Exception as e:
            logger.error(f"Error removing session: {e}")
            return False

    def list_sessions(
        self,
        tags: Optional[List[str]] = None,
        limit: Optional[int] = None,
        sort_by: str = "updated_at",
    ) -> List[Session]:
        """List available sessions, optionally filtered and limited."""
        sessions = []

        for file_path in self.storage_path.glob("*.json"):
            try:
                with open(file_path, encoding="utf-8") as f:
                    data = json.load(f)

                session = Session.from_dict(
                    data,
                    default_directory=(
                        str(self.workspace_root) if self.workspace_root else None
                    ),
                )

                # Filtrar por tags
                if tags and not any(tag in session.tags for tag in tags):
                    continue
                sessions.append(session)
            except Exception as e:
                logger.warning(f"Error reading session {file_path}: {e}")

        reverse = sort_by in ["updated_at", "created_at", "message_count"]
        if sort_by == "message_count":
            sessions.sort(key=lambda s: len(s.conversation_history), reverse=reverse)
        elif sort_by == "name":
            sessions.sort(key=lambda s: s.name.lower())
        else:
            sessions.sort(key=lambda s: getattr(s, sort_by, ""), reverse=reverse)

        if limit:
            sessions = sessions[:limit]

        return sessions

    def export_session(self, session_id: str, export_path: str) -> bool:
        """Export a session to a file and return the export path."""
        session = self.load_session(session_id)
        if not session:
            return False

        try:
            export_data = {
                "version": "1.0",
                "exported_at": datetime.now().isoformat(),
                "session": session.to_dict(),
            }

            _atomic_write_json(Path(export_path), export_data)

            logger.info(f"Session exported to {export_path}")
            return True
        except Exception as e:
            logger.error(f"Error exporting session: {e}")
            return False

    def import_session(self, import_path: str) -> Optional[Session]:
        """Import a session from a file and return the session."""
        try:
            with open(import_path, encoding="utf-8") as f:
                data = json.load(f)

            session_data = data.get("session", data)

            # Gerar novo ID para evitar conflitos
            session_data["id"] = str(uuid.uuid4())[:8]
            session_data["name"] = f"{session_data.get('name', 'Imported')} (imported)"

            session = Session.from_dict(session_data)
            self.save_session(session)

            logger.info(f"Session imported: {session.name}")
            return session
        except Exception as e:
            logger.error(f"Error importing session: {e}")
            return None

    def get_recent_sessions(self, limit: int = 5) -> List[Session]:
        """Return the most recent sessions."""
        return self.list_sessions(limit=limit, sort_by="updated_at")

    def search_sessions(self, query: str) -> List[Session]:
        """Search sessions by name or content."""
        query_lower = query.lower()
        results = []

        for session in self.list_sessions():
            # Buscar no nome
            if query_lower in session.name.lower():
                results.append(session)
                continue

            # Search in description
            if query_lower in session.description.lower():
                results.append(session)
                continue

            # Buscar nas tags
            if any(query_lower in tag.lower() for tag in session.tags):
                results.append(session)
                continue

            # Search in history
            for msg in session.conversation_history:
                if query_lower in msg.get("content", "").lower():
                    results.append(session)
                    break

        return results

    def get_stats(self) -> Dict[str, Any]:
        """Return session manager statistics as a dict."""
        sessions = self.list_sessions()

        total_messages = sum(len(s.conversation_history) for s in sessions)

        tags_count: dict[str, int] = {}
        for session in sessions:
            for tag in session.tags:
                tags_count[tag] = tags_count.get(tag, 0) + 1

        return {
            "total_sessions": len(sessions),
            "total_messages": total_messages,
            "current_session": (
                self.current_session.id if self.current_session else None
            ),
            "tags": tags_count,
            "storage_path": str(self.storage_path),
        }


_session_manager: Optional[SessionManager] = None


def get_session_manager(project_root: Optional[Path] = None) -> SessionManager:
    """Return the global session manager singleton."""
    global _session_manager
    if _session_manager is None:
        _session_manager = SessionManager(workspace_root=project_root)
    elif project_root is not None:
        _session_manager.set_workspace_root(project_root)
    return _session_manager
