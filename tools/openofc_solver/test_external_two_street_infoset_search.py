from __future__ import annotations

import pytest

from engine import Board, Card, parse_cards
from external_research_world_sampler import sample_physical_world
from external_two_street_infoset_search import AUTHORITY, TwoStreetWorld, run_two_street_infoset_uct
from strategic_cfr import DealPlan, HUState, information_state_key


def B(top: str, middle: str, bottom: str) -> Board:
    return Board(parse_cards(top), parse_cards(middle), parse_cards(bottom))


def _known_before_hidden_r3_r4() -> tuple[Card, ...]:
    return parse_cards(
        "Qc Qd 2c 2d 3c 3d 4c 5c 6c "
        "Jc Jd 4h 5h 6h 7h 9c Tc Jh "
        "2h 3h 2s 3s "
        "7c 8c 8h"
    )


def _support_worlds() -> tuple[TwoStreetWorld, ...]:
    worlds = []
    for seed in (2026082811, 2026082813, 2026082817, 2026082819, 2026082823, 2026082829):
        sampled = sample_physical_world(
            known_cards=_known_before_hidden_r3_r4(),
            zone_sizes=(("p1_r3", 3), ("p0_r4", 3), ("p1_r4", 3)),
            seed=seed,
        )
        worlds.append(
            TwoStreetWorld(
                world_id=f"seed-{seed}",
                p1_r3=sampled.zone("p1_r3"),
                p0_r4=sampled.zone("p0_r4"),
                p1_r4=sampled.zone("p1_r4"),
            )
        )
    return tuple(worlds)


def _coherent_r3_state(world: TwoStreetWorld) -> HUState:
    plan = DealPlan(
        opening=(
            parse_cards("Qc 2c 3c 4c 5c"),
            parse_cards("Jc 4h 5h 9c Tc"),
        ),
        rounds=(
            (parse_cards("Qd 2d 2h"), parse_cards("Jd 6h 2s")),
            (parse_cards("3d 6c 3h"), parse_cards("7h Jh 3s")),
            (parse_cards("7c 8c 8h"), world.p1_r3),
            (world.p0_r4, world.p1_r4),
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


def test_support_worlds_are_physical_and_root_information_isolated() -> None:
    worlds = _support_worlds()
    root_keys = []
    for world in worlds:
        state = _coherent_r3_state(world)
        dealt = state.plan.dealt_cards()
        assert len(dealt) == 34
        assert len(set(dealt)) == 34
        root_keys.append(information_state_key(state))
    assert len(set(root_keys)) == 1


def test_two_street_q0_is_deterministic_and_reaches_all_four_layers() -> None:
    worlds = _support_worlds()
    state = _coherent_r3_state(worlds[0])
    kwargs = dict(iterations=1_500, seed=2026082831, exploration=1.0)
    a = run_two_street_infoset_uct(state, worlds, **kwargs)
    b = run_two_street_infoset_uct(state, worlds, **kwargs)
    assert a == b
    assert a.authority == AUTHORITY
    assert a.root_information_state_key == information_state_key(state)
    assert a.terminal_episodes == a.iterations
    assert sum(stat.visits for stat in a.root_action_stats) == a.iterations
    assert {(s.round_index, s.actor) for s in a.layer_stats} == {(3, 0), (3, 1), (4, 0), (4, 1)}
    assert a.infoset_count >= 4
    assert a.terminal_min_p0_utility <= a.terminal_mean_p0_utility <= a.terminal_max_p0_utility


def test_two_street_q0_validation_fails_closed() -> None:
    worlds = _support_worlds()
    state = _coherent_r3_state(worlds[0])
    with pytest.raises(ValueError, match="iterations"):
        run_two_street_infoset_uct(state, worlds, iterations=0, seed=1)
    with pytest.raises(ValueError, match="exploration"):
        run_two_street_infoset_uct(state, worlds, iterations=10, seed=1, exploration=-1.0)
    with pytest.raises(ValueError, match="at least two"):
        run_two_street_infoset_uct(state, worlds[:1], iterations=10, seed=1)
    duplicate = TwoStreetWorld(
        world_id="duplicate",
        p1_r3=worlds[0].p1_r3,
        p0_r4=worlds[0].p1_r3,
        p1_r4=worlds[0].p1_r4,
    )
    with pytest.raises(ValueError, match="reuses a physical card"):
        run_two_street_infoset_uct(state, (worlds[0], duplicate), iterations=10, seed=1)
