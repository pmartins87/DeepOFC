# DeepOFC dynamic Fantasy detector — replay probe v1 — 2026-08-16

## Outcome

The first FP0.2 vertical slice now discovers current Fantasy rank anchors from
the supplied 450x830 pixels, recognizes physical cards, and returns a fresh
`{card, source_rect, drag_anchor, confidence evidence}` object list.  Reflow
positions are not retained as strategic slot identities.

Across the frozen 12-frame replay manifest, the probe accepted 77/77 exact
card objects in nine frames and rejected three whole observations safely.  It
accepted no wrong frame.

## Safety/robustness gates proved by the replay

- frame 35 is an animation/reflow transition and is rejected by the regular
  grid residual;
- frame 37 contains a visually plausible `3c -> 5c` confusion, but `5c` was
  not in the original Fantasy deal, so physical-card lineage rejects the whole
  observation;
- frame 41 contains a low-margin `5h` glyph and is rejected rather than guessed;
- every accepted scrape contains complete, unique physical identities;
- every source rectangle and drag anchor is rebuilt from the current frame.

This is the intended FP0 behavior: an ambiguous scrape delays the action and
requests another stable scrape; it never authorizes a best-guess drag.

## Replay coverage

| Layout/state | Frames | Result |
|---|---:|---:|
| Initial 15-card fan | 32, 52, 60 | 45/45 exact objects |
| Stable reflow | 36, 39, 40 | 26/26 exact objects |
| Two upright cards remaining | 53, 61, 62 | 6/6 exact objects |
| Expected fail-closed | 35, 37, 41 | 3/3 rejected |

The probe also fixes the original v2 initial-fan replay path to honor its
frozen bilinear resampling contract and current `deskew.angles_degrees` schema.

## Authority and remaining work

This result does not enable runtime authority.  The OpenHoldem flags remain:

```text
ofc_fantasy_recognizer_calibrated = 0
ofc_drag_targets_calibrated = 0
ofc_executor_enabled = 0
```

The next step is to port the pixel-localization kernel to the inert native
OpenHoldem recognizer API, replay these same BMPs through `HBITMAP`, and only
then connect its fresh objects to `COFCVisualObservation::hero_loose_sources`.

Initial 14, 16 and 17-card layouts remain unclaimed because the supplied
captures do not contain those initial geometries.  The detector interface is
count-independent, but those three layouts require real fixtures before they
can pass the pixel gate.
