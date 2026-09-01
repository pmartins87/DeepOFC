from __future__ import annotations

"""Pre-frozen cases for continuation-aware M5R interval transfer validation."""

import hashlib
import json

from hu_continuation import HUContinuationState, all_states

SCHEMA = "openofc-m5r-continuation-transfer-validation-manifest-v1"
AUTHORITY = "M5R_PRE_FROZEN_CONTINUATION_TRANSFER_VALIDATION_CASES_NOT_CERTIFICATION"

UPSTREAM_EXACT_LADDER_RUN_ID = 33426520598
UPSTREAM_INTERVAL_BRIDGE_RUN_ID = 33427294227
UPSTREAM_REACH_GEOMETRY_RUN_ID = 33448898087
UPSTREAM_CALIBRATED_FRONTIER_RUN_ID = 33453166880

# Smallest positive exact reach breakpoint for each family.  These values were
# frozen from the geometry gate before continuation-aware results were run.
POSITIVE_THRESHOLD_HEX_BY_FAMILY = {
    "three-round-v1": "0x1.2f684bda12f68p-13",
    "three-round-v2": "0x1.0db20a88f4695p-14",
}

MODE_INDEX = {0: 0, 14: 1, 15: 2, 16: 3, 17: 4}


def zero_vector() -> dict[HUContinuationState, float]:
    return {state: 0.0 for state in all_states()}


def structured_vector() -> dict[HUContinuationState, float]:
    """Deterministic nonzero antisymmetric stress vector.

    The formula intentionally depends on both Fantasy-mode imbalance and button,
    so the transfer validation cannot accidentally pass by ignoring either.
    Under exact player exchange the value changes sign.
    """

    out: dict[HUContinuationState, float] = {}
    for state in all_states():
        mode_term = 0.375 * (
            MODE_INDEX[state.p0_fantasy_cards] - MODE_INDEX[state.p1_fantasy_cards]
        )
        button_term = 0.125 if state.button == 0 else -0.125
        out[state] = mode_term + button_term
    return out


def _vector_payload(values: dict[HUContinuationState, float]) -> dict[str, float]:
    return {state.as_key(): float(values[state]) for state in sorted(all_states())}


def _sha(payload: object) -> str:
    raw = json.dumps(
        payload, sort_keys=True, separators=(",", ":"), allow_nan=False
    ).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def vector_sha256(values: dict[HUContinuationState, float]) -> str:
    return _sha(_vector_payload(values))


def unsigned_manifest() -> dict[str, object]:
    zero = zero_vector()
    structured = structured_vector()
    return {
        "schema": SCHEMA,
        "authority": AUTHORITY,
        "upstream": {
            "exact_ladder_run_id": UPSTREAM_EXACT_LADDER_RUN_ID,
            "interval_bridge_run_id": UPSTREAM_INTERVAL_BRIDGE_RUN_ID,
            "reach_geometry_run_id": UPSTREAM_REACH_GEOMETRY_RUN_ID,
            "calibrated_frontier_run_id": UPSTREAM_CALIBRATED_FRONTIER_RUN_ID,
        },
        "families": ["three-round-v1", "three-round-v2"],
        "players": [0, 1],
        "current_kernel": "NORMAL_NORMAL",
        "current_buttons_represented_by_benchmark": [0, 1],
        "positive_threshold_hex_by_family": dict(POSITIVE_THRESHOLD_HEX_BY_FAMILY),
        "vectors": {
            "zero": {
                "role": "UPSTREAM_RAW_BRIDGE_EQUIVALENCE_BASELINE",
                "sha256": vector_sha256(zero),
                "values": _vector_payload(zero),
            },
            "structured": {
                "role": "NONZERO_BUTTON_AND_FANTASY_MODE_STRESS",
                "formula": "0.375*(mode_index_p0-mode_index_p1)+(0.125 if button==0 else -0.125)",
                "sha256": vector_sha256(structured),
                "values": _vector_payload(structured),
            },
        },
        "structured_required_checks": [
            "EXACT_BR_VS_ZERO_THRESHOLD_INTERVAL",
            "EXACT_BR_INSIDE_SMALLEST_POSITIVE_BREAKPOINT_INTERVAL",
            "BOTH_RESPONDING_PLAYERS",
            "BOTH_THREE_ROUND_FAMILIES",
            "NO_RESPONDING_PLAYER_ACTION_PRUNING",
        ],
        "production_certification_eligible": False,
        "real_routes_certified": 0,
    }


def manifest_sha256() -> str:
    return _sha(unsigned_manifest())


def manifest_payload() -> dict[str, object]:
    payload = unsigned_manifest()
    payload["sha256"] = manifest_sha256()
    return payload
