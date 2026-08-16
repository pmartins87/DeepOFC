from __future__ import annotations

import pytest

from deepofc.actions import NormalPlacementAction
from deepofc.sequential import (
    HUSequentialNormalState,
    deterministic_first_legal_hand,
    replay_hu_normal_hand,
)


def test_initial_hu_sequential_state_deals_private_five_card_batches():
    state = HUSequentialNormalState.new(seed=123, first_player=0)
    assert state.round_index == 0
    assert state.actor_in_round == 0
    assert state.acting_chair == 0
    assert state.actions_taken == 0
    assert state.deck.cursor == 10
    assert len(state.incoming[0]) == 5
    assert len(state.incoming[1]) == 5
    assert len(set((*state.incoming[0], *state.incoming[1]))) == 10
    assert state.boards[0].filled_count() == 0
    assert state.boards[1].filled_count() == 0


def test_observation_hides_opponent_current_incoming_and_discards():
    state = HUSequentialNormalState.new(seed=456, first_player=0)
    obs0 = state.observation(0)
    assert set(obs0.state.hero_incoming) == set(state.incoming[0])
    assert not (set(state.incoming[1]) & set(obs0.state.known_cards()))
    assert obs0.state.player(1).hidden_incoming_count == 5
    assert obs0.state.player(1).hidden_discard_count == 0

    # Finish round 0, then let player 0 act in round 1 so player 1 observes the
    # public placements but not player 0's discarded card.
    state = state.apply(state.legal_actions()[0])
    state = state.apply(state.legal_actions()[0])
    assert state.round_index == 1 and state.acting_chair == 0
    state = state.apply(state.legal_actions()[0])
    discard0 = state.discards[0][-1]
    obs1 = state.observation(1)
    assert discard0 not in obs1.state.known_cards()
    assert obs1.state.player(0).hidden_discard_count == 1
    assert all(not hasattr(record, "discard") for record in obs1.public_action_history)
    assert discard0.code not in repr(obs1.public_action_history)

    # Player 0 must retain the same private discard in its own perfect-recall
    # observation even though player 1 cannot see it.
    own = state.observation(0)
    assert discard0 in own.state.hero_discards
    assert own.own_action_history[-1][1] == discard0.code


def test_direct_apply_remains_fail_closed_without_enumerating_all_actions():
    state = HUSequentialNormalState.new(seed=777, first_player=0)
    state = state.apply(state.legal_actions()[0])
    state = state.apply(state.legal_actions()[0])
    assert state.round_index == 1

    valid = state.legal_actions()[0]
    incoming = set(state.incoming[state.acting_chair])
    outsider = next(card for card in state.deck.cards[state.deck.cursor:] if card not in incoming)
    invalid = NormalPlacementAction(
        placements=valid.placements,
        discard=outsider,
    )
    with pytest.raises(ValueError, match="cover each incoming physical card exactly once"):
        state.apply(invalid)


def test_full_seeded_hu_hand_replays_exactly_from_action_keys():
    finished = deterministic_first_legal_hand(seed=20260816, first_player=1, dealer_chair=1)
    assert finished.terminal
    assert finished.actions_taken == 10
    assert finished.deck.cursor == 34
    assert finished.boards[0].is_complete()
    assert finished.boards[1].is_complete()
    assert len(finished.discards[0]) == 4
    assert len(finished.discards[1]) == 4
    assert len(finished._authoritative_known_cards()) == 34
    assert len(set(finished._authoritative_known_cards())) == 34

    keys = tuple(record.action.key() for record in finished.history)
    replayed = replay_hu_normal_hand(
        seed=20260816,
        action_keys=keys,
        first_player=1,
        dealer_chair=1,
    )
    assert replayed == finished

    # At terminal each player knows both public boards plus only its own four
    # discard identities; the opponent's four discards remain absent.
    for chair in (0, 1):
        obs = replayed.observation(chair)
        opponent = 1 - chair
        assert set(replayed.discards[opponent]).isdisjoint(obs.state.known_cards())
        assert set(replayed.discards[chair]).issubset(obs.state.known_cards())
        assert obs.state.player(opponent).hidden_discard_count == 4
        assert not obs.state.action_required


def test_round_progress_is_exact_for_both_actor_orders():
    for first in (0, 1):
        state = HUSequentialNormalState.new(seed=999 + first, first_player=first)
        expected_actor_sequence = []
        for round_index in range(5):
            expected_actor_sequence.extend((first, 1 - first))
            before = 0 if round_index == 0 else 5 + 2 * (round_index - 1)
            assert state.round_index == round_index
            assert tuple(board.filled_count() for board in state.boards) == (before, before)
            assert tuple(len(cards) for cards in state.incoming) == (
                (5 if round_index == 0 else 3),
                (5 if round_index == 0 else 3),
            )
            state = state.apply(state.legal_actions()[0])
            assert state.acting_chair == 1 - first
            state = state.apply(state.legal_actions()[0])
        assert state.terminal
        assert [record.chair for record in state.history] == expected_actor_sequence


@pytest.mark.parametrize("seed", range(40))
@pytest.mark.parametrize("first_player", (0, 1))
def test_structural_fuzz_80_complete_hands_preserve_physical_and_replay_invariants(seed, first_player):
    finished = deterministic_first_legal_hand(seed=seed, first_player=first_player)
    assert finished.terminal
    assert finished.actions_taken == 10
    assert finished.deck.cursor == 34
    assert tuple(board.filled_count() for board in finished.boards) == (13, 13)
    assert tuple(len(x) for x in finished.discards) == (4, 4)
    known = finished._authoritative_known_cards()
    assert len(known) == 34
    assert len(set(known)) == 34
    assert set(known) == set(finished.deck.cards[:34])

    keys = tuple(record.action.key() for record in finished.history)
    replayed = replay_hu_normal_hand(
        seed=seed,
        action_keys=keys,
        first_player=first_player,
    )
    assert replayed == finished
