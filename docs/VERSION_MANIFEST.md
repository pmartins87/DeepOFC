# DeepOFC version and provenance manifest

Manifest version: `2026-08-27.2`
Status: `TRANSITIONAL_CONSOLIDATION`

This file answers a simple question with immutable references: **which repository/ref currently owns each part of the project?**

The manifest remains transitional until the M4/M5 solver staging tree has been migrated from `myoh_private` into `DeepOFC` and equivalence-certified.

## Canonical repositories

| Component | Repository | Intended canonical branch | Current authority |
|---|---|---|---|
| Project governance / roadmap / handoff | `pmartins87/DeepOFC` | `main` | DeepOFC |
| Rules / model / scoring / simulator / reference solver | `pmartins87/DeepOFC` | `main` | DeepOFC |
| M4/M5 strategic staging | `pmartins87/myoh_private` | `openofc-m4v-continuation-transport` | temporary exception until migration/equivalence PASS |
| OpenHoldem runtime integration | `pmartins87/myoh_private` | `deepofc` plus explicitly named experiment branches | myoh_private |
| Runtime field package | `pmartins87/myoh_private` | must be source-bound | unresolved as one canonical latest package |

## Frozen strategic source

- repository: `pmartins87/myoh_private`
- branch: `openofc-m4v-continuation-transport`
- frozen commit: `c21c3c4f1017c83df07eb22230318a8131bf40d1`
- frozen tree: `73523862dac5b704d6f9878edefaa36212f20bc9`
- HEAD message: `OpenOFC M5C: add staging certification gate`

**Important:** the HEAD message does not identify the architectural frontier. The exact tree at that commit contains M5D, M5E, M5F and M5G implementations/contracts/tests that were committed earlier and then followed by additional M5C documentation/workflow commits.

## Strategic architecture references

### M5B — train at current V

- anchor commit: `008307c972582df978a7ee7db6717bf8cc1fa1db`
- message: `OpenOFC M5B: add train-at-current-V normal kernel probes`
- principal file: `tools/openofc_solver/m5b_adaptive_normal_oracles.py`
- authority remains probe/not-certified until held-out strategic criteria pass.

### M5C — route certification firewall

- contract: `tools/openofc_solver/M5C_ROUTE_CERTIFICATION_CONTRACT.md`
- dedicated workflow: `.github/workflows/openofc-m5c-route-certification.yml`
- dedicated successful run: `33044932517`
- meaning: firewall implementation PASS; strategic routes themselves remain uncertified.

### M5D — dynamic exact-V certification

- contract: `tools/openofc_solver/M5D_DYNAMIC_CERTIFIED_BELLMAN_CONTRACT.md`
- implementation: `tools/openofc_solver/m5d_dynamic_certified_bellman.py`
- meaning: per-iterate Bellman routing remains fail-closed unless routes are certified for the actual continuation vector.

### M5E — Fantasy route certification

- contract: `tools/openofc_solver/M5E_FANTASY_ROUTE_CERTIFICATION_CONTRACT.md`
- implementation: `tools/openofc_solver/m5e_fantasy_route_certification.py`
- meaning: Fantasy×Fantasy routes require their additional support-gap/model-error evidence; synthetic evidence cannot promote a real route.

### M5F — Fantasy held-out evidence producer

- contract: `tools/openofc_solver/M5F_FANTASY_HELDOUT_EVIDENCE_CONTRACT.md`
- implementation: `tools/openofc_solver/m5f_fantasy_heldout_evidence.py`
- meaning: combines the required Fantasy evidence components but does not by itself make evidence production-ready.

### M5G — full authoritative registry factory

- anchor commit: `a7befe2a47b456d4f08a240cd7968e6ec38cb150`
- message: `OpenOFC M5G: add full authoritative registry factory`
- contract: `tools/openofc_solver/M5G_FULL_REGISTRY_FACTORY_CONTRACT.md`
- implementation: `tools/openofc_solver/m5g_full_registry_factory.py`
- meaning: final architectural firewall assembling the complete 50-state registry from already real-certified exact-V routes. It does not create strategic evidence or tune thresholds.

## Strategic certification identity rule

A complete real Bellman surface still requires **50 state-local real-certified exact-V routes**:

- 2 Normal × Normal;
- 16 Normal × Fantasy;
- 32 Fantasy × Fantasy.

Architecture through M5G does not waive these requirements. A REAL dynamic M4Z trace remains blocked until the complete real-ready registry exists.

## DeepOFC governance references

### Consolidation baseline

- pre-consolidation main: `b3bd48245749e9b9128d90d433c063b2b6444f08`
- consolidation PR: `#11`
- consolidation main commit: `a90cf7a3713c1a1e5fd402a4cbd29a38c00ebaf7`

### G1 frozen solver inventory

- branch: `migration/openofc-solver-inventory-c21c3c4`
- generated inventory commit: `92d43f141c1a55f65c801749503619105479c70c`
- workflow run: `33059295351` — PASS
- machine-readable inventory: `docs/migration/openofc_solver_inventory_c21c3c4.json`
- human summary: `docs/migration/OPENOFC_SOLVER_INVENTORY_C21C3C4.md`
- source-files payload SHA-256: `89a546aef6f367226cbaf9c6a54d886488519d88b0f1c7d07415db13df382e84`
- result: 152 staging files inventoried; 119 marked `migrate`; 33 preserved as `historical`; 38 related M4/M5 workflows recorded.

This is a provenance/ownership gate only. Strategic authority stays in the frozen staging source until migration + equivalence PASS.

### Runtime-continuity reference checkpoint

- repository: `pmartins87/DeepOFC`
- branch: `agent/runtime-continuity-v54`
- head: `f4fcccc5453b5156ab6bf4b195cf3759c1676955`
- status document: `docs/V54_STAGE1_STATUS.md`
- field gate: `docs/V54_FIELD_GATE.md`

## OpenHoldem runtime references

### Canonical integration baseline

- repository: `pmartins87/myoh_private`
- branch: `deepofc`
- head observed at consolidation: `705362437d1eb2fef582f48f9c64966b3795b76f`

### Preserved later runtime lineage

The repository preserves later runtime branches/tooling, including v5.4/v5.43/v5.44 lineage and later v5.8.x-labelled source tooling. Those sources are durable evidence, but their labels alone do not define one canonical field package.

Examples of preserved runtime experiment branches include:

- `openofc-v54-runtime-continuity`
- `openofc-v542b-partial-reconnect`
- `openofc-v542c-dealer-recovery`
- `openofc-v543-confirm-gate`
- `openofc-v543-field-resilience`
- `openofc-v543-fieldfix-tablemap-contract5`
- `openofc-v543-generic-fantasy`
- `openofc-v543-joker-execution-gate`
- `openofc-v543-joker-pixel-gate*`
- `openofc-v544-field-recovery` at observed head `382bb569dc787808042c6ac51a833d4c03c8f752`

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

Until such a manifest exists, chat labels such as `v5.8.0` are useful test-session names but **not canonical source/package versions**.

## Migration authority rule

During solver migration:

1. frozen source remains `myoh_private@c21c3c4f1017c83df07eb22230318a8131bf40d1`;
2. the checked-in G1 inventory is the authoritative source-set/provenance input;
3. migrated files must carry an old-path/source-blob/source-SHA256 → target-path/target-SHA256 map;
4. pure migration must make no semantic changes;
5. old and new implementations must produce matching deterministic golden behavior on the migration gate;
6. only after equivalence PASS may this manifest switch M4/M5 authority to `pmartins87/DeepOFC`.

## Update discipline

Update this manifest whenever any of the following changes:

- canonical solver head;
- production-candidate policy;
- runtime source head used for a package;
- tablemap/recognizer identity;
- milestone certification authority;
- repository ownership of a component.

Do not update version labels without updating immutable provenance in the same change.
