from __future__ import annotations

import math

import pytest

from deepofc.hu_two_round_joker import HUTwoRoundJokerSubgame
from m5q_variance_mstar_floor import appendix_c_mstar_zero_variance_floor


def test_uniform_joker_mstar_is_positive_and_no_larger_than_static_m() -> None:
    game = HUTwoRoundJokerSubgame()
    report = appendix_c_mstar_zero_variance_floor(
        game,
        game.uniform_profile(),
        utility_range=1.0,
        sampling_probability_floor=1.0,
    )

    for structure in (report.player0, report.player1):
        assert structure.best_response_m_value > 0.0
        assert structure.best_response_m_value <= structure.static_m_value + 1e-12
        assert structure.reached_prefix_groups <= structure.prefix_groups
        assert structure.max_actions > 0

    assert report.certification_eligible is False if hasattr(report, "certification_eligible") else True
    assert report.payload()["certification_eligible"] is False
    assert report.payload()["real_routes_certified"] == 0


def test_raw_range_and_sampling_floor_scale_the_optimistic_coefficient() -> None:
    game = HUTwoRoundJokerSubgame()
    profile = game.uniform_profile()
    unit = appendix_c_mstar_zero_variance_floor(
        game, profile, utility_range=1.0, sampling_probability_floor=1.0
    )
    raw = appendix_c_mstar_zero_variance_floor(
        game, profile, utility_range=206.0, sampling_probability_floor=1.0
    )
    half_delta = appendix_c_mstar_zero_variance_floor(
        game, profile, utility_range=1.0, sampling_probability_floor=0.5
    )

    assert math.isclose(raw.exploitability_coefficient, 206.0 * unit.exploitability_coefficient)
    assert math.isclose(half_delta.exploitability_coefficient, 2.0 * unit.exploitability_coefficient)
    assert raw.required_iterations(0.15) >= unit.required_iterations(0.15)
    assert half_delta.required_iterations(0.15) >= 4 * unit.required_iterations(0.15) - 3


def test_floor_identity_is_deterministic() -> None:
    game = HUTwoRoundJokerSubgame()
    first = appendix_c_mstar_zero_variance_floor(
        game, game.uniform_profile(), utility_range=1.0
    )
    second = appendix_c_mstar_zero_variance_floor(
        game, game.uniform_profile(), utility_range=1.0
    )
    assert first.sha256 == second.sha256
    assert first.payload() == second.payload()


def test_invalid_inputs_fail_closed() -> None:
    game = HUTwoRoundJokerSubgame()
    profile = game.uniform_profile()
    with pytest.raises(ValueError):
        appendix_c_mstar_zero_variance_floor(game, profile, utility_range=0.0)
    with pytest.raises(ValueError):
        appendix_c_mstar_zero_variance_floor(
            game, profile, utility_range=1.0, sampling_probability_floor=0.0
        )
    with pytest.raises(ValueError):
        appendix_c_mstar_zero_variance_floor(
            game, profile, utility_range=1.0, sampling_probability_floor=1.01
        )
