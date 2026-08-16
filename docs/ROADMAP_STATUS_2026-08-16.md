# DeepOFC roadmap status — 2026-08-16

This checkpoint records the actual project state after the R6 V2 architecture tribunal and the latest R9/R10 OpenHoldem work. It exists because `docs/ROADMAP.md` still contains some pre-tribunal/predating-R10 wording and must not be treated as the sole source for the current critical path until it is consolidated.

## Executive status

DeepOFC is **not blocked**. The project has two active parallel fronts:

1. **Strategy / solver:** the R6 architecture-selection gate is sufficiently closed to proceed with External Sampling MCCFR as the primary deep/global blueprint candidate. DCFR remains a strong tool for smaller/conditioned exact subgames. This does not certify the full Joker Ultimate game as solved.
2. **Runtime / OpenHoldem:** R9 recognition remains the live-safety blocker, while R10 transaction infrastructure is now substantially ahead of the older roadmap wording and continues behind the hard no-click guard.

R11 shadow, R12 controlled live, and R13 production remain blocked by the recognition/action certification chain.

## Gate snapshot

| Gate | Current status | Key reality now | Main remaining blocker |
|---|---|---|---|
| R0 Bootstrap | Operational | repositories, evidence manifests, normal/Fantasy fixtures | archival `.tm` copy only |
| R1 Rules/state | Advanced | 54-card JK1/JK2 physical deck, Joker duplication semantics, normal/Fantasy canonical state | remaining re-Fantasy/cap/rake/discard-observability edges |
| R2 Exact scoring | Advanced | standard + board-aware Joker scoring/foul/royalties | capped/multiway/both-foul/final trigger coverage |
| R3 Legal actions | Advanced | exact normal actions; exact lazy Fantasy 14–17 action semantics | practical search reduction + broader independent validation |
| R4 Simulator | Advanced | complete normal HU hidden-state engine, leak-free observations, deterministic replay | 3-player sequential engine, full Fantasy transitions, large fuzz campaign |
| R5 Baseline engine | Advanced | exact normal late-street kernels and native exact Fantasy references | earlier-round/general continuation and incomplete-opponent Fantasy values |
| R6 Solver study | **Architecture gate passed for current decision** | exact BR tribunal; deeper hidden-state benchmarks; V2 equal-terminal-work benchmark strongly favors External Sampling | scaling to representative full game; 3-player remains separate; production exploitability not yet certified |
| R7 Training | Not yet productionized | solver architecture now selected enough to design it | reproducible long-run pipeline/checkpoint/artifact protocol |
| R8 Exploitation | Deferred | concept preserved | only after a stronger base policy exists |
| R9 OH recognition | **Active critical blocker** | isolated OFC state, normal/Fantasy routing, JK1/JK2 persistence, Fantasy15 measured recognition layer | deterministic real pixels → physical cards → raw → canonical proof; remaining geometries/Joker/rank-8 evidence |
| R10 Autoplayer | **Active behind guard** | arbitrary drag primitive, fixed-plan multi-scrape orchestrator, normal Confirm semantic verifier, fail-closed logic | certified source rectangles/drop regions; real gesture replay; post-drag canonical verification; Fantasy completion |
| R11 Shadow | Blocked | — | R9/R10 replay certification |
| R12 Controlled live | Blocked | — | sustained shadow safety |
| R13 Production | Blocked | — | complete runtime + strategy + training + operations bundle |

## R6 architecture tribunal — current decision

The canonical V2 benchmark uses the sequential HU engine with genuine future private chance and physical JK1/JK2 identities.

Equal terminal-evaluation work:

- exact tree size: **839,808 leaves**;
- DCFR current profile: **1 full-tree pass = 839,808 training terminals**;
- External Sampling current profile: **2,592 iterations = 839,808 training terminals**.

Exact-BR exploitability after equal terminal work:

- DCFR: **1.8328332833**;
- External Sampling: **0.3106694643**.

Thus External Sampling had about **83.05% lower exploitability** under this work normalization; DCFR was about **5.90× more exploitable**. External Sampling was slower in wall-clock time in the current implementation, but much stronger per terminal evaluation.

Methodological caveat: equal leaf visits are a compute-work normalization, not identical learning opportunities. Therefore the supported conclusion is not that the algorithms are universally ordered; it is that **for the current representative V2 benchmark and implementations, External Sampling is the strongest practical deep/global blueprint route**. DCFR remains valuable where repeated exact full-tree passes are affordable.

The earlier repaired two-round blueprint result (~0.00877424 exploitability) remains a benchmark result, not a full-game production certificate.

## R9 current critical path

R9 still owns the live-safety gate. The next decisive proof must be end-to-end and deterministic:

`real replay BMP pixels -> recognized physical cards (including JK1/JK2) -> raw OFC observation -> canonical OFC state -> exact Python/C++ golden equality`

No ambiguous card may be guessed. Recognition must fail closed.

Immediate evidence gaps remain:

- actual serialized replay-derived rank templates and rejection provenance;
- more independent Joker visual occurrences/states;
- independent rank-8 evidence or an independently validated alternative recognizer path;
- normal first-round five-loose-card geometry;
- Fantasy 14/16/17 real geometry/recognition (15 must not be silently extrapolated);
- 3-player geometry.

## R10 progress beyond the older roadmap wording

R10 is no longer only a drag primitive plus planner scaffold.

The strategy action is now treated as a **fixed canonical turn plan**. The runtime orchestrator validates a fresh canonical scrape after each tentative placement and refuses to silently re-solve/change target when the observed strategic state drifts. Any mismatch latches the turn as blocked.

Normal Confirm now has a semantic transition verifier. It accepts only evidence compatible with a successful Confirm, including same-round handoff or direct next-round committed state, and rejects cases such as Hero still being the actor or target placements disappearing unexpectedly.

OpenHoldem `deepofc` build integration for the normal Confirm verifier passed its dedicated GitHub Actions gate before being persisted.

The hard R9 no-click guard remains intentional. R10 may be developed and regression-tested, but must not issue live clicks until R9 is deliberately certified.

## Current critical path to tables

1. **R9:** close the deterministic pixel-to-canonical replay proof for normal play and Fantasy15 first.
2. **R9:** close remaining 14/16/17 Fantasy and normal-first-round/3-player geometry gaps.
3. **R10:** certify physical source resolver + row drop regions against the same recognized state.
4. **R10:** replay/sandbox transaction loop: one drag -> fresh scrape -> exact verification -> next drag; Confirm -> committed-state verification.
5. **R11:** sustained shadow mode with no clicks and zero unsafe mismatches.
6. **R12:** lowest-stake controlled live with kill switch and complete logs.
7. **R13:** production bundle only after strategy/runtime/training/operations are reproducible.

In parallel, the strategy branch should scale External Sampling toward more representative early-round/full-game states and build R7 reproducibility without blocking R9/R10 integration.
