from deepofc.hu_subgame import HUFinalRoundSubgame, actions_for_hand


def test_reduced_hu_subgame_has_real_hidden_information_and_uniform_chance():
    game = HUFinalRoundSubgame()
    assert len(game.outcomes) == 1120
    assert abs(game.chance_probability * len(game.outcomes) - 1.0) < 1e-15
    assert game.count_merged_second_infosets() > 0
    assert all(len(actions) == 6 for actions in game.info_actions.values())


def test_uniform_symmetric_profile_has_zero_expected_value():
    game = HUFinalRoundSubgame()
    profile = game.uniform_profile()
    assert abs(game.expected_u0(profile)) < 1e-12
    assert game.exact_reference_value == 0.0


def test_exact_best_response_measure_is_nonnegative_and_player_symmetric():
    game = HUFinalRoundSubgame()
    profile = game.uniform_profile()
    br0 = game.best_response_value(profile, 0)
    br1 = game.best_response_value(profile, 1)
    assert br0 >= -1e-12
    assert br1 >= -1e-12
    assert abs(br0 - br1) < 1e-12
    assert abs(game.nash_conv(profile) - (br0 + br1)) < 1e-12
    assert abs(game.exploitability(profile) - 0.5 * (br0 + br1)) < 1e-12


def test_terminal_player_swap_mirror_on_representative_physical_histories():
    game = HUFinalRoundSubgame()
    # Keep the normal CI gate light; a separate R6 workflow exhausts all 40,320
    # terminal branches through assert_terminal_swap_symmetry().
    for outcome in game.outcomes[::137]:
        mirrored = outcome.mirrored_swapped()
        first_actions = actions_for_hand(outcome.hand(outcome.first_player))
        second_actions = actions_for_hand(outcome.hand(outcome.second_player))
        for first_action in first_actions:
            for second_action in second_actions:
                u0 = game.terminal_u0(outcome, first_action, second_action)
                mirror_u0 = game.terminal_u0(
                    mirrored,
                    first_action.mirrored(),
                    second_action.mirrored(),
                )
                assert u0 == -mirror_u0
