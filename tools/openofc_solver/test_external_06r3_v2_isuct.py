from __future__ import annotations

from collections import defaultdict

from deepofc.hu_three_round_sequential_v2 import HUThreeRoundSequentialSubgameV2
from v2_information_set_uct import V2InformationSetUCT


def test_future_chance_does_not_change_v2_root_infoset() -> None:
    game = HUThreeRoundSequentialSubgameV2()
    grouped = defaultdict(set)
    for outcome in game.outcomes:
        state = game.initial_state(outcome)
        info = game.info(state)
        grouped[outcome.first_player].add(info)

    assert set(grouped) == {0, 1}
    assert len(grouped[0]) == 1
    assert len(grouped[1]) == 1


def test_v2_isuct_accounting_and_profile() -> None:
    game = HUThreeRoundSequentialSubgameV2()
    solver = V2InformationSetUCT(game, exploration=2.0, seed=20260830)
    solver.run(256)

    assert solver.iterations == 256
    assert solver.terminal_evaluations == 256
    assert solver.accounting_exact()
    assert solver.nodes

    profile = solver.visit_profile()
    assert profile
    for info, distribution in profile.items():
        assert set(distribution) == set(game.actions(info))
        assert abs(sum(distribution.values()) - 1.0) <= 1e-12
        assert all(probability >= 0.0 for probability in distribution.values())


def test_v2_isuct_reproducible() -> None:
    game = HUThreeRoundSequentialSubgameV2()
    a = V2InformationSetUCT(game, exploration=2.0, seed=20260831)
    b = V2InformationSetUCT(game, exploration=2.0, seed=20260831)
    a.run(128)
    b.run(128)

    pa = {
        info: {action.key(): probability for action, probability in dist.items()}
        for info, dist in a.visit_profile().items()
    }
    pb = {
        info: {action.key(): probability for action, probability in dist.items()}
        for info, dist in b.visit_profile().items()
    }
    assert pa == pb
