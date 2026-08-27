# DeepOFC canonical current state

Date: 2026-08-27
Status: active development; not production-ready
Canonical status schema: `deepofc-current-state-v3`

This document is the single entry point for the current project state. Historical milestone documents remain evidence, but when their status wording conflicts with this file, this file wins until the conflict is deliberately reconciled.

## Executive state

DeepOFC has two active engineering tracks that must converge before production:

1. **Strategy / solver** — the continuation/Bellman architecture is implemented through **M5G**. The strategic source staged in `pmartins87/myoh_private@c21c3c4f1017c83df07eb22230318a8131bf40d1` has now passed provenance-preserving migration and deterministic old-vs-new behavioral equivalence into DeepOFC. The remaining strategic blocker is real held-out evidence/certification, not repository ownership or architecture construction.
2. **Runtime / OpenHoldem** — recognition, reconstruction, transaction safety, drag/Confirm execution and field recovery remain a separately gated runtime problem. Existing v5.x field labels are not canonical project versions unless bound to source commit, policy, tablemap, recognizer/calibration and build/artifact provenance.

The repository-governance drift discovered on 2026-08-27 did **not** imply lost work. The M4/M5 strategic tree had been persisted in the OpenHoldem repository. That tree has now been migrated without semantic rewriting and compared against the frozen source.

## Repository authority

The intended authority split is restored:

- `pmartins87/DeepOFC` — canonical game model, scoring, simulator, solver, strategy research, training/exploitation design, evidence contracts, project roadmap and handoff documentation.
- `pmartins87/myoh_private` — OpenHoldem runtime integration, scraper/recognizer, UI transaction layer, runtime builds and runtime-specific field evidence.

The frozen `myoh_private@c21c3c4...` tree remains immutable **historical strategic provenance**. The migration branch `migration/openofc-solver-code-c21c3c4` is the authority-transfer candidate. When this change is present on `DeepOFC/main`, the temporary M4/M5 staging exception is closed.

## Strategic architecture frontier: M5G

The exact frozen staging tree proves that the architecture advanced beyond M5C. Its HEAD message says `OpenOFC M5C: add staging certification gate` because later M5C documentation/workflow commits followed the earlier M5D–M5G implementation commits. The HEAD subject is therefore not the architectural frontier.

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

Thus **architecture through M5G and repository migration are proven; strategic promotion is not**. The next strategy work is independent held-out evidence, an independently justified threshold protocol, state-local certification, then the first REAL M4Z Bellman trace.

## Solver migration — PASS through behavioral equivalence

### G1 v1 — useful failure, superseded

The first inventory policy added matching tests after computing dependency closure. The first behavioral equivalence run `33070445519` correctly caught the resulting gap: **19/20** probes matched, while migrated `test_engine.py` failed only because its local dependency `teacher_search.py` had not been selected. The frozen source test passed. This was an inventory-closure defect, not a solver semantic divergence.

### G1 v2 — fixed-point inventory PASS

The inventory policy was corrected to a fixed point over:

`selected Python -> local imports` and `migrated module -> matching test`, repeated until stable.

Authoritative corrected inventory:

- workflow run: `33070689091` — PASS;
- frozen solver-subtree files: **187**;
- migrate: **126**;
- historical: **61**;
- related M4/M5 workflows recorded: **38**;
- role counts: benchmark 19, contract 39, helper 10, source 64, test 55;
- files payload SHA-256: `06df84fa80c6bf869125ec858551b84c00895b4230c07079aa0b20eaa8b8c007`.

Artifacts:

- `docs/migration/openofc_solver_inventory_c21c3c4.json`
- `docs/migration/OPENOFC_SOLVER_INVENTORY_C21C3C4.md`

### G2/G3 — pure byte-identical migration PASS

Corrected pure-migration workflow run `33070802793` passed. It materialized the **126** selected files at the same `tools/openofc_solver/...` paths, compiled the Python tree, passed M5 core tests, passed the migrated M5 test surface, passed the `test_engine.py` regression and removed generated bytecode before persistence.

Provenance contract:

- all 126 source/target files byte-identical: **true**;
- inventory payload SHA-256: `06df84fa80c6bf869125ec858551b84c00895b4230c07079aa0b20eaa8b8c007`;
- provenance canonical SHA-256: `4041f7560f9a94b5e85b9c1c986f39e690bca5e3635328fad1bff1fdd1b11766`;
- materialized solver commit: `0c0ae8d77c8ca35c344f59c1515f6712b2ca1a2a`.

Artifacts:

- `docs/migration/openofc_solver_provenance_c21c3c4.json`
- `docs/migration/OPENOFC_SOLVER_MIGRATION_C21C3C4.md`

### G4 — deterministic old-vs-new behavioral equivalence PASS

Workflow run `33070910873` independently executed the frozen source checkout and migrated DeepOFC checkout under the same Python/runtime controls. **20/20 predeclared probes passed on both sides and produced identical normalized stdout/stderr.**

The suite covers engine behavior, HU continuation, M4U/M4V/M4W/M4X/M4Y/M4Z, M5A/M5B/M5C/M5D/M5E/M5F/M5G, Normal×Fantasy and Fantasy×Fantasy kernel/payoff paths.

- source PASS: 20/20;
- target PASS: 20/20;
- normalized transcript equality: 20/20;
- equivalence report SHA-256: `935162877ad8f7821fa106ba7cd2f5bfc588a60f2273c34443eb805926e93664`;
- equivalence evidence commit: `d45a9b77df8d75c1feaf45c8354ea152cd311355`.

Artifacts:

- `docs/migration/openofc_solver_equivalence_c21c3c4.json`
- `docs/migration/OPENOFC_SOLVER_EQUIVALENCE_C21C3C4.md`

These gates prove migration identity/equivalence. They do **not** certify strategic quality.

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
| R5/R6 decision + solver architecture | Advanced; architecture through M5G migrated/equivalence-proven; real route evidence/certification remains |
| R7 training | Not productionized; must emerge from certified solver architecture and reproducible artifact protocol |
| R8 exploitation | Deferred until a stronger certified base policy exists |
| R9 recognition/state bridge | Runtime live-safety blocker |
| R10 autoplayer | Developed behind safety gates; production execution still depends on recognition/reconstruction authority |
| R11 shadow | Blocked until replay/runtime certification |
| R12 controlled live | Blocked until sustained shadow safety |
| R13 production | Blocked until strategy + runtime + training + operations are reproducible and certified |

## Current critical path

### Repository / governance

1. Merge the migration/equivalence authority-transfer change into `DeepOFC/main` after PR CI PASS.
2. Thereafter treat `myoh_private@c21c3c4...` as immutable historical strategic provenance rather than an active strategic source.
3. Keep future solver development in DeepOFC and export explicit versioned policy artifacts to the runtime repository.

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
