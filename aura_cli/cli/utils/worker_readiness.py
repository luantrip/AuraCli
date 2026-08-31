"""Readiness checks for headless and delegated worker launches.

The checks in this module are intentionally side-effect free: they do not create
workers, threads, provider clients, network requests, or write configuration.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Mapping, Sequence

from aura_cli.core.llm.model_utils import (
    get_provider_from_model,
    normalize_model_name,
)

_PROVIDER_CREDENTIALS = {
    "gemini": "GOOGLE_API_KEY",
    "claude": "ANTHROPIC_API_KEY",
    "gpt": "OPENAI_API_KEY",
    "openrouter": "OPENROUTER_API_KEY",
    "nvidia": "NVIDIA_API_KEY",
    "cerebras": "CEREBRAS_API_KEY",
    "groq": "GROQ_API_KEY",
    # Preserve the current runtime fallback used when the CLI receives `auto`.
    "auto": "GOOGLE_API_KEY",
}


@dataclass(frozen=True)
class ReadinessReport:
    """Serializable result of a worker launch preflight."""

    ready: bool
    code: str
    message: str
    worker_type: str
    model: str
    provider: str | None = None
    credential_name: str | None = None
    workspace: str | None = None
    dependencies: tuple[str, ...] = field(default_factory=tuple)

    def to_dict(self) -> dict[str, object]:
        """Return a JSON-safe representation without credential values."""
        return {
            "status": "ready" if self.ready else "error",
            "ready": self.ready,
            "code": self.code,
            "error_code": None if self.ready else self.code,
            "message": self.message,
            "error": None if self.ready else self.message,
            "worker_type": self.worker_type,
            "model": self.model,
            "provider": self.provider,
            "credential_name": self.credential_name,
            "workspace": self.workspace,
            "dependencies": list(self.dependencies),
        }


class WorkerReadinessError(RuntimeError):
    """Raised before thread creation when a worker is not ready to launch."""

    def __init__(self, report: ReadinessReport) -> None:
        self.report = report
        super().__init__(report.message)


def _resolve_provider_and_model(model: str | None) -> tuple[str, str] | None:
    normalized = normalize_model_name(model)
    if not normalized:
        return None
    provider = get_provider_from_model(normalized)
    if provider == "auto":
        return provider, normalized
    if not provider:
        return None
    return provider, normalized


def _credential_present(api_keys: Mapping[str, str], credential_name: str) -> bool:
    value = api_keys.get(credential_name)
    return bool(value and str(value).strip())


def build_worker_readiness(
    *,
    worker_type: str,
    model: str | None,
    api_keys: Mapping[str, str],
    project_root: Path | None,
    dependency_check: Callable[[], Mapping[str, object] | Sequence[str] | None]
    | None = None,
) -> ReadinessReport:
    """Build a side-effect-free readiness report for a concrete worker launch."""
    worker_name = worker_type.strip().lower() or "worker"
    requested_model = str(model or "").strip()
    resolved = _resolve_provider_and_model(requested_model)
    workspace = str(project_root or Path.cwd())

    if not requested_model or resolved is None:
        return ReadinessReport(
            ready=False,
            code="model",
            message=(
                f"Invalid model or provider not identified for {worker_name}: "
                f"'{requested_model or 'vazio'}'."
            ),
            worker_type=worker_name,
            model=requested_model,
            workspace=workspace,
        )

    provider, normalized_model = resolved
    credential_name = _PROVIDER_CREDENTIALS.get(provider)
    if credential_name is None:
        return ReadinessReport(
            ready=False,
            code="provider",
            message=f"Provider não suportado para {worker_name}: '{provider}'.",
            worker_type=worker_name,
            model=normalized_model,
            provider=provider,
            workspace=workspace,
        )

    root = Path(project_root or Path.cwd()).expanduser()
    if not root.exists() or not root.is_dir():
        return ReadinessReport(
            ready=False,
            code="workspace",
            message=f"Workspace não existe ou não é diretório: {root}.",
            worker_type=worker_name,
            model=normalized_model,
            provider=provider,
            credential_name=credential_name,
            workspace=str(root),
        )

    if not _credential_present(api_keys, credential_name):
        return ReadinessReport(
            ready=False,
            code="configuration",
            message=(
                f"{credential_name} não configurada para o provider '{provider}'. "
                "Configure com /settings ou pelo ambiente."
            ),
            worker_type=worker_name,
            model=normalized_model,
            provider=provider,
            credential_name=credential_name,
            workspace=str(root),
        )

    dependencies: list[str] = []
    if dependency_check is not None:
        try:
            dependency_result = dependency_check()
        except Exception as error:
            return ReadinessReport(
                ready=False,
                code="dependency",
                message=(
                    f"Dependência de ferramentas indisponível para {worker_name}: "
                    f"{error}"
                ),
                worker_type=worker_name,
                model=normalized_model,
                provider=provider,
                credential_name=credential_name,
                workspace=str(root),
            )
        if isinstance(dependency_result, Mapping):
            dependencies = [
                str(name)
                for name, available in dependency_result.items()
                if not available
            ]
        elif dependency_result:
            dependencies = [str(item) for item in dependency_result]
        if dependencies:
            return ReadinessReport(
                ready=False,
                code="dependency",
                message=(
                    f"Dependências ausentes para {worker_name}: "
                    f"{', '.join(dependencies)}."
                ),
                worker_type=worker_name,
                model=normalized_model,
                provider=provider,
                credential_name=credential_name,
                workspace=str(root),
                dependencies=tuple(dependencies),
            )

    return ReadinessReport(
        ready=True,
        code="ready",
        message=f"{worker_name} pronto para iniciar.",
        worker_type=worker_name,
        model=normalized_model,
        provider=provider,
        credential_name=credential_name,
        workspace=str(root),
    )


def ensure_worker_ready(**kwargs: object) -> ReadinessReport:
    """Raise `WorkerReadinessError` when the supplied launch is not ready."""
    report = build_worker_readiness(**kwargs)  # type: ignore[arg-type]
    if not report.ready:
        raise WorkerReadinessError(report)
    return report
