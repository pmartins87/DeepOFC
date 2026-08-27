from __future__ import annotations

"""M5P classical high-probability External Sampling MCCFR bound accounting.

This module implements only the structural/worst-case theorem feasibility layer
from Lanctot et al. (NeurIPS 2009, corrected Theorem 4). It does not inspect
sampled regret tables and cannot emit a production route certificate.
"""

from dataclasses import asdict, dataclass
import hashlib
import json
import math
from typing import Hashable

from deepofc.hu_two_round import HUTwoRoundSubgame, TwoRoundInfoSet
from deepofc.scoring import (
    BOTTOM_ROYALTY_BY_CATEGORY,
    MIDDLE_ROYALTY_BY_CATEGORY,
    TOP_PAIR_ROYALTY,
    TOP_TRIPS_ROYALTY,
)

SCHEMA = "openofc-m5p-external-sampling-theoretical-bound-v1"
AUTHORITY = "CLASSICAL_EXTERNAL_SAMPLING_HIGH_PROBABILITY_BOUND_FEASIBILITY_ONLY"
THEOREM_SOURCE = (
    "Lanctot-Waugh-Zinkevich-Bowling NeurIPS 2009 corrected Theorem 4"
)


def _canonical_bytes(payload: object) -> bytes:
    return json.dumps(
        payload, sort_keys=True, separators=(",", ":"), allow_nan=False
    ).encode("utf-8")


def _sha(payload: object) -> str:
    return hashlib.sha256(_canonical_bytes(payload)).hexdigest()


def _freeze(value: object) -> Hashable:
    if isinstance(value, tuple):
        return tuple(_freeze(item) for item in value)
    if isinstance(value, list):
        return tuple(_freeze(item) for item in value)
    if isinstance(value, dict):
        return tuple(sorted((_freeze(k), _freeze(v)) for k, v in value.items()))
    if isinstance(value, (str, int, float, bool, type(None))):
        return value
    return repr(value)


def project_raw_pairwise_utility_abs_bound() -> float:
    """Conservative one-sided raw HU OFC point magnitude from frozen scoring."""

    top = max(max(TOP_PAIR_ROYALTY.values()), max(TOP_TRIPS_ROYALTY.values()))
    middle = max(50, max(MIDDLE_ROYALTY_BY_CATEGORY.values()))
    bottom = max(25, max(BOTTOM_ROYALTY_BY_CATEGORY.values()))
    max_royalties = top + middle + bottom
    # Three row points plus a three-point scoop bonus.
    return float(max_royalties + 6)


def project_raw_pairwise_utility_range() -> float:
    """Conservative Delta_u = max utility - min utility for one HU settlement."""

    return 2.0 * project_raw_pairwise_utility_abs_bound()


def _own_prefix(info: TwoRoundInfoSet) -> tuple[Hashable, ...]:
    if info.round_index == 3:
        return ()
    if info.round_index == 4:
        if info.own_round3_action is None:
            raise ValueError("round-4 infoset missing remembered own round-3 action")
        return (_freeze(info.own_round3_action),)
    raise ValueError("M5P only audits the exact two-round benchmark structure")


@dataclass(frozen=True)
class PlayerSequenceStructure:
    player: int
    infosets: int
    prefix_groups: int
    own_action_sequences: int
    m_value: float
    largest_prefix_group: int

    def payload(self) -> dict[str, object]:
        return asdict(self)


def player_sequence_structure(
    game: HUTwoRoundSubgame,
    player: int,
) -> PlayerSequenceStructure:
    if player not in (0, 1):
        raise ValueError("player must be 0 or 1")

    groups: dict[tuple[Hashable, ...], int] = {}
    sequences: set[tuple[Hashable, ...]] = {()}
    infosets = 0

    for info, actions in game.info_actions.items():
        if info.player != player:
            continue
        infosets += 1
        prefix = _own_prefix(info)
        groups[prefix] = groups.get(prefix, 0) + 1
        sequences.add(prefix)
        for action in actions:
            sequences.add((*prefix, _freeze(action.key())))

    if infosets <= 0 or not groups or not sequences:
        raise RuntimeError("M5P found an empty player information structure")
    if sum(groups.values()) != infosets:
        raise AssertionError("M5P prefix grouping lost infosets")

    m_value = sum(math.sqrt(float(count)) for count in groups.values())
    if not math.isfinite(m_value) or m_value <= 0.0:
        raise RuntimeError("M5P produced invalid M-value")

    return PlayerSequenceStructure(
        player=player,
        infosets=infosets,
        prefix_groups=len(groups),
        own_action_sequences=len(sequences),
        m_value=m_value,
        largest_prefix_group=max(groups.values()),
    )


def theorem4_factor(per_player_failure_probability: float) -> float:
    p = float(per_player_failure_probability)
    if not (0.0 < p <= 1.0):
        raise ValueError("per-player failure probability must be in (0,1]")
    return 1.0 + math.sqrt(2.0) / math.sqrt(p)


@dataclass(frozen=True)
class ExternalSamplingTheoreticalBound:
    iterations: int
    overall_failure_probability: float
    per_player_failure_probability: float
    joint_confidence: float
    utility_range: float
    theorem_factor: float
    player0: PlayerSequenceStructure
    player1: PlayerSequenceStructure
    player0_average_regret_upper_bound: float
    player1_average_regret_upper_bound: float
    nash_conv_upper_bound: float
    exploitability_upper_bound: float
    exploitability_coefficient_per_unit_utility_range: float
    authority: str = AUTHORITY
    theorem_source: str = THEOREM_SOURCE
    schema: str = SCHEMA
    sha256: str = ""

    def unsigned_payload(self) -> dict[str, object]:
        return {
            "schema": self.schema,
            "authority": self.authority,
            "theorem_source": self.theorem_source,
            "iterations": self.iterations,
            "overall_failure_probability": self.overall_failure_probability,
            "per_player_failure_probability": self.per_player_failure_probability,
            "joint_confidence": self.joint_confidence,
            "utility_range": self.utility_range,
            "theorem_factor": self.theorem_factor,
            "player0": self.player0.payload(),
            "player1": self.player1.payload(),
            "player0_average_regret_upper_bound": self.player0_average_regret_upper_bound,
            "player1_average_regret_upper_bound": self.player1_average_regret_upper_bound,
            "nash_conv_upper_bound": self.nash_conv_upper_bound,
            "exploitability_upper_bound": self.exploitability_upper_bound,
            "exploitability_coefficient_per_unit_utility_range": self.exploitability_coefficient_per_unit_utility_range,
            "production_certification_eligible": False,
        }

    def payload(self) -> dict[str, object]:
        payload = self.unsigned_payload()
        payload["sha256"] = self.sha256
        return payload


def external_sampling_theoretical_bound(
    game: HUTwoRoundSubgame,
    *,
    iterations: int,
    overall_failure_probability: float = 0.05,
    utility_range: float = 1.0,
) -> ExternalSamplingTheoreticalBound:
    if iterations <= 0:
        raise ValueError("iterations must be positive")
    alpha = float(overall_failure_probability)
    if not (0.0 < alpha < 1.0):
        raise ValueError("overall failure probability must be in (0,1)")
    delta = float(utility_range)
    if not math.isfinite(delta) or delta <= 0.0:
        raise ValueError("utility range must be finite and positive")

    p = alpha / 2.0
    factor = theorem4_factor(p)
    p0 = player_sequence_structure(game, 0)
    p1 = player_sequence_structure(game, 1)

    def player_bound(structure: PlayerSequenceStructure) -> float:
        return (
            factor
            * delta
            * structure.m_value
            * math.sqrt(float(structure.own_action_sequences))
            / math.sqrt(float(iterations))
        )

    r0 = player_bound(p0)
    r1 = player_bound(p1)
    nash_conv = r0 + r1
    exploitability = 0.5 * nash_conv
    coefficient_per_unit = (
        0.5
        * factor
        * (
            p0.m_value * math.sqrt(float(p0.own_action_sequences))
            + p1.m_value * math.sqrt(float(p1.own_action_sequences))
        )
    )

    unsigned: dict[str, object] = {
        "schema": SCHEMA,
        "authority": AUTHORITY,
        "theorem_source": THEOREM_SOURCE,
        "iterations": int(iterations),
        "overall_failure_probability": alpha,
        "per_player_failure_probability": p,
        "joint_confidence": 1.0 - alpha,
        "utility_range": delta,
        "theorem_factor": factor,
        "player0": p0.payload(),
        "player1": p1.payload(),
        "player0_average_regret_upper_bound": r0,
        "player1_average_regret_upper_bound": r1,
        "nash_conv_upper_bound": nash_conv,
        "exploitability_upper_bound": exploitability,
        "exploitability_coefficient_per_unit_utility_range": coefficient_per_unit,
        "production_certification_eligible": False,
    }
    return ExternalSamplingTheoreticalBound(
        iterations=int(iterations),
        overall_failure_probability=alpha,
        per_player_failure_probability=p,
        joint_confidence=1.0 - alpha,
        utility_range=delta,
        theorem_factor=factor,
        player0=p0,
        player1=p1,
        player0_average_regret_upper_bound=r0,
        player1_average_regret_upper_bound=r1,
        nash_conv_upper_bound=nash_conv,
        exploitability_upper_bound=exploitability,
        exploitability_coefficient_per_unit_utility_range=coefficient_per_unit,
        sha256=_sha(unsigned),
    )


def required_iterations_for_exploitability(
    game: HUTwoRoundSubgame,
    *,
    target_exploitability: float,
    overall_failure_probability: float = 0.05,
    utility_range: float = 1.0,
) -> int:
    target = float(target_exploitability)
    if not math.isfinite(target) or target <= 0.0:
        raise ValueError("target exploitability must be finite and positive")
    probe = external_sampling_theoretical_bound(
        game,
        iterations=1,
        overall_failure_probability=overall_failure_probability,
        utility_range=utility_range,
    )
    # B_T = B_1 / sqrt(T). Ceil preserves the requested upper-bound target.
    return max(1, math.ceil((probe.exploitability_upper_bound / target) ** 2))
