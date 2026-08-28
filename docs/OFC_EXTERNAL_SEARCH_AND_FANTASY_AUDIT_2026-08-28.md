# OFC external search and Fantasy audit — 2026-08-28

Status: **component audit / research authority only**  
Frozen strategic baseline: `DeepOFC@c3430819d6cb22c8ad823791a35374d56a88a32a`  
Strategic route certificates remain **REAL = 0/50**.

## 1. Late exact/bounded search — `Saholy99/ofcp-engine`

Pinned source:

- `Saholy99/ofcp-engine@b8e5e2e7c4db5f096bcac7c83b812c9a8d3f542d`;
- `src/ofc_solver/late_search.py`.

### What it does well

The implementation has a clean operational hierarchy:

1. attempt bounded exact search;
2. if the exact budget/depth is exceeded in auto mode, try beam search;
3. optionally narrow the beam;
4. fall back to rollout when the searched tree is unsupported or over budget;
5. expose nodes, depth, terminal evaluations and fallback reason.

That dispatch/failure-reporting pattern is good engineering and should influence runtime search orchestration.

### Authority boundary

Its recursive `_search_value` receives one fully materialized `GameState` and expands legal actions from that state. When that state was reconstructed by sampling hidden cards, the recursion is exact **inside the sampled determinization**. It is not automatically an exact imperfect-information HU policy because the acting player does not know the sampled opponent packet/discards.

DeepOFC already has two different authorities that must stay separate:

- exact fully observed terminal/teacher kernels, where all variables required by the oracle are genuinely known;
- strategic infoset policies, whose action/value cannot depend on hidden opponent information.

The experiment `EXT-LATE-03A-AUTHORITY-FIREWALL` therefore tests the distinction explicitly: the same legal P0 information state is paired with multiple hidden opponent R4 packets. A perfect-information R4 minimax computes hidden-world-dependent root values even though the P0 information-state key is unchanged. Coincidentally equal argmax actions in a fixture do not repair the authority violation; the state-conditioned Q-values themselves are functions of unavailable information.

### Decision

| use | classification |
|---|---|
| fully observed final/terminal slice | **EQUIVALENT / valid exact reference** |
| bounded search for runtime proposal/pruning | **COMPLEMENTARY** |
| determinize then exact/beam search at hidden-information node | **SCREENING_ONLY** |
| label determinized value as exact infoset EV | **REJECT** |
| replace DeepOFC strategic solver with sampled-state minimax | **REJECT** |

No late-search code import is currently justified. The useful part is the dispatch/telemetry pattern, which can be reimplemented around target-authority kernels if later A/B evidence shows runtime benefit.

---

## 2. Fantasy recursive solver — `ainaosyusi/ofc-pineapple-ai`

Pinned source:

- `ainaosyusi/ofc-pineapple-ai@20fcbdebe0cdce3ac06e5ede639b8f78c177ceaa`;
- `src/cpp/solver.hpp`.

### External algorithm

The C++ `FantasySolver` recursively assigns each of 14–17 cards to Bottom, Middle, Top, or Discard. It prunes by:

- row capacities;
- whether enough remaining cards exist to fill all rows;
- Bottom/Middle ordering once Middle completes;
- Middle/Top ordering once Top completes.

The source comment states a theoretical maximum of `171M` states and says pruning is key. However, the score-bound pruning section is still a TODO in the pinned revision; the implementation does **not** contain a proved current-score-plus-upper-bound cutoff.

### External objective mismatch

At a complete assignment the external score is:

`bottom royalty + middle royalty + top royalty + 15 if re-Fantasy`

when already in Fantasy. That objective differs materially from the DeepOFC target. It omits the exact opponent board payoff and substitutes a fixed `STAY_BONUS=15` for the continuation state value.

Therefore even a very fast external search can choose a strategically wrong board for our game. Search speed cannot compensate for optimizing the wrong objective.

### DeepOFC V1

`deepofc/fantasy_solver.py::evaluate_fantasy_exact_subsets` is an exact fully observed 14–17-card semantic reference. It:

- precomputes exact 3-card and 5-card subset ranks;
- uses the frozen board-aware Joker semantics;
- enumerates legal disjoint Bottom/Middle/Top physical subsets;
- computes exact pairwise HU points against complete opponent board(s);
- preserves exact re-Fantasy qualification;
- adds a supplied continuation value only when re-Fantasy qualifies;
- uses deterministic canonical tie-breaking.

Historical real Fantasy15 dual-Joker run `31900847707` established the exact target optimum of **28 points** for frame53, but V1 required **59.073160 s** and scored 5,160,130 valid boards after 6,174,560 Top partitions.

### DeepOFC V2

`deepofc/fantasy_solver_v2.py::evaluate_fantasy_exact_subsets_v2` already implements a target-specific exact optimization. For non-negative continuation value it proves a monotonicity property: once Bottom and Middle are fixed, choosing a stronger legal Top cannot reduce current pairwise row payoff, Top royalty, scoop state, or re-Fantasy qualification. V2 therefore builds an exact achievable-Top frontier for each leftover-card mask and queries only the strongest Top not exceeding Middle.

This removes the repeated `C(N-10, 3)` physical Top loop while preserving exact target value. Negative continuation is fail-closed to V1 rather than silently applying the proof outside its domain.

### Architectural comparison

| property | DeepOFC V2 | `ainaosyusi` FantasySolver |
|---|---|---|
| 14–17 cards | yes | yes |
| 2 Jokers | target exact semantics | external wildcard semantics; parity not universal |
| opponent payoff | exact pairwise target scoring | absent from objective |
| continuation | supplied strategic continuation value | fixed `STAY_BONUS=15` |
| foul/order pruning | exact | present |
| subset/rank caching | yes | incremental row values |
| Top repeated-search reduction | exact cached frontier | recursive assignment |
| proved score upper-bound pruning | Top monotonic frontier proof | source TODO, not implemented |
| deterministic canonical tie break | yes | implementation-specific first best |
| strategic authority for target | exact terminal kernel | **incompatible objective** |

### Decision

The external Fantasy solver does **not** justify an architecture migration. Its C++ implementation may still motivate a future performance-only shadow kernel, but such a kernel must reproduce DeepOFC’s evaluator/Joker/scoring/continuation semantics byte-for-byte or value-for-value on a frozen corpus.

Before any C++ rewrite, `EXT-FANTASY-04A-INTERNAL-BASELINE` measures the current V2 implementation on the real 15-card dual-Joker frame and synthetic 17-card dual-Joker stress case. A rewrite is not authorized merely because C++ is expected to be faster.

Promotion criteria for a future C++ Fantasy shadow kernel:

1. zero decision-value mismatch on exact V1/V2 corpus;
2. zero optimal-action-set loss where exact ties are known;
3. same Joker/foul/royalty/refantasy semantics;
4. objective `current target payoff + V[next state]`, never fixed stay bonus;
5. deterministic replay under frozen input;
6. substantial matched-machine speed or memory gain;
7. no strategic-certification claim beyond the terminal kernel actually validated.

---

## 3. Consequence for the project roadmap

External research has so far produced **guardrails and engineering candidates**, not a replacement solver:

- evaluator: keep DeepOFC; external regression vectors strengthened testing and exposed an incompatible Joker flush comparison rule;
- hidden-world sampler: adopt only as uniform physical-consistency shadow infrastructure;
- late search: retain exact terminal teachers; determinized search remains screening/proposal authority;
- Fantasy: keep DeepOFC V2 semantic architecture; obtain current benchmark before considering a C++ parity implementation;
- ISMCTS: remains the next genuinely novel search experiment after the sampler/search authority gates are green.

The strategic solver remains the authority and **REAL = 0/50** until the independent M5 certification gates say otherwise.
