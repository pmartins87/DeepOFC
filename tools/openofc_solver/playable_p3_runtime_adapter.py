from __future__ import annotations

"""Fail-closed P3 bridge from a runtime observation to the P2 policy.

This module is deliberately pure: it recognizes no pixels and sends no mouse
input.  It accepts an already reconstructed two-player Normal/Normal
``HUPlayerObservation``, creates the exact suit-canonical visible node used in
training, selects from the immutable P2 artifact, independently revalidates the
selected action in ``deepofc.actions``, and emits the existing semantic
``RuntimeTurnPlan`` for the shadow/single-drag transaction layer.

Public history is mandatory from hand start.  A current board alone cannot
recover which public action sequence produced it, and that sequence is part of
the trained information key.  Mid-hand guessing therefore fails closed.
"""

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
import re
from typing import Mapping

from deepofc.actions import NormalPlacementAction, enumerate_normal_actions
from deepofc.runtime_plan import RuntimeTurnPlan, build_runtime_turn_plan
from deepofc.sequential import HUPlayerObservation
from deepofc.state import (
    Card as RuntimeCard,
    OFCState,
    PendingPlacement,
    PlayerBoard,
    Row,
)
from engine import Action, Board, Card
from playable_p2_candidate import (
    LoadedPlayableManifest,
    LoadedPlayableRoute,
    canonical_bytes,
    load_manifest,
    payload_sha256,
)
from strategic_cfr import PublicActionEvent
from strategic_suit_symmetry import (
    HUVisibleObservation,
    canonical_visible_node_view,
)

ADAPTER_SCHEMA = "openofc-playable-p3-normal-runtime-adapter-v1"
DECISION_SCHEMA = "openofc-playable-p3-normal-runtime-decision-v1"
AUTHORITY = "SHADOW_ONLY_NO_PHYSICAL_EXECUTION_AUTHORITY"
SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")

_RUNTIME_TO_ENGINE_ROW = {
    Row.TOP: 0,
    Row.MIDDLE: 1,
    Row.BOTTOM: 2,
}
_ENGINE_TO_RUNTIME_ROW = {value: key for key, value in _RUNTIME_TO_ENGINE_ROW.items()}


@dataclass(frozen=True)
class PersistentHUSeats:
    """Stable mapping from P2 persistent identities to runtime chairs."""

    p0_chair: int
    p1_chair: int

    def __post_init__(self) -> None:
        if self.p0_chair == self.p1_chair:
            raise ValueError("persistent P0/P1 must map to distinct runtime chairs")

    @property
    def chairs(self) -> tuple[int, int]:
        return (self.p0_chair, self.p1_chair)

    def identity_for_chair(self, chair: int) -> int:
        if chair == self.p0_chair:
            return 0
        if chair == self.p1_chair:
            return 1
        raise ValueError("runtime chair is absent from persistent P0/P1 mapping")

    def chair_for_identity(self, identity: int) -> int:
        if identity not in (0, 1):
            raise ValueError("persistent identity must be P0 or P1")
        return self.chairs[identity]


@dataclass(frozen=True)
class RuntimePolicyNode:
    button: int
    hero_identity: int
    actor_role: int
    visible: HUVisibleObservation
    canonical_key: str
    action_pairs: tuple[tuple[str, Action], ...]
    suit_map: tuple[int, int, int, int]


@dataclass(frozen=True)
class PlayableP3Decision:
    action: NormalPlacementAction
    runtime_plan: RuntimeTurnPlan
    canonical_key: str
    canonical_action_key: str
    selected_probability: float
    receipt: Mapping[str, object]

    @property
    def receipt_sha256(self) -> str:
        return str(self.receipt["sha256"])

    def receipt_json(self) -> str:
        return json.dumps(
            self.receipt,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        )


def _engine_card(card: RuntimeCard) -> Card:
    return Card.parse(card.code)


def _engine_board(board: PlayerBoard) -> Board:
    return Board(
        top=tuple(_engine_card(card) for card in board.top),
        middle=tuple(_engine_card(card) for card in board.middle),
        bottom=tuple(_engine_card(card) for card in board.bottom),
    )


def _normal_runtime_gate(state: OFCState, seats: PersistentHUSeats) -> None:
    if state.mode != "joker_ultimate":
        raise ValueError("P3 adapter requires the Joker Ultimate runtime mode")
    if len(state.players) != 2 or set(player.chair for player in state.players) != set(
        seats.chairs
    ):
        raise ValueError("P3 adapter requires exactly the mapped two-player table")
    if any(player.fantasy for player in state.players):
        raise ValueError("P3 first candidate supports Normal/Normal only")
    if any(player.sitting_out for player in state.players):
        raise ValueError("P3 adapter refuses a sitting-out HU player")
    if state.round_index not in range(5):
        raise ValueError("P3 adapter requires a normal round 0..4")
    if state.acting_chair != state.hero_chair:
        raise ValueError("P3 adapter may select an action only for the acting Hero")
    if not state.hero_can_prepare:
        raise ValueError("P3 adapter requires an actionable Hero preparation state")
    if state.dealer_chair not in seats.chairs:
        raise ValueError("runtime dealer is absent from persistent P0/P1 mapping")


def _validate_hidden_counts(
    state: OFCState,
    *,
    role_chairs: tuple[int, int],
    actor_role: int,
) -> None:
    expected_packet = 5 if state.round_index == 0 else 3
    for role, chair in enumerate(role_chairs):
        player = state.player(chair)
        acted_current_round = role < actor_role
        expected_discards = max(0, state.round_index - 1)
        if acted_current_round and state.round_index > 0:
            expected_discards += 1

        if chair == state.hero_chair:
            if player.hidden_incoming_count != 0 or player.hidden_discard_count != 0:
                raise ValueError("Hero private cards must be explicit, not hidden counts")
            continue

        expected_hidden_incoming = 0 if acted_current_round else expected_packet
        if player.hidden_incoming_count != expected_hidden_incoming:
            raise ValueError("opponent hidden incoming count contradicts ordered progress")
        if player.hidden_discard_count != expected_discards:
            raise ValueError("opponent hidden discard count contradicts ordered progress")


def runtime_policy_node(
    observation: HUPlayerObservation,
    seats: PersistentHUSeats,
) -> RuntimePolicyNode:
    """Convert a runtime player observation into the exact trained node."""

    state = observation.state
    _normal_runtime_gate(state, seats)
    button = seats.identity_for_chair(state.dealer_chair)
    nondealer_chair = seats.chair_for_identity(1 - button)
    dealer_chair = seats.chair_for_identity(button)
    role_chairs = (nondealer_chair, dealer_chair)
    actor_role = role_chairs.index(state.acting_chair)
    hero_identity = seats.identity_for_chair(state.hero_chair)
    _validate_hidden_counts(
        state,
        role_chairs=role_chairs,
        actor_role=actor_role,
    )

    history: list[PublicActionEvent] = []
    for record in observation.public_action_history:
        if record.chair not in role_chairs:
            raise ValueError("public-history chair is absent from the mapped HU seats")
        role = role_chairs.index(record.chair)
        placements: list[tuple[str, int]] = []
        for code, row_name in record.placements:
            runtime_card = RuntimeCard.from_code(str(code))
            row = Row(str(row_name))
            placements.append((runtime_card.code, _RUNTIME_TO_ENGINE_ROW[row]))
        history.append(
            PublicActionEvent(
                round_index=int(record.round_index),
                player=role,
                placements=tuple(sorted(placements)),
            )
        )

    visible = HUVisibleObservation(
        round_index=state.round_index,
        actor=actor_role,
        boards=(
            _engine_board(state.player(nondealer_chair).board),
            _engine_board(state.player(dealer_chair).board),
        ),
        own_discards=tuple(_engine_card(card) for card in state.hero_discards),
        incoming=tuple(_engine_card(card) for card in state.hero_incoming),
        public_history=tuple(history),
    )
    canonical_key, pairs, suit_map = canonical_visible_node_view(visible)
    if not pairs:
        raise ValueError("validated P3 runtime observation has no legal action")
    return RuntimePolicyNode(
        button=button,
        hero_identity=hero_identity,
        actor_role=actor_role,
        visible=visible,
        canonical_key=canonical_key,
        action_pairs=tuple(pairs),
        suit_map=suit_map,
    )


def _runtime_action(state: OFCState, action: Action) -> NormalPlacementAction:
    incoming = state.hero_incoming
    placements = tuple(
        PendingPlacement(
            card=incoming[index],
            row=_ENGINE_TO_RUNTIME_ROW[int(row)],
        )
        for index, row in action.placements
    )
    discard = (
        None
        if action.discard_index is None
        else incoming[action.discard_index]
    )
    candidate = NormalPlacementAction(placements=placements, discard=discard)
    legal_keys = {legal.key() for legal in enumerate_normal_actions(state)}
    if candidate.key() not in legal_keys:
        raise ValueError("P2-selected action failed independent runtime legality validation")
    return candidate


class PlayableP3RuntimeAdapter:
    """Immutable P2 bundle plus the visible-state P3 decision boundary."""

    def __init__(
        self,
        bundle: LoadedPlayableManifest,
        *,
        expected_manifest_sha256: str,
    ) -> None:
        if not SHA256_PATTERN.fullmatch(expected_manifest_sha256):
            raise ValueError("expected P2 manifest identity must be lowercase SHA-256")
        if bundle.manifest_sha256 != expected_manifest_sha256:
            raise ValueError("loaded P2 manifest differs from the pinned SHA-256")
        self._bundle = bundle

    @classmethod
    def from_manifest(
        cls,
        path: Path,
        *,
        expected_manifest_sha256: str,
    ) -> "PlayableP3RuntimeAdapter":
        return cls(
            load_manifest(Path(path)),
            expected_manifest_sha256=expected_manifest_sha256,
        )

    @property
    def bundle(self) -> LoadedPlayableManifest:
        return self._bundle

    def select(
        self,
        observation: HUPlayerObservation,
        seats: PersistentHUSeats,
    ) -> PlayableP3Decision:
        node = runtime_policy_node(observation, seats)
        route: LoadedPlayableRoute = self._bundle.route_for_button(node.button)
        action_keys = tuple(key for key, _action in node.action_pairs)
        probabilities = route.policy(node.canonical_key, action_keys)
        selected_key = route.select_action(node.canonical_key, action_keys)
        selected_index = action_keys.index(selected_key)
        selected_engine_action = node.action_pairs[selected_index][1]

        state = observation.state
        runtime_action = _runtime_action(state, selected_engine_action)
        runtime_plan = build_runtime_turn_plan(state, runtime_action)
        receipt: dict[str, object] = {
            "schema": DECISION_SCHEMA,
            "adapter_schema": ADAPTER_SCHEMA,
            "authority": AUTHORITY,
            "physical_execution_authorized": False,
            "policy_manifest_sha256": self._bundle.manifest_sha256,
            "policy_source_commit": self._bundle.source_commit,
            "route": {
                "button": node.button,
                "state": route.state.as_key(),
                "file_sha256": self._bundle.file_sha256_for_button(node.button),
                "route_sha256": route.route_sha256,
                "policy_snapshot_sha256": route.snapshot.sha256,
                "model_sha256": route.snapshot.model_sha256,
            },
            "persistent_chairs": {
                "p0": seats.p0_chair,
                "p1": seats.p1_chair,
                "hero_identity": node.hero_identity,
            },
            "runtime_decision_fingerprint": runtime_plan.decision_fingerprint,
            "canonical_information_key": node.canonical_key,
            "canonical_information_key_sha256": hashlib.sha256(
                node.canonical_key.encode("utf-8")
            ).hexdigest(),
            "canonical_action_key": selected_key,
            "selected_probability": probabilities[selected_index],
            "runtime_action_key": runtime_action.key(),
            "runtime_turn_plan": runtime_plan.to_payload(),
            "runtime_binding_complete": False,
        }
        receipt["sha256"] = payload_sha256(receipt)
        if canonical_bytes(receipt) != self._receipt_bytes(receipt):
            raise AssertionError("P3 decision receipt is not canonically stable")
        return PlayableP3Decision(
            action=runtime_action,
            runtime_plan=runtime_plan,
            canonical_key=node.canonical_key,
            canonical_action_key=selected_key,
            selected_probability=probabilities[selected_index],
            receipt=receipt,
        )

    @staticmethod
    def _receipt_bytes(receipt: Mapping[str, object]) -> bytes:
        if not SHA256_PATTERN.fullmatch(str(receipt.get("sha256", ""))):
            raise ValueError("P3 decision receipt SHA-256 is missing")
        unsigned = dict(receipt)
        expected = str(unsigned.pop("sha256"))
        if payload_sha256(unsigned) != expected:
            raise ValueError("P3 decision receipt SHA-256 mismatch")
        return canonical_bytes(receipt)
