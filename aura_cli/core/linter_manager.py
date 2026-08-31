"""Linter Manager — Auto-Validation and Self-Correction.

Manages automatic linter and compiler execution to validate generated code.
"""

from pathlib import Path
import subprocess
from typing import Dict, List, Optional, Tuple


class LinterManager:
    """Automatic code validation manager."""

    def __init__(self, project_root: Path):
        """Initialise the LinterManager."""
        self.project_root = project_root
        self.detected_linters: List[str] = []
        self._detect_available_linters()

    def _detect_available_linters(self) -> None:
        """Detect available linters and compilers in the project."""
        if (self.project_root / "package.json").exists():
            if (self.project_root / "tsconfig.json").exists():
                self.detected_linters.append("typescript")
            self.detected_linters.append("npm_lint")

        if (self.project_root / "pyproject.toml").exists() or (
            self.project_root / "setup.py"
        ).exists():
            self.detected_linters.append("python")

        if (self.project_root / "Cargo.toml").exists():
            self.detected_linters.append("rust")

        if (self.project_root / "go.mod").exists():
            self.detected_linters.append("go")

    def validate_file(self, file_path: Path) -> Tuple[bool, Optional[str], List[str]]:
        """Validate a file with the appropriate linter."""
        suffix = file_path.suffix.lower()

        if suffix == ".py" and "python" in self.detected_linters:
            return self._validate_python(file_path)
        elif suffix in [".ts", ".tsx"] and "typescript" in self.detected_linters:
            return self._validate_typescript(file_path)
        elif suffix == ".rs" and "rust" in self.detected_linters:
            return self._validate_rust(file_path)
        elif suffix == ".go" and "go" in self.detected_linters:
            return self._validate_go(file_path)

        return True, None, []

    def _validate_python(
        self, file_path: Path
    ) -> Tuple[bool, Optional[str], List[str]]:
        """Run Python linting on a file."""
        try:
            result = subprocess.run(
                ["python", "-m", "py_compile", str(file_path)],
                capture_output=True,
                text=True,
                timeout=30,
            )
            if result.returncode == 0:
                return True, None, []
            return False, result.stderr, [result.stderr]
        except Exception as e:
            return False, str(e), [str(e)]

    def _validate_typescript(
        self, file_path: Path
    ) -> Tuple[bool, Optional[str], List[str]]:
        """Run TypeScript linting on a file."""
        try:
            result = subprocess.run(
                ["npx", "tsc", "--noEmit", str(file_path)],
                capture_output=True,
                text=True,
                timeout=30,
            )
            if result.returncode == 0:
                return True, None, []
            return False, result.stderr, result.stderr.split("\n")
        except Exception as e:
            return False, str(e), [str(e)]

    def _validate_rust(self, file_path: Path) -> Tuple[bool, Optional[str], List[str]]:
        """Run Rust linting on a file."""
        try:
            result = subprocess.run(
                ["rustc", "--error-format=short", str(file_path)],
                capture_output=True,
                text=True,
                timeout=30,
            )
            if result.returncode == 0:
                return True, None, []
            return False, result.stderr, result.stderr.split("\n")
        except Exception as e:
            return False, str(e), [str(e)]

    def _validate_go(self, file_path: Path) -> Tuple[bool, Optional[str], List[str]]:
        """Run Go linting on a file."""
        try:
            result = subprocess.run(
                ["go", "build", "-o", "/dev/null", str(file_path)],
                capture_output=True,
                text=True,
                timeout=30,
            )
            if result.returncode == 0:
                return True, None, []
            return False, result.stderr, result.stderr.split("\n")
        except Exception as e:
            return False, str(e), [str(e)]

    def get_available_linters(self) -> List[str]:
        """Return a list of available linters."""
        return self.detected_linters.copy()

    def auto_fix_file(self, file_path: Path) -> bool:
        """Tenta corrigir automaticamente erros no arquivo."""
        suffix = file_path.suffix.lower()

        if suffix == ".py":
            return self._auto_fix_python(file_path)

        return False

    def _auto_fix_python(self, file_path: Path) -> bool:
        """Auto-fix Python lint issues using ruff."""
        try:
            # Try to use black for formatting
            result = subprocess.run(
                ["black", "--quiet", str(file_path)], capture_output=True, timeout=30
            )
            return result.returncode == 0
        except Exception:
            return False

    def validate_generated_files(
        self, file_paths: List[Path]
    ) -> Dict[str, Tuple[bool, Optional[str]]]:
        """Validate a list of generated files."""
        results = {}
        for file_path in file_paths:
            is_valid, error_msg, _ = self.validate_file(file_path)
            results[str(file_path)] = (is_valid, error_msg)
        return results
