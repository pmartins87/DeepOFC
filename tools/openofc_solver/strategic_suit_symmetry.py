from __future__ import annotations

"""Exact 24-way suit-isomorphism reduction for the HU strategic solver.

Poker suits have no intrinsic ordering in KKPoker OFC.  Applying one global
permutation of clubs/diamonds/hearts/spades to every card in an information
state preserves legal actions, hand ranks, royalties, fouls and terminal score.
This module canonicalizes that exact game automorphism instead of asking the
trainer to rediscover the same strategy up to 24 times.

Crucially, the permutation is selected from *only the acting player's
information state*.  Hidden opponent packets/discards and future cards are not
consulted.  The full public action history is transformed too, so strategic
signalling and perfect recall are preserved.
"""

from dataclasses import dataclass
from itertools import permutations
import json
import math
from typing import Sequence

from engine import Action, Board, Card, legal_actions
from strategic_cfr import (
    HUState,
    OutcomeSamplingMCCFR,
    PublicActionEvent,
    child_state,
    terminal_utility,
)

SUIT_PERMUTATIONS: tuple[tuple[int, int, int, int], ...] = tuple(
    permutations(range(4))
)
SOLVER_KIND = "suit24-exact"


@dataclass(frozen=True)
class HUVisibleObservation:
    """Complete acting-player view needed by the suit-canonical policy.

    Unlike :class:`HUState`, this object cannot carry an opponent packet,
    opponent discard identity, or any future card.  It is therefore the safe
    boundary for deployment adapters.  Boards and public-history player ids are
    in one-hand role order: 0=non-dealer/first, 1=dealer/button/second.
    """

    round_index: int
    actor: int
    boards: tuple[Board, Board]
    own_discards: tuple[Card, ...]
    incoming: tuple[Card, ...]
    public_history: tuple[PublicActionEvent, ...]

    @classmethod
    def from_state(cls, state: HUState) -> "HUVisibleObservation":
        if state.terminal():
            raise ValueError("terminal state has no visible policy observation")
        return cls(
            round_index=state.round_index,
            actor=state.actor,
            boards=state.boards,
            own_discards=state.discards[state.actor],
            incoming=state.plan.incoming(state.round_index, state.actor),
            public_history=state.public_history,
        )

    def validate(self) -> None:
        """Fail closed unless the visible node is a complete legal HU prefix."""

        if self.actor not in (0, 1):
            raise ValueError("visible HU actor must be role 0 or 1")
        if self.round_index not in range(5):
            raise ValueError("visible normal HU round must be 0..4")
        if len(self.boards) != 2:
            raise ValueError("visible HU observation requires two role-ordered boards")

        expected_incoming = 5 if self.round_index == 0 else 3
        if len(self.incoming) != expected_incoming:
            raise ValueError(
                f"visible round {self.round_index} requires {expected_incoming} incoming cards"
            )
        expected_own_discards = max(0, self.round_index - 1)
        if len(self.own_discards) != expected_own_discards:
            raise ValueError(
                "visible acting-player discard history has the wrong cardinality"
            )

        expected_events = tuple(
            (round_index, player)
            for round_index in range(self.round_index + 1)
            for player in (0, 1)
            if round_index < self.round_index or player < self.actor
        )
        actual_events = tuple(
            (event.round_index, event.player) for event in self.public_history
        )
        if actual_events != expected_events:
            raise ValueError(
                "visible public history is not the complete nondealer/dealer action prefix"
            )

        history_rows: list[list[list[Card]]] = [
            [[], [], []],
            [[], [], []],
        ]
        public_cards: list[Card] = []
        for event in self.public_history:
            expected_placements = 5 if event.round_index == 0 else 2
            if len(event.placements) != expected_placements:
                raise ValueError("visible public-history placement count is invalid")
            event_cards: set[Card] = set()
            for token, row in event.placements:
                if int(row) not in (0, 1, 2):
                    raise ValueError("visible public-history row is invalid")
                card = Card.parse(str(token))
                if str(card) != str(token):
                    raise ValueError("visible public-history card token is not canonical")
                if card in event_cards:
                    raise ValueError("visible public-history event repeats a physical card")
                event_cards.add(card)
                history_rows[event.player][int(row)].append(card)
                public_cards.append(card)

        if len(public_cards) != len(set(public_cards)):
            raise ValueError("visible public history repeats a physical card")
        for player in (0, 1):
            for row, board_cards in enumerate(self.boards[player].rows()):
                if tuple(sorted(board_cards)) != tuple(sorted(history_rows[player][row])):
                    raise ValueError(
                        "visible public history does not reconcile to the current boards"
                    )

        visible_private = (*self.own_discards, *self.incoming)
        if len(visible_private) != len(set(visible_private)):
            raise ValueError("visible own private cards repeat a physical card")
        if set(public_cards) & set(visible_private):
            raise ValueError("visible private card is already present on a public board")


def visible_observation_from_state(state: HUState) -> HUVisibleObservation:
    observation = HUVisibleObservation.from_state(state)
    observation.validate()
    return observation


def permute_card(card: Card, suit_map: Sequence[int]) -> Card:
    if len(suit_map) != 4 or sorted(int(x) for x in suit_map) != [0, 1, 2, 3]:
        raise ValueError("suit_map must be a permutation of 0..3")
    if card.joker:
        return card
    return Card(rank=card.rank, suit=int(suit_map[card.suit]))


def _token(card: Card, suit_map: Sequence[int]) -> str:
    return str(permute_card(card, suit_map))


def _token_from_text(text: str, suit_map: Sequence[int]) -> str:
    return _token(Card.parse(text), suit_map)


def _board_payload(board, suit_map: Sequence[int]) -> tuple[tuple[str, ...], ...]:
    return tuple(
        tuple(sorted(_token(card, suit_map) for card in row))
        for row in board.rows()
    )


def _visible_information_key_under_suit_map_unchecked(
    observation: HUVisibleObservation,
    suit_map: Sequence[int],
) -> str:
    player = observation.actor
    opponent = 1 - player
    history = tuple(
        (
            event.round_index,
            event.player,
            tuple(sorted(
                (_token_from_text(card, suit_map), int(row))
                for card, row in event.placements
            )),
        )
        for event in observation.public_history
    )
    payload = {
        "v": 2,
        "symmetry": SOLVER_KIND,
        "player": player,
        "position": "nondealer_first" if player == 0 else "dealer_button_second",
        "round": observation.round_index,
        "self_board": _board_payload(observation.boards[player], suit_map),
        "opp_board": _board_payload(observation.boards[opponent], suit_map),
        "own_discards": tuple(sorted(
            _token(card, suit_map) for card in observation.own_discards
        )),
        "incoming": tuple(sorted(
            _token(card, suit_map) for card in observation.incoming
        )),
        "public_history": history,
    }
    return json.dumps(payload, sort_keys=True, separators=(",", ":"))


def visible_information_key_under_suit_map(
    observation: HUVisibleObservation,
    suit_map: Sequence[int],
) -> str:
    observation.validate()
    return _visible_information_key_under_suit_map_unchecked(
        observation, suit_map
    )


def information_key_under_suit_map(
    state: HUState,
    suit_map: Sequence[int],
) -> str:
    return visible_information_key_under_suit_map(
        visible_observation_from_state(state), suit_map
    )


def canonical_visible_information_key(
    observation: HUVisibleObservation,
) -> tuple[str, tuple[int, int, int, int]]:
    """Return the canonical key using visible cards and history only."""

    observation.validate()
    candidates = (
        (
            _visible_information_key_under_suit_map_unchecked(
                observation, suit_map
            ),
            suit_map,
        )
        for suit_map in SUIT_PERMUTATIONS
    )
    return min(candidates, key=lambda item: (item[0], item[1]))


def canonical_information_key(state: HUState) -> tuple[str, tuple[int, int, int, int]]:
    """Return lexicographically canonical visible information and suit map."""
    return canonical_visible_information_key(
        HUVisibleObservation.from_state(state)
    )


def action_key_under_suit_map(
    action: Action,
    incoming: Sequence[Card],
    suit_map: Sequence[int],
) -> str:
    placements = sorted(
        (_token(incoming[index], suit_map), int(row))
        for index, row in action.placements
    )
    discard = None
    if action.discard_index is not None:
        discard = _token(incoming[action.discard_index], suit_map)
    return json.dumps(
        {"p": placements, "d": discard},
        sort_keys=True,
        separators=(",", ":"),
    )


def _canonical_visible_action_pairs_unchecked(
    observation: HUVisibleObservation,
    suit_map: Sequence[int],
) -> list[tuple[str, Action]]:
    pairs = [
        (action_key_under_suit_map(action, observation.incoming, suit_map), action)
        for action in legal_actions(
            observation.boards[observation.actor],
            observation.incoming,
            observation.round_index,
        )
    ]
    pairs.sort(key=lambda item: item[0])
    if len({key for key, _action in pairs}) != len(pairs):
        raise AssertionError("suit-canonical legal action keys collided")
    return pairs


def canonical_visible_action_pairs(
    observation: HUVisibleObservation,
    suit_map: Sequence[int],
) -> list[tuple[str, Action]]:
    observation.validate()
    return _canonical_visible_action_pairs_unchecked(observation, suit_map)


def canonical_action_pairs(
    state: HUState,
    suit_map: Sequence[int],
) -> list[tuple[str, Action]]:
    return canonical_visible_action_pairs(
        HUVisibleObservation.from_state(state), suit_map
    )


def canonical_visible_node_view(
    observation: HUVisibleObservation,
) -> tuple[str, list[tuple[str, Action]], tuple[int, int, int, int]]:
    key, suit_map = canonical_visible_information_key(observation)
    return (
        key,
        _canonical_visible_action_pairs_unchecked(observation, suit_map),
        suit_map,
    )


def canonical_node_view(
    state: HUState,
) -> tuple[str, list[tuple[str, Action]], tuple[int, int, int, int]]:
    return canonical_visible_node_view(HUVisibleObservation.from_state(state))


def _sample_index(probabilities: Sequence[float], rng) -> int:
    x = rng.random()
    cumulative = 0.0
    for i, p in enumerate(probabilities):
        if p < 0.0 or not math.isfinite(p):
            raise ValueError("invalid policy probability")
        cumulative += p
        if x < cumulative or i == len(probabilities) - 1:
            return i
    raise AssertionError("probability sampling fell through")


class SuitCanonicalOutcomeSamplingMCCFR(OutcomeSamplingMCCFR):
    """Outcome-sampling MCCFR with exact suit-isomorphic infoset merging."""

    solver_kind = SOLVER_KIND

    def _episode(
        self,
        state: HUState,
        update_player: int,
        *,
        my_reach: float,
        opp_reach: float,
        sample_reach: float,
    ) -> float:
        if state.terminal():
            return terminal_utility(state, update_player)

        current = state.actor
        key, pairs, _suit_map = canonical_node_view(state)
        action_keys = [action_key for action_key, _ in pairs]
        actions = [action for _, action in pairs]
        node = self._node(key, action_keys)
        policy = node.current_policy()

        if current == update_player:
            uniform = 1.0 / len(policy)
            sample_policy = [
                self.epsilon * uniform + (1.0 - self.epsilon) * p
                for p in policy
            ]
        else:
            sample_policy = list(policy)

        sampled = _sample_index(sample_policy, self.rng)
        if current == update_player:
            new_my_reach = my_reach * policy[sampled]
            new_opp_reach = opp_reach
        else:
            new_my_reach = my_reach
            new_opp_reach = opp_reach * policy[sampled]
        new_sample_reach = sample_reach * sample_policy[sampled]
        child_value = self._episode(
            child_state(state, actions[sampled]),
            update_player,
            my_reach=new_my_reach,
            opp_reach=new_opp_reach,
            sample_reach=new_sample_reach,
        )

        child_values = [0.0] * len(policy)
        child_values[sampled] = child_value / sample_policy[sampled]
        value_estimate = sum(
            policy[i] * child_values[i] for i in range(len(policy))
        )

        if current == update_player:
            if sample_reach <= 0.0:
                raise AssertionError("sample reach became non-positive")
            scale = opp_reach / sample_reach
            cf_value = value_estimate * scale
            for i in range(len(policy)):
                delta = child_values[i] * scale - cf_value
                updated = node.cumulative_regrets[i] + delta
                node.cumulative_regrets[i] = (
                    max(0.0, updated) if self.cfr_plus else updated
                )
            for i in range(len(policy)):
                node.cumulative_policy[i] += (
                    my_reach * policy[i] / sample_reach
                )
            node.visits += 1

        return value_estimate
