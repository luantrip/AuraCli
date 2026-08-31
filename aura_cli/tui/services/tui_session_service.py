"""Bridge TUI chat state with core SessionManager persistence."""

from __future__ import annotations

from datetime import datetime
import json
import os
from pathlib import Path
import tempfile
import time
from typing import TYPE_CHECKING, Any, Dict, List, Optional

from aura_cli.application.sessions import chat_messages_to_history, role_to_sender
from aura_cli.core.logger import get_logger
from aura_cli.core.sessions import get_session_manager
from aura_cli.core.sessions.session_manager import Session

if TYPE_CHECKING:
    from aura_cli.tui.app import AuraTUI

logger = get_logger(__name__)


def _workspace_root(app: Any = None, manager: Any = None) -> Path:
    """Resolve the canonical workspace for TUI session metadata."""
    app_loop = getattr(app, "app_loop", None) if app is not None else None
    candidates = (
        getattr(app_loop, "project_root", None),
        getattr(manager, "workspace_root", None),
    )
    for candidate in candidates:
        if isinstance(candidate, (str, Path)):
            return Path(candidate).expanduser().resolve()
    from aura_cli.core.tools.file_system import get_allowed_base_dir

    return get_allowed_base_dir()


def _bounded_directory(raw_directory: Any, base_dir: Path) -> str:
    """Keep imported session directories inside the active workspace."""
    if not isinstance(raw_directory, (str, Path)) or not str(raw_directory).strip():
        return str(base_dir)
    try:
        candidate = Path(raw_directory).expanduser()
        resolved = (
            candidate if candidate.is_absolute() else base_dir / candidate
        ).resolve()
        resolved.relative_to(base_dir)
    except (OSError, RuntimeError, ValueError):
        return str(base_dir)
    return str(resolved)


def _configure_manager_workspace(manager: Any, app: Any = None) -> Path:
    """Bind a concrete SessionManager to the active TUI workspace when supported."""
    root = _workspace_root(app, manager)
    if hasattr(manager, "workspace_root"):
        manager.workspace_root = root
    return root


def export_session_jsonl(session: Session, path: Path) -> None:
    """Export session messages as JSONL for line-oriented history readers."""
    temporary_path: Optional[Path] = None
    try:
        file_descriptor, temporary_name = tempfile.mkstemp(
            prefix=f".{path.name}.", suffix=".tmp", dir=path.parent
        )
        temporary_path = Path(temporary_name)
        with os.fdopen(file_descriptor, "w", encoding="utf-8") as f:
            for entry in session.conversation_history:
                line = {
                    "role": entry.get("role", "user"),
                    "content": entry.get("content", ""),
                    "cwd": session.current_directory,
                }
                f.write(json.dumps(line, ensure_ascii=False) + "\n")
            f.flush()
            os.fsync(f.fileno())
        os.replace(temporary_path, path)
        temporary_path = None
    finally:
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)


def sync_tui_chat_to_session(app: AuraTUI, session: Session) -> None:
    """Copy current TUI chat bubbles into a Session object."""
    session.conversation_history = chat_messages_to_history(app.all_chat_messages)
    session.current_directory = str(_workspace_root(app))
    session.updated_at = datetime.now().isoformat()
    if app.app_loop and getattr(app.app_loop, "stats", None):
        model = getattr(app.app_loop.stats, "current_model", None) or ""
        if model:
            session.model = str(model)
    sid = app.store.get("session.id")
    if sid:
        session.set_context("tui_session_id", sid)


def save_tui_session(app: AuraTUI) -> Optional[Session]:
    """Persist current chat via SessionManager (+ JSONL mirror)."""
    manager = get_session_manager()
    _configure_manager_workspace(manager, app)
    session = manager.current_session
    if session is None:
        name = f"TUI {datetime.now().strftime('%Y-%m-%d %H:%M')}"
        session = manager.create_session(name, tags=["tui"])
    sync_tui_chat_to_session(app, session)
    manager.save_session(session)
    jsonl_path = manager.storage_path / f"{session.id}.jsonl"
    try:
        export_session_jsonl(session, jsonl_path)
    except Exception as e:
        logger.warning(f"Não foi possível exportar JSONL: {e}")
    app.store.set("session.id", session.id)
    app.store.set("session.manager_id", session.id)
    return session


def start_new_tui_session(app: AuraTUI, *, save_current: bool = True) -> Session:
    """Optionally save current chat, then start a fresh Session + empty chat."""
    from aura_cli.tui.widgets.chat import AuraChatLog

    if save_current and app.all_chat_messages:
        save_tui_session(app)
    manager = get_session_manager()
    _configure_manager_workspace(manager, app)
    name = f"TUI {datetime.now().strftime('%Y-%m-%d %H:%M')}"
    session = manager.create_session(name, tags=["tui"])
    app.post_message(AuraChatLog.ClearHistory())
    app.all_chat_messages.clear()
    app.store.set("session.id", session.id)
    app.store.set("session.started_at", datetime.now().isoformat())
    app.store.set("session.manager_id", session.id)
    return session


def restore_session_to_chat(app: AuraTUI, session: Session) -> None:
    """Load a saved Session into the TUI chat log."""
    from aura_cli.tui.widgets.chat import AuraChatLog

    app.post_message(AuraChatLog.ClearHistory())
    app.all_chat_messages.clear()
    manager = get_session_manager()
    manager.current_session = session
    for entry in session.conversation_history:
        role = entry.get("role", "assistant")
        content = entry.get("content", "")
        meta = entry.get("metadata") or {}
        sender = meta.get("sender") or role_to_sender(role)
        app.post_message_to_chat(sender, content)
    app.store.set("session.manager_id", session.id)
    app.store.set("session.id", session.id)


def load_session_from_path(path: Path) -> Optional[Session]:
    """Load SessionManager JSON or synthesize from JSONL."""
    manager = get_session_manager()
    workspace_root = _configure_manager_workspace(manager)
    if path.suffix == ".json":
        return manager.load_session(path.stem)
    if path.suffix == ".jsonl":
        session_id = path.stem
        messages: List[Dict[str, Any]] = []
        cwd = None
        with open(path, encoding="utf-8") as f:
            for line in f:
                try:
                    row = json.loads(line)
                    messages.append(
                        {
                            "role": row.get("role", "user"),
                            "content": row.get("content", ""),
                            "timestamp": datetime.now().isoformat(),
                            "metadata": {},
                        }
                    )
                    if "cwd" in row:
                        cwd = row["cwd"]
                except json.JSONDecodeError:
                    continue
        now = datetime.now().isoformat()
        return Session(
            id=session_id,
            name=f"JSONL {session_id}",
            created_at=now,
            updated_at=now,
            conversation_history=messages,
            current_directory=_bounded_directory(cwd, workspace_root),
            tags=["jsonl"],
        )
    return None


def preview_external_tui_session(source: str, app: Any):
    """Build an external-session preview through the TUI service boundary."""
    from aura_cli.core.sessions.external_import import preview_external_session

    app_loop = getattr(app, "app_loop", None)
    return preview_external_session(
        source,
        workspace_root=_workspace_root(app),
        active_model=str(getattr(app_loop, "final_model", "")),
    )


def import_external_tui_session(source: str, app: Any) -> Session:
    """Import an external session using the active TUI workspace."""
    from aura_cli.core.sessions.external_import import import_external_session

    manager = get_session_manager()
    _configure_manager_workspace(manager, app)
    return import_external_session(manager, source)


def maybe_autosave(app: AuraTUI, *, force: bool = False) -> bool:
    """Persist changed chat, respecting the configured autosave interval."""
    from aura_cli.core.sessions import get_session_manager

    manager = get_session_manager()
    if not force and not manager.auto_save:
        return False
    if not app.all_chat_messages:
        return False
    count = len(app.all_chat_messages)
    last = getattr(app, "_last_saved_message_count", -1)
    if not force and count == last:
        return False

    interval_value = getattr(manager, "auto_save_interval", 0)
    interval = (
        float(interval_value) if isinstance(interval_value, (int, float)) else 0.0
    )
    now = time.monotonic()
    last_autosave = getattr(app, "__dict__", {}).get("_last_autosave_at")
    if (
        not force
        and interval > 0
        and isinstance(last_autosave, (int, float))
        and now - last_autosave < interval
    ):
        return False

    save_tui_session(app)
    app._last_saved_message_count = count
    app._last_autosave_at = now
    return True
