"""Generate or verify semantic visual goldens for the Aura TUI."""

from __future__ import annotations

from argparse import ArgumentParser
from dataclasses import asdict
import json
from pathlib import Path
from typing import Any

from aura_cli.application.presentation.visual_acceptance import run_visual_scenario

ROOT = Path(__file__).resolve().parents[1]
SCENARIOS_PATH = ROOT / "tests/fixtures/visual_system/scenarios.json"
GOLDEN_PATH = ROOT / "tests/fixtures/visual_system/golden_frames.json"
VIEWPORTS = ((80, 24), (160, 40), (80, 24), (160, 40))


def build_goldens(
    scenarios: dict[str, list[dict[str, Any]]],
) -> dict[str, list[dict[str, Any]]]:
    """Replay every scenario and serialize its observable frames."""
    return {
        name: [
            asdict(frame) for frame in run_visual_scenario(events, viewports=VIEWPORTS)
        ]
        for name, events in scenarios.items()
    }


def main() -> int:
    parser = ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check",
        action="store_true",
        help="fail when the checked-in golden differs from the replay",
    )
    args = parser.parse_args()

    scenarios = json.loads(SCENARIOS_PATH.read_text(encoding="utf-8"))
    actual = build_goldens(scenarios)
    rendered = json.dumps(actual, ensure_ascii=False, indent=2) + "\n"

    if args.check:
        expected = GOLDEN_PATH.read_text(encoding="utf-8")
        if expected != rendered:
            print(f"Golden desatualizado: {GOLDEN_PATH}")
            return 1
        print(f"Golden verificado: {GOLDEN_PATH}")
        return 0

    GOLDEN_PATH.write_text(rendered, encoding="utf-8")
    print(f"Golden atualizado: {GOLDEN_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
