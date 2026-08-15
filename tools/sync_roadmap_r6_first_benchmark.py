from pathlib import Path

path = Path("docs/ROADMAP.md")
text = path.read_text(encoding="utf-8")

old_status = "| R6 Solver study | 🟡 Active | architecture v1 frozen; exact terminal kernels and native runtime path establish reference values; HU/3-way game-theory distinction frozen | build tractable HU extensive-form subgames and benchmark MCCFR/CFR+/DCFR/re-solving/hybrid candidates by exploitability and cost |"
new_status = "| R6 Solver study | 🟡 **Advanced / active** | first exact HU imperfect-information OFC subgame; structural value=0; 40,320 terminal symmetry proof; exact BR/NashConv/exploitability; CFR+, DCFR and external-sampling MCCFR with 10-seed calibration | deeper multi-decision HU subgames; outcome-sampling/re-solving/scale benchmarks; then separate 3-player validation |"
if old_status not in text:
    raise SystemExit("R6 status row anchor not found")
text = text.replace(old_status, new_status, 1)

old_block = """Next benchmark program:

- [ ] construct small HU extensive-form subgames whose exact/best-response value can be computed;
- [ ] benchmark external-sampling MCCFR;
- [ ] benchmark outcome-sampling MCCFR;
- [ ] benchmark CFR+/DCFR on tractable abstractions/subgames;
- [ ] benchmark continual re-solving from the live public state;
- [ ] benchmark hybrid search + learned value/policy only after exact/search references exist;
- [ ] measure exploitability/best response, convergence rate, memory, CPU cost and runtime latency rather than choosing by training loss alone;
- [ ] treat 3-player separately with multiplayer self-play/equilibrium-approximation validation.

**Gate:** documented benchmark on representative exact subgames explains why the selected architecture is the strongest practical route toward the target near-perfect player.
"""
new_block = """First exact HU architecture benchmark now implemented/proven:

- [x] constructed a real final-round HU OFC subgame with private three-card hands, hidden first-player discard, public confirmed placements and **2,352 information sets**;
- [x] **2,240** second-player information sets merge multiple physically distinct hidden histories, so the benchmark is genuinely imperfect-information rather than a perfect-information placement toy;
- [x] exact player-swap + suit-mirror + actor-order automorphism freezes the benchmark game value at **0**, with **40,320 / 40,320** terminal payoff-symmetry branches checked exhaustively;
- [x] exact best response, NashConv and exploitability evaluator implemented for this one-decision-per-player benchmark;
- [x] uniform profile frozen at exact expected value **0** but exploitability **0.428571428571**;
- [x] full-tree CFR+ benchmark reaches exact exploitability **0.000013028071** at 256 iterations;
- [x] full-tree DCFR (`alpha=1.5, beta=0, gamma=2`) reaches exact exploitability **0.000000076188** at 256 iterations and dominates CFR+ on this tractable tree at essentially equal full-tree cost;
- [x] deterministic external-sampling MCCFR implemented and exact-BR evaluated; corrected single-seed 50k benchmark reaches exploitability **0.013472149428** in about **8.0 s training-only**;
- [x] MCCFR lazy average-strategy one-iteration alignment bug found during audit, corrected, and regression-gated so iteration 1 averages exactly the policy actually used;
- [x] corrected **10-seed** external-sampling calibration at 20k iterations gives mean exploitability **0.033331994488** and p95/max **0.034406383220**;
- [x] training time and exact-evaluation time are reported separately so best-response diagnostics are not miscounted as solver training cost;
- [x] benchmark and limitations frozen in `docs/HU_IMPERFECT_INFO_R6_BENCHMARK_2026-08-15.md`.

Current interpretation: full-tree DCFR is the strongest measured algorithm on this **small tractable tree**, while external sampling remains relevant because it visits only a sampled fraction of the game tree. This is not yet a production architecture decision.

Next benchmark program:

- [ ] construct a deeper HU subgame with **at least two decisions by the same player**, preserving perfect recall and private-discard information;
- [ ] replace the one-action-specialized exact best response with a deeper-game independently validated BR/reference evaluator;
- [ ] benchmark outcome-sampling MCCFR only against that validated reference rather than by training loss;
- [ ] benchmark continual re-solving from the live public state;
- [ ] test where full-tree DCFR becomes computationally dominated by sampled/re-solving approaches as the chance/action tree grows;
- [ ] benchmark hybrid search + learned value/policy only after exact/search references exist;
- [ ] measure exploitability/best response, convergence rate, memory, CPU cost and runtime latency rather than choosing by self-play value alone;
- [ ] treat 3-player separately with multiplayer self-play/equilibrium-approximation validation.

**Gate:** documented benchmarks on increasingly representative exact/reference subgames explain why the selected architecture is the strongest practical route toward the target near-perfect player.
"""
if old_block not in text:
    raise SystemExit("R6 benchmark block anchor not found")
text = text.replace(old_block, new_block, 1)
path.write_text(text, encoding="utf-8")
print("ROADMAP R6 FIRST BENCHMARK PATCH: APPLIED")
