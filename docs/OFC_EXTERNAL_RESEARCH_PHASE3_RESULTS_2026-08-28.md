# OFC external research — Phase 3 results — 2026-08-28

Status: **research/shadow evidence only**  
Frozen strategic baseline: `DeepOFC@c3430819d6cb22c8ad823791a35374d56a88a32a`  
Strategic route certificates: **REAL = 0/50**.

## EXT-LATE-03A — late-search authority firewall

External reference:

- `Saholy99/ofcp-engine@b8e5e2e7c4db5f096bcac7c83b812c9a8d3f542d`;
- `src/ofc_solver/late_search.py`.

Internal gate:

- `tools/openofc_solver/test_external_late_search_authority_firewall.py`.

Final result after correcting the first test fixture:

- workflow run: `33140651141`;
- job: `98750532268`;
- result: **SUCCESS**;
- tests: **2 passed**;
- manifest SHA256: `17beea1e348f308b0e1e0bc098c78d2e0a94c8c76b99d4a11527bfc556c1ccc6`;
- artifact id: `9673799404`;
- artifact name: `openofc-external-late-search-03a`;
- artifact ZIP SHA256: `f64ef63339c75aced3c12a767915502c7cf18f8bfe9387f4795cb958756621ab`;
- promotion recommendation: `KEEP_BASELINE`.

The first draft attempted to prove that two hidden opponent packets always changed the perfect-information argmax in the chosen R4 fixture. They did not: the argmax happened to be stable across that fixture. The corrected authority test uses the stronger logical requirement that matters here: **the exact root action-value vector changes with the hidden opponent packet while the legal P0 information-state key remains identical**. Therefore a state-local determinized minimax value is a function of information unavailable to P0 and cannot be labelled an exact infoset value.

Decision:

- fully observed terminal exact search: valid exact reference;
- determinized hidden-world exact/beam search: screening/proposal only;
- no replacement of DeepOFC strategic infoset solver.

## EXT-FANTASY-04A — current exact Fantasy performance baseline

External reference:

- `ainaosyusi/ofc-pineapple-ai@20fcbdebe0cdce3ac06e5ede639b8f78c177ceaa`;
- `src/cpp/solver.hpp`.

Internal kernels:

- `deepofc/fantasy_solver.py` V1 exact semantic reference;
- `deepofc/fantasy_solver_v2.py` exact Top-frontier optimization.

Workflow result:

- workflow run: `33140651236`;
- job: `98750532715`;
- result: **SUCCESS**;
- manifest SHA256: `7e8a0b6856fe2c3be64f4c7890cc44247fda954ba3b79b1095257344502722a2`;
- artifact id: `9673823124`;
- artifact name: `openofc-external-fantasy-baseline-04a`;
- artifact ZIP SHA256: `66c5b8616b688a0998294f0ebddaa1a8eafce7fbc1d745ca9dc4b7f344470855`;
- rewrite authorized: **false**.

### Real 15-card dual-Joker frame53

Current V2:

- exact optimal points: **28**;
- elapsed: **18.094652 s** on the GitHub-hosted runner;
- Bottom/Middle pairs: `756,756`;
- Top rank queries: `617,456`;
- valid boards scored: `607,871`;
- PASS.

Historical V1 exact run `31900847707` on the same real frame:

- exact optimal points: **28**;
- elapsed: **59.073160 s**;
- Top partitions tested: `6,174,560`;
- valid boards scored: `5,160,130`.

The environments were different hosted-runner revisions, so the elapsed ratio is not a strict matched-machine speedup certificate. The structural work reduction is real and deterministic: V2 reduced the Top-stage search from millions of physical partitions to hundreds of thousands of exact frontier queries while retaining the same optimum.

### Synthetic 17-card dual-Joker stress

Current V2:

- exact optimal points: **28**;
- elapsed: **69.568653 s**;
- Bottom/Middle pairs: `4,900,896`;
- Top rank queries: `3,844,322`;
- valid boards scored: `3,831,102`;
- PASS.

### External Fantasy solver decision

The pinned external C++ solver is not a superior target architecture at this stage:

1. its final objective is own royalties plus a fixed `STAY_BONUS=15`, not exact opponent payoff plus strategic continuation `V[next]`;
2. its advertised score-bound pruning is a source TODO, not implemented proof-backed branch-and-bound;
3. its Joker evaluator cannot be assumed target-equivalent because EXT-EVAL-01A already found a concrete source-level mismatch;
4. DeepOFC V2 already contains an exact target-specific Top-frontier reduction.

A C++ rewrite remains potentially attractive **only as a performance implementation of our semantics**, not as a migration to the external algorithm. Any such shadow kernel must first equal V1/V2 values/actions on a frozen corpus and then show matched-machine performance gain.

## Research frontier after Phase 3

The first four external-research gates now give a coherent picture:

- evaluator/Joker: keep baseline; external regressions useful, external rule not wholesale compatible;
- hidden-world sampling: shared physical-world shadow sampler accepted for screening only;
- late search: exact only when the needed state is genuinely observed; determinizations are screening only;
- Fantasy: keep target exact V2 architecture; optimize implementation only after parity.

The next genuinely new candidate is a **target-rule HU information-set MCTS/ISMCTS experiment**, validated first on a tractable final-round hidden-packet game with an independently enumerable exact expectation. No RL/self-play scale-up is justified yet.
