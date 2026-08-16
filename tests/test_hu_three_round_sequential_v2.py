from __future__ import annotations

from collections import defaultdict

from deepofc.hu_three_round_mccfr import HUThreeRoundExternalSamplingMCCFR
from deepofc.hu_three_round_sequential_v2 import HUThreeRoundSequentialSubgameV2
from deepofc.scoring import is_foul


def after_round2(game, outcome):
    state = game.initial_state(outcome)
    state = game.transition(state, game.actions(game.info(state))[0])
    state = game.transition(state, game.actions(game.info(state))[0])
    assert state.round_index == 3 and state.actor_in_round == 0
    return state


def test_v2_has_32_independent_future_chance_outcomes():
    game = HUThreeRoundSequentialSubgameV2()
    assert len(game.outcomes) == 32
    assert len({
        (o.p0_r3_variant, o.p0_r4_variant, o.p1_r3_variant, o.p1_r4_variant, o.first_player)
        for o in game.outcomes
    }) == 32


def test_current_round_observation_cannot_reveal_any_future_chance_bits():
    game = HUThreeRoundSequentialSubgameV2()
    for first in (0, 1):
        outcomes = [o for o in game.outcomes if o.first_player == first]
        for hero in (0, 1):
            observations = {game.initial_state(o).observation(hero) for o in outcomes}
            # Sixteen distinct authoritative future decks collapse to exactly one
            # player observation at the current decision.
            assert len(observations) == 1


def test_round3_private_hand_still_does_not_reveal_round4_or_opponent_bits():
    game = HUThreeRoundSequentialSubgameV2()
    for first in (0, 1):
        for hero in (0, 1):
            grouped = defaultdict(set)
            for outcome in game.outcomes:
                if outcome.first_player != first:
                    continue
                state = after_round2(game, outcome)
                own_r3 = outcome.r3_variant(hero)
                grouped[own_r3].add(state.observation(hero))
            # Given the observed own r3 hand, the independently sampled own r4
            # bit and both opponent future bits are still hidden.
            assert set(grouped) == {0, 1}
            assert all(len(observations) == 1 for observations in grouped.values())


def test_v2_first_legal_path_reaches_valid_nonfoul_terminal():
    game = HUThreeRoundSequentialSubgameV2()
    state = game.initial_state(game.outcomes[0])
    while not state.terminal:
        state = game.transition(state, game.actions(game.info(state))[0])
    state.assert_fully_valid()
    assert tuple(board.filled_count() for board in state.boards) == (13, 13)
    assert tuple(len(d) for d in state.discards) == (4, 4)
    assert not is_foul(state.boards[0], equality_allowed=True)
    assert not is_foul(state.boards[1], equality_allowed=True)


def test_v2_external_sampling_one_iteration_expands_162_own_sequences_per_player():
    game = HUThreeRoundSequentialSubgameV2()
    solver = HUThreeRoundExternalSamplingMCCFR(game, seed=20260816)
    solver.step()
    stats = solver.stats()
    assert stats.iterations == 1
    assert stats.terminal_evaluations == 324
