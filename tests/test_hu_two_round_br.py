from deepofc.hu_two_round import HUTwoRoundSubgame
from deepofc.hu_two_round_br import (
    exact_best_response,
    profile_with_pure_response,
)


def test_exact_deep_best_response_matches_independent_tree_evaluation():
    game = HUTwoRoundSubgame()
    opponent = game.uniform_profile()

    response = exact_best_response(game, opponent, 0)
    materialized = profile_with_pure_response(game, opponent, response)
    independently_evaluated = game.expected_u0(materialized)

    assert response.value >= -1e-12
    assert abs(independently_evaluated - response.value) < 1e-10
    assert set(response.choices) == {
        info for info in game.info_actions if info.player == 0
    }
