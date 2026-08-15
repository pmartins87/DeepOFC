from pathlib import Path

path = Path("docs/ROADMAP.md")
text = path.read_text(encoding="utf-8")

status_replacements = {
    "| R4 Simulator | ⬜ Not started as certified gate | deterministic state primitives exist | complete 54-card deal/observation/settlement simulator and fuzzing |":
    "| R4 Simulator | 🟡 Advanced | deterministic 54-card deck, exact normal/Fantasy action application, physical-card invariants, HU/3-way raw zero-sum settlement, Fantasy qualification primitives | full sequential hidden-state/observation environment, whole-game replay, large fuzz/property campaigns |",
    "| R5 Baseline decision engine | ⬜ Not started | — | exact/search/Monte-Carlo baselines |":
    "| R5 Baseline decision engine | 🟡 **Advanced / active** | exact final normal-round kernel; Fantasy-14 certified against 1,009,008-action brute force; real Fantasy-15 dual-Joker exact solve; native C++ exact 14/15/17 kernel with Python rescore and Windows/MSVC gates | early-round continuation solving, hidden/incomplete-opponent Fantasy expectation, self-consistent Fantasy continuation values, broader exact/property validation |",
    "| R6 Solver study | ⬜ Not started | — | architecture benchmark/selection |":
    "| R6 Solver study | 🟡 Active | architecture v1 frozen; exact terminal kernels and native runtime path establish reference values; HU/3-way game-theory distinction frozen | build tractable HU extensive-form subgames and benchmark MCCFR/CFR+/DCFR/re-solving/hybrid candidates by exploitability and cost |",
}
for old, new in status_replacements.items():
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"expected exactly one roadmap status line, found {count}: {old}")
    text = text.replace(old, new)

start = text.index("## R4 — Environment / simulator")
end = text.index("## R7 — Training pipeline")
new_block = r'''## R4 — Environment / simulator

Implemented and tested:

- [x] canonical physical **54-card** deck with persistent JK1/JK2;
- [x] deterministic seed shuffle/draw primitives;
- [x] remaining-card calculation from known physical identity rather than Joker nominal substitutions;
- [x] exact application of first-round five-card placement;
- [x] exact later-round place-two/discard-one application;
- [x] exact one-shot Fantasy 13-card board + 1–4 unused-card application;
- [x] duplicate physical cards across players are rejected;
- [x] raw HU pairwise settlement;
- [x] raw 3-player settlement as sum of pairwise transfers, with zero-sum invariant;
- [x] normal Fantasy entry predicates `QQ→14 / KK→15 / AA→16 / Top trips→17` for valid completed boards;
- [x] re-Fantasy qualification predicate for Top trips or Bottom quads+ under board-aware Joker resolution.

Still required before R4 PASS:

- [ ] full sequential 2-player hidden-state engine through all five normal rounds;
- [ ] full sequential 3-player hidden-state engine;
- [ ] explicit observation projection so private incoming/discards never leak to other players;
- [ ] Fantasy/re-Fantasy transitions for every still-unfrozen card-count path;
- [ ] complete-hand deterministic replay from seed and logged actions;
- [ ] large fuzz/property campaigns over physical uniqueness, row capacities, actor order and terminal zero-sum invariants;
- [ ] integrate capped cash settlement only after R1 freezes its exact client semantics.

**Gate:** complete games replay deterministically from seed/actions, information visibility is correct, and large fuzz/property campaigns preserve every state/scoring invariant.

## R5 — Baseline decision engine

R5 now has exact reference kernels rather than heuristic-only baselines.

Implemented/proven:

- [x] exact fifth/final normal-round solver over every legal `place two / discard one` action;
- [x] Fantasy continuation exposed explicitly rather than hidden in an arbitrary bonus;
- [x] exact Python subset/bitmask Fantasy solver for fully observed terminal states;
- [x] **Fantasy-14 independently certified** against all **1,009,008** raw canonical actions: both methods return exact best value **60**;
- [x] Fantasy-14 optimized Python search measured about **21.93x** faster than the brute-force reference on the frozen CI fixture;
- [x] supplied real **15-card Fantasy with JK1+JK2** solved exactly against the completed visible opponent board;
- [x] real frame53 observed arrangement scores **8** raw current-hand points while the exact optimum scores **28**; both qualify for re-Fantasy, so no infinite-horizon +20 claim is made yet;
- [x] exact Python V2 collapses repeated Top enumeration while preserving optimum value;
- [x] synthetic 17-card dual-Joker V2 stress reaches the same canonical score but exposed Python runtime as too slow for production;
- [x] standalone **C++14 native exact Fantasy kernel** added using the same ordinary-hand/Joker/board-validity semantics;
- [x] native Linux gate reproduces certified values **14=60 / real15=28 / stress17=28**;
- [x] every native-selected board is independently rescored by the canonical Python evaluator and agrees exactly;
- [x] native kernel compiles/runs under **MSVC / Windows Server 2022**, the relevant toolchain family for future OpenHoldem integration;
- [x] measured native Linux times on the frozen CI cases: roughly **0.018 s / 0.759 s / 3.324 s** for 14/15/17;
- [x] measured native Windows/MSVC times on the frozen CI cases: roughly **0.026 s / 1.742 s / 5.129 s** for 14/15/17.

These timings are fixture/runner evidence, not universal latency guarantees. The important result is that exact Fantasy 14–17 is already computationally plausible without replacing the combinatorial solution with a learned guess.

Still required:

- [ ] support expected utility when an opponent board is hidden/incomplete rather than pretending it is known;
- [ ] solve self-consistent continuation values for Fantasy/re-Fantasy paths;
- [ ] Monte Carlo/expectimax reference continuation solver for normal rounds 1–4;
- [ ] transposition/state hashing and mathematically valid suit/rank symmetries for stochastic search;
- [ ] broader randomized cross-language/property gates, especially Joker-heavy cases;
- [ ] package the native kernel as a reusable library/API only after its standalone gates remain stable.

**Gate:** terminal kernels are independently certified, early-round EV estimates converge reproducibly, and every approximation is measured against exact/reference subproblems.

## R6 — Solver architecture study

Architecture v1 is frozen in `docs/SOLVER_ARCHITECTURE_V1.md`. Current conclusions are evidence-driven rather than selected by analogy with Hold'em:

- HU raw OFC is a two-player zero-sum extensive-form imperfect-information game before KKPoker economics;
- 3-player raw settlement also sums to zero globally, but it is multiplayer zero-sum and does not inherit two-player CFR guarantees automatically;
- exact rule/scoring/action and terminal Fantasy kernels remain authoritative references regardless of any learned/search policy;
- Fantasy terminal placement is well suited to exact combinatorial search and currently does **not** require ML merely for latency;
- normal rounds 1–4 require continuation values over future chance and strategic opponent actions, so a greedy board optimizer is insufficient.

Next benchmark program:

- [ ] construct small HU extensive-form subgames whose exact/best-response value can be computed;
- [ ] benchmark external-sampling MCCFR;
- [ ] benchmark outcome-sampling MCCFR;
- [ ] benchmark CFR+/DCFR on tractable abstractions/subgames;
- [ ] benchmark continual re-solving from the live public state;
- [ ] benchmark hybrid search + learned value/policy only after exact/search references exist;
- [ ] measure exploitability/best response, convergence rate, memory, CPU cost and runtime latency rather than choosing by training loss alone;
- [ ] treat 3-player separately with multiplayer self-play/equilibrium-approximation validation.

**Gate:** documented benchmark on representative exact subgames explains why the selected architecture is the strongest practical route toward the target near-perfect player.

'''
text = text[:start] + new_block + text[end:]
path.write_text(text, encoding="utf-8")
print("ROADMAP R4-R6 synchronized")
