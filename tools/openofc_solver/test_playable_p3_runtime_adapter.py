from __future__ import annotations

from dataclasses import replace
import json
from pathlib import Path
import random

import pytest

from deepofc.actions import enumerate_normal_actions
from deepofc.runtime_orchestrator import RuntimeTurnOrchestrator
from deepofc.sequential import HUPlayerObservation, HUSequentialNormalState
from deepofc.state import Card, PendingPlacement
from playable_p2_candidate import payload_sha256
from playable_p3_runtime_adapter import (
    AUTHORITY,
    PersistentHUSeats,
    PlayableP3RuntimeAdapter,
    runtime_policy_node,
)
from strategic_cfr import (
    DealPlan,
    HUState,
    child_state,
    legal_action_pairs,
    sample_deal_plan,
)
from strategic_suit_symmetry import (
    canonical_visible_node_view,
    visible_observation_from_state,
)

ROOT = Path(__file__).resolve().parents[2]
MANIFEST = (
    ROOT
    / "artifacts"
    / "playable_p2_normal_normal_candidate_20260902"
    / "playable_p2_manifest.json"
)
MANIFEST_SHA256 = "f10c079a61ba08832cfc334afb9c055e023dfc9c23a24140d02b2f7bd8413898"


@pytest.fixture(scope="module")
def adapter() -> PlayableP3RuntimeAdapter:
    return PlayableP3RuntimeAdapter.from_manifest(
        MANIFEST,
        expected_manifest_sha256=MANIFEST_SHA256,
    )


def _advance_first_legal(
    state: HUSequentialNormalState,
    count: int,
) -> HUSequentialNormalState:
    for _ in range(count):
        state = state.apply(state.legal_actions()[0])
    return state


def _swap_only_hidden_cards(plan: DealPlan) -> DealPlan:
    """Keep both opening packets fixed while changing unseen future worlds."""

    rounds = [[list(packet) for packet in pair] for pair in plan.rounds]
    rounds[0][1][0], rounds[3][0][0] = rounds[3][0][0], rounds[0][1][0]
    return DealPlan(
        opening=plan.opening,
        rounds=tuple(
            (tuple(sorted(pair[0])), tuple(sorted(pair[1])))
            for pair in rounds
        ),  # type: ignore[arg-type]
    )


def _assert_route_firewall(
    adapter: PlayableP3RuntimeAdapter,
    state_a: HUState,
    state_b: HUState,
) -> None:
    key_a, pairs_a, _map_a = canonical_visible_node_view(
        visible_observation_from_state(state_a)
    )
    key_b, pairs_b, _map_b = canonical_visible_node_view(
        visible_observation_from_state(state_b)
    )
    actions_a = tuple(key for key, _action in pairs_a)
    actions_b = tuple(key for key, _action in pairs_b)
    assert key_a == key_b
    assert actions_a == actions_b

    route = adapter.bundle.route_for_button(1)
    assert route.policy(key_a, actions_a) == route.policy(key_b, actions_b)
    assert route.select_action(key_a, actions_a) == route.select_action(
        key_b, actions_b
    )


def test_real_p2_bundle_selects_b1_and_builds_a_legal_shadow_plan(
    adapter: PlayableP3RuntimeAdapter,
) -> None:
    # Persistent P1 owns the button, so persistent P0/non-dealer acts first.
    game = HUSequentialNormalState.new(
        seed=2026090301,
        first_player=0,
        dealer_chair=1,
    )
    observation = game.observation(0)
    decision = adapter.select(observation, PersistentHUSeats(0, 1))

    assert decision.action.key() in {
        action.key() for action in enumerate_normal_actions(observation.state)
    }
    assert decision.runtime_plan.hero_chair == 0
    assert len(decision.runtime_plan.target_placements) == 5
    assert decision.runtime_plan.unused_cards == ()
    assert decision.receipt["authority"] == AUTHORITY
    assert decision.receipt["physical_execution_authorized"] is False
    assert decision.receipt["route"]["button"] == 1
    assert decision.receipt["policy_manifest_sha256"] == MANIFEST_SHA256
    unsigned = dict(decision.receipt)
    expected = unsigned.pop("sha256")
    assert payload_sha256(unsigned) == expected == decision.receipt_sha256

    repeated = adapter.select(observation, PersistentHUSeats(0, 1))
    assert repeated.action == decision.action
    assert repeated.runtime_plan == decision.runtime_plan
    assert repeated.receipt_json() == decision.receipt_json()


def test_real_p2_bundle_routes_persistent_button_zero_to_b0(
    adapter: PlayableP3RuntimeAdapter,
) -> None:
    # Persistent P0 owns the button, so persistent P1/non-dealer acts first.
    game = HUSequentialNormalState.new(
        seed=2026090302,
        first_player=1,
        dealer_chair=0,
    )
    observation = game.observation(1)
    node = runtime_policy_node(observation, PersistentHUSeats(0, 1))
    decision = adapter.select(observation, PersistentHUSeats(0, 1))
    assert node.button == 0
    assert node.actor_role == 0
    assert node.hero_identity == 1
    assert decision.receipt["route"]["button"] == 0


def test_late_round_public_history_produces_a_policy_decision(
    adapter: PlayableP3RuntimeAdapter,
) -> None:
    game = HUSequentialNormalState.new(
        seed=2026090303,
        first_player=0,
        dealer_chair=1,
    )
    # Two opening actions plus both round-1 actions => round 2, non-dealer.
    game = _advance_first_legal(game, 4)
    observation = game.observation(0)
    assert observation.state.round_index == 2
    assert len(observation.public_action_history) == 4
    decision = adapter.select(observation, PersistentHUSeats(0, 1))
    assert decision.action.key() in {
        action.key() for action in game.legal_actions()
    }
    assert len(decision.runtime_plan.target_placements) == 2
    assert len(decision.runtime_plan.unused_cards) == 1


def test_selected_plan_replays_through_fresh_scrape_verification(
    adapter: PlayableP3RuntimeAdapter,
) -> None:
    game = HUSequentialNormalState.new(
        seed=2026090304,
        first_player=0,
        dealer_chair=1,
    )
    observation = game.observation(0)
    decision = adapter.select(observation, PersistentHUSeats(0, 1))
    orchestrator = RuntimeTurnOrchestrator(decision.runtime_plan)
    progress = orchestrator.advance(observation.state)
    pending: list[PendingPlacement] = []

    while progress.next_placement is not None:
        step = progress.next_placement
        pending.append(PendingPlacement(Card.from_code(step.card_code), step.row))
        fresh = replace(
            observation.state,
            hero_pending=tuple(pending),
            hero_can_confirm=len(pending) == 5,
            action_required=len(pending) == 5,
        )
        progress = orchestrator.advance(fresh)

    assert progress.ready_for_confirm
    assert len(progress.already_correct) == 5


def test_missing_or_inconsistent_public_history_fails_closed(
    adapter: PlayableP3RuntimeAdapter,
) -> None:
    game = HUSequentialNormalState.new(
        seed=2026090305,
        first_player=0,
        dealer_chair=1,
    )
    game = _advance_first_legal(game, 2)
    observation = game.observation(0)
    missing = HUPlayerObservation(
        state=observation.state,
        own_action_history=observation.own_action_history,
        public_action_history=(),
    )
    with pytest.raises(ValueError, match="complete nondealer/dealer action prefix"):
        adapter.select(missing, PersistentHUSeats(0, 1))


def test_pinned_manifest_sha_is_mandatory() -> None:
    with pytest.raises(ValueError, match="differs from the pinned"):
        PlayableP3RuntimeAdapter.from_manifest(
            MANIFEST,
            expected_manifest_sha256="0" * 64,
        )


def test_receipt_is_json_canonical_and_contains_no_execution_geometry(
    adapter: PlayableP3RuntimeAdapter,
) -> None:
    game = HUSequentialNormalState.new(
        seed=2026090306,
        first_player=0,
        dealer_chair=1,
    )
    receipt = adapter.select(
        game.observation(0), PersistentHUSeats(0, 1)
    ).receipt_json()
    parsed = json.loads(receipt)
    assert json.dumps(parsed, sort_keys=True, separators=(",", ":")) == receipt
    assert "source_rect" not in receipt
    assert "target_rect" not in receipt


def test_real_p2_policy_and_action_are_invariant_to_hidden_world(
    adapter: PlayableP3RuntimeAdapter,
) -> None:
    plan_a = sample_deal_plan(random.Random(2026090307))
    plan_b = _swap_only_hidden_cards(plan_a)
    state_a = HUState(plan=plan_a)
    state_b = HUState(plan=plan_b)

    # Actor 0 cannot observe the changed opponent/future cards.
    _assert_route_firewall(adapter, state_a, state_b)

    # Actor 1 receives the same opening packet and sees the same public action;
    # changed future packets remain outside its information boundary too.
    action = legal_action_pairs(state_a)[29][1]
    state_a = child_state(state_a, action)
    state_b = child_state(state_b, action)
    _assert_route_firewall(adapter, state_a, state_b)
