import math

from deepofc.hu_cfr import FullTreeCFR
from deepofc.hu_subgame import HUFinalRoundSubgame


def _assert_profile_is_normalized(game, profile):
    assert set(profile) == set(game.info_actions)
    for info, legal in game.info_actions.items():
        dist = profile[info]
        assert set(dist) == set(legal)
        assert all(probability >= 0.0 for probability in dist.values())
        assert abs(sum(dist.values()) - 1.0) < 1e-12


def test_cfr_plus_and_dcfr_keep_valid_behavioral_profiles():
    game = HUFinalRoundSubgame()
    for variant in ("cfr_plus", "dcfr"):
        solver = FullTreeCFR(game, variant=variant)
        solver.run(2)
        _assert_profile_is_normalized(game, solver.current_profile())
        _assert_profile_is_normalized(game, solver.average_profile())
        snapshot = solver.snapshot()
        assert snapshot.iteration == 2
        assert math.isfinite(snapshot.expected_u0)
        assert math.isfinite(snapshot.exploitability)
        assert snapshot.exploitability >= -1e-12
