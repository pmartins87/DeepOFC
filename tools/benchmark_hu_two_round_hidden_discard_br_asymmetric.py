from __future__ import annotations

from pathlib import Path
import random
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from deepofc.hu_two_round_br import exact_best_response, profile_with_pure_response
from deepofc.hu_two_round_hidden_discard import HUTwoRoundHiddenDiscardSubgame


def deterministic_asymmetric_profile(game):
    rng = random.Random(20260815)
    profile = {}
    for info, legal in game.info_actions.items():
        ordered = sorted(legal, key=lambda action: action.key())
        raw = {action: 0.01 + rng.random() ** 3 for action in ordered}
        total = sum(raw.values())
        profile[info] = {action: raw[action] / total for action in ordered}
    return profile


def main() -> None:
    game = HUTwoRoundHiddenDiscardSubgame()
    profile = deterministic_asymmetric_profile(game)

    started = time.perf_counter()
    profile_u0 = game.expected_u0(profile)
    profile_seconds = time.perf_counter() - started

    started = time.perf_counter()
    br0 = exact_best_response(game, profile, 0)
    br0_seconds = time.perf_counter() - started
    started = time.perf_counter()
    cross0 = game.expected_u0(profile_with_pure_response(game, profile, br0))
    cross0_seconds = time.perf_counter() - started

    started = time.perf_counter()
    br1 = exact_best_response(game, profile, 1)
    br1_seconds = time.perf_counter() - started
    started = time.perf_counter()
    cross1 = -game.expected_u0(profile_with_pure_response(game, profile, br1))
    cross1_seconds = time.perf_counter() - started

    if abs(br0.value - cross0) > 1e-10:
        raise SystemExit(f"hidden-discard asymmetric BR0 mismatch: {br0.value} vs {cross0}")
    if abs(br1.value - cross1) > 1e-10:
        raise SystemExit(f"hidden-discard asymmetric BR1 mismatch: {br1.value} vs {cross1}")
    if br0.value + br1.value < -1e-10:
        raise SystemExit("hidden-discard asymmetric NashConv unexpectedly negative")

    print(
        f"asymmetric_hidden_discard expected_u0={profile_u0:.12f} "
        f"br0={br0.value:.12f} br1={br1.value:.12f} "
        f"nash_conv={br0.value + br1.value:.12f} "
        f"exploitability={0.5 * (br0.value + br1.value):.12f}"
    )
    print(f"independent_crosscheck br0_full_tree={cross0:.12f} br1_full_tree={cross1:.12f}")
    print(
        f"timing profile_seconds={profile_seconds:.6f} br0_seconds={br0_seconds:.6f} "
        f"cross0_seconds={cross0_seconds:.6f} br1_seconds={br1_seconds:.6f} "
        f"cross1_seconds={cross1_seconds:.6f}"
    )
    print("HU TWO-ROUND HIDDEN-DISCARD ASYMMETRIC BR: PASS")


if __name__ == "__main__":
    main()
