from __future__ import annotations

"""M5L Q2 held-out benchmark-family calibration driver.

The driver is committed before activation so its held-out families, profiles,
budget and evidence schema are reviewable and immutable before any Q2 result is
seen.  Do not add/activate a Q2 workflow until Q1 has completed and its outcome
has been recorded.

Q2 is calibration only and cannot emit a certification-eligible manifest.
"""

from collections.abc import Iterator, Mapping
from dataclasses import asdict, dataclass
import hashlib
import json
from pathlib import Path
from typing import Callable

from deepofc.actions import NormalPlacementAction
from deepofc.hu_two_round import HUTwoRoundSubgame, StrategyProfile, TwoRoundInfoSet
from deepofc.hu_two_round_br import (
    exact_best_response,
    profile_with_pure_response,
)
from deepofc.hu_two_round_hidden_discard import HUTwoRoundHiddenDiscardSubgame
from deepofc.hu_two_round_joker import HUTwoRoundJokerSubgame
from m5l_two_round_response import TwoRoundOutcomeSampledResponseLearner

SCHEMA = "openofc-m5l-two-round-q2-heldout-v1"
AUTHORITY = "HELDOUT_BENCHMARK_FAMILY_CALIBRATION_NOT_CERTIFICATION"
ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "artifacts" / "m5l_two_round_q2.json"

# Frozen before any Q2 result is observed.  Q0B showed the same exact-key method
# is still underqualified at much larger budgets; Q2 therefore asks a diagnostic
# transfer/stability question rather than trying to tune until a desired result.
RESPONSE_BUDGET = 16_384
RESPONSE_SEEDS = (2026083101, 2026083137)
EPSILON = 0.6
TOL = 1e-9


class ProceduralTwoRoundProfile(
    Mapping[TwoRoundInfoSet, Mapping[NormalPlacementAction, float]]
):
    """On-demand profile whose rule depends only on public infoset/action identity."""

    def __init__(self, game: HUTwoRoundSubgame, rule: str) -> None:
        if rule not in {"uniform", "hash-biased-mixed"}:
            raise ValueError(f"unknown Q2 profile rule: {rule}")
        self.game = game
        self.rule = rule

    def __getitem__(self, info: TwoRoundInfoSet) -> Mapping[NormalPlacementAction, float]:
        actions = tuple(self.game.actions(info))
        if self.rule == "uniform":
            return {action: 1.0 / len(actions) for action in actions}
        weights: dict[NormalPlacementAction, float] = {}
        for action in actions:
            raw = f"m5l-q2|{repr(info)}|{action.key()}".encode("utf-8")
            integer = int.from_bytes(hashlib.sha256(raw).digest()[:8], "big")
            weights[action] = 1.0 + float(integer % 1000)
        total = sum(weights.values())
        return {action: value / total for action, value in weights.items()}

    def __iter__(self) -> Iterator[TwoRoundInfoSet]:
        return iter(())

    def __len__(self) -> int:
        return 0

    def get(self, key: TwoRoundInfoSet, default=None):
        return self[key]


@dataclass(frozen=True)
class FamilySpec:
    family_id: str
    factory: Callable[[], HUTwoRoundSubgame]
    provenance: str


FAMILIES = (
    FamilySpec(
        "hidden-discard",
        HUTwoRoundHiddenDiscardSubgame,
        "ambiguous hidden round-3 discard support; exact perfect-recall two-round BR",
    ),
    FamilySpec(
        "joker",
        HUTwoRoundJokerSubgame,
        "persistent physical Joker support with hidden-discard ambiguity; exact two-round BR",
    ),
)
PROFILE_RULES = ("uniform", "hash-biased-mixed")


def _canonical_bytes(payload: object) -> bytes:
    return json.dumps(
        payload, sort_keys=True, separators=(",", ":"), allow_nan=False
    ).encode("utf-8")


def _sha(payload: object) -> str:
    return hashlib.sha256(_canonical_bytes(payload)).hexdigest()


def _source_manifest() -> dict[str, object]:
    paths = (
        "deepofc/hu_two_round.py",
        "deepofc/hu_two_round_br.py",
        "deepofc/hu_two_round_hidden_discard.py",
        "deepofc/hu_two_round_joker.py",
        "tools/openofc_solver/M5L_REFERENCE_EVALUATOR_QUALIFICATION_CONTRACT.md",
        "tools/openofc_solver/m5l_two_round_response.py",
        "tools/openofc_solver/run_m5l_two_round_q2.py",
    )
    rows = [
        {
            "path": rel,
            "sha256": hashlib.sha256((ROOT / rel).read_bytes()).hexdigest(),
        }
        for rel in paths
    ]
    payload: dict[str, object] = {"files": rows}
    payload["sha256"] = _sha(payload)
    return payload


def _exact_replay_value(
    game: HUTwoRoundSubgame,
    profile: StrategyProfile,
    player: int,
    exact,
) -> float:
    full = profile_with_pure_response(game, profile, exact)
    u0 = float(game.expected_u0(full))
    return u0 if player == 0 else -u0


def main() -> None:
    rows: list[dict[str, object]] = []
    for family in FAMILIES:
        game = family.factory()
        for profile_rule in PROFILE_RULES:
            profile: StrategyProfile = ProceduralTwoRoundProfile(game, profile_rule)
            for player in (0, 1):
                exact = exact_best_response(game, profile, player)
                exact_replay = _exact_replay_value(game, profile, player, exact)
                if abs(float(exact.value) - exact_replay) > 1e-10:
                    raise RuntimeError(
                        f"M5L Q2 exact replay mismatch family={family.family_id} "
                        f"profile={profile_rule} player={player}"
                    )

                for seed in RESPONSE_SEEDS:
                    training_seed = int.from_bytes(
                        hashlib.sha256(
                            f"{seed}|{family.family_id}|{profile_rule}|{player}".encode("utf-8")
                        ).digest()[:8],
                        "big",
                    )
                    learner = TwoRoundOutcomeSampledResponseLearner(
                        game,
                        profile,
                        deviator_player=player,
                        epsilon=EPSILON,
                        seed=training_seed,
                    )
                    training = learner.run_to(RESPONSE_BUDGET)
                    pure, learned, fallback = learner.pure_response(exact)
                    approximate = learner.exact_value_of_pure_response(pure)
                    residual = float(exact.value - approximate)
                    if residual < -TOL:
                        raise RuntimeError(
                            "M5L Q2 approximate response exceeded exact best response"
                        )
                    total_infosets = len(exact.choices)
                    rows.append(
                        {
                            "family_id": family.family_id,
                            "family_provenance": family.provenance,
                            "profile_rule": profile_rule,
                            "player": player,
                            "response_seed": int(seed),
                            "response_training_seed": training_seed,
                            "response_budget": RESPONSE_BUDGET,
                            "exact_best_response_value": float(exact.value),
                            "exact_replay_value": exact_replay,
                            "exact_best_response_infosets": total_infosets,
                            "approximate_response_value": float(approximate),
                            "underestimation_residual": max(0.0, residual),
                            "responding_infosets_learned": int(learned),
                            "responding_infosets_fallback": int(fallback),
                            "responding_infoset_coverage": (
                                float(learned) / float(total_infosets)
                                if total_infosets else 1.0
                            ),
                            "training": asdict(training),
                        }
                    )

    residuals = [float(row["underestimation_residual"]) for row in rows]
    by_family: dict[str, dict[str, float]] = {}
    for family in sorted({str(row["family_id"]) for row in rows}):
        values = [
            float(row["underestimation_residual"])
            for row in rows
            if row["family_id"] == family
        ]
        by_family[family] = {
            "rows": float(len(values)),
            "min_residual": min(values),
            "max_residual": max(values),
            "mean_residual": sum(values) / len(values),
        }

    payload: dict[str, object] = {
        "schema": SCHEMA,
        "authority": AUTHORITY,
        "qualification_stage": "Q2_HELDOUT_BENCHMARK_FAMILIES",
        "activation_precondition": "Q1_COMPLETE_AND_RECORDED",
        "response_budget": RESPONSE_BUDGET,
        "response_seeds": list(RESPONSE_SEEDS),
        "epsilon": EPSILON,
        "families": [
            {"family_id": family.family_id, "provenance": family.provenance}
            for family in FAMILIES
        ],
        "profile_rules": list(PROFILE_RULES),
        "source_manifest": _source_manifest(),
        "rows": rows,
        "summary": {
            "rows": len(rows),
            "families": sorted(by_family),
            "profiles": list(PROFILE_RULES),
            "players": [0, 1],
            "min_underestimation_residual": min(residuals),
            "max_underestimation_residual": max(residuals),
            "mean_underestimation_residual": sum(residuals) / len(residuals),
            "by_family": by_family,
            "certification_eligible": False,
            "reference_manifest_emitted": False,
        },
    }
    payload["sha256"] = _sha(payload)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(
        json.dumps(payload, indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "artifact": str(OUT.relative_to(ROOT)),
                "sha256": payload["sha256"],
                "summary": payload["summary"],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
