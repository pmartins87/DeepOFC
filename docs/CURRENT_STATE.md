# DeepOFC canonical current state

Date: 2026-08-27
Status: active development; not production-ready
Canonical status schema: `deepofc-current-state-v2`

This document is the single entry point for the current project state. Historical milestone documents remain evidence, but when their status wording conflicts with this file, this file wins until the conflict is deliberately reconciled.

## Executive state

DeepOFC has two active engineering tracks that must converge before production:

1. **Strategy / solver** — the continuation/Bellman architecture is implemented through **M5G**, while real strategic evidence/certification remains the blocker. The M4/M5 tree is presently staged in `pmartins87/myoh_private`, branch `openofc-m4v-continuation-transport`, frozen at `c21c3c4f1017c83df07eb22230318a8131bf40d1`, pending controlled migration back into this authoritative model/solver repository.
2. **Runtime / OpenHoldem** — recognition, reconstruction, transaction safety, drag/Confirm execution and field recovery remain a separately gated runtime problem. Existing v5.x field labels must not be treated as canonical project versions unless they are bound to source commit, policy, tablemap and build provenance.

The repository-governance drift discovered on 2026-08-27 did **not** imply lost work. It meant the latest solver work was persisted in the OpenHoldem repository instead of this repository. The immediate consolidation task is provenance-preserving migration, not reimplementation.

## Repository authority

The intended authority split is restored as project policy:

- `pmartins87/DeepOFC` — canonical game model, scoring, simulator, solver, strategy research, training/exploitation design, evidence contracts, project roadmap and handoff documentation.
- `pmartins87/myoh_private` — OpenHoldem runtime integration, scraper/recognizer, UI transaction layer, runtime builds and runtime-specific field evidence.

Temporary exception: the M4/M5 strategic solver staging tree currently lives under `pmartins87/myoh_private/tools/openofc_solver`. It remains authoritative **for those staged files only** until the migration gate in `docs/SOLVER_MIGRATION_PLAN.md` is complete.

## Strategic architecture frontier: M5G

The exact frozen staging tree proves that the architecture advanced beyond M5C. The staging HEAD message still says `OpenOFC M5C: add staging certification gate`, because additional M5C documentation/workflow commits were added after M5D–M5G implementation commits. Therefore the HEAD subject is **not** the strategic frontier.

Frozen source:

- repository: `pmartins87/myoh_private`
- branch: `openofc-m4v-continuation-transport`
- frozen head: `c21c3c4f1017c83df07eb22230318a8131bf40d1`
- M5B anchor: `008307c972582df978a7ee7db6717bf8cc1fa1db` — train-at-current-V normal kernel probes
- M5C dedicated workflow run: `33044932517` — PASS for the certification firewall implementation
- M5G implementation anchor: `a7befe2a47b456d4f08a240cd7968e6ec38cb150` — full authoritative registry factory

### M5A–M5G interpretation

- **M5A** — continuation-aware fixed-policy/model value adapters.
- **M5B** — policy improvement trained at the current continuation vector; still probe/not-certified until held-out strategic evidence passes.
- **M5C** — fail-closed route certification firewall. Its CI PASS proves the firewall mechanism, not policy quality.
- **M5D** — dynamic exact-V certified Bellman orchestration: a route must be certified for the continuation vector actually being evaluated; synthetic evidence remains incapable of real promotion.
- **M5E** — Fantasy×Fantasy route-certification bridge with the additional support-gap/model-error requirements.
- **M5F** — Fantasy×Fantasy held-out evidence producer combining the exact-support teacher, support-restricted deviation evidence and held-out model/action-value error. Its generated evidence is not automatically production-ready.
- **M5G** — full 50-state registry factory and final architectural certification firewall before a REAL dynamic M4Z Bellman trace. It assembles already certified routes; it does not create the missing strategic evidence or choose thresholds.

### What is still blocked

A complete real Bellman surface still requires **50 distinct real-certified exact-V routes**:

- 2 Normal × Normal;
- 16 Normal × Fantasy;
- 32 Fantasy × Fantasy.

Required evidence includes independent held-out seeds/samples, bounded value standard error and unilateral-deviation gain. Fantasy × Fantasy additionally requires the exact-teacher support gap and held-out model/action-value error criteria.

Thus **architecture through M5G is present; strategic promotion is not**. The next strategy work is independent held-out evidence, an independently justified threshold protocol, state-local certification, and only then a REAL M4Z Bellman trace.

## G1 migration inventory — PASS

The first provenance-preserving migration gate is now materialized on branch `migration/openofc-solver-inventory-c21c3c4`.

Artifacts:

- `docs/migration/openofc_solver_inventory_c21c3c4.json`
- `docs/migration/OPENOFC_SOLVER_INVENTORY_C21C3C4.md`
- generator: `tools/migration/build_openofc_solver_inventory.py`
- workflow: `.github/workflows/openofc-solver-inventory.yml`
- workflow run: `33059295351` — PASS
- materialized inventory commit: `92d43f141c1a55f65c801749503619105479c70c`

Inventory result:

- 152 files in the frozen solver staging subtree;
- 69 files in the current-root transitive dependency closure;
- 119 files marked `migrate` after adding current contracts and tests of migrated dependencies;
- 33 files preserved as `historical` rather than silently copied;
- 38 related M4/M5 workflows recorded;
- file-list/provenance payload SHA-256: `89a546aef6f367226cbaf9c6a54d886488519d88b0f1c7d07415db13df382e84`.

G1 is an ownership/provenance PASS. It does not alter strategic authority yet.

## Solver quality state

The earlier R6 architecture tribunal remains valid background evidence: under the representative equal-terminal-work benchmark, External Sampling MCCFR was the strongest practical deep/global blueprint route among the tested implementations, while DCFR remained useful for tractable exact/conditioned subgames.

That result selected an architecture direction; it did not solve the full Joker Ultimate game.

The M4/M5 lineage has moved the project from algorithm selection toward continuation-aware Bellman machinery with exact-V certification boundaries. Production exploitability for the complete target game remains uncertified.

## Runtime state

The latest consolidated DeepOFC runtime-continuity checkpoint in this repository is the v5.4 continuity work on branch `agent/runtime-continuity-v54`, head `f4fcccc5453b5156ab6bf4b195cf3759c1676955`.

That checkpoint established the intended semantics:

- a bad/ambiguous scrape may suppress an unsafe click, but must not permanently suppress future scrapes or valid decisions;
- stale process lineage must not override a valid current screen;
- reacquisition must discard stale plans;
- mid-hand bootstrap and Fantasy 14–17 bootstrap need explicit support;
- drag/Confirm idempotence must survive reacquisition;
- build logs must identify source, policy and tablemap provenance.

Subsequent runtime source work, including later v5.8.x-labelled tooling, is preserved in `pmartins87/myoh_private`. The field-build naming lineage is not yet consolidated enough to declare one later chat/build label the canonical package identity.

Accordingly, **no unbound field label such as `v5.8.0` is a canonical source/package version until source commit + policy + tablemap + recognizer/calibration + build/artifact provenance are recorded together.**

## Global roadmap interpretation

The R0–R13 roadmap remains the production-readiness framework. Its older status table is retained as historical structure, while current status is interpreted as follows:

| Area | Current interpretation |
|---|---|
| R0–R3 rules/scoring/actions | Advanced foundation; keep closing edge cases and independent validation |
| R4 simulator | Advanced foundation; full representative game scaling remains |
| R5/R6 decision + solver architecture | Advanced; continuation/Bellman architecture now staged through M5G, with real route evidence/certification still blocked |
| R7 training | Not productionized; must emerge from certified solver architecture and reproducible artifact protocol |
| R8 exploitation | Deferred until a stronger certified base policy exists |
| R9 recognition/state bridge | Runtime live-safety blocker |
| R10 autoplayer | Developed behind safety gates; production execution still depends on recognition/reconstruction authority |
| R11 shadow | Blocked until replay/runtime certification |
| R12 controlled live | Blocked until sustained shadow safety |
| R13 production | Blocked until strategy + runtime + training + operations are reproducible and certified |

## Current critical path

### Governance / continuity

1. Merge the frozen G1 inventory and corrected M5G frontier into `DeepOFC/main`.
2. Define the pure-migration target layout and generate old-path/source-blob/new-path provenance mapping.
3. Copy the 119 `migrate` files with no semantic edits.
4. Run independent DeepOFC CI plus deterministic old-vs-new equivalence gates.
5. Switch M4/M5 authority to DeepOFC only after equivalence PASS.
6. Freeze `myoh_private@c21c3c4...` as historical strategic provenance after authority transfer.

### Strategy

1. Generate independent held-out Normal × Normal deviation/uncertainty evidence.
2. Generate independent held-out Normal × Fantasy deviation/uncertainty evidence.
3. Generate Fantasy × Fantasy support-gap + deviation + held-out model/action-value error evidence under the M5E/M5F contracts.
4. Freeze thresholds from a separately justified protocol.
5. Certify all 50 exact-V routes state-by-state.
6. Build the real-ready M5G registry from 50/50 real certificates.
7. Enable the first REAL dynamic M4Z 50-state Bellman trace.
8. Measure convergence/stability/exploitability and decide the next scaling/training gate from evidence.

### Runtime

1. Consolidate runtime build provenance into one machine-readable manifest.
2. Bind every field package to native source commit, policy/solver version, tablemap/recognizer identity and artifact SHA.
3. Continue deterministic pixels → physical cards → raw observation → canonical state proof.
4. Certify transaction loop: drag → fresh scrape → exact verification; Confirm → committed-state verification.
5. Shadow mode before controlled live use.

## Hard project rules

- A code path existing is not a gate PASS.
- A CI PASS for a certification framework is not a strategic policy certificate.
- M5G architecture presence is not 50/50 real certification.
- Training loss, imitation agreement or smoke-test improvement cannot substitute for held-out strategic evidence.
- No ambiguous visual state may be guessed into a live action.
- No runtime build label is canonical without immutable provenance.
- No solver migration may silently rewrite semantics; equivalence comes before authority transfer.
- Chat history is useful context, but GitHub artifacts and explicit manifests are the durable project record.

## Start here on every continuation

Read, in order:

1. `docs/CURRENT_STATE.md`
2. `docs/VERSION_MANIFEST.md`
3. `docs/HANDOFF.md`
4. `docs/ROADMAP.md`
5. the milestone-specific contract/evidence named by the handoff

This ordering is deliberate: it prevents older roadmap/status wording from silently overriding newer frozen project state.
