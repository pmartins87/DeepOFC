# External solver research baseline — 2026-08-27

This document freezes the strategic baseline that must be used for every external-solver comparison started on 2026-08-27.

## Frozen source baseline

- Repository: `pmartins87/DeepOFC`
- Strategic branch: `strategy/m5r-frozen-policy-br-certification`
- Frozen commit: `c3430819d6cb22c8ad823791a35374d56a88a32a`
- Draft PR: `#19` — `OpenOFC M5R: establish frozen-policy exact best-response certification authority`
- Strategic certification status at freeze: **REAL = 0/50**
- No external component is part of this baseline.

The research branch `research/external-ofc-solver-audit-20260827` was created directly from the frozen commit above. External research must not silently alter the M5R strategic branch.

## Proven M5R evidence available at freeze

The following GitHub Actions runs completed successfully before or during baseline freeze:

- M5R-B exact frozen-policy BR validation ladder: run `33129695535` — PASS.
- M5R-D rigorous prefix-subtree BR interval: run `33130303602` — PASS.
- M5R-E rigorous deep opponent-branch BR interval: run `33130542751` — PASS.
- M5R-F target-width missed-deviation budget controller: run `33130749073` — PASS, including mechanics, Joker P0/P1, hidden-discard P0/P1 and aggregate.

M5R-F aggregate artifact:

- name: `openofc-m5r-target-width-budget-controller-pilot`
- artifact ZIP digest: `sha256:01e30e23bbfd2450b4fca2f48b068919c8a686bc2739de4054f09f66bf5ebbdc`

These gates validate reduced-game reference/evaluator architecture and bounded missed-deviation mechanics. They do **not** certify any real 50-state route.

## Baseline comparison rule

Any proposed external idea must be introduced as an isolated candidate and evaluated against this frozen baseline. A component may replace baseline behavior only after all of the following are true:

1. target-game rule compatibility is explicitly established;
2. semantic invariants and hidden-information rules pass;
3. the candidate is deterministic/reproducible where the baseline requires determinism;
4. A/B evidence demonstrates a material gain or a correctness repair;
5. certification authority is not weakened;
6. runtime/OpenHoldem integration remains a separate gate from strategic quality.

A more sophisticated implementation, a larger neural network, more training steps, or a higher self-reported win rate is not sufficient evidence for replacement.
