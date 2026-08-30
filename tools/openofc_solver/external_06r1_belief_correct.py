from __future__ import annotations

"""06R1 belief-correct local resolver research core.

06R0 intentionally preserved the concrete hidden past and only re-sampled
future packets.  That was valid for reuse geometry, not for strategic strength.
This module reconstructs the exact posterior induced by the frozen payoff-blind
06R0 prefix policy without reading the opponent's concrete hidden discard tuple.

Authority: BELIEF_CORRECT_R4_LOCAL_RESOLVING_RESEARCH_ONLY
"""

from dataclasses import dataclass
from itertools import combinations
import math
import random
from typing import Iterable, Iterator, Mapping, Sequence

from engine import Card, full_deck
from external_06p0_conditioned_uct import ConditionedSuitCanonicalISUCT
from external_06r0_conditioned_solver import (
    ConditionedFixtureSpec,
    ConditionedSuitCanonicalOutcomeSamplingMCCFR,
    _prefix_action_index,
)
from external_06s0_suit_automorphism import (
    canonical_information_state,
    canonical_legal_action_keys,
    permute_action_key,
)
from strategic_cfr import (
    DealPlan,
    HUState,
    PublicActionEvent,
    child_state,
    information_state_key,
    legal_action_pairs,
    terminal_utility,
)

AUTHORITY = "BELIEF_CORRECT_R4_LOCAL_RESOLVING_RESEARCH_ONLY"
PacketKey = tuple[int, int]
HiddenHistory = tuple[Card, ...]


@dataclass(frozen=True)
class BeliefSupport:
    fixture_name: str
    fixture_seed: int
    root_information_state_key: str
    root_canonical_information_state_key: str
    root_actor: int
    root_round: int
    opponent: int
    opponent_hidden_event_rounds: tuple[int, ...]
    hidden_histories: tuple[HiddenHistory, ...]
    fixed_known_cards: tuple[Card, ...]

    @property
    def hidden_history_count(self) -> int:
        return len(self.hidden_histories)


@dataclass(frozen=True)
class R4ExactOracle:
    root_action_values: tuple[tuple[str, float], ...]
    best_action_key: str
    best_value: float
    posterior_worlds: int
    p1_information_states_by_root_action: tuple[tuple[str, int], ...]

    def value_map(self) -> dict[str, float]:
        return dict(self.root_action_values)


def _event_cards(event: PublicActionEvent) -> tuple[Card, ...]:
    return tuple(sorted(Card.parse(token) for token, _row in event.placements))


def _event_map(root: HUState) -> dict[tuple[int, int], PublicActionEvent]:
    out: dict[tuple[int, int], PublicActionEvent] = {}
    for event in root.public_history:
        key = (event.round_index, event.player)
        if key in out:
            raise AssertionError("duplicate public action event for round/player")
        out[key] = event
    return out


def _opening_from_public(root: HUState) -> tuple[tuple[Card, ...], tuple[Card, ...]]:
    events = _event_map(root)
    packets: list[tuple[Card, ...]] = []
    for player in (0, 1):
        event = events.get((0, player))
        if event is None:
            raise AssertionError("conditioned root is missing public opening event")
        packet = _event_cards(event)
        if len(packet) != 5:
            raise AssertionError("opening event must expose all five cards")
        packets.append(packet)
    opening = (packets[0], packets[1])
    if len(set(opening[0] + opening[1])) != 10:
        raise AssertionError("public opening contains duplicate physical cards")
    return opening


def _own_packet_assignments(root: HUState) -> dict[PacketKey, tuple[Card, ...]]:
    """Reconstruct only the acting player's legally known packet history."""
    player = root.actor
    events = _event_map(root)
    if len(root.discards[player]) != root.round_index - 1:
        raise AssertionError("own-discard count differs from root round")

    assignments: dict[PacketKey, tuple[Card, ...]] = {}
    for round_index in range(1, root.round_index):
        event = events.get((round_index, player))
        if event is None:
            raise AssertionError("missing acting-player past event")
        placed = _event_cards(event)
        if len(placed) != 2:
            raise AssertionError("pineapple event must expose two placed cards")
        packet = tuple(sorted(placed + (root.discards[player][round_index - 1],)))
        if len(set(packet)) != 3:
            raise AssertionError("reconstructed own packet duplicates a card")
        assignments[(round_index, player)] = packet

    current = tuple(sorted(root.plan.incoming(root.round_index, player)))
    if len(current) != 3 or len(set(current)) != 3:
        raise AssertionError("current own packet must contain three unique cards")
    assignments[(root.round_index, player)] = current
    return assignments


def _opponent_hidden_events(root: HUState) -> tuple[PublicActionEvent, ...]:
    opponent = 1 - root.actor
    rows = [e for e in root.public_history if e.player == opponent and e.round_index >= 1]
    rows.sort(key=lambda e: root.public_history.index(e))
    if any(len(e.placements) != 2 for e in rows):
        raise AssertionError("opponent pineapple event must expose two cards")
    return tuple(rows)


def _fixed_known_cards(
    opening: tuple[tuple[Card, ...], tuple[Card, ...]],
    own_assignments: Mapping[PacketKey, tuple[Card, ...]],
    opponent_events: Sequence[PublicActionEvent],
) -> tuple[Card, ...]:
    known: list[Card] = list(opening[0] + opening[1])
    for packet in own_assignments.values():
        known.extend(packet)
    for event in opponent_events:
        known.extend(_event_cards(event))
    if len(known) != len(set(known)):
        raise AssertionError("fixed root information contains duplicate physical cards")
    return tuple(sorted(known))


def _build_plan(
    *,
    opening: tuple[tuple[Card, ...], tuple[Card, ...]],
    assignments: Mapping[PacketKey, tuple[Card, ...]],
    reserved_cards: Iterable[Card] = (),
    rng: random.Random | None = None,
) -> DealPlan:
    used: list[Card] = list(opening[0] + opening[1])
    for packet in assignments.values():
        used.extend(packet)
    if len(used) != len(set(used)):
        raise AssertionError("partial conditioned deal duplicates a card")

    used_set = set(used)
    reserved = set(reserved_cards) - used_set
    remaining = [c for c in full_deck(2) if c not in used_set and c not in reserved]
    if rng is None:
        remaining.sort()
    else:
        rng.shuffle(remaining)
    cursor = 0
    rounds: list[tuple[tuple[Card, ...], tuple[Card, ...]]] = []
    for round_index in range(1, 5):
        pair: list[tuple[Card, ...]] = []
        for player in (0, 1):
            packet = assignments.get((round_index, player))
            if packet is None:
                packet = tuple(sorted(remaining[cursor:cursor + 3]))
                cursor += 3
            if len(packet) != 3:
                raise AssertionError("conditioned packet must contain three cards")
            pair.append(tuple(packet))
        rounds.append((pair[0], pair[1]))
    plan = DealPlan(opening=opening, rounds=tuple(rounds))  # type: ignore[arg-type]
    dealt = plan.dealt_cards()
    if len(dealt) != 34 or len(set(dealt)) != 34:
        raise AssertionError("conditioned plan must contain 34 unique physical cards")
    return plan


def _replay_prefix(
    plan: DealPlan,
    *,
    spec: ConditionedFixtureSpec,
    expected_history: Sequence[PublicActionEvent],
    event_limit: int | None = None,
) -> HUState | None:
    limit = len(expected_history) if event_limit is None else int(event_limit)
    if not 0 <= limit <= len(expected_history):
        raise ValueError("invalid event limit")
    state = HUState(plan=plan)
    for index in range(limit):
        if state.terminal():
            return None
        pairs = legal_action_pairs(state)
        choice = _prefix_action_index(state, spec.seed, len(pairs))
        state = child_state(state, pairs[choice][1])
        if state.public_history[-1] != expected_history[index]:
            return None
    return state


def build_belief_support(root: HUState, spec: ConditionedFixtureSpec) -> BeliefSupport:
    if (root.round_index, root.actor) != (spec.round_index, spec.actor):
        raise ValueError("root does not match fixture spec")
    if root.round_index < 1:
        raise ValueError("belief support requires R1 or later")

    opening = _opening_from_public(root)
    own_assignments = _own_packet_assignments(root)
    opponent_events = _opponent_hidden_events(root)
    fixed_known = _fixed_known_cards(opening, own_assignments, opponent_events)
    fixed_set = set(fixed_known)
    deck = tuple(full_deck(2))
    opponent = 1 - root.actor

    histories: list[HiddenHistory] = [()]
    for event in opponent_events:
        event_index = root.public_history.index(event)
        placed = _event_cards(event)
        next_histories: list[HiddenHistory] = []
        for history in histories:
            history_set = set(history)
            candidates = [c for c in deck if c not in fixed_set and c not in history_set]
            for candidate in candidates:
                assignments = dict(own_assignments)
                for prior_event, hidden in zip(opponent_events, history):
                    assignments[(prior_event.round_index, opponent)] = tuple(
                        sorted(_event_cards(prior_event) + (hidden,))
                    )
                assignments[(event.round_index, opponent)] = tuple(sorted(placed + (candidate,)))
                try:
                    plan = _build_plan(
                        opening=opening,
                        assignments=assignments,
                        reserved_cards=fixed_set | history_set | {candidate},
                    )
                except AssertionError:
                    continue
                replayed = _replay_prefix(
                    plan,
                    spec=spec,
                    expected_history=root.public_history,
                    event_limit=event_index + 1,
                )
                if replayed is not None:
                    next_histories.append(history + (candidate,))
        histories = sorted(set(next_histories))
        if not histories:
            raise AssertionError(
                f"posterior support became empty at opponent round {event.round_index}"
            )

    valid: list[HiddenHistory] = []
    for history in histories:
        assignments = dict(own_assignments)
        for event, hidden in zip(opponent_events, history):
            assignments[(event.round_index, opponent)] = tuple(
                sorted(_event_cards(event) + (hidden,))
            )
        plan = _build_plan(
            opening=opening,
            assignments=assignments,
            reserved_cards=fixed_set | set(history),
        )
        replayed = _replay_prefix(plan, spec=spec, expected_history=root.public_history)
        if replayed is None:
            continue
        if (replayed.round_index, replayed.actor) != (root.round_index, root.actor):
            continue
        if information_state_key(replayed) != information_state_key(root):
            continue
        if canonical_information_state(replayed)[0] != canonical_information_state(root)[0]:
            continue
        if canonical_legal_action_keys(replayed) != canonical_legal_action_keys(root):
            continue
        valid.append(history)
    if not valid:
        raise AssertionError("no compatible hidden-discard history survived")

    return BeliefSupport(
        fixture_name=spec.name,
        fixture_seed=spec.seed,
        root_information_state_key=information_state_key(root),
        root_canonical_information_state_key=canonical_information_state(root)[0],
        root_actor=root.actor,
        root_round=root.round_index,
        opponent=opponent,
        opponent_hidden_event_rounds=tuple(e.round_index for e in opponent_events),
        hidden_histories=tuple(sorted(set(valid))),
        fixed_known_cards=fixed_known,
    )


def _assignments_for_history(
    root: HUState,
    support: BeliefSupport,
    history: HiddenHistory,
) -> tuple[
    tuple[tuple[Card, ...], tuple[Card, ...]],
    dict[PacketKey, tuple[Card, ...]],
]:
    opening = _opening_from_public(root)
    assignments = _own_packet_assignments(root)
    events = _opponent_hidden_events(root)
    if len(events) != len(history):
        raise ValueError("hidden history length differs from support")
    for event, hidden in zip(events, history):
        assignments[(event.round_index, support.opponent)] = tuple(
            sorted(_event_cards(event) + (hidden,))
        )
    return opening, assignments


def sample_belief_root(
    root: HUState,
    spec: ConditionedFixtureSpec,
    support: BeliefSupport,
    rng: random.Random,
) -> HUState:
    history = support.hidden_histories[rng.randrange(len(support.hidden_histories))]
    opening, assignments = _assignments_for_history(root, support, history)
    plan = _build_plan(
        opening=opening,
        assignments=assignments,
        reserved_cards=set(support.fixed_known_cards) | set(history),
        rng=rng,
    )
    sampled = _replay_prefix(plan, spec=spec, expected_history=root.public_history)
    if sampled is None:
        raise AssertionError("belief sample failed frozen prefix replay")
    if (sampled.round_index, sampled.actor) != (root.round_index, root.actor):
        raise AssertionError("belief sample did not reach root")
    if information_state_key(sampled) != support.root_information_state_key:
        raise AssertionError("belief sample changed raw root information")
    if canonical_information_state(sampled)[0] != support.root_canonical_information_state_key:
        raise AssertionError("belief sample changed canonical root information")
    if canonical_legal_action_keys(sampled) != canonical_legal_action_keys(root):
        raise AssertionError("belief sample changed root legal actions")
    return sampled


def iter_exact_r4_p0_worlds(
    root: HUState,
    spec: ConditionedFixtureSpec,
    support: BeliefSupport,
) -> Iterator[HUState]:
    if (root.round_index, root.actor) != (4, 0):
        raise ValueError("exact world enumeration requires R4 P0")
    if support.opponent != 1:
        raise AssertionError("R4 P0 opponent must be P1")

    for history in support.hidden_histories:
        opening, assignments = _assignments_for_history(root, support, history)
        used = set(opening[0] + opening[1])
        for packet in assignments.values():
            used.update(packet)
        remaining = [c for c in full_deck(2) if c not in used]
        for packet in combinations(remaining, 3):
            world_assignments = dict(assignments)
            world_assignments[(4, 1)] = tuple(sorted(packet))
            plan = _build_plan(opening=opening, assignments=world_assignments)
            sampled = _replay_prefix(plan, spec=spec, expected_history=root.public_history)
            if sampled is None:
                raise AssertionError("exact posterior world failed prefix replay")
            if information_state_key(sampled) != support.root_information_state_key:
                raise AssertionError("exact posterior world changed root information")
            yield sampled


def _canonical_pairs(state: HUState) -> tuple[str, tuple[tuple[str, object], ...]]:
    key, perm = canonical_information_state(state)
    rows = [
        (permute_action_key(raw_key, perm), action)
        for raw_key, action in legal_action_pairs(state)
    ]
    rows.sort(key=lambda row: row[0])
    if len({k for k, _a in rows}) != len(rows):
        raise AssertionError("canonical action collision")
    return key, tuple(rows)


def exact_r4_p0_oracle(
    root: HUState,
    spec: ConditionedFixtureSpec,
    support: BeliefSupport,
) -> R4ExactOracle:
    root_key, root_pairs = _canonical_pairs(root)
    if root_key != support.root_canonical_information_state_key:
        raise AssertionError("oracle root key differs from belief support")

    # Count worlds once without retaining them. The generator is deterministic
    # and is replayed independently for every root action, keeping memory small.
    world_count = sum(1 for _ in iter_exact_r4_p0_worlds(root, spec, support))
    if world_count <= 0:
        raise AssertionError("exact R4 posterior has no worlds")

    values: list[tuple[str, float]] = []
    p1_counts: list[tuple[str, int]] = []
    for canonical_root_action, _root_action in root_pairs:
        grouped: dict[str, dict[str, float]] = {}
        action_sets: dict[str, tuple[str, ...]] = {}
        seen_worlds = 0
        for world in iter_exact_r4_p0_worlds(root, spec, support):
            seen_worlds += 1
            _key, world_pairs = _canonical_pairs(world)
            world_map = dict(world_pairs)
            child = child_state(world, world_map[canonical_root_action])
            if child.terminal() or (child.round_index, child.actor) != (4, 1):
                raise AssertionError("R4 P0 action must lead to R4 P1")
            p1_key = information_state_key(child)
            pairs = tuple(legal_action_pairs(child))
            keys = tuple(key for key, _action in pairs)
            previous = action_sets.get(p1_key)
            if previous is None:
                action_sets[p1_key] = keys
                grouped[p1_key] = {key: 0.0 for key in keys}
            elif previous != keys:
                raise AssertionError("same P1 infoset produced different actions")
            for p1_action_key, p1_action in pairs:
                terminal = child_state(child, p1_action)
                grouped[p1_key][p1_action_key] += terminal_utility(terminal, 0)
        if seen_worlds != world_count:
            raise AssertionError("posterior world enumeration is not deterministic")

        # Every posterior world has equal chance weight. P1 chooses one legal
        # action per raw infoset to minimize conditional expected P0 utility.
        value = sum(min(action_sums.values()) for action_sums in grouped.values()) / world_count
        if not math.isfinite(value):
            raise AssertionError("exact root value is non-finite")
        values.append((canonical_root_action, value))
        p1_counts.append((canonical_root_action, len(grouped)))

    values.sort(key=lambda row: row[0])
    best_value = max(value for _key, value in values)
    best_keys = sorted(key for key, value in values if abs(value - best_value) <= 1e-12)
    return R4ExactOracle(
        root_action_values=tuple(values),
        best_action_key=best_keys[0],
        best_value=best_value,
        posterior_worlds=world_count,
        p1_information_states_by_root_action=tuple(sorted(p1_counts)),
    )


class BeliefCorrectISUCT(ConditionedSuitCanonicalISUCT):
    def __init__(
        self,
        *,
        base_root: HUState,
        spec: ConditionedFixtureSpec,
        support: BeliefSupport,
        exploration: float = 2.0,
        seed: int = 20260830,
    ) -> None:
        super().__init__(
            base_root=base_root,
            exploration=exploration,
            seed=seed,
            resample_future=False,
        )
        self.spec = spec
        self.support = support
        self.belief_rng = random.Random(int(seed) ^ 0x06A1B311)

    def _world(self) -> HUState:
        return sample_belief_root(self.base_root, self.spec, self.support, self.belief_rng)


class BeliefCorrectMCCFR(ConditionedSuitCanonicalOutcomeSamplingMCCFR):
    def __init__(
        self,
        *,
        base_root: HUState,
        spec: ConditionedFixtureSpec,
        support: BeliefSupport,
        epsilon: float = 0.6,
        seed: int = 20260830,
        cfr_plus: bool = True,
    ) -> None:
        super().__init__(
            base_root=base_root,
            resample_future=False,
            epsilon=epsilon,
            seed=seed,
            cfr_plus=cfr_plus,
        )
        self.spec = spec
        self.support = support
        self.belief_rng = random.Random(int(seed) ^ 0x06CF7311)

    def _sample_conditioned_root(self) -> HUState:
        return sample_belief_root(self.base_root, self.spec, self.support, self.belief_rng)


def normalize_policy(rows: Mapping[str, float]) -> dict[str, float]:
    out = {str(key): float(value) for key, value in rows.items()}
    if any(not math.isfinite(v) or v < 0.0 for v in out.values()):
        raise ValueError("policy weights must be finite and non-negative")
    mass = sum(out.values())
    if mass <= 0.0:
        raise ValueError("policy has zero mass")
    return {key: value / mass for key, value in sorted(out.items())}


def exact_policy_regret(policy: Mapping[str, float], oracle: R4ExactOracle) -> float:
    normalized = normalize_policy(policy)
    values = oracle.value_map()
    if set(normalized) != set(values):
        raise ValueError("policy action set differs from oracle")
    expected = sum(normalized[key] * values[key] for key in values)
    regret = oracle.best_value - expected
    if regret < -1e-9:
        raise AssertionError("exact policy regret became materially negative")
    return max(0.0, regret)


def exact_top_action_regret(action_key: str, oracle: R4ExactOracle) -> float:
    values = oracle.value_map()
    if action_key not in values:
        raise ValueError("top action is absent from oracle")
    regret = oracle.best_value - values[action_key]
    if regret < -1e-9:
        raise AssertionError("exact top-action regret became materially negative")
    return max(0.0, regret)
