"""Graphite modal styling and view projections for CLI settings."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from prompt_toolkit.styles import Style

GRAPHITE_COLORS = {
    "background": "#0b0d10",
    "surface": "#15181d",
    "surface_active": "#242a33",
    "border": "#3a414c",
    "text": "#e6e9ef",
    "muted": "#8b949e",
    "accent": "#7aa2f7",
    "success": "#9ece6a",
}


def graphite_dialog_style() -> Style:
    """Return a complete prompt-toolkit dialog theme with no blue defaults."""
    c = GRAPHITE_COLORS
    return Style.from_dict(
        {
            "background": f"bg:{c['background']}",
            "dialog": f"bg:{c['surface']} {c['text']}",
            "dialog frame.border": f"bg:{c['surface']} {c['border']}",
            "dialog frame.label": f"bg:{c['surface']} {c['text']} bold",
            "dialog.body": f"bg:{c['surface']} {c['text']}",
            "dialog shadow": f"bg:{c['background']}",
            "dialog.body label": f"bg:{c['surface']} {c['muted']}",
            "radio-list": f"bg:{c['surface']} {c['text']}",
            "radio": f"bg:{c['surface']} {c['muted']}",
            "radio-selected": f"bg:{c['surface_active']} {c['accent']} bold",
            "radio-checked": f"bg:{c['surface_active']} {c['success']} bold",
            "radio-number": f"bg:{c['surface']} {c['border']}",
            "button": f"bg:{c['surface_active']} {c['muted']}",
            "button.focused": f"bg:{c['accent']} {c['background']} bold",
            "text-area": f"bg:{c['background']} {c['text']}",
            "text-area focused": f"bg:{c['background']} {c['text']}",
        }
    )


@dataclass(frozen=True)
class ModelOptionView:
    model_id: str
    label: str
    provider: str
    active: bool


def build_model_options(
    models: Mapping[str, Mapping[str, Any]], current_model: str
) -> tuple[ModelOptionView, ...]:
    """Build stable, provider-grouped labels for the modal model picker."""
    projected = []
    for model_id, info in models.items():
        provider = str(info.get("provider", "Outro")).strip().title()
        name = str(info.get("name", model_id)).strip()
        active = model_id == current_model
        marker = "●" if active else "○"
        suffix = " · atual" if active else ""
        projected.append(
            ModelOptionView(
                model_id=model_id,
                label=f"{marker}  {name} · {provider}{suffix}",
                provider=provider,
                active=active,
            )
        )
    return tuple(
        sorted(
            projected,
            key=lambda item: (not item.active, item.provider, item.label.casefold()),
        )
    )


def settings_summary(active_providers: int, model: str, theme: str) -> str:
    """Compact modal header with explicit hierarchy and navigation hint."""
    return (
        f"{active_providers}/6 provedores  ·  {model}  ·  {theme}\n"
        "↑↓ navegar   Enter abrir   Esc voltar"
    )


__all__ = [
    "GRAPHITE_COLORS",
    "ModelOptionView",
    "build_model_options",
    "graphite_dialog_style",
    "settings_summary",
]
