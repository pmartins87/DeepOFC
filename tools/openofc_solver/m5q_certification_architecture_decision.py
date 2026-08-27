from __future__ import annotations

"""Frozen M5Q certification-architecture decision.

This module binds already-produced M5Q evidence into a machine-checkable project
architecture decision.  It certifies no strategic route and does not modify the
production solver.
"""

from dataclasses import asdict, dataclass
import hashlib
import json

SCHEMA = "openofc-m5q-certification-architecture-decision-v1"
AUTHORITY = "M5Q_CERTIFICATION_ARCHITECTURE_DECISION_NOT_STRATEGIC_CERTIFICATION"
TARGET_EXPLOITABILITY = 0.15


def _canonical_bytes(payload: object) -> bytes:
    return json.dumps(
        payload, sort_keys=True, separators=(",", ":"), allow_nan=False
    ).encode("utf-8")


def _sha(payload: object) -> str:
    return hashlib.sha256(_canonical_bytes(payload)).hexdigest()


@dataclass(frozen=True)
class EvidenceBinding:
    gate_id: str
    workflow_run_id: int
    payload_sha256: str
    authority_scope: str

    def payload(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class M5QArchitectureDecision:
    evidence: tuple[EvidenceBinding, ...]
    exploration_epsilon1_joker_floor: float
    exploration_epsilon1_hidden_floor: float
    exploration_epsilon1_joker_required_iterations: int
    exploration_epsilon1_hidden_required_iterations: int
    adaptive_checkpoint_iterations: int
    adaptive_sampled_positive_regret_contribution: float
    adaptive_concentration_additive: float
    adaptive_support_free_upper_bound: float
    adaptive_exact_exploitability: float
    adaptive_concentration_to_exact_ratio: float
    global_floor_exploration_status: str
    scalar_coordinate_freedman_status: str
    preferred_next_architecture: str
    support_free_methods_globally_rejected: bool
    production_solver_modified: bool
    production_certification_eligible: bool
    real_routes_certified: int
    authority: str = AUTHORITY
    schema: str = SCHEMA
    sha256: str = ""

    def unsigned_payload(self) -> dict[str, object]:
        return {
            "schema": self.schema,
            "authority": self.authority,
            "target_exploitability": TARGET_EXPLOITABILITY,
            "evidence": [row.payload() for row in self.evidence],
            "exploration_epsilon1": {
                "joker_global_sampling_probability_floor": self.exploration_epsilon1_joker_floor,
                "hidden_discard_global_sampling_probability_floor": self.exploration_epsilon1_hidden_floor,
                "joker_required_iterations_for_target": self.exploration_epsilon1_joker_required_iterations,
                "hidden_discard_required_iterations_for_target": self.exploration_epsilon1_hidden_required_iterations,
            },
            "adaptive_predictable_freedman_checkpoint": {
                "iterations": self.adaptive_checkpoint_iterations,
                "sampled_positive_regret_contribution": self.adaptive_sampled_positive_regret_contribution,
                "concentration_additive": self.adaptive_concentration_additive,
                "support_free_upper_bound": self.adaptive_support_free_upper_bound,
                "exact_exploitability": self.adaptive_exact_exploitability,
                "concentration_to_exact_exploitability_ratio": self.adaptive_concentration_to_exact_ratio,
            },
            "decision": {
                "global_floor_exploration_status": self.global_floor_exploration_status,
                "scalar_coordinate_freedman_status": self.scalar_coordinate_freedman_status,
                "preferred_next_architecture": self.preferred_next_architecture,
                "support_free_methods_globally_rejected": self.support_free_methods_globally_rejected,
            },
            "production_solver_modified": self.production_solver_modified,
            "production_certification_eligible": self.production_certification_eligible,
            "real_routes_certified": self.real_routes_certified,
        }

    def payload(self) -> dict[str, object]:
        payload = self.unsigned_payload()
        payload["sha256"] = self.sha256
        return payload


def frozen_m5q_architecture_decision() -> M5QArchitectureDecision:
    evidence = (
        EvidenceBinding(
            "M5Q_A_SAMPLED_REGRET_UNBIASEDNESS_DIAGNOSTIC",
            33102897371,
            "0188c219f6946055b8dae8c350ebfbca7aef65c93403dbb5f79c793cf30cedf5",
            "FINITE_MONTE_CARLO_DIAGNOSTIC_NOT_PROOF",
        ),
        EvidenceBinding(
            "M5Q_EXPLORATION_SUPPORT_FEASIBILITY",
            33117273274,
            "317b0fc0a242fb3bfea751c2c611a2c0106a7d13cb8a1497ae23f9f6f31e6bce",
            "EXPLORATION_SUPPORTED_EXTERNAL_SAMPLING_PILOT_NOT_CERTIFICATION",
        ),
        EvidenceBinding(
            "M5Q_REACH_WEIGHTED_AVERAGE_GATE",
            33124398189,
            "2c51534c4528d4b53e807a4e76fa8f93872d462c9ca8839ba1073fd23e0e268c",
            "REACH_WEIGHTED_AVERAGE_SEMANTIC_GATE_NOT_CERTIFICATION",
        ),
        EvidenceBinding(
            "M5Q_COARSE_FREEDMAN_UNION_FEASIBILITY",
            33124925558,
            "2a38e5415cd68ae8fa5bbf213b3944273c7291e635a622612ab642e17eb7c01e",
            "COORDINATE_FREEDMAN_UNION_FEASIBILITY_NOT_CERTIFICATION",
        ),
        EvidenceBinding(
            "M5Q_PREDICTABLE_VISIT_VARIANCE",
            33125162221,
            "bd0312c66eb13151a7159f1e42eafbba72544b7ab1ad272bf867cba27ce13f51",
            "PREDICTABLE_VISIT_VARIANCE_AUDIT_NOT_CERTIFICATION",
        ),
        EvidenceBinding(
            "M5Q_VISIT_WEIGHTED_FREEDMAN_FEASIBILITY",
            33125564827,
            "5aa1877d067bb871becaa71bdf770bd24b0697ecf589e641803a49ad234482d7",
            "VISIT_WEIGHTED_FREEDMAN_FEASIBILITY_PILOT_NOT_CERTIFICATION",
        ),
        EvidenceBinding(
            "M5Q_ADAPTIVE_PREDICTABLE_FREEDMAN_TRAJECTORY",
            33125700677,
            "ebb5fb5fa8da4804955445025256649d3526c5902dba97f60072cd26997246ff",
            "ADAPTIVE_PREDICTABLE_FREEDMAN_TRAJECTORY_PILOT_NOT_CERTIFICATION",
        ),
    )

    concentration = 5592.373477969387
    exact = 0.6407294367903822
    ratio = concentration / exact
    unsigned: dict[str, object] = {
        "schema": SCHEMA,
        "authority": AUTHORITY,
        "target_exploitability": TARGET_EXPLOITABILITY,
        "evidence": [row.payload() for row in evidence],
        "exploration_epsilon1": {
            "joker_global_sampling_probability_floor": 0.0005787037037037037,
            "hidden_discard_global_sampling_probability_floor": 0.000248015873015873,
            "joker_required_iterations_for_target": 918799060363021,
            "hidden_discard_required_iterations_for_target": 1382605782910640640,
        },
        "adaptive_predictable_freedman_checkpoint": {
            "iterations": 64,
            "sampled_positive_regret_contribution": 1.0007071512319758,
            "concentration_additive": concentration,
            "support_free_upper_bound": 5593.374185120619,
            "exact_exploitability": exact,
            "concentration_to_exact_exploitability_ratio": ratio,
        },
        "decision": {
            "global_floor_exploration_status": "DEPRIORITIZED_AS_PRIMARY_PRODUCTION_CERTIFICATE",
            "scalar_coordinate_freedman_status": "DEPRIORITIZED_AS_PRIMARY_PRODUCTION_CERTIFICATE",
            "preferred_next_architecture": "FROZEN_POLICY_INDEPENDENT_DEVIATION_BEST_RESPONSE_CERTIFICATION",
            "support_free_methods_globally_rejected": False,
        },
        "production_solver_modified": False,
        "production_certification_eligible": False,
        "real_routes_certified": 0,
    }
    return M5QArchitectureDecision(
        evidence=evidence,
        exploration_epsilon1_joker_floor=0.0005787037037037037,
        exploration_epsilon1_hidden_floor=0.000248015873015873,
        exploration_epsilon1_joker_required_iterations=918799060363021,
        exploration_epsilon1_hidden_required_iterations=1382605782910640640,
        adaptive_checkpoint_iterations=64,
        adaptive_sampled_positive_regret_contribution=1.0007071512319758,
        adaptive_concentration_additive=concentration,
        adaptive_support_free_upper_bound=5593.374185120619,
        adaptive_exact_exploitability=exact,
        adaptive_concentration_to_exact_ratio=ratio,
        global_floor_exploration_status="DEPRIORITIZED_AS_PRIMARY_PRODUCTION_CERTIFICATE",
        scalar_coordinate_freedman_status="DEPRIORITIZED_AS_PRIMARY_PRODUCTION_CERTIFICATE",
        preferred_next_architecture="FROZEN_POLICY_INDEPENDENT_DEVIATION_BEST_RESPONSE_CERTIFICATION",
        support_free_methods_globally_rejected=False,
        production_solver_modified=False,
        production_certification_eligible=False,
        real_routes_certified=0,
        sha256=_sha(unsigned),
    )
