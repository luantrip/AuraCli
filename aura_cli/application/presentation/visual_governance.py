"""Governance declarations required for every visual work capability."""

from __future__ import annotations

from dataclasses import dataclass

from aura_cli.application.presentation.tui_surfaces import SurfaceKind
from aura_cli.application.presentation.work_items import WorkItemKind, WorkItemState


@dataclass(frozen=True)
class VisualCapabilityDeclaration:
    kind: WorkItemKind
    lifecycle: frozenset[WorkItemState]
    surfaces: frozenset[SurfaceKind]
    declares_attention: bool
    declares_evidence: bool

    def validate(self) -> None:
        if not self.lifecycle:
            raise ValueError(f"{self.kind.value} must declare lifecycle states")
        if not self.surfaces:
            raise ValueError(f"{self.kind.value} must declare visual surfaces")
        if not self.declares_attention:
            raise ValueError(f"{self.kind.value} must declare attention behavior")
        if not self.declares_evidence:
            raise ValueError(f"{self.kind.value} must declare evidence behavior")


_ACTIVE = frozenset(
    {
        WorkItemState.QUEUED,
        WorkItemState.PREPARING,
        WorkItemState.RUNNING,
        WorkItemState.COMPLETED,
        WorkItemState.FAILED,
        WorkItemState.CANCELLED,
        WorkItemState.INTERRUPTED,
    }
)
_STANDARD = frozenset(
    {SurfaceKind.ACTIVITY, SurfaceKind.CONVERSATION, SurfaceKind.NOTIFICATION}
)

VISUAL_CAPABILITIES = {
    kind: VisualCapabilityDeclaration(
        kind=kind,
        lifecycle=(
            frozenset(
                {
                    WorkItemState.AWAITING_USER,
                    WorkItemState.RUNNING,
                    WorkItemState.DECLINED,
                }
            )
            if kind is WorkItemKind.DECISION
            else _ACTIVE
        ),
        surfaces=(
            frozenset({SurfaceKind.BLOCKING, SurfaceKind.ACTIVITY})
            if kind is WorkItemKind.DECISION
            else frozenset(
                {SurfaceKind.TOOL, SurfaceKind.ACTIVITY, SurfaceKind.NOTIFICATION}
            )
            if kind is WorkItemKind.EXTERNAL
            else _STANDARD
        ),
        declares_attention=True,
        declares_evidence=True,
    )
    for kind in WorkItemKind
}


def audit_visual_capabilities() -> tuple[str, ...]:
    violations: list[str] = []
    for kind in WorkItemKind:
        declaration = VISUAL_CAPABILITIES.get(kind)
        if declaration is None:
            violations.append(f"missing:{kind.value}")
            continue
        try:
            declaration.validate()
        except ValueError as error:
            violations.append(str(error))
    return tuple(violations)


__all__ = [
    "VISUAL_CAPABILITIES",
    "VisualCapabilityDeclaration",
    "audit_visual_capabilities",
]
