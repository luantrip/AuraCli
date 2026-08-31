# Founder Business Skills

`founder` is AuraCli's native business-validation skill package. It converts
the external founder workflow into AuraCli-native artifacts and deterministic
Python primitives.

## Capabilities

- seeded buyer-profile generation and answer tallying;
- price-sensitivity summaries from ordered survey answers;
- contribution, break-even, ramp, payback and cash calculations;
- transparent `Profitable`, `Not yet` or `Incomplete` plan verdicts;
- guided playbooks for board review, competitors, consumer research, pricing,
  offer, CFO, marketing, brand, operations and launch.

The skill document is available at
`aura_cli/core/skills/founder/SKILL.md`. Its calculations live beside it in
`aura_cli/core/skills/founder/` and do not require network access.

## Evidence rules

Simulated buyers are research signals, not customers, testimonials or forecasts.
Costs, competitor facts, permits and market claims must remain explicit inputs
or sourced evidence. The final verdict is computed from those inputs and never
written by hand.

Founder artifacts should be stored through Aura's project artifact layout,
keeping generated plans out of the source tree.
