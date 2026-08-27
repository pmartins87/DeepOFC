from __future__ import annotations

"""Run the frozen M5Q support-free martingale prerequisite audit."""

import hashlib
import json
from pathlib import Path

from deepofc.hu_two_round_hidden_discard import HUTwoRoundHiddenDiscardSubgame
from deepofc.hu_two_round_joker import HUTwoRoundJokerSubgame
from m5q_support_free_martingale_prerequisites import audit_support_free_prerequisites

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "artifacts" / "m5q_support_free_martingale_prerequisites.json"


def _canonical_bytes(payload: object) -> bytes:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")


def _sha(payload: object) -> str:
    return hashlib.sha256(_canonical_bytes(payload)).hexdigest()


def _source_manifest() -> dict[str, object]:
    paths = (
        "deepofc/hu_two_round_mccfr.py",
        "tools/openofc_solver/M5Q_SUPPORT_FREE_MARTINGALE_PREREQUISITES_CONTRACT.md",
        "tools/openofc_solver/m5q_support_free_martingale_prerequisites.py",
        "tools/openofc_solver/m5q_support_range_feasibility.py",
        "tools/openofc_solver/run_m5q_support_free_martingale_prerequisites.py",
        "tools/openofc_solver/test_m5q_support_free_martingale_prerequisites.py",
    )
    rows = [
        {"path": rel, "sha256": hashlib.sha256((ROOT / rel).read_bytes()).hexdigest()}
        for rel in paths
    ]
    payload: dict[str, object] = {"files": rows}
    payload["sha256"] = _sha(payload)
    return payload


def main() -> None:
    report = audit_support_free_prerequisites(
        (
            ("joker", HUTwoRoundJokerSubgame()),
            ("hidden-discard", HUTwoRoundHiddenDiscardSubgame()),
        )
    )
    payload: dict[str, object] = {
        "report": report.payload(),
        "source_manifest": _source_manifest(),
        "decision": {
            "instantiate_support_free_concentration_bound_now": False,
            "reason": report.next_blocker,
            "required_follow_up": [
                "implement_and_independently_validate theorem-compatible reach-weighted average strategy semantics",
                "implement and validate predictable/conditional sampled-regret variance accounting",
                "only then instantiate a named martingale concentration theorem",
            ],
        },
    }
    payload["sha256"] = _sha(payload)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(payload, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8")
    print(json.dumps({"artifact": str(OUT.relative_to(ROOT)), "sha256": payload["sha256"], "bounded_increment_prerequisite_pass": report.bounded_increment_prerequisite_pass, "next_blocker": report.next_blocker, "support_free_certificate_prerequisites_complete": report.support_free_certificate_prerequisites_complete}, sort_keys=True))


if __name__ == "__main__":
    main()
