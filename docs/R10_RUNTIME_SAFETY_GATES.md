# DeepOFC R10 runtime safety gates

This document freezes the physical-action authorization boundary for KKPoker OFC Joker Ultimate. It is intentionally stricter than merely having mouse code or rectangle geometry available.

## Three independent layers

R10 separates three concerns that must not be conflated:

1. **Source geometry** — where the exact physical Hero card is visible *in the current frame*.
2. **Destination calibration** — which client rectangle is a proven safe drop target for Top/Middle/Bottom.
3. **Execution authority** — whether the runtime is deliberately permitted to send physical OFC mouse input at all.

Progress in one layer must never silently enable another.

## Ephemeral source geometry

For normal loose cards the tablemap exposes geometry-only regions:

```text
ofc_hero_in0drag
ofc_hero_in1drag
ofc_hero_in2drag
```

The scraper binds each current recognized physical card to the rectangle from the same raw observation:

```text
physical card -> current source rectangle
```

This mapping is UI metadata only. It is not canonical solver state and does not create persistent visual slot identity.

Fantasy will use the same semantic contract but its curved/overlapping fan requires a separate calibrated recognition/layout path. Because the fan may reflow after a card is removed, every successful Fantasy drag must be followed by a fresh scrape and a fresh physical-card -> source-rectangle mapping.

## Gate A — calibrated row targets

The tablemap must carry:

```text
s$ofc_drag_targets_calibrated  0|1
```

`COFCActionPlanner` accepts a physical placement plan only when the value is exactly `1`.

The three destinations are:

```text
ofc_drop_top
ofc_drop_middle
ofc_drop_bottom
```

Region existence alone is not certification. Replay/draft tablemaps always use `0`, even if experimental `ofc_drop_*` rectangles are present.

Only an empirically validated runtime tablemap may deliberately set Gate A to `1`.

## Gate B — execution enabled

A separate tablemap symbol controls physical execution:

```text
s$ofc_executor_enabled  0|1
```

`COFCActionExecutor` refuses to send a drag unless this value is exactly `1`.

This gate is independent of target calibration. A development/shadow runtime may therefore have valid source geometry and even certified row targets while still remaining physically inert.

Generated replay drafts always use:

```text
s$ofc_drag_targets_calibrated  0
s$ofc_executor_enabled         0
```

## Gate C — current hard R9 live no-click guard

The existing `CAutoplayer` Joker Ultimate guard remains the controlling live-path prohibition while R9/R10 are under construction.

The transactional executor is deliberately **not wired into `CAutoplayer`**. Therefore even the presence of the arbitrary mouse primitive, planner and executor classes does not create a live OFC click path.

Gate C is removed only by a later deliberate roadmap transition after the required replay/sandbox/shadow gates pass.

## One-drag transaction invariant

When execution is eventually authorized, `COFCActionExecutor` permits only this sequence:

```text
valid canonical state + fresh raw observation
    -> resolve exact physical source card
    -> require Gate A
    -> require Gate B
    -> perform exactly one physical drag
    -> mark transaction awaiting verification
    -> fresh scrape/reconstruction
    -> verify exact requested card->row pending transition
    -> only then permit another drag
```

A second drag before verification is forbidden.

After any physical attempt with an uncertain result, the executor blocks rather than retries. A known new-hand reset is required to clear the blocked state.

## Window-level physical safeguards

The casino drag wrapper additionally requires:

- loaded `MouseDragBetweenRects` entry point;
- a valid attached HWND;
- source and destination rectangles with positive area;
- both rectangles fully inside the attached client area;
- the attached KKPoker table already being the foreground window.

The wrapper does not steal focus and then drag. If the user is interacting with another window, the OFC drag is refused.

## Post-drag verification

`COFCActionPlanner::VerifyPendingTransition()` requires that one drag:

- preserves hand/player/dealer/round metadata;
- preserves the physical incoming-card identity;
- adds exactly one pending placement;
- puts the requested physical card in exactly the requested canonical row;
- preserves every pre-existing tentative placement.

Any mismatch fails closed.

## What remains before physical OFC play

The infrastructure above does **not** mean DeepOFC is ready to click live. Still required include:

- real-pixel `BMP -> tablemap -> raw -> canonical` validation;
- empirically calibrated normal row drop targets;
- first-round five-loose-card source geometry;
- exact discard behavior;
- calibrated Confirm click geometry and commit-transition verification;
- Joker face recognition;
- real Fantasy 14–17-card fan recognition and source re-resolution;
- sandbox/replay gesture validation;
- R11 sustained shadow validation;
- controlled R12 activation.

Until those gates pass, the safe configuration remains `0/0` plus the hard R9 no-click guard.
