from __future__ import annotations

"""Practical current-state suit-canonical information-set UCT candidate.

This is intentionally a pragmatic search baseline, not an equilibrium solver.
It borrows the useful *shape* of public OFC ISMCTS implementations -- repeatedly
sample a hidden/future world and back up terminal utility through information-set
nodes -- while keeping DeepOFC's certified information firewall, target rules,
physical 54-card chance model and exact scoring.

The first strategically clean full-game use is R1 P0, where no earlier hidden
discard exists and `resample_unseen_future` is an exact conditional sampler of
not-yet-seen deal packets given the observed root.
"""

from dataclasses import dataclass
import math
import random
from typing import Sequence

from external_06r0_conditioned_solver import resample_unseen_future
from external_06s0_suit_automorphism import (
    canonical_information_state,
    permute_action_key,
)
from strategic_cfr import HUState, child_state, legal_action_pairs, terminal_utility

AUTHORITY = "PRACTICAL_CONDITIONED_IS_UCT_RESEARCH_ONLY"


@dataclass
class ISUCTActionStat:
    visits: int = 0
    value_sum: float = 0.0

    @property
    def mean_value(self) -> float:
        return self.value_sum / self.visits if self.visits else 0.0


class ISUCTNode:
    def __init__(self, action_keys: Sequence[str]) -> None:
        keys = tuple(action_keys)
        if not keys:
            raise ValueError("IS-UCT node requires at least one legal action")
        if len(set(keys)) != len(keys):
            raise ValueError("IS-UCT action keys must be unique")
        self.action_keys = keys
        self.actions = {key: ISUCTActionStat() for key in keys}
        self.visits = 0

    def select(
        self,
        *,
        maximize_root_utility: bool,
        exploration: float,
        rng: random.Random,
    ) -> str:
        unseen = [key for key in self.action_keys if self.actions[key].visits == 0]
        if unseen:
            # Randomize only among genuinely untried actions. Seeded RNG makes
            # the complete search exactly reproducible while avoiding lexical
            # action-order bias in low-budget comparisons.
            return unseen[rng.randrange(len(unseen))]

        log_parent = math.log(max(2, self.visits))
        scored: list[tuple[float, str]] = []
        for key in self.action_keys:
            stat = self.actions[key]
            bonus = exploration * math.sqrt(log_parent / stat.visits)
            if maximize_root_utility:
                score = stat.mean_value + bonus
            else:
                # Lower-confidence-bound selection for the opponent: search
                # aggressively for actions that can reduce root-player utility.
                score = stat.mean_value - bonus
            scored.append((score, key))

        if maximize_root_utility:
            best = max(score for score, _key in scored)
            tied = sorted(key for score, key in scored if score == best)
        else:
            best = min(score for score, _key in scored)
            tied = sorted(key for score, key in scored if score == best)
        return tied[0]

    def observe(self, action_key: str, root_utility: float) -> None:
        stat = self.actions[action_key]
        stat.visits += 1
        stat.value_sum += float(root_utility)
        self.visits += 1


@dataclass(frozen=True)
class RootActionReadout:
    canonical_action_key: str
    visits: int
    mean_root_utility: float


class ConditionedSuitCanonicalISUCT:
    """Information-set UCT rooted at one observed DeepOFC state.

    Every trajectory gets a fresh physically consistent future deal. Decisions
    are keyed only by the certified acting-player infoset, then quotiented by the
    exact global-suit automorphism from 06S0. All backed-up values are expressed
    as utility of the root player; root-player nodes maximize and opponent nodes
    minimize that same zero-sum quantity.
    """

    def __init__(
        self,
        *,
        base_root: HUState,
        exploration: float = 2.0,
        seed: int = 20260830,
        resample_future: bool = True,
    ) -> None:
        if base_root.terminal():
            raise ValueError("IS-UCT requires a non-terminal root")
        if exploration < 0.0 or not math.isfinite(exploration):
            raise ValueError("exploration must be finite and non-negative")
        self.base_root = base_root
        self.root_player = base_root.actor
        self.exploration = float(exploration)
        self.seed = int(seed)
        self.resample_future = bool(resample_future)
        self.rng = random.Random(self.seed)
        self.nodes: dict[str, ISUCTNode] = {}
        self.iterations = 0
        self.terminal_evaluations = 0

        self.root_key, _ = canonical_information_state(base_root)

    def _world(self) -> HUState:
        if self.resample_future:
            return resample_unseen_future(self.base_root, self.rng)
        return self.base_root

    @staticmethod
    def _canonical_pairs(state: HUState) -> tuple[str, list[tuple[str, object]]]:
        info_key, perm = canonical_information_state(state)
        mapped: list[tuple[str, object]] = []
        for raw_key, action in legal_action_pairs(state):
            mapped.append((permute_action_key(raw_key, perm), action))
        mapped.sort(key=lambda row: row[0])
        keys = [key for key, _action in mapped]
        if len(set(keys)) != len(keys):
            raise AssertionError("suit canonicalization collapsed legal actions")
        return info_key, mapped

    def _node(self, key: str, action_keys: Sequence[str]) -> ISUCTNode:
        keys = tuple(action_keys)
        node = self.nodes.get(key)
        if node is None:
            node = ISUCTNode(keys)
            self.nodes[key] = node
        elif node.action_keys != keys:
            raise AssertionError("same canonical infoset produced different action set")
        return node

    def run_iteration(self) -> float:
        state = self._world()
        trace: list[tuple[ISUCTNode, str]] = []

        while not state.terminal():
            key, pairs = self._canonical_pairs(state)
            action_keys = [action_key for action_key, _action in pairs]
            action_by_key = {action_key: action for action_key, action in pairs}
            node = self._node(key, action_keys)
            chosen = node.select(
                maximize_root_utility=state.actor == self.root_player,
                exploration=self.exploration,
                rng=self.rng,
            )
            trace.append((node, chosen))
            state = child_state(state, action_by_key[chosen])

        value = terminal_utility(state, self.root_player)
        self.terminal_evaluations += 1
        for node, action_key in trace:
            node.observe(action_key, value)
        self.iterations += 1
        return value

    def run(self, iterations: int) -> None:
        if iterations <= 0:
            raise ValueError("iterations must be positive")
        for _ in range(iterations):
            self.run_iteration()

    def root_readout(self) -> tuple[RootActionReadout, ...]:
        node = self.nodes.get(self.root_key)
        if node is None:
            return ()
        rows = [
            RootActionReadout(
                canonical_action_key=key,
                visits=node.actions[key].visits,
                mean_root_utility=node.actions[key].mean_value,
            )
            for key in node.action_keys
        ]
        rows.sort(key=lambda row: (-row.visits, -row.mean_root_utility, row.canonical_action_key))
        return tuple(rows)

    def best_root_action_key(self) -> str:
        rows = self.root_readout()
        if not rows:
            raise RuntimeError("IS-UCT has not visited the root")
        return rows[0].canonical_action_key

    def visit_accounting_exact(self) -> bool:
        # Every trajectory visits exactly one root node/action and ends in one
        # terminal evaluation. Deeper node totals can be checked independently.
        root = self.nodes.get(self.root_key)
        return (
            root is not None
            and root.visits == self.iterations
            and sum(stat.visits for stat in root.actions.values()) == self.iterations
            and self.terminal_evaluations == self.iterations
        )
