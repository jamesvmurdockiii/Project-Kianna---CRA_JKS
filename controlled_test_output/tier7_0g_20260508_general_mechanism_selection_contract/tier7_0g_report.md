# Tier 7.0g General Mechanism-Selection Contract

- Generated: `2026-05-08T19:00:57+00:00`
- Status: **PASS**
- Criteria: `7/7`
- Selected mechanism: `bounded_nonlinear_recurrent_continuous_state_interface`

## Why This Mechanism

- ESN dominates Mackey-Glass/Lorenz, indicating nonlinear recurrent state plus train-prefix readout remains stronger than v2.2 fading memory.
- NARMA10 favors explicit lag memory, indicating the next mechanism needs stronger causal memory/readout rather than only longer exposure.
- v2.2 ranks second at 8000 and beats lag/reservoir aggregate, so the path is worth repairing rather than abandoning.

## Contract

- Hypothesis: A bounded nonlinear recurrent continuous-state interface layered on v2.2 will improve standard dynamical benchmark performance by adding reusable causal state beyond fading memory alone, without task-specific labels or leakage.
- Null: Nonlinear recurrent state does not improve over v2.2 fading memory, or any improvement is matched by shuffled/permuted/frozen-state controls.
- Required lengths: `[720, 2000, 8000]`

Promotion criteria:

- aggregate geomean MSE improves at least 25 percent versus v2.2 at the valid 8000-step same-seed scoreboard
- mechanism beats lag-only aggregate or identifies a task-specific complement with predeclared claim boundary
- Mackey-Glass/Lorenz ESN gap narrows materially without worsening NARMA10
- permuted/frozen/shuffled/no-update controls do not match the promoted mechanism
- finite-stream and leakage guardrails pass
- compact regression passes before any baseline freeze

Fail or park criteria:

- no material improvement over v2.2
- shams match the candidate
- improvement appears only on a private diagnostic task
- NARMA10 or any public task regresses without a declared tradeoff
- result requires test-row fitting, future leakage, or task-specific seed hacking

Nonclaims:

- not sleep/replay
- not lifecycle/self-scaling
- not hardware transfer
- not a baseline freeze
- not AGI/ASI evidence
