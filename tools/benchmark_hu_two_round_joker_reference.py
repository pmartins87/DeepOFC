from __future__ import annotations

from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from deepofc.hu_two_round_br import exact_nash_conv
from deepofc.hu_two_round_joker import HUTwoRoundJokerSubgame
from deepofc.hu_two_round_resolve import build_round4_public_subgames


def main() -> None:
    started = time.perf_counter()
    game = HUTwoRoundJokerSubgame()
    build_seconds = time.perf_counter() - started

    terminals = game.terminal_count()
    if terminals <= 0:
        raise SystemExit("Joker benchmark produced no terminals")
    merged = game.count_merged_round4_infosets()
    uniform = game.uniform_profile()
    uniform_ev = game.expected_u0(uniform)
    if abs(uniform_ev) > 1e-12:
        raise SystemExit(f"Joker uniform symmetry value drift: {uniform_ev}")

    public = build_round4_public_subgames(game, uniform)
    ambiguous_discard_states = 0
    joker_discard_ambiguity_states = 0
    max_discard_pairs = 0
    for sub in public.values():
        pairs = set()
        has_joker_discard = False
        has_nonjoker_discard = False
        for history in sub.histories:
            d1 = history.first_round3_action.discard
            d2 = history.second_round3_action.discard
            assert d1 is not None and d2 is not None
            pairs.add((d1.code, d2.code))
            if d1.is_joker or d2.is_joker:
                has_joker_discard = True
            else:
                has_nonjoker_discard = True
        max_discard_pairs = max(max_discard_pairs, len(pairs))
        if len(pairs) > 1:
            ambiguous_discard_states += 1
        if len(pairs) > 1 and has_joker_discard and has_nonjoker_discard:
            joker_discard_ambiguity_states += 1
    if joker_discard_ambiguity_states <= 0:
        raise SystemExit(
            "Joker support failed to create public states ambiguous between Joker and non-Joker discards"
        )

    started = time.perf_counter()
    symmetry_checks = game.assert_terminal_swap_symmetry()
    symmetry_seconds = time.perf_counter() - started
    if symmetry_checks != terminals:
        raise SystemExit(
            f"Joker terminal symmetry coverage mismatch: {symmetry_checks} vs {terminals}"
        )

    started = time.perf_counter()
    conv, br0, br1 = exact_nash_conv(game, uniform)
    br_seconds = time.perf_counter() - started

    print(
        f"joker_reference chance_outcomes={len(game.outcomes)} infosets={len(game.info_actions)} "
        f"merged_round4_infosets={merged} terminals={terminals} "
        f"symmetry_checks={symmetry_checks} uniform_expected_u0={uniform_ev:.12f}"
    )
    print(
        f"public_states={len(public)} ambiguous_discard_states={ambiguous_discard_states} "
        f"joker_vs_nonjoker_discard_states={joker_discard_ambiguity_states} "
        f"max_discard_pairs={max_discard_pairs}"
    )
    print(
        f"uniform_br0={br0.value:.12f} uniform_br1={br1.value:.12f} "
        f"uniform_nash_conv={conv:.12f} exploitability={0.5 * conv:.12f}"
    )
    print(
        f"timing build_seconds={build_seconds:.6f} symmetry_seconds={symmetry_seconds:.6f} "
        f"br_seconds={br_seconds:.6f}"
    )
    print("HU TWO-ROUND PHYSICAL-JOKER REFERENCE: PASS")


if __name__ == "__main__":
    main()
