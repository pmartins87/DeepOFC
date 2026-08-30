from __future__ import annotations

"""Reference-only exact global-suit automorphism helpers for 06S0.

Nothing in this module is wired into the strategic trainer. The implementation
intentionally enumerates all 24 suit permutations so the proof surface is easy
to audit before any optimized canonicalizer is considered.
"""

from itertools import permutations
import json
from typing import Iterable, Sequence

from engine import Board, Card
from strategic_cfr import (
    DealPlan,
    HUState,
    PublicActionEvent,
    information_state_key,
    legal_action_pairs,
)

SuitPermutation = tuple[int, int, int, int]
ALL_SUIT_PERMUTATIONS: tuple[SuitPermutation, ...] = tuple(permutations(range(4)))
IDENTITY_SUIT_PERMUTATION: SuitPermutation = (0, 1, 2, 3)


def inverse_suit_permutation(perm: SuitPermutation) -> SuitPermutation:
    if tuple(sorted(perm)) != IDENTITY_SUIT_PERMUTATION:
        raise ValueError("suit permutation must be a permutation of 0..3")
    inverse = [0, 0, 0, 0]
    for source, target in enumerate(perm):
        inverse[target] = source
    return tuple(inverse)  # type: ignore[return-value]


def permute_card(card: Card, perm: SuitPermutation) -> Card:
    if card.joker:
        return card
    return Card(rank=card.rank, suit=perm[card.suit])


def _parse_and_permute_card_token(token: str, perm: SuitPermutation) -> Card:
    return permute_card(Card.parse(token), perm)


def permute_board(board: Board, perm: SuitPermutation) -> Board:
    return Board(*(
        tuple(permute_card(card, perm) for card in row)
        for row in board.rows()
    ))


def _permute_sorted_packet(packet: Sequence[Card], perm: SuitPermutation) -> tuple[Card, ...]:
    return tuple(sorted(permute_card(card, perm) for card in packet))


def permute_deal_plan(plan: DealPlan, perm: SuitPermutation) -> DealPlan:
    opening = (
        _permute_sorted_packet(plan.opening[0], perm),
        _permute_sorted_packet(plan.opening[1], perm),
    )
    rounds = tuple(
        (
            _permute_sorted_packet(packets[0], perm),
            _permute_sorted_packet(packets[1], perm),
        )
        for packets in plan.rounds
    )
    return DealPlan(opening=opening, rounds=rounds)  # type: ignore[arg-type]


def permute_public_event(event: PublicActionEvent, perm: SuitPermutation) -> PublicActionEvent:
    placements = tuple(sorted(
        (str(_parse_and_permute_card_token(card, perm)), int(row))
        for card, row in event.placements
    ))
    return PublicActionEvent(event.round_index, event.player, placements)


def permute_state(state: HUState, perm: SuitPermutation) -> HUState:
    return HUState(
        plan=permute_deal_plan(state.plan, perm),
        round_index=state.round_index,
        actor=state.actor,
        boards=(permute_board(state.boards[0], perm), permute_board(state.boards[1], perm)),
        discards=(
            tuple(permute_card(card, perm) for card in state.discards[0]),
            tuple(permute_card(card, perm) for card in state.discards[1]),
        ),
        public_history=tuple(permute_public_event(event, perm) for event in state.public_history),
    )


def permute_action_key(action_key: str, perm: SuitPermutation) -> str:
    payload = json.loads(action_key)
    placements = sorted(
        [str(_parse_and_permute_card_token(card, perm)), int(row)]
        for card, row in payload["p"]
    )
    discard = payload["d"]
    if discard is not None:
        discard = str(_parse_and_permute_card_token(discard, perm))
    return json.dumps({"p": placements, "d": discard}, sort_keys=True, separators=(",", ":"))


def _permute_board_payload(rows: Iterable[Iterable[str]], perm: SuitPermutation) -> list[list[str]]:
    return [
        sorted(str(_parse_and_permute_card_token(token, perm)) for token in row)
        for row in rows
    ]


def permute_observation_payload(payload: dict, perm: SuitPermutation) -> dict:
    """Permute only fields already present in the certified observable infoset payload."""
    transformed = {
        "v": payload["v"],
        "player": payload["player"],
        "position": payload["position"],
        "round": payload["round"],
        "self_board": _permute_board_payload(payload["self_board"], perm),
        "opp_board": _permute_board_payload(payload["opp_board"], perm),
        "own_discards": sorted(
            str(_parse_and_permute_card_token(token, perm))
            for token in payload["own_discards"]
        ),
        "incoming": [
            str(card)
            for card in sorted(
                _parse_and_permute_card_token(token, perm)
                for token in payload["incoming"]
            )
        ],
        "public_history": [],
    }
    for event in payload["public_history"]:
        round_index, player, placements = event
        mapped = sorted(
            [str(_parse_and_permute_card_token(card, perm)), int(row)]
            for card, row in placements
        )
        transformed["public_history"].append([int(round_index), int(player), mapped])
    return transformed


def serialize_observation_payload(payload: dict) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"))


def canonicalize_observation_payload(payload: dict) -> tuple[str, SuitPermutation]:
    candidates = [
        (serialize_observation_payload(permute_observation_payload(payload, perm)), perm)
        for perm in ALL_SUIT_PERMUTATIONS
    ]
    return min(candidates, key=lambda row: (row[0], row[1]))


def canonical_information_state(state: HUState) -> tuple[str, SuitPermutation]:
    # The source payload is information_state_key(), whose hidden-information
    # firewall was certified in 06A. No other DealPlan field is inspected here.
    raw = json.loads(information_state_key(state))
    return canonicalize_observation_payload(raw)


def canonical_legal_action_keys(state: HUState) -> tuple[str, ...]:
    _canonical_key, perm = canonical_information_state(state)
    keys = tuple(sorted(
        permute_action_key(raw_key, perm)
        for raw_key, _action in legal_action_pairs(state)
    ))
    if len(set(keys)) != len(keys):
        raise AssertionError("suit canonicalization collapsed two legal actions inside one infoset")
    return keys


def full_state_semantic_payload(state: HUState) -> dict:
    """Canonical-order semantic snapshot used only to prove transition commutation."""
    def packet(cards: Sequence[Card]) -> list[str]:
        return sorted(str(card) for card in cards)

    return {
        "round": state.round_index,
        "actor": state.actor,
        "opening": [packet(state.plan.opening[0]), packet(state.plan.opening[1])],
        "round_packets": [
            [packet(packets[0]), packet(packets[1])]
            for packets in state.plan.rounds
        ],
        "boards": [
            [sorted(str(card) for card in row) for row in state.boards[player].rows()]
            for player in (0, 1)
        ],
        "discards": [packet(state.discards[0]), packet(state.discards[1])],
        "public_history": [
            [event.round_index, event.player, [list(item) for item in event.placements]]
            for event in state.public_history
        ],
    }
