from __future__ import annotations

from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from deepofc.hu_two_round_br import exact_nash_conv
from deepofc.hu_two_round_hidden_discard import HUTwoRoundHiddenDiscardSubgame
from deepofc.hu_two_round_resolve import build_round4_public_subgames


def main() -> None:
    started = time.perf_counter()
    game = HUTwoRoundHiddenDiscardSubgame()
    build_seconds = time.perf_counter() - started

    terminals = game.terminal_count()
    if terminals != 373_248:
        raise SystemExit(f"unexpected hidden-discard terminal count: {terminals}")

    merged = game.count_merged_round4_infosets()
    uniform = game.uniform_profile()
    uniform_ev = game.expected_u0(uniform)
    if abs(uniform_ev) > 1e-12:
        raise SystemExit(f"hidden-discard uniform symmetry value drift: {uniform_ev}")

    public = build_round4_public_subgames(game, uniform)
    ambiguous_states = 0
    max_discard_pairs = 0
    hidden_histories = 0
    for sub in public.values():
        pairs = set()
        for history in sub.histories:
            d1 = history.first_round3_action.discard
            d2 = history.second_round3_action.discard
            assert d1 is not None and d2 is not None
            pairs.add((d1.code, d2.code))
            hidden_histories += 1
        max_discard_pairs = max(max_discard_pairs, len(pairs))
        if len(pairs) > 1:
            ambiguous_states += 1
    if ambiguous_states <= 0 or max_discard_pairs <= 1:
        raise SystemExit(
            "overlapping support failed to create strategically ambiguous hidden discards"
        )

    symmetry_started = time.perf_counter()
    symmetry_checks = game.assert_terminal_swap_symmetry()
    symmetry_seconds = time.perf_counter() - symmetry_started
    if symmetry_checks != terminals:
        raise SystemExit(
            f"hidden-discard symmetry coverage mismatch: {symmetry_checks} vs {terminals}"
        )

    br_started = time.perf_counter()
    nash_conv, br0, br1 = exact_nash_conv(game, uniform)
    br_seconds = time.perf_counter() - br_started

    print(
        f"hidden_discard_reference chance_outcomes={len(game.outcomes)} "
        f"infosets={len(game.info_actions)} merged_round4_infosets={merged} "
        f"terminals={terminals} symmetry_checks={symmetry_checks} "
        f"uniform_expected_u0={uniform_ev:.12f}"
    )
    print(
        f"public_states={len(public)} hidden_histories={hidden_histories} "
        f"ambiguous_discard_states={ambiguous_states} "
        f"max_discard_pairs={max_discard_pairs}"
    )
    print(
        f"uniform_br0={br0.value:.12f} uniform_br1={br1.value:.12f} "
        f"uniform_nash_conv={nash_conv:.12f} "
        f"uniform_exploitability={0.5 * nash_conv:.12f}"
    )
    print(
        f"timing build_seconds={build_seconds:.6f} "
        f"symmetry_seconds={symmetry_seconds:.6f} br_seconds={br_seconds:.6f}"
    )
    print("HU TWO-ROUND HIDDEN-DISCARD REFERENCE: PASS")


if __name__ == "__main__":
    main()
