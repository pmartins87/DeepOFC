from __future__ import annotations

from external_05g_broad_support import (
    AUTHORITY,
    broad_private_types,
    broad_worlds,
    public_pre_r3_state,
    support_sha256,
    validate_broad_physical_support,
)
from external_hidden_discard_overlap import find_hidden_discard_collisions, with_overlap_world
from strategic_cfr import information_state_key


def _packet_key(packet):
    return tuple(sorted(str(card) for card in packet))


def test_05g_frozen_cartesian_support_has_required_private_type_counts() -> None:
    types = broad_private_types()
    worlds = broad_worlds()
    assert AUTHORITY == "BROAD_HIDDEN_INFORMATION_REDUCED_GAME_SHADOW_ONLY"
    assert len(worlds) == 36
    assert len({_packet_key(packet) for packet in types["p0_r3"]}) == 3
    assert len({_packet_key(packet) for packet in types["p1_r3"]}) == 3
    assert len({_packet_key(packet) for packet in types["p0_r4"]}) == 2
    assert len({_packet_key(packet) for packet in types["p1_r4"]}) == 2
    assert support_sha256(worlds) == support_sha256(broad_worlds())


def test_05g_every_world_is_one_physically_unique_34_card_hu_deal() -> None:
    worlds = broad_worlds()
    base = public_pre_r3_state()
    validate_broad_physical_support(base, worlds)
    for world in worlds:
        dealt = with_overlap_world(base, world).plan.dealt_cards()
        assert len(dealt) == 34
        assert len(set(dealt)) == 34


def test_05g_private_information_is_visible_to_owner_but_opponent_types_do_not_leak_at_root() -> None:
    worlds = broad_worlds()
    base = public_pre_r3_state()
    by_p0_type = {}
    for world in worlds:
        key = information_state_key(with_overlap_world(base, world))
        p0_type = _packet_key(world.p0_r3)
        by_p0_type.setdefault(p0_type, set()).add(key)
    # P0's incoming R3 packet distinguishes its own three root infosets.
    assert len(by_p0_type) == 3
    assert all(len(keys) == 1 for keys in by_p0_type.values())
    assert len({next(iter(keys)) for keys in by_p0_type.values()}) == 3


def test_05g_contains_hidden_discard_collision_witnesses_in_both_directions() -> None:
    worlds = broad_worlds()
    base = public_pre_r3_state()
    witnesses = find_hidden_discard_collisions(base, worlds)
    hidden_players = {row.hidden_player for row in witnesses}
    assert 0 in hidden_players
    assert 1 in hidden_players
    assert all(row.discarded_a != row.discarded_b for row in witnesses)
