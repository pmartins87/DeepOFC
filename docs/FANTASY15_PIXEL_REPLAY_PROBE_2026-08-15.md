# DeepOFC R9 — Fantasy15 raw-pixel replay probe — 2026-08-15

## Result

A deterministic replay-only recognizer was run directly against the original user-supplied BMPs from `ofc fantasy.zip` after first verifying each frozen SHA256.

The probe recognized all three captured 15-card Fantasy fans **exactly**:

```text
session_1/frame000032.bmp
expected   Ah Ac Kh Js Jd Tc 9s 9c 7s 6s 6h 5h 3s 3c 2s
recognized Ah Ac Kh Js Jd Tc 9s 9c 7s 6s 6h 5h 3s 3c 2s
PASS 15/15

session_1/frame000052.bmp
expected   JK1 JK2 Ac Kd Qc Qd Js 9s 9h 7s 6h 4s 4c 3s 2c
recognized JK1 JK2 Ac Kd Qc Qd Js 9s 9h 7s 6h 4s 4c 3s 2c
PASS 15/15

session_1/frame000060.bmp
expected   Ac Ad Qd Tc 8c 7h 7c 6d 5c 4h 4d 3s 3c 3d 2s
recognized Ac Ad Qd Tc 8c 7h 7c 6d 5c 4h 4d 3s 3c 3d 2s
PASS 15/15
```

Total: **45/45 physical fan positions exact**, consisting of 43 standard cards + persistent JK1 + persistent JK2.

## Exact source verification

The tool refuses to run a source frame whose bytes do not match the geometry contract. The three verified source hashes are:

```text
frame000032 723c94862c6020f838d48938a96403b3f4605e77a36b064c5120135c88884130
frame000052 7ea7ff00bf0c8c0d47b3ce8313e1732c9b2958513f23787eee31b70d3f3a4935
frame000060 05689f26ba0e2d3a3cfa3c25e215f3cae38f1292d8ddede7df2e286d37b9eb99
```

These are the hashes already frozen in `joker_ultimate_hu_fantasy15_450x830_geometry_v1.json`.

## Recognition path used

The replay probe is implemented by:

`tools/probe_fantasy15_pixels.py`

It uses:

- the 15 measured `identity_patch` rectangles;
- per-slot deskew angles;
- one 16×24 normalized rank-glyph medoid for each rank `2..A`;
- aligned XOR/union rank distance with ±2-pixel translation;
- maximum rank distance `0.50`;
- minimum best-vs-second rank margin `0.04`;
- median RGB of the selected **rank glyph itself** for suit classification, because KKPoker colors the rank by suit;
- four frozen suit RGB prototypes;
- maximum suit RGB distance `40`;
- minimum suit best-vs-second margin `80`;
- a replay-backed pre-detector for the small vertical `JOKER` glyph strip in the two observed Joker fan cards.

The compact 13-rank bank is frozen in:

`tablemaps/joker_ultimate_hu_fantasy15_rank_medoid_bank_v1.json`

## Observed margins over the three calibration fans

For the 43 standard cards recognized from raw pixels:

```text
rank: max accepted distance = 0.4586466165
rank: min accepted margin   = 0.0440161105
suit: max accepted distance = 35.5070415552
suit: min accepted margin   = 82.3975725938
```

The two Joker fan glyphs in frame52 produced the following replay features:

```text
JK1: selected component area=31, width=7, height=8, median RGB=(233,32,44)
JK2: selected component area=25, width=7, height=8, median RGB=(104,104,104)
```

Across the 43 standard cards in these captures, the selected normal rank glyph is materially larger; this makes the observed Joker strip separable in this calibration replay.

## Why this is NOT yet runtime certification

This is a real-pixel result and is materially stronger than the earlier mask-only probe, but it is still a **calibration replay**, not an independent generalization test:

1. the three frames are the same evidence population from which geometry/templates were calibrated;
2. rank `8` still has only one observed fan exemplar, so the successful `8c` recognition uses a bank containing that same calibration exemplar;
3. JK1 and JK2 each still have only one observed fan occurrence;
4. real 14-, 16- and 17-card fan layouts have not been captured/calibrated;
5. this probe currently proves the Python replay recognizer, not yet the production C++ `CScraper` pixel path;
6. frame53 arrangement recognition still must be connected to pixels for all 13 tentative row cards + two unused cards.

Therefore:

```text
ofc_fantasy_recognizer_calibrated = 0
ofc_drag_targets_calibrated        = 0
ofc_executor_enabled                = 0
```

remain correct.

## Reproduction command

With the supplied BMPs extracted into one directory:

```text
python tools/probe_fantasy15_pixels.py \
  --frames-dir <directory-containing-frame000032.bmp-frame000052.bmp-frame000060.bmp> \
  --geometry tablemaps/joker_ultimate_hu_fantasy15_450x830_geometry_v1.json \
  --bank tablemaps/joker_ultimate_hu_fantasy15_rank_medoid_bank_v1.json \
  --out fantasy15_pixel_probe_report.json
```

Install replay tooling with `requirements-replay.txt`.

## Next hard R9 step

Move from this calibration proof to the full authoritative chain:

```text
real BMP pixels
 -> deterministic Fantasy recognizer with fail-closed rejection
 -> RawOFCObservation
 -> C++ COFCReconstructor
 == independent Python golden state
```

For real frame52 this means 15 loose physical cards including JK1/JK2. For real frame53 it means the same 15-card physical set represented as 13 tentative 3/5/5 placements plus two unused loose cards.

The no-click guard remains active throughout this work.
