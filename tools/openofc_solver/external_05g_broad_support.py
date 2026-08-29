from __future__ import annotations

"""Deterministic support construction for 05G broad hidden-information research.

The support is frozen from card geometry only.  No terminal utility, best-response
value, Search statistic, or MCCFR statistic participates in construction.

Authority:
  BROAD_HIDDEN_INFORMATION_REDUCED_GAME_SHADOW_ONLY
"""

from dataclasses import dataclass
import hashlib
import json
from itertools import product
from typing import Sequence

from engine import Board, Card, parse_cards
from external_hidden_discard_overlap import (
    OverlapWorld,
    find_hidden_discard_collisions,
    validate_worlds,
    with_overlap_world,
)
from external_hidden_discard_overlap_strategic import ReachableSupport, build_reachable_support
from strategic_cfr import DealPlan, HUState

AUTHORITY = "BROAD_HIDDEN_INFORMATION_REDUCED_GAME_SHADOW_ONLY"
SCHEMA = "openofc-external-05g-broad-support-v1"


@dataclass(frozen=True)
class BroadSupportGeometry:
    authority: str
    schema: str
    support_sha256: str
    support_worlds: int
    p0_r3_private_types: int
    p1_r3_private_types: int
    p0_r4_private_types: int
    p1_r4_private_types: int
    reachable_information_states: int
    ambiguous_information_states: int
    ambiguous_nonroot_information_states: int
    nonroot_information_states_ge3_worlds: int
    max_compatible_worlds: int
    p0_hidden_discard_collision: bool
    p1_hidden_discard_collision: bool
    layers: tuple[tuple[str, int, int, int], ...]


def _packet_key(cards: Sequence[Card]) -> tuple[str, ...]:
    return tuple(sorted(str(card) for card in cards))


def _board(top: str, middle: str, bottom: str) -> Board:
    return Board(parse_cards(top), parse_cards(middle), parse_cards(bottom))


def broad_private_types() -> dict[str, tuple[tuple[Card, ...], ...]]:
    """Return the precommitted 3x3x2x2 private/future packet schedule.

    R3 types deliberately share two public-placeable cards and vary a third card,
    making hidden-discard collisions possible without inspecting payoff values.
    R4 types broaden future-card geometry while remaining disjoint from every
    other category used in the Cartesian product.
    """

    return {
        "p0_r3": (
            parse_cards("7c 8c 8h"),
            parse_cards("7c 8c 9d"),
            parse_cards("7c 8c Td"),
        ),
        "p1_r3": (
            parse_cards("Ah Kh Qh"),
            parse_cards("Ah Kh Ks"),
            parse_cards("Ah Kh As"),
        ),
        "p0_r4": (
            parse_cards("9h Th Ts"),
            parse_cards("9s 8d 7d"),
        ),
        "p1_r4": (
            parse_cards("Ad Kc Qs"),
            parse_cards("Ac Kd Qs"),
        ),
    }


def broad_worlds() -> tuple[OverlapWorld, ...]:
    types = broad_private_types()
    worlds: list[OverlapWorld] = []
    for p0r3_i, p1r3_i, p0r4_i, p1r4_i in product(
        range(len(types["p0_r3"])),
        range(len(types["p1_r3"])),
        range(len(types["p0_r4"])),
        range(len(types["p1_r4"])),
    ):
        worlds.append(
            OverlapWorld(
                world_id=f"p0r3-{p0r3_i}_p1r3-{p1r3_i}_p0r4-{p0r4_i}_p1r4-{p1r4_i}",
                p0_r3=types["p0_r3"][p0r3_i],
                p1_r3=types["p1_r3"][p1r3_i],
                p0_r4=types["p0_r4"][p0r4_i],
                p1_r4=types["p1_r4"][p1r4_i],
            )
        )
    support = validate_worlds(worlds)
    if len(support) != 36:
        raise AssertionError("05G frozen support must contain exactly 36 worlds")
    return support


def public_pre_r3_state() -> HUState:
    """Canonical public state immediately before P0 receives its R3 packet."""

    w = broad_worlds()[0]
    plan = DealPlan(
        opening=(
            parse_cards("Qc 2c 3c 4c 5c"),
            parse_cards("Jc 4h 5h 9c Tc"),
        ),
        rounds=(
            (parse_cards("Qd 2d 2h"), parse_cards("Jd 6h 2s")),
            (parse_cards("3d 6c 3h"), parse_cards("7h Jh 3s")),
            (w.p0_r3, w.p1_r3),
            (w.p0_r4, w.p1_r4),
        ),
    )
    return HUState(
        plan=plan,
        round_index=3,
        actor=0,
        boards=(
            _board("Qc Qd", "2c 2d 3c 3d", "4c 5c 6c"),
            _board("Jc Jd", "4h 5h 6h 7h", "9c Tc Jh"),
        ),
        discards=(parse_cards("2h 3h"), parse_cards("2s 3s")),
        public_history=(),
    )


def support_sha256(worlds: Sequence[OverlapWorld]) -> str:
    payload = [
        {
            "world_id": world.world_id,
            "p0_r3": _packet_key(world.p0_r3),
            "p1_r3": _packet_key(world.p1_r3),
            "p0_r4": _packet_key(world.p0_r4),
            "p1_r4": _packet_key(world.p1_r4),
        }
        for world in worlds
    ]
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def validate_broad_physical_support(
    base_state: HUState,
    worlds: Sequence[OverlapWorld],
) -> None:
    support = validate_worlds(worlds)
    seen_ids: set[str] = set()
    for world in support:
        if world.world_id in seen_ids:
            raise AssertionError("duplicate world id")
        seen_ids.add(world.world_id)
        state = with_overlap_world(base_state, world)
        dealt = state.plan.dealt_cards()
        if len(dealt) != 34 or len(set(dealt)) != 34:
            raise AssertionError("05G world must contain 34 unique dealt cards")


def summarize_geometry(
    base_state: HUState,
    worlds: Sequence[OverlapWorld],
    *,
    support_rows: Sequence[ReachableSupport] | None = None,
) -> BroadSupportGeometry:
    support = validate_worlds(worlds)
    validate_broad_physical_support(base_state, support)
    rows = tuple(support_rows) if support_rows is not None else build_reachable_support(base_state, support)
    collisions = find_hidden_discard_collisions(base_state, support)
    hidden_players = {row.hidden_player for row in collisions}

    ambiguous = [row for row in rows if len(row.concrete_states) > 1]
    nonroot_ambiguous = [
        row
        for row in ambiguous
        if (row.round_index, row.actor) != (3, 0)
    ]
    ge3 = [row for row in nonroot_ambiguous if len(row.concrete_states) >= 3]

    layer_rows: list[tuple[str, int, int, int]] = []
    layer_keys = sorted({(row.round_index, row.actor) for row in rows})
    for round_index, actor in layer_keys:
        subset = [row for row in rows if row.round_index == round_index and row.actor == actor]
        layer_rows.append(
            (
                f"R{round_index}_P{actor}",
                len(subset),
                sum(1 for row in subset if len(row.concrete_states) > 1),
                max((len(row.concrete_states) for row in subset), default=0),
            )
        )

    types = broad_private_types()
    return BroadSupportGeometry(
        authority=AUTHORITY,
        schema=SCHEMA,
        support_sha256=support_sha256(support),
        support_worlds=len(support),
        p0_r3_private_types=len({_packet_key(packet) for packet in types["p0_r3"]}),
        p1_r3_private_types=len({_packet_key(packet) for packet in types["p1_r3"]}),
        p0_r4_private_types=len({_packet_key(packet) for packet in types["p0_r4"]}),
        p1_r4_private_types=len({_packet_key(packet) for packet in types["p1_r4"]}),
        reachable_information_states=len(rows),
        ambiguous_information_states=len(ambiguous),
        ambiguous_nonroot_information_states=len(nonroot_ambiguous),
        nonroot_information_states_ge3_worlds=len(ge3),
        max_compatible_worlds=max((len(row.concrete_states) for row in rows), default=0),
        p0_hidden_discard_collision=0 in hidden_players,
        p1_hidden_discard_collision=1 in hidden_players,
        layers=tuple(layer_rows),
    )


__all__ = [
    "AUTHORITY",
    "SCHEMA",
    "BroadSupportGeometry",
    "broad_private_types",
    "broad_worlds",
    "public_pre_r3_state",
    "support_sha256",
    "validate_broad_physical_support",
    "summarize_geometry",
]
