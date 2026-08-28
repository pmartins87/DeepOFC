from __future__ import annotations

"""05F reduced HU R3->R4 game with deliberate hidden-discard overlap.

Chance selects a complete physical world before R3.  Each decision is then keyed
only by the canonical acting-player information state.  Distinct worlds may
therefore merge after identical public placements even when a private discarded
card differs.

Authority:
  HIDDEN_DISCARD_OVERLAP_REDUCED_GAME_SHADOW_ONLY
"""

from dataclasses import dataclass, replace
import math
import random
from typing import Iterable, Sequence

from engine import Card
from strategic_cfr import DealPlan, HUState, child_state, information_state_key, legal_action_pairs, terminal_utility

AUTHORITY = "HIDDEN_DISCARD_OVERLAP_REDUCED_GAME_SHADOW_ONLY"
SCHEMA = "openofc-external-hidden-discard-overlap-v1"


@dataclass(frozen=True)
class OverlapWorld:
    world_id: str
    p0_r3: tuple[Card, ...]
    p1_r3: tuple[Card, ...]
    p0_r4: tuple[Card, ...]
    p1_r4: tuple[Card, ...]


@dataclass(frozen=True)
class HiddenDiscardCollision:
    hidden_player: int
    observing_player: int
    round_index_after_action: int
    world_a: str
    world_b: str
    public_placements: tuple[tuple[str, int], ...]
    discarded_a: str
    discarded_b: str
    observer_information_state_key: str


@dataclass(frozen=True)
class OverlapNodeStat:
    round_index: int
    actor: int
    information_state_key: str
    visits: int
    compatible_worlds: tuple[str, ...]
    action_visits: tuple[tuple[str, int], ...]


@dataclass(frozen=True)
class OverlapSearchResult:
    schema: str
    authority: str
    iterations: int
    seed: int
    support_worlds: int
    information_states: int
    ambiguous_information_states: int
    ambiguous_nonroot_information_states: int
    max_compatible_worlds: int
    terminal_mean_u0: float
    node_stats: tuple[OverlapNodeStat, ...]


class _Node:
    def __init__(self, action_keys: Sequence[str]) -> None:
        keys = tuple(action_keys)
        if not keys:
            raise ValueError("information-set node requires legal actions")
        self.action_keys = keys
        self.visits = {key: 0 for key in keys}
        self.sums = {key: 0.0 for key in keys}
        self.total = 0

    def select(self, *, maximize: bool, exploration: float) -> str:
        unseen = [key for key in self.action_keys if self.visits[key] == 0]
        if unseen:
            return unseen[0]
        log_total = math.log(self.total + 1.0)
        if maximize:
            return max(
                self.action_keys,
                key=lambda key: (
                    self.sums[key] / self.visits[key]
                    + exploration * math.sqrt(log_total / self.visits[key]),
                    -self.action_keys.index(key),
                ),
            )
        return min(
            self.action_keys,
            key=lambda key: (
                self.sums[key] / self.visits[key]
                - exploration * math.sqrt(log_total / self.visits[key]),
                self.action_keys.index(key),
            ),
        )

    def observe(self, action_key: str, value: float) -> None:
        self.visits[action_key] += 1
        self.sums[action_key] += float(value)
        self.total += 1


def _packet_key(cards: Sequence[Card]) -> tuple[str, ...]:
    return tuple(sorted(str(card) for card in cards))


def validate_worlds(worlds: Iterable[OverlapWorld]) -> tuple[OverlapWorld, ...]:
    support = tuple(worlds)
    if len(support) < 4:
        raise ValueError("05F overlap support requires at least four physical worlds")
    ids = [world.world_id for world in support]
    if any(not world_id for world_id in ids) or len(set(ids)) != len(ids):
        raise ValueError("world IDs must be non-empty and unique")
    fingerprints = []
    for world in support:
        packets = (world.p0_r3, world.p1_r3, world.p0_r4, world.p1_r4)
        if any(len(packet) != 3 for packet in packets):
            raise ValueError("every R3/R4 packet must contain exactly three cards")
        flat = tuple(card for packet in packets for card in packet)
        if len(set(flat)) != 12:
            raise ValueError("one physical world reuses a card across private/future zones")
        fingerprints.append(tuple(_packet_key(packet) for packet in packets))
    if len(set(fingerprints)) != len(fingerprints):
        raise ValueError("support contains duplicate physical worlds")
    if len({_packet_key(world.p0_r3) for world in support}) < 2:
        raise ValueError("support must contain at least two P0 R3 private types")
    if len({_packet_key(world.p1_r3) for world in support}) < 2:
        raise ValueError("support must contain at least two P1 R3 private types")
    return support


def with_overlap_world(base_state: HUState, world: OverlapWorld) -> HUState:
    if base_state.round_index != 3 or base_state.actor != 0 or base_state.terminal():
        raise ValueError("05F base state must be the public state immediately before P0 R3")
    rounds = list(base_state.plan.rounds)
    rounds[2] = (tuple(sorted(world.p0_r3)), tuple(sorted(world.p1_r3)))
    rounds[3] = (tuple(sorted(world.p0_r4)), tuple(sorted(world.p1_r4)))
    plan = DealPlan(opening=base_state.plan.opening, rounds=tuple(rounds))  # type: ignore[arg-type]
    state = replace(base_state, plan=plan)
    dealt = state.plan.dealt_cards()
    if len(dealt) != 34 or len(set(dealt)) != 34:
        raise ValueError("05F world does not form a physically unique 34-card HU deal")
    return state


def _discard_token(state: HUState, action) -> str:
    if action.discard_index is None:
        raise AssertionError("R3 Pineapple action must discard one card")
    incoming = state.plan.incoming(state.round_index, state.actor)
    return str(incoming[action.discard_index])


def _public_signature_after(state: HUState, action) -> tuple[tuple[str, int], ...]:
    child = child_state(state, action)
    return child.public_history[-1].placements


def _common_public_actions(state_a: HUState, state_b: HUState):
    by_sig_a: dict[tuple[tuple[str, int], ...], list[tuple[str, object]]] = {}
    by_sig_b: dict[tuple[tuple[str, int], ...], list[tuple[str, object]]] = {}
    for key, action in legal_action_pairs(state_a):
        by_sig_a.setdefault(_public_signature_after(state_a, action), []).append((key, action))
    for key, action in legal_action_pairs(state_b):
        by_sig_b.setdefault(_public_signature_after(state_b, action), []).append((key, action))
    for signature in sorted(set(by_sig_a) & set(by_sig_b)):
        for pair_a in by_sig_a[signature]:
            for pair_b in by_sig_b[signature]:
                yield signature, pair_a, pair_b


def find_hidden_discard_collisions(
    base_state: HUState,
    worlds: Iterable[OverlapWorld],
) -> tuple[HiddenDiscardCollision, ...]:
    """Find exact same-public-placement/different-private-discard witnesses."""
    support = validate_worlds(worlds)
    witnesses: list[HiddenDiscardCollision] = []

    # P0 hidden discard -> P1 R3 information state.
    for i, world_a in enumerate(support):
        for world_b in support[i + 1:]:
            if _packet_key(world_a.p0_r3) == _packet_key(world_b.p0_r3):
                continue
            if (
                _packet_key(world_a.p1_r3), _packet_key(world_a.p0_r4), _packet_key(world_a.p1_r4)
            ) != (
                _packet_key(world_b.p1_r3), _packet_key(world_b.p0_r4), _packet_key(world_b.p1_r4)
            ):
                continue
            state_a = with_overlap_world(base_state, world_a)
            state_b = with_overlap_world(base_state, world_b)
            for signature, (_key_a, action_a), (_key_b, action_b) in _common_public_actions(state_a, state_b):
                discard_a = _discard_token(state_a, action_a)
                discard_b = _discard_token(state_b, action_b)
                if discard_a == discard_b:
                    continue
                child_a = child_state(state_a, action_a)
                child_b = child_state(state_b, action_b)
                key_a = information_state_key(child_a)
                key_b = information_state_key(child_b)
                if key_a == key_b:
                    witnesses.append(
                        HiddenDiscardCollision(
                            hidden_player=0,
                            observing_player=1,
                            round_index_after_action=3,
                            world_a=world_a.world_id,
                            world_b=world_b.world_id,
                            public_placements=signature,
                            discarded_a=discard_a,
                            discarded_b=discard_b,
                            observer_information_state_key=key_a,
                        )
                    )
                    break
            if witnesses and witnesses[-1].hidden_player == 0:
                break
        if witnesses and witnesses[-1].hidden_player == 0:
            break

    # P1 hidden discard -> P0 R4 information state. Hold P0's complete private
    # information fixed and first force the same deterministic P0 public action.
    for i, world_a in enumerate(support):
        found = False
        for world_b in support[i + 1:]:
            if _packet_key(world_a.p1_r3) == _packet_key(world_b.p1_r3):
                continue
            if (
                _packet_key(world_a.p0_r3), _packet_key(world_a.p0_r4), _packet_key(world_a.p1_r4)
            ) != (
                _packet_key(world_b.p0_r3), _packet_key(world_b.p0_r4), _packet_key(world_b.p1_r4)
            ):
                continue
            root_a = with_overlap_world(base_state, world_a)
            root_b = with_overlap_world(base_state, world_b)
            p0_pairs_a = legal_action_pairs(root_a)
            p0_pairs_b = dict(legal_action_pairs(root_b))
            common_p0_key = next((key for key, _ in p0_pairs_a if key in p0_pairs_b), None)
            if common_p0_key is None:
                continue
            p0_action_a = dict(p0_pairs_a)[common_p0_key]
            p0_action_b = p0_pairs_b[common_p0_key]
            p1_state_a = child_state(root_a, p0_action_a)
            p1_state_b = child_state(root_b, p0_action_b)
            for signature, (_ka, action_a), (_kb, action_b) in _common_public_actions(p1_state_a, p1_state_b):
                discard_a = _discard_token(p1_state_a, action_a)
                discard_b = _discard_token(p1_state_b, action_b)
                if discard_a == discard_b:
                    continue
                p0_r4_a = child_state(p1_state_a, action_a)
                p0_r4_b = child_state(p1_state_b, action_b)
                key_a = information_state_key(p0_r4_a)
                key_b = information_state_key(p0_r4_b)
                if key_a == key_b:
                    witnesses.append(
                        HiddenDiscardCollision(
                            hidden_player=1,
                            observing_player=0,
                            round_index_after_action=4,
                            world_a=world_a.world_id,
                            world_b=world_b.world_id,
                            public_placements=signature,
                            discarded_a=discard_a,
                            discarded_b=discard_b,
                            observer_information_state_key=key_a,
                        )
                    )
                    found = True
                    break
            if found:
                break
        if found:
            break

    return tuple(witnesses)


def run_overlap_infoset_uct(
    base_state: HUState,
    worlds: Iterable[OverlapWorld],
    *,
    iterations: int,
    seed: int,
    exploration: float = 1.0,
) -> OverlapSearchResult:
    if iterations <= 0:
        raise ValueError("iterations must be positive")
    if exploration < 0.0 or not math.isfinite(exploration):
        raise ValueError("exploration must be finite and non-negative")
    support = validate_worlds(worlds)
    rng = random.Random(int(seed))
    nodes: dict[str, _Node] = {}
    meta: dict[str, tuple[int, int]] = {}
    compatible_worlds: dict[str, set[str]] = {}
    terminal_sum = 0.0

    def node_for(state: HUState, world_id: str) -> tuple[str, _Node]:
        info_key = information_state_key(state)
        action_keys = tuple(key for key, _action in legal_action_pairs(state))
        node = nodes.get(info_key)
        if node is None:
            node = _Node(action_keys)
            nodes[info_key] = node
            meta[info_key] = (state.round_index, state.actor)
        else:
            if node.action_keys != action_keys:
                raise AssertionError("same information state produced a different legal action set")
            if meta[info_key] != (state.round_index, state.actor):
                raise AssertionError("information-state key collided across actor/round")
        compatible_worlds.setdefault(info_key, set()).add(world_id)
        return info_key, node

    for _ in range(iterations):
        world = support[rng.randrange(len(support))]
        state = with_overlap_world(base_state, world)
        trace: list[tuple[_Node, str]] = []
        while not state.terminal():
            _key, node = node_for(state, world.world_id)
            action_key = node.select(maximize=state.actor == 0, exploration=exploration)
            action = dict(legal_action_pairs(state))[action_key]
            trace.append((node, action_key))
            state = child_state(state, action)
        if len(trace) != 4:
            raise AssertionError("05F episode must contain P0R3/P1R3/P0R4/P1R4")
        value = float(terminal_utility(state, 0))
        terminal_sum += value
        for node, action_key in trace:
            node.observe(action_key, value)

    stats: list[OverlapNodeStat] = []
    ambiguous = 0
    ambiguous_nonroot = 0
    max_worlds = 0
    for key in sorted(nodes):
        node = nodes[key]
        round_index, actor = meta[key]
        worlds_here = tuple(sorted(compatible_worlds.get(key, ())))
        max_worlds = max(max_worlds, len(worlds_here))
        if len(worlds_here) > 1:
            ambiguous += 1
            if (round_index, actor) != (3, 0):
                ambiguous_nonroot += 1
        stats.append(
            OverlapNodeStat(
                round_index=round_index,
                actor=actor,
                information_state_key=key,
                visits=node.total,
                compatible_worlds=worlds_here,
                action_visits=tuple((action_key, node.visits[action_key]) for action_key in node.action_keys),
            )
        )

    if ambiguous_nonroot <= 0:
        raise RuntimeError("05F search failed to observe any non-root hidden-world ambiguity")
    return OverlapSearchResult(
        schema=SCHEMA,
        authority=AUTHORITY,
        iterations=int(iterations),
        seed=int(seed),
        support_worlds=len(support),
        information_states=len(nodes),
        ambiguous_information_states=ambiguous,
        ambiguous_nonroot_information_states=ambiguous_nonroot,
        max_compatible_worlds=max_worlds,
        terminal_mean_u0=terminal_sum / iterations,
        node_stats=tuple(stats),
    )


__all__ = [
    "AUTHORITY",
    "SCHEMA",
    "OverlapWorld",
    "HiddenDiscardCollision",
    "OverlapNodeStat",
    "OverlapSearchResult",
    "validate_worlds",
    "with_overlap_world",
    "find_hidden_discard_collisions",
    "run_overlap_infoset_uct",
]
