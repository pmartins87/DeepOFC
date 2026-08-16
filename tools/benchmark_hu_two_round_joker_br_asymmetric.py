from __future__ import annotations

from pathlib import Path
import random
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from deepofc.hu_two_round_br import exact_best_response, profile_with_pure_response
from deepofc.hu_two_round_joker import HUTwoRoundJokerSubgame


def deterministic_profile(game):
    rng = random.Random(20260816)
    profile = {}
    for info, legal in game.info_actions.items():
        ordered = sorted(legal, key=lambda action: action.key())
        raw = {action: 0.01 + rng.random() ** 3 for action in ordered}
        total = sum(raw.values())
        profile[info] = {action: raw[action] / total for action in ordered}
    return profile


def main() -> None:
    game = HUTwoRoundJokerSubgame()
    profile = deterministic_profile(game)
    profile_u0 = game.expected_u0(profile)

    br0 = exact_best_response(game, profile, 0)
    cross0 = game.expected_u0(profile_with_pure_response(game, profile, br0))
    br1 = exact_best_response(game, profile, 1)
    cross1 = -game.expected_u0(profile_with_pure_response(game, profile, br1))

    if abs(br0.value - cross0) > 1e-10:
        raise SystemExit(f"Joker asymmetric BR0 mismatch: {br0.value} vs {cross0}")
    if abs(br1.value - cross1) > 1e-10:
        raise SystemExit(f"Joker asymmetric BR1 mismatch: {br1.value} vs {cross1}")

    print(
        f"joker_asymmetric expected_u0={profile_u0:.12f} "
        f"br0={br0.value:.12f} br1={br1.value:.12f} "
        f"nash_conv={br0.value + br1.value:.12f} "
        f"exploitability={0.5 * (br0.value + br1.value):.12f}"
    )
    print(f"independent_crosscheck br0_full_tree={cross0:.12f} br1_full_tree={cross1:.12f}")
    print("HU TWO-ROUND PHYSICAL-JOKER ASYMMETRIC BR: PASS")


if __name__ == "__main__":
    main()
