from __future__ import annotations

"""Uniform information-safe determinization for practical online OpenOFC search.

The sampler deliberately ignores strategic action-likelihood signalling.  It
uses only the acting player's legal information plus public history and samples
all hidden cards uniformly without replacement.  It never consults the concrete
opponent discard tuple or unseen future packets stored in the source HUState.
"""

import hashlib
import json
import random
from typing import Mapping

from engine import Card, full_deck
from external_06s0_suit_automorphism import canonical_information_state, canonical_legal_action_keys
from strategic_cfr import DealPlan, HUState, PLAYERS, PublicActionEvent, information_state_key

AUTHORITY = "UNIFORM_INFORMATION_SAFE_BELIEF_V1_RESEARCH_ONLY"
PacketKey = tuple[int, int]


def _events(root: HUState) -> dict[PacketKey, PublicActionEvent]:
    out: dict[PacketKey, PublicActionEvent] = {}
    for event in root.public_history:
        key = (event.round_index, event.player)
        if key in out:
            raise AssertionError("duplicate public event for round/player")
        out[key] = event
    return out


def _placed_cards(event: PublicActionEvent) -> tuple[Card, ...]:
    return tuple(sorted(Card.parse(token) for token, _row in event.placements))


def _opening(events: Mapping[PacketKey, PublicActionEvent]) -> tuple[tuple[Card, ...], tuple[Card, ...]]:
    packets = []
    for player in PLAYERS:
        event = events.get((0, player))
        if event is None:
            raise AssertionError("post-opening state is missing public opening event")
        packet = _placed_cards(event)
        if len(packet) != 5 or len(set(packet)) != 5:
            raise AssertionError("opening event must expose five unique cards")
        packets.append(packet)
    result = (packets[0], packets[1])
    if len(set(result[0] + result[1])) != 10:
        raise AssertionError("opening events contain duplicate physical cards")
    return result


def _opponent_events_that_already_happened(root: HUState) -> tuple[PublicActionEvent, ...]:
    opponent = 1 - root.actor
    rows = [
        event for event in root.public_history
        if event.player == opponent and event.round_index >= 1
    ]
    rows.sort(key=lambda event: (event.round_index, event.player))
    for event in rows:
        if len(event.placements) != 2:
            raise AssertionError("pineapple public event must expose exactly two placed cards")
    expected = root.round_index - 1 + (1 if root.actor == 1 else 0)
    if len(rows) != expected:
        raise AssertionError(
            f"opponent public-action count {len(rows)} differs from expected {expected}"
        )
    return tuple(rows)


def _actor_exact_packets(root: HUState, events: Mapping[PacketKey, PublicActionEvent]) -> dict[PacketKey, tuple[Card, ...]]:
    actor = root.actor
    expected_discards = root.round_index - 1
    if len(root.discards[actor]) != expected_discards:
        raise AssertionError("actor own-discard count differs from round")
    assignments: dict[PacketKey, tuple[Card, ...]] = {}
    for round_index in range(1, root.round_index):
        event = events.get((round_index, actor))
        if event is None:
            raise AssertionError("missing actor past public action")
        placed = _placed_cards(event)
        discard = root.discards[actor][round_index - 1]
        packet = tuple(sorted(placed + (discard,)))
        if len(packet) != 3 or len(set(packet)) != 3:
            raise AssertionError("actor past packet reconstruction is invalid")
        assignments[(round_index, actor)] = packet

    current = tuple(sorted(root.plan.incoming(root.round_index, actor)))
    if len(current) != 3 or len(set(current)) != 3:
        raise AssertionError("actor current packet must contain three unique cards")
    assignments[(root.round_index, actor)] = current
    return assignments


def sample_uniform_information_safe_world(root: HUState, rng: random.Random) -> HUState:
    if root.terminal() or not 1 <= root.round_index <= 4:
        raise ValueError("uniform information-safe sampler requires a non-terminal R1..R4 state")

    events = _events(root)
    opening = _opening(events)
    actor = root.actor
    opponent = 1 - actor
    assignments = _actor_exact_packets(root, events)
    opponent_events = _opponent_events_that_already_happened(root)

    known: set[Card] = set(opening[0] + opening[1])
    for packet in assignments.values():
        if known.intersection(packet):
            raise AssertionError("actor known packet overlaps an already known physical card")
        known.update(packet)
    for event in opponent_events:
        placed = _placed_cards(event)
        if known.intersection(placed):
            raise AssertionError("opponent public placement overlaps an already known physical card")
        known.update(placed)

    deck = tuple(full_deck(2))
    if len(deck) != 54 or len(set(deck)) != 54:
        raise AssertionError("physical deck invariant failed")
    unknown = [card for card in deck if card not in known]
    rng.shuffle(unknown)
    cursor = 0

    sampled_opponent_discards: list[Card] = []
    for event in opponent_events:
        if cursor >= len(unknown):
            raise AssertionError("hidden-discard sampler exhausted deck")
        hidden = unknown[cursor]
        cursor += 1
        placed = _placed_cards(event)
        packet = tuple(sorted(placed + (hidden,)))
        if len(packet) != 3 or len(set(packet)) != 3:
            raise AssertionError("sampled opponent past packet is invalid")
        assignments[(event.round_index, opponent)] = packet
        sampled_opponent_discards.append(hidden)

    rounds: list[tuple[tuple[Card, ...], tuple[Card, ...]]] = []
    for round_index in range(1, 5):
        pair: list[tuple[Card, ...]] = []
        for player in PLAYERS:
            packet = assignments.get((round_index, player))
            if packet is None:
                packet = tuple(sorted(unknown[cursor:cursor + 3]))
                cursor += 3
                if len(packet) != 3:
                    raise AssertionError("future packet sampler exhausted deck")
                assignments[(round_index, player)] = packet
            pair.append(packet)
        rounds.append((pair[0], pair[1]))

    plan = DealPlan(opening=opening, rounds=tuple(rounds))  # type: ignore[arg-type]
    dealt = plan.dealt_cards()
    if len(dealt) != 34 or len(set(dealt)) != 34:
        raise AssertionError("sampled deal plan must contain 34 unique physical cards")

    discards = [(), ()]
    discards[actor] = tuple(root.discards[actor])
    discards[opponent] = tuple(sampled_opponent_discards)
    sampled = HUState(
        plan=plan,
        round_index=root.round_index,
        actor=root.actor,
        boards=root.boards,
        discards=(discards[0], discards[1]),
        public_history=root.public_history,
    )

    if information_state_key(sampled) != information_state_key(root):
        raise AssertionError("uniform sampler changed raw acting-player information")
    if canonical_information_state(sampled)[0] != canonical_information_state(root)[0]:
        raise AssertionError("uniform sampler changed canonical acting-player information")
    if canonical_legal_action_keys(sampled) != canonical_legal_action_keys(root):
        raise AssertionError("uniform sampler changed canonical legal action set")
    return sampled


def plan_digest(state: HUState) -> str:
    payload = {
        "opening": [[str(card) for card in packet] for packet in state.plan.opening],
        "rounds": [
            [[str(card) for card in packet] for packet in pair]
            for pair in state.plan.rounds
        ],
    }
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def information_safe_probe(root: HUState, *, seed: int, samples: int = 32) -> dict:
    if samples <= 0:
        raise ValueError("samples must be positive")
    rng = random.Random(int(seed))
    hashes = []
    for _ in range(samples):
        hashes.append(plan_digest(sample_uniform_information_safe_world(root, rng)))
    return {
        "samples": samples,
        "unique_plans": len(set(hashes)),
        "root_information_sha256": hashlib.sha256(information_state_key(root).encode("utf-8")).hexdigest(),
        "all_unique_physical_plans": len(set(hashes)) > 1,
    }
