from __future__ import annotations

"""06R1 belief-correct local resolver research core.

The 06R0 sampler intentionally kept the concrete hidden past and only changed
future packets.  That was sufficient for a reuse-geometry gate but is not a
posterior.  This module reconstructs the exact posterior induced by the frozen
payoff-blind 06R0 prefix policy, without consulting the opponent's concrete
hidden discard realization, and provides belief-correct IS-UCT / MCCFR roots.

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

PacketKey = tuple[int, int]  # (round_index 1..4, player 0/1)
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
    packets = []
    for player in (0, 1):
        event = events.get((0, player))
        if event is None:
            raise AssertionError("conditioned root is missing public opening event")
        packet = _event_cards(event)
        if len(packet) != 5:
            raise AssertionError("opening public event must expose all five cards")
        packets.append(packet)
    opening = (packets[0], packets[1])
    if len(set(opening[0] + opening[1])) != 10:
        raise AssertionError("public opening contains duplicate physical cards")
    return opening


def _own_packet_assignments(root: HUState) -> dict[PacketKey, tuple[Card, ...]]:
    """Reconstruct the acting player's past/current packets from legal information.

    Past packets are public placed cards plus the actor's own private discard.
    The current packet is directly part of the acting player's information state.
    No opponent hidden discard is read here.
    """
    player = root.actor
    events = _event_map(root)
    expected_own_discards = root.round_index - 1
    if len(root.discards[player]) != expected_own_discards:
        raise AssertionError("acting-player own-discard count differs from root round")

    assignments: dict[PacketKey, tuple[Card, ...]] = {}
    for round_index in range(1, root.round_index):
        event = events.get((round_index, player))
        if event is None:
            raise AssertionError("missing acting-player past public event")
        placed = _event_cards(event)
        if len(placed) != 2:
            raise AssertionError("pineapple public event must expose exactly two cards")
        packet = tuple(sorted(placed + (root.discards[player][round_index - 1],)))
        if len(set(packet)) != 3:
            raise AssertionError("acting-player reconstructed packet duplicates a card")
        assignments[(round_index, player)] = packet

    current = tuple(root.plan.incoming(root.round_index, player))
    if len(current) != 3 or len(set(current)) != 3:
        raise AssertionError("acting-player current packet must contain three unique cards")
    assignments[(root.round_index, player)] = tuple(sorted(current))
    return assignments


def _opponent_hidden_events(root: HUState) -> tuple[PublicActionEvent, ...]:
    opponent = 1 - root.actor
    rows = [
        event
        for event in root.public_history
        if event.player == opponent and event.round_index >= 1
    ]
    rows.sort(key=lambda event: root.public_history.index(event))
    for event in rows:
        if len(event.placements) != 2:
            raise AssertionError("opponent pineapple public event must expose two cards")
    return tuple(rows)


def _fixed_known_cards(
    root: HUState,
    opening: tuple[tuple[Card, ...], tuple[Card, ...]],
    own_assignments: Mapping[PacketKey, tuple[Card, ...]],
    opponent_events: Sequence[PublicActionEvent],
) -> tuple[Card, ...]:
    known: list[Card] = list(opening[0] + opening[1])
    for packet in own_assignments.values():
        known.extend(packet)
    for event in opponent_events:
        known.extend(_event_cards(event))
    unique = tuple(sorted(set(known)))
    if len(unique) != len(known):
        # A card can appear in an own packet both as a past public placement and
        # in the opening only if the root itself is corrupt.  Fail closed.
        raise AssertionError("fixed legal root information contains duplicate physical cards")
    return unique


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
        raise AssertionError("partial conditioned deal has duplicate physical cards")

    reserved = set(reserved_cards) - set(used)
    remaining = [card for card in full_deck(2) if card not in set(used) and card not in reserved]
    if rng is None:
        remaining.sort()
    else:
        rng.shuffle(remaining)
    cursor = 0

    rounds: list[tuple[tuple[Card, ...], tuple[Card, ...]]] = []
    for round_index in range(1, 5):
        packets: list[tuple[Card, ...]] = []
        for player in (0, 1):
            packet = assignments.get((round_index, player))
            if packet is None:
                packet = tuple(sorted(remaining[cursor:cursor + 3]))
                cursor += 3
                if len(packet) != 3:
                    raise AssertionError("not enough filler cards for conditioned plan")
            packets.append(tuple(packet))
        rounds.append((packets[0], packets[1]))
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
        chosen_index = _prefix_action_index(state, spec.seed, len(pairs))
        state = child_state(state, pairs[chosen_index][1])
        if state.public_history[-1] != expected_history[index]:
            return None
    return state


def build_belief_support(root: HUState, spec: ConditionedFixtureSpec) -> BeliefSupport:
    if (root.round_index, root.actor) != (spec.round_index, spec.actor):
        raise ValueError("root does not match fixture spec")
    if root.round_index < 1:
        raise ValueError("06R1 belief support requires a post-opening root")

    opening = _opening_from_public(root)
    own_assignments = _own_packet_assignments(root)
    opponent_events = _opponent_hidden_events(root)
    fixed_known = _fixed_known_cards(root, opening, own_assignments, opponent_events)
    deck = tuple(full_deck(2))

    histories: list[tuple[Card, ...]] = [()]
    opponent = 1 - root.actor
    for event in opponent_events:
        event_index = root.public_history.index(event)
        placed = _event_cards(event)
        next_histories: list[tuple[Card, ...]] = []
        for history in histories:
            already_hidden = set(history)
            candidates = [
                card for card in deck
                if card not in set(fixed_known) and card not in already_hidden
            ]
            for candidate in candidates:
                packet = tuple(sorted(placed + (candidate,)))
                if len(set(packet)) != 3:
                    continue
                assignments = dict(own_assignments)
                for prior_event, hidden_card in zip(opponent_events, history):
                    assignments[(prior_event.round_index, opponent)] = tuple(
                        sorted(_event_cards(prior_event) + (hidden_card,))
                    )
                assignments[(event.round_index, opponent)] = packet
                reserved = set(fixed_known) | already_hidden | {candidate}
                try:
                    plan = _build_plan(
                        opening=opening,
                        assignments=assignments,
                        reserved_cards=reserved,
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

    # Full-history validation must use only reconstructed legal information and
    # candidate hidden cards.  The original opponent discard tuple is never read.
    valid_histories: list[HiddenHistory] = []
    for history in histories:
        assignments = dict(own_assignments)
        for event, hidden_card in zip(opponent_events, history):
            assignments[(event.round_index, opponent)] = tuple(
                sorted(_event_cards(event) + (hidden_card,))
            )
        plan = _build_plan(
            opening=opening,
            assignments=assignments,
            reserved_cards=set(fixed_known) | set(history),
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
        valid_histories.append(history)

    if not valid_histories:
        raise AssertionError("no full compatible hidden-discard history survived")

    return BeliefSupport(
        fixture_name=spec.name,
        fixture_seed=spec.seed,
        root_information_state_key=information_state_key(root),
        root_canonical_information_state_key=canonical_information_state(root)[0],
        root_actor=root.actor,
        root_round=root.round_index,
        opponent=opponent,
        opponent_hidden_event_rounds=tuple(event.round_index for event in opponent_events),
        hidden_histories=tuple(sorted(set(valid_histories))),
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
    for event, hidden_card in zip(events, history):
        assignments[(event.round_index, support.opponent)] = tuple(
            sorted(_event_cards(event) + (hidden_card,))
        )
    return opening, assignments


def sample_belief_root(
    root: HUState,
    spec: ConditionedFixtureSpec,
    support: BeliefSupport,
    rng: random.Random,
) -> HUState:
    if not support.hidden_histories:
        raise ValueError("belief support is empty")
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
        raise AssertionError("sampled belief plan failed frozen prefix replay")
    if (sampled.round_index, sampled.actor) != (root.round_index, root.actor):
        raise AssertionError("sampled belief world did not reach the root")
    if information_state_key(sampled) != support.root_information_state_key:
        raise AssertionError("belief sample changed raw root information")
    if canonical_information_state(sampled)[0] != support.root_canonical_information_state_key:
        raise AssertionError("belief sample changed canonical root information")
    if canonical_legal_action_keys(sampled) != canonical_legal_action_keys(root):
        raise AssertionError("belief sample changed canonical legal root actions")
    return sampled


def iter_exact_r4_p0_worlds(
    root: HUState,
    spec: ConditionedFixtureSpec,
    support: BeliefSupport,
) -> Iterator[HUState]:
    if root.round_index != 4 or root.actor != 0:
        raise ValueError("exact 06R1 world enumeration currently requires R4 P0")
    if support.opponent != 1:
        raise AssertionError("R4 P0 opponent must be P1")

    for history in support.hidden_histories:
        opening, assignments = _assignments_for_history(root, support, history)
        used = set(opening[0] + opening[1])
        for packet in assignments.values():
            used.update(packet)
        remaining = [card for card in full_deck(2) if card not in used]
        # At R4 P0 the only not-yet-fixed packet is P1's current R4 packet.
        for packet in combinations(remaining, 3):
            world_assignments = dict(assignments)
            world_assignments[(4, 1)] = tuple(sorted(packet))
            plan = _build_plan(opening=opening, assignments=world_assignments)
            sampled = _replay_prefix(plan, spec=spec, expected_history=root.public_history)
            if sampled is None:
                raise AssertionError("exact R4 posterior world failed prefix replay")
            if information_state_key(sampled) != support.root_information_state_key:
                raise AssertionError("exact R4 posterior world changed root information")
            yield sampled


def _canonical_root_pairs(state: HUState) -> tuple[str, tuple[tuple[str, object], ...]]:
    key, perm = canonical_information_state(state)
    rows = [
        (permute_action_key(raw_key, perm), action)
        for raw_key, action in legal_action_pairs(state)
    ]
    rows.sort(key=lambda row: row[0])
    if len({key for key, _action in rows}) != len(rows):
        raise AssertionError("canonical root action collision")
    return key, tuple(rows)


def exact_r4_p0_oracle(
    root: HUState,
    spec: ConditionedFixtureSpec,
    support: BeliefSupport,
) -> R4ExactOracle:
    root_key, root_pairs = _canonical_root_pairs(root)
    if root_key != support.root_canonical_information_state_key:
        raise AssertionError("oracle root canonical key differs from belief support")

    worlds = tuple(iter_exact_r4_p0_worlds(root, spec, support))
    if not worlds:
        raise AssertionError("exact R4 posterior has no worlds")
    world_count = len(worlds)

    values: list[tuple[str, float]] = []
    p1_counts: list[tuple[str, int]] = []
    for canonical_root_action, root_action in root_pairs:
        grouped: dict[str, dict[str, float]] = {}
        group_counts: dict[str, int] = {}
        action_sets: dict[str, tuple[str, ...]] = {}

        for world in worlds:
            _world_root_key, world_root_pairs = _canonical_root_pairs(world)
            world_map = dict(world_root_pairs)
            if canonical_root_action not in world_map:
                raise AssertionError("posterior world changed root canonical action set")
            child = child_state(world, world_map[canonical_root_action])
            if child.terminal() or child.actor != 1 or child.round_index != 4:
                raise AssertionError("R4 P0 action must lead to R4 P1")
            p1_key = information_state_key(child)
            pairs = tuple(legal_action_pairs(child))
            keys = tuple(key for key, _action in pairs)
            previous = action_sets.get(p1_key)
            if previous is None:
                action_sets[p1_key] = keys
                grouped[p1_key] = {key: 0.0 for key in keys}
                group_counts[p1_key] = 0
            elif previous != keys:
                raise AssertionError("same P1 raw infoset produced different action set")
            group_counts[p1_key] += 1
            for p1_action_key, p1_action in pairs:
                terminal = child_state(child, p1_action)
                grouped[p1_key][p1_action_key] += terminal_utility(terminal, 0)

        total = 0.0
        for p1_key, action_sums in grouped.items():
            if not action_sums:
                raise AssertionError("P1 infoset has no legal response")
            # Equal posterior world weights. P1 chooses one action per legal
            # information state to minimize expected P0 terminal utility.
            best_response_sum = min(action_sums.values())
            total += best_response_sum
        value = total / world_count
        if not math.isfinite(value):
            raise AssertionError("exact R4 root value is non-finite")
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
        return sample_belief_root(
            self.base_root,
            self.spec,
            self.support,
            self.belief_rng,
        )


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
        self.belief_rng = random.Random(int(seed) ^ 0x06CFR311)

    def _sample_conditioned_root(self) -> HUState:
        return sample_belief_root(
            self.base_root,
            self.spec,
            self.support,
            self.belief_rng,
        )


def normalize_policy(rows: Mapping[str, float]) -> dict[str, float]:
    out = {str(key): float(value) for key, value in rows.items()}
    if any(not math.isfinite(value) or value < 0.0 for value in out.values()):
        raise ValueError("policy weights must be finite and non-negative")
    mass = sum(out.values())
    if mass <= 0.0:
        raise ValueError("policy has zero mass")
    return {key: value / mass for key, value in sorted(out.items())}


def exact_policy_regret(policy: Mapping[str, float], oracle: R4ExactOracle) -> float:
    normalized = normalize_policy(policy)
    values = oracle.value_map()
    if set(normalized) != set(values):
        raise ValueError("policy action set differs from exact oracle")
    expected = sum(normalized[key] * values[key] for key in values)
    regret = oracle.best_value - expected
    if regret < -1e-9:
        raise AssertionError("exact local policy regret became materially negative")
    return max(0.0, regret)


def exact_top_action_regret(action_key: str, oracle: R4ExactOracle) -> float:
    values = oracle.value_map()
    if action_key not in values:
        raise ValueError("top action is absent from exact oracle")
    regret = oracle.best_value - values[action_key]
    if regret < -1e-9:
        raise AssertionError("exact top-action regret became materially negative")
    return max(0.0, regret)
