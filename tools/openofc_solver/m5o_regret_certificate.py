from __future__ import annotations

"""Fail-closed reduced-game regret-derived exploitability certificate.

This module intentionally supports only deterministic, undiscounted standard CFR
on the exact two-round perfect-recall HU benchmark.  It is a feasibility auditor,
not a production M4Z certification oracle.
"""

from dataclasses import dataclass
import hashlib
import json
import math

from deepofc.hu_two_round_br import exact_nash_conv
from deepofc.hu_two_round_cfr import TwoRoundFullTreeCFR

SCHEMA = "openofc-m5o-two-round-regret-certificate-v1"
AUTHORITY = "EXACT_FULL_TREE_CFR_REGRET_BOUND_FEASIBILITY_NOT_PRODUCTION_CERTIFICATION"
NUMERICAL_TOLERANCE = 1e-9


def _canonical_bytes(payload: object) -> bytes:
    return json.dumps(
        payload, sort_keys=True, separators=(",", ":"), allow_nan=False
    ).encode("utf-8")


def _sha(payload: object) -> str:
    return hashlib.sha256(_canonical_bytes(payload)).hexdigest()


def _finite(value: float, label: str) -> float:
    number = float(value)
    if not math.isfinite(number):
        raise ValueError(f"{label} must be finite")
    return number


@dataclass(frozen=True)
class PlayerRegretBound:
    player: int
    infosets: int
    positive_max_cumulative_cf_regret_sum: float
    average_external_regret_upper_bound: float

    def __post_init__(self) -> None:
        if self.player not in (0, 1):
            raise ValueError("M5O player must be 0 or 1")
        if self.infosets <= 0:
            raise ValueError("M5O player must have at least one infoset")
        if self.positive_max_cumulative_cf_regret_sum < 0.0:
            raise ValueError("M5O cumulative regret bound cannot be negative")
        if self.average_external_regret_upper_bound < 0.0:
            raise ValueError("M5O average regret bound cannot be negative")
        _finite(
            self.positive_max_cumulative_cf_regret_sum,
            "positive_max_cumulative_cf_regret_sum",
        )
        _finite(
            self.average_external_regret_upper_bound,
            "average_external_regret_upper_bound",
        )

    def payload(self) -> dict[str, object]:
        return {
            "player": self.player,
            "infosets": self.infosets,
            "positive_max_cumulative_cf_regret_sum": self.positive_max_cumulative_cf_regret_sum,
            "average_external_regret_upper_bound": self.average_external_regret_upper_bound,
        }


@dataclass(frozen=True)
class TwoRoundRegretCertificate:
    iterations: int
    player0: PlayerRegretBound
    player1: PlayerRegretBound
    nash_conv_upper_bound: float
    exploitability_upper_bound: float
    exact_nash_conv: float
    exact_exploitability: float
    nash_conv_bound_slack: float
    tolerance: float
    bound_verified: bool
    sha256: str
    schema: str = SCHEMA
    authority: str = AUTHORITY

    def __post_init__(self) -> None:
        if self.schema != SCHEMA or self.authority != AUTHORITY:
            raise ValueError("unsupported M5O certificate identity")
        if self.iterations <= 0:
            raise ValueError("M5O certificate requires completed CFR iterations")
        for label, value in (
            ("nash_conv_upper_bound", self.nash_conv_upper_bound),
            ("exploitability_upper_bound", self.exploitability_upper_bound),
            ("exact_nash_conv", self.exact_nash_conv),
            ("exact_exploitability", self.exact_exploitability),
            ("nash_conv_bound_slack", self.nash_conv_bound_slack),
            ("tolerance", self.tolerance),
        ):
            _finite(value, label)
        if self.nash_conv_upper_bound < 0.0 or self.exploitability_upper_bound < 0.0:
            raise ValueError("M5O upper bounds cannot be negative")
        if self.exact_nash_conv < -self.tolerance:
            raise ValueError("exact NashConv cannot be materially negative")
        if not self.bound_verified:
            raise ValueError("M5O certificate cannot materialize with an unverified bound")
        if self.sha256 != _sha(self.unsigned_payload()):
            raise ValueError("M5O certificate SHA-256 mismatch")

    def unsigned_payload(self) -> dict[str, object]:
        return {
            "schema": self.schema,
            "authority": self.authority,
            "iterations": self.iterations,
            "player0": self.player0.payload(),
            "player1": self.player1.payload(),
            "nash_conv_upper_bound": self.nash_conv_upper_bound,
            "exploitability_upper_bound": self.exploitability_upper_bound,
            "exact_nash_conv": self.exact_nash_conv,
            "exact_exploitability": self.exact_exploitability,
            "nash_conv_bound_slack": self.nash_conv_bound_slack,
            "tolerance": self.tolerance,
            "bound_verified": self.bound_verified,
        }

    def payload(self) -> dict[str, object]:
        payload = self.unsigned_payload()
        payload["sha256"] = self.sha256
        return payload


def _player_bound(solver: TwoRoundFullTreeCFR, player: int) -> PlayerRegretBound:
    total = 0.0
    infosets = 0
    for info, regrets in solver.regrets.items():
        if info.player != player:
            continue
        infosets += 1
        if not regrets:
            raise ValueError("M5O encountered an empty regret vector")
        values = tuple(_finite(value, "cumulative counterfactual regret") for value in regrets.values())
        total += max(0.0, max(values))
    if infosets <= 0:
        raise ValueError("M5O found no infosets for player")
    return PlayerRegretBound(
        player=player,
        infosets=infosets,
        positive_max_cumulative_cf_regret_sum=float(total),
        average_external_regret_upper_bound=float(total) / float(solver.iteration),
    )


def certify_two_round_standard_cfr(
    solver: TwoRoundFullTreeCFR,
    *,
    tolerance: float = NUMERICAL_TOLERANCE,
) -> TwoRoundRegretCertificate:
    """Audit the CFR decomposition bound against independently exact NashConv."""

    if solver.variant != "cfr":
        raise ValueError(
            "M5O regret certificate supports only undiscounted standard CFR"
        )
    if solver.iteration <= 0:
        raise ValueError("M5O regret certificate requires at least one iteration")
    tolerance = _finite(tolerance, "tolerance")
    if tolerance < 0.0:
        raise ValueError("M5O tolerance cannot be negative")

    p0 = _player_bound(solver, 0)
    p1 = _player_bound(solver, 1)
    nash_bound = (
        p0.average_external_regret_upper_bound
        + p1.average_external_regret_upper_bound
    )

    profile = solver.average_profile()
    exact_nc, _, _ = exact_nash_conv(solver.game, profile)
    exact_nc = max(0.0, _finite(exact_nc, "exact_nash_conv"))
    slack = float(nash_bound) - exact_nc
    scale = max(1.0, abs(float(nash_bound)), abs(exact_nc))
    allowed = tolerance * scale
    verified = slack >= -allowed
    if not verified:
        raise RuntimeError(
            "M5O regret-derived NashConv bound was violated: "
            f"bound={nash_bound} exact={exact_nc} slack={slack} allowed={allowed}"
        )

    payload: dict[str, object] = {
        "schema": SCHEMA,
        "authority": AUTHORITY,
        "iterations": int(solver.iteration),
        "player0": p0.payload(),
        "player1": p1.payload(),
        "nash_conv_upper_bound": float(nash_bound),
        "exploitability_upper_bound": 0.5 * float(nash_bound),
        "exact_nash_conv": exact_nc,
        "exact_exploitability": 0.5 * exact_nc,
        "nash_conv_bound_slack": slack,
        "tolerance": tolerance,
        "bound_verified": True,
    }
    return TwoRoundRegretCertificate(
        iterations=int(payload["iterations"]),
        player0=p0,
        player1=p1,
        nash_conv_upper_bound=float(payload["nash_conv_upper_bound"]),
        exploitability_upper_bound=float(payload["exploitability_upper_bound"]),
        exact_nash_conv=float(payload["exact_nash_conv"]),
        exact_exploitability=float(payload["exact_exploitability"]),
        nash_conv_bound_slack=float(payload["nash_conv_bound_slack"]),
        tolerance=float(payload["tolerance"]),
        bound_verified=True,
        sha256=_sha(payload),
    )
