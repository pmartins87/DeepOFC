# DeepOFC canonical current state

Date: 2026-08-27
Status: active development; not production-ready
Canonical status schema: `deepofc-current-state-v1`

This document is the single entry point for the current project state. Historical milestone documents remain evidence, but when their status wording conflicts with this file, this file wins until the conflict is deliberately reconciled.

## Executive state

DeepOFC has two active engineering tracks that must converge before production:

1. **Strategy / solver** — the current strategic milestone is **M5C**. The M4/M5 continuation/Bellman work is presently staged in `pmartins87/myoh_private`, branch `openofc-m4v-continuation-transport`, head `c21c3c4f1017c83df07eb22230318a8131bf40d1`, pending controlled migration back into this authoritative model/solver repository.
2. **Runtime / OpenHoldem** — recognition, reconstruction, transaction safety, drag/Confirm execution and field recovery remain a separately gated runtime problem. Existing v5.x field labels must not be treated as canonical project versions unless they are bound to source commit, policy, tablemap and build provenance.

The repository-governance drift discovered on 2026-08-27 did **not** imply lost work. It meant the latest solver work was persisted in the OpenHoldem repository instead of this repository. The immediate consolidation task is therefore provenance-preserving migration, not reimplementation.

## Repository authority

The intended authority split is restored as project policy:

- `pmartins87/DeepOFC` — canonical game model, scoring, simulator, solver, strategy research, training/exploitation design, evidence contracts, project roadmap and handoff documentation.
- `pmartins87/myoh_private` — OpenHoldem runtime integration, scraper/recognizer, UI transaction layer, runtime builds and runtime-specific field evidence.

Temporary exception: the M4/M5 strategic solver staging tree currently lives under `pmartins87/myoh_private/tools/openofc_solver`. It remains authoritative **for those staged files only** until the migration gate in `docs/SOLVER_MIGRATION_PLAN.md` is complete.

## Strategic milestone: M5C

The strategic lineage has advanced beyond the 2026-08-16 R6 architecture tribunal.

Current staging head:

- repository: `pmartins87/myoh_private`
- branch: `openofc-m4v-continuation-transport`
- head: `c21c3c4f1017c83df07eb22230318a8131bf40d1`
- head message: `OpenOFC M5C: add staging certification gate`
- M5B anchor: `008307c972582df978a7ee7db6717bf8cc1fa1db` — train-at-current-V normal kernel probes
- M5C workflow run: `33044932517` — passed on the staging head

### What the M5C PASS means

It means the **fail-closed certification mechanism** is implemented and its dedicated CI gate passes.

It does **not** mean the current policies are strategically certified, solved, production-ready or safe to promote into a real Bellman surface.

M5C requires state-local independent evidence. A complete real Bellman surface currently requires 50 distinct ready certificates:

- 2 Normal × Normal routes;
- 16 Normal × Fantasy routes;
- 32 Fantasy × Fantasy routes.

Required strategic evidence includes independent held-out seeds and samples, bounded value standard error and unilateral-deviation gain. Fantasy × Fantasy additionally requires the exact-teacher support-gap and held-out model/action-value error criteria defined by the M5C contract.

The next strategic gate is therefore **evidence generation and route-by-route certification**, followed only then by the first REAL 50-state M4Z Bellman trace.

## Solver quality state

The earlier R6 architecture tribunal remains valid background evidence: under the representative equal-terminal-work benchmark, External Sampling MCCFR was the strongest practical deep/global blueprint route among the tested implementations, while DCFR remained useful for tractable exact/conditioned subgames.

That result selected an architecture direction; it did not solve the full Joker Ultimate game.

The current M4/M5 work has moved the project from algorithm selection toward a continuation-aware Bellman framework with explicit strategic promotion firewalls. This is substantial progress, but production exploitability for the complete target game remains uncertified.

## Runtime state

The latest consolidated DeepOFC runtime-continuity checkpoint in this repository is the v5.4 continuity work on branch `agent/runtime-continuity-v54`, head `f4fcccc5453b5156ab6bf4b195cf3759c1676955`.

That checkpoint established the intended semantics:

- a bad/ambiguous scrape may suppress an unsafe click, but must not permanently suppress future scrapes or valid decisions;
- stale process lineage must not override a valid current screen;
- reacquisition must discard stale plans;
- mid-hand bootstrap and Fantasy 14–17 bootstrap need explicit support;
- drag/Confirm idempotence must survive reacquisition;
- build logs must identify source, policy and tablemap provenance.

Subsequent runtime experiments exist in `pmartins87/myoh_private` on multiple `openofc-v54*` / `openofc-v543*` branches. They are preserved, but the field-build naming lineage is not yet consolidated enough to declare one later chat/build label the canonical project runtime version.

Accordingly, **no unbound field label such as a chat-only `v5.8.0` should be treated as a canonical source version until its source commit + policy + tablemap + build manifest are recorded.**

## Global roadmap interpretation

The R0–R13 roadmap remains the production readiness framework. Its older status table is retained as historical structure, while current status is interpreted as follows:

| Area | Current interpretation |
|---|---|
| R0–R3 rules/scoring/actions | Advanced foundation; keep closing edge cases and independent validation |
| R4 simulator | Advanced foundation; full representative game scaling remains |
| R5/R6 decision + solver architecture | Advanced; architecture selected and continuation/Bellman work now staged through M5C |
| R7 training | Not productionized; must emerge from certified solver architecture and reproducible artifact protocol |
| R8 exploitation | Deferred until a stronger certified base policy exists |
| R9 recognition/state bridge | Runtime live-safety blocker |
| R10 autoplayer | Developed behind safety gates; production execution still depends on recognition/reconstruction authority |
| R11 shadow | Blocked until replay/runtime certification |
| R12 controlled live | Blocked until sustained shadow safety |
| R13 production | Blocked until strategy + runtime + training + operations are reproducible and certified |

## Current critical path

### Governance / continuity

1. Merge this consolidation checkpoint.
2. Inventory the M4/M5 staging tree and dependency closure.
3. Migrate the solver tree into DeepOFC with source-path/commit/hash provenance preserved.
4. Run cross-repository equivalence tests before changing authority.
5. Remove the temporary solver-staging exception only after equivalence passes.

### Strategy

1. Generate independent held-out M5C evidence for Normal × Normal.
2. Generate independent held-out M5C evidence for Normal × Fantasy.
3. Generate Fantasy × Fantasy M4X support-gap + M5B deviation + M4W model-error evidence.
4. Freeze thresholds from an independently justified protocol.
5. Certify all 50 routes state-by-state.
6. Enable the first REAL 50-state M4Z Bellman trace only after all required routes are ready.
7. Measure convergence/stability/exploitability and decide the next scaling/training gate from evidence.

### Runtime

1. Consolidate runtime build provenance into one machine-readable manifest.
2. Bind every field package to native source commit, policy/solver version and tablemap version.
3. Continue deterministic pixels → physical cards → raw observation → canonical state proof.
4. Certify transaction loop: drag → fresh scrape → exact verification; Confirm → committed-state verification.
5. Shadow mode before controlled live use.

## Hard project rules

- A code path existing is not a gate PASS.
- A CI PASS for a certification framework is not a strategic policy certificate.
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
