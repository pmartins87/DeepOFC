# DeepOFC version and provenance manifest

Manifest version: `2026-08-27.1`
Status: `TRANSITIONAL_CONSOLIDATION`

This file answers a simple question with immutable references: **which repository/ref currently owns each part of the project?**

The manifest remains transitional until the M4/M5 solver staging tree has been migrated from `myoh_private` into `DeepOFC` and equivalence-certified.

## Canonical repositories

| Component | Repository | Intended canonical branch | Current authority |
|---|---|---|---|
| Project governance / roadmap / handoff | `pmartins87/DeepOFC` | `main` | DeepOFC |
| Rules / model / scoring / simulator / reference solver | `pmartins87/DeepOFC` | `main` | DeepOFC |
| M4/M5 strategic staging | `pmartins87/myoh_private` | `openofc-m4v-continuation-transport` | temporary exception until migration |
| OpenHoldem runtime integration | `pmartins87/myoh_private` | `deepofc` plus explicitly named experiment branches | myoh_private |
| Runtime field package | `pmartins87/myoh_private` | must be source-bound | unresolved as one canonical latest package |

## Frozen strategic references

### Current M5C staging head

- repository: `pmartins87/myoh_private`
- branch: `openofc-m4v-continuation-transport`
- commit: `c21c3c4f1017c83df07eb22230318a8131bf40d1`
- message: `OpenOFC M5C: add staging certification gate`
- contract: `tools/openofc_solver/M5C_ROUTE_CERTIFICATION_CONTRACT.md`
- dedicated workflow: `.github/workflows/openofc-m5c-route-certification.yml`
- successful dedicated run: `33044932517`

### M5B anchor

- commit: `008307c972582df978a7ee7db6717bf8cc1fa1db`
- message: `OpenOFC M5B: add train-at-current-V normal kernel probes`
- principal file: `tools/openofc_solver/m5b_adaptive_normal_oracles.py`
- authority remains probe/not-certified until held-out strategic criteria pass.

## Frozen DeepOFC references

### Main baseline before consolidation

- repository: `pmartins87/DeepOFC`
- branch: `main`
- commit at consolidation start: `b3bd48245749e9b9128d90d433c063b2b6444f08`

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

### Preserved later runtime experiment lineage

The repository contains later named experiment branches including:

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

These branches are preserved evidence/experiments. Their existence alone does not define a canonical latest runtime package.

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

Until such a manifest exists, chat labels such as `v5.8.0` are useful test-session names but **not canonical source versions**.

## Strategic certification identity rule

A strategic route is promoted only through the M5C evidence/certificate mechanism. The current requirement for a complete real Bellman surface is 50 state-local ready certificates:

- 2 Normal × Normal;
- 16 Normal × Fantasy;
- 32 Fantasy × Fantasy.

The M5C CI success certifies the firewall implementation, not those 50 strategies.

## Migration authority rule

During solver migration:

1. the staged source commit above remains frozen;
2. migrated files must carry a provenance inventory mapping old path → source blob/commit → new path;
3. dependency closure must be explicit;
4. old and new implementations must produce matching deterministic golden outputs on the migration gate;
5. only after PASS may this manifest switch M4/M5 authority to `pmartins87/DeepOFC`.

## Update discipline

Update this manifest whenever any of the following changes:

- canonical solver head;
- production-candidate policy;
- runtime source head used for a package;
- tablemap/recognizer identity;
- milestone certification authority;
- repository ownership of a component.

Do not update version labels without updating immutable provenance in the same change.
