# DeepOFC R9 — Fantasy 15-card recognition probe (2026-08-15)

## Status

**Replay engineering probe only. Not runtime certified.**

This document records measurements from the three user-supplied 15-card KKPoker Joker Ultimate Fantasy deals already frozen in `tablemaps/joker_ultimate_hu_fantasy15_450x830_geometry_v1.json`:

- `session_1/frame000032.bmp`
- `session_1/frame000052.bmp`
- `session_1/frame000060.bmp`

The current tablemap/runtime authority remains:

```text
ofc_fantasy_recognizer_calibrated = 0
```

The purpose of this probe is to determine whether the curved/rotated fan can be recognized deterministically before any C++ Fantasy path is enabled.

## 1. Geometry is highly stable for the observed 15-card fan

The 15 exposed identity patches follow a smooth arc across all three observed deals. A quadratic fit to the patch-top trajectory yields a usable local tangent for deskewing each fan slot.

Approximate deskew angles from left to right are:

```text
0  -18.85 deg
1  -16.52 deg
2  -14.22 deg
3  -11.79 deg
4   -9.31 deg
5   -6.69 deg
6   -4.15 deg
7   -1.59 deg
8   +1.08 deg
9   +3.64 deg
10  +6.18 deg
11  +8.80 deg
12 +11.39 deg
13 +13.92 deg
14 +16.32 deg
```

Applying the opposite image rotation to each exposed patch makes the rank/suit glyphs approximately upright. This confirms that the curved layout is not, by itself, a blocker to deterministic recognition.

This result applies only to the directly observed 15-card layout. It must not be extrapolated silently to 14-, 16- or 17-card Fantasy.

## 2. Standard-card glyph extraction succeeds on the observed deals

Across the three 15-card deals there are:

- 45 physical fan positions total;
- 2 physical Jokers in frame 52;
- 43 standard-card samples.

After geometric deskew, a deterministic card-mask procedure can isolate the exposed rank glyph and the suit glyph from all **43/43 standard-card samples** in these three frames.

The rank samples cover every standard rank at least once:

```text
A K Q J T 9 8 7 6 5 4 3 2
```

The rank `8` currently has only one observed standard-card fan exemplar. Every other rank has at least two exemplars across the three deals.

## 3. Suit recognition is unusually favorable

The KKPoker client uses four stable suit colors in the observed fan:

```text
hearts   red
clubs    green
diamonds blue
spades   black/gray
```

A simple deterministic classifier using the median foreground color of the extracted suit glyph classifies all **43/43 observed standard-card suits correctly**.

This does not yet certify live runtime behavior, but it means the difficult part of the Fantasy recognizer is rank/Joker identity rather than suit classification.

## 4. Replay-derived rank-template separation is already strong

For the probe, each extracted rank silhouette was normalized to a binary `24 x 16` mask. Nearest-template distance was measured as normalized XOR over union.

A leave-one-sample-out test produced:

```text
42 / 43 correct = 97.67%
```

The **only failure is the sole observed standard `8` sample**, because removing it for leave-one-out leaves the template bank with no `8` exemplar at all. Therefore, among ranks for which at least one independent exemplar remains in the bank, the result is:

```text
42 / 42 correct = 100%
```

The narrowest observed correct same-rank versus wrong-rank distance margin is approximately `0.049` in this probe.

This is promising but is **not sufficient to flip the runtime calibration gate**. In particular:

- the sample size is small;
- the same three source deals generated both the template candidates and the validation population;
- rank `8` lacks an independent second exemplar;
- 14/16/17-card fan layouts are unobserved;
- image scaling/rendering changes across client versions are not yet tested.

## 5. Existing bootstrap tablemap contains a useful independent font corpus

The original user-supplied `KKPoker_OFC.tm` has SHA256:

```text
de8566692d30e4c88092b9521c94a4ed053158669672067bd485ca340b1a69e0
```

This exactly matches `evidence/manifest.json`.

The tablemap contains many `T1`, `T5` and `T6` rank/suit font templates, including all standard ranks. This is important because it gives R9 an independent KKPoker glyph corpus that predates the new Fantasy frames.

A deliberately simple first comparison of normalized deskewed fan masks against the raw legacy `T1` masks is not accurate enough by itself, which means we should not pretend that merely rotating the fan and calling the existing transform solves the problem. The next experiment should reproduce the actual OpenHoldem fuzzy-font transform semantics or use a replay-derived template bank with explicit confidence/margin rejection.

## 6. Joker recognition in the fan is separable from standard ranks

Frame 52 contains both physical Jokers in slots 0 and 1.

After deskew:

- JK1 has a strong orange/red foreground signature;
- JK2 has a strong gray/black foreground signature;
- neither looks like a normal rank+suit card.

This supports a staged recognizer:

```text
fan patch
  -> persistent-Joker detector (JK1 / JK2)
  -> otherwise standard rank detector
  -> four-color suit detector
```

Confirmed gold Joker cards remain a separate visual form and still require their color-coded small-marker detector.

## 7. Activation requirements remain strict

`ofc_fantasy_recognizer_calibrated` must remain `0` until, at minimum:

1. all supplied 15-card fan frames reconstruct exactly as the frozen physical-card sequences;
2. frame 53 reconstructs the complete 13-card tentative 3/5/5 arrangement plus the two unplaced discards;
3. persistent JK1/JK2 identity survives `fan -> tentative row -> confirmed gold marker`;
4. ambiguous rank matches fail closed instead of selecting the nearest class unconditionally;
5. at least one independent second `8` exemplar is validated;
6. any observed 14/16/17-card layouts receive their own geometry/calibration contract rather than being inferred from 15-card spacing;
7. the C++ implementation passes a full OpenHoldem `Release|Win32` build and cross-language golden gate.

Until then, the correct R9 behavior is exactly what the runtime now does: detect Fantasy early and refuse to reuse normal geometry.
