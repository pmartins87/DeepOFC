from __future__ import annotations

from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from deepofc.hu_two_round import HUTwoRoundSubgame
from deepofc.hu_two_round_cfr import TwoRoundFullTreeCFR


def exact_expected_outcome_delta_at_uniform(game: HUTwoRoundSubgame):
    """Enumerate the complete sampling law and integrate Eq. 10 exactly.

    At the initial zero-regret profile every behavioral distribution is uniform,
    so epsilon-greedy outcome sampling has the same sampling distribution for
    every epsilon. We nevertheless keep q(z), opponent/chance reach and future
    own reach as separate factors to validate the importance-weighted formula
    rather than cancelling them algebraically in the implementation.
    """

    expected = {
        info: {action: 0.0 for action in actions}
        for info, actions in game.info_actions.items()
    }
    cp = game.chance_probability
    terminals = 0

    for traverser in (0, 1):
        for outcome in game.outcomes:
            first = outcome.first_player
            second = outcome.second_player

            first_r3_info = game.round3_first_info(outcome)
            first_r3_actions = game.actions(first_r3_info)
            p_first_r3 = 1.0 / len(first_r3_actions)
            for first_r3 in first_r3_actions:
                second_r3_info = game.round3_second_info(outcome, first_r3)
                second_r3_actions = game.actions(second_r3_info)
                p_second_r3 = 1.0 / len(second_r3_actions)

                for second_r3 in second_r3_actions:
                    _, _, action0_r3, action1_r3 = game._boards_after_round3(
                        outcome, first_r3, second_r3
                    )
                    first_own_r3 = action0_r3 if first == 0 else action1_r3
                    first_opp_r3 = action1_r3 if first == 0 else action0_r3
                    second_own_r3 = action0_r3 if second == 0 else action1_r3
                    second_opp_r3 = action1_r3 if second == 0 else action0_r3

                    first_r4_info = game.round4_info(
                        outcome,
                        player=first,
                        own_round3_action=first_own_r3,
                        opponent_round3_action=first_opp_r3,
                        current_first_action=None,
                    )
                    first_r4_actions = game.actions(first_r4_info)
                    p_first_r4 = 1.0 / len(first_r4_actions)

                    for first_r4 in first_r4_actions:
                        second_r4_info = game.round4_info(
                            outcome,
                            player=second,
                            own_round3_action=second_own_r3,
                            opponent_round3_action=second_opp_r3,
                            current_first_action=first_r4,
                        )
                        second_r4_actions = game.actions(second_r4_info)
                        p_second_r4 = 1.0 / len(second_r4_actions)

                        for second_r4 in second_r4_actions:
                            terminals += 1
                            q = (
                                cp
                                * p_first_r3
                                * p_second_r3
                                * p_first_r4
                                * p_second_r4
                            )
                            u0 = float(
                                game.terminal_u0(
                                    outcome,
                                    first_r3,
                                    second_r3,
                                    first_r4,
                                    second_r4,
                                )
                            )
                            utility = u0 if traverser == 0 else -u0

                            if first == traverser:
                                own_decisions = (
                                    (first_r3_info, first_r3, p_first_r3),
                                    (first_r4_info, first_r4, p_first_r4),
                                )
                                pi_minus_i = (
                                    cp * p_second_r3 * p_second_r4
                                )
                            else:
                                own_decisions = (
                                    (second_r3_info, second_r3, p_second_r3),
                                    (second_r4_info, second_r4, p_second_r4),
                                )
                                pi_minus_i = cp * p_first_r3 * p_first_r4

                            future_own_probability = 1.0
                            for info, sampled_action, sigma_selected in reversed(
                                own_decisions
                            ):
                                weight = (
                                    utility
                                    * pi_minus_i
                                    * future_own_probability
                                    / q
                                )
                                sigma = 1.0 / len(game.actions(info))
                                bucket = expected[info]
                                for action in bucket:
                                    if action == sampled_action:
                                        sampled_regret = weight * (1.0 - sigma)
                                    else:
                                        sampled_regret = -weight * sigma
                                    bucket[action] += q * sampled_regret
                                future_own_probability *= sigma_selected

    expected_terminals = 2 * game.terminal_count()
    if terminals != expected_terminals:
        raise AssertionError(
            f"integrated {terminals} terminal samples, expected {expected_terminals}"
        )
    return expected


def main() -> None:
    game = HUTwoRoundSubgame()

    full_started = time.perf_counter()
    full = TwoRoundFullTreeCFR(game, variant="dcfr")
    full.step()
    full_seconds = time.perf_counter() - full_started

    sampled_started = time.perf_counter()
    expected_sampled = exact_expected_outcome_delta_at_uniform(game)
    sampled_seconds = time.perf_counter() - sampled_started

    worst = 0.0
    worst_label = None
    compared = 0
    for info, exact_values in full.regrets.items():
        sampled_values = expected_sampled[info]
        for action, exact_value in exact_values.items():
            error = abs(sampled_values[action] - exact_value)
            compared += 1
            if error > worst:
                worst = error
                worst_label = (info, action, sampled_values[action], exact_value)

    print(
        "outcome_unbiasedness "
        f"infosets={len(game.info_actions)} actions_compared={compared} "
        f"sample_histories_integrated={2 * game.terminal_count()} "
        f"max_abs_regret_error={worst:.18e}"
    )
    print(
        f"full_tree_first_step_seconds={full_seconds:.6f} "
        f"exact_sampling_expectation_seconds={sampled_seconds:.6f}"
    )
    if worst > 1e-10:
        raise SystemExit(
            "outcome-sampling expected regret does not match full-tree CFR: "
            f"worst={worst} at {worst_label}"
        )
    print("HU TWO-ROUND OUTCOME-SAMPLING UNBIASEDNESS: PASS")


if __name__ == "__main__":
    main()
