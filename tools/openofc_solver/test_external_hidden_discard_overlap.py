from __future__ import annotations

import math

import pytest

from engine import Board, parse_cards
from external_hidden_discard_overlap import (
    AUTHORITY,
    OverlapWorld,
    find_hidden_discard_collisions,
    run_overlap_infoset_uct,
    validate_worlds,
    with_overlap_world,
)
from strategic_cfr import DealPlan, HUState, information_state_key


def B(top: str, middle: str, bottom: str) -> Board:
    return Board(parse_cards(top), parse_cards(middle), parse_cards(bottom))


def _overlap_worlds() -> tuple[OverlapWorld, ...]:
    p0_types = (
        parse_cards("7c 8c 8h"),
        parse_cards("7c 8c 9d"),
    )
    p1_types = (
        parse_cards("Ah Kh Qh"),
        parse_cards("Ah Kh Ks"),
    )
    p0_r4 = parse_cards("9h Th Td")
    p1_r4 = parse_cards("Ad Kc Qs")
    worlds = []
    for p0_index, p0_r3 in enumerate(p0_types):
        for p1_index, p1_r3 in enumerate(p1_types):
            worlds.append(
                OverlapWorld(
                    world_id=f"p0t{p0_index}-p1t{p1_index}",
                    p0_r3=p0_r3,
                    p1_r3=p1_r3,
                    p0_r4=p0_r4,
                    p1_r4=p1_r4,
                )
            )
    return tuple(worlds)


def _public_pre_r3_state() -> HUState:
    worlds = _overlap_worlds()
    w = worlds[0]
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
            B("Qc Qd", "2c 2d 3c 3d", "4c 5c 6c"),
            B("Jc Jd", "4h 5h 6h 7h", "9c Tc Jh"),
        ),
        discards=(parse_cards("2h 3h"), parse_cards("2s 3s")),
        public_history=(),
    )


def test_four_world_support_is_physical_and_private_types_are_observable_only_to_owner() -> None:
    worlds = validate_worlds(_overlap_worlds())
    base = _public_pre_r3_state()
    assert len(worlds) == 4
    states = [with_overlap_world(base, world) for world in worlds]
    for state in states:
        dealt = state.plan.dealt_cards()
        assert len(dealt) == 34
        assert len(set(dealt)) == 34

    # P0 sees its own R3 type, but does not see P1's R3 type.
    keys = {(world.world_id, information_state_key(state)) for world, state in zip(worlds, states)}
    by_p0_type = {}
    for world, key in keys:
        p0_type = world.split("-")[0]
        by_p0_type.setdefault(p0_type, set()).add(key)
    assert all(len(values) == 1 for values in by_p0_type.values())
    assert len({next(iter(values)) for values in by_p0_type.values()}) == 2


def test_explicit_hidden_discard_collisions_exist_in_both_directions() -> None:
    worlds = _overlap_worlds()
    base = _public_pre_r3_state()
    witnesses = find_hidden_discard_collisions(base, worlds)
    assert len(witnesses) >= 2
    p0_hidden = next(row for row in witnesses if row.hidden_player == 0)
    p1_hidden = next(row for row in witnesses if row.hidden_player == 1)
    assert p0_hidden.observing_player == 1
    assert p0_hidden.round_index_after_action == 3
    assert p0_hidden.discarded_a != p0_hidden.discarded_b
    assert p1_hidden.observing_player == 0
    assert p1_hidden.round_index_after_action == 4
    assert p1_hidden.discarded_a != p1_hidden.discarded_b


def test_infoset_uct_observes_nonroot_multiworld_nodes_deterministically() -> None:
    worlds = _overlap_worlds()
    base = _public_pre_r3_state()
    kwargs = dict(iterations=6_000, seed=2026082891, exploration=1.25)
    a = run_overlap_infoset_uct(base, worlds, **kwargs)
    b = run_overlap_infoset_uct(base, worlds, **kwargs)
    assert a == b
    assert a.authority == AUTHORITY
    assert a.support_worlds == 4
    assert a.ambiguous_information_states > 0
    assert a.ambiguous_nonroot_information_states > 0
    assert a.max_compatible_worlds >= 2
    assert math.isfinite(a.terminal_mean_u0)
    assert any(
        len(row.compatible_worlds) > 1 and (row.round_index, row.actor) != (3, 0)
        for row in a.node_stats
    )


def test_validation_fails_closed() -> None:
    worlds = _overlap_worlds()
    base = _public_pre_r3_state()
    with pytest.raises(ValueError, match="at least four"):
        validate_worlds(worlds[:3])
    with pytest.raises(ValueError, match="iterations"):
        run_overlap_infoset_uct(base, worlds, iterations=0, seed=1)
    bad = OverlapWorld(
        world_id="bad",
        p0_r3=worlds[0].p0_r3,
        p1_r3=worlds[0].p0_r3,
        p0_r4=worlds[0].p0_r4,
        p1_r4=worlds[0].p1_r4,
    )
    with pytest.raises(ValueError, match="reuses a card"):
        validate_worlds((worlds[0], worlds[1], worlds[2], bad))
