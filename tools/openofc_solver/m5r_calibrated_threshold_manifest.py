from __future__ import annotations

"""Pre-frozen threshold manifest for the M5R three-round interval frontier.

The positive thresholds are exactly the distinct opponent-counterfactual-reach
levels observed by authoritative reach-geometry run 33448898087.  They are
stored as hexadecimal floating-point strings so the binary values are frozen
without decimal-roundtrip ambiguity.
"""

import hashlib
import json

SCHEMA = "openofc-m5r-calibrated-threshold-manifest-v1"
AUTHORITY = "M5R_REDUCED_EXACT_REACH_BREAKPOINTS_PRE_FROZEN_NOT_CERTIFICATION"

EXACT_LADDER_RUN_ID = 33426520598
EXACT_LADDER_AGGREGATE_FILE_SHA256 = (
    "948139daa538ba5af8faa31b5dee3eada4efc01289f66d98dfefae135beddb9d"
)
INTERVAL_BRIDGE_RUN_ID = 33427294227
INTERVAL_BRIDGE_AGGREGATE_FILE_SHA256 = (
    "b44c01e1c17c8ada4e477dc008fc66975b36dca1d7e1405f66ec251a9f37e985"
)
REACH_GEOMETRY_RUN_ID = 33448898087
REACH_GEOMETRY_INTERNAL_SHA256 = (
    "40f73f3cda42921983d48f5fc688e6ce3af9c709f50c8a385747948846a98c20"
)
REACH_GEOMETRY_ARTIFACT_DIGEST = (
    "sha256:ee8ecc38382fef8408cb98abf26dfc6e9da5e813ad2e909c54b9ae2122accee9"
)

THRESHOLD_HEX_BY_FAMILY: dict[str, tuple[str, ...]] = {
    "three-round-v1": (
        "0x1.2f684bda12f68p-13",
        "0x1.948b0fcd6e9e0p-13",
        "0x1.2f684bda12f68p-12",
        "0x1.948b0fcd6e9e0p-12",
        "0x1.c71c71c71c71cp-11",
        "0x1.2f684bda12f68p-10",
        "0x1.c71c71c71c71cp-9",
        "0x1.5555555555555p-7",
    ),
    "three-round-v2": (
        "0x1.0db20a88f4695p-14",
        "0x1.0db20a88f4695p-13",
        "0x1.948b0fcd6e9e0p-12",
        "0x1.2f684bda12f68p-10",
        "0x1.c71c71c71c71cp-9",
    ),
}

EXPECTED_REFERENCE: dict[str, dict[int, dict[str, float | int]]] = {
    "three-round-v1": {
        0: {
            "exact_br_value": 10.418788580246916,
            "responding_infosets": 204_962,
            "terminal_histories": 1_312_200,
        },
        1: {
            "exact_br_value": 10.418788580246916,
            "responding_infosets": 204_962,
            "terminal_histories": 1_312_200,
        },
    },
    "three-round-v2": {
        0: {
            "exact_br_value": 6.843106995884774,
            "responding_infosets": 96_022,
            "terminal_histories": 839_808,
        },
        1: {
            "exact_br_value": 6.8431069958847734,
            "responding_infosets": 96_022,
            "terminal_histories": 839_808,
        },
    },
}

GEOMETRY_CELL_SHA256: dict[str, dict[int, str]] = {
    "three-round-v1": {
        0: "2506b13e4509e9626a51236a53a7b98e74bbfbdbf3374afd625a22e68d22a35b",
        1: "d3daf9d8923102cad21e8065d0a0b1d4ba2ce2a8c90e46d0e86729cde7989110",
    },
    "three-round-v2": {
        0: "a27bff88a8c10fe089ea3a8bcea81e9d8390e05679f7cca7edbe9784b1dfab03",
        1: "26a90a26c8524edcd53b829c3d0031383982bb6fd9725bd96fd1a4eeb2208474",
    },
}


def positive_thresholds(family: str) -> tuple[float, ...]:
    try:
        rows = THRESHOLD_HEX_BY_FAMILY[family]
    except KeyError as exc:
        raise ValueError(f"unsupported family: {family}") from exc
    values = tuple(float.fromhex(value) for value in rows)
    if not values or any(value <= 0.0 for value in values):
        raise AssertionError("calibrated threshold panel must be positive")
    if tuple(sorted(set(values))) != values:
        raise AssertionError("calibrated threshold panel must be strictly increasing")
    return values


def unsigned_manifest() -> dict[str, object]:
    return {
        "schema": SCHEMA,
        "authority": AUTHORITY,
        "selection_rule": (
            "ALL_DISTINCT_POSITIVE_OPPONENT_COUNTERFACTUAL_REACH_LEVELS_"
            "OBSERVED_PER_FAMILY_BEFORE_FRONTIER_EXECUTION"
        ),
        "upstream": {
            "exact_ladder_run_id": EXACT_LADDER_RUN_ID,
            "exact_ladder_aggregate_file_sha256": EXACT_LADDER_AGGREGATE_FILE_SHA256,
            "interval_bridge_run_id": INTERVAL_BRIDGE_RUN_ID,
            "interval_bridge_aggregate_file_sha256": INTERVAL_BRIDGE_AGGREGATE_FILE_SHA256,
            "reach_geometry_run_id": REACH_GEOMETRY_RUN_ID,
            "reach_geometry_internal_sha256": REACH_GEOMETRY_INTERNAL_SHA256,
            "reach_geometry_artifact_digest": REACH_GEOMETRY_ARTIFACT_DIGEST,
        },
        "threshold_hex_by_family": {
            family: list(values)
            for family, values in sorted(THRESHOLD_HEX_BY_FAMILY.items())
        },
        "expected_reference": {
            family: {
                str(player): dict(values)
                for player, values in sorted(players.items())
            }
            for family, players in sorted(EXPECTED_REFERENCE.items())
        },
        "geometry_cell_sha256": {
            family: {
                str(player): value
                for player, value in sorted(players.items())
            }
            for family, players in sorted(GEOMETRY_CELL_SHA256.items())
        },
        "production_certification_eligible": False,
        "real_routes_certified": 0,
    }


def manifest_sha256() -> str:
    raw = json.dumps(
        unsigned_manifest(),
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def manifest_payload() -> dict[str, object]:
    payload = unsigned_manifest()
    payload["sha256"] = manifest_sha256()
    return payload
