from __future__ import annotations

"""Materialize the frozen M5Q certification-architecture decision."""

import hashlib
import json
from pathlib import Path

from m5q_certification_architecture_decision import frozen_m5q_architecture_decision

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "artifacts" / "m5q_certification_architecture_decision.json"


def _canonical_bytes(payload: object) -> bytes:
    return json.dumps(
        payload, sort_keys=True, separators=(",", ":"), allow_nan=False
    ).encode("utf-8")


def _sha(payload: object) -> str:
    return hashlib.sha256(_canonical_bytes(payload)).hexdigest()


def _source_manifest() -> dict[str, object]:
    paths = (
        "docs/M5Q_CERTIFICATION_ARCHITECTURE_DECISION_2026-08-27.md",
        "tools/openofc_solver/m5q_certification_architecture_decision.py",
        "tools/openofc_solver/run_m5q_certification_architecture_decision.py",
        "tools/openofc_solver/test_m5q_certification_architecture_decision.py",
    )
    rows = [
        {"path": rel, "sha256": hashlib.sha256((ROOT / rel).read_bytes()).hexdigest()}
        for rel in paths
    ]
    payload: dict[str, object] = {"files": rows}
    payload["sha256"] = _sha(payload)
    return payload


def main() -> None:
    report = frozen_m5q_architecture_decision()
    payload: dict[str, object] = {
        "report": report.payload(),
        "source_manifest": _source_manifest(),
        "next_milestone": {
            "id": "M5R",
            "name": "FROZEN_POLICY_BEST_RESPONSE_CERTIFICATION_ARCHITECTURE",
            "requirements": [
                "exact reduced-game best response as authority baseline",
                "fail-closed certification-eligible evaluator manifest",
                "independent validation of any scalable evaluator against exact authority",
                "approximate exploiters remain screening-only unless a valid missed-exploitability upper bound exists",
            ],
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
                "decision_sha256": report.sha256,
                "exploration_joker_required_iterations": report.exploration_epsilon1_joker_required_iterations,
                "exploration_hidden_required_iterations": report.exploration_epsilon1_hidden_required_iterations,
                "adaptive_concentration_to_exact_ratio": report.adaptive_concentration_to_exact_ratio,
                "preferred_next_architecture": report.preferred_next_architecture,
                "real_routes_certified": report.real_routes_certified,
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
