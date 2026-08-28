# External two-street search vs CFR comparator — 05D contract

Status: **Q0 ACTIVE / REDUCED-GAME COMPARATOR ONLY**.

Authority: `REDUCED_GAME_STRATEGIC_COMPARATOR_NOT_CERTIFICATION`.

05C-Q1 completed successfully in run `33141974295`: all 12 search cells selected the same root action, and same-algorithm root reproducibility ceased to be discriminating. 05D therefore moves to an independent CFR-family comparator on the exact same six-world game.

## Frozen game identity

The comparator uses the exact 05C game: same coherent R3 root, same six complete physical worlds with uniform weights, same canonical information-state keys, same legal actions/transitions and exact zero-sum terminal utility. No policy may condition on world identity or illegal private/future information.

## 05D-Q0

Q0 is a mechanical/semantic smoke, not a quality verdict.

Frozen budgets:

- UCT: 5,000 iterations, seed 2026082831;
- external-sampling MCCFR: 256 global iterations, seed 2026082853.

The MCCFR implementation performs one P0 and one P1 traversal per global iteration against the same pre-update regret tables and the same sampled physical world. Traverser actions are enumerated; non-traverser actions are sampled from current regret matching. Regrets use the traverser's utility sign.

Q0 exposes only the **current regret-matching profile**. No local time average is called a CFR average. A future own-reach-weighted average requires a separate implementation/validation step.

The UCT profile is extracted from local action visit frequencies at every reached information set. Unseen information sets use an explicit uniform research fallback during cross-policy evaluation.

Fixed policy pairs are evaluated by exact enumeration over the six physical worlds:

- search vs search;
- MCCFR vs MCCFR;
- search P0 vs MCCFR P1;
- MCCFR P0 vs search P1.

Q0 also records root-policy total variation distance, information-state coverage and terminal enumeration work. No numerical comparison becomes a strategic PASS/FAIL gate.

## 05D-Q1 after Q0

If Q0 is mechanically green, Q1 may add frozen MCCFR budget/seed ladders, own-reach-weighted average policy if independently validated, policy agreement and learned-response lower bounds. Budget choices must be frozen before Q1 evidence is viewed.

## Authority firewall

05D cannot populate M5C certification evidence, emit a certification-eligible M5H manifest, create a REAL Bellman route, modify live strategy, or claim the six-world support is the real posterior. Any future certification attempt must pass M5L independently.

REAL routes remain `0/50`.
