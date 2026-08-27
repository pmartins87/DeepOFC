# DeepOFC canonical current state

Date: 2026-08-27
Status: active development; not production-ready
Canonical status schema: `deepofc-current-state-v4`

This document is the single entry point for the current project state. Historical milestone documents remain evidence, but when their status wording conflicts with this file, this file wins until the conflict is deliberately reconciled.

## Executive state

DeepOFC has two active engineering tracks that must converge before production:

1. **Strategy / solver** — the continuation/Bellman architecture is implemented through **M5G** and is now canonically owned by `pmartins87/DeepOFC/main`. The former strategic staging tree from `pmartins87/myoh_private@c21c3c4f1017c83df07eb22230318a8131bf40d1` completed corrected fixed-point inventory, 126/126 byte-identical migration, 20/20 deterministic old-vs-new equivalence, canonical PR CI, merge and post-merge main CI. The remaining strategic blocker is real held-out evidence/certification.
2. **Runtime / OpenHoldem** — recognition, reconstruction, transaction safety, drag/Confirm execution and field recovery remain a separately gated runtime problem. Existing v5.x field labels are not canonical project versions unless bound to source commit, policy, tablemap, recognizer/calibration and build/artifact provenance.

The repository-governance drift discovered on 2026-08-27 did **not** imply lost work. The M4/M5 strategic tree had been persisted in the OpenHoldem repository. That tree has now been migrated without semantic rewriting, equivalence-proven and transferred back into the intended strategic repository.

## Repository authority

The authority split is restored and final for this migration:

- `pmartins87/DeepOFC`, branch `main` — canonical game model, scoring, simulator, solver, strategy research, training/exploitation design, evidence contracts, project roadmap and handoff documentation.
- `pmartins87/myoh_private` — OpenHoldem runtime integration, scraper/recognizer, UI transaction layer, runtime builds and runtime-specific field evidence.
- `pmartins87/myoh_private@c21c3c4...` — immutable historical provenance for the formerly staged M4/M5 strategic tree, not an active strategic source.

Authority-transfer record:

- PR #13;
- merge commit `4842d01dc68b14bae5a083d8ae0138297d7a0783`;
- post-merge `main` CI run `33074839933` — **PASS**;
- final record `docs/migration/OPENOFC_SOLVER_AUTHORITY_TRANSFER_C21C3C4.md`.

## Strategic architecture frontier: M5G

The exact frozen staging tree proved that architecture advanced beyond M5C. Its HEAD message says `OpenOFC M5C: add staging certification gate` because later M5C documentation/workflow commits followed earlier M5D–M5G implementation commits. The HEAD subject is therefore not the architectural frontier.

Frozen source provenance:

- repository: `pmartins87/myoh_private`
- branch: `openofc-m4v-continuation-transport`
- frozen commit: `c21c3c4f1017c83df07eb22230318a8131bf40d1`
- frozen solver tree: `73523862dac5b704d6f9878edefaa36212f20bc9`
- M5B anchor: `008307c972582df978a7ee7db6717bf8cc1fa1db`
- M5C dedicated workflow run: `33044932517` — certification-firewall implementation PASS
- M5G anchor: `a7befe2a47b456d4f08a240cd7968e6ec38cb150`

### M5A–M5G interpretation

- **M5A** — continuation-aware fixed-policy/model value adapters.
- **M5B** — policy-improvement probes trained at the current continuation vector; still probe/not-certified until held-out strategic evidence passes.
- **M5C** — fail-closed route-certification firewall. Its CI PASS proves the mechanism, not policy quality.
- **M5D** — dynamic exact-V certified Bellman orchestration: a route must be certified for the continuation vector actually being evaluated.
- **M5E** — Fantasy×Fantasy route-certification bridge with support-gap/model-error requirements.
- **M5F** — Fantasy×Fantasy held-out evidence producer combining exact-support teacher, support-restricted deviation evidence and held-out model/action-value error. Produced evidence is not automatically production-ready.
- **M5G** — full 50-state registry factory and final architectural firewall before a REAL dynamic M4Z Bellman trace. It assembles already certified routes; it does not create missing evidence or choose thresholds.

### What is still blocked strategically

A complete real Bellman surface requires **50 distinct real-certified exact-V routes**:

- 2 Normal × Normal;
- 16 Normal × Fantasy;
- 32 Fantasy × Fantasy.

Required evidence includes independent held-out seeds/samples, bounded value standard error and unilateral-deviation gain. Fantasy × Fantasy additionally requires exact-teacher support gap and held-out model/action-value error criteria.

Thus **architecture through M5G and repository authority transfer are proven; strategic promotion is not**. The next strategy work is independent held-out evidence, an independently justified threshold protocol, state-local certification, then the first REAL M4Z Bellman trace.

## Solver migration / authority transfer — G1–G6 COMPLETE

### G1 v1 — useful failure, superseded

The first inventory policy added matching tests after computing dependency closure. Behavioral equivalence run `33070445519` correctly caught the resulting gap: **19/20** probes matched, while migrated `test_engine.py` failed only because local dependency `teacher_search.py` had not been selected. The frozen source test passed. This was an inventory-closure defect, not solver semantic divergence.

### G1 v2 — fixed-point inventory — PASS

The inventory policy was corrected to a fixed point over selected Python modules, their local imports, matching tests, and dependencies introduced by those tests.

Authoritative corrected inventory:

- workflow run `33070689091` — **PASS**;
- frozen solver-subtree files: **187**;
- migrate: **126**;
- historical: **61**;
- related M4/M5 workflows recorded: **38**;
- role counts: benchmark 19, contract 39, helper 10, source 64, test 55;
- files payload SHA-256: `06df84fa80c6bf869125ec858551b84c00895b4230c07079aa0b20eaa8b8c007`.

### G2/G3 — pure byte-identical migration / independent migrated tests — PASS

Corrected pure-migration workflow run `33070802793`: **PASS**.

- 126 selected files materialized at the same `tools/openofc_solver/...` paths;
- all 126 source/target files byte-identical: **true**;
- Python compile PASS;
- M5 core tests PASS;
- migrated M5 test surface PASS;
- `test_engine.py` regression PASS;
- generated Python bytecode removed before persistence;
- provenance canonical SHA-256: `4041f7560f9a94b5e85b9c1c986f39e690bca5e3635328fad1bff1fdd1b11766`;
- materialized solver commit: `0c0ae8d77c8ca35c344f59c1515f6712b2ca1a2a`.

### G4 — deterministic old-vs-new behavioral equivalence — PASS

Workflow run `33070910873`: **PASS**.

The frozen source and migrated DeepOFC tree were run independently under the same Python/runtime controls.

- source PASS: 20/20;
- target PASS: 20/20;
- normalized transcript equality: 20/20;
- equivalence report SHA-256: `935162877ad8f7821fa106ba7cd2f5bfc588a60f2273c34443eb805926e93664`;
- persisted equivalence evidence commit: `d45a9b77df8d75c1feaf45c8354ea152cd311355`.

The suite covers engine behavior, HU continuation, M4U/M4V/M4W/M4X/M4Y/M4Z, M5A/M5B/M5C/M5D/M5E/M5F/M5G, Normal×Fantasy and Fantasy×Fantasy kernel/payoff paths.

### G5 — canonical DeepOFC PR CI — PASS

PR #13 initially exposed one integration omission: repository-level `requirements-dev.txt` did not yet declare NumPy, which newly migrated tests import. `numpy==2.4.6` was added, matching the proven migration/equivalence environment.

- corrected PR head: `c364a3056349ba627f273265c7c7a742b2d72c99`;
- canonical PR CI run `33074562167`: **PASS**.

### G6 — merge / authority transfer — PASS

- PR #13 merged;
- merge commit: `4842d01dc68b14bae5a083d8ae0138297d7a0783`;
- post-merge `main` CI run `33074839933`: **PASS**;
- DeepOFC main is now the active strategic authority;
- frozen `myoh_private@c21c3c4...` is historical provenance only.

These gates prove migration identity/equivalence and repository authority. They do **not** certify strategic quality.

## Solver quality state

The earlier R6 architecture tribunal remains valid background evidence: under the representative equal-terminal-work benchmark, External Sampling MCCFR was the strongest practical deep/global blueprint route among tested implementations, while DCFR remained useful for tractable exact/conditioned subgames.

That selected an architecture direction; it did not solve the full Joker Ultimate game. M4/M5 then built continuation-aware Bellman machinery with exact-V promotion boundaries. Full-game production exploitability remains uncertified.

## Runtime state

The latest consolidated DeepOFC runtime-continuity checkpoint in this repository is the v5.4 continuity work on branch `agent/runtime-continuity-v54`, head `f4fcccc5453b5156ab6bf4b195cf3759c1676955`.

Required runtime semantics remain:

- ambiguous/bad scrape suppresses unsafe action without permanently blocking later valid reacquisition;
- current-screen evidence outranks stale process lineage;
- reacquisition discards stale plans;
- mid-hand and Fantasy 14–17 bootstrap require explicit support;
- drag/Confirm execution must remain idempotent across reacquisition;
- every field build must expose source, policy and tablemap provenance.

Later v5.8.x-labelled runtime tooling is preserved in `pmartins87/myoh_private`, but a field package becomes canonical only when source commit, policy, tablemap, recognizer/calibration, build and artifact SHA are bound together.

## Global roadmap interpretation

The R0–R13 roadmap remains the production-readiness framework.

| Area | Current interpretation |
|---|---|
| R0–R3 rules/scoring/actions | Advanced foundation; keep closing edge cases and independent validation |
| R4 simulator | Advanced foundation; full representative game scaling remains |
| R5/R6 decision + solver architecture | Advanced; architecture through M5G migrated, equivalence-proven and canonically owned by DeepOFC; real route evidence/certification remains |
| R7 training | Not productionized; must emerge from certified solver architecture and reproducible artifact protocol |
| R8 exploitation | Deferred until a stronger certified base policy exists |
| R9 recognition/state bridge | Runtime live-safety blocker |
| R10 autoplayer | Developed behind safety gates; production execution still depends on recognition/reconstruction authority |
| R11 shadow | Blocked until replay/runtime certification |
| R12 controlled live | Blocked until sustained shadow safety |
| R13 production | Blocked until strategy + runtime + training + operations are reproducible and certified |

## Current critical path

### Repository / governance

1. Keep all new solver/strategy development in `DeepOFC/main` or review branches based from it.
2. Preserve `myoh_private@c21c3c4...` as immutable historical provenance.
3. Export explicit versioned policy artifacts to the runtime repository rather than moving strategic source authority back there.
4. Keep canonical current-state, handoff and manifest documents synchronized with future strategic milestones.

### Strategy

1. Generate independent held-out Normal × Normal deviation/uncertainty evidence.
2. Generate independent held-out Normal × Fantasy deviation/uncertainty evidence.
3. Generate Fantasy × Fantasy support-gap + deviation + held-out model/action-value error evidence under M5E/M5F.
4. Freeze thresholds from a separately justified protocol.
5. Certify all 50 exact-V routes state-by-state.
6. Build the M5G real-ready registry from 50/50 real certificates.
7. Enable the first REAL dynamic M4Z 50-state Bellman trace.
8. Measure convergence/stability/exploitability and decide the next scaling/training gate from evidence.

### Runtime

1. Consolidate runtime build provenance into one machine-readable manifest.
2. Bind every field package to native source commit, policy/solver version, tablemap/recognizer identity and artifact SHA.
3. Continue deterministic pixels → physical cards → raw observation → canonical state proof.
4. Certify drag → fresh scrape → exact verification and Confirm → committed-state verification.
5. Shadow mode before controlled live use.

## Hard project rules

- A code path existing is not a gate PASS.
- A CI PASS for a certification framework is not a strategic policy certificate.
- M5G architecture presence is not 50/50 real certification.
- Migration equivalence proves source transfer, not exploitability.
- Repository authority transfer does not imply strategic promotion.
- Training loss, imitation agreement or smoke-test improvement cannot substitute for held-out strategic evidence.
- No ambiguous visual state may be guessed into a live action.
- No runtime build label is canonical without immutable provenance.
- Chat history is useful context, but GitHub artifacts and explicit manifests are the durable project record.

## Start here on every continuation

Read, in order:

1. `docs/CURRENT_STATE.md`
2. `docs/VERSION_MANIFEST.md`
3. `docs/HANDOFF.md`
4. `docs/ROADMAP.md`
5. the milestone-specific contract/evidence named by the handoff
