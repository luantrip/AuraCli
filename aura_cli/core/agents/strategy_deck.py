"""Strategy deck for diversified subagent execution.

Provides ``StrategyDeck`` which loads the three-axis strategy cards
(reasoning_mode × workflow × strategy) and deals them uniformly at random
with no repeats across a single draw. A ``AgentCard`` is injected into
a subagent's system prompt via ``StrategyInjector`` to produce diverse,
independent approaches to the same task.

The canonical cards file lives under ``aura_cli/data/arena/strategies.json``.
The deck falls back gracefully when that file is absent (unit tests, stripped
distributions) by generating a minimal synthetic deck.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import json
from pathlib import Path
import random
from typing import Optional

from aura_cli.core.logger import get_logger

logger = get_logger(__name__)

# Default path to the bundled strategies file.
_DEFAULT_STRATEGIES_PATH = (
    Path(__file__).parent.parent.parent / "data" / "arena" / "strategies.json"
)

# Maximum characters allowed for a card when injected into a prompt.
_CARD_MAX_CHARS = 800

# ─── Card dataclass ──────────────────────────────────────────────────────────


@dataclass(frozen=True)
class AgentCard:
    """A strategy card assigned to one subagent.

    Every card is the cross-product of exactly one entry from each of the
    three axes: reasoning mode, workflow, and strategy.
    """

    reasoning_id: str
    reasoning_name: str
    reasoning_how: str
    workflow_id: str
    workflow_name: str
    workflow_how: str
    strategy_id: str
    strategy_name: str
    strategy_how: str

    def short_label(self) -> str:
        """Return a one-line human-readable summary of the card."""
        return (
            f"{self.reasoning_name} / {self.workflow_name} / {self.strategy_name}"
        )

    def to_dict(self) -> dict:
        """Serialise to a plain dict (for JSON storage in arena state)."""
        return {
            "reasoning_id": self.reasoning_id,
            "reasoning_name": self.reasoning_name,
            "reasoning_how": self.reasoning_how,
            "workflow_id": self.workflow_id,
            "workflow_name": self.workflow_name,
            "workflow_how": self.workflow_how,
            "strategy_id": self.strategy_id,
            "strategy_name": self.strategy_name,
            "strategy_how": self.strategy_how,
        }

    @classmethod
    def from_dict(cls, data: dict) -> AgentCard:
        """Deserialise from a plain dict."""
        return cls(**data)


# ─── Deck ────────────────────────────────────────────────────────────────────


@dataclass
class StrategyDeck:
    """Loads and deals strategy cards from a JSON file.

    Cards are the cartesian product of all reasoning modes, workflows, and
    strategies in the JSON file.  ``draw(n)`` deals *n* unique cards spread
    uniformly across all three axes so that every reasoning mode and workflow
    appears at least once before any is repeated.

    Args:
        strategies_path: Path to the JSON file. Defaults to the bundled file.
    """

    strategies_path: Path = field(
        default_factory=lambda: _DEFAULT_STRATEGIES_PATH
    )
    _reasoning: list[dict] = field(default_factory=list, init=False, repr=False)
    _workflows: list[dict] = field(default_factory=list, init=False, repr=False)
    _strategies: list[dict] = field(default_factory=list, init=False, repr=False)
    _loaded: bool = field(default=False, init=False, repr=False)

    # ── Loading ──────────────────────────────────────────────────────────────

    def _ensure_loaded(self) -> None:
        if self._loaded:
            return
        path = Path(self.strategies_path)
        if path.exists():
            try:
                with path.open(encoding="utf-8") as fh:
                    data = json.load(fh)
                self._reasoning = list(data.get("reasoning") or [])
                self._workflows = list(data.get("workflows") or [])
                self._strategies = list(data.get("strategies") or [])
                logger.debug(
                    "StrategyDeck loaded %d reasoning × %d workflows × %d strategies "
                    "from %s",
                    len(self._reasoning),
                    len(self._workflows),
                    len(self._strategies),
                    path,
                )
            except Exception as exc:
                logger.warning("Failed to load strategies.json (%s); using defaults", exc)
                self._use_defaults()
        else:
            logger.debug("strategies.json not found at %s; using defaults", path)
            self._use_defaults()
        self._loaded = True

    def _use_defaults(self) -> None:
        """Minimal synthetic deck used when the JSON file is absent."""
        self._reasoning = [
            {"id": "first-principles", "name": "First principles",
             "how": "Strip to facts. Rebuild from axioms."},
            {"id": "adversarial", "name": "Adversarial",
             "how": "List every failure mode first, then build against them."},
            {"id": "decomposition", "name": "Decomposition",
             "how": "Break into independent sub-problems. Solve each, then integrate."},
        ]
        self._workflows = [
            {"id": "tdd", "name": "TDD",
             "how": "Write the test first. Then write the minimum code to pass it."},
            {"id": "scratch-and-refine", "name": "Scratch & Refine",
             "how": "Draft quickly, then refine in a second pass."},
        ]
        self._strategies = [
            {"id": "simple-first", "name": "Simplest first",
             "how": "Choose the simplest solution that meets every requirement."},
            {"id": "defensive", "name": "Defensive",
             "how": "Prefer explicit error handling and safe defaults."},
        ]

    # ── Public API ────────────────────────────────────────────────────────────

    @property
    def reasoning(self) -> list[dict]:
        self._ensure_loaded()
        return self._reasoning

    @property
    def workflows(self) -> list[dict]:
        self._ensure_loaded()
        return self._workflows

    @property
    def strategies(self) -> list[dict]:
        self._ensure_loaded()
        return self._strategies

    def total_combinations(self) -> int:
        """Return the number of unique cards in the full product."""
        self._ensure_loaded()
        return len(self._reasoning) * len(self._workflows) * len(self._strategies)

    def draw(
        self, n: int, seed: Optional[int] = None
    ) -> list[AgentCard]:
        """Draw *n* unique cards with uniform spread across all axes.

        The spread algorithm cycles through each axis in shuffled order so that
        a run of *n* agents uses every reasoning mode at least once before any
        repeats, and similarly for workflows and strategies.

        Args:
            n: Number of cards to draw. Must be >= 1.
            seed: Optional RNG seed for reproducibility.

        Returns:
            List of *n* unique ``AgentCard`` objects.

        Raises:
            ValueError: if n < 1.
        """
        if n < 1:
            raise ValueError(f"n must be >= 1, got {n}")
        self._ensure_loaded()

        rng = random.Random(seed)

        # Shuffle each axis independently for uniform spread.
        r_list = self._reasoning[:]
        w_list = self._workflows[:]
        s_list = self._strategies[:]
        rng.shuffle(r_list)
        rng.shuffle(w_list)
        rng.shuffle(s_list)

        cards: list[AgentCard] = []
        seen: set[tuple[str, str, str]] = set()

        # Generate by cycling axes, ensuring uniqueness.
        r_idx = w_idx = s_idx = 0
        attempts = 0
        max_attempts = max(n * 20, 200)

        while len(cards) < n and attempts < max_attempts:
            attempts += 1
            r = r_list[r_idx % len(r_list)]
            w = w_list[w_idx % len(w_list)]
            s = s_list[s_idx % len(s_list)]
            key = (r["id"], w["id"], s["id"])
            if key not in seen:
                seen.add(key)
                cards.append(
                    AgentCard(
                        reasoning_id=r["id"],
                        reasoning_name=r["name"],
                        reasoning_how=r["how"],
                        workflow_id=w["id"],
                        workflow_name=w["name"],
                        workflow_how=w["how"],
                        strategy_id=s["id"],
                        strategy_name=s["name"],
                        strategy_how=s["how"],
                    )
                )
            # Advance axes in round-robin to spread evenly.
            r_idx += 1
            if r_idx % len(r_list) == 0:
                w_idx += 1
            if w_idx % len(w_list) == 0:
                s_idx += 1

        if len(cards) < n:
            # Exhausted unique combinations — start re-using with fresh shuffle.
            rng.shuffle(r_list)
            rng.shuffle(w_list)
            rng.shuffle(s_list)
            r_idx = w_idx = s_idx = 0
            while len(cards) < n:
                r = r_list[r_idx % len(r_list)]
                w = w_list[w_idx % len(w_list)]
                s = s_list[s_idx % len(s_list)]
                cards.append(
                    AgentCard(
                        reasoning_id=r["id"],
                        reasoning_name=r["name"],
                        reasoning_how=r["how"],
                        workflow_id=w["id"],
                        workflow_name=w["name"],
                        workflow_how=w["how"],
                        strategy_id=s["id"],
                        strategy_name=s["name"],
                        strategy_how=s["how"],
                    )
                )
                r_idx += 1
                if r_idx % len(r_list) == 0:
                    w_idx += 1

        return cards[:n]

    def draw_one(self, seed: Optional[int] = None) -> AgentCard:
        """Draw a single card at random."""
        return self.draw(1, seed=seed)[0]

    def card_for_persona(self, persona_name: str) -> AgentCard:
        """Map an existing persona name to the most compatible card.

        Falls back to ``draw_one()`` with a deterministic seed derived from
        the persona name so the mapping is stable across runs.
        """
        self._ensure_loaded()
        seed = sum(ord(c) for c in persona_name)

        # Attempt fuzzy match on reasoning/workflow by persona name keywords.
        r_map: dict[str, str] = {
            "architect": "systems-thinking",
            "planner": "decomposition",
            "refactor": "first-principles",
            "security": "adversarial",
            "test": "inversion",
            "code": "worked-example",
        }
        w_map: dict[str, str] = {
            "test": "tdd",
            "refactor": "scratch-and-refine",
        }

        r_id: Optional[str] = None
        w_id: Optional[str] = None
        for keyword, mapped_id in r_map.items():
            if keyword in persona_name.lower():
                r_id = mapped_id
                break
        for keyword, mapped_id in w_map.items():
            if keyword in persona_name.lower():
                w_id = mapped_id
                break

        # Draw a candidate card and override matched axes.
        card = self.draw_one(seed=seed)
        if r_id or w_id:
            r_item = next(
                (x for x in self._reasoning if x["id"] == r_id), None
            ) if r_id else None
            w_item = next(
                (x for x in self._workflows if x["id"] == w_id), None
            ) if w_id else None
            return AgentCard(
                reasoning_id=(r_item or {}).get("id", card.reasoning_id),
                reasoning_name=(r_item or {}).get("name", card.reasoning_name),
                reasoning_how=(r_item or {}).get("how", card.reasoning_how),
                workflow_id=(w_item or {}).get("id", card.workflow_id),
                workflow_name=(w_item or {}).get("name", card.workflow_name),
                workflow_how=(w_item or {}).get("how", card.workflow_how),
                strategy_id=card.strategy_id,
                strategy_name=card.strategy_name,
                strategy_how=card.strategy_how,
            )
        return card
