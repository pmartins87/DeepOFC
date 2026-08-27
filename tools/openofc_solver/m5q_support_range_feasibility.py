from __future__ import annotations

"""Exact reduced-game utility range and External Sampling support diagnostics."""

from dataclasses import asdict, dataclass
import hashlib
import json
import math
from typing import Iterator

from deepofc.hu_two_round import (
    HUTwoRoundSubgame,
    StrategyProfile,
    TwoRoundChanceOutcome,
)
from deepofc.actions import NormalPlacementAction

SCHEMA = "openofc-m5q-support-range-feasibility-v1"
AUTHORITY = "EXTERNAL_SAMPLING_SUPPORT_RANGE_FEASIBILITY_NOT_CERTIFICATION"


def _canonical_bytes(payload: object) -> bytes:
    return json.dumps(
        payload, sort_keys=True, separators=(",", ":"), allow_nan=False
    ).encode("utf-8")


def _sha(payload: object) -> str:
    return hashlib.sha256(_canonical_bytes(payload)).hexdigest()


def _terminal_histories(
    game: HUTwoRoundSubgame,
    profile: StrategyProfile | None,
) -> Iterator[
    tuple[
        TwoRoundChanceOutcome,
        NormalPlacementAction,
        NormalPlacementAction,
        NormalPlacementAction,
        NormalPlacementAction,
        float,
        float,
        float,
        float,
    ]
]:
    """Enumerate every terminal history, optionally with local profile masses."""

    for outcome in game.outcomes:
        first = outcome.first_player
        second = outcome.second_player
        first_r3_info = game.round3_first_info(outcome)
        first_r3_actions = game.actions(first_r3_info)
        first_r3_dist = (
            game._distribution(profile, first_r3_info) if profile is not None else None
        )

        for first_r3 in first_r3_actions:
            p_first_r3 = 1.0 if first_r3_dist is None else first_r3_dist[first_r3]
            second_r3_info = game.round3_second_info(outcome, first_r3)
            second_r3_actions = game.actions(second_r3_info)
            second_r3_dist = (
                game._distribution(profile, second_r3_info) if profile is not None else None
            )
            for second_r3 in second_r3_actions:
                p_second_r3 = 1.0 if second_r3_dist is None else second_r3_dist[second_r3]
                board0, board1, action0_r3, action1_r3 = game._boards_after_round3(
                    outcome, first_r3, second_r3
                )
                first_own_r3 = action0_r3 if first == 0 else action1_r3
                first_opp_r3 = action1_r3 if first == 0 else action0_r3
                second_own_r3 = action0_r3 if second == 0 else action1_r3
                second_opp_r3 = action1_r3 if second == 0 else action0_r3

                first_r4_info = game.round4_info(
                    outcome,
                    player=first,
                    own_round3_action=first_own_r3,
                    opponent_round3_action=first_opp_r3,
                    current_first_action=None,
                )
                first_r4_actions = game.actions(first_r4_info)
                first_r4_dist = (
                    game._distribution(profile, first_r4_info) if profile is not None else None
                )
                for first_r4 in first_r4_actions:
                    p_first_r4 = 1.0 if first_r4_dist is None else first_r4_dist[first_r4]
                    second_r4_info = game.round4_info(
                        outcome,
                        player=second,
                        own_round3_action=second_own_r3,
                        opponent_round3_action=second_opp_r3,
                        current_first_action=first_r4,
                    )
                    second_r4_actions = game.actions(second_r4_info)
                    second_r4_dist = (
                        game._distribution(profile, second_r4_info)
                        if profile is not None
                        else None
                    )
                    for second_r4 in second_r4_actions:
                        p_second_r4 = (
                            1.0 if second_r4_dist is None else second_r4_dist[second_r4]
                        )
                        yield (
                            outcome,
                            first_r3,
                            second_r3,
                            first_r4,
                            second_r4,
                            p_first_r3,
                            p_second_r3,
                            p_first_r4,
                            p_second_r4,
                        )


@dataclass(frozen=True)
class ExactTerminalUtilityRange:
    terminal_histories: int
    minimum_p0_utility: float
    maximum_p0_utility: float
    utility_range: float

    def payload(self) -> dict[str, object]:
        return asdict(self)


def exact_terminal_utility_range(game: HUTwoRoundSubgame) -> ExactTerminalUtilityRange:
    count = 0
    minimum = math.inf
    maximum = -math.inf
    for outcome, first_r3, second_r3, first_r4, second_r4, *_ in _terminal_histories(
        game, None
    ):
        value = float(
            game.terminal_u0(
                outcome, first_r3, second_r3, first_r4, second_r4
            )
        )
        count += 1
        minimum = min(minimum, value)
        maximum = max(maximum, value)
    if count <= 0 or not math.isfinite(minimum) or not math.isfinite(maximum):
        raise RuntimeError("M5Q exact utility-range audit found no finite terminals")
    if maximum < minimum:
        raise AssertionError("M5Q exact terminal utility range is inverted")
    return ExactTerminalUtilityRange(
        terminal_histories=count,
        minimum_p0_utility=minimum,
        maximum_p0_utility=maximum,
        utility_range=maximum - minimum,
    )


@dataclass(frozen=True)
class TraverserSamplingSupport:
    traverser: int
    terminal_histories: int
    zero_probability_histories: int
    positive_probability_histories: int
    minimum_sampling_probability: float
    minimum_positive_sampling_probability: float | None
    maximum_sampling_probability: float

    @property
    def has_strictly_positive_global_floor(self) -> bool:
        return self.zero_probability_histories == 0 and self.minimum_sampling_probability > 0.0

    def payload(self) -> dict[str, object]:
        result = asdict(self)
        result["has_strictly_positive_global_floor"] = self.has_strictly_positive_global_floor
        return result


@dataclass(frozen=True)
class ExternalSamplingSupportReport:
    profile_id: str
    player0_traverser: TraverserSamplingSupport
    player1_traverser: TraverserSamplingSupport
    authority: str = AUTHORITY
    schema: str = SCHEMA
    sha256: str = ""

    def unsigned_payload(self) -> dict[str, object]:
        return {
            "schema": self.schema,
            "authority": self.authority,
            "profile_id": self.profile_id,
            "player0_traverser": self.player0_traverser.payload(),
            "player1_traverser": self.player1_traverser.payload(),
            "production_certification_eligible": False,
            "real_routes_certified": 0,
        }

    def payload(self) -> dict[str, object]:
        payload = self.unsigned_payload()
        payload["sha256"] = self.sha256
        return payload


def external_sampling_support_report(
    game: HUTwoRoundSubgame,
    profile: StrategyProfile,
    *,
    profile_id: str,
) -> ExternalSamplingSupportReport:
    label = str(profile_id).strip()
    if not label:
        raise ValueError("M5Q profile_id must be non-empty")

    count = [0, 0]
    zeros = [0, 0]
    minimum = [math.inf, math.inf]
    minimum_positive = [math.inf, math.inf]
    maximum = [0.0, 0.0]
    cp = float(game.chance_probability)
    if not math.isfinite(cp) or cp <= 0.0:
        raise RuntimeError("M5Q requires positive finite chance probability")

    for (
        outcome,
        _first_r3,
        _second_r3,
        _first_r4,
        _second_r4,
        p_first_r3,
        p_second_r3,
        p_first_r4,
        p_second_r4,
    ) in _terminal_histories(game, profile):
        probabilities = (p_first_r3, p_second_r3, p_first_r4, p_second_r4)
        if any((not math.isfinite(p) or p < 0.0) for p in probabilities):
            raise ValueError("M5Q profile contains invalid local probability")
        actors = (
            outcome.first_player,
            outcome.second_player,
            outcome.first_player,
            outcome.second_player,
        )
        for traverser in (0, 1):
            q = cp
            for actor, probability in zip(actors, probabilities):
                if actor != traverser:
                    q *= probability
            count[traverser] += 1
            minimum[traverser] = min(minimum[traverser], q)
            maximum[traverser] = max(maximum[traverser], q)
            if q == 0.0:
                zeros[traverser] += 1
            else:
                minimum_positive[traverser] = min(minimum_positive[traverser], q)

    supports: list[TraverserSamplingSupport] = []
    for traverser in (0, 1):
        if count[traverser] <= 0 or not math.isfinite(minimum[traverser]):
            raise RuntimeError("M5Q support audit found no terminal histories")
        positive = count[traverser] - zeros[traverser]
        min_positive_value = (
            None
            if positive == 0
            else float(minimum_positive[traverser])
        )
        supports.append(
            TraverserSamplingSupport(
                traverser=traverser,
                terminal_histories=count[traverser],
                zero_probability_histories=zeros[traverser],
                positive_probability_histories=positive,
                minimum_sampling_probability=float(minimum[traverser]),
                minimum_positive_sampling_probability=min_positive_value,
                maximum_sampling_probability=float(maximum[traverser]),
            )
        )

    unsigned: dict[str, object] = {
        "schema": SCHEMA,
        "authority": AUTHORITY,
        "profile_id": label,
        "player0_traverser": supports[0].payload(),
        "player1_traverser": supports[1].payload(),
        "production_certification_eligible": False,
        "real_routes_certified": 0,
    }
    return ExternalSamplingSupportReport(
        profile_id=label,
        player0_traverser=supports[0],
        player1_traverser=supports[1],
        sha256=_sha(unsigned),
    )
