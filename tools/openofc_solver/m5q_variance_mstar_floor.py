from __future__ import annotations

"""Appendix-C M_i(sigma*) zero-variance feasibility accounting.

This module evaluates only exact reduced-game profiles.  It uses an independently
exact pure best response to compute the strategy-dependent M_i(sigma*) constant
from Gibson's long-form Appendix C, Theorem C.1.  Estimator variance is fixed to
zero and the sampling-probability floor is caller supplied; therefore results are
optimistic feasibility floors, never production certificates.
"""

from dataclasses import asdict, dataclass
import hashlib
import json
import math
from typing import Hashable, Mapping

from deepofc.actions import NormalPlacementAction
from deepofc.hu_two_round import HUTwoRoundSubgame, StrategyProfile, TwoRoundInfoSet
from deepofc.hu_two_round_br import TwoRoundBestResponse, exact_best_response
from m5p_external_sampling_theoretical_bound import (
    player_sequence_structure,
)
from m5q_variance_theorem_floor import player_info_structure

SCHEMA = "openofc-m5q-appendix-c-mstar-zero-variance-floor-v1"
AUTHORITY = "APPENDIX_C_MSTAR_VARIANCE_FLOOR_FEASIBILITY_NOT_CERTIFICATION"
THEOREM_SOURCE = "Gibson long-form Appendix C Theorem C.1"


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


def _own_prefix(info: TwoRoundInfoSet) -> tuple[Hashable, ...]:
    if info.round_index == 3:
        return ()
    if info.round_index == 4:
        if info.own_round3_action is None:
            raise ValueError("round-4 infoset missing remembered own round-3 action")
        return (_freeze(info.own_round3_action),)
    raise ValueError("M5Q M-star floor only supports the exact two-round benchmark")


def _round3_predecessor(info: TwoRoundInfoSet) -> TwoRoundInfoSet:
    if info.round_index != 4:
        raise ValueError("predecessor reconstruction requires round-4 infoset")
    observed = info.opponent_round3_public if info.role == "second" else None
    return TwoRoundInfoSet(
        player=info.player,
        round_index=3,
        role=info.role,
        own_round3_hand=info.own_round3_hand,
        observed_current_first_public=observed,
    )


@dataclass(frozen=True)
class BestResponseMStructure:
    player: int
    infosets: int
    prefix_groups: int
    reached_prefix_groups: int
    static_m_value: float
    best_response_m_value: float
    max_actions: int

    def payload(self) -> dict[str, object]:
        return asdict(self)


def best_response_m_structure(
    game: HUTwoRoundSubgame,
    response: TwoRoundBestResponse,
) -> BestResponseMStructure:
    player = response.player
    if player not in (0, 1):
        raise ValueError("response player must be 0 or 1")

    groups: dict[tuple[Hashable, ...], list[TwoRoundInfoSet]] = {}
    for info in game.info_actions:
        if info.player == player:
            groups.setdefault(_own_prefix(info), []).append(info)
    if not groups:
        raise RuntimeError("M5Q M-star found no player prefix groups")

    reached_groups = 0
    m_star = 0.0
    for prefix, infos in groups.items():
        reaches: list[float] = []
        for info in infos:
            if info.round_index == 3:
                reaches.append(1.0)
                continue
            predecessor = _round3_predecessor(info)
            chosen = response.choices.get(predecessor)
            if chosen is None:
                raise AssertionError("exact best response missing round-3 predecessor")
            remembered = _freeze(info.own_round3_action)
            reaches.append(1.0 if _freeze(chosen.key()) == remembered else 0.0)
        group_reach = max(reaches)
        if group_reach > 0.0:
            reached_groups += 1
        m_star += group_reach * math.sqrt(float(len(infos)))

    static = player_sequence_structure(game, player)
    info_structure = player_info_structure(game, player)
    if info_structure.infosets != static.infosets:
        raise AssertionError("M5Q information-structure disagreement")
    if len(groups) != static.prefix_groups:
        raise AssertionError("M5Q prefix-group disagreement")
    if not (0.0 < m_star <= static.m_value + 1e-12):
        raise AssertionError(
            f"invalid best-response M-value: m*={m_star} static={static.m_value}"
        )

    return BestResponseMStructure(
        player=player,
        infosets=static.infosets,
        prefix_groups=static.prefix_groups,
        reached_prefix_groups=reached_groups,
        static_m_value=static.m_value,
        best_response_m_value=m_star,
        max_actions=info_structure.max_actions,
    )


@dataclass(frozen=True)
class AppendixCMStarFloor:
    utility_range: float
    sampling_probability_floor: float
    delta_hat_prime: float
    player0: BestResponseMStructure
    player1: BestResponseMStructure
    br0_value: float
    br1_value: float
    exact_nash_conv: float
    exploitability_coefficient: float
    authority: str = AUTHORITY
    theorem_source: str = THEOREM_SOURCE
    schema: str = SCHEMA
    sha256: str = ""

    def unsigned_payload(self) -> dict[str, object]:
        return {
            "schema": self.schema,
            "authority": self.authority,
            "theorem_source": self.theorem_source,
            "utility_range": self.utility_range,
            "sampling_probability_floor": self.sampling_probability_floor,
            "delta_hat_prime": self.delta_hat_prime,
            "variance_assumption": 0.0,
            "player0": self.player0.payload(),
            "player1": self.player1.payload(),
            "br0_value": self.br0_value,
            "br1_value": self.br1_value,
            "exact_nash_conv": self.exact_nash_conv,
            "exploitability_coefficient": self.exploitability_coefficient,
            "certification_eligible": False,
            "real_routes_certified": 0,
        }

    def payload(self) -> dict[str, object]:
        payload = self.unsigned_payload()
        payload["sha256"] = self.sha256
        return payload

    def bound_at(self, iterations: int) -> float:
        if iterations <= 0:
            raise ValueError("iterations must be positive")
        return self.exploitability_coefficient / math.sqrt(float(iterations))

    def required_iterations(self, target_exploitability: float) -> int:
        target = float(target_exploitability)
        if not math.isfinite(target) or target <= 0.0:
            raise ValueError("target exploitability must be finite and positive")
        return max(1, math.ceil((self.exploitability_coefficient / target) ** 2))


def appendix_c_mstar_zero_variance_floor(
    game: HUTwoRoundSubgame,
    profile: StrategyProfile,
    *,
    utility_range: float,
    sampling_probability_floor: float = 1.0,
) -> AppendixCMStarFloor:
    delta_u = float(utility_range)
    if not math.isfinite(delta_u) or delta_u <= 0.0:
        raise ValueError("utility_range must be finite and positive")
    delta = float(sampling_probability_floor)
    if not math.isfinite(delta) or not (0.0 < delta <= 1.0):
        raise ValueError("sampling_probability_floor must be in (0,1]")

    br0 = exact_best_response(game, profile, 0)
    br1 = exact_best_response(game, profile, 1)
    p0 = best_response_m_structure(game, br0)
    p1 = best_response_m_structure(game, br1)
    delta_hat_prime = delta_u / delta
    coefficient = 0.5 * delta_hat_prime * (
        p0.best_response_m_value * math.sqrt(float(p0.max_actions))
        + p1.best_response_m_value * math.sqrt(float(p1.max_actions))
    )
    unsigned: dict[str, object] = {
        "schema": SCHEMA,
        "authority": AUTHORITY,
        "theorem_source": THEOREM_SOURCE,
        "utility_range": delta_u,
        "sampling_probability_floor": delta,
        "delta_hat_prime": delta_hat_prime,
        "variance_assumption": 0.0,
        "player0": p0.payload(),
        "player1": p1.payload(),
        "br0_value": br0.value,
        "br1_value": br1.value,
        "exact_nash_conv": br0.value + br1.value,
        "exploitability_coefficient": coefficient,
        "certification_eligible": False,
        "real_routes_certified": 0,
    }
    return AppendixCMStarFloor(
        utility_range=delta_u,
        sampling_probability_floor=delta,
        delta_hat_prime=delta_hat_prime,
        player0=p0,
        player1=p1,
        br0_value=br0.value,
        br1_value=br1.value,
        exact_nash_conv=br0.value + br1.value,
        exploitability_coefficient=coefficient,
        sha256=_sha(unsigned),
    )
