from __future__ import annotations

"""Exact reduced-game exploration-support feasibility for Appendix-C bounds."""

from dataclasses import asdict, dataclass
import hashlib
import json
import math

from deepofc.hu_two_round import HUTwoRoundSubgame, StrategyProfile
from m5q_support_range_feasibility import external_sampling_support_report
from m5q_variance_mstar_floor import appendix_c_mstar_zero_variance_floor

SCHEMA = "openofc-m5q-exploration-support-floor-v1"
AUTHORITY = "EXPLORATION_SUPPORTED_APPENDIX_C_FLOOR_NOT_CERTIFICATION"


def _canonical_bytes(payload: object) -> bytes:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")


def _sha(payload: object) -> str:
    return hashlib.sha256(_canonical_bytes(payload)).hexdigest()


def uniform_exploration_mix(
    game: HUTwoRoundSubgame,
    profile: StrategyProfile,
    *,
    epsilon: float,
) -> dict:
    eps = float(epsilon)
    if not math.isfinite(eps) or not (0.0 < eps <= 1.0):
        raise ValueError("epsilon must be in (0,1]")
    mixed = {}
    for info, actions in game.info_actions.items():
        base = game._distribution(profile, info)
        uniform = 1.0 / len(actions)
        mixed[info] = {
            action: (1.0 - eps) * base[action] + eps * uniform
            for action in actions
        }
    return mixed


@dataclass(frozen=True)
class ExplorationFloorResult:
    epsilon: float
    global_sampling_floor: float
    player0_sampling_floor: float
    player1_sampling_floor: float
    zero_probability_histories: int
    exact_exploitability: float
    appendix_c_bound_at_probe_iterations: float
    appendix_c_required_iterations_for_target: int
    appendix_c_payload_sha256: str
    support_payload_sha256: str
    authority: str = AUTHORITY
    schema: str = SCHEMA
    sha256: str = ""

    def unsigned_payload(self) -> dict[str, object]:
        return {
            "schema": self.schema,
            "authority": self.authority,
            "epsilon": self.epsilon,
            "global_sampling_floor": self.global_sampling_floor,
            "player0_sampling_floor": self.player0_sampling_floor,
            "player1_sampling_floor": self.player1_sampling_floor,
            "zero_probability_histories": self.zero_probability_histories,
            "exact_exploitability": self.exact_exploitability,
            "appendix_c_bound_at_probe_iterations": self.appendix_c_bound_at_probe_iterations,
            "appendix_c_required_iterations_for_target": self.appendix_c_required_iterations_for_target,
            "appendix_c_payload_sha256": self.appendix_c_payload_sha256,
            "support_payload_sha256": self.support_payload_sha256,
            "production_certification_eligible": False,
            "real_routes_certified": 0,
        }

    def payload(self) -> dict[str, object]:
        payload = self.unsigned_payload()
        payload["sha256"] = self.sha256
        return payload


def evaluate_exploration_floor(
    game: HUTwoRoundSubgame,
    base_profile: StrategyProfile,
    *,
    epsilon: float,
    utility_range: float,
    target_exploitability: float,
    probe_iterations: int,
) -> ExplorationFloorResult:
    mixed = uniform_exploration_mix(game, base_profile, epsilon=epsilon)
    support = external_sampling_support_report(
        game, mixed, profile_id=f"epsilon-mix:{float(epsilon):.8f}"
    )
    p0_floor = support.player0_traverser.minimum_sampling_probability
    p1_floor = support.player1_traverser.minimum_sampling_probability
    delta = min(p0_floor, p1_floor)
    zero_histories = (
        support.player0_traverser.zero_probability_histories
        + support.player1_traverser.zero_probability_histories
    )
    if zero_histories != 0 or delta <= 0.0:
        raise AssertionError("positive exploration mixture must restore full terminal support")

    floor = appendix_c_mstar_zero_variance_floor(
        game,
        mixed,
        utility_range=utility_range,
        sampling_probability_floor=delta,
    )
    exact_exploitability = 0.5 * floor.exact_nash_conv
    unsigned: dict[str, object] = {
        "schema": SCHEMA,
        "authority": AUTHORITY,
        "epsilon": float(epsilon),
        "global_sampling_floor": delta,
        "player0_sampling_floor": p0_floor,
        "player1_sampling_floor": p1_floor,
        "zero_probability_histories": zero_histories,
        "exact_exploitability": exact_exploitability,
        "appendix_c_bound_at_probe_iterations": floor.bound_at(probe_iterations),
        "appendix_c_required_iterations_for_target": floor.required_iterations(target_exploitability),
        "appendix_c_payload_sha256": floor.sha256,
        "support_payload_sha256": support.sha256,
        "production_certification_eligible": False,
        "real_routes_certified": 0,
    }
    return ExplorationFloorResult(
        epsilon=float(epsilon),
        global_sampling_floor=delta,
        player0_sampling_floor=p0_floor,
        player1_sampling_floor=p1_floor,
        zero_probability_histories=zero_histories,
        exact_exploitability=exact_exploitability,
        appendix_c_bound_at_probe_iterations=floor.bound_at(probe_iterations),
        appendix_c_required_iterations_for_target=floor.required_iterations(target_exploitability),
        appendix_c_payload_sha256=floor.sha256,
        support_payload_sha256=support.sha256,
        sha256=_sha(unsigned),
    )
