from __future__ import annotations

"""M5L Q1 multi-profile calibration scaffold.

Q1 deliberately remains dormant until Q0 passes.  The driver is committed now so
its profile construction and evidence schema can be reviewed while the expensive
Q0 exact-BR run is executing.  A workflow should only be added after Q0 is green.

No output of this script is certification eligible.
"""

from collections.abc import Iterator, Mapping
from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
from typing import Sequence

from deepofc.actions import NormalPlacementAction
from deepofc.hu_three_round_br import exact_best_response, exact_value_of_pure_response
from deepofc.hu_three_round_mccfr import HUThreeRoundExternalSamplingMCCFR
from deepofc.hu_three_round_sequential import HUThreeRoundSequentialSubgame, StrategyProfile
from deepofc.sequential import HUPlayerObservation
from tools.openofc_solver.run_m5l_three_round_q0 import (
    OutcomeSampledResponseLearner,
    _seed64,
)

SCHEMA = "openofc-m5l-three-round-q1-v1"
AUTHORITY = "MULTI_PROFILE_CALIBRATION_NOT_CERTIFICATION"
ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "artifacts" / "m5l_three_round_q1.json"
RESPONSE_BUDGET = 1024
RESPONSE_SEEDS = (2026082781, 2026082797)
EPSILON = 0.6
TOL = 1e-9


def _canonical_bytes(payload: object) -> bytes:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")


def _sha(payload: object) -> str:
    return hashlib.sha256(_canonical_bytes(payload)).hexdigest()


class ProceduralProfile(Mapping[HUPlayerObservation, Mapping[NormalPlacementAction, float]]):
    """Infinite-on-demand deterministic profile with an immutable rule identity."""

    def __init__(self, game: HUThreeRoundSequentialSubgame, rule: str) -> None:
        if rule not in {"lexicographic-pure", "hash-biased-mixed"}:
            raise ValueError(f"unknown Q1 procedural profile rule: {rule}")
        self.game = game
        self.rule = rule

    def __getitem__(self, info: HUPlayerObservation) -> Mapping[NormalPlacementAction, float]:
        legal = tuple(self.game.actions(info))
        if self.rule == "lexicographic-pure":
            chosen = min(legal, key=lambda action: action.key())
            return {action: 1.0 if action == chosen else 0.0 for action in legal}

        # A stable, non-trivial mixed profile.  Hashes are used only as fixed
        # positive weights; no hidden game information enters the rule.
        weights: dict[NormalPlacementAction, float] = {}
        for action in legal:
            raw = f"m5l-q1|{repr(info)}|{action.key()}".encode("utf-8")
            integer = int.from_bytes(hashlib.sha256(raw).digest()[:8], "big")
            weights[action] = 1.0 + float(integer % 1000)
        total = sum(weights.values())
        return {action: value / total for action, value in weights.items()}

    def __iter__(self) -> Iterator[HUPlayerObservation]:
        return iter(())

    def __len__(self) -> int:
        return 0

    def get(self, key: HUPlayerObservation, default=None):
        return self[key]


@dataclass(frozen=True)
class ProfileSpec:
    profile_id: str
    profile: StrategyProfile
    provenance: str


def _profiles(game: HUThreeRoundSequentialSubgame) -> tuple[ProfileSpec, ...]:
    # Uniform is the canonical sparse-empty profile: missing infosets are uniform.
    uniform: StrategyProfile = {}

    # A solver-generated sparse profile adds a qualitatively different opponent.
    # Missing unvisited infosets deliberately retain the game's uniform fallback.
    solver = HUThreeRoundExternalSamplingMCCFR(game, seed=2026082771)
    solver.run(1024)
    solver_profile = solver.current_profile()
    solver_stats = solver.stats()

    return (
        ProfileSpec(
            "uniform",
            uniform,
            "canonical empty profile; game distribution supplies uniform legal actions",
        ),
        ProfileSpec(
            "lexicographic-pure",
            ProceduralProfile(game, "lexicographic-pure"),
            "one-hot lexicographically smallest legal action at every infoset",
        ),
        ProfileSpec(
            "hash-biased-mixed",
            ProceduralProfile(game, "hash-biased-mixed"),
            "stable positive SHA-derived public-infoset/action weights",
        ),
        ProfileSpec(
            "mccfr-1024",
            solver_profile,
            (
                f"HUThreeRoundExternalSamplingMCCFR seed={solver.seed} "
                f"iterations={solver_stats.iterations} terminals={solver_stats.terminal_evaluations} "
                f"regret_infosets={solver_stats.regret_infosets}"
            ),
        ),
    )


def _source_manifest() -> dict[str, object]:
    paths = (
        "deepofc/hu_three_round_br.py",
        "deepofc/hu_three_round_mccfr.py",
        "deepofc/hu_three_round_sequential.py",
        "tools/openofc_solver/M5L_REFERENCE_EVALUATOR_QUALIFICATION_CONTRACT.md",
        "tools/openofc_solver/run_m5l_three_round_q0.py",
        "tools/openofc_solver/run_m5l_three_round_q1.py",
    )
    rows = []
    for rel in paths:
        raw = (ROOT / rel).read_bytes()
        rows.append({"path": rel, "sha256": hashlib.sha256(raw).hexdigest()})
    payload: dict[str, object] = {"files": rows}
    payload["sha256"] = _sha(payload)
    return payload


def main() -> None:
    game = HUThreeRoundSequentialSubgame()
    rows: list[dict[str, object]] = []

    for profile_spec in _profiles(game):
        for player in (0, 1):
            exact = exact_best_response(game, profile_spec.profile, player)
            exact_replay, exact_replay_terminals = exact_value_of_pure_response(
                game, profile_spec.profile, exact
            )
            if abs(float(exact.value) - float(exact_replay)) > 1e-10:
                raise RuntimeError(
                    f"M5L Q1 exact replay mismatch profile={profile_spec.profile_id} player={player}"
                )

            for response_seed in RESPONSE_SEEDS:
                learner = OutcomeSampledResponseLearner(
                    game,
                    profile_spec.profile,
                    deviator_player=player,
                    epsilon=EPSILON,
                    seed=_seed64(response_seed, profile_spec.profile_id, player),
                )
                learner.run_to(RESPONSE_BUDGET)
                pure, learned_infosets, fallback_infosets = learner.pure_response(exact)
                approximate_value, approximate_replay_terminals = exact_value_of_pure_response(
                    game, profile_spec.profile, pure
                )
                residual = float(exact.value - approximate_value)
                if residual < -TOL:
                    raise RuntimeError("M5L Q1 approximate response exceeded exact BR")
                total_infosets = len(exact.choices)
                rows.append(
                    {
                        "profile_id": profile_spec.profile_id,
                        "profile_provenance": profile_spec.provenance,
                        "player": player,
                        "response_seed": int(response_seed),
                        "response_training_seed": int(learner.seed),
                        "response_budget": RESPONSE_BUDGET,
                        "exact_best_response_value": float(exact.value),
                        "exact_replay_value": float(exact_replay),
                        "exact_best_response_infosets": total_infosets,
                        "exact_terminal_histories": int(exact.terminal_histories),
                        "exact_replay_terminals": int(exact_replay_terminals),
                        "approximate_response_value": float(approximate_value),
                        "approximate_replay_terminals": int(approximate_replay_terminals),
                        "underestimation_residual": max(0.0, residual),
                        "responding_infosets_learned": int(learned_infosets),
                        "responding_infosets_fallback": int(fallback_infosets),
                        "responding_infoset_coverage": (
                            float(learned_infosets) / float(total_infosets)
                            if total_infosets
                            else 1.0
                        ),
                    }
                )

    residuals = [float(row["underestimation_residual"]) for row in rows]
    payload: dict[str, object] = {
        "schema": SCHEMA,
        "authority": AUTHORITY,
        "qualification_stage": "Q1_MULTI_PROFILE_CALIBRATION",
        "response_budget": RESPONSE_BUDGET,
        "response_seeds": list(RESPONSE_SEEDS),
        "epsilon": EPSILON,
        "source_manifest": _source_manifest(),
        "rows": rows,
        "summary": {
            "profiles": sorted({str(row["profile_id"]) for row in rows}),
            "players": [0, 1],
            "rows": len(rows),
            "min_underestimation_residual": min(residuals),
            "max_underestimation_residual": max(residuals),
            "mean_underestimation_residual": sum(residuals) / len(residuals),
            "certification_eligible": False,
            "reference_manifest_emitted": False,
        },
    }
    payload["sha256"] = _sha(payload)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(payload, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8")
    print(json.dumps({"artifact": str(OUT.relative_to(ROOT)), "sha256": payload["sha256"], "summary": payload["summary"]}, sort_keys=True))


if __name__ == "__main__":
    main()
