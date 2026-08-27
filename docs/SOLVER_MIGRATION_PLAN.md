# DeepOFC solver migration plan

Date: 2026-08-27
Status: active

## Goal

Move the recent M4/M5 strategic development from its temporary staging location in `pmartins87/myoh_private/tools/openofc_solver` into the intended authoritative solver repository `pmartins87/DeepOFC`, while preserving provenance and proving behavioral equivalence.

## Frozen source

- repository: `pmartins87/myoh_private`
- branch: `openofc-m4v-continuation-transport`
- commit: `c21c3c4f1017c83df07eb22230318a8131bf40d1`

No later source revision may silently enter this migration. Later changes must be recorded as separate deltas.

## Gates

### 1. Inventory

Create a machine-readable inventory of the frozen staging subtree with:

- source path;
- source blob/file hash;
- role: source, test, benchmark, contract, workflow, evidence, helper;
- project-local dependencies;
- destination classification.

Dependency closure matters more than filename prefixes. Files required by M4/M5 must be included even when their names do not begin with `m4` or `m5`.

### 2. Provenance map

For every migrated file record:

`source repository + source commit + source path + source hash -> target path + target hash`

If import paths require a mechanical edit, preserve both source and target hashes and document the transformation. Semantic changes are outside the pure migration step.

### 3. Destination layout

Keep mathematical solver code, Bellman logic, continuation models, strategic tests and strategic benchmark contracts in DeepOFC. Keep OpenHoldem-specific integration in the OpenHoldem repository.

Avoid cosmetic renames during migration when they would make provenance harder to audit.

### 4. Equivalence gate

Before transferring authority, compare frozen old and migrated new implementations on deterministic golden cases covering at least:

- continuation-state serialization and fingerprints;
- kernel classification;
- continuation-aware payoff/evaluation primitives;
- M5A fixed-policy adapters;
- M5B current-V probe behavior under frozen seeds and budgets where practical;
- M5C evidence canonicalization and fail-closed certificate behavior;
- route registry identity checks;
- Fantasy support/model metrics required by M5C.

Exact deterministic paths must match exactly. Any statistical path must use a predeclared common-seed comparison protocol.

### 5. Independent CI

DeepOFC must be able to run the migrated strategic tests without depending on an OpenHoldem checkout. Cross-repository checks may remain as additional evidence.

### 6. Authority transfer

Only after inventory, provenance, equivalence and CI pass:

1. update `docs/VERSION_MANIFEST.md` so M4/M5 strategic authority points to DeepOFC;
2. update `docs/CURRENT_STATE.md` and `docs/HANDOFF.md`;
3. freeze the old staging branch as historical provenance;
4. continue new strategic development in DeepOFC.

## Non-goals

The migration must not simultaneously redesign M5C, tune strategic thresholds, change game/Joker semantics or perform broad solver refactors. Those changes belong in later, separately validated commits.

## Failure rule

If equivalence fails, the frozen staging source remains authoritative for the affected component until the divergence is explained and the migration gate passes.

## Completion record

The final migration result must record:

- frozen source commit;
- inventory hash;
- provenance-map hash;
- target commit;
- validation/CI runs;
- equivalence results;
- approved mechanical transformations;
- final authority decision.
