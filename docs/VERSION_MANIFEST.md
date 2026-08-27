# DeepOFC version and provenance manifest

Manifest version: `2026-08-27.3`
Status: `STRATEGIC_MIGRATION_EQUIVALENCE_PASS`

This file answers a simple question with immutable references: **which repository/ref owns each part of the project, and what evidence supports that authority?**

## Canonical repositories

| Component | Repository | Canonical branch/ref | Authority |
|---|---|---|---|
| Project governance / roadmap / handoff | `pmartins87/DeepOFC` | `main` | DeepOFC |
| Rules / model / scoring / simulator / strategic solver | `pmartins87/DeepOFC` | `main` after the migration/equivalence change is merged | DeepOFC strategic authority transfer is evidenced and ready |
| Frozen M4/M5 strategic provenance | `pmartins87/myoh_private` | `c21c3c4f1017c83df07eb22230318a8131bf40d1` | historical immutable provenance |
| OpenHoldem runtime integration | `pmartins87/myoh_private` | `deepofc` plus explicitly named experiment branches | myoh_private |
| Runtime field package | `pmartins87/myoh_private` | must be source-bound | unresolved as one canonical latest package |

The migration/equivalence branch is `migration/openofc-solver-code-c21c3c4`. This manifest is part of that authority-transfer change: once present on `DeepOFC/main`, the former temporary M4/M5 strategic staging exception is closed.

## Frozen strategic source

- repository: `pmartins87/myoh_private`
- branch: `openofc-m4v-continuation-transport`
- commit: `c21c3c4f1017c83df07eb22230318a8131bf40d1`
- solver tree: `73523862dac5b704d6f9878edefaa36212f20bc9`
- HEAD subject: `OpenOFC M5C: add staging certification gate`
- M5G anchor: `a7befe2a47b456d4f08a240cd7968e6ec38cb150`

The exact frozen tree contains architecture through **M5G**. The HEAD subject is not the architectural frontier.

## Strategic architecture anchors

### M5B

- commit: `008307c972582df978a7ee7db6717bf8cc1fa1db`
- principal file: `tools/openofc_solver/m5b_adaptive_normal_oracles.py`
- interpretation: train-at-current-V policy-improvement probe; not real-certified policy.

### M5C

- contract: `tools/openofc_solver/M5C_ROUTE_CERTIFICATION_CONTRACT.md`
- successful dedicated run: `33044932517`
- interpretation: certification-firewall implementation PASS only.

### M5D–M5G

The frozen tree contains:

- M5D dynamic exact-V certified Bellman orchestration;
- M5E Fantasy×Fantasy certification bridge;
- M5F Fantasy×Fantasy held-out evidence producer;
- M5G full 50-state registry factory.

M5G requires already certified routes and cannot manufacture real evidence, choose production thresholds or certify the complete game by itself.

## Corrected strategic migration identity

### G1 v1 — superseded

The first inventory selection was not dependency-closed after matching tests were added. The first behavioral-equivalence run `33070445519` passed **19/20** probes and exposed the missing `test_engine.py -> teacher_search.py` dependency on the target side. Frozen source behavior remained green. This is recorded as an inventory-policy defect, not a semantic divergence.

### G1 v2 — fixed-point inventory

Workflow run `33070689091`: **PASS**.

Frozen inventory:

- schema: `deepofc-openofc-solver-inventory-v2`;
- solver-subtree files: **187**;
- migrate: **126**;
- historical: **61**;
- related M4/M5 workflows: **38**;
- roles: benchmark 19, contract 39, helper 10, source 64, test 55;
- files payload SHA-256: `06df84fa80c6bf869125ec858551b84c00895b4230c07079aa0b20eaa8b8c007`.

Selection is a fixed point over local imports and matching tests. `teacher_search.py` is explicitly inside the corrected selected set.

### G2/G3 — pure migration

Corrected pure migration run `33070802793`: **PASS**.

- migrated files: **126**;
- all source/target files byte-identical: **true**;
- provenance canonical SHA-256: `4041f7560f9a94b5e85b9c1c986f39e690bca5e3635328fad1bff1fdd1b11766`;
- materialized solver commit: `0c0ae8d77c8ca35c344f59c1515f6712b2ca1a2a`;
- generated Python bytecode is removed before persistence and is not migration evidence.

Primary artifacts:

- `docs/migration/openofc_solver_provenance_c21c3c4.json`
- `docs/migration/OPENOFC_SOLVER_MIGRATION_C21C3C4.md`

### G4 — old-vs-new behavioral equivalence

Workflow run `33070910873`: **PASS**.

- suite: `openofc-migration-equivalence-2026-08-27-v1`;
- Python: `3.11.16`;
- NumPy: `2.4.6`;
- `PYTHONHASHSEED=0` and single-thread numerical-library controls;
- tests: **20**;
- frozen source PASS: **20/20**;
- migrated target PASS: **20/20**;
- normalized stdout/stderr equality: **20/20**;
- equivalence report SHA-256: `935162877ad8f7821fa106ba7cd2f5bfc588a60f2273c34443eb805926e93664`;
- gate-start target commit: `dd5839c364e7a9d18b97ab580c1ad38d9814ac9f`;
- persisted equivalence evidence commit: `d45a9b77df8d75c1feaf45c8354ea152cd311355`.

Primary artifacts:

- `docs/migration/openofc_solver_equivalence_c21c3c4.json`
- `docs/migration/OPENOFC_SOLVER_EQUIVALENCE_C21C3C4.md`

The 20-probe suite covers engine behavior, HU continuation, M4U–M4Z, M5A–M5G and Normal×Fantasy/Fantasy×Fantasy kernel/payoff paths.

## Strategic certification identity rule

Migration equivalence establishes source identity/behavior across repositories. It does **not** establish strategic optimality.

A complete real Bellman surface still requires **50 state-local real-certified exact-V routes**:

- 2 Normal × Normal;
- 16 Normal × Fantasy;
- 32 Fantasy × Fantasy.

Required evidence includes held-out seeds/samples, value standard error, unilateral-deviation gain, and for Fantasy × Fantasy the exact-teacher support gap plus held-out M4W model/action-value error.

The next strategic authority after repository transfer is therefore the **evidence/certification protocol**, not an unconditional production policy.

## OpenHoldem runtime references

### Canonical integration baseline

- repository: `pmartins87/myoh_private`
- branch: `deepofc`
- observed consolidation head: `705362437d1eb2fef582f48f9c64966b3795b76f`

### Runtime-continuity reference checkpoint

- repository: `pmartins87/DeepOFC`
- branch: `agent/runtime-continuity-v54`
- head: `f4fcccc5453b5156ab6bf4b195cf3759c1676955`
- status document: `docs/V54_STAGE1_STATUS.md`
- field gate: `docs/V54_FIELD_GATE.md`

### Preserved runtime experiment lineage

`myoh_private` contains later `openofc-v54*`, `openofc-v542*`, `openofc-v543*`, `openofc-v544*` and later v5.8.x-labelled experimental/runtime work. Branch names and chat labels remain evidence labels, not canonical field-package identities by themselves.

## Field-build identity rule

A field package is canonical only when one immutable manifest binds at least:

- semantic package/version label;
- native OpenHoldem source commit;
- solver/policy identity or explicit baseline-policy identity;
- tablemap identity and SHA-256;
- recognizer/calibration identity;
- build workflow/run or reproducible local build recipe;
- artifact SHA-256;
- applicable runtime safety-gate status;
- date and provenance.

## Update discipline

Update this manifest whenever any of the following changes:

- canonical solver head;
- production-candidate policy;
- route-certification/evidence authority;
- runtime source head used for a package;
- tablemap/recognizer identity;
- milestone certification authority;
- repository ownership of a component.

Do not update version labels without updating immutable provenance in the same change.
