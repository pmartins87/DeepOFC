# DeepOFC OpenHoldem R9–R10 vertical-slice audit — 2026-08-16

This document corrects the stale R9/R10 status in `docs/ROADMAP.md` using the current `pmartins87/myoh_private` `deepofc` branch as authority.

## Audited OpenHoldem state

- Repository: `pmartins87/myoh_private`
- Branch: `deepofc`
- Audited head: `bdacf60787d9399c50ffe1d5a1b6acfb5f6b6adc`
- Head message: `DeepOFC R10: include Fantasy15 pixel layer in vertical regression gate`
- R10 vertical build workflow: `.github/workflows/deepofc-r10-executor-build.yml`
- Audited workflow run: `31933455400`
- Result: **SUCCESS** (`Release|Win32` OpenHoldem build plus R9/R10 contract assertions)

## What is already implemented and build-gated

### R9 — raw visual state and canonical reconstruction

The current branch already contains an isolated OFC runtime state path rather than reusing Hold'em card semantics.

Implemented:

- explicit Joker Ultimate tablemap gate;
- raw `COFCVisualObservation` separate from canonical `COFCState`;
- normal 2-player / 3-player metadata contract;
- physical 54-card identity domain with distinct persistent `JK1=52` and `JK2=53`;
- explicit normal row slots, loose Hero cards, Hero discard tracker, hidden opponent-card counts, dealer and ordered acting-chair recognition;
- source rectangles attached ephemerally to freshly scraped loose Hero physical cards;
- fail-closed duplicate-physical-card rejection;
- stateful raw→canonical reconstruction with committed-vs-pending separation;
- exact normal round progression checks for `5 / 3 / 3 / 3 / 3`;
- fail-closed mid-hand reconstruction when prior canonical state is unavailable;
- Fantasy semantic reconstruction for a one-shot 14–17-card Hero decision;
- persistent physical Joker identity across reconstruction; occurrence swapping is forbidden;
- a separately compiled Fantasy15 real-pixel recognizer/model layer.

### Fantasy recognition status

The important distinction is:

- **code/model layer exists and compiles**;
- **live/native Fantasy pixel recognition is intentionally NOT certified or routed into the scraper yet**.

At the audited head, `COFCScraper.cpp` still freezes:

```cpp
#define DEEPOFC_NATIVE_FANTASY15_RECOGNIZER_CERTIFIED 0
```

The R10 vertical workflow explicitly fails if that gate changes to `1`, or if the pixel recognizer is wired into the live scraper/autoplayer before a real-pixel native replay certification exists.

Therefore Fantasy is **infrastructure advanced, production disabled**, not missing and not live-ready.

### R10 — physical placement planning

`COFCActionPlanner` is already implemented.

It:

- accepts a canonical state plus the **same fresh raw observation** that produced it;
- resolves a requested physical card by identity from current loose-card sources;
- refuses duplicate/ambiguous/stale sources;
- maps only to explicit Top/Middle/Bottom drop targets;
- refuses any movement unless `s$ofc_drag_targets_calibrated == 1`;
- rejects already-pending cards;
- validates post-drag state by physical card identity and canonical row membership;
- requires one drag to add exactly one pending placement;
- proves every pre-existing pending placement survived unchanged.

This is the correct model for KKPoker because within-row visual slot order is not strategic state and Fantasy fan cards may reflow after every drag.

### R10 — guarded arbitrary mouse drag

The OpenHoldem mouse layer and `CCasinoInterface` already expose an arbitrary source-rectangle→target-rectangle drag primitive.

The casino wrapper refuses a drag when:

- the drag DLL entry point is absent;
- the attached HWND is invalid;
- source or target lies outside client bounds;
- the attached table has lost foreground focus.

### R10 — transactional single-drag executor

`COFCActionExecutor` is already implemented and is stronger than the stale roadmap described.

It enforces:

1. explicit `s$ofc_executor_enabled == 1` authority;
2. plan from fresh raw geometry;
3. exactly one physical drag;
4. `awaiting_verification_ = true` immediately at transaction start;
5. no second drag before a fresh canonical verification;
6. post-drag `VerifyPendingTransition` before clearing the transaction;
7. permanent fail-closed `blocked_` latch after any ambiguous post-mutation condition;
8. block persists until an explicitly known new-hand reset.

A physical primitive failure after transaction start is deliberately treated as ambiguous mutation and blocks retries.

## Live execution remains intentionally disconnected

The branch still contains the R9 hard read-only guard in `CAutoplayer::DoAutoplayer()`:

```cpp
if (p_tablemap->SupportsOFCJokerUltimate()) {
  // autoplayer suppressed
  return;
}
```

The R10 build workflow explicitly fails if `COFCActionExecutor`, `BeginPlacement`, the Fantasy pixel recognizer, or its entry point is wired into live `CAutoplayer` prematurely.

This is correct. Infrastructure may advance behind gates while no live mouse/keyboard action is reachable on a Joker Ultimate table.

## Corrected R9/R10 status

### R9

**Advanced / active; normal semantic path substantially built; Fantasy pixel certification remains critical.**

Remaining R9 blockers include:

- native **real-pixel → Fantasy15 recognized physical cards → raw observation → canonical state** replay proof;
- promotion of the Fantasy15 native recognizer only after that proof;
- live Joker classifier certification rather than replay-only evidence;
- first-round five-loose-card geometry/calibration;
- 14/16/17-card Fantasy fan geometry and recognizer coverage;
- 3-player geometry/calibration;
- sustained replay/property campaigns against ambiguous pixels and UI transitions.

### R10

**Transactional infrastructure advanced; live execution intentionally blocked.**

The stale roadmap items “physical-card source resolver”, “transactional action executor”, and “post-drag verification” are already implemented.

Remaining R10 work is now primarily:

- live-certified Top/Middle/Bottom drop targets (`ofc_drag_targets_calibrated` remains an explicit authority gate);
- a versioned **strategy-action → physical placement sequence** bridge; the strategy must come from the DeepOFC solver/policy interface, never a hardcoded placement heuristic;
- full multi-placement turn orchestration around the already-safe single-drag primitive;
- Confirm-control execution and a verified commit/round-transition transaction;
- Fantasy source re-scrape/reflow between every drag;
- normal/Fantasy gesture replay certification;
- only after R9 + R10 certification, deliberate replacement of the hard read-only guard by a narrower guarded OFC runtime path.

## Current vertical slice

Already real:

`pixels/tablemap → COFCVisualObservation → COFCState → externally requested (physical card,row) → fresh source resolution → calibrated row target → one drag → fresh COFCState → exact pending-transition verification`

Still missing for a complete autonomous turn:

`DeepOFC strategy/policy action → ordered full-turn placement plan → [single-drag transaction × N] → Confirm → verified commit/next-round transition`

## Safety invariants that must not be weakened

1. Never enable live OFC execution merely because code compiles.
2. Never let a tablemap flag alone activate an uncertified native recognizer.
3. Never infer or swap physical JK1/JK2 identity.
4. Never persist Fantasy fan source slots across a drag; re-scrape source geometry.
5. Never issue a second physical mutation before verifying the previous mutation.
6. Never retry blindly after an attempted drag whose result is ambiguous.
7. Never turn a strategy gap into a fixed placement heuristic. The UI layer executes solver/policy decisions; it does not invent them.
8. Any uncertainty in scrape, state reconstruction, geometry, action mapping or post-action verification must fail closed.

## Immediate next milestone

Build the versioned **strategy-action / turn-plan bridge** while keeping `CAutoplayer` read-only. The bridge must express canonical physical-card placements (and unused/discard cards where applicable) without embedding strategy. Then the existing R10 single-drag transaction can be composed into a full offline/replay turn executor and certified before any live enablement.
