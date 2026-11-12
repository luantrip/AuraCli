"""Constitution wizard body (decomposed from ConstitutionScreen)."""

from __future__ import annotations

from typing import Any, Callable, Dict, Optional

from textual import on
from textual.app import ComposeResult
from textual.containers import Container, Horizontal, Vertical
from textual.widgets import Button, Input, Label, Select, Static

_STAGE_CHOICES = [
    ("MVP/Prototyping (speed-focused)", "MVP/Prototyping"),
    ("Stable Production (safety & testing focused)", "Stable Production"),
    ("Legacy Refactoring (maintain compatibility)", "Legacy Refactoring"),
    ("Full Overhaul (complete reorganisation)", "Full Overhaul"),
]

_STAGE_BEHAVIORS: Dict[str, str] = {
    "MVP/Prototyping": (
        "Permissive and speed-focused. May suggest quick and experimental solutions. "
        "Tests are recommended but not mandatory."
    ),
    "Stable Production": (
        "Conservative and test-obsessed. Every change must have unit tests. "
        "Refactorings must be incremental and safe."
    ),
    "Legacy Refactoring": (
        "Cuidadoso e focado em compatibilidade. Manter interfaces existentes quando "
        "possible. Gradual, tested refactorings."
    ),
    "Caos Total": (
        "Complete reorganization needed. May suggest major refactorings and "
        "architectural changes. Documentation and tests are critical."
    ),
}

_QUESTIONS = [
    ("stack", "Stack principal (ex: Python + FastAPI, Node.js + React)"),
    ("database", "Banco de dados (ex: PostgreSQL, MongoDB, SQLite)"),
    ("api_style", "Estilo da API (ex: REST, GraphQL, gRPC)"),
    ("patterns", "Design patterns (e.g. Repository, Clean Architecture)"),
    ("rules", "Other important rules or conventions"),
]


class ConstitutionWizardPanel(Container):
    """Multi-step constitution interview."""

    def __init__(
        self,
        on_complete: Optional[Callable[[str], None]] = None,
        on_cancel: Optional[Callable[[], Any]] = None,
        **kwargs,
    ) -> None:
        super().__init__(id="constitution_wizard", **kwargs)
        self._on_complete = on_complete
        self._cancel_callback = on_cancel
        self._step = 0
        self._answers: Dict[str, str] = {}

    def compose(self) -> ComposeResult:
        yield Static("", id="step-label")
        with Vertical(id="content"):
            yield Select(
                options=_STAGE_CHOICES,
                prompt="Select the project stage",
                id="stage-select",
            )
            yield Label("", classes="question-label", id="question-label")
            yield Input(placeholder="Sua resposta...", id="answer-input")
            yield Static("", id="summary")
        with Horizontal(id="buttons"):
            yield Button("Cancel", variant="error", id="btn-cancel")
            yield Button("Next →", variant="primary", id="btn-next")

    def on_mount(self) -> None:
        self._render_step()

    def _render_step(self) -> None:
        stage_select = self.query_one("#stage-select", Select)
        answer_input = self.query_one("#answer-input", Input)
        question_label = self.query_one("#question-label", Label)
        summary = self.query_one("#summary", Static)
        step_label = self.query_one("#step-label", Static)
        btn_next = self.query_one("#btn-next", Button)

        total = 1 + len(_QUESTIONS) + 1
        step_label.update(f"Passo {self._step + 1} de {total}")

        if self._step == 0:
            stage_select.display = True
            answer_input.display = False
            question_label.display = False
            summary.display = False
            btn_next.label = "Next →"
        elif 1 <= self._step <= len(_QUESTIONS):
            stage_select.display = False
            answer_input.display = True
            question_label.display = True
            summary.display = False
            _, q_text = _QUESTIONS[self._step - 1]
            question_label.update(f"▣ {q_text}")
            answer_input.value = self._answers.get(_QUESTIONS[self._step - 1][0], "")
            answer_input.focus()
            btn_next.label = (
                "Next →" if self._step < len(_QUESTIONS) else "Review →"
            )
        else:
            stage_select.display = False
            answer_input.display = False
            question_label.display = False
            summary.display = True
            summary.update(self._build_summary())
            btn_next.label = "✔ Confirm"

    def _build_summary(self) -> str:
        lines = ["[bold cyan]Constitution Summary:[/bold cyan]\n"]
        for key, label in [("stage", "Stage")] + [(k, lb) for k, lb in _QUESTIONS]:
            val = self._answers.get(key, "—")
            lines.append(f"[bold]{label}:[/bold] {val}")
        return "\n".join(lines)

    def _build_constitution(self) -> str:
        stage = self._answers.get("stage", "")
        behavior = _STAGE_BEHAVIORS.get(stage, "")
        parts = [
            f"**PROJECT STAGE**\n- {stage}\n",
            f"**COMPORTAMENTO ESPERADO DO AGENTE**\n- {behavior}\n",
        ]
        for key, label in _QUESTIONS:
            val = self._answers.get(key, "Not defined")
            parts.append(f"**{label.upper()}**\n- {val}\n")
        return "\n".join(parts)

    @on(Button.Pressed, "#btn-cancel")
    def _on_cancel(self) -> None:
        if self._cancel_callback:
            self._cancel_callback()

    @on(Button.Pressed, "#btn-next")
    def _on_next(self) -> None:
        if self._step == 0:
            stage_select = self.query_one("#stage-select", Select)
            if stage_select.value is Select.BLANK:
                self.notify("Select a stage to continue.", severity="warning")
                return
            self._answers["stage"] = str(stage_select.value)
        elif 1 <= self._step <= len(_QUESTIONS):
            answer_input = self.query_one("#answer-input", Input)
            key = _QUESTIONS[self._step - 1][0]
            self._answers[key] = answer_input.value.strip()
        else:
            if self._on_complete:
                self._on_complete(self._build_constitution())
            return

        self._step += 1
        self._render_step()
