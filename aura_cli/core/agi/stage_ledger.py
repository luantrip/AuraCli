"""Durable per-stage accounting for AGI executions."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
import json
from pathlib import Path
import time
from typing import Optional


@dataclass
class Stage:
    label: str
    description: str = ""
    started_at: float = field(default_factory=time.time)
    completed_at: Optional[float] = None
    usd_cost: float = 0.0
    input_tokens: int = 0
    output_tokens: int = 0
    fell_back: bool = False
    kept_base: bool = False
    cached: bool = False
    error: Optional[str] = None
    notes: str = ""

    def complete(self, *, usd_cost: float = 0.0, input_tokens: int = 0,
                 output_tokens: int = 0) -> Stage:
        self.completed_at = time.time()
        self.usd_cost = usd_cost
        self.input_tokens = input_tokens
        self.output_tokens = output_tokens
        return self


class StageLedger:
    """Collects auditable stage results without depending on the LLM layer."""

    def __init__(self, task_id: str) -> None:
        self.task_id = task_id
        self.stages: list[Stage] = []

    def record_stage(self, stage: Stage) -> Stage:
        self.stages.append(stage)
        return stage

    def start(self, label: str, description: str = "") -> Stage:
        return self.record_stage(Stage(label=label, description=description))

    def total_cost(self) -> float:
        return sum(stage.usd_cost for stage in self.stages)

    def summary(self) -> dict:
        return {
            "task_id": self.task_id,
            "stages": len(self.stages),
            "completed": sum(stage.completed_at is not None for stage in self.stages),
            "total_cost": self.total_cost(),
            "input_tokens": sum(stage.input_tokens for stage in self.stages),
            "output_tokens": sum(stage.output_tokens for stage in self.stages),
            "fallbacks": sum(stage.fell_back for stage in self.stages),
            "cached": sum(stage.cached for stage in self.stages),
        }

    def save(self, path: Path) -> None:
        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        payload = {"summary": self.summary(), "stages": [asdict(stage) for stage in self.stages]}
        target.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")

    @classmethod
    def load(cls, path: Path) -> StageLedger:
        payload = json.loads(Path(path).read_text(encoding="utf-8"))
        ledger = cls(payload["summary"]["task_id"])
        ledger.stages = [Stage(**item) for item in payload.get("stages", [])]
        return ledger
