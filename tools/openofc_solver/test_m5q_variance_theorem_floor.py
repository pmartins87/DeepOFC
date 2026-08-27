from __future__ import annotations

import math

import pytest

from deepofc.hu_two_round_joker import HUTwoRoundJokerSubgame
from m5q_variance_theorem_floor import (
    AUTHORITY,
    player_info_structure,
    zero_variance_theorem_floor,
)


def test_joker_player_structure_is_symmetric_and_nonempty() -> None:
    game = HUTwoRoundJokerSubgame()
    p0 = player_info_structure(game, 0)
    p1 = player_info_structure(game, 1)
    assert p0.infosets == p1.infosets
    assert p0.max_actions == p1.max_actions
    assert p0.infosets > 0
    assert p0.max_actions > 0


def test_zero_variance_floor_scales_linearly_with_delta_and_inverse_sqrt_t() -> None:
    game = HUTwoRoundJokerSubgame()
    unit = zero_variance_theorem_floor(game, delta_hat=1.0)
    doubled = zero_variance_theorem_floor(game, delta_hat=2.0)
    assert unit.authority == AUTHORITY
    assert doubled.exploitability_coefficient == pytest.approx(
        2.0 * unit.exploitability_coefficient, rel=1e-12
    )
    assert unit.bound_at(400) == pytest.approx(0.5 * unit.bound_at(100), rel=1e-12)
    assert unit.sha256 and len(unit.sha256) == 64


def test_required_iterations_is_minimal_integer_for_target() -> None:
    game = HUTwoRoundJokerSubgame()
    floor = zero_variance_theorem_floor(game, delta_hat=1.0)
    target = 0.15
    required = floor.required_iterations(target)
    assert required > 1
    assert floor.bound_at(required) <= target + 1e-12
    assert floor.bound_at(required - 1) > target - 1e-12


def test_fail_closed_inputs() -> None:
    game = HUTwoRoundJokerSubgame()
    with pytest.raises(ValueError):
        player_info_structure(game, -1)
    with pytest.raises(ValueError):
        zero_variance_theorem_floor(game, delta_hat=0.0)
    floor = zero_variance_theorem_floor(game, delta_hat=1.0)
    with pytest.raises(ValueError):
        floor.required_iterations(math.nan)
    with pytest.raises(ValueError):
        floor.bound_at(0)
