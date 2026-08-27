from __future__ import annotations

import math

from deepofc.hu_two_round_joker import HUTwoRoundJokerSubgame
from m5r_truncated_br_interval import truncated_best_response_interval


def test_nested_joker_intervals_contain_exact_br_and_collapse_at_full_resolution() -> None:
    game = HUTwoRoundJokerSubgame()
    profile = game.uniform_profile()
    rows = [
        truncated_best_response_interval(
            game,
            profile,
            0,
            p0_utility_min=-2.0,
            p0_utility_max=2.0,
            resolution_modulus=modulus,
        )
        for modulus in (16, 4, 1)
    ]

    for row in rows:
        assert row.lower_br_value <= row.exact_br_value + 1e-10
        assert row.exact_br_value <= row.upper_br_value + 1e-10
        assert row.upper_deviation_gain + 1e-10 >= row.exact_deviation_gain
        assert row.interval_width >= -1e-12
        assert row.production_certification_eligible is False
        assert row.real_routes_certified == 0

    assert rows[0].resolved_terminal_histories < rows[1].resolved_terminal_histories
    assert rows[1].resolved_terminal_histories < rows[2].resolved_terminal_histories
    assert rows[0].interval_width + 1e-10 >= rows[1].interval_width
    assert rows[1].interval_width + 1e-10 >= rows[2].interval_width
    assert math.isclose(rows[2].lower_br_value, 1.125, abs_tol=1e-12)
    assert math.isclose(rows[2].upper_br_value, 1.125, abs_tol=1e-12)
    assert rows[2].unresolved_terminal_histories == 0
