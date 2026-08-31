"""Test Runner Visualization Panel for Aura TUI.

Interactive test execution panel with pytest integration and real-time results.
"""

import asyncio
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import json
from pathlib import Path
import sys
from time import perf_counter
from typing import Any, Dict, List, Optional

from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.message import Message
from textual.reactive import reactive
from textual.widgets import Button, Input, ProgressBar, Static, Tree

from aura_cli.application.artifacts import ArtifactLayout


class TestStatus(Enum):
    """Test execution status."""

    PENDING = "pending"
    RUNNING = "running"
    PASSED = "passed"
    FAILED = "failed"
    SKIPPED = "skipped"
    ERROR = "error"
    CANCELLED = "cancelled"


@dataclass
class TestResult:
    """Individual test result."""

    name: str
    file_path: str
    status: TestStatus = TestStatus.PENDING
    duration_ms: int = 0
    error_message: Optional[str] = None
    stdout: str = ""
    line_number: int = 0


@dataclass
class TestSuiteResult:
    """Complete test suite result."""

    started_at: str
    completed_at: Optional[str] = None
    passed: int = 0
    failed: int = 0
    skipped: int = 0
    errors: int = 0
    total: int = 0
    duration_ms: int = 0
    coverage: Optional[float] = None
    cancelled: int = 0
    tests: List[TestResult] = field(default_factory=list)


class TestRunnerPanel(Static):
    """Interactive test runner panel for pytest integration."""

    is_running = reactive(False)
    current_test = reactive("")

    class TestsStarted(Message):
        """Emitted when test execution begins."""

        def __init__(self, test_count: int):
            """Initialize the widget."""
            super().__init__()
            self.test_count = test_count

    class TestsCompleted(Message):
        """Emitted when test execution finishes."""

        def __init__(self, result: TestSuiteResult):
            """Initialize the widget."""
            super().__init__()
            self.result = result

    class TestResultUpdated(Message):
        """Emitted when a test result is updated."""

        def __init__(self, test: TestResult):
            """Initialize the widget."""
            super().__init__()
            self.test = test

    def __init__(self, test_path: str = ".", **kwargs):
        """Initialize the widget."""
        super().__init__(**kwargs)
        self.test_path = test_path
        self.discovered_tests: Dict[str, TestResult] = {}
        self.current_suite: Optional[TestSuiteResult] = None
        self._runner_task: Optional[Any] = None
        self._current_process: Optional[asyncio.subprocess.Process] = None
        self._stop_requested = False
        self._last_export_path: Optional[Path] = None

    def compose(self) -> ComposeResult:
        """Compose the widget layout."""
        with Horizontal():
            with Vertical(classes="test-list-pane"):
                yield Static("◆ Suíte de testes", classes="pane-header")

                with Horizontal(classes="summary-bar"):
                    yield Static("✔ 0", id="passed_count", classes="summary-passed")
                    yield Static("  ✖ 0", id="failed_count", classes="summary-failed")
                    yield Static("  ⊘ 0", id="skipped_count", classes="summary-skipped")
                    yield Static("  ▥ 0%", id="coverage_display")

                yield Input(placeholder="Filtrar testes...", id="test_filter")
                yield Tree("Testes", id="test_tree", classes="test-tree")

                with Horizontal(classes="action-bar"):
                    yield Button("⚲ Descobrir", id="discover_btn")
                    yield Button("▶ Executar tudo", id="run_all_btn", variant="primary")
                    yield Button("▶ Executar selecionado", id="run_selected_btn")

            with Vertical(classes="test-output-pane"):
                yield Static("↑ Saída dos testes", classes="pane-header")
                yield ProgressBar(
                    id="test_progress", classes="progress-container", show_eta=True
                )
                yield VerticalScroll(id="test_output", classes="output-log")

                with Horizontal(classes="action-bar"):
                    yield Button(
                        "⏹ Parar", id="stop_btn", variant="error", disabled=True
                    )
                    yield Button("✖ Limpar", id="clear_btn")
                    yield Button("⊞ Exportar", id="export_btn")

    def on_mount(self) -> None:
        """Initialize widget state after mounting."""
        progress = self.query_one("#test_progress", ProgressBar)
        progress.display = False

        self.run_worker(self._discover_tests())

    def _write_log(self, message: str, log_class: str = "log-info") -> None:
        """Append a message to the log display."""
        log_container = self.query_one("#test_output", VerticalScroll)
        log_entry = Static(message, classes=f"log-entry {log_class}")
        log_container.mount(log_entry)
        log_container.scroll_end()

    def _clear_log(self) -> None:
        """Clear the log display."""
        log_container = self.query_one("#test_output", VerticalScroll)
        log_container.remove_children()

    async def _discover_tests(self) -> None:
        """Discover available tests in the project."""
        tree = self.query_one("#test_tree", Tree)
        tree.clear()

        self._write_log("Descobrindo testes...", "log-start")

        try:
            process = await asyncio.create_subprocess_exec(
                sys.executable,
                "-m",
                "pytest",
                "--collect-only",
                "-q",
                self.test_path,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await process.communicate()
            if process.returncode not in (0, 5):
                detail = stderr.decode(errors="replace").strip()
                raise RuntimeError(detail or "falha ao coletar testes com pytest")

            node_ids = [
                line.strip()
                for line in stdout.decode(errors="replace").splitlines()
                if "::" in line and not line.startswith(("=", "ERROR"))
            ]

            self.discovered_tests.clear()

            files: Dict[str, List[tuple]] = {}
            for node_id in node_ids:
                file_path, test_name = node_id.split("::", 1)
                line = 0
                if file_path not in files:
                    files[file_path] = []
                files[file_path].append((test_name, line))

                self.discovered_tests[node_id] = TestResult(
                    name=test_name,
                    file_path=file_path,
                    line_number=line,
                )

            root = tree.root
            root.expand()

            for file_path, tests in sorted(files.items()):
                file_branch = root.add(f"◇ {file_path}", expand=True)
                for test_name, line in tests:
                    file_branch.add_leaf(
                        f"● {test_name}",
                        data={"file": file_path, "name": test_name, "line": line},
                    )

            self._write_log(
                f"✔ {len(self.discovered_tests)} testes encontrados", "log-success"
            )

        except Exception as e:
            self._write_log(f"✖ Failed to discover tests: {e}", "log-error")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button press events."""
        button_id = event.button.id

        if button_id == "discover_btn":
            self.run_worker(self._discover_tests())
        elif button_id == "run_all_btn":
            self._run_all_tests()
        elif button_id == "run_selected_btn":
            self._run_selected_test()
        elif button_id == "stop_btn":
            self._stop_tests()
        elif button_id == "clear_btn":
            self._clear_log()
        elif button_id == "export_btn":
            self._export_results()

    def _run_all_tests(self) -> None:
        """Run all discovered tests."""
        if self.is_running or not self.discovered_tests:
            return

        test_names = list(self.discovered_tests.keys())
        self._runner_task = self.run_worker(self._run_tests(test_names))

    def _run_selected_test(self) -> None:
        """Run the currently selected test."""
        if self.is_running:
            return

        tree = self.query_one("#test_tree", Tree)
        selected = tree.cursor_node

        if selected and selected.data:
            file_path = selected.data.get("file")
            test_name = selected.data.get("name")

            if file_path and test_name:
                full_name = f"{file_path}::{test_name}"
                self.run_worker(self._run_tests([full_name]))

    async def _run_tests(self, test_names: List[str]) -> None:
        """Execute tests asynchronously."""
        self.is_running = True

        run_all_btn = self.query_one("#run_all_btn", Button)
        run_selected_btn = self.query_one("#run_selected_btn", Button)
        stop_btn = self.query_one("#stop_btn", Button)

        run_all_btn.disabled = True
        run_selected_btn.disabled = True
        stop_btn.disabled = False

        progress = self.query_one("#test_progress", ProgressBar)
        progress.display = True
        progress.update(total=len(test_names), progress=0)

        self._clear_log()

        self._stop_requested = False
        self.current_suite = TestSuiteResult(
            started_at=datetime.now().isoformat(),
            total=len(test_names),
        )

        self._write_log(f"▶ Executando {len(test_names)} testes...", "log-start")
        self._write_log(
            f"Iniciado às {datetime.now().strftime('%H:%M:%S')}", "log-info"
        )
        self._write_log("", "log-info")

        self.post_message(self.TestsStarted(len(test_names)))

        start_time = datetime.now()

        try:
            for i, test_name in enumerate(test_names):
                if not self.is_running:
                    break

                self.current_test = test_name
                test = self.discovered_tests.get(test_name)

                if not test:
                    continue

                test.status = TestStatus.RUNNING

                self._write_log(f"● Executando: {test.name}", "log-info")

                started = perf_counter()
                self._current_process = await asyncio.create_subprocess_exec(
                    sys.executable,
                    "-m",
                    "pytest",
                    "-q",
                    test_name,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.STDOUT,
                )
                process = self._current_process
                stdout, _ = await process.communicate()
                self._current_process = None
                output = stdout.decode(errors="replace").strip()
                test.stdout = output
                test.duration_ms = int((perf_counter() - started) * 1000)
                if self._stop_requested and not self.is_running:
                    outcome = TestStatus.CANCELLED
                elif process.returncode == 0 and " skipped" in output:
                    outcome = TestStatus.SKIPPED
                elif process.returncode == 0:
                    outcome = TestStatus.PASSED
                else:
                    outcome = TestStatus.FAILED
                test.status = outcome

                if outcome == TestStatus.PASSED:
                    self.current_suite.passed += 1
                    self._write_log(f"  ✔ PASSOU ({test.duration_ms}ms)", "log-success")
                elif outcome == TestStatus.FAILED:
                    self.current_suite.failed += 1
                    test.error_message = (
                        output or f"pytest encerrou com código {process.returncode}"
                    )
                    self._write_log(f"  ✖ FALHOU ({test.duration_ms}ms)", "log-error")
                    self._write_log(f"    {test.error_message}", "log-error")
                elif outcome == TestStatus.CANCELLED:
                    self.current_suite.cancelled += 1
                    self._write_log("  ⏹ CANCELADO", "log-warning")
                else:
                    self.current_suite.skipped += 1
                    self._write_log("  ⊘ IGNORADO", "log-warning")

                self.current_suite.tests.append(test)

                progress.update(progress=i + 1)
                self._update_summary()

                self._update_test_tree_item(test)

                self.post_message(self.TestResultUpdated(test))

            end_time = datetime.now()
            self.current_suite.completed_at = end_time.isoformat()
            self.current_suite.duration_ms = int(
                (end_time - start_time).total_seconds() * 1000
            )

            self._write_log("", "log-info")
            self._write_log("═══════════════════════════════════════", "log-info")
            self._write_log("Resultados:", "log-start")
            self._write_log(f"  Passaram: {self.current_suite.passed}", "log-success")
            self._write_log(f"  Falharam: {self.current_suite.failed}", "log-error")
            self._write_log(f"  Ignorados: {self.current_suite.skipped}", "log-warning")
            self._write_log(f"  Total: {self.current_suite.total}", "log-info")
            self._write_log(
                f"  Cancelados: {self.current_suite.cancelled}", "log-warning"
            )
            self._write_log(
                f"  Duração: {self.current_suite.duration_ms}ms", "log-info"
            )

            if self.current_suite.failed == 0:
                self._write_log("", "log-info")
                self._write_log("✔ Todos os testes passaram!", "log-success")
            else:
                self._write_log("", "log-info")
                self._write_log(
                    f"✖ {self.current_suite.failed} testes falharam", "log-error"
                )

            self.post_message(self.TestsCompleted(self.current_suite))

        except Exception as e:
            self._write_log(f"Failed to run tests: {e}", "log-error")

        finally:
            self.is_running = False
            self.current_test = ""

            run_all_btn.disabled = False
            run_selected_btn.disabled = False
            stop_btn.disabled = True
            progress.display = False

            self._update_summary()
            self._current_process = None
            self._runner_task = None

    def _update_summary(self) -> None:
        """Update the test results summary."""
        if not self.current_suite:
            return

        passed = self.query_one("#passed_count", Static)
        failed = self.query_one("#failed_count", Static)
        skipped = self.query_one("#skipped_count", Static)
        coverage = self.query_one("#coverage_display", Static)

        passed.update(f"✔ {self.current_suite.passed}")
        failed.update(f"  ✖ {self.current_suite.failed}")
        skipped.update(f"  ⊘ {self.current_suite.skipped}")
        coverage_value = (
            f"{self.current_suite.coverage}%"
            if self.current_suite.coverage is not None
            else "—"
        )
        coverage.update(f"  ▥ {coverage_value}")

    def _update_test_tree_item(self, test: TestResult) -> None:
        """Update a test item in the tree with its result."""
        tree = self.query_one("#test_tree", Tree)

        for file_node in tree.root.children:
            for test_node in file_node.children:
                if test_node.data and test_node.data.get("name") == test.name:
                    status_icon = self._get_status_icon(test.status)
                    test_node.set_label(f"{status_icon} {test.name}")
                    break

    @staticmethod
    def _status_label(status: TestStatus) -> str:
        """Return the user-facing Portuguese label for a test status."""
        labels = {
            TestStatus.PENDING: "pendente",
            TestStatus.RUNNING: "em execução",
            TestStatus.PASSED: "passou",
            TestStatus.FAILED: "falhou",
            TestStatus.SKIPPED: "ignorado",
            TestStatus.ERROR: "erro",
            TestStatus.CANCELLED: "cancelled",
        }
        return labels.get(status, status.value)

    def _get_status_icon(self, status: TestStatus) -> str:
        """Return an icon character for a given status."""
        icons = {
            TestStatus.PENDING: "●",
            TestStatus.RUNNING: "◉",
            TestStatus.PASSED: "✔",
            TestStatus.FAILED: "✖",
            TestStatus.SKIPPED: "⊘",
            TestStatus.ERROR: "⚠",
            TestStatus.CANCELLED: "⏹",
        }
        return icons.get(status, "●")

    def _stop_tests(self) -> None:
        """Stop the running test suite and terminate its current subprocess."""
        if self.is_running:
            self._stop_requested = True
            self.is_running = False
            process = self._current_process
            if process is not None and process.returncode is None:
                process.terminate()
            self._write_log("", "log-info")
            self._write_log("⏹ Execução de testes interrompida", "log-warning")
            self.notify("Testes interrompidos", severity="warning")

    def _export_results(self) -> None:
        """Export test results to a timestamped JSON file."""
        if not self.current_suite:
            self.notify("Nenhum resultado de teste para exportar", severity="warning")
            return

        payload = {
            "started_at": self.current_suite.started_at,
            "completed_at": self.current_suite.completed_at,
            "passed": self.current_suite.passed,
            "failed": self.current_suite.failed,
            "skipped": self.current_suite.skipped,
            "cancelled": self.current_suite.cancelled,
            "errors": self.current_suite.errors,
            "total": self.current_suite.total,
            "duration_ms": self.current_suite.duration_ms,
            "coverage": self.current_suite.coverage,
            "tests": [
                {
                    "name": test.name,
                    "file_path": test.file_path,
                    "status": test.status.value,
                    "duration_ms": test.duration_ms,
                    "error_message": test.error_message,
                    "stdout": test.stdout,
                    "line_number": test.line_number,
                }
                for test in self.current_suite.tests
            ],
        }
        export_dir = ArtifactLayout().project("exports")
        export_dir.mkdir(parents=True, exist_ok=True)
        export_path = export_dir / (
            f"aura-test-results-{datetime.now().strftime('%Y%m%d-%H%M%S')}.json"
        )
        export_path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        self._last_export_path = export_path
        self.notify(f"Resultados exportados: {export_path.name}")

    def on_input_changed(self, event: Input.Changed) -> None:
        """Handle filter input changes."""
        if event.input.id == "test_filter":
            self._filter_tests(event.value)

    def _filter_tests(self, query: str) -> None:
        """Filter the test tree by search query."""
        tree = self.query_one("#test_tree", Tree)
        query_lower = query.lower()

        for file_node in tree.root.children:
            file_visible = False

            for test_node in file_node.children:
                if test_node.data:
                    test_name = test_node.data.get("name", "")
                    visible = not query or query_lower in test_name.lower()
                    test_node.display = visible  # type: ignore[attr-defined]
                    if visible:
                        file_visible = True

            file_node.display = file_visible  # type: ignore[attr-defined]

    def on_tree_node_selected(self, event: Tree.NodeSelected) -> None:
        """Handle tree node selection."""
        if event.node.data:
            test_name = event.node.data.get("name")
            file_path = event.node.data.get("file")

            if test_name and file_path:
                full_name = f"{file_path}::{test_name}"
                test = self.discovered_tests.get(full_name)

                if test:
                    self._show_test_detail(test)

    def _show_test_detail(self, test: TestResult) -> None:
        """Show detailed output for a selected test."""
        self._clear_log()

        self._write_log(f"Teste: {test.name}", "log-label")
        self._write_log(f"Arquivo: {test.file_path}:{test.line_number}", "log-label")
        self._write_log(
            f"Estado: {self._get_status_icon(test.status)} {self._status_label(test.status)}",
            "log-label",
        )

        if test.duration_ms:
            self._write_log(f"Duração: {test.duration_ms}ms", "log-label")

        if test.error_message:
            self._write_log("", "log-content")
            self._write_log("Erro:", "log-label")
            self._write_log(f"  {test.error_message}", "log-error")

        if test.stdout:
            self._write_log("", "log-content")
            self._write_log("Saída:", "log-label")
            self._write_log(test.stdout, "log-content")
