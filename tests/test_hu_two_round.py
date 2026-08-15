from deepofc.hu_two_round import (
    HUTwoRoundSubgame,
    action_public_key,
    mirror_action,
)


def test_two_round_reduced_support_and_branch_cardinality():
    game = HUTwoRoundSubgame()
    assert len(game.outcomes) == 32
    assert abs(game.chance_probability * len(game.outcomes) - 1.0) < 1e-15
    assert game.terminal_count() == 373_248

    outcome = game.outcomes[0]
    first = outcome.first_player
    second = outcome.second_player
    first_r3 = game._round3_actions(outcome, first)
    second_r3 = game._round3_actions(outcome, second)
    assert len(first_r3) == 21
    assert len(second_r3) == 21

    observed_round4_counts = set()
    for action_first in first_r3:
        for action_second in second_r3:
            board0, board1, _, _ = game._boards_after_round3(
                outcome, action_first, action_second
            )
            observed_round4_counts.add(
                len(game._round4_actions(outcome, first, board0, board1))
            )
            observed_round4_counts.add(
                len(game._round4_actions(outcome, second, board0, board1))
            )
    assert observed_round4_counts == {3, 6}


def test_round4_infosets_preserve_exact_private_action_for_perfect_recall():
    game = HUTwoRoundSubgame()
    outcome = game.outcomes[0]
    first = outcome.first_player
    second = outcome.second_player
    first_r3 = game._round3_actions(outcome, first)[0]
    second_r3 = game._round3_actions(outcome, second)[0]

    board0, board1, action0, action1 = game._boards_after_round3(
        outcome, first_r3, second_r3
    )
    own = action0 if first == 0 else action1
    opp = action1 if first == 0 else action0
    assert own.discard is not None
    assert game._round4_actions(outcome, first, board0, board1)

    info = game.round4_info(
        outcome,
        player=first,
        own_round3_action=own,
        opponent_round3_action=opp,
        current_first_action=None,
    )

    # NormalPlacementAction.key() includes placements AND the private discarded
    # physical card. Storing the complete key freezes perfect recall explicitly,
    # even though for one fixed three-card hand the two public placements also
    # determine the discarded third card.
    assert info.own_round3_action == own.key()
    assert info.own_round3_action[-1] == own.discard.code
    assert info.own_round3_hand == tuple(
        sorted(card.code for card in outcome.hand(first, 3))
    )
    assert info.opponent_round3_public == action_public_key(opp)


def test_round4_still_contains_genuine_hidden_history_merging():
    game = HUTwoRoundSubgame()
    assert game.count_merged_round4_infosets() > 0


def test_representative_terminal_swap_symmetry_and_no_unfrozen_scoring_branch():
    game = HUTwoRoundSubgame()
    support = set(game.outcomes)

    for outcome in game.outcomes[::7]:
        mirrored = outcome.mirrored_swapped()
        assert mirrored in support
        first = outcome.first_player
        second = outcome.second_player
        first_r3_actions = game._round3_actions(outcome, first)
        second_r3_actions = game._round3_actions(outcome, second)

        for first_r3 in first_r3_actions[::5]:
            for second_r3 in second_r3_actions[::5]:
                board0, board1, _, _ = game._boards_after_round3(
                    outcome, first_r3, second_r3
                )
                first_r4_actions = game._round4_actions(outcome, first, board0, board1)
                second_r4_actions = game._round4_actions(outcome, second, board0, board1)
                for first_r4 in first_r4_actions[:1]:
                    for second_r4 in second_r4_actions[:1]:
                        u0 = game.terminal_u0(
                            outcome,
                            first_r3,
                            second_r3,
                            first_r4,
                            second_r4,
                        )
                        mirror_u0 = game.terminal_u0(
                            mirrored,
                            mirror_action(first_r3),
                            mirror_action(second_r3),
                            mirror_action(first_r4),
                            mirror_action(second_r4),
                        )
                        assert u0 == -mirror_u0
