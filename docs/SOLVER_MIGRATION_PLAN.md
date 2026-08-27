# DeepOFC solver migration plan

Date: 2026-08-27
Status: G1 inventory PASS; G2/G3 pure migration next

## Goal

Move the recent M4/M5 strategic development from its temporary staging location in `pmartins87/myoh_private/tools/openofc_solver` into the intended authoritative solver repository `pmartins87/DeepOFC`, while preserving provenance and proving behavioral equivalence.

## Frozen source

- repository: `pmartins87/myoh_private`
- branch: `openofc-m4v-continuation-transport`
- commit: `c21c3c4f1017c83df07eb22230318a8131bf40d1`
- tree: `73523862dac5b704d6f9878edefaa36212f20bc9`

No later source revision may silently enter this migration. Later changes must be recorded as separate deltas.

The exact frozen tree contains architecture through M5G. The fact that the frozen HEAD subject says M5C must not be used to truncate the migration set.

## G1 — inventory — PASS

Generated artifacts:

- `docs/migration/openofc_solver_inventory_c21c3c4.json`
- `docs/migration/OPENOFC_SOLVER_INVENTORY_C21C3C4.md`
- generator: `tools/migration/build_openofc_solver_inventory.py`
- workflow: `.github/workflows/openofc-solver-inventory.yml`
- workflow run `33059295351`: PASS
- materialized inventory commit: `92d43f141c1a55f65c801749503619105479c70c`

Frozen inventory result:

- 152 solver-subtree files;
- 69 current-root transitive dependency-closure files;
- 119 files classified `migrate` after current M4/M5 contracts and tests of migrated dependencies are included;
- 33 classified `historical`;
- 38 related M4/M5 workflows recorded;
- source-files payload SHA-256: `89a546aef6f367226cbaf9c6a54d886488519d88b0f1c7d07415db13df382e84`.

The machine-readable inventory records source path, Git blob SHA, file SHA-256, size, role, local imports, migration disposition and reason.

## G2 — destination layout

For the **pure migration gate**, preserve the source relative layout exactly:

`tools/openofc_solver/...` → `tools/openofc_solver/...`

This is deliberate. The staging source uses flat local imports and changing namespaces during migration would mix semantic/refactor risk with ownership transfer.

After pure migration + equivalence PASS, a later dedicated refactor may move code into a cleaner package namespace with its own tests and provenance.

OpenHoldem-specific runtime integration remains in `pmartins87/myoh_private`; the migrated set is the mathematical/strategic subtree selected by the G1 inventory.

## G3 — provenance-preserving pure copy

For every inventory entry marked `migrate`, create a target file with identical bytes at the same relative `tools/openofc_solver/...` path.

Generate a machine-readable provenance map with:

`source repository + source commit + source path + source blob SHA + source SHA256 -> target path + target SHA256`

Pure-copy acceptance criterion:

- every migrated target SHA-256 equals its source SHA-256 exactly;
- no semantic transformation is allowed;
- missing or extra files fail the gate;
- historical files are not silently copied.

Associated M4/M5 CI should be recreated in DeepOFC only where required to validate the migrated strategic tree; workflow provenance from G1 remains available for audit.

## G4 — equivalence gate

Before transferring authority, compare frozen old and migrated new implementations on deterministic golden cases covering at least:

- continuation-state serialization and fingerprints;
- kernel classification;
- continuation-aware payoff/evaluation primitives;
- M5A fixed-policy adapters;
- M5B current-V probe behavior under frozen seeds and budgets where practical;
- M5C evidence canonicalization and fail-closed certificate behavior;
- M5D exact-V route/certification behavior;
- M5E Fantasy certification bridge behavior;
- M5F Fantasy evidence canonicalization/metrics;
- M5G 50-state registry identity/completeness fail-closed behavior.

Exact deterministic paths must match exactly. Any statistical path must use a predeclared common-seed comparison protocol.

A first mechanical equivalence layer is identical source/target SHA-256 for every pure-copied file. Behavioral equivalence remains a separate required layer.

## G5 — independent CI

DeepOFC must be able to run the migrated strategic tests without depending on an OpenHoldem checkout.

At minimum:

1. execute the migrated unit/contract tests selected by the G1 inventory;
2. execute deterministic migration golden/equivalence checks;
3. fail closed on any missing dependency, source-hash divergence or route/certificate semantic difference.

Cross-repository checks may remain as additional evidence, but passing only in `myoh_private` is insufficient after authority transfer.

## G6 — authority transfer

Only after inventory, provenance, pure-copy hash equality, behavioral equivalence and independent CI pass:

1. update `docs/VERSION_MANIFEST.md` so M4/M5 strategic authority points to DeepOFC;
2. update `docs/CURRENT_STATE.md` and `docs/HANDOFF.md`;
3. freeze `myoh_private@c21c3c4...` as historical strategic provenance;
4. continue new strategic development in DeepOFC;
5. let runtime consume explicit versioned/exported policy artifacts instead of becoming the only owner of strategic source.

## Strategic work after/beside migration

Migration does not create strategic evidence. The real strategy gate remains:

1. independent held-out Normal×Normal evidence;
2. independent held-out Normal×Fantasy evidence;
3. Fantasy×Fantasy support-gap + deviation + held-out model/action-value evidence;
4. separately justified thresholds;
5. 50/50 state-local real-certified exact-V routes;
6. M5G real-ready registry;
7. first REAL dynamic M4Z Bellman trace.

## Non-goals

The migration must not simultaneously:

- redesign M5C–M5G;
- tune strategic thresholds;
- change game/Joker semantics;
- improve exploitability;
- perform broad solver refactors;
- rename imports/namespaces for style.

Those changes belong in later, separately validated commits.

## Failure rule

If hash or behavioral equivalence fails, the frozen staging source remains authoritative for the affected component until the divergence is explained and the migration gate passes.

## Completion record

The final migration result must record:

- frozen source commit/tree;
- inventory hash;
- provenance-map hash;
- target commit;
- validation/CI runs;
- pure-copy SHA equality result;
- behavioral equivalence results;
- any later approved transformations;
- final authority decision.
