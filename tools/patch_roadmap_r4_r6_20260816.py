from pathlib import Path

path = Path("docs/ROADMAP.md")
text = path.read_text(encoding="utf-8")

replacements = {
    "- [ ] full sequential 2-player hidden-state engine through all five normal rounds;": "- [x] full sequential 2-player hidden-state engine through all five normal rounds;",
    "- [ ] explicit observation projection so private incoming/discards never leak to other players;": "- [x] explicit HU observation projection so private incoming/discards never leak to the other player, with exact own-action perfect recall and public placement-only history;",
    "- [ ] complete-hand deterministic replay from seed and logged actions;": "- [x] complete normal-HU deterministic replay from seed and logged canonical action keys;",
    "- [ ] construct a deeper HU subgame with **at least two decisions by the same player**, preserving perfect recall and private-discard information;": "- [x] construct deeper HU subgames with **at least two decisions by the same player**, preserving perfect recall and strategically ambiguous private-discard information;",
    "- [ ] replace the one-action-specialized exact best response with a deeper-game independently validated BR/reference evaluator;": "- [x] replace the one-action-specialized exact best response with a deeper-game independently validated BR/reference evaluator, including asymmetric pure-response replay cross-checks;",
    "- [ ] benchmark outcome-sampling MCCFR only against that validated reference rather than by training loss;": "- [x] benchmark outcome-sampling MCCFR only against that validated reference rather than by training loss; exact-unbiased estimator passed but outcome sampling was empirically rejected in this regime;",
    "- [ ] benchmark continual re-solving from the live public state;": "- [x] benchmark public-state continual re-solving and stitch solved continuations back into the complete strategy before exact full-game best-response evaluation;",
    "- [ ] test where full-tree DCFR becomes computationally dominated by sampled/re-solving approaches as the chance/action tree grows;": "- [x] measure the DCFR/external-sampling crossover on 373,248-terminal hidden-discard and 41,472-terminal physical-Joker games, separating training and exact-evaluation cost;",
}
for old, new in replacements.items():
    if old not in text:
        raise SystemExit(f"roadmap anchor not found: {old}")
    text = text.replace(old, new, 1)

r4_anchor = "- [ ] large fuzz/property campaigns over physical uniqueness, row capacities, actor order and terminal zero-sum invariants;"
if r4_anchor not in text:
    raise SystemExit("R4 fuzz anchor not found")
text = text.replace(
    r4_anchor,
    "- [ ] large fuzz/property campaigns over physical uniqueness, row capacities, actor order and terminal zero-sum invariants; current HU structural gate already covers 80 complete seeded hands across both actor orders, but this is not yet the final large campaign;",
    1,
)

r6_anchor = "Next benchmark program:\n"
if r6_anchor not in text:
    raise SystemExit("R6 next-program anchor not found")
update = """Current deeper-HU evidence (2026-08-16):\n\n- [x] 373,248-terminal two-decision benchmark certified with exact structural value 0 and deep exact best response;\n- [x] stronger overlapping-support fixture certified with **882** public states compatible with multiple hidden-discard pairs and up to **4** distinct discard pairs behind one public state;\n- [x] 5-seed external-sampling current-profile calibration at 20k iterations reaches mean exploitability about **0.0007590**, maximum about **0.0019046**, with two seeds at exact zero and all five seeds best at the 20k checkpoint;\n- [x] standard and linear own-reach-weighted CFR averages independently cross-checked; at the measured finite budget the current profile remains materially stronger;\n- [x] lazy sampled-DCFR mechanism independently checked but strategically rejected versus ordinary external sampling;\n- [x] physical-Joker two-decision benchmark certified with persistent JK1/JK2, **41,472** terminals and **162** public states ambiguous between Joker and non-Joker discards;\n- [x] physical-Joker budget curves show no universal solver winner: DCFR is excellent at moderate budget on small trees, while external sampling scales and reached exact zero at 20k;\n- [x] canonical full five-round **HU normal-play sequential engine** added in R4 with authoritative hidden state, player observation projection, perfect recall and deterministic replay;\n- [ ] resolve zero-blueprint-reach/off-tree public beliefs with a safety mechanism validated by exact full-game best response; the 1% trembled-belief experiment remains pending;\n- [ ] move the next R6 tribunal earlier in the hand, using the canonical sequential HU engine and at least **three decisions per player** rather than another hand-built last-two-street fixture.\n\nCanonical evidence document: `docs/HU_TWO_ROUND_R6_BENCHMARK_2026-08-16.md`.\n\n"""
text = text.replace(r6_anchor, update + r6_anchor, 1)

path.write_text(text, encoding="utf-8")
print("ROADMAP R4/R6 2026-08-16 PATCH: APPLIED")
