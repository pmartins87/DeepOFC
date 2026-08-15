from pathlib import Path

path = Path('docs/ROADMAP.md')
text = path.read_text(encoding='utf-8')

old_status = "| R5 Baseline decision engine | 🟡 **Advanced / active** | exact final normal-round kernel; Fantasy-14 certified against 1,009,008-action brute force; real Fantasy-15 dual-Joker exact solve; native C++ exact 14/15/17 kernel with Python rescore and Windows/MSVC gates | early-round continuation solving, hidden/incomplete-opponent Fantasy expectation, self-consistent Fantasy continuation values, broader exact/property validation |"
new_status = "| R5 Baseline decision engine | 🟡 **Advanced / active** | exact final normal-round kernel; exact one-street-back expectimax reference; MC baseline calibrated against exact chance tree; Fantasy-14 brute-certified; real Fantasy-15 dual-Joker exact solve; native C++ exact 14/15/17 kernel | general early-round strategic continuation, hidden/incomplete-opponent Fantasy expectation, self-consistent Fantasy continuation values, broader exact/property validation |"
if text.count(old_status) != 1:
    raise SystemExit('unexpected R5 status line')
text = text.replace(old_status, new_status)

anchor = "- [x] measured native Windows/MSVC times on the frozen CI cases: roughly **0.026 s / 1.742 s / 5.129 s** for 14/15/17.\n"
addition = anchor + "- [x] exact **one-street-back last-chance expectimax** added for normal `round_index=3` subgames where opponents are already complete: every `C(pool,3)` next Hero draw is enumerated and its final street solved exactly;\n- [x] finite-population Monte Carlo baseline added with deterministic seeds, common random numbers across candidate actions, sampling without replacement and reported standard error/diagnostic 95% interval;\n- [x] Monte Carlo is regression-gated to become **bit-for-value equal to exact expectimax** when all chance branches are sampled;\n- [x] 56-branch convergence benchmark freezes exact EV **-8.714285714286** and exact collapse at 56/56 sampled branches;\n- [x] 20-seed calibration on that subgame identified an exact-best action in **20/20 seeds** at 8, 16 and 32 samples; mean RMSE fell from about **1.164 → 0.953 → 0.583**, while empirical 95% interval coverage was about **89.5% / 94.5% / 94.5%**. These are fixture-specific calibration results, not a global sample prescription.\n"
if text.count(anchor) != 1:
    raise SystemExit('unexpected R5 native timing anchor')
text = text.replace(anchor, addition)

old_todo = "- [ ] Monte Carlo/expectimax reference continuation solver for normal rounds 1–4;"
new_todo = "- [ ] extend continuation solving beyond the certified one-street-back last-chance subgame to general normal rounds 1–4 with opponent future actions and hidden information;"
if text.count(old_todo) != 1:
    raise SystemExit('unexpected R5 continuation TODO')
text = text.replace(old_todo, new_todo)

path.write_text(text, encoding='utf-8')
print('ROADMAP R5 continuation progress synchronized')
