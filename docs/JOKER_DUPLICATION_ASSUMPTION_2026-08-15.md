# DeepOFC — Joker duplication assumption frozen 2026-08-15

## Status

This document records a **project decision supplied by the user**, not a fact independently proven by the current KKPoker evidence.

The in-client rule says that a Joker may represent another playing card to form the strongest hand. The supplied Fantasy replay further proves that both physical Jokers may be used simultaneously and may take different nominal values in one row. However, the supplied evidence does not directly show a Joker copying a nominal card already physically present.

For DeepOFC strategy/scoring we now deliberately assume the following stronger wildcard contract.

## Frozen substitution rule

Each physical Joker (`JK1` and `JK2`) is evaluated independently.

Its nominal substitution domain is the complete 52-card standard nominal deck:

```text
{2c..Ac, 2d..Ad, 2h..Ah, 2s..As}
```

Substitutions are **with replacement**.

Therefore:

1. a Joker may assume a nominal card that already exists physically in the same row;
2. a Joker may assume a nominal card that exists physically elsewhere on a known board;
3. `JK1` and `JK2` may assume the same nominal card;
4. wildcard assignment never changes canonical physical identity: the state continues to store `JK1`/`JK2`, not the substituted standard card;
5. the evaluator selects the strongest resulting poker `HandRank`; if multiple nominal assignments produce the same rank and tiebreak, they are strategically equivalent for row comparison and royalties and no arbitrary nominal assignment is persisted.

This means the evaluator is not constrained by standard-deck card uniqueness when choosing a Joker's nominal value.

## Why this is represented as an explicit assumption

The current gameplay evidence proves persistent physical Joker identity and proves simultaneous two-Joker use, but it does not prove nominal duplication. DeepOFC is intentionally moving forward on the user's stated assumption because it matches the expected behavior of this class of wildcard games.

If future KKPoker evidence contradicts it, this contract and all dependent golden tests must be deliberately revised rather than silently patched around the discrepancy.

## Five-of-a-Kind boundary remains fail-closed

Allowing substitution with replacement creates one new edge that the published KKPoker hand/royalty material does not define: **Five-of-a-Kind** can become nominally reachable, for example:

```text
As Ah Ad JK1 JK2
```

if both Jokers may represent an Ace.

The current published royalty tables stop at Quads / Straight Flush / Royal Flush and do not state:

- whether Five-of-a-Kind is recognized as a separate category;
- where it ranks relative to Straight Flush / Royal Flush;
- what Middle or Bottom royalty it receives.

DeepOFC therefore accepts duplicate substitutions generally but deliberately raises a fail-closed error when Five-of-a-Kind becomes reachable in a five-card row. It must not silently downgrade such a state to Quads or invent a royalty.

Top-row play is unaffected by this specific ambiguity because Top has only three cards and its strongest published category remains Trips.

## Executable implementation

`deepofc/scoring.py` now evaluates Joker rows by exact enumeration over all nominal substitutions with replacement:

- one Joker: 52 nominal assignments;
- two Jokers: 52 x 52 = 2,704 nominal assignments.

The row's maximum `HandRank` is selected exactly. The result is cached by canonical row contents for reuse.

Regression tests freeze, among other cases:

- `Qs Qh JK1 -> QQQ` on Top;
- supplied-real-pattern `Js 9s 7s JK1 JK2 -> J-high Straight Flush`;
- `As 9s 7s 2s JK1 -> Flush A,A,9,7,2`, proving a Joker may copy an already-present `As` nominal;
- `As 9s 2s JK1 JK2 -> Flush A,A,A,9,2`, proving both Jokers may choose the same nominal `As`;
- `As Ah Ad JK1 JK2` fails closed because Five-of-a-Kind ranking/royalty remains undefined.

The DeepOFC CI run `31883031063` passed after these tests were added.

## Consequence for the roadmap

The former R1 question "may a Joker duplicate an existing physical standard card / may both Jokers map to the same nominal card?" is no longer an open design question for DeepOFC: it is resolved by project assumption as **yes**.

The remaining Joker-scoring blocker is narrower and explicit:

```text
Five-of-a-Kind hierarchy and royalty semantics, if that nominal outcome is recognized by KKPoker.
```
