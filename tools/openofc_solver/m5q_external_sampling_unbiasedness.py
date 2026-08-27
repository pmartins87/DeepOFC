from __future__ import annotations

"""M5Q instrumentation for External Sampling sampled-regret unbiasedness audits.

The production MCCFR implementation is not rewritten. This module subclasses it
only to expose the already-existing sampled traversal delta without applying the
update, then compares Monte Carlo projection means with the exact full-tree CFR
one-step regret increment at the same frozen regret-matching profile.

The resulting diagnostics are explicitly non-certifying.
"""

from dataclasses import asdict, dataclass
import hashlib
import json
import math
from typing import Hashable, Mapping

from deepofc.actions import NormalPlacementAction
from deepofc.hu_two_round import HUTwoRoundSubgame, TwoRoundInfoSet
from deepofc.hu_two_round_cfr import TwoRoundFullTreeCFR
from deepofc.hu_two_round_mccfr import TwoRoundExternalSamplingMCCFR

SCHEMA = "openofc-m5q-external-sampling-unbiasedness-diagnostic-v1"
AUTHORITY = "EXTERNAL_SAMPLING_REGRET_UNBIASEDNESS_DIAGNOSTIC_NOT_CERTIFICATION"
PROFILE_RULES = ("uniform", "hash-mixed")

RegretTable = dict[TwoRoundInfoSet, dict[NormalPlacementAction, float]]


def _canonical_bytes(payload: object) -> bytes:
    return json.dumps(
        payload, sort_keys=True, separators=(",", ":"), allow_nan=False
    ).encode("utf-8")


def _sha(payload: object) -> str:
    return hashlib.sha256(_canonical_bytes(payload)).hexdigest()


def _coordinate_key(
    info: TwoRoundInfoSet,
    action: NormalPlacementAction,
) -> str:
    return f"{repr(info)}|{repr(action.key())}"


def _copy_regrets(table: Mapping) -> RegretTable:
    return {
        info: {action: float(value) for action, value in values.items()}
        for info, values in table.items()
    }


def frozen_regret_table(game: HUTwoRoundSubgame, rule: str) -> RegretTable:
    """Return a deterministic frozen cumulative-regret table for one stressor."""

    if rule not in PROFILE_RULES:
        raise ValueError(f"unsupported M5Q profile rule: {rule}")
    table: RegretTable = {}
    for info, actions in game.info_actions.items():
        row: dict[NormalPlacementAction, float] = {}
        for action in actions:
            if rule == "uniform":
                value = 0.0
            else:
                raw = hashlib.sha256(
                    f"m5q-hash-mixed|{_coordinate_key(info, action)}".encode("utf-8")
                ).digest()
                integer = int.from_bytes(raw[:8], "big")
                # [-1, 1] inclusive on a fine deterministic grid. Regret matching
                # uses only the positive mass, so this creates broad non-uniform
                # behavior without fitting to any diagnostic result.
                value = float((integer % 2001) - 1000) / 1000.0
            row[action] = value
        table[info] = row
    return table


class InstrumentedTwoRoundExternalSamplingMCCFR(TwoRoundExternalSamplingMCCFR):
    """Read-only sampled-delta probe over the production traversal code path."""

    def install_frozen_regrets(self, table: Mapping) -> None:
        if set(table) != set(self.regrets):
            raise ValueError("M5Q frozen regret table infoset surface mismatch")
        copied = _copy_regrets(table)
        for info, legal in self.game.info_actions.items():
            if set(copied[info]) != set(legal):
                raise ValueError("M5Q frozen regret table action surface mismatch")
        self.regrets = copied

    def sample_regret_delta_pair(self) -> RegretTable:
        """Draw the same P0+P1 sampled regret delta used by one global step.

        Only RNG state advances. No regrets, iteration counters or strategy
        averaging state are changed.
        """

        delta: RegretTable = {}
        self._sampled_traversal(0, delta)
        self._sampled_traversal(1, delta)
        return _copy_regrets(delta)


@dataclass(frozen=True)
class ExactDeltaReference:
    profile_rule: str
    coordinate_count: int
    exact_delta: RegretTable
    exact_delta_sha256: str
    profile_max_probability_difference: float


def _regret_payload(table: Mapping) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for info in sorted(table, key=repr):
        for action in sorted(table[info], key=lambda candidate: candidate.key()):
            rows.append(
                {
                    "coordinate": _coordinate_key(info, action),
                    "value": float(table[info][action]),
                }
            )
    return rows


def profile_max_probability_difference(
    game: HUTwoRoundSubgame,
    regret_table: Mapping,
) -> float:
    exact = TwoRoundFullTreeCFR(game, variant="cfr")
    sampled = InstrumentedTwoRoundExternalSamplingMCCFR(game, seed=1)
    exact.regrets = _copy_regrets(regret_table)
    sampled.install_frozen_regrets(regret_table)
    max_diff = 0.0
    for info in game.info_actions:
        p_exact = exact._distribution(info)
        p_sampled = sampled._distribution(info)
        for action in game.actions(info):
            max_diff = max(max_diff, abs(p_exact[action] - p_sampled[action]))
    return max_diff


def exact_full_tree_regret_delta(
    game: HUTwoRoundSubgame,
    *,
    profile_rule: str,
) -> ExactDeltaReference:
    """Compute exact one-step CFR regret delta from the frozen profile table."""

    frozen = frozen_regret_table(game, profile_rule)
    exact = TwoRoundFullTreeCFR(game, variant="cfr")
    exact.regrets = _copy_regrets(frozen)
    before = _copy_regrets(exact.regrets)
    exact.step()

    delta: RegretTable = {}
    coordinate_count = 0
    for info, actions in game.info_actions.items():
        row: dict[NormalPlacementAction, float] = {}
        for action in actions:
            coordinate_count += 1
            value = float(exact.regrets[info][action] - before[info][action])
            if not math.isfinite(value):
                raise FloatingPointError("non-finite exact M5Q regret delta")
            row[action] = value
        delta[info] = row

    payload = _regret_payload(delta)
    return ExactDeltaReference(
        profile_rule=profile_rule,
        coordinate_count=coordinate_count,
        exact_delta=delta,
        exact_delta_sha256=_sha(payload),
        profile_max_probability_difference=profile_max_probability_difference(
            game, frozen
        ),
    )


class ProjectionMap:
    """Deterministic dense Rademacher projections over the regret surface."""

    def __init__(
        self,
        game: HUTwoRoundSubgame,
        *,
        projection_count: int,
    ) -> None:
        if projection_count <= 0:
            raise ValueError("projection_count must be positive")
        coordinates = [
            (info, action)
            for info in game.info_actions
            for action in game.actions(info)
        ]
        if not coordinates:
            raise RuntimeError("M5Q cannot project an empty regret surface")
        self.coordinate_count = len(coordinates)
        self.projection_count = int(projection_count)
        scale = 1.0 / math.sqrt(float(self.coordinate_count))
        self.weights: list[dict[tuple[TwoRoundInfoSet, NormalPlacementAction], float]] = []
        for projection in range(self.projection_count):
            row: dict[tuple[TwoRoundInfoSet, NormalPlacementAction], float] = {}
            for info, action in coordinates:
                raw = hashlib.sha256(
                    f"m5q-projection-{projection}|{_coordinate_key(info, action)}".encode(
                        "utf-8"
                    )
                ).digest()
                sign = 1.0 if raw[0] & 1 else -1.0
                row[(info, action)] = sign * scale
            self.weights.append(row)

    def project(self, delta: Mapping) -> tuple[float, ...]:
        totals = [0.0 for _ in range(self.projection_count)]
        for info, values in delta.items():
            for action, value in values.items():
                number = float(value)
                if not math.isfinite(number):
                    raise FloatingPointError("non-finite sampled M5Q regret delta")
                coordinate = (info, action)
                for projection, weights in enumerate(self.weights):
                    totals[projection] += weights[coordinate] * number
        return tuple(totals)


@dataclass
class _OnlineMoments:
    n: int = 0
    mean: float = 0.0
    m2: float = 0.0
    minimum: float = math.inf
    maximum: float = -math.inf

    def add(self, value: float) -> None:
        self.n += 1
        delta = value - self.mean
        self.mean += delta / float(self.n)
        self.m2 += delta * (value - self.mean)
        self.minimum = min(self.minimum, value)
        self.maximum = max(self.maximum, value)

    @property
    def sample_variance(self) -> float:
        return self.m2 / float(self.n - 1) if self.n > 1 else 0.0

    @property
    def standard_error(self) -> float:
        return math.sqrt(self.sample_variance / float(self.n)) if self.n else math.inf


@dataclass(frozen=True)
class ProjectionDiagnostic:
    projection: int
    exact_expectation: float
    sample_mean: float
    sample_variance: float
    standard_error: float
    absolute_error: float
    standardized_error: float | None
    sample_minimum: float
    sample_maximum: float
    passes_six_se_gate: bool


@dataclass(frozen=True)
class UnbiasednessDiagnostic:
    profile_rule: str
    probes: int
    rng_seed: int
    projection_count: int
    coordinate_count: int
    exact_delta_sha256: str
    profile_max_probability_difference: float
    max_absolute_error: float
    max_standardized_error: float
    all_projections_pass: bool
    projections: tuple[ProjectionDiagnostic, ...]
    authority: str = AUTHORITY
    schema: str = SCHEMA
    sha256: str = ""

    def unsigned_payload(self) -> dict[str, object]:
        return {
            "schema": self.schema,
            "authority": self.authority,
            "profile_rule": self.profile_rule,
            "probes": self.probes,
            "rng_seed": self.rng_seed,
            "projection_count": self.projection_count,
            "coordinate_count": self.coordinate_count,
            "exact_delta_sha256": self.exact_delta_sha256,
            "profile_max_probability_difference": self.profile_max_probability_difference,
            "max_absolute_error": self.max_absolute_error,
            "max_standardized_error": self.max_standardized_error,
            "all_projections_pass": self.all_projections_pass,
            "projections": [asdict(row) for row in self.projections],
            "certification_eligible": False,
        }

    def payload(self) -> dict[str, object]:
        payload = self.unsigned_payload()
        payload["sha256"] = self.sha256
        return payload


def run_projection_unbiasedness_diagnostic(
    game: HUTwoRoundSubgame,
    *,
    profile_rule: str,
    probes: int,
    rng_seed: int,
    projection_count: int = 8,
    standard_error_multiplier: float = 6.0,
) -> UnbiasednessDiagnostic:
    if probes < 2:
        raise ValueError("M5Q requires at least two probes")
    if standard_error_multiplier <= 0.0:
        raise ValueError("standard_error_multiplier must be positive")

    exact = exact_full_tree_regret_delta(game, profile_rule=profile_rule)
    frozen = frozen_regret_table(game, profile_rule)
    sampled = InstrumentedTwoRoundExternalSamplingMCCFR(game, seed=int(rng_seed))
    sampled.install_frozen_regrets(frozen)
    projector = ProjectionMap(game, projection_count=projection_count)
    if projector.coordinate_count != exact.coordinate_count:
        raise AssertionError("M5Q projection/exact coordinate surfaces differ")

    exact_values = projector.project(exact.exact_delta)
    moments = [_OnlineMoments() for _ in range(projection_count)]
    for _ in range(probes):
        draw = projector.project(sampled.sample_regret_delta_pair())
        for accumulator, value in zip(moments, draw):
            accumulator.add(value)

    rows: list[ProjectionDiagnostic] = []
    for index, (expected, accumulator) in enumerate(zip(exact_values, moments)):
        error = abs(accumulator.mean - expected)
        se = accumulator.standard_error
        if se <= 0.0:
            standardized: float | None = None
            passes = error <= 1e-12
        else:
            standardized = error / se
            passes = standardized <= standard_error_multiplier
        rows.append(
            ProjectionDiagnostic(
                projection=index,
                exact_expectation=float(expected),
                sample_mean=float(accumulator.mean),
                sample_variance=float(accumulator.sample_variance),
                standard_error=float(se),
                absolute_error=float(error),
                standardized_error=None if standardized is None else float(standardized),
                sample_minimum=float(accumulator.minimum),
                sample_maximum=float(accumulator.maximum),
                passes_six_se_gate=bool(passes),
            )
        )

    max_standardized = max(
        (row.standardized_error or 0.0) for row in rows
    )
    unsigned: dict[str, object] = {
        "schema": SCHEMA,
        "authority": AUTHORITY,
        "profile_rule": profile_rule,
        "probes": int(probes),
        "rng_seed": int(rng_seed),
        "projection_count": int(projection_count),
        "coordinate_count": exact.coordinate_count,
        "exact_delta_sha256": exact.exact_delta_sha256,
        "profile_max_probability_difference": exact.profile_max_probability_difference,
        "max_absolute_error": max(row.absolute_error for row in rows),
        "max_standardized_error": max_standardized,
        "all_projections_pass": all(row.passes_six_se_gate for row in rows),
        "projections": [asdict(row) for row in rows],
        "certification_eligible": False,
    }
    return UnbiasednessDiagnostic(
        profile_rule=profile_rule,
        probes=int(probes),
        rng_seed=int(rng_seed),
        projection_count=int(projection_count),
        coordinate_count=exact.coordinate_count,
        exact_delta_sha256=exact.exact_delta_sha256,
        profile_max_probability_difference=exact.profile_max_probability_difference,
        max_absolute_error=float(unsigned["max_absolute_error"]),
        max_standardized_error=float(max_standardized),
        all_projections_pass=bool(unsigned["all_projections_pass"]),
        projections=tuple(rows),
        sha256=_sha(unsigned),
    )
