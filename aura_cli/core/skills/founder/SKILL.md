---
name: founder
version: 1.0.0
description: Native AuraCli business validation skill for research, pricing, economics, launch planning and transparent business-plan verdicts.
author: Aura Core Team
---
# Founder

Use this skill to validate a business idea before committing significant money.
The workflow produces explicit artifacts and never treats simulated research as
real customer evidence.

## Workflow

1. Define the idea, target customer, price and assumptions.
2. Review the idea through board, competitor and customer lenses.
3. Run a seeded consumer panel when a fast objection map is useful.
4. Analyse price sensitivity and unit economics from explicit inputs.
5. Design the offer, marketing, operations and launch experiment.
6. Compile a verdict: `Profitable`, `Not yet` or `Incomplete`.

## Native tools

Use `aura_cli.core.skills.founder.deal_buyers` for reproducible buyer cards,
`analyse_price_sensitivity` for ordered price answers,
`analyse_economics` for contribution/break-even/ramp calculations, and
`compile_plan` for a verdict whose checks remain inspectable.

## Rules

- Never invent costs, competitors, customer answers or legal requirements.
- Mark simulated buyers as research, never as testimonials or forecasts.
- Keep source assumptions alongside every numeric result.
- Prefer a cheap real-world experiment before a large launch.
- Use the existing AuraCli Arena only when multiple solution approaches need
  comparison; do not spend on a large panel without user confirmation.

## Outputs

Store founder artifacts under the project artifact directory, not in the source
tree: idea, customer profile, panel results, pricing analysis, economics,
offer, marketing, operations, launch and final plan.

The full package is split into focused playbooks for board review, competitors,
consumer, pricing, offer, CFO, marketing, brand, operations, launch and plan
assembly.
