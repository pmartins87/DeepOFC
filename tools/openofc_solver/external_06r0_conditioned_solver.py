from __future__ import annotations

"""06R0 conditioned-suffix research helpers.

The strategic core remains untouched.  This module creates payoff-blind observed
root fixtures, re-samples only not-yet-fixed future deal packets, and runs the
already-certified exact-suit outcome-sampling learner from those conditioned
roots.  It is a reuse-geometry diagnostic, not a posterior-correct resolver.
"""

from dataclasses import dataclass
import hashlib
import json
import random
from typing import Sequence

from engine import full_deck
from external_06s0_suit_automorphism import (
    canonical_information_state,
    canonical_legal_action_keys,
)
from external_06s1_suit_canonical_solver import SuitCanonicalOutcomeSamplingMCCFR
from strategic_cfr import (
    DealPlan,
    HUState,
    PLAYERS,
    child_state,
    information_state_key,
    legal_action_pairs,
    sample_deal_plan,
)

AUTHORITY = "CONDITIONED_SUFFIX_REUSE_GEOMETRY_DIAGNOSTIC_ONLY"


@dataclass(frozen=True)
class ConditionedFixtureSpec:
    name: str
    seed: int
    round_index: int
    actor: int


FROZEN_FIXTURES: tuple[ConditionedFixtureSpec, ...] = (
    ConditionedFixtureSpec("R1_P0_A", 61001, 1, 0),
    ConditionedFixtureSpec("R2_P0_A", 62001, 2, 0),
    ConditionedFixtureSpec("R2_P1_A", 62002, 2, 1),
    ConditionedFixtureSpec("R3_P0_A", 63001, 3, 0),
    ConditionedFixtureSpec("R3_P1_A", 63002, 3, 1),
    ConditionedFixtureSpec("R4_P0_A", 64001, 4, 0),
)


def _prefix_action_index(state: HUState, fixture_seed: int, legal_count: int) -> int:
    if legal_count <= 0:
        raise ValueError("prefix state has no legal action")
    material = (
        f"06R0|{fixture_seed}|{state.round_index}|{state.actor}|"
        f"{information_state_key(state)}"
    ).encode("utf-8")
    digest = hashlib.sha256(material).digest()
    return int.from_bytes(digest[:8], "big") % legal_count


def build_conditioned_fixture(spec: ConditionedFixtureSpec) -> HUState:
    """Build one deterministic payoff-blind prefix ending at the frozen root."""
    if spec.actor not in PLAYERS:
        raise ValueError("fixture actor must be 0 or 1")
    if not 1 <= spec.round_index <= 4:
        raise ValueError("06R0 fixtures must start in rounds 1..4")

    state = HUState(plan=sample_deal_plan(random.Random(spec.seed)))
    while (state.round_index, state.actor) != (spec.round_index, spec.actor):
        if state.terminal():
            raise AssertionError("fixture target was not reached before terminal")
        pairs = legal_action_pairs(state)
        index = _prefix_action_index(state, spec.seed, len(pairs))
        state = child_state(state, pairs[index][1])
    return state


def _preserve_round_packet(root: HUState, round_index: int, player: int) -> bool:
    if round_index < root.round_index:
        return True
    if round_index > root.round_index:
        return False
    # At a P0 root P1 has not yet received/acted on a publicly observable
    # packet for this conditioned decision, so P1's current packet is sampled.
    # At a P1 root P0 has already acted and P1's own packet is known.
    if root.actor == 0:
        return player == 0
    return True


def _plan_payload(plan: DealPlan) -> dict:
    return {
        "opening": [[str(card) for card in packet] for packet in plan.opening],
        "rounds": [
            [[str(card) for card in packet] for packet in pair]
            for pair in plan.rounds
        ],
    }


def plan_sha256(plan: DealPlan) -> str:
    return hashlib.sha256(
        json.dumps(_plan_payload(plan), sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def resample_unseen_future(root: HUState, rng: random.Random) -> HUState:
    """Sample not-yet-fixed deal packets while preserving the exact root infoset.

    This intentionally leaves all already-fixed past packets untouched. It is a
    future-only chance model for the 06R0 geometry gate, not a Bayesian model of
    earlier hidden opponent discards.
    """
    if root.terminal() or not 1 <= root.round_index <= 4:
        raise ValueError("conditioned root must be a non-terminal R1..R4 state")

    preserved_cards = set(root.plan.opening[0]) | set(root.plan.opening[1])
    for round_index, pair in enumerate(root.plan.rounds, start=1):
        for player in PLAYERS:
            if _preserve_round_packet(root, round_index, player):
                preserved_cards.update(pair[player])

    deck = list(full_deck(2))
    if len(deck) != len(set(deck)):
        raise AssertionError("physical full deck must contain unique cards")
    candidates = [card for card in deck if card not in preserved_cards]
    rng.shuffle(candidates)
    cursor = 0

    new_rounds: list[tuple[tuple, tuple]] = []
    for round_index, pair in enumerate(root.plan.rounds, start=1):
        packets = []
        for player in PLAYERS:
            if _preserve_round_packet(root, round_index, player):
                packet = pair[player]
            else:
                packet = tuple(sorted(candidates[cursor:cursor + 3]))
                cursor += 3
                if len(packet) != 3:
                    raise AssertionError("conditional future sampler exhausted deck")
            packets.append(packet)
        new_rounds.append((packets[0], packets[1]))

    plan = DealPlan(
        opening=root.plan.opening,
        rounds=tuple(new_rounds),  # type: ignore[arg-type]
    )
    dealt = plan.dealt_cards()
    if len(dealt) != 34 or len(set(dealt)) != 34:
        raise AssertionError("conditioned deal plan must retain 34 unique physical cards")

    sampled = HUState(
        plan=plan,
        round_index=root.round_index,
        actor=root.actor,
        boards=root.boards,
        discards=root.discards,
        public_history=root.public_history,
    )
    validate_same_root_information(root, sampled)
    return sampled


def validate_same_root_information(base: HUState, sampled: HUState) -> None:
    if information_state_key(base) != information_state_key(sampled):
        raise AssertionError("future resampling changed raw root information state")
    base_canonical, _ = canonical_information_state(base)
    sampled_canonical, _ = canonical_information_state(sampled)
    if base_canonical != sampled_canonical:
        raise AssertionError("future resampling changed suit-canonical root information state")
    if canonical_legal_action_keys(base) != canonical_legal_action_keys(sampled):
        raise AssertionError("future resampling changed canonical root legal action set")
    if (
        base.boards != sampled.boards
        or base.discards != sampled.discards
        or base.public_history != sampled.public_history
        or base.round_index != sampled.round_index
        or base.actor != sampled.actor
    ):
        raise AssertionError("future resampling changed materialized root state")


def remaining_decisions_per_iteration(root: HUState) -> int:
    """Exact number of regret-updating nodes across the two update episodes."""
    if root.terminal():
        return 0
    round_index = root.round_index
    actor = root.actor
    decisions = 0
    while round_index <= 4:
        decisions += 1
        if actor == 0:
            actor = 1
        else:
            round_index += 1
            actor = 0
    return decisions


class ConditionedSuitCanonicalOutcomeSamplingMCCFR(SuitCanonicalOutcomeSamplingMCCFR):
    """Outcome-sampling MCCFR rooted at one observed suffix information state."""

    def __init__(
        self,
        *,
        base_root: HUState,
        resample_future: bool,
        epsilon: float = 0.6,
        seed: int = 20260830,
        cfr_plus: bool = True,
    ) -> None:
        if base_root.terminal():
            raise ValueError("conditioned solver requires non-terminal root")
        super().__init__(epsilon=epsilon, seed=seed, cfr_plus=cfr_plus)
        self.base_root = base_root
        self.resample_future = bool(resample_future)
        self.root_history_length = len(base_root.public_history)
        self.expected_updates_per_iteration = remaining_decisions_per_iteration(base_root)

    def _sample_conditioned_root(self) -> HUState:
        if self.resample_future:
            return resample_unseen_future(self.base_root, self.rng)
        return self.base_root

    def run_iteration(self) -> None:
        for update_player in PLAYERS:
            state = self._sample_conditioned_root()
            self._episode(
                state,
                update_player,
                my_reach=1.0,
                opp_reach=1.0,
                sample_reach=1.0,
            )
            self.episodes += 1
        self.iterations += 1


def checkpoint_semantic_bytes(
    solver: ConditionedSuitCanonicalOutcomeSamplingMCCFR,
) -> bytes:
    """Deterministic solver-state bytes for same-seed mechanical probes."""
    return json.dumps(
        solver.checkpoint_payload(),
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")


def root_probe(root: HUState, *, sample_seed: int, samples: int = 32) -> dict:
    if samples <= 0:
        raise ValueError("samples must be positive")
    rng = random.Random(sample_seed)
    raw_key = information_state_key(root)
    canonical_key, _ = canonical_information_state(root)
    legal_keys = canonical_legal_action_keys(root)
    plan_hashes: set[str] = set()
    exact_information = True
    for _ in range(samples):
        sampled = resample_unseen_future(root, rng)
        plan_hashes.add(plan_sha256(sampled.plan))
        exact_information = exact_information and (
            information_state_key(sampled) == raw_key
            and canonical_information_state(sampled)[0] == canonical_key
            and canonical_legal_action_keys(sampled) == legal_keys
        )
    return {
        "samples": samples,
        "unique_sampled_plan_sha256": len(plan_hashes),
        "raw_and_canonical_root_information_exact": exact_information,
        "root_legal_action_count": len(legal_keys),
        "root_history_length": len(root.public_history),
        "remaining_decisions_per_iteration": remaining_decisions_per_iteration(root),
        "root_key_sha256": hashlib.sha256(canonical_key.encode("utf-8")).hexdigest(),
    }
