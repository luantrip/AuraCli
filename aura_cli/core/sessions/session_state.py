"""In-memory session state manager (runtime complement to SessionManager).

SessionStateManager holds constitution (cached), validator, project stage,
learned rules and context files for the current session. Persistent data
(history, open files) lives in SessionManager. Thread-safe singleton via
get_session_state().
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
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
from aura_cli.core.memory.memory_service import (
    LearnedRule,
    MemoryService,
    get_memory_service,
)

logger = get_logger(__name__)


@dataclass
class SessionState:
    """
    Immutable snapshot of session state at a point in time.

    Attributes:
        session_id: Unique session identifier
        constitution: Project constitution content
        constitution_validator: Validator for the constitution
        project_stage: Detected project stage (mvp, production, etc.)
        learned_rules: Rules learned during session
        context_files: Files added to context
        active_mode: Current active mode (normal, agi, ops)
        created_at: Session creation timestamp
    """

    session_id: str
    constitution: Optional[str] = None
    constitution_validator: Optional[ConstitutionValidator] = None
    project_stage: Optional[str] = None
    learned_rules: List[LearnedRule] = field(default_factory=list)
    context_files: List[str] = field(default_factory=list)
    active_mode: str = "normal"  # normal, agi, ops
    created_at: datetime = field(default_factory=datetime.now)

    def has_constitution(self) -> bool:
        """Check if constitution is loaded."""
        return self.constitution is not None and len(self.constitution) > 0

    def validate_prompt(self, prompt: str) -> Tuple[bool, List[str], Optional[str]]:
        """
        Validate a prompt against constitution.

        Args:
            prompt: Prompt to validate

        Returns:
            Tuple of (is_valid, violations, sanitized_prompt)
        """
        if self.constitution_validator is None:
            return True, [], None
        return self.constitution_validator.validate_prompt(prompt)

    def to_dict(self) -> Dict[str, Any]:
        """Convert state to dictionary."""
        return {
            "session_id": self.session_id,
            "constitution": self.constitution[:500] if self.constitution else None,
            "has_constitution": self.has_constitution(),
            "project_stage": self.project_stage,
            "learned_rules_count": len(self.learned_rules),
            "context_files": self.context_files,
            "active_mode": self.active_mode,
            "created_at": self.created_at.isoformat(),
        }


class SessionStateManager:
    """
    Manages runtime session state in a thread-safe manner.

    This singleton manager maintains the current session state,
    including constitution, validation, and learned rules.

    Features:
        - Thread-safe state access
        - Lazy constitution loading
        - Mode tracking (normal/agi/ops)
        - Integration with MemoryService
        - Auto-consolidation of learned rules after threshold

    Attributes:
        _current_state: Current session state
        _memory_service: Unified memory service instance
        _lock: Thread lock for safe access
        _rules_since_consolidation: Counter for auto-consolidation trigger
    """

    _instance: Optional[SessionStateManager] = None
    _lock = threading.RLock()

    AUTO_CONSOLIDATION_THRESHOLD = 5  # Consolidate after N rules
    AUTO_CONSOLIDATION_ENABLED = True

    def __init__(self):
        """Initialize the manager (use get_instance() for singleton)."""
        self._current_state: Optional[SessionState] = None
        self._memory_service: Optional[MemoryService] = None
        self._initialized = False
        self._state_lock = threading.RLock()
        self._rules_since_consolidation = 0

    def _create_updated_state(self, **updates) -> Optional[SessionState]:
        """Create a new SessionState with specified field updates."""
        if not self._current_state:
            return None
        import dataclasses

        current_dict = dataclasses.asdict(self._current_state)
        current_dict.update(updates)
        return SessionState(**current_dict)

    @classmethod
    def get_instance(cls) -> SessionStateManager:
        """
        Get singleton instance.

        Returns:
            SessionStateManager instance
        """
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    def initialize(self, project_root: Optional[Path] = None) -> SessionState:
        """
        Initialize a new session with constitution loading.

        Args:
            project_root: Project root directory

        Returns:
            Initialized SessionState
        """
        import time

        with self._state_lock:
            self._memory_service = get_memory_service(project_root)

            constitution = self._memory_service.get_constitution()

            validator = None
            project_stage = None

            if constitution:
                validator = ConstitutionValidator(constitution)
                project_stage = self._extract_project_stage(constitution)

            learned_rules = self._memory_service.get_learned_rules()

            self._current_state = SessionState(
                session_id=f"session_{int(time.time())}",
                constitution=constitution,
                constitution_validator=validator,
                project_stage=project_stage,
                learned_rules=learned_rules,
            )

            self._initialized = True
            logger.info(
                f"Session initialized: {self._current_state.session_id}, "
                f"constitution={'yes' if constitution else 'no'}"
            )

            return self._current_state

    def get_current_state(self) -> Optional[SessionState]:
        """
        Get current session state.

        Returns:
            Current SessionState or None if not initialized
        """
        with self._state_lock:
            return self._current_state

    def ensure_initialized(self, project_root: Optional[Path] = None) -> SessionState:
        """
        Ensure session is initialized, initializing if needed.

        Args:
            project_root: Project root directory (only used if not initialized)

        Returns:
            Current or newly initialized SessionState
        """
        with self._state_lock:
            if not self._initialized or self._current_state is None:
                return self.initialize(project_root)
            return self._current_state

    def is_initialized(self) -> bool:
        """Check if session is initialized."""
        with self._state_lock:
            return self._initialized and self._current_state is not None

    def get_constitution(self) -> Optional[str]:
        """
        Get constitution from current state.

        Returns:
            Constitution content or None
        """
        with self._state_lock:
            if self._current_state:
                return self._current_state.constitution
            return None

    def update_constitution(self, content: str) -> bool:
        """
        Update constitution in state and persist.

        Args:
            content: New constitution content

        Returns:
            True if updated successfully
        """
        with self._state_lock:
            if not self._memory_service:
                logger.warning("Cannot update constitution: not initialized")
                return False

            if not self._memory_service.save_constitution(content):
                return False

            if self._current_state:
                validator = ConstitutionValidator(content)
                project_stage = self._extract_project_stage(content)
                self._current_state = self._create_updated_state(
                    constitution=content,
                    constitution_validator=validator,
                    project_stage=project_stage,
                )

            logger.info("Constitution updated in session state")
            return True

    def get_validator(self) -> Optional[ConstitutionValidator]:
        """
        Get constitution validator from current state.

        Returns:
            ConstitutionValidator or None
        """
        with self._state_lock:
            if self._current_state:
                return self._current_state.constitution_validator
            return None

    def set_active_mode(self, mode: str) -> None:
        """
        Set current active mode.

        Args:
            mode: Mode name (normal, agi, ops)
        """
        valid_modes = ["normal", "agi", "ops"]
        if mode not in valid_modes:
            logger.warning(f"Invalid mode: {mode}, expected one of {valid_modes}")
            return

        with self._state_lock:
            if self._current_state:
                self._current_state = self._create_updated_state(active_mode=mode)
                logger.debug(f"Active mode set to: {mode}")

    def get_active_mode(self) -> str:
        """
        Get current active mode.

        Returns:
            Current mode name
        """
        with self._state_lock:
            if self._current_state:
                return self._current_state.active_mode
            return "normal"

    def is_agi_mode(self) -> bool:
        """Check if AGI mode is active."""
        return self.get_active_mode() == "agi"

    def is_ops_mode(self) -> bool:
        """Check if OPS mode is active."""
        return self.get_active_mode() == "ops"

    def add_learned_rule(
        self, rule: str, context: str = "", source: str = "agi"
    ) -> bool:
        """
        Add a learned rule to session and persist.

        Automatically triggers consolidation if threshold is reached.

        Args:
            rule: Rule text
            context: Context where rule was learned
            source: Source of the rule

        Returns:
            True if added successfully
        """
        with self._state_lock:
            if not self._memory_service:
                return False

            if not self._memory_service.add_learned_rule(rule, context, source):
                return False

            if self._current_state:
                new_rule = LearnedRule(rule=rule, context=context, source=source)
                updated_rules = [*self._current_state.learned_rules, new_rule]
                self._current_state = self._create_updated_state(
                    learned_rules=updated_rules
                )

            self._rules_since_consolidation += 1

            if (
                self.AUTO_CONSOLIDATION_ENABLED
                and self._rules_since_consolidation >= self.AUTO_CONSOLIDATION_THRESHOLD
            ):
                logger.info(
                    f"Auto-consolidation triggered: {self._rules_since_consolidation} rules accumulated"
                )
                self._auto_consolidate()

            return True

    def _auto_consolidate(self) -> bool:
        """
        Automatically consolidate learned rules into constitution.

        Called when the rules threshold is reached.

        Returns:
            True if consolidation was successful
        """
        try:
            result = self.consolidate_rules()
            if result:
                self._rules_since_consolidation = 0
                logger.info("Auto-consolidation completed successfully")
            return result
        except Exception as e:
            logger.warning(f"Auto-consolidation failed: {e}")
            return False

    def get_rules_pending_consolidation(self) -> int:
        """
        Get the number of rules pending consolidation.

        Returns:
            Number of rules added since last consolidation
        """
        return self._rules_since_consolidation

    def set_auto_consolidation(
        self, enabled: bool, threshold: Optional[int] = None
    ) -> None:
        """
        Configure auto-consolidation settings.

        Args:
            enabled: Whether to enable auto-consolidation
            threshold: Number of rules before auto-consolidation (optional)
        """
        self.AUTO_CONSOLIDATION_ENABLED = enabled
        if threshold is not None and threshold > 0:
            self.AUTO_CONSOLIDATION_THRESHOLD = threshold
        logger.info(
            f"Auto-consolidation: {'enabled' if enabled else 'disabled'}, "
            f"threshold: {self.AUTO_CONSOLIDATION_THRESHOLD}"
        )

    def get_learned_rules(self) -> List[LearnedRule]:
        """
        Get learned rules from current state.

        Returns:
            List of learned rules
        """
        with self._state_lock:
            if self._current_state:
                return self._current_state.learned_rules
            return []

    def consolidate_rules(self) -> bool:
        """
        Consolidate learned rules into constitution.

        Returns:
            True if consolidation was successful
        """
        with self._state_lock:
            if not self._memory_service:
                return False

            result = self._memory_service.consolidate_rules()

            if result:
                constitution = self._memory_service.get_constitution()
                if constitution and self._current_state:
                    validator = ConstitutionValidator(constitution)
                    self._current_state = self._create_updated_state(
                        constitution=constitution,
                        constitution_validator=validator,
                        learned_rules=[],
                    )

            return result

    def add_context_file(self, file_path: str) -> None:
        """Add a file to context."""
        with self._state_lock:
            if (
                self._current_state
                and file_path not in self._current_state.context_files
            ):
                updated_files = [*self._current_state.context_files, file_path]
                self._current_state = self._create_updated_state(
                    context_files=updated_files
                )

    def get_context_files(self) -> List[str]:
        """Get list of files in context."""
        with self._state_lock:
            if self._current_state:
                return self._current_state.context_files
            return []

    def _extract_project_stage(self, constitution: str) -> Optional[str]:
        """Extract project stage from constitution."""
        import re

        if not constitution:
            return None

        constitution_lower = constitution.lower()

        stage_patterns = [
            r"(?:estágio|fase|stage|phase)[:\-]?\s*(mvp|prototipação|produção\s+estável|refatoração\s+de\s+legado|caos\s+total|produção|legado|caos)",
            r"(mvp|prototipação|produção\s+estável)",
        ]

        for pattern in stage_patterns:
            matches = re.findall(pattern, constitution_lower, re.IGNORECASE)
            if matches:
                stage = matches[0].lower().strip()
                if "mvp" in stage or "prototipação" in stage:
                    return "mvp/prototipação"
                elif "produção" in stage:
                    return "produção estável"
                elif "legado" in stage:
                    return "refatoração de legado"
                elif "caos" in stage:
                    return "caos total"
                return stage

        return None

    def reset(self) -> None:
        """Reset session state."""
        with self._state_lock:
            self._current_state = None
            self._memory_service = None
            self._initialized = False
            logger.info("Session state reset")


def get_session_state() -> SessionStateManager:
    """
    Get the session state manager singleton.

    Returns:
        SessionStateManager instance
    """
    # Try DI container first (preferred path)
    try:
        from aura_cli.core.di import Services, get_container

        container = get_container()
        if container.has(Services.SESSION_STATE):
            return container.resolve(Services.SESSION_STATE)
    except Exception:
        pass

    # Fallback to legacy singleton
    return SessionStateManager.get_instance()


def reset_session_state() -> None:
    """Reset the session state singleton."""
    manager = get_session_state()
    manager.reset()
