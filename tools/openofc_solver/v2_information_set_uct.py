from __future__ import annotations

"""Information-set UCT adapter for the certified three-round V2 benchmark.

Authority: research-only candidate for EXT-06R2.

The sampled V2 chance outcome is used only to materialize a physically valid
trajectory. Tree nodes are keyed exclusively by the acting player's
HUPlayerObservation, so sampled hidden/future information is never inserted into
the information-set key.
"""

from dataclasses import dataclass
import math
import random

from deepofc.actions import NormalPlacementAction
from deepofc.hu_three_round_sequential_v2 import HUThreeRoundSequentialSubgameV2
from deepofc.sequential import HUPlayerObservation


@dataclass
class V2ISUCTActionStat:
    visits: int = 0
    value_sum_p0: float = 0.0

    @property
    def mean_p0(self) -> float:
        return self.value_sum_p0 / self.visits if self.visits else 0.0


class V2ISUCTNode:
    def __init__(self, actions: tuple[NormalPlacementAction, ...]) -> None:
        if not actions:
            raise ValueError("V2 ISUCT node requires legal actions")
        if len(set(actions)) != len(actions):
            raise ValueError("V2 ISUCT legal actions are not unique")
        self.actions = tuple(actions)
        self.stats = {action: V2ISUCTActionStat() for action in self.actions}
        self.visits = 0

    def select(
        self,
        *,
        actor: int,
        exploration: float,
        rng: random.Random,
    ) -> NormalPlacementAction:
        unseen = [action for action in self.actions if self.stats[action].visits == 0]
        if unseen:
            unseen.sort(key=lambda action: action.key())
            return unseen[rng.randrange(len(unseen))]

        log_parent = math.log(max(2, self.visits))
        rows: list[tuple[float, NormalPlacementAction]] = []
        for action in self.actions:
            stat = self.stats[action]
            bonus = exploration * math.sqrt(log_parent / stat.visits)
            score = stat.mean_p0 + bonus if actor == 0 else stat.mean_p0 - bonus
            rows.append((score, action))

        if actor == 0:
            best = max(score for score, _action in rows)
        elif actor == 1:
            best = min(score for score, _action in rows)
        else:
            raise AssertionError("V2 ISUCT actor must be P0 or P1")

        tied = sorted(
            (action for score, action in rows if score == best),
            key=lambda action: action.key(),
        )
        return tied[0]

    def observe(self, action: NormalPlacementAction, utility_p0: float) -> None:
        stat = self.stats[action]
        stat.visits += 1
        stat.value_sum_p0 += float(utility_p0)
        self.visits += 1


class V2InformationSetUCT:
    """Seeded information-set UCT self-play/search on V2.

    P0 utility is the single backed-up scalar. P0 information-set nodes maximize
    it and P1 information-set nodes minimize it. Each iteration independently
    samples one of the game's 32 equally likely chance outcomes.
    """

    def __init__(
        self,
        game: HUThreeRoundSequentialSubgameV2,
        *,
        exploration: float = 2.0,
        seed: int = 20260830,
    ) -> None:
        if exploration < 0.0 or not math.isfinite(exploration):
            raise ValueError("exploration must be finite and non-negative")
        self.game = game
        self.exploration = float(exploration)
        self.seed = int(seed)
        self.rng = random.Random(self.seed)
        self.nodes: dict[HUPlayerObservation, V2ISUCTNode] = {}
        self.iterations = 0
        self.terminal_evaluations = 0

    def _node(self, info: HUPlayerObservation) -> V2ISUCTNode:
        actions = tuple(self.game.actions(info))
        node = self.nodes.get(info)
        if node is None:
            node = V2ISUCTNode(actions)
            self.nodes[info] = node
        elif node.actions != actions:
            raise AssertionError("same V2 infoset produced a different legal action tuple")
        return node

    def run_iteration(self) -> float:
        outcome = self.game.outcomes[self.rng.randrange(len(self.game.outcomes))]
        state = self.game.initial_state(outcome)
        trace: list[tuple[V2ISUCTNode, NormalPlacementAction]] = []

        while not state.terminal:
            info = self.game.info(state)
            actor = state.acting_chair
            node = self._node(info)
            action = node.select(
                actor=actor,
                exploration=self.exploration,
                rng=self.rng,
            )
            trace.append((node, action))
            state = self.game.transition(state, action)

        utility_p0 = float(self.game.terminal_u0(state))
        if not math.isfinite(utility_p0):
            raise AssertionError("V2 ISUCT terminal utility is non-finite")
        self.terminal_evaluations += 1
        for node, action in trace:
            node.observe(action, utility_p0)
        self.iterations += 1
        return utility_p0

    def run(self, iterations: int) -> None:
        if iterations < 0:
            raise ValueError("iterations must be non-negative")
        for _ in range(iterations):
            self.run_iteration()

    def visit_profile(self) -> dict[
        HUPlayerObservation, dict[NormalPlacementAction, float]
    ]:
        profile: dict[HUPlayerObservation, dict[NormalPlacementAction, float]] = {}
        for info, node in self.nodes.items():
            total = sum(stat.visits for stat in node.stats.values())
            if total != node.visits:
                raise AssertionError("V2 ISUCT node visit accounting drift")
            if total <= 0:
                continue
            profile[info] = {
                action: node.stats[action].visits / total
                for action in node.actions
            }
        return profile

    def greedy_profile(self) -> dict[
        HUPlayerObservation, dict[NormalPlacementAction, float]
    ]:
        profile: dict[HUPlayerObservation, dict[NormalPlacementAction, float]] = {}
        for info, node in self.nodes.items():
            if node.visits <= 0:
                continue
            max_visits = max(node.stats[action].visits for action in node.actions)
            tied = sorted(
                (action for action in node.actions if node.stats[action].visits == max_visits),
                key=lambda action: action.key(),
            )
            chosen = tied[0]
            profile[info] = {
                action: 1.0 if action == chosen else 0.0
                for action in node.actions
            }
        return profile

    def accounting_exact(self) -> bool:
        if self.terminal_evaluations != self.iterations:
            return False
        for node in self.nodes.values():
            if node.visits != sum(stat.visits for stat in node.stats.values()):
                return False
        return True
