"""Safe, incremental refactoring executor with checkpoints and rollback.

Creates a Git checkpoint (or file backup) before each batch, validates
syntax and tests after each batch, and auto-rolls back on failure.
Maintains a complete session log under .aura/checkpoints/<session>/.

.aura/ layout created by this module:
    checkpoints/<YYYYMMDD_HHMMSS>/
        session.json          ← batch state and change counts
        before_batch_N_M/     ← file snapshots before each batch
"""

from datetime import datetime
import json
from pathlib import Path
import shutil
import subprocess
from typing import Any, Dict, List, Optional

from aura_cli.application.refactoring import RefactoringPlan
from aura_cli.core.logger import get_logger
from aura_cli.core.testing.test_runner import validate_tests_pass
from aura_cli.core.tools.dev_tools import edit_file
from aura_cli.core.validation import ValidationResult, validate_code

logger = get_logger(__name__)


class RefactoringSession:
    """Manages refactoring session with checkpoints and rollback."""

    def __init__(self, plan: "RefactoringPlan", scope: str = "."):
        """Initialize the instance."""
        self.plan = plan
        self.scope = Path(scope).resolve()
        self.applied_changes: List[Dict] = []
        self.checkpoints: List[Dict] = []
        self.failed_changes: List[Dict] = []
        self.current_step = 0
        self.current_batch = 0
        self.session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        from aura_cli.core.paths import ArtifactLayout

        self.checkpoint_dir = ArtifactLayout(self.scope).project(
            "checkpoints", self.session_id
        )
        self.checkpoint_dir.mkdir(parents=True, exist_ok=True)
        self.session_file = self.checkpoint_dir / "session.json"
        self._has_git = self._check_git_available()

    def _check_git_available(self) -> bool:
        """Return True if Git is available."""
        try:
            result = subprocess.run(
                ["git", "rev-parse", "--git-dir"],
                capture_output=True,
                cwd=str(self.scope),
                timeout=5,
            )
            return result.returncode == 0
        except (FileNotFoundError, subprocess.TimeoutExpired):
            return False

    def save_checkpoint(self, name: str, description: str = "") -> Optional[str]:
        """Save a refactoring checkpoint before applying changes."""
        checkpoint_id = f"{name}_{self.current_step}"

        if self._has_git:
            try:
                subprocess.run(
                    ["git", "add", "-A"],
                    check=True,
                    capture_output=True,
                    cwd=str(self.scope),
                )

                commit_msg = f"Aura checkpoint: {checkpoint_id}"
                if description:
                    commit_msg += f" - {description}"

                subprocess.run(
                    ["git", "commit", "-m", commit_msg],
                    check=True,
                    capture_output=True,
                    cwd=str(self.scope),
                )

                result = subprocess.run(
                    ["git", "rev-parse", "HEAD"],
                    capture_output=True,
                    text=True,
                    check=True,
                    cwd=str(self.scope),
                )

                commit_hash = result.stdout.strip()
                checkpoint_data = {
                    "id": checkpoint_id,
                    "type": "git",
                    "commit_hash": commit_hash,
                    "step": self.current_step,
                    "batch": self.current_batch,
                    "timestamp": datetime.now().isoformat(),
                    "description": description,
                }
                self.checkpoints.append(checkpoint_data)
                self._save_session_state()

                logger.info(
                    f"Checkpoint Git salvo: {checkpoint_id} ({commit_hash[:8]})"
                )
                return commit_hash

            except subprocess.CalledProcessError as e:
                error_msg = (
                    f"Error creating Git checkpoint: {e}. "
                    f"Comando falhou: '{' '.join(e.cmd) if hasattr(e, 'cmd') else 'N/A'}'. "
                    "Usando backup de arquivos como alternativa. "
                    "Verifique se o repositório Git está configurado corretamente."
                )
                logger.warning(error_msg)
                self._has_git = False

        backup_path = self.checkpoint_dir / checkpoint_id
        backup_path.mkdir(parents=True, exist_ok=True)

        backed_files = []
        for change in self.applied_changes:
            file_path = self.scope / change["step"]["file"]
            if file_path.exists():
                backup_file = backup_path / file_path.name
                shutil.copy2(file_path, backup_file)
                backed_files.append(str(file_path.relative_to(self.scope)))

        checkpoint_data = {
            "id": checkpoint_id,
            "type": "backup",
            "backup_path": str(backup_path),
            "files": backed_files,
            "step": self.current_step,
            "batch": self.current_batch,
            "timestamp": datetime.now().isoformat(),
            "description": description,
        }
        self.checkpoints.append(checkpoint_data)
        self._save_session_state()

        logger.info(
            f"Checkpoint backup salvo: {checkpoint_id} ({len(backed_files)} arquivos)"
        )
        return str(backup_path)

    def rollback_to_checkpoint(self, checkpoint_id: Optional[str] = None) -> bool:
        """Roll back all changes to a saved checkpoint."""
        if not self.checkpoints:
            logger.error("Nenhum checkpoint disponível para rollback")
            return False

        checkpoint: dict[str, Any] | None
        if checkpoint_id is None:
            checkpoint = self.checkpoints[-1]
        else:
            checkpoint = next(
                (
                    c
                    for c in self.checkpoints
                    if c["id"] == checkpoint_id
                    or c.get("commit_hash") == checkpoint_id
                    or c.get("backup_path") == checkpoint_id
                ),
                None,
            )

        if checkpoint is None:
            logger.error(f"Checkpoint '{checkpoint_id}' not found")
            return False

        try:
            if checkpoint["type"] == "git" and self._has_git:
                commit_hash = checkpoint["commit_hash"]
                subprocess.run(
                    ["git", "reset", "--hard", commit_hash],
                    check=True,
                    capture_output=True,
                    cwd=str(self.scope),
                )
                logger.info(f"Rollback Git para commit {commit_hash[:8]}")

                self.current_step = checkpoint["step"]
                self.current_batch = checkpoint["batch"]
                self._remove_applied_changes_after(checkpoint["step"])
                self._save_session_state()
                return True

            elif checkpoint["type"] == "backup":
                backup_path = Path(checkpoint["backup_path"])
                if not backup_path.exists():
                    logger.error(f"Backup not found: {backup_path}")
                    return False

                for file_name in checkpoint.get("files", []):
                    backup_file = backup_path / Path(file_name).name
                    original_file = self.scope / file_name

                    if backup_file.exists() and original_file.exists():
                        shutil.copy2(backup_file, original_file)
                        logger.debug(f"Restaurado: {file_name}")

                self.current_step = checkpoint["step"]
                self.current_batch = checkpoint["batch"]
                self._remove_applied_changes_after(checkpoint["step"])
                self._save_session_state()

                logger.info(
                    f"Rollback de backup: {checkpoint['id']} ({len(checkpoint.get('files', []))} arquivos)"
                )
                return True

        except FileNotFoundError as e:
            error_msg = (
                f"Rollback error: Checkpoint file not found: {e}. "
                "Não é possível restaurar o estado anterior. "
                f"Verifique se os arquivos de backup existem em {self.checkpoint_dir}."
            )
            logger.error(error_msg, exc_info=True)
            return False
        except PermissionError as e:
            error_msg = (
                f"Erro no rollback: Sem permissão para restaurar arquivos: {e}. "
                "Verifique permissões de escrita nos arquivos que precisam ser restaurados."
            )
            logger.error(error_msg, exc_info=True)
            return False
        except Exception as e:
            error_msg = (
                f"Erro inesperado no rollback: {e}. "
                f"Tipo de erro: {type(e).__name__}. "
                "Verifique os logs para mais detalhes. "
                "Os arquivos podem estar em estado inconsistente."
            )
            logger.error(error_msg, exc_info=True)
            return False

        return False

    def _remove_applied_changes_after(self, step: int):
        """Remove applied changes after a given index."""
        self.applied_changes = [c for c in self.applied_changes if c["step"] <= step]

    def _save_session_state(self):
        """Persist the current refactoring session state."""
        state = {
            "session_id": self.session_id,
            "current_step": self.current_step,
            "current_batch": self.current_batch,
            "checkpoints": self.checkpoints,
            "applied_changes_count": len(self.applied_changes),
            "failed_changes_count": len(self.failed_changes),
            "timestamp": datetime.now().isoformat(),
        }

        try:
            with open(self.session_file, "w") as f:
                json.dump(state, f, indent=2)
        except Exception as e:
            logger.warning(f"Error saving session state: {e}")


def _apply_batch_step(
    step: dict, step_idx: int, batch_idx: int, session: Any, validate: bool, scope: str
) -> tuple:
    """Apply a single refactoring step. Returns (failed, error_msg)."""
    try:
        result = apply_change(step, scope)
        if not result.get("success", False):
            err = result.get("error", "Unknown error")
            session.failed_changes.append(
                {
                    "step": step,
                    "error": err,
                    "batch": batch_idx,
                    "step_in_batch": step_idx,
                }
            )
            logger.error(f"Error applying change: {err}")
            return True, err

        session.applied_changes.append(
            {
                "step": step,
                "result": result,
                "batch": batch_idx,
                "step_in_batch": step_idx,
                "step_number": session.current_step,
            }
        )
        session.current_step += 1

        if validate:
            validation = validate_change(
                step["file"], step.get("before"), step.get("after"), scope
            )
            if not validation.passed:
                err = f"Validação falhou: {len(validation.errors)} erros"
                session.failed_changes.append(
                    {
                        "step": step,
                        "validation_errors": validation.errors,
                        "batch": batch_idx,
                        "step_in_batch": step_idx,
                    }
                )
                logger.warning(f"Validação falhou para {step['file']}")
                return True, err
    except FileNotFoundError as e:
        err = f"File not found during refactoring: {e}. Check that file {step.get('file', 'unknown')} exists and is accessible."
        session.failed_changes.append(
            {"step": step, "error": err, "batch": batch_idx, "step_in_batch": step_idx}
        )
        logger.error(f"Exceção ao aplicar mudança: {e}", exc_info=True)
        return True, str(e)
    return False, None


def _validate_batch_files(
    batch: list, batch_idx: int, session: Any, scope: str
) -> tuple:
    """Validate all files modified in a batch. Returns (failed, error_msg)."""
    for step in batch:
        file_path = step["file"]
        full_path = (
            Path(scope) / file_path
            if not Path(file_path).is_absolute()
            else Path(file_path)
        )
        if not full_path.exists():
            continue
        validation = validate_code(str(full_path), checks=["syntax", "types"])
        if not validation.passed:
            session.failed_changes.append(
                {
                    "file": file_path,
                    "validation_errors": validation.errors,
                    "batch": batch_idx,
                }
            )
            logger.warning(f"Validação falhou para {file_path}")
            return True, f"Validação falhou para {file_path}"
        if not validate_tests_pass(file_path, scope):
            session.failed_changes.append(
                {"file": file_path, "tests_failed": True, "batch": batch_idx}
            )
            logger.warning(f"Testes falharam para {file_path}")
            return True, f"Testes falharam para {file_path}"
    return False, None


def apply_refactoring_plan(
    plan: RefactoringPlan,
    validate: bool = True,
    auto_rollback: bool = True,
    batch_size: int = 10,
    scope: str = ".",
) -> Dict:
    """Apply a complete refactoring plan."""
    session = RefactoringSession(plan, scope)

    # Initialize Nexus Graph for Impact Analysis
    try:
        from aura_cli.core.context.graph_service import GraphService

        graph_service = GraphService(Path(scope))
        dependency_graph = graph_service.build_graph()
        if dependency_graph:
            logger.info(
                f"Nexus Graph initialized: {len(dependency_graph.nodes)} files mapped"
            )
    except Exception as e:
        logger.warning(f"Failed to initialize Nexus Graph: {e}")
        dependency_graph = None

    logger.info(
        f"Iniciando refatoração: {len(plan.steps)} steps, estratégia: {plan.strategy}"
    )

    batches = plan.get_batches(batch_size)
    total_batches = len(batches)

    logger.info(
        f"Processando {total_batches} batches de até {batch_size} mudanças cada"
    )

    for batch_idx, batch in enumerate(batches):
        logger.info(
            f"Processando batch {batch_idx + 1}/{total_batches} ({len(batch)} mudanças)"
        )

        # Impact Analysis for current batch
        if dependency_graph:
            impacted_files = set()
            for step in batch:
                file_path = step["file"]
                dependents = dependency_graph.get_dependents(file_path)
                if dependents:
                    impacted_files.update(dependents)

            if impacted_files:
                logger.warning(
                    f"⚠️ IMPACT ALERT: This batch affects {len(impacted_files)} dependent files: "
                    f"{', '.join(list(impacted_files)[:5])}..."
                )

        session.current_batch = batch_idx

        checkpoint = session.save_checkpoint(
            f"before_batch_{batch_idx}",
            f"Antes do batch {batch_idx + 1}/{total_batches}",
        )

        batch_failed = False
        batch_error = None

        for step_idx, step in enumerate(batch):
            batch_failed, batch_error = _apply_batch_step(
                step, step_idx, batch_idx, session, validate, scope
            )
            if batch_failed:
                break

        if validate and not batch_failed:
            batch_failed, batch_error = _validate_batch_files(
                batch, batch_idx, session, scope
            )

        if batch_failed and auto_rollback:
            logger.warning(
                f"Batch {batch_idx + 1} falhou: {batch_error}, revertendo..."
            )
            if checkpoint:
                success = session.rollback_to_checkpoint(checkpoint)
                if success:
                    logger.info(
                        f"Rollback bem-sucedido para checkpoint antes do batch {batch_idx + 1}"
                    )
                else:
                    logger.error("Rollback falhou!")

            break

        logger.info(f"Batch {batch_idx + 1}/{total_batches} completed successfully")

    total_applied = len(session.applied_changes)
    total_failed = len(session.failed_changes)
    success_rate = (total_applied / len(plan.steps) * 100) if plan.steps else 0

    result = {
        "success": total_failed == 0,
        "applied": total_applied,
        "failed": total_failed,
        "total": len(plan.steps),
        "success_rate": success_rate,
        "checkpoints": len(session.checkpoints),
        "can_rollback": len(session.checkpoints) > 0,
        "session_id": session.session_id,
        "failed_changes": session.failed_changes[:10],  # Primeiros 10 erros
        "last_checkpoint": (
            session.checkpoints[-1]["id"] if session.checkpoints else None
        ),
    }

    logger.info(
        f"Refatoração concluída: {total_applied}/{len(plan.steps)} aplicadas ({success_rate:.1f}%)"
    )

    return result


def apply_change(step: Dict, scope: str = ".") -> Dict:
    """Apply an individual change."""
    try:
        file_path = step["file"]
        old_content = step.get("before", "")
        new_content = step.get("after", "")

        if not Path(file_path).is_absolute():
            file_path = str(Path(scope) / file_path)

        if old_content and new_content:
            result = edit_file(file_path, old_content, new_content)
            success = "sucesso" in result.lower() or "success" in result.lower()
            return {"success": success, "message": result, "file": file_path}
        elif new_content:
            from aura_cli.core.tools.file_system import write_file

            result = write_file(file_path, new_content)
            success = "sucesso" in result.lower() or "success" in result.lower()
            return {"success": success, "message": result, "file": file_path}
        else:
            return {"success": False, "error": "No content provided", "file": file_path}

    except FileNotFoundError as e:
        error_msg = (
            f"File not found when applying change: {e}. "
            f"Check that file {step.get('file', 'unknown')} existe."
        )
        logger.error(error_msg, exc_info=True)
        return {
            "success": False,
            "error": error_msg,
            "file": step.get("file", "unknown"),
        }
    except PermissionError as e:
        error_msg = (
            f"Erro de permissão ao aplicar mudança no arquivo {step.get('file', 'unknown')}: {e}. "
            "Verifique permissões de escrita no arquivo."
        )
        logger.error(error_msg, exc_info=True)
        return {
            "success": False,
            "error": error_msg,
            "file": step.get("file", "unknown"),
        }
    except Exception as e:
        error_msg = (
            f"Erro inesperado ao aplicar mudança no arquivo {step.get('file', 'unknown')}: {e}. "
            f"Tipo de erro: {type(e).__name__}. "
            "Verifique os logs para mais detalhes."
        )
        logger.error(error_msg, exc_info=True)
        return {
            "success": False,
            "error": error_msg,
            "file": step.get("file", "unknown"),
        }


def validate_change(
    file_path: str, before: Optional[str], after: Optional[str], scope: str = "."
) -> ValidationResult:
    """Validate a change before applying it."""
    result = ValidationResult()

    if after:
        from aura_cli.core.tools.dev_tools import validate_syntax

        syntax_result = validate_syntax(after, "python")
        if syntax_result != "OK":
            result.add_error("syntax", syntax_result)
            return result

    full_path = (
        Path(scope) / file_path
        if not Path(file_path).is_absolute()
        else Path(file_path)
    )
    if full_path.exists():
        validation = validate_code(str(full_path), checks=["syntax", "types"])
        if not validation.passed:
            result.errors.extend(validation.errors)
            result.warnings.extend(validation.warnings)
            result.passed = False

    return result
