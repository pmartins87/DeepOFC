from __future__ import annotations

from deepofc.hu_two_round_br import exact_best_response
from deepofc.hu_two_round_joker import HUTwoRoundJokerSubgame
from m5q_support_range_feasibility import exact_terminal_utility_range
from m5r_deep_branch_br_interval import deep_branch_best_response_interval
from m5r_target_width_budget_controller import plan_target_width_budget


def _profile(game, dominant_mass: float = 0.8):
    result = {}
    for info, actions in game.info_actions.items():
        ordered = tuple(sorted(actions, key=lambda action: action.key()))
        if len(ordered) == 1:
            result[info] = {ordered[0]: 1.0}
            continue
        tail = (1.0 - dominant_mass) / (len(ordered) - 1)
        result[info] = {
            action: dominant_mass if index == 0 else tail
            for index, action in enumerate(ordered)
        }
    return result


def test_planner_uses_no_terminal_utility() -> None:
    game = HUTwoRoundJokerSubgame()
    profile = _profile(game)

    def forbidden(*_args, **_kwargs):
        raise AssertionError("M5R-F planner must not call terminal_u0")

    game.terminal_u0 = forbidden
    plan = plan_target_width_budget(
        game,
        profile,
        0,
        utility_range=4.0,
        target_width=0.8,
    )
    assert plan.guaranteed_unresolved_br_width_cap <= 0.8 + 1e-12
    assert plan.planned_resolved_terminal_histories + plan.planned_skipped_terminal_histories == game.terminal_count()


def test_zero_target_requires_exact_work_for_bounded_full_support_profile() -> None:
    game = HUTwoRoundJokerSubgame()
    plan = plan_target_width_budget(
        game,
        _profile(game),
        0,
        utility_range=4.0,
        target_width=0.0,
    )
    assert plan.selected_prune_reach_threshold == 0.0
    assert plan.guaranteed_unresolved_br_width_cap <= 1e-12
    assert plan.planned_resolved_terminal_histories == game.terminal_count()
    assert plan.planned_skipped_terminal_histories == 0


def test_full_range_target_allows_zero_terminal_work() -> None:
    game = HUTwoRoundJokerSubgame()
    plan = plan_target_width_budget(
        game,
        _profile(game),
        1,
        utility_range=4.0,
        target_width=4.0,
    )
    assert plan.guaranteed_unresolved_br_width_cap <= 4.0 + 1e-12
    assert plan.planned_resolved_terminal_histories == 0
    assert plan.planned_terminal_work_fraction == 0.0


def test_planned_cap_dominates_actual_deep_interval() -> None:
    reference = HUTwoRoundJokerSubgame()
    profile = _profile(reference)
    utility = exact_terminal_utility_range(reference)
    p0_value = reference.expected_u0(profile)
    exact = exact_best_response(reference, profile, 0).value
    target = 0.20 * utility.utility_range

    planner_game = HUTwoRoundJokerSubgame()
    plan = plan_target_width_budget(
        planner_game,
        _profile(planner_game),
        0,
        utility_range=utility.utility_range,
        target_width=target,
    )

    eval_game = HUTwoRoundJokerSubgame()
    result = deep_branch_best_response_interval(
        eval_game,
        _profile(eval_game),
        0,
        profile_p0_value=p0_value,
        p0_utility_min=utility.minimum_p0_utility,
        p0_utility_max=utility.maximum_p0_utility,
        prune_reach_threshold=plan.selected_prune_reach_threshold,
    )

    assert result.lower_br_value <= exact + 1e-10 <= result.upper_br_value + 1e-10
    assert result.interval_width <= plan.guaranteed_unresolved_br_width_cap + 1e-10
    assert plan.guaranteed_unresolved_br_width_cap <= target + 1e-10
    assert result.resolved_terminal_histories == plan.planned_resolved_terminal_histories
    assert result.skipped_terminal_histories == plan.planned_skipped_terminal_histories
