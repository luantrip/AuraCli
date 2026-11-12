"""F-P1-7 — the Sentinel claim stays honest.

Sentinel is a pull-based, content-hash change detector (one-shot ``scan_changes``),
not a continuous real-time watcher. These contracts stop product docs from
re-advertising a "real-time file watcher" that does not exist.
"""

from __future__ import annotations

from pathlib import Path
import re

_REPO_ROOT = Path(__file__).resolve().parents[2]

# A line that both calls it real-time AND a watcher is the misleading claim. The
# manager docstring is allowed to say "not a real-time watcher", so the contract
# targets the affirmative phrasing in product-facing tables.
_BAD_CLAIM = re.compile(r"real[\s-]?time (file )?watch", re.IGNORECASE)


def _sentinel_lines(path: Path) -> list[str]:
    return [
        line
        for line in path.read_text(encoding="utf-8").splitlines()
        if "sentinel" in line.lower()
    ]


def test_readme_does_not_call_sentinel_a_realtime_watcher() -> None:
    readme = _REPO_ROOT / "README.md"
    offenders = [line for line in _sentinel_lines(readme) if _BAD_CLAIM.search(line)]
    assert offenders == [], offenders


def test_nim_modules_doc_does_not_call_sentinel_a_realtime_watcher() -> None:
    doc = _REPO_ROOT / "docs" / "architecture" / "nim-modules.md"
    offenders = [line for line in _sentinel_lines(doc) if _BAD_CLAIM.search(line)]
    assert offenders == [], offenders


def test_sentinel_is_described_as_a_change_detector_in_readme() -> None:
    readme = _REPO_ROOT / "README.md"
    sentinel_lines = _sentinel_lines(readme)
    assert any("change detector" in line.lower() for line in sentinel_lines)
