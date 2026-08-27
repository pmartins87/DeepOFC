# DeepOFC handoff

Updated: 2026-08-27

This is the operational continuation document for the next chat/session/agent. Do not reconstruct project state from branch names, HEAD commit subjects or chat labels alone.

## Read first

1. `docs/CURRENT_STATE.md`
2. `docs/VERSION_MANIFEST.md`
3. this file
4. `docs/ROADMAP.md`
5. `docs/migration/OPENOFC_SOLVER_INVENTORY_C21C3C4.md`
6. milestone-specific contracts/evidence referenced below

## One-line state

DeepOFC is an advanced but uncertified KKPoker OFC Joker Ultimate project. The continuation/Bellman **architecture exists through M5G**, while real held-out strategic evidence/certification and runtime live-safety remain blocked. The immediate repository task is provenance-preserving solver migration from the frozen OpenHoldem staging tree into DeepOFC.

## Current strategic source

Temporary authority:

- repo: `pmartins87/myoh_private`
- branch: `openofc-m4v-continuation-transport`
- frozen staging head: `c21c3c4f1017c83df07eb22230318a8131bf40d1`
- frozen tree: `73523862dac5b704d6f9878edefaa36212f20bc9`
- M5G anchor: `a7befe2a47b456d4f08a240cd7968e6ec38cb150`

The frozen tree contains M5D–M5G even though its HEAD subject says M5C. Use tree/file provenance, not the latest commit message, to determine architectural content.

## Strategic architecture status

- M5A: continuation-aware fixed-policy/model adapters.
- M5B: train-at-current-V improvement probes.
- M5C: fail-closed state-local route certification firewall; dedicated run `33044932517` PASS means framework PASS only.
- M5D: dynamic exact-V certified Bellman orchestration.
- M5E: Fantasy×Fantasy certification bridge.
- M5F: Fantasy×Fantasy held-out evidence producer; does not automatically make evidence real-ready.
- M5G: full 50-state registry factory from already certified routes; final architectural firewall before REAL dynamic M4Z.

None of those architecture labels means the full target game is strategically solved.

## Current real strategic requirement

A complete real surface needs 50 independent state-local **real-certified exact-V** routes:

- 2 Normal × Normal;
- 16 Normal × Fantasy;
- 32 Fantasy × Fantasy.

Required evidence includes:

- independent held-out seed count;
- held-out sample count;
- value standard error;
- unilateral-deviation gain;
- for Fantasy × Fantasy, exact-teacher support gap;
- for Fantasy × Fantasy, held-out M4W action-value/model error;
- explicit threshold manifest with independently justified provenance.

Synthetic/test evidence must remain incapable of production promotion.

## Repository migration status

### Consolidation checkpoint — PASS/merged

- PR #11 merged to `DeepOFC/main`.
- consolidation main commit: `a90cf7a3713c1a1e5fd402a4cbd29a38c00ebaf7`.
- canonical current-state/version/handoff/migration-policy documents now exist.

### G1 — frozen staging inventory — PASS

Branch: `migration/openofc-solver-inventory-c21c3c4`

- [x] freeze staging source at `c21c3c4...`;
- [x] inventory exact staging subtree;
- [x] compute Git blob SHA + file SHA-256 + size + role;
- [x] compute project-local import dependency closure;
- [x] classify migrate vs historical;
- [x] record related M4/M5 workflows;
- [x] materialize machine-readable and human-readable inventory;
- [x] CI run `33059295351` PASS.

Inventory result:

- 152 staging files;
- 69 current-root transitive dependency-closure files;
- 119 marked `migrate` after associated contracts/tests are included;
- 33 marked `historical`;
- 38 related workflows;
- files payload SHA-256 `89a546aef6f367226cbaf9c6a54d886488519d88b0f1c7d07415db13df382e84`.

### G2/G3 — next repository step

After this inventory/correction branch is merged:

1. create a dedicated pure-code migration branch from new `main`;
2. initially preserve the exact relative layout as `tools/openofc_solver/` inside DeepOFC so flat local imports do not require semantic edits;
3. copy only the inventory entries marked `migrate`;
4. generate a provenance map:
   `source repo + source commit + source path + source blob + source SHA256 -> target path + target SHA256`;
5. require identical bytes/hashes for the pure-copy stage;
6. run migrated tests independently in DeepOFC;
7. add old-vs-new deterministic equivalence probes;
8. switch strategic authority only after equivalence PASS.

A later namespace/refactor may occur only as a separate change after pure migration is certified.

## Strategic evidence queue

Once the frozen source remains stable, migration and evidence preparation may proceed in parallel, but production authority must still fail closed.

1. Normal × Normal held-out deviation + uncertainty evidence.
2. Normal × Fantasy held-out acting-player deviation + uncertainty evidence.
3. Fantasy × Fantasy M4X support-gap + M5B/support-restricted deviation + M4W held-out model-error evidence.
4. independent threshold protocol.
5. state-local certification for all 50 routes.
6. M5G build of a 50/50 real-ready registry.
7. first REAL dynamic M4Z 50-state trace.

## Runtime — separate but convergent track

- preserve recoverable/fail-closed runtime semantics;
- consolidate field-build source/package provenance;
- close deterministic pixel → card → raw → canonical proof;
- certify drag/Confirm transaction loop;
- shadow before controlled live.

Later v5.8.x-labelled runtime tooling is preserved in `myoh_private`, but a field package is canonical only when its source commit, policy, tablemap, recognizer/calibration, build and artifact SHA are bound together.

Runtime development must not silently redefine solver authority, and solver progress must not bypass runtime live-safety gates.

## Frozen strategic background

The R6 architecture tribunal selected External Sampling MCCFR as the strongest practical deep/global blueprint direction on the representative equal-terminal-work benchmark. DCFR remains useful for smaller/conditioned exact subgames. This is architecture evidence, not a full-game solution certificate.

M5A–M5G then built the continuation-aware policy/value, certification and dynamic-registry machinery needed to make future Bellman promotion evidence-driven rather than assumption-driven.

## Runtime background

The v5.4 continuity checkpoint exists because earlier field behavior could preserve stale canonical lineage or permanently block after scrape/reconstruction faults. The required semantics are recoverable reacquisition, current-screen authority, stale-plan discard, safe bootstrap and drag/Confirm idempotence.

## Do not do

- Do not restart the solver architecture study from scratch without contradictory evidence.
- Do not call M5B–M5G architecture production policy or a solved game.
- Do not substitute training loss/top-1 agreement for deviation/exploitability evidence.
- Do not migrate solver files by copy-and-forget; preserve provenance and prove equivalence.
- Do not refactor imports/namespaces during the pure-copy migration gate.
- Do not infer the latest runtime package from the highest chat version number.
- Do not issue live clicks from ambiguous visual state.
- Do not let chat history become the only durable record of a milestone.

## Definition of next meaningful milestones

Repository milestone:
- provenance-preserving pure solver migration + independent CI + old-vs-new equivalence PASS.

Strategic milestone:
- first meaningful real held-out route certifications under a separately justified threshold protocol.

Full strategic promotion milestone:
- 50/50 real-certified exact-V routes, M5G real-ready registry, then the first REAL dynamic M4Z Bellman trace.
