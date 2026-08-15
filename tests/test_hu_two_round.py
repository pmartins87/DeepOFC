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


def test_round4_infosets_preserve_private_discard_perfect_recall():
    game = HUTwoRoundSubgame()
    outcome = game.outcomes[0]
    first = outcome.first_player
    second = outcome.second_player
    second_actions = game._round3_actions(outcome, second)

    # Find two first-player round-3 actions with the same public placements but
    # different hidden discards. They MUST remain distinct at that player's own
    # round-4 infoset because perfect recall includes the private discard.
    groups = {}
    for action in game._round3_actions(outcome, first):
        groups.setdefault(action_public_key(action), []).append(action)
    pair = next(
        actions
        for actions in groups.values()
        if len(actions) >= 2 and len({action.discard for action in actions}) >= 2
    )
    first_a, first_b = pair[:2]
    second_r3 = second_actions[0]

    def first_round4_info(first_r3):
        board0, board1, action0, action1 = game._boards_after_round3(
            outcome, first_r3, second_r3
        )
        own = action0 if first == 0 else action1
        opp = action1 if first == 0 else action0
        # Ensure this branch really reaches a legal round-4 decision.
        assert game._round4_actions(outcome, first, board0, board1)
        return game.round4_info(
            outcome,
            player=first,
            own_round3_action=own,
            opponent_round3_action=opp,
            current_first_action=None,
        )

    info_a = first_round4_info(first_a)
    info_b = first_round4_info(first_b)
    assert action_public_key(first_a) == action_public_key(first_b)
    assert first_a.discard != first_b.discard
    assert info_a != info_b
    assert info_a.own_round3_action != info_b.own_round3_action


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
