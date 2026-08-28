from __future__ import annotations

"""05C-Q0 two-street R3->R4 information-set tree search.

This is a mechanical shadow experiment only. A complete physical hidden world
is sampled per episode, but every decision node is keyed exclusively by the
canonical information state visible to the acting player.

Authority:
  FINITE_SUPPORT_R3_R4_INFOSET_TREE_SHADOW_ONLY
"""

from dataclasses import dataclass, replace
import math
import random
from typing import Iterable, Sequence

from engine import Card
from strategic_cfr import DealPlan, HUState, child_state, information_state_key, legal_action_pairs, terminal_utility

AUTHORITY = "FINITE_SUPPORT_R3_R4_INFOSET_TREE_SHADOW_ONLY"
SCHEMA = "openofc-external-two-street-infoset-search-v1"


@dataclass(frozen=True)
class TwoStreetWorld:
    world_id: str
    p1_r3: tuple[Card, ...]
    p0_r4: tuple[Card, ...]
    p1_r4: tuple[Card, ...]


@dataclass(frozen=True)
class TreeActionStat:
    action_key: str
    visits: int
    mean_value: float


@dataclass(frozen=True)
class TreeNodeStat:
    round_index: int
    actor: int
    information_state_key: str
    visits: int
    fully_explored: bool
    action_stats: tuple[TreeActionStat, ...]


@dataclass(frozen=True)
class LayerStat:
    round_index: int
    actor: int
    infosets: int
    total_visits: int


@dataclass(frozen=True)
class TwoStreetSearchResult:
    schema: str
    authority: str
    root_information_state_key: str
    iterations: int
    seed: int
    support_worlds: int
    selected_root_action_key: str
    root_action_stats: tuple[TreeActionStat, ...]
    infoset_count: int
    fully_explored_infosets: int
    layer_stats: tuple[LayerStat, ...]
    terminal_episodes: int
    terminal_mean_p0_utility: float
    terminal_min_p0_utility: float
    terminal_max_p0_utility: float
    node_stats: tuple[TreeNodeStat, ...]


class _BanditNode:
    def __init__(self, action_keys: Sequence[str]) -> None:
        keys = tuple(action_keys)
        if not keys:
            raise ValueError("information-set node requires at least one action")
        self.action_keys = keys
        self.visits = {key: 0 for key in keys}
        self.sums = {key: 0.0 for key in keys}
        self.total_visits = 0

    def observe(self, action_key: str, value: float) -> None:
        self.visits[action_key] += 1
        self.sums[action_key] += float(value)
        self.total_visits += 1

    def _mean(self, key: str) -> float:
        n = self.visits[key]
        if n <= 0:
            raise ValueError("mean requested for unvisited action")
        return self.sums[key] / n

    def select(self, *, maximize: bool, exploration: float) -> str:
        unvisited = [key for key in self.action_keys if self.visits[key] == 0]
        if unvisited:
            return unvisited[0]
        log_total = math.log(self.total_visits + 1.0)
        if maximize:
            return max(
                self.action_keys,
                key=lambda key: (
                    self._mean(key) + exploration * math.sqrt(log_total / self.visits[key]),
                    -self.action_keys.index(key),
                ),
            )
        return min(
            self.action_keys,
            key=lambda key: (
                self._mean(key) - exploration * math.sqrt(log_total / self.visits[key]),
                self.action_keys.index(key),
            ),
        )

    def stats(self) -> tuple[TreeActionStat, ...]:
        return tuple(
            TreeActionStat(
                action_key=key,
                visits=self.visits[key],
                mean_value=(self.sums[key] / self.visits[key]) if self.visits[key] else 0.0,
            )
            for key in self.action_keys
        )

    def fully_explored(self) -> bool:
        return all(self.visits[key] > 0 for key in self.action_keys)


def _packet_key(packet: Sequence[Card]) -> tuple[str, ...]:
    return tuple(sorted(str(card) for card in packet))


def _validated_worlds(worlds: Iterable[TwoStreetWorld]) -> tuple[TwoStreetWorld, ...]:
    frozen = tuple(worlds)
    if len(frozen) < 2:
        raise ValueError("two-street support requires at least two physical worlds")
    ids = [world.world_id for world in frozen]
    if any(not world_id for world_id in ids) or len(set(ids)) != len(ids):
        raise ValueError("two-street world IDs must be non-empty and unique")
    fingerprints = []
    for world in frozen:
        packets = (world.p1_r3, world.p0_r4, world.p1_r4)
        if any(len(packet) != 3 for packet in packets):
            raise ValueError("every hidden/current/future packet must contain exactly three cards")
        flat = tuple(card for packet in packets for card in packet)
        if len(set(flat)) != 9:
            raise ValueError("two-street world reuses a physical card across hidden zones")
        fingerprints.append(tuple(_packet_key(packet) for packet in packets))
    if len(set(fingerprints)) != len(fingerprints):
        raise ValueError("two-street support contains duplicate physical worlds")
    return frozen


def _with_world(base_state: HUState, world: TwoStreetWorld) -> HUState:
    if base_state.round_index != 3 or base_state.actor != 0 or base_state.terminal():
        raise ValueError("05C requires a non-terminal round=3 actor=P0 root")
    rounds = list(base_state.plan.rounds)
    p0_r3, _old_p1_r3 = rounds[2]
    rounds[2] = (p0_r3, tuple(sorted(world.p1_r3)))
    rounds[3] = (tuple(sorted(world.p0_r4)), tuple(sorted(world.p1_r4)))
    plan = DealPlan(opening=base_state.plan.opening, rounds=tuple(rounds))  # type: ignore[arg-type]
    state = replace(base_state, plan=plan)
    dealt = state.plan.dealt_cards()
    if len(dealt) != 34 or len(set(dealt)) != 34:
        raise ValueError("two-street world is not a physically unique 34-card HU deal")
    return state


def _assert_root_isolation(base_state: HUState, support: tuple[TwoStreetWorld, ...]) -> str:
    keys = []
    actions = []
    for world in support:
        state = _with_world(base_state, world)
        keys.append(information_state_key(state))
        actions.append(tuple(key for key, _action in legal_action_pairs(state)))
    if len(set(keys)) != 1:
        raise AssertionError("hidden two-street world changed P0 R3 root information state")
    if len(set(actions)) != 1:
        raise AssertionError("hidden two-street world changed P0 R3 legal action set")
    return keys[0]


def run_two_street_infoset_uct(
    base_state: HUState,
    worlds: Iterable[TwoStreetWorld],
    *,
    iterations: int,
    seed: int,
    exploration: float = 1.0,
) -> TwoStreetSearchResult:
    """Run the 05C-Q0 four-decision information-set tree shadow search."""
    if iterations <= 0:
        raise ValueError("iterations must be positive")
    if exploration < 0.0 or not math.isfinite(exploration):
        raise ValueError("exploration must be finite and non-negative")
    support = _validated_worlds(worlds)
    root_key = _assert_root_isolation(base_state, support)
    first_root = _with_world(base_state, support[0])
    root_action_keys = tuple(key for key, _action in legal_action_pairs(first_root))

    nodes: dict[str, _BanditNode] = {root_key: _BanditNode(root_action_keys)}
    meta: dict[str, tuple[int, int]] = {root_key: (3, 0)}
    rng = random.Random(int(seed))
    terminal_values: list[float] = []

    def node_for(state: HUState) -> tuple[str, _BanditNode]:
        key = information_state_key(state)
        pairs = legal_action_pairs(state)
        action_keys = tuple(action_key for action_key, _action in pairs)
        node = nodes.get(key)
        if node is None:
            node = _BanditNode(action_keys)
            nodes[key] = node
            meta[key] = (state.round_index, state.actor)
        else:
            if node.action_keys != action_keys:
                raise AssertionError("same information state produced a different legal action set")
            if meta[key] != (state.round_index, state.actor):
                raise AssertionError("information-state key collided across actor/round")
        return key, node

    for _ in range(iterations):
        # Root decision comes before the hidden-world draw. This makes the
        # determinization firewall mechanically explicit at the first node.
        root = nodes[root_key]
        root_action_key = root.select(maximize=True, exploration=exploration)
        world = support[rng.randrange(len(support))]
        state = _with_world(base_state, world)
        if information_state_key(state) != root_key:
            raise AssertionError("sampled world leaked into root information state")

        trace: list[tuple[_BanditNode, str]] = []
        root_action = dict(legal_action_pairs(state))[root_action_key]
        trace.append((root, root_action_key))
        state = child_state(state, root_action)

        while not state.terminal():
            _key, node = node_for(state)
            maximize = state.actor == 0
            action_key = node.select(maximize=maximize, exploration=exploration)
            action = dict(legal_action_pairs(state))[action_key]
            trace.append((node, action_key))
            state = child_state(state, action)

        if len(trace) != 4:
            raise AssertionError("05C episode must contain exactly P0R3/P1R3/P0R4/P1R4 decisions")
        value = terminal_utility(state, 0)
        terminal_values.append(value)
        for node, action_key in trace:
            node.observe(action_key, value)

    root_stats = nodes[root_key].stats()
    selected = max(
        root_stats,
        key=lambda stat: (
            stat.visits,
            stat.mean_value,
            -root_action_keys.index(stat.action_key),
        ),
    ).action_key

    node_stats = []
    layer_acc: dict[tuple[int, int], list[int]] = {}
    for key in sorted(nodes):
        node = nodes[key]
        round_index, actor = meta[key]
        node_stats.append(
            TreeNodeStat(
                round_index=round_index,
                actor=actor,
                information_state_key=key,
                visits=node.total_visits,
                fully_explored=node.fully_explored(),
                action_stats=node.stats(),
            )
        )
        bucket = layer_acc.setdefault((round_index, actor), [0, 0])
        bucket[0] += 1
        bucket[1] += node.total_visits

    layer_stats = tuple(
        LayerStat(round_index=r, actor=a, infosets=counts[0], total_visits=counts[1])
        for (r, a), counts in sorted(layer_acc.items())
    )
    if not terminal_values:
        raise AssertionError("05C produced no terminal episodes")
    return TwoStreetSearchResult(
        schema=SCHEMA,
        authority=AUTHORITY,
        root_information_state_key=root_key,
        iterations=int(iterations),
        seed=int(seed),
        support_worlds=len(support),
        selected_root_action_key=selected,
        root_action_stats=root_stats,
        infoset_count=len(nodes),
        fully_explored_infosets=sum(1 for node in nodes.values() if node.fully_explored()),
        layer_stats=layer_stats,
        terminal_episodes=len(terminal_values),
        terminal_mean_p0_utility=sum(terminal_values) / len(terminal_values),
        terminal_min_p0_utility=min(terminal_values),
        terminal_max_p0_utility=max(terminal_values),
        node_stats=tuple(node_stats),
    )


__all__ = [
    "AUTHORITY",
    "SCHEMA",
    "TwoStreetWorld",
    "TreeActionStat",
    "TreeNodeStat",
    "LayerStat",
    "TwoStreetSearchResult",
    "run_two_street_infoset_uct",
]
