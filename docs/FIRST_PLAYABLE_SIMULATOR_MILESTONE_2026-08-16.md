# DeepOFC — First Playable Simulator milestone — 2026-08-16

## Scope correction

DeepOFC targets the KKPoker simulator used by the project. It is not a deployment plan for real-money/live tables. Therefore the previous roadmap language around a live-safety blocker, no-click guard, shadow mode, lowest-stake live rollout, and production table certification is not part of the critical path to the project's first playable milestone.

Robust validation remains useful because recognition/action errors break simulator play and corrupt training/evaluation, but it is an engineering-quality requirement rather than a real-table safety gate.

## Current objective: FP0 — first closed-loop playable agent

FP0 is reached when OpenHoldem can repeatedly complete this loop in the simulator:

`screen -> OFC observation -> canonical state -> legal policy action -> physical drag(s) -> rescrape/re-identify -> Confirm -> next state`

The policy used for FP0 does not need to be the final trained External Sampling blueprint. A deterministic legal baseline or already-certified exact/late-street policy is sufficient to prove the complete runtime loop. The stronger trained policy can replace it afterwards without redesigning the observation/action interface.

## What is already available

- canonical 54-card state with physical JK1/JK2 support;
- normal and Fantasy legal-action semantics, including Fantasy 14–17;
- complete normal HU hidden-state simulator and deterministic replay path;
- exact scoring/reference infrastructure and late-street/baseline kernels;
- solver-family decision: External Sampling MCCFR for the deep/global blueprint, DCFR for smaller exact/conditioned subgames;
- isolated OpenHoldem OFC state/tablemap/autoplayer vertical slice;
- arbitrary drag primitive;
- fixed canonical turn-plan orchestration with rescrape support;
- normal Confirm semantic transition verification;
- measured Fantasy15 recognition/calibration work;
- OFC-specific tablemap contract via `ofc_variant=joker_ultimate`.

## TM/OH cleanup required for the edited KKPoker_DeepOFC_v2.tm

The OpenHoldem legacy completeness checker previously forced Hold'em-specific regions such as hole cards, community cards, pot/bets, and at least three betting buttons. This encouraged dummy regions at `(0,0)` that are semantically meaningless for OFC.

OpenHoldem branch `deepofc` now has an OFC-aware completeness path. For `ofc_variant=joker_ultimate`, it keeps the generic connection/basic map checks and font-group validation, then skips the legacy Hold'em-only completeness requirements. This allows the dummy `(0,0)` compatibility regions to be removed from the OFC tablemap instead of preserving fake Hold'em semantics.

The next TM pass should remove only regions that existed solely to satisfy the legacy completeness checker; real OFC regions and generic connection fields remain.

## Fantasy source-card architecture

Fixed source slots are not the runtime authority for Fantasy. The KKPoker simulator reflows the remaining loose cards after placements, and 14/15/16/17-card Fantasy layouts can use different geometry. A static `src00..src16` model therefore cannot safely identify the card to drag throughout a turn.

The runtime model will be a dynamic card-object detector over a broad Fantasy-hand scan area.

For every fresh scrape:

1. scan the broad Fantasy loose-card area and detect candidate card anchors/bounding boxes;
2. recognize each candidate as a physical card, including separate JK1/JK2 identities;
3. build a fresh list such as `{physical_card, bbox, drag_anchor, confidence}`;
4. map the strategic action to the desired physical card;
5. resolve that card's **current** drag anchor from the fresh list;
6. execute exactly one drag;
7. rescrape the whole loose-card area because the simulator may have reflowed every remaining card;
8. re-identify all remaining cards before resolving the next drag.

The broad region is therefore useful as a scan ROI, but should not be converted into one monolithic text value. A single text result would identify card labels without preserving the per-card geometry required for drag-and-drop.

The existing Fantasy15 `src00..src14` measurements remain valuable as calibration/evaluation evidence and as priors for candidate spacing. They should not become persistent card identities after a drag.

### Count/layout handling

Runtime should infer the current loose-card count from the detected objects and/or a reliable simulator indicator. Geometry profiles for 14, 15, 16, and 17 cards may be used to constrain candidate search windows when the visual fan differs materially, but card identity must always come from the current frame.

If one union scan area covers every 14–17 layout reliably, prefer one area. If the layouts have materially different vertical/curvature envelopes, keep four count-specific scan ROIs while preserving the same dynamic object-detector interface.

## FP0 critical path

### FP0.1 — OFC tablemap cleanup

- validate the new OFC-aware completeness checker in a Windows/OpenHoldem build;
- load the edited `.tm` after removing legacy-only `(0,0)` regions;
- retain only generic connection fields and semantically real OFC regions/fonts/symbols.

**Exit:** edited OFC tablemap loads without needing fake Hold'em regions.

### FP0.2 — Dynamic Fantasy loose-card detector

- define broad Fantasy scan ROI(s);
- candidate segmentation/anchor extraction;
- rank/suit recognition and JK1/JK2 physical identity;
- support 14, 15, 16 and 17 visible-card counts;
- return fresh card objects with current drag coordinates after every reflow.

**Exit:** on recorded simulator frames, every available Fantasy card is individually identifiable and locatable before and after placements.

### FP0.3 — Canonical observation integration

- normal incoming/board scrape -> raw OFC observation -> canonical state;
- Fantasy dynamic object list -> raw Fantasy observation -> canonical state;
- ensure the strategic layer never depends on source-slot ordering.

**Exit:** the same semantic state is produced regardless of visual reflow/order of loose Fantasy cards.

### FP0.4 — Closed-loop action execution

- strategy returns a fixed canonical turn plan;
- resolve first requested card against current card-object list;
- drag to calibrated top/middle/bottom destination;
- rescrape/re-identify;
- resolve next requested card at its new location;
- repeat until turn placement/discard is complete;
- Confirm and scrape the committed next state.

**Exit:** one complete normal turn and one complete Fantasy turn execute without requiring fixed source indices.

### FP0.5 — Attach a legal policy and play complete simulator hands

- initially attach a deterministic legal baseline/exact available policy to prove runtime;
- complete one full HU normal hand;
- complete Fantasy paths for 14, 15, 16 and 17 cards;
- then run repeated hands and record observation/action/state traces.

**Exit / FIRST PLAYABLE:** DeepOFC independently observes, decides, drags, confirms and continues through complete hands in the KKPoker simulator.

## What does NOT block first playable

The following remain important for ultimate playing strength, but do not block FP0:

- full-game long-run External Sampling training;
- final exploitability characterization;
- exploitation/opponent-model layer;
- full 3-player solver scaling if FP0 is first proven HU;
- production packaging/operations work intended for a later mature release.

## After FP0

After the first complete simulator loop is stable, the critical path changes from 'can it play?' to 'how strong is it?': reproducible R7 training, representative early-round/full-game External Sampling scaling, 3-player expansion, stronger Fantasy continuation values, and eventually the exploitation layer.
