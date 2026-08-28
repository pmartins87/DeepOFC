from __future__ import annotations

"""Reduced final-round information-set search for external MCTS research.

This is deliberately narrower than a production ISMCTS implementation.  It
models the P0-first HU R4 decision with an explicit finite support over the
opponent's hidden three-card packet:

- one root information set shared by every hidden packet;
- root actions selected by UCB1;
- one hidden packet sampled per iteration;
- P1's final response solved exactly after P0 acts, because P1 then knows its
  own packet and the public P0 placement;
- root statistics aggregated across hidden worlds rather than stored per
  determinization.

The module also provides an independent exhaustive expectation over the same
finite hidden-packet support.  That makes the search scientifically testable
before any full-tree ISMCTS experiment.

Authority:
  UNIFORM_FINITE_SUPPORT_R4_INFOSET_SEARCH_SCREENING_ONLY

This is NOT a strategic posterior for the full game and cannot certify a real
Bellman route.
"""

from dataclasses import dataclass, replace
import math
import random
from typing import Iterable, Sequence

from engine import Card
from strategic_cfr import (
    DealPlan,
    HUState,
    child_state,
    information_state_key,
    legal_action_pairs,
    terminal_utility,
)

AUTHORITY = "UNIFORM_FINITE_SUPPORT_R4_INFOSET_SEARCH_SCREENING_ONLY"
SCHEMA = "openofc-external-r4-infoset-search-v1"


@dataclass(frozen=True)
class ExactR4SupportResult:
    root_information_state_key: str
    packet_count: int
    action_values: tuple[tuple[str, float], ...]
    best_action_keys: tuple[str, ...]
    best_value: float


@dataclass(frozen=True)
class RootActionStat:
    action_key: str
    visits: int
    mean_value: float


@dataclass(frozen=True)
class R4InfosetSearchResult:
    schema: str
    authority: str
    root_information_state_key: str
    iterations: int
    seed: int
    packet_count: int
    selected_action_key: str
    action_stats: tuple[RootActionStat, ...]
    determinized_reply_cache_entries: int


def _packet_key(packet: Sequence[Card]) -> tuple[str, ...]:
    return tuple(sorted(str(card) for card in packet))


def _validated_support(packets: Iterable[Sequence[Card]]) -> tuple[tuple[Card, ...], ...]:
    frozen = tuple(tuple(packet) for packet in packets)
    if len(frozen) < 2:
        raise ValueError("R4 hidden-packet support requires at least two worlds")
    keys = []
    for packet in frozen:
        if len(packet) != 3:
            raise ValueError("every R4 opponent packet must contain exactly three cards")
        if len(set(packet)) != 3:
            raise ValueError("R4 opponent packet contains duplicate physical cards")
        keys.append(_packet_key(packet))
    if len(keys) != len(set(keys)):
        raise ValueError("R4 hidden-packet support contains duplicate worlds")
    return tuple(tuple(sorted(packet)) for packet in frozen)


def _with_p1_r4_packet(state: HUState, packet: Sequence[Card]) -> HUState:
    if state.round_index != 4 or state.actor != 0 or state.terminal():
        raise ValueError("reduced R4 infoset search requires non-terminal round=4 actor=P0")
    packet = tuple(sorted(packet))
    if len(packet) != 3 or len(set(packet)) != 3:
        raise ValueError("P1 R4 packet must contain three unique cards")
    rounds = list(state.plan.rounds)
    p0_packet, _old_p1_packet = rounds[3]
    rounds[3] = (p0_packet, packet)
    plan = DealPlan(opening=state.plan.opening, rounds=tuple(rounds))  # type: ignore[arg-type]
    return replace(state, plan=plan)


def _assert_one_root_infoset(base_state: HUState, support: tuple[tuple[Card, ...], ...]) -> str:
    keys = tuple(information_state_key(_with_p1_r4_packet(base_state, packet)) for packet in support)
    if len(set(keys)) != 1:
        raise AssertionError("hidden P1 packet changed P0 root information-state key")
    action_sets = tuple(
        tuple(key for key, _action in legal_action_pairs(_with_p1_r4_packet(base_state, packet)))
        for packet in support
    )
    if len(set(action_sets)) != 1:
        raise AssertionError("hidden P1 packet changed P0 legal root action set")
    return keys[0]


def _exact_p1_reply_value(state: HUState, root_action_key: str) -> float:
    root_pairs = dict(legal_action_pairs(state))
    root_action = root_pairs.get(root_action_key)
    if root_action is None:
        raise KeyError(root_action_key)
    after_root = child_state(state, root_action)
    replies = legal_action_pairs(after_root)
    if not replies:
        raise AssertionError("P1 final response set is empty")
    values = []
    for _reply_key, reply_action in replies:
        terminal = child_state(after_root, reply_action)
        if not terminal.terminal():
            raise AssertionError("R4 reply did not reach terminal state")
        values.append(terminal_utility(terminal, 0))
    return min(values)


def exact_uniform_support_values(
    base_state: HUState,
    opponent_packets: Iterable[Sequence[Card]],
) -> ExactR4SupportResult:
    """Enumerate the exact P0 expectation under a finite uniform packet support."""
    support = _validated_support(opponent_packets)
    root_key = _assert_one_root_infoset(base_state, support)
    first_world = _with_p1_r4_packet(base_state, support[0])
    root_actions = tuple(key for key, _action in legal_action_pairs(first_world))
    if not root_actions:
        raise AssertionError("root has no legal actions")

    values = []
    for action_key in root_actions:
        per_world = tuple(
            _exact_p1_reply_value(_with_p1_r4_packet(base_state, packet), action_key)
            for packet in support
        )
        values.append((action_key, sum(per_world) / len(per_world)))

    best_value = max(value for _key, value in values)
    best_keys = tuple(sorted(key for key, value in values if abs(value - best_value) <= 1e-12))
    return ExactR4SupportResult(
        root_information_state_key=root_key,
        packet_count=len(support),
        action_values=tuple(sorted(values)),
        best_action_keys=best_keys,
        best_value=best_value,
    )


def run_uniform_support_root_uct(
    base_state: HUState,
    opponent_packets: Iterable[Sequence[Card]],
    *,
    iterations: int,
    seed: int,
    exploration: float = math.sqrt(2.0),
) -> R4InfosetSearchResult:
    """Run root-level information-set UCT over hidden P1 R4 packets.

    The root node is keyed only by P0's legal information state.  A sampled
    hidden packet is used transiently to evaluate the selected root action and
    is never part of the root-node identity.
    """
    if iterations <= 0:
        raise ValueError("iterations must be positive")
    if exploration < 0.0 or not math.isfinite(exploration):
        raise ValueError("exploration must be finite and non-negative")

    support = _validated_support(opponent_packets)
    root_key = _assert_one_root_infoset(base_state, support)
    first_world = _with_p1_r4_packet(base_state, support[0])
    action_keys = tuple(key for key, _action in legal_action_pairs(first_world))
    visits = {key: 0 for key in action_keys}
    sums = {key: 0.0 for key in action_keys}
    reply_cache: dict[tuple[tuple[str, ...], str], float] = {}
    rng = random.Random(seed)

    for t in range(iterations):
        unvisited = [key for key in action_keys if visits[key] == 0]
        if unvisited:
            action_key = unvisited[0]
        else:
            log_total = math.log(t + 1.0)
            action_key = max(
                action_keys,
                key=lambda key: (
                    sums[key] / visits[key]
                    + exploration * math.sqrt(log_total / visits[key]),
                    -action_keys.index(key),
                ),
            )

        packet = support[rng.randrange(len(support))]
        cache_key = (_packet_key(packet), action_key)
        value = reply_cache.get(cache_key)
        if value is None:
            value = _exact_p1_reply_value(_with_p1_r4_packet(base_state, packet), action_key)
            reply_cache[cache_key] = value
        visits[action_key] += 1
        sums[action_key] += value

    stats = tuple(
        RootActionStat(
            action_key=key,
            visits=visits[key],
            mean_value=sums[key] / visits[key],
        )
        for key in action_keys
    )
    selected = max(
        stats,
        key=lambda stat: (stat.visits, stat.mean_value, -action_keys.index(stat.action_key)),
    ).action_key
    return R4InfosetSearchResult(
        schema=SCHEMA,
        authority=AUTHORITY,
        root_information_state_key=root_key,
        iterations=iterations,
        seed=int(seed),
        packet_count=len(support),
        selected_action_key=selected,
        action_stats=stats,
        determinized_reply_cache_entries=len(reply_cache),
    )


__all__ = [
    "AUTHORITY",
    "SCHEMA",
    "ExactR4SupportResult",
    "RootActionStat",
    "R4InfosetSearchResult",
    "exact_uniform_support_values",
    "run_uniform_support_root_uct",
]
