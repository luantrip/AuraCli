"""Composition root primitives for the interactive CLI runtime."""

from __future__ import annotations

import contextlib
from dataclasses import dataclass, field
import os
from pathlib import Path
import subprocess
import sys
import threading
import time
from typing import Any

from aura_cli.core.paths import ArtifactLayout
from aura_cli.core.tools.file_system import set_allowed_base_dir


class EmbeddingServerLifecycle:
    """Own the optional local embedding subprocess for one CLI process."""

    def __init__(self) -> None:
        self._process: subprocess.Popen[Any] | None = None
        self._lock = threading.Lock()

    @staticmethod
    def port_in_use(port: int) -> bool:
        import socket

        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.settimeout(1)
                return sock.connect_ex(("127.0.0.1", port)) == 0
        except OSError:
            return False

    @classmethod
    def wait_until_ready(cls, port: int, timeout: float = 45.0) -> bool:
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            if cls.port_in_use(port):
                return True
            time.sleep(1)
        return False

    def start(self, port: int) -> subprocess.Popen[Any] | None:
        """Start the server unless another process already owns its port."""
        with self._lock:
            if self.port_in_use(port):
                self._process = None
                return None
            from aura_cli.core.paths import aura_path

            venv_python = str(aura_path("embeddings_venv", "bin", "python"))
            server_python = (
                venv_python if os.path.exists(venv_python) else sys.executable
            )
            server_script = str(
                Path(__file__).parents[2]
                / "aura_cli"
                / "core"
                / "embeddings"
                / "server.py"
            )
            env = os.environ.copy()
            env["HF_HUB_DISABLE_TELEMETRY"] = "1"
            env["TOKENIZERS_PARALLELISM"] = "false"
            self._process = subprocess.Popen(
                [server_python, server_script],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                env=env,
            )
            threading.Thread(
                target=self.wait_until_ready,
                args=(port,),
                daemon=True,
                name="embedding-server-watchdog",
            ).start()
            return self._process

    def stop(self) -> None:
        """Terminate a server started by this process, if any."""
        with self._lock:
            process, self._process = self._process, None
        if process is None:
            return
        process.terminate()
        try:
            process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            process.kill()
            with contextlib.suppress(subprocess.TimeoutExpired):
                process.wait(timeout=5)


@dataclass
class RuntimeServices:
    """Critical, workspace-scoped services owned by one CLI session."""

    project_root: Path
    memory_service: Any
    session_state: Any
    notebook_service: Any
    imagination_manager: Any
    tangent_manager: Any
    checkpoint_manager: Any
    hook_manager: Any
    container: Any
    workspace: Any
    turn_repository: Any = None
    _shutdown_complete: bool = field(default=False, init=False, repr=False)
    _shutdown_lock: threading.Lock = field(
        default_factory=threading.Lock, init=False, repr=False
    )

    @classmethod
    def initialize(cls, project_root: Path) -> RuntimeServices:
        """Initialize critical services synchronously and exactly once."""
        from aura_cli.application.workspace import WorkspaceState
        from aura_cli.core.checkpoint import CheckpointManager
        from aura_cli.core.context.base import ContextManager
        from aura_cli.core.di import Services, get_container
        from aura_cli.core.di_bootstrap import bootstrap_services
        from aura_cli.core.memory.memory_manager import ImaginationManager
        from aura_cli.core.memory.memory_service import get_memory_service
        from aura_cli.core.memory.notebook_service import get_notebook_service
        from aura_cli.core.paths import aura_path
        from aura_cli.core.sessions.session_state import get_session_state
        from aura_cli.core.sessions.turn_repository import AtomicTurnRepository

        bootstrap_services()
        container = get_container()
        resolved_root = Path(project_root).expanduser().resolve()

        set_allowed_base_dir(str(resolved_root))
        memory_service = get_memory_service(resolved_root)
        session_state = get_session_state()
        session_state.initialize(resolved_root)
        notebook_service = get_notebook_service(
            base_path=ArtifactLayout(resolved_root).project("notebooks")
        )
        imagination_manager = ImaginationManager(resolved_root)
        tangent_manager = container.resolve(Services.TANGENT_MANAGER)
        checkpoint_manager = CheckpointManager(
            shadow_dir=ArtifactLayout(resolved_root).project(".checkpoints"),
            workspace_root=resolved_root,
        )
        hook_manager = container.resolve(Services.HOOK_MANAGER)
        context_manager = ContextManager()
        workspace = WorkspaceState(
            project_root=resolved_root,
            memory=memory_service,
            session=session_state,
            context=context_manager,
            notebook=notebook_service,
            imagination=imagination_manager,
            checkpoint=checkpoint_manager,
        )
        turn_repository = AtomicTurnRepository(aura_path("sessions"))

        container.override(Services.NOTEBOOK_SERVICE, notebook_service)
        container.override(Services.CHECKPOINT_MANAGER, checkpoint_manager)
        return cls(
            project_root=resolved_root,
            memory_service=memory_service,
            session_state=session_state,
            notebook_service=notebook_service,
            imagination_manager=imagination_manager,
            tangent_manager=tangent_manager,
            checkpoint_manager=checkpoint_manager,
            hook_manager=hook_manager,
            container=container,
            workspace=workspace,
            turn_repository=turn_repository,
        )

    def shutdown(self) -> None:
        """Release container-owned singletons once."""
        with self._shutdown_lock:
            if self._shutdown_complete:
                return
            self.container.shutdown()
            from aura_cli.core.memory.notebook_service import reset_notebook_service

            reset_notebook_service()
            self._shutdown_complete = True
