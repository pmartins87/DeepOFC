# R10 design — fail-closed OFC card drag autoplayer

R10 is deliberately blocked from live clicking by the R9 hard read-only guard. This document defines the physical action layer so implementation can proceed behind that guard without weakening safety.

## Existing OpenHoldem mouse capability audit

The current OpenHoldem tree already loads a reference `mouse.dll` with:

- `MouseClick(hwnd, rect, button, clicks)`;
- `MouseClickDrag(hwnd, rect, is_horizontal_drag)`.

`MouseClickDrag` is **not sufficient for OFC card placement**. Its API receives one rectangle and internally drags from one edge of that same rectangle to the opposite edge. It was designed for slider-style horizontal/vertical drags, not an arbitrary source-card rectangle to an arbitrary destination-row rectangle.

Therefore R10 needs a new general primitive, conceptually:

```cpp
MouseDragBetweenRects(
    HWND hwnd,
    RECT source_rect,
    RECT target_rect,
    int duration_ms,
    ...safety/options...
)
```

or an equivalent point/rect API.

The existing humanized mouse movement helper can be reused, but OFC correctness must come from deterministic source/target identity and post-drag verification, not from random cursor behavior.

## Required transaction model

Every card movement is a verified transaction:

1. R9 scraper returns a valid canonical state.
2. Strategy selects one exact **physical card** and one canonical destination row.
3. Runtime resolves that physical card to the currently visible source rectangle.
4. Runtime resolves the canonical row to a calibrated safe drop rectangle.
5. Mouse moves to a randomized-but-interior source point.
6. Left button down.
7. Mouse moves to an interior target point while the button remains down.
8. Left button up.
9. Runtime waits for a stable frame.
10. R9 rescrapes.
11. Canonical transition must show that exact physical card in the intended row/pending placement.
12. Only then may the next physical action occur.

On any mismatch the transaction aborts the whole turn and prevents further clicks.

## Why row destination is canonical but slot is not

KKPoker re-sorts cards within a row. Therefore the strategy must never request `middle slot 3`; it requests `Middle`. The UI layer chooses a safe physical drop target for Middle, then validates row membership after KKPoker's visual resort.

Drop targets must be calibrated separately from scrape source rectangles:

```text
ofc_drop_top
ofc_drop_middle
ofc_drop_bottom
```

## Normal Pineapple action sequences

### Round 1

- five incoming cards;
- drag each of the five to its selected canonical row;
- no discard;
- verify tentative 5-card placement set;
- Confirm only when Hero is the canonical actor.

### Rounds 2–5

- three incoming cards;
- place exactly two;
- discard exactly one according to observed KKPoker semantics;
- verify the two placements and the discard outcome;
- Confirm.

The discard UI must be learned from evidence. If KKPoker discards the one unplaced loose card automatically on Confirm, R10 must use and verify that behavior instead of inventing a discard target.

## Fantasy action sequence

Fantasy is the same `joker_ultimate` variant but a different source layout and one-shot placement state.

For a 14–17-card Fantasy hand:

- identify every physical card in the fan;
- strategy chooses exactly 13 for the 3/5/5 board;
- all unused cards are Hero-known discards;
- drag the selected 13 cards to Top/Middle/Bottom according to the action;
- preserve physical identity across fan reflow/reordering after every drag;
- verify after **every** drag, because removing one card can change the visible geometry of the remaining curved fan;
- verify discard semantics for the unused 1–4 cards;
- Confirm only after the complete intended 13-card board/discard set is visible and canonical.

The need to re-resolve source geometry after each Fantasy drag is important: static `fan slot 7` coordinates cannot be assumed to keep pointing to the same physical card after earlier cards are removed.

## Source-card identity and fan reflow

Normal loose cards can use fixed source rectangles when validated.

Fantasy cards are overlapped/rotated and may reflow. The runtime therefore needs a mapping produced by the current scrape:

```text
physical card -> current source rectangle / click-safe visible subregion
```

That mapping is ephemeral and must be recomputed after each successful drag.

## Joker handling

JK1/JK2 are physical occurrence labels. If their faces are visually indistinguishable, source selection can still be safe when only one Joker is visible. With two visible Jokers, any exchangeability optimization must be proven at the **whole action/state** level before either source can be treated as interchangeable.

## Safety invariants

R10 must never click/drag when:

- R9 canonical state is invalid;
- tablemap variant is not exactly `joker_ultimate`;
- acting-chair/Confirm state is contradictory;
- intended physical source card cannot be uniquely located;
- target row has no safe calibrated drop region;
- a previous drag has not yet been verified;
- stable-frame timeout expires;
- post-drag card identity/row differs from the requested transition;
- unexpected popup/layout change is detected.

The first mismatch terminates the action sequence. No best-effort continuation.

## Implementation order

1. Finish R9 full Win32 build and pixel replay gate.
2. Add general arbitrary source->target drag primitive to `mouse.dll` and load it in OpenHoldem.
3. Add an OFC-only action executor behind the hard read-only guard.
4. Add synthetic/sandbox tests for arbitrary drag coordinates and button-down continuity.
5. Add normal-card replay gesture plans.
6. Add Fantasy source re-resolution after each simulated drag.
7. Run R11 shadow mode before removing the guard for controlled R12 live testing.
