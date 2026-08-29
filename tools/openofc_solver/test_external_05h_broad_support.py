from __future__ import annotations

from external_05h_broad_support import (
    private_types,
    public_pre_r3_state,
    support_sha256,
    validate_physical_support,
    worlds,
)


def test_05h_frozen_cartesian_schedule_and_physical_worlds() -> None:
    types = private_types()
    assert {key: len(value) for key, value in types.items()} == {
        "p0_r3": 4,
        "p1_r3": 4,
        "p0_r4": 3,
        "p1_r4": 3,
    }
    support = worlds()
    assert len(support) == 144
    assert len({world.world_id for world in support}) == 144
    validate_physical_support(public_pre_r3_state(), support)


def test_05h_support_hash_is_deterministic() -> None:
    first = worlds()
    second = worlds()
    assert support_sha256(first) == support_sha256(second)
    assert len(support_sha256(first)) == 64
