"""
Auxiliary project stage heuristic.

Provides a lightweight classification of the project stage for contextual consumption. It does not represent a central state layer of the product and should not be expanded as if `core.state` fosse um subsistema amplo.
"""

from pathlib import Path


class ProjectState:
    """Small helper to detect the approximate project stage."""

    @staticmethod
    def detect_stage(project_root: Path) -> str:
        """
        Detects the development stage of the project based on file structure and history.

        Args:
            project_root: Path to project root

        Returns:
            One of: greenfield, early_stage, growth, maintenance, legacy
        """
        root = Path(project_root)
        if not root.exists():
            return "greenfield"

        # Count files (approximate)
        file_count = 0
        has_tests = (root / "tests").exists() or (root / "test").exists()

        try:
            for _ in root.rglob("*"):
                file_count += 1
                if file_count > 1000:
                    break
        except Exception as _e:
            pass  # silenced: {_e}

        if file_count < 5:
            return "greenfield"

        if file_count < 50:
            return "early_stage"

        if file_count < 500:
            return "growth"

        if not has_tests and file_count > 200:
            return "legacy"

        return "maintenance"
