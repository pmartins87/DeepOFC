from __future__ import annotations

"""Optimistic zero-variance floor for Gibson et al. Theorem 2.

This module deliberately sets the theorem's variance term to its impossible best
case, zero. If the resulting iteration floor is already impractical, no empirical
variance estimation can make this theorem a practical primary certificate.
"""

from dataclasses import asdict, dataclass
import hashlib
import json
import math

from deepofc.hu_two_round import HUTwoRoundSubgame

SCHEMA = "openofc-m5q-variance-theorem-zero-variance-floor-v1"
AUTHORITY = "GIBSON_THEOREM2_ZERO_VARIANCE_OPTIMISTIC_FLOOR_NOT_CERTIFICATION"
THEOREM_SOURCE = "Gibson-Lanctot-Burch-Szafron-Bowling AAAI 2012 Theorem 2"


def _canonical_bytes(payload: object) -> bytes:
    return json.dumps(
        payload, sort_keys=True, separators=(",", ":"), allow_nan=False
    ).encode("utf-8")


def _sha(payload: object) -> str:
    return hashlib.sha256(_canonical_bytes(payload)).hexdigest()


@dataclass(frozen=True)
class PlayerInfoStructure:
    player: int
    infosets: int
    max_actions: int


def player_info_structure(game: HUTwoRoundSubgame, player: int) -> PlayerInfoStructure:
    if player not in (0, 1):
        raise ValueError("player must be 0 or 1")
    rows = [
        len(actions)
        for info, actions in game.info_actions.items()
        if info.player == player
    ]
    if not rows:
        raise RuntimeError("M5Q variance floor found no player infosets")
    if min(rows) <= 0:
        raise RuntimeError("M5Q variance floor found empty action set")
    return PlayerInfoStructure(
        player=player,
        infosets=len(rows),
        max_actions=max(rows),
    )


@dataclass(frozen=True)
class ZeroVarianceTheoremFloor:
    delta_hat: float
    player0: PlayerInfoStructure
    player1: PlayerInfoStructure
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
            "delta_hat": self.delta_hat,
            "variance_assumption": 0.0,
            "player0": asdict(self.player0),
            "player1": asdict(self.player1),
            "exploitability_coefficient": self.exploitability_coefficient,
            "certification_eligible": False,
        }

    def payload(self) -> dict[str, object]:
        payload = self.unsigned_payload()
        payload["sha256"] = self.sha256
        return payload

    def required_iterations(self, target_exploitability: float) -> int:
        target = float(target_exploitability)
        if not math.isfinite(target) or target <= 0.0:
            raise ValueError("target exploitability must be finite and positive")
        return max(1, math.ceil((self.exploitability_coefficient / target) ** 2))

    def bound_at(self, iterations: int) -> float:
        if iterations <= 0:
            raise ValueError("iterations must be positive")
        return self.exploitability_coefficient / math.sqrt(float(iterations))


def zero_variance_theorem_floor(
    game: HUTwoRoundSubgame,
    *,
    delta_hat: float,
) -> ZeroVarianceTheoremFloor:
    delta = float(delta_hat)
    if not math.isfinite(delta) or delta <= 0.0:
        raise ValueError("delta_hat must be finite and positive")
    p0 = player_info_structure(game, 0)
    p1 = player_info_structure(game, 1)
    coefficient = 0.5 * delta * (
        float(p0.infosets) * math.sqrt(float(p0.max_actions))
        + float(p1.infosets) * math.sqrt(float(p1.max_actions))
    )
    unsigned: dict[str, object] = {
        "schema": SCHEMA,
        "authority": AUTHORITY,
        "theorem_source": THEOREM_SOURCE,
        "delta_hat": delta,
        "variance_assumption": 0.0,
        "player0": asdict(p0),
        "player1": asdict(p1),
        "exploitability_coefficient": coefficient,
        "certification_eligible": False,
    }
    return ZeroVarianceTheoremFloor(
        delta_hat=delta,
        player0=p0,
        player1=p1,
        exploitability_coefficient=coefficient,
        sha256=_sha(unsigned),
    )
