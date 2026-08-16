# DeepOFC R9 — Fantasy15 real-pixel holdout (2026-08-16)

## Result

**PASS — 15/15 physical cards recognized exactly on the held-out real KKPoker Fantasy fan.**

This gate uses the user-supplied `ofc fantasy.zip` replay and the already-frozen measured geometry in `tablemaps/joker_ultimate_hu_fantasy15_450x830_geometry_v1.json`.

It is deliberately a **replay-only recognition proof**. It does **not** enable live runtime authority, clicking, dragging, or the native Fantasy recognizer.

## Independence structure

Calibration/training frames:

- `frame000032.bmp` — SHA256 `723c94862c6020f838d48938a96403b3f4605e77a36b064c5120135c88884130`
- `frame000060.bmp` — SHA256 `05689f26ba0e2d3a3cfa3c25e215f3cae38f1292d8ddede7df2e286d37b9eb99`

Held-out proof frame:

- `frame000052.bmp` — SHA256 `7ea7ff00bf0c8c0d47b3ce8313e1732c9b2958513f23787eee31b70d3f3a4935`

The program validates these hashes before reading pixels. Frame 52 contributes **no standard-card rank template** to its own evaluation.

Frames 32 + 60 jointly cover all 13 ranks. A deterministic HOG-like descriptor is computed from the exposed rank strip of each measured fan slot and averaged by rank. Suits use the stable KKPoker client color coding visible in the replay: hearts red, diamonds blue, clubs green, spades neutral/dark.

The two physical Jokers are treated separately. Their vertical `JOKER` faces are first rejected by the standard-rank distance gate; persistent identity then follows the evidence-backed mapping already frozen by the project:

- `JK1` = orange/red pineapple Joker;
- `JK2` = gray/black pineapple Joker.

## Held-out expected fan

```text
JK1 JK2 Ac Kd Qc Qd Js 9s 9h 7s 6h 4s 4c 3s 2c
```

## Held-out recognized fan

```text
JK1 JK2 Ac Kd Qc Qd Js 9s 9h 7s 6h 4s 4c 3s 2c
```

Results:

- standard cards: **13/13**;
- persistent Jokers: **2/2**;
- complete 15-card fan: **15/15**.

The largest standard-card rank distance on the holdout was `1.903226028`, below the frozen standard acceptance limit `2.25`. The smallest accepted standard-card separation from the second-best rank was `0.614146415`, above the frozen minimum margin `0.15`.

The two Joker rank-rejection distances were:

- JK1: `3.521040631`;
- JK2: `4.891074858`.

Both exceed the Joker rejection boundary `3.20`, leaving a clean gap from every accepted standard card in this holdout.

## Reproduction

With the original replay ZIP available locally:

```text
python tools/benchmark_fantasy15_real_pixel_holdout.py --zip "ofc fantasy.zip" --report fantasy15_pixel_holdout_report.json
```

The only replay dependency is Pillow, already declared in `requirements-replay.txt`.

## What this closes — and what it does not

This closes the first independent **real pixels -> physical card identity** proof for the measured 15-card HU Fantasy fan geometry. It materially advances R9 beyond geometry-only evidence.

It does **not** yet close R9 as a whole. Remaining independent gates include at least:

- porting/fixing the classifier in the native OpenHoldem path and proving C++ output against the same real-pixel holdout;
- `recognized cards -> COFCVisualObservation/raw -> canonical state` equality in native replay;
- 14-, 16- and 17-card Fantasy fan geometry/recognition;
- 3-player geometry;
- first-round loose-card geometry where still missing;
- post-drag fan reflow/source re-resolution;
- broader live-calibration evidence before any runtime recognition authority is changed.

Runtime flags remain unchanged and hard-off:

```text
ofc_fantasy_recognizer_calibrated = 0
ofc_drag_targets_calibrated = 0
ofc_executor_enabled = 0
DEEPOFC_NATIVE_FANTASY15_RECOGNIZER_CERTIFIED = 0
```

**No-click remains mandatory.**
