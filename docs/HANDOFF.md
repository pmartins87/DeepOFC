# DeepOFC handoff

Updated: 2026-08-27

This is the operational continuation document for the next chat/session/agent. Do not reconstruct project state from branch names or chat labels alone.

## Read first

1. `docs/CURRENT_STATE.md`
2. `docs/VERSION_MANIFEST.md`
3. this file
4. `docs/ROADMAP.md`
5. milestone-specific contracts/evidence referenced below

## One-line state

DeepOFC is an advanced but uncertified KKPoker OFC Joker Ultimate project. The strategic solver has reached **M5C staging**, while the runtime and strategic histories became split across two repositories. The immediate job is to finish provenance-preserving consolidation, then generate real held-out M5C route evidence.

## Current strategic source

Temporary authority:

- repo: `pmartins87/myoh_private`
- branch: `openofc-m4v-continuation-transport`
- frozen staging head: `c21c3c4f1017c83df07eb22230318a8131bf40d1`
- M5C contract: `tools/openofc_solver/M5C_ROUTE_CERTIFICATION_CONTRACT.md`
- dedicated M5C workflow run `33044932517`: PASS

Interpretation: the **certification firewall implementation** passed. The strategies themselves are not yet certified.

Do not enable a REAL 50-state M4Z Bellman run merely because this CI gate is green.

## Current M5C strategic requirement

A complete real surface needs 50 independent state-local ready certificates:

- 2 Normal × Normal;
- 16 Normal × Fantasy;
- 32 Fantasy × Fantasy.

Before promotion, generate the independent evidence required by the M5C contract:

- held-out seed count;
- held-out sample count;
- value standard error;
- unilateral-deviation gain;
- for Fantasy × Fantasy, exact-teacher support gap;
- for Fantasy × Fantasy, held-out M4W action-value/model error;
- explicit threshold manifest with independently justified provenance.

Synthetic/test evidence must remain incapable of promotion.

## Immediate work queue

### G1 — repository consolidation

Status: active.

- [x] Create canonical current-state document.
- [x] Create version/provenance manifest.
- [x] Create canonical handoff.
- [ ] Merge consolidation checkpoint to `DeepOFC/main`.
- [ ] Inventory M4/M5 staging dependency closure.
- [ ] Create old-path/source-blob/new-path migration manifest.
- [ ] Copy/migrate solver modules and tests into DeepOFC on a dedicated branch.
- [ ] Add deterministic cross-repository equivalence gate.
- [ ] Switch M4/M5 authority in `VERSION_MANIFEST.md` only after equivalence PASS.

Migration contract: `docs/SOLVER_MIGRATION_PLAN.md`.

### S1 — M5C evidence generation

Start only after the consolidation checkpoint is durable. Migration and evidence work may then proceed in parallel if the staging head remains frozen.

1. Normal × Normal held-out deviation + uncertainty probes.
2. Normal × Fantasy held-out acting-player deviation + uncertainty probes.
3. Fantasy × Fantasy M4X support-gap + M5B deviation + M4W error evidence.
4. independent threshold protocol;
5. state-local certification for all 50 routes;
6. first REAL 50-state M4Z trace.

### RUNTIME — separate but convergent track

- preserve recoverable/fail-closed runtime semantics;
- consolidate field-build source/package provenance;
- close deterministic pixel → card → raw → canonical proof;
- certify drag/Confirm transaction loop;
- shadow before controlled live.

Runtime development must not silently redefine solver authority, and solver progress must not bypass runtime live-safety gates.

## Frozen strategic background

The R6 architecture tribunal selected External Sampling MCCFR as the strongest practical deep/global blueprint direction on the representative equal-terminal-work benchmark. DCFR remains useful for smaller/conditioned exact subgames. This is architecture evidence, not a full-game solution certificate.

M5A introduced continuation-aware fixed-policy/model value adapters. M5B added train-at-current-V policy-improvement probes. M5C is the promotion firewall that requires independent strategic evidence before those routes may serve as real Bellman operators.

## Runtime background

The v5.4 continuity checkpoint exists because earlier field behavior could preserve stale canonical lineage or permanently block after scrape/reconstruction faults. The required semantics are recoverable reacquisition, current-screen authority, stale-plan discard, safe bootstrap and drag/Confirm idempotence.

A later field/test label is not canonical unless its source commit, policy, tablemap, recognizer/calibration and artifact/build provenance are bound in the version manifest.

## Do not do

- Do not restart the solver architecture study from scratch without contradictory evidence.
- Do not call M5B/M5C probes production policy.
- Do not substitute training loss or top-1 agreement for deviation/exploitability evidence.
- Do not migrate solver files by copy-and-forget; preserve provenance and prove equivalence.
- Do not infer the latest runtime source from the highest chat version number.
- Do not issue live clicks from ambiguous visual state.
- Do not let chat history become the only durable record of a milestone.

## Definition of next meaningful strategic milestone

The next milestone is **not another letter because code was added**. It is one of:

1. a completed provenance-preserving solver migration gate; or
2. the first meaningful set of real held-out M5C route certificates under a justified threshold protocol.

A full strategic promotion milestone is reached when all required routes are certified and the first REAL M4Z 50-state Bellman trace can run without test/synthetic authority.
