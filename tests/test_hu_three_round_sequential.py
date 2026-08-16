from __future__ import annotations

from deepofc.hu_three_round_sequential import HUThreeRoundSequentialSubgame
from deepofc.hu_two_round_joker import joker_mirror_action
from deepofc.scoring import is_foul
from deepofc.simulator import settle_raw_points


def test_three_round_benchmark_has_eight_chance_outcomes_and_real_sequential_checkpoint():
    game = HUThreeRoundSequentialSubgame()
    assert len(game.outcomes) == 8
    for outcome in game.outcomes:
        state = game.initial_state(outcome)
        assert state.round_index == 2
        assert state.actor_in_round == 0
        assert state.actions_taken == 4
        assert state.deck.cursor == 22
        assert tuple(board.filled_count() for board in state.boards) == (7, 7)
        assert tuple(len(cards) for cards in state.incoming) == (3, 3)
        assert tuple(len(cards) for cards in state.discards) == (1, 1)
        assert len(state.boards[0].middle) == 5
        assert len(state.boards[1].middle) == 5


def test_three_round_first_legal_path_reaches_nonfoul_terminal_with_six_more_actions():
    game = HUThreeRoundSequentialSubgame()
    state = game.initial_state(game.outcomes[0])
    start_actions = state.actions_taken
    while not state.terminal:
        legal = state.legal_actions()
        assert legal
        state = state.apply(legal[0])
    assert state.actions_taken - start_actions == 6
    assert tuple(board.filled_count() for board in state.boards) == (13, 13)
    assert tuple(len(cards) for cards in state.discards) == (4, 4)
    assert not is_foul(state.boards[0])
    assert not is_foul(state.boards[1])
    settlement = settle_raw_points(state.boards)
    assert settlement.zero_sum


def test_three_round_root_actions_mirror_to_swapped_chance_outcome():
    game = HUThreeRoundSequentialSubgame()
    outcome = game.outcomes[0]
    mirrored = outcome.mirrored_swapped()
    left = game.initial_state(outcome)
    right = game.initial_state(mirrored)
    assert right.acting_chair == 1 - left.acting_chair
    right_by_key = {action.key(): action for action in right.legal_actions()}
    for action in left.legal_actions():
        mirrored_action = joker_mirror_action(action)
        assert mirrored_action.key() in right_by_key
