# DeepOFC / OpenHoldem R9-R10 vertical slice status — 2026-08-16

## Purpose

This note records the exact state of the OpenHoldem `deepofc` integration after closing the V2 solver architecture gate and advancing the OFC-specific recognition/action pipeline. It is intentionally narrower and more current than the general roadmap.

## Authoritative repositories

- Strategy/game engine: `pmartins87/DeepOFC`, branch `main`.
- OpenHoldem OFC fork: `pmartins87/myoh_private`, branch `deepofc`.
- OpenHoldem head certified by the integrated R9-R10 gate in this note: `bdacf60787d9399c50ffe1d5a1b6acfb5f6b6adc`.

## Current vertical slice

Target architecture:

`fresh table pixels -> OFC raw visual observation -> canonical OFCState -> strategy action -> fresh source/target geometry -> one drag -> fresh rescrape -> canonical transition verification`

The architecture is fail-closed. No ambiguous scrape, unsupported geometry, unverified prior action, or disabled authority flag may fall through to a physical action.

## R9 recognition / reconstruction

### Normal OFC

Implemented and compiled in OpenHoldem:

- OFC-specific scraper isolated from legacy Hold'em hole/community-card state;
- strict empty/back/Joker/rank/suit slot contract;
- physical JK1/JK2 identities preserved;
- stateful canonical reconstruction across normal rounds 0..4;
- first decision receives 5 Hero cards; later decisions receive 3;
- transition logic commits 5 on round 0, then 2 plus one discard on later rounds;
- mid-hand reconstruction requires prior canonical state and rejects missing/inconsistent history;
- duplicate physical-card and committed-card movement/disappearance checks.

### Fantasy canonical state

Implemented in `COFCReconstructor`:

- Fantasy is routed separately from normal-play geometry;
- Hero Fantasy uses `round_index=-1`;
- 14..17 visible Hero physical cards are supported by the canonical state contract;
- tentative 3/5/5 placement is represented as pending placement, not committed Hero board;
- Hero may freely rearrange tentative cards before Confirm;
- actionable Confirm requires exactly 13 tentative placements and 1..4 unused cards;
- opponent committed board must remain physically consistent;
- JK1/JK2 remain persistent physical identities.

## Fantasy15 independent real-pixel recognition evidence

Source archive: `ofc fantasy.zip`.

Archive SHA-256:

`1b91e038bb42acee2520187907d9ef9d6f34fc303d065ac2bc5dd1e92d52027e`

The frozen 15-card initial-fan rank model is trained only from real frames 32 and 60. Real frame 52 is a zero-training-sample holdout.

Frozen model:

- exact 450x830 client geometry;
- 15 measured fan rectangles;
- deterministic 32x32 binary HOG;
- 324 features;
- 13 rank centroids `23456789TJQKA`;
- standard max squared distance `2.25`;
- standard minimum margin `0.15`;
- Joker reject minimum rank distance `3.20`;
- physical Joker identity from persistent KKPoker color signature.

Independent holdout result on frame 52:

- standard cards: **13/13**;
- JK1/JK2: **2/2**;
- full fan: **15/15**.

Expected and predicted physical sequence:

`JK1 JK2 Ac Kd Qc Qd Js 9s 9h 7s 6h 4s 4c 3s 2c`

Durable evidence:

`evidence/fantasy15_quantized_native_model_real_pixel_holdout_2026-08-16.json`

This evidence certifies the frozen classifier on the independent real-pixel holdout. It does **not** by itself authorize a live OpenHoldem scrape path.

## Frozen model imported into OpenHoldem

The exact quantized model is imported into:

`OpenHoldem/COFCFantasy15PixelModel.generated.h`

The import workflow pins the model source to DeepOFC commit:

`03e584895ac81d33b5971f329a7da7ec81547f5d`

The import gate verifies:

- model dimensions 13 x 324;
- exact per-rank sum and weighted checksums;
- exact thresholds;
- Fantasy runtime certification remains OFF;
- no live autoplayer authority is granted.

Import workflow run: `31933058411` — PASS.

## Native OpenHoldem Fantasy15 pixel recognizer

Implemented and compiled:

- `OpenHoldem/COFCFantasy15PixelRecognizer.h`
- `OpenHoldem/COFCFantasy15PixelRecognizer.cpp`

The component:

- accepts an OpenHoldem `HBITMAP`;
- requires exact 450x830 dimensions;
- extracts deterministic top-down 32-bit pixels with `GetDIBits`;
- uses the measured 15 source-fan rectangles;
- reproduces the frozen HOG/rank/suit/Joker decision rules;
- rejects rank/suit ambiguity;
- rejects duplicate physical-card labels;
- invalidates the whole fan if any one slot fails;
- contains no click, cursor, input, or drag primitive.

The component is compiled into OpenHoldem Release/Win32. Recognition-only build run `31933304613` — PASS.

The compile-time Fantasy scraper certification flag remains `0`; the new recognizer is deliberately not yet callable by the scraper.

## R10 transactional action layer

Implemented and compiled behind hard guards:

- `COFCActionPlanner` maps a strategy placement to fresh observed source geometry and a calibrated row target;
- drag targets require explicit tablemap calibration authority;
- `COFCActionExecutor` requires explicit executor authority;
- exactly one physical drag may occur per transaction step;
- after a drag, a fresh scrape and canonical-state verification are mandatory;
- a mismatch blocks the transaction; no blind retry or second action is allowed;
- `CCasinoInterface::DragRectToRect` checks window/focus/bounds and does not steal focus;
- OFC executor is not wired into live `CAutoplayer`.

## Integrated R9-R10 regression gate

Workflow:

`.github/workflows/deepofc-r10-executor-build.yml`

The gate now covers the whole current R9-R10 vertical slice, including:

- OFC state/reconstructor;
- normal/Fantasy scraper routing;
- frozen Fantasy15 pixel model;
- native Fantasy15 HBITMAP recognizer;
- action planner;
- transactional executor;
- casino drag wrapper;
- tablemap authorities;
- `CAutoplayer` live-disconnection assertion;
- OpenHoldem Release/Win32 build.

Integrated run `31933455400` — **PASS**.

Certified OpenHoldem head for this run:

`bdacf60787d9399c50ffe1d5a1b6acfb5f6b6adc`

## What is deliberately NOT certified yet

The following are real blockers, not forgotten work:

1. **OpenHoldem-native HBITMAP replay certification.** The frozen classifier has independent real-pixel proof and the HBITMAP recognizer compiles, but the exact OpenHoldem `GetDIBits -> recognizer` path still needs to be replayed against the real frame 52 before changing `DEEPOFC_NATIVE_FANTASY15_RECOGNIZER_CERTIFIED` from `0` to `1`.
2. **Fantasy arrangement recognition.** The 13 tentatively arranged cards plus the 1..4 unused loose cards must be recognized from their different on-table geometry. Frame 53 provides a golden 13+2 state with both physical Jokers; frame 41 provides another independent 13+2 arrangement from the frame-32 fan.
3. **Scraper-to-reconstructor Fantasy replay.** After initial-fan and arrangement recognition are certified, the real replay sequence must produce the exact raw observation and exact canonical state, including persistent JK1/JK2.
4. **Other Fantasy fan counts/geometries.** 14/16/17 and other chair/player-count layouts require their own measured evidence. The current 450x830 source geometry must never be extrapolated to them.
5. **Strategy bridge.** Physical placement must come from the solver/EV policy interface, never from a fixed placement heuristic.
6. **Live physical action authority.** Drag target calibration and executor authority remain OFF until recognition, state reconstruction, strategy mapping, and post-action verification are certified together.

## Immediate next gates

1. Certify the exact native OpenHoldem HBITMAP path on the independent frame-52 pixels without publishing the raw user-supplied table screenshot.
2. Build and independently validate the Fantasy arrangement/loose-card recognizer using multiple real hands.
3. Replay `fan -> arrangement -> canonical state` and demand exact physical-card/state equality.
4. Only then wire the Fantasy pixel recognizer into `COFCScraper`, still read-only.
5. Keep `CAutoplayer` and the physical executor disconnected until the full read-only vertical slice is exact.

## Safety invariant

No benchmark PASS, tablemap symbol, model file, or compile success alone authorizes a live action. Recognition authority, geometry authority, strategy authority, transactional execution authority, and post-action verification are separate gates and remain separate by design.
