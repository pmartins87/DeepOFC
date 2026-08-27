from __future__ import annotations

import pytest

from deepofc.hu_two_round_cfr import TwoRoundFullTreeCFR
from deepofc.hu_two_round_joker import HUTwoRoundJokerSubgame
from m5o_regret_certificate import (
    AUTHORITY,
    SCHEMA,
    certify_two_round_standard_cfr,
)


def test_m5o_refuses_nonstandard_or_empty_solver() -> None:
    game = HUTwoRoundJokerSubgame()
    with pytest.raises(ValueError, match="only undiscounted standard CFR"):
        certify_two_round_standard_cfr(TwoRoundFullTreeCFR(game, variant="cfr_plus"))
    with pytest.raises(ValueError, match="at least one iteration"):
        certify_two_round_standard_cfr(TwoRoundFullTreeCFR(game, variant="cfr"))


def test_standard_cfr_regret_bound_dominates_exact_nashconv() -> None:
    game = HUTwoRoundJokerSubgame()
    solver = TwoRoundFullTreeCFR(game, variant="cfr")
    solver.run(1)
    cert = certify_two_round_standard_cfr(solver)

    assert cert.schema == SCHEMA
    assert cert.authority == AUTHORITY
    assert cert.iterations == 1
    assert cert.bound_verified is True
    assert cert.player0.infosets > 0
    assert cert.player1.infosets > 0
    assert cert.nash_conv_upper_bound + cert.tolerance >= cert.exact_nash_conv
    assert cert.exploitability_upper_bound == pytest.approx(
        0.5 * cert.nash_conv_upper_bound
    )
    assert cert.exact_exploitability == pytest.approx(0.5 * cert.exact_nash_conv)
    assert cert.sha256 == cert.payload()["sha256"]
