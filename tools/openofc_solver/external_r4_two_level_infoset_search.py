from __future__ import annotations

"""Two-level final-round information-set UCT for external-search research.

05A proved that a hidden-packet-blind P0 root can converge on the exact finite-
support optimum when P1's reply is solved by an exact shortcut.  05B removes
that shortcut.  Both decisions are now explicit search nodes:

* P0 root: one information set shared across every hidden P1 R4 packet;
* chance: sample one hidden packet only after P0's action has been selected;
* P1 node: keyed by P1's legal information state, which includes P1's own
  current packet and the public P0 placement;
* P0 selects with UCB1 (maximize P0 utility);
* P1 selects with the zero-sum mirrored confidence rule (minimize P0 utility);
* terminal utility remains the exact canonical HU scorer.

This is still a finite-support R4 experiment, not a posterior conditioned on
strategic earlier-round signalling and not a full-game ISMCTS solver.

Authority:
  UNIFORM_FINITE_SUPPORT_R4_TWO_LEVEL_INFOSET_UCT_SCREENING_ONLY
"""

from dataclasses import dataclass
import math
import random
from typing import Iterable, Sequence

from engine import Card
from external_r4_infoset_search import (
    _assert_one_root_infoset,
    _validated_support,
    _with_p1_r4_packet,
)
from strategic_cfr import (
    HUState,
    child_state,
    information_state_key,
    legal_action_pairs,
    terminal_utility,
)

AUTHORITY = "UNIFORM_FINITE_SUPPORT_R4_TWO_LEVEL_INFOSET_UCT_SCREENING_ONLY"
SCHEMA = "openofc-external-r4-two-level-infoset-search-v1"


@dataclass(frozen=True)
class TreeActionStat:
    action_key: str
    visits: int
    mean_value: float


@dataclass(frozen=True)
class MinInfoSetStat:
    information_state_key: str
    visits: int
    action_stats: tuple[TreeActionStat, ...]
    fully_explored: bool
    empirical_min_action_key: str
    empirical_min_value: float


@dataclass(frozen=True)
class TwoLevelR4SearchResult:
    schema: str
    authority: str
    root_information_state_key: str
    iterations: int
    seed: int
    packet_count: int
    selected_action_key: str
    root_action_stats: tuple[TreeActionStat, ...]
    p1_infoset_count: int
    p1_fully_explored_infosets: int
    selected_support_worlds_seen: int
    selected_support_worlds_fully_explored: int
    selected_support_backup_complete: bool
    selected_support_backed_value: float | None
    p1_infoset_stats: tuple[MinInfoSetStat, ...]


class _BanditNode:
    def __init__(self, action_keys: Sequence[str]) -> None:
        keys = tuple(action_keys)
        if not keys:
            raise ValueError("bandit node requires at least one action")
        self.action_keys = keys
        self.visits = {key: 0 for key in keys}
        self.sums = {key: 0.0 for key in keys}
        self.total_visits = 0

    def observe(self, action_key: str, value: float) -> None:
        if action_key not in self.visits:
            raise KeyError(action_key)
        self.visits[action_key] += 1
        self.sums[action_key] += float(value)
        self.total_visits += 1

    def mean(self, action_key: str) -> float:
        n = self.visits[action_key]
        if n <= 0:
            raise ValueError("mean requested for unvisited action")
        return self.sums[action_key] / n

    def select_max(self, exploration: float) -> str:
        unvisited = [key for key in self.action_keys if self.visits[key] == 0]
        if unvisited:
            return unvisited[0]
        log_total = math.log(self.total_visits + 1.0)
        return max(
            self.action_keys,
            key=lambda key: (
                self.mean(key)
                + exploration * math.sqrt(log_total / self.visits[key]),
                -self.action_keys.index(key),
            ),
        )

    def select_min(self, exploration: float) -> str:
        unvisited = [key for key in self.action_keys if self.visits[key] == 0]
        if unvisited:
            return unvisited[0]
        log_total = math.log(self.total_visits + 1.0)
        # P1 minimizes P0 utility.  The mirrored UCB rule is a lower-confidence
        # bound: actions with low means or high uncertainty are explored first.
        return min(
            self.action_keys,
            key=lambda key: (
                self.mean(key)
                - exploration * math.sqrt(log_total / self.visits[key]),
                self.action_keys.index(key),
            ),
        )

    def stats(self) -> tuple[TreeActionStat, ...]:
        out = []
        for key in self.action_keys:
            n = self.visits[key]
            out.append(
                TreeActionStat(
                    action_key=key,
                    visits=n,
                    mean_value=(self.sums[key] / n) if n else 0.0,
                )
            )
        return tuple(out)

    def fully_explored(self) -> bool:
        return all(self.visits[key] > 0 for key in self.action_keys)

    def empirical_min(self) -> tuple[str, float]:
        if not self.fully_explored():
            raise ValueError("empirical minimum requires every action to be visited")
        key = min(
            self.action_keys,
            key=lambda action_key: (self.mean(action_key), self.action_keys.index(action_key)),
        )
        return key, self.mean(key)


def _root_action(state: HUState, action_key: str):
    action = dict(legal_action_pairs(state)).get(action_key)
    if action is None:
        raise KeyError(action_key)
    return action


def _p1_state_for(
    base_state: HUState,
    packet: Sequence[Card],
    root_action_key: str,
) -> HUState:
    world = _with_p1_r4_packet(base_state, packet)
    after_root = child_state(world, _root_action(world, root_action_key))
    if after_root.round_index != 4 or after_root.actor != 1 or after_root.terminal():
        raise AssertionError("P0 R4 action did not produce the expected P1 information set")
    return after_root


def run_uniform_support_two_level_uct(
    base_state: HUState,
    opponent_packets: Iterable[Sequence[Card]],
    *,
    iterations: int,
    seed: int,
    root_exploration: float = 1.0,
    reply_exploration: float = 1.0,
) -> TwoLevelR4SearchResult:
    """Search both R4 decision layers without an exact P1 reply shortcut."""
    if iterations <= 0:
        raise ValueError("iterations must be positive")
    for label, value in (
        ("root_exploration", root_exploration),
        ("reply_exploration", reply_exploration),
    ):
        if value < 0.0 or not math.isfinite(value):
            raise ValueError(f"{label} must be finite and non-negative")

    support = _validated_support(opponent_packets)
    root_key = _assert_one_root_infoset(base_state, support)
    first_world = _with_p1_r4_packet(base_state, support[0])
    root_action_keys = tuple(key for key, _action in legal_action_pairs(first_world))
    root = _BanditNode(root_action_keys)
    p1_nodes: dict[str, _BanditNode] = {}
    rng = random.Random(int(seed))

    for _ in range(iterations):
        # Crucial authority firewall: choose P0's action BEFORE drawing the hidden
        # P1 packet, so the root policy cannot condition on determinization data.
        root_action_key = root.select_max(root_exploration)
        packet = support[rng.randrange(len(support))]
        p1_state = _p1_state_for(base_state, packet, root_action_key)
        p1_key = information_state_key(p1_state)
        p1_pairs = legal_action_pairs(p1_state)
        p1_action_keys = tuple(key for key, _action in p1_pairs)
        node = p1_nodes.get(p1_key)
        if node is None:
            node = _BanditNode(p1_action_keys)
            p1_nodes[p1_key] = node
        elif node.action_keys != p1_action_keys:
            raise AssertionError("same P1 information state produced different legal actions")

        p1_action_key = node.select_min(reply_exploration)
        p1_action = dict(p1_pairs)[p1_action_key]
        terminal = child_state(p1_state, p1_action)
        if not terminal.terminal():
            raise AssertionError("P1 R4 action did not reach terminal state")
        value = terminal_utility(terminal, 0)
        node.observe(p1_action_key, value)
        root.observe(root_action_key, value)

    root_stats = root.stats()
    selected = max(
        root_stats,
        key=lambda stat: (
            stat.visits,
            stat.mean_value,
            -root_action_keys.index(stat.action_key),
        ),
    ).action_key

    p1_summaries = []
    for key in sorted(p1_nodes):
        node = p1_nodes[key]
        fully = node.fully_explored()
        if fully:
            min_key, min_value = node.empirical_min()
        else:
            visited = [k for k in node.action_keys if node.visits[k] > 0]
            min_key = min(
                visited,
                key=lambda action_key: (node.mean(action_key), node.action_keys.index(action_key)),
            )
            min_value = node.mean(min_key)
        p1_summaries.append(
            MinInfoSetStat(
                information_state_key=key,
                visits=node.total_visits,
                action_stats=node.stats(),
                fully_explored=fully,
                empirical_min_action_key=min_key,
                empirical_min_value=min_value,
            )
        )

    selected_world_values = []
    selected_worlds_seen = 0
    selected_worlds_complete = 0
    for packet in support:
        p1_state = _p1_state_for(base_state, packet, selected)
        node = p1_nodes.get(information_state_key(p1_state))
        if node is None:
            continue
        selected_worlds_seen += 1
        if node.fully_explored():
            selected_worlds_complete += 1
            _min_key, min_value = node.empirical_min()
            selected_world_values.append(min_value)

    backup_complete = selected_worlds_complete == len(support)
    backed_value = (
        sum(selected_world_values) / len(selected_world_values)
        if backup_complete
        else None
    )

    return TwoLevelR4SearchResult(
        schema=SCHEMA,
        authority=AUTHORITY,
        root_information_state_key=root_key,
        iterations=int(iterations),
        seed=int(seed),
        packet_count=len(support),
        selected_action_key=selected,
        root_action_stats=root_stats,
        p1_infoset_count=len(p1_nodes),
        p1_fully_explored_infosets=sum(1 for node in p1_nodes.values() if node.fully_explored()),
        selected_support_worlds_seen=selected_worlds_seen,
        selected_support_worlds_fully_explored=selected_worlds_complete,
        selected_support_backup_complete=backup_complete,
        selected_support_backed_value=backed_value,
        p1_infoset_stats=tuple(p1_summaries),
    )


__all__ = [
    "AUTHORITY",
    "SCHEMA",
    "TreeActionStat",
    "MinInfoSetStat",
    "TwoLevelR4SearchResult",
    "run_uniform_support_two_level_uct",
]
