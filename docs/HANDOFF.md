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

DeepOFC is an advanced but strategically uncertified KKPoker OFC Joker Ultimate project. The continuation/Bellman architecture reaches **M5G**. The former OpenHoldem strategic staging tree has completed provenance-preserving transfer into `DeepOFC/main` through corrected fixed-point inventory, **126/126 byte-identical migration**, **20/20 deterministic old-vs-new equivalence**, canonical PR CI PASS, merge PR #13 and post-merge `main` CI PASS. The repository migration is complete; the next substantive blocker is real held-out evidence and 50/50 exact-V route certification.

## Canonical strategic authority

Active strategic source:

- repository: `pmartins87/DeepOFC`
- branch: `main`
- authority-transfer merge commit: `4842d01dc68b14bae5a083d8ae0138297d7a0783`
- post-merge canonical CI run: `33074839933` — **PASS**

Frozen historical provenance:

- repository: `pmartins87/myoh_private`
- branch: `openofc-m4v-continuation-transport`
- commit: `c21c3c4f1017c83df07eb22230318a8131bf40d1`
- solver tree: `73523862dac5b704d6f9878edefaa36212f20bc9`

Future strategic development belongs in DeepOFC. The runtime repository should consume explicit versioned/exported policy artifacts rather than become the sole owner of strategic source.

## Completed migration gates

### G1 v1 — superseded by evidence

The first migration inventory was not fully closed over dependencies introduced by matching tests. Old-vs-new run `33070445519` returned **19/20** exact matches. The sole target failure was `test_engine.py -> teacher_search.py` missing from the migration set, while the frozen source passed. This was an inventory-policy defect, not a solver semantic divergence.

### G1 v2 — fixed-point inventory — PASS

Workflow run `33070689091`: **PASS**.

- schema `deepofc-openofc-solver-inventory-v2`;
- frozen subtree: **187 files**;
- migrate: **126**;
- historical: **61**;
- M4/M5 workflows recorded: **38**;
- payload SHA-256: `06df84fa80c6bf869125ec858551b84c00895b4230c07079aa0b20eaa8b8c007`.

### G2/G3 — pure migration / independent migrated tests — PASS

Workflow run `33070802793`: **PASS**.

- 126 selected files copied byte-for-byte at the same `tools/openofc_solver/...` paths;
- all source/target SHA-256 and Git blob identities match;
- Python tree compiles;
- M5 core tests PASS;
- migrated M5 test surface PASS;
- `test_engine.py` regression PASS;
- generated Python bytecode removed before persistence;
- materialized solver commit: `0c0ae8d77c8ca35c344f59c1515f6712b2ca1a2a`;
- provenance canonical SHA-256: `4041f7560f9a94b5e85b9c1c986f39e690bca5e3635328fad1bff1fdd1b11766`.

### G4 — deterministic behavioral equivalence — PASS

Workflow run `33070910873`: **PASS**.

- source PASS: **20/20**;
- target PASS: **20/20**;
- normalized stdout/stderr identical: **20/20**;
- report SHA-256: `935162877ad8f7821fa106ba7cd2f5bfc588a60f2273c34443eb805926e93664`;
- evidence commit: `d45a9b77df8d75c1feaf45c8354ea152cd311355`.

The suite covers engine, HU continuation, M4U–M4Z, M5A–M5G and Normal×Fantasy/Fantasy×Fantasy kernel/payoff behavior.

### G5 — canonical DeepOFC PR CI — PASS

PR #13 was opened from `migration/openofc-solver-code-c21c3c4` to `main`.

The first PR-level CI run correctly exposed one repository integration omission: migrated tests import NumPy, while `requirements-dev.txt` contained only pytest. `numpy==2.4.6` was added, matching the proven equivalence environment.

- corrected PR head: `c364a3056349ba627f273265c7c7a742b2d72c99`;
- canonical PR CI run `33074562167`: **PASS**.

### G6 — merge / authority transfer — PASS

- PR #13 merged;
- merge commit: `4842d01dc68b14bae5a083d8ae0138297d7a0783`;
- post-merge `main` CI run `33074839933`: **PASS**;
- DeepOFC now owns active strategic authority;
- `myoh_private@c21c3c4...` is historical provenance only.

Final completion record:

`docs/migration/OPENOFC_SOLVER_AUTHORITY_TRANSFER_C21C3C4.md`

Migration identity/equivalence proves source transfer. It does **not** certify strategic quality or production exploitability.

## Strategic architecture state

The migrated tree contains architecture through M5G:

- M5A — fixed-policy/model continuation-aware adapters;
- M5B — current-V policy-improvement probes;
- M5C — fail-closed route-certification firewall;
- M5D — dynamic exact-V certified Bellman route enforcement;
- M5E — Fantasy×Fantasy certification bridge;
- M5F — Fantasy×Fantasy held-out evidence producer;
- M5G — full 50-state registry factory/final architectural firewall.

M5G only assembles routes that already satisfy the real certification contract. It cannot replace missing held-out evidence or decide production thresholds.

## Next substantive strategic queue

A full real surface requires **50 real-certified exact-V routes**:

- 2 Normal × Normal;
- 16 Normal × Fantasy;
- 32 Fantasy × Fantasy.

Proceed with:

1. independent held-out Normal × Normal deviation + uncertainty evidence;
2. independent held-out Normal × Fantasy acting-player deviation + uncertainty evidence;
3. Fantasy × Fantasy exact-support gap + unilateral deviation + held-out M4W model/action-value error evidence;
4. independently justified threshold protocol;
5. state-local exact-V certification for all 50 routes;
6. M5G real-ready registry only at 50/50;
7. first REAL dynamic M4Z 50-state Bellman trace;
8. convergence/stability/exploitability measurement before claiming stronger strategic readiness.

Synthetic/test evidence must remain incapable of promotion.

## Runtime — separate but convergent track

Runtime remains a live-safety blocker independently of solver progress:

- preserve recoverable/fail-closed scrape/reacquisition semantics;
- consolidate field-build source/package provenance;
- close deterministic pixels → physical cards → raw observation → canonical state proof;
- certify drag → fresh scrape → exact verification;
- certify Confirm → committed-state verification;
- shadow before controlled live use.

Field labels such as v5.8.x remain test-session/package labels until source commit, solver/policy, tablemap, recognizer/calibration, build and artifact SHA are bound in one manifest.

## Frozen strategic background

The earlier R6 architecture tribunal selected External Sampling MCCFR as the strongest practical deep/global blueprint direction on the representative equal-terminal-work benchmark. DCFR remains useful for smaller/conditioned exact subgames. That is architecture evidence, not a complete-game solution certificate.

M5A–M5G subsequently moved the project from architecture selection into continuation-aware Bellman orchestration with fail-closed promotion boundaries.

## Do not do

- Do not restart the solver architecture study without contradictory evidence.
- Do not call M5B/M5C/M5G machinery a production policy.
- Do not substitute migration equivalence for exploitability evidence.
- Do not substitute training loss/top-1 agreement for unilateral-deviation/held-out strategic evidence.
- Do not resurrect the superseded 119/123-file inventory numbers; the authoritative v2 migration set is 126.
- Do not move new strategic source back into the runtime repository.
- Do not infer latest runtime authority from the highest chat version number.
- Do not issue live clicks from ambiguous visual state.
- Do not let chat history become the only durable record of a milestone.

## Definition of the next meaningful strategic milestone

The repository migration milestone is **complete**.

The next true strategy milestone is the first meaningful set of **real held-out route certificates under an independently justified threshold protocol**. The full strategic promotion milestone is 50/50 real-certified exact-V routes plus an M5G real-ready registry enabling the first REAL dynamic M4Z Bellman trace.
