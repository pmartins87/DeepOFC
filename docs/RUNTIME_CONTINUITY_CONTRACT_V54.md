# DeepOFC runtime continuity contract v5.4

Date: 2026-08-20

This contract is frozen from the v5.3 field failure and supersedes any runtime behavior in which a perception, reconstruction, planning, drag, Confirm, or transition error can place OpenOFC in an absorbing `BLOCKED` state.

## Primary invariant: the process never dies because one scrape was wrong

DeepOFC is a continuously observing player. Every scrape is evidence about the game *as it is currently visible*. A bad scrape may invalidate **that observation** and may therefore suppress a click from that observation, but it must never invalidate all future observations.

The required liveness invariant is:

> `fault -> log -> fresh scrape -> reconstruct/reacquire -> continue`

There is no legitimate transition of the runtime state machine to a permanent error sink merely because one card, dealer marker, actor marker, row, drag result, or round transition was ambiguous or inconsistent.

The corresponding safety invariant is also preserved:

> uncertainty must not authorize a guessed drag or guessed Confirm.

Therefore “continue playing despite faults” means that the **observer and recovery loop always continues**. It does not mean clicking from an observation that the recognizer itself considers unsafe.

## Current-screen authority

Process memory is useful evidence, not authority over the pixels.

If stored lineage says “still round 3” while fresh, self-consistent current-screen evidence says “round 4”, the current screen wins. The stored state is retired, the stale action plan is discarded, and the runtime replans from the accepted current state.

This rule directly addresses the v5.3 failure:

`Hero incoming card identities changed within the same round`

That error is now a recoverable observation fault. A bounded sequence of changed-but-rejected scrapes enters `REACQUIRE`; it cannot leave the controller waiting forever on the prior round.

Required durable events include:

- `SCRAPE_FAULT`;
- `WAIT_NEXT_STALE` / `REACQUIRE_BEGIN`;
- `REACQUIRE_ACCEPT`;
- `REACQUIRE_REJECT`;
- `BOOTSTRAP_ACCEPT`;
- `SCREEN_AUTHORITY_ACCEPT`;
- transaction-specific retry/receipt events in the executor.

## Bootstrap from any game state

A new OpenHoldem process must not depend on memory from a previous process. It must continuously attempt to reconstruct the current table and resume from whatever state is present.

Required bootstrap targets are:

- normal round 0, 1, 2, 3 or 4;
- before Hero may act;
- while Hero may pre-arrange;
- while Hero may Confirm;
- after Confirm while waiting for a transition;
- Fantasy with 14, 15, 16 or 17 cards;
- partially arranged Fantasy after one or more drags;
- post-hand / transition screens, which remain observation states rather than errors.

A key architectural gap remains in the existing normal-state bridge: `reconstruct_observation()` currently requires prior canonical state for normal mid-hand frames because `RawOFCObservation` does not identify which Hero row cards are current-round tentative cards after a restart. That dependency is incompatible with this contract.

The R9 bridge must therefore become self-contained enough to bootstrap a normal hand in progress. The preferred solution is to expose current-round physical-card identity/dragability from the current UI when available. If the client pixels do not uniquely expose that distinction in one frame, the runtime must maintain a bounded multi-frame/hypothesis reacquisition procedure instead of declaring the whole session unrecoverable.

## No permanent `BLOCKED` phase

The production continuity machine is defined around:

- `BOOTSTRAP`;
- `TRACKING`;
- `WAIT_TRANSITION`;
- `REACQUIRE`.

There is deliberately no terminal `BLOCKED` state in the continuity supervisor.

Failures that were previously treated as fatal become recoverable fault classes, including at least:

- unknown/low-confidence card;
- transient animation/reflow;
- no unique dealer/actor marker;
- current incoming identity disagreement;
- previous committed lineage disagreement;
- unexpected round/state transition;
- missing or temporarily unrecognized action geometry;
- drag not yet observed;
- Confirm receipt not yet observed.

Configuration defects can make a particular action impossible, but even then the observer must continue running and logging fresh evidence. The runtime is never allowed to stop looking at the table because of the first defect it encountered.

## Transaction boundary and duplicate-action rule

Reacquisition invalidates the stale **plan**, not the table process.

After `REACQUIRE_ACCEPT`, the executor must rebuild the action plan against the newly authoritative state. It must also preserve transaction idempotence:

- never send a second Confirm merely because its receipt was temporarily unreadable;
- never repeat a drag blindly after state lineage was lost;
- first compare the current screen against the intended transaction effect;
- retry only operations whose current-screen evidence proves the retry is still required;
- use bounded retries per transaction, followed by another reacquisition cycle rather than permanent blocking.

Thus runtime continuity and duplicate-action prevention are separate invariants and both are mandatory.

## Fantasy terminology

There is one runtime state called **Fantasy**.

The number of cards is a property:

`fantasy_card_count = 14 | 15 | 16 | 17`

The project must not use `Fantasy15` as the name of a game mode, recognizer, runtime path, controller, Confirm button, source-card API, or state enum. Correct logging is for example:

`mode=FANTASY cards=15`

not:

`mode=FANTASY15`

Count-specific evidence may still say that a particular captured fixture contains 15 Fantasy cards, but the fixture count must not leak into generic architecture names. Existing historical files named `FANTASY15_*` are legacy evidence/implementation debt and must be renamed or explicitly marked count-specific before the next field package.

For OpenHoldem/TableMap integration the generic target names are therefore concepts such as:

- `ofc_fantasy_confirm_button`;
- `ofc_fantasy_recognizer_calibrated`;
- `hero_fantasy_sources`;
- `fantasy_card_count`.

A temporary compatibility alias may read an old tablemap symbol while migration is in progress, but logs and new code must use the generic terminology.

## Reference implementation in this branch

`deepofc/runtime_continuity.py` is the executable reference for state-continuity semantics. It intentionally does not own mouse transaction logic. Its tests freeze these properties:

1. a process can accept a valid current normal candidate at any round during bootstrap;
2. Fantasy is one mode for all 14–17 card counts;
3. repeated changed scrape failures force reacquisition instead of freezing `WAIT_TRANSITION`;
4. arbitrary perception faults remain recoverable and no terminal blocked phase exists;
5. a valid current screen can replace a stale stored transition expectation;
6. a valid expected next round is accepted once and then becomes stable.

The next implementation step is to port this contract into the native OpenHoldem controller/reconstructor, then replay the v5.3 failure sequence as a mandatory regression before another Windows field build.
