from __future__ import annotations

"""Deterministic geometry-only support for 05H 144-world broadening.

No payoff, Search statistic, MCCFR statistic, best response, NashConv or
exploitability participates in support construction.
"""

from dataclasses import dataclass
import hashlib
import json
from itertools import product
from typing import Sequence

from engine import Card, parse_cards
from external_05g_broad_support import public_pre_r3_state
from external_hidden_discard_overlap import (
    OverlapWorld,
    find_hidden_discard_collisions,
    validate_worlds,
    with_overlap_world,
)
from external_hidden_discard_overlap_strategic import ReachableSupport, build_reachable_support

AUTHORITY = "BROADER_HIDDEN_INFORMATION_REDUCED_GAME_SHADOW_ONLY"
SCHEMA = "openofc-external-05h-144-world-support-v1"


@dataclass(frozen=True)
class HSupportGeometry:
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
    nonroot_information_states_ge3_states: int
    max_compatible_states: int
    p0_hidden_discard_collision: bool
    p1_hidden_discard_collision: bool
    layers: tuple[tuple[str, int, int, int], ...]


def _packet_key(cards: Sequence[Card]) -> tuple[str, ...]:
    return tuple(sorted(str(card) for card in cards))


def private_types() -> dict[str, tuple[tuple[Card, ...], ...]]:
    return {
        "p0_r3": (
            parse_cards("7c 8c 8h"),
            parse_cards("7c 8c 9d"),
            parse_cards("7c 8c Td"),
            parse_cards("7c 8c 8s"),
        ),
        "p1_r3": (
            parse_cards("Ah Kh Qh"),
            parse_cards("Ah Kh Ks"),
            parse_cards("Ah Kh As"),
            parse_cards("Ah Kh Js"),
        ),
        "p0_r4": (
            parse_cards("9h Th Ts"),
            parse_cards("9s 8d 7d"),
            parse_cards("4d 5d 6d"),
        ),
        "p1_r4": (
            parse_cards("Ad Kc Qs"),
            parse_cards("Ac Kd Qs"),
            parse_cards("4s 5s 6s"),
        ),
    }


def worlds() -> tuple[OverlapWorld, ...]:
    types = private_types()
    out: list[OverlapWorld] = []
    for p0r3_i, p1r3_i, p0r4_i, p1r4_i in product(
        range(len(types["p0_r3"])),
        range(len(types["p1_r3"])),
        range(len(types["p0_r4"])),
        range(len(types["p1_r4"])),
    ):
        out.append(
            OverlapWorld(
                world_id=f"05h_p0r3-{p0r3_i}_p1r3-{p1r3_i}_p0r4-{p0r4_i}_p1r4-{p1r4_i}",
                p0_r3=types["p0_r3"][p0r3_i],
                p1_r3=types["p1_r3"][p1r3_i],
                p0_r4=types["p0_r4"][p0r4_i],
                p1_r4=types["p1_r4"][p1r4_i],
            )
        )
    support = validate_worlds(out)
    if len(support) != 144:
        raise AssertionError("05H frozen support must contain exactly 144 worlds")
    return support


def support_sha256(support: Sequence[OverlapWorld]) -> str:
    payload = [
        {
            "world_id": world.world_id,
            "p0_r3": _packet_key(world.p0_r3),
            "p1_r3": _packet_key(world.p1_r3),
            "p0_r4": _packet_key(world.p0_r4),
            "p1_r4": _packet_key(world.p1_r4),
        }
        for world in support
    ]
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def validate_physical_support(base_state, support: Sequence[OverlapWorld]) -> None:
    frozen = validate_worlds(support)
    if len(frozen) != 144:
        raise AssertionError("05H physical support count changed")
    ids = [world.world_id for world in frozen]
    if len(ids) != len(set(ids)):
        raise AssertionError("duplicate 05H world id")
    for world in frozen:
        state = with_overlap_world(base_state, world)
        dealt = state.plan.dealt_cards()
        if len(dealt) != 34 or len(set(dealt)) != 34:
            raise AssertionError("05H world must form one physically unique 34-card HU deal")


def summarize_geometry(
    base_state,
    support: Sequence[OverlapWorld],
    *,
    support_rows: Sequence[ReachableSupport] | None = None,
) -> HSupportGeometry:
    frozen = validate_worlds(support)
    validate_physical_support(base_state, frozen)
    rows = tuple(support_rows) if support_rows is not None else build_reachable_support(base_state, frozen)
    collisions = find_hidden_discard_collisions(base_state, frozen)
    hidden_players = {collision.hidden_player for collision in collisions}

    ambiguous = [row for row in rows if len(row.concrete_states) > 1]
    ambiguous_nonroot = [
        row for row in ambiguous if (row.round_index, row.actor) != (3, 0)
    ]
    ge3 = [row for row in ambiguous_nonroot if len(row.concrete_states) >= 3]

    layers: list[tuple[str, int, int, int]] = []
    for round_index, actor in sorted({(row.round_index, row.actor) for row in rows}):
        subset = [row for row in rows if (row.round_index, row.actor) == (round_index, actor)]
        layers.append(
            (
                f"R{round_index}_P{actor}",
                len(subset),
                sum(1 for row in subset if len(row.concrete_states) > 1),
                max((len(row.concrete_states) for row in subset), default=0),
            )
        )

    types = private_types()
    return HSupportGeometry(
        authority=AUTHORITY,
        schema=SCHEMA,
        support_sha256=support_sha256(frozen),
        support_worlds=len(frozen),
        p0_r3_private_types=len({_packet_key(packet) for packet in types["p0_r3"]}),
        p1_r3_private_types=len({_packet_key(packet) for packet in types["p1_r3"]}),
        p0_r4_private_types=len({_packet_key(packet) for packet in types["p0_r4"]}),
        p1_r4_private_types=len({_packet_key(packet) for packet in types["p1_r4"]}),
        reachable_information_states=len(rows),
        ambiguous_information_states=len(ambiguous),
        ambiguous_nonroot_information_states=len(ambiguous_nonroot),
        nonroot_information_states_ge3_states=len(ge3),
        max_compatible_states=max((len(row.concrete_states) for row in rows), default=0),
        p0_hidden_discard_collision=0 in hidden_players,
        p1_hidden_discard_collision=1 in hidden_players,
        layers=tuple(layers),
    )


__all__ = [
    "AUTHORITY",
    "SCHEMA",
    "HSupportGeometry",
    "private_types",
    "worlds",
    "public_pre_r3_state",
    "support_sha256",
    "validate_physical_support",
    "summarize_geometry",
]
