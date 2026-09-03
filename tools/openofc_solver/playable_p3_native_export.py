from __future__ import annotations

"""Deterministic native-weight export for the P3 OpenHoldem shadow bridge.

The P2 route packages intentionally retain training and optimizer state.  The
runtime needs only immutable prediction weights.  This module exports one
dense IEEE-754 binary vector per button route, with a fixed self-identifying
header and a canonical aggregate manifest.  It also reloads the export and
recomputes policy probabilities without consulting the P2 model object.

This is an interchange contract, not physical-execution authority.
"""

import argparse
from dataclasses import dataclass
import hashlib
import json
import math
from pathlib import Path
import re
import struct
from typing import Mapping, Sequence

from playable_p2_candidate import (
    LoadedPlayableManifest,
    LoadedPlayableRoute,
    file_sha256,
    load_manifest,
    payload_sha256,
)
from playable_p3_runtime_adapter import ADAPTER_SCHEMA
from strategic_advantage_model import interaction_terms
from strategic_feature_encoder import (
    ACTION_SIZE,
    FEATURE_DIMENSION,
    OFFSET_ACTION,
    SCHEMA as FEATURE_SCHEMA,
    encode_canonical_action_key,
    encode_canonical_state_key,
)

EXPORT_SCHEMA = "openofc-playable-p3-native-policy-export-v1"
AUTHORITY = "SHADOW_ONLY_NO_PHYSICAL_EXECUTION_AUTHORITY"
WEIGHT_FORMAT = "openofc-p3-dense-float64-le-v1"
WEIGHT_MAGIC = b"DOFCP3W1"
WEIGHT_VERSION = 1
WEIGHT_HEADER = struct.Struct("<8sIIII32s32s32s32s")
SELECTION_RULE = "maximum_probability_then_lexicographically_smallest_action_key"
SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")


def _source_sha256(filename: str) -> str:
    return file_sha256(Path(__file__).with_name(filename))


def _sha_bytes(value: str, *, label: str) -> bytes:
    if not SHA256_PATTERN.fullmatch(value):
        raise ValueError(f"{label} must be a lowercase SHA-256")
    return bytes.fromhex(value)


def _route_filename(button: int) -> str:
    return f"playable_p3_b{button}_weights.f64le"


def _dense_weights(route: LoadedPlayableRoute) -> tuple[float, ...]:
    weights = [0.0] * route.model.dimension
    for index, value in route.model.weights.items():
        if index < 0 or index >= len(weights) or not math.isfinite(value):
            raise ValueError("P2 model contains an invalid deployment weight")
        weights[index] = float(value)
    return tuple(weights)


def _weight_bytes(
    route: LoadedPlayableRoute,
    *,
    p2_manifest_sha256: str,
) -> bytes:
    button = route.state.button
    dense = _dense_weights(route)
    header = WEIGHT_HEADER.pack(
        WEIGHT_MAGIC,
        WEIGHT_VERSION,
        button,
        route.model.buckets,
        route.model.dimension,
        _sha_bytes(p2_manifest_sha256, label="P2 manifest identity"),
        _sha_bytes(route.snapshot.model_sha256, label="P2 model identity"),
        _sha_bytes(route.snapshot.sha256, label="P2 snapshot identity"),
        _sha_bytes(route.route_sha256, label="P2 route identity"),
    )
    return header + struct.pack(f"<{len(dense)}d", *dense)


def _route_manifest_row(
    bundle: LoadedPlayableManifest,
    button: int,
    exported_path: Path,
) -> dict[str, object]:
    route = bundle.route_for_button(button)
    return {
        "button": button,
        "state": route.state.as_key(),
        "source_route_file_sha256": bundle.file_sha256_for_button(button),
        "route_sha256": route.route_sha256,
        "policy_snapshot_sha256": route.snapshot.sha256,
        "model_sha256": route.snapshot.model_sha256,
        "weights_file": exported_path.name,
        "weights_file_sha256": file_sha256(exported_path),
        "weights_format": WEIGHT_FORMAT,
        "weights_count": route.model.dimension,
        "nonzero_weights": len(route.model.weights),
    }


def build_native_manifest(
    bundle: LoadedPlayableManifest,
    exported_paths: Sequence[Path],
) -> dict[str, object]:
    paths = tuple(Path(path) for path in exported_paths)
    if len(paths) != 2:
        raise ValueError("P3 native export requires exactly two weight files")
    rows = [
        _route_manifest_row(bundle, button, paths[button])
        for button in (0, 1)
    ]
    buckets = {bundle.route_for_button(button).model.buckets for button in (0, 1)}
    dimensions = {
        bundle.route_for_button(button).model.dimension for button in (0, 1)
    }
    if len(buckets) != 1 or len(dimensions) != 1:
        raise ValueError("P2 B0/B1 model dimensions must agree for native export")
    if next(iter(buckets)) != 1 << 16 or next(iter(dimensions)) != (
        1 + ACTION_SIZE + (1 << 16)
    ):
        raise ValueError("P3 native v1 requires the frozen 2^16-bucket model")
    base: dict[str, object] = {
        "schema": EXPORT_SCHEMA,
        "authority": AUTHORITY,
        "physical_execution_authorized": False,
        "adapter_schema": ADAPTER_SCHEMA,
        "p2_manifest_sha256": bundle.manifest_sha256,
        "p2_source_commit": bundle.source_commit,
        "selection_rule": SELECTION_RULE,
        "source_files": {
            "playable_p3_native_export.py": _source_sha256(
                "playable_p3_native_export.py"
            ),
            "playable_p3_runtime_adapter.py": _source_sha256(
                "playable_p3_runtime_adapter.py"
            ),
            "strategic_suit_symmetry.py": _source_sha256(
                "strategic_suit_symmetry.py"
            ),
            "strategic_feature_encoder.py": _source_sha256(
                "strategic_feature_encoder.py"
            ),
            "strategic_advantage_model.py": _source_sha256(
                "strategic_advantage_model.py"
            ),
        },
        "feature_contract": {
            "schema": FEATURE_SCHEMA,
            "feature_dimension": FEATURE_DIMENSION,
            "offset_action": OFFSET_ACTION,
            "action_size": ACTION_SIZE,
            "interaction_buckets": next(iter(buckets)),
            "prediction_dimension": next(iter(dimensions)),
            "hash": "splitmix64-finalizer-v1",
            "policy": "normalize-positive-advantage-or-uniform",
        },
        "binary_header": {
            "format": WEIGHT_FORMAT,
            "magic_ascii": WEIGHT_MAGIC.decode("ascii"),
            "version": WEIGHT_VERSION,
            "size_bytes": WEIGHT_HEADER.size,
            "layout": (
                "magic[8],version:u32,button:u32,buckets:u32,dimension:u32,"
                "p2_manifest[32],model[32],snapshot[32],route[32],weights:f64[]"
            ),
            "byte_order": "little-endian",
        },
        "routes": rows,
        "limitations": {
            "normal_normal_only": True,
            "formal_certification": False,
            "runtime_binding_complete": False,
            "recorded_shadow_required": True,
        },
    }
    base["sha256"] = payload_sha256(base)
    return base


def export_native_bundle(
    p2_manifest_path: Path,
    output_dir: Path,
    *,
    expected_p2_manifest_sha256: str,
) -> Path:
    bundle = load_manifest(Path(p2_manifest_path))
    if bundle.manifest_sha256 != expected_p2_manifest_sha256:
        raise ValueError("P3 export source differs from the pinned P2 manifest")
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    paths: list[Path] = []
    for button in (0, 1):
        path = out / _route_filename(button)
        path.write_bytes(
            _weight_bytes(
                bundle.route_for_button(button),
                p2_manifest_sha256=bundle.manifest_sha256,
            )
        )
        paths.append(path)
    payload = build_native_manifest(bundle, paths)
    manifest_path = out / "playable_p3_native_manifest.json"
    manifest_path.write_text(
        json.dumps(payload, indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    return manifest_path


@dataclass(frozen=True)
class LoadedNativeRoute:
    button: int
    state: str
    weights: tuple[float, ...]
    buckets: int
    p2_route_file_sha256: str
    route_sha256: str
    snapshot_sha256: str
    model_sha256: str
    weights_file_sha256: str

    @property
    def dimension(self) -> int:
        return 1 + ACTION_SIZE + self.buckets

    def predict(self, canonical_key: str, canonical_action_key: str) -> float:
        state_features = encode_canonical_state_key(canonical_key)
        action_features = encode_canonical_action_key(canonical_action_key)
        return sum(
            self.weights[index] * value
            for index, value in interaction_terms(
                state_features,
                action_features,
                buckets=self.buckets,
            )
        )

    def policy(
        self,
        canonical_key: str,
        canonical_action_keys: Sequence[str],
    ) -> tuple[float, ...]:
        keys = tuple(str(key) for key in canonical_action_keys)
        if not keys or len(set(keys)) != len(keys):
            raise ValueError("native policy requires a non-empty unique legal set")
        scores = tuple(max(0.0, self.predict(canonical_key, key)) for key in keys)
        total = sum(scores)
        if total <= 0.0:
            probabilities = (1.0 / len(keys),) * len(keys)
        else:
            probabilities = tuple(score / total for score in scores)
        # ``policy_for_visible_node`` is the deployed P2 API.  It deliberately
        # validates and normalizes the model output once more; preserve that
        # exact floating-point operation order for byte-level replay parity.
        normalized_total = sum(probabilities)
        if normalized_total <= 0.0:
            raise ValueError("native policy returned zero probability mass")
        return tuple(probability / normalized_total for probability in probabilities)

    def select_action(
        self,
        canonical_key: str,
        canonical_action_keys: Sequence[str],
    ) -> str:
        keys = tuple(str(key) for key in canonical_action_keys)
        probabilities = self.policy(canonical_key, keys)
        maximum = max(probabilities)
        return min(
            key
            for key, probability in zip(keys, probabilities)
            if probability == maximum
        )


@dataclass(frozen=True)
class LoadedNativeExport:
    manifest_sha256: str
    p2_manifest_sha256: str
    p2_source_commit: str
    routes: tuple[LoadedNativeRoute, LoadedNativeRoute]

    def route_for_button(self, button: int) -> LoadedNativeRoute:
        if button not in (0, 1):
            raise ValueError("native policy button must be P0 or P1")
        route = self.routes[button]
        if route.button != button:
            raise AssertionError("native route tuple lost button ordering")
        return route


def _verify_native_manifest(payload: Mapping[str, object]) -> dict[str, object]:
    expected_fields = {
        "schema",
        "authority",
        "physical_execution_authorized",
        "adapter_schema",
        "p2_manifest_sha256",
        "p2_source_commit",
        "selection_rule",
        "source_files",
        "feature_contract",
        "binary_header",
        "routes",
        "limitations",
        "sha256",
    }
    if set(payload) != expected_fields:
        raise ValueError("P3 native manifest fields differ from schema")
    raw = dict(payload)
    expected = str(raw.pop("sha256", ""))
    if not SHA256_PATTERN.fullmatch(expected) or payload_sha256(raw) != expected:
        raise ValueError("P3 native manifest SHA-256 mismatch")
    if raw.get("schema") != EXPORT_SCHEMA or raw.get("authority") != AUTHORITY:
        raise ValueError("unsupported P3 native manifest schema/authority")
    if raw.get("physical_execution_authorized") is not False:
        raise ValueError("P3 native export cannot authorize physical execution")
    if raw.get("adapter_schema") != ADAPTER_SCHEMA:
        raise ValueError("P3 native export adapter schema mismatch")
    if raw.get("selection_rule") != SELECTION_RULE:
        raise ValueError("P3 native export selection rule mismatch")
    source_files = raw.get("source_files")
    expected_source_files = {
        "playable_p3_native_export.py",
        "playable_p3_runtime_adapter.py",
        "strategic_suit_symmetry.py",
        "strategic_feature_encoder.py",
        "strategic_advantage_model.py",
    }
    if (
        not isinstance(source_files, dict)
        or set(source_files) != expected_source_files
    ):
        raise ValueError("P3 native export source-file inventory mismatch")
    if any(
        not SHA256_PATTERN.fullmatch(str(source_files[name]))
        for name in expected_source_files
    ):
        raise ValueError("P3 native export source-file identity is invalid")
    limitations = raw.get("limitations")
    if limitations != {
        "normal_normal_only": True,
        "formal_certification": False,
        "runtime_binding_complete": False,
        "recorded_shadow_required": True,
    }:
        raise ValueError("P3 native export authority firewall mismatch")
    return raw


def _load_weight_file(
    path: Path,
    row: Mapping[str, object],
    *,
    p2_manifest_sha256: str,
) -> LoadedNativeRoute:
    raw = path.read_bytes()
    if file_sha256(path) != str(row["weights_file_sha256"]):
        raise ValueError("P3 native weight-file SHA-256 mismatch")
    if len(raw) < WEIGHT_HEADER.size:
        raise ValueError("P3 native weight file is truncated")
    (
        magic,
        version,
        button,
        buckets,
        dimension,
        manifest_bytes,
        model_bytes,
        snapshot_bytes,
        route_bytes,
    ) = WEIGHT_HEADER.unpack_from(raw)
    if magic != WEIGHT_MAGIC or version != WEIGHT_VERSION:
        raise ValueError("P3 native weight header format mismatch")
    if button != int(row["button"]):
        raise ValueError("P3 native weight header button mismatch")
    if manifest_bytes.hex() != p2_manifest_sha256:
        raise ValueError("P3 native weight header P2 identity mismatch")
    identities = (
        (model_bytes.hex(), str(row["model_sha256"]), "model"),
        (snapshot_bytes.hex(), str(row["policy_snapshot_sha256"]), "snapshot"),
        (route_bytes.hex(), str(row["route_sha256"]), "route"),
    )
    if any(actual != expected for actual, expected, _label in identities):
        raise ValueError("P3 native weight header route identity mismatch")
    expected_dimension = 1 + ACTION_SIZE + buckets
    if dimension != expected_dimension or dimension != int(row["weights_count"]):
        raise ValueError("P3 native weight dimension mismatch")
    expected_bytes = WEIGHT_HEADER.size + dimension * 8
    if len(raw) != expected_bytes:
        raise ValueError("P3 native weight file length mismatch")
    weights = struct.unpack_from(f"<{dimension}d", raw, WEIGHT_HEADER.size)
    if any(not math.isfinite(value) for value in weights):
        raise ValueError("P3 native weight file contains non-finite data")
    nonzero = sum(value != 0.0 for value in weights)
    if nonzero != int(row["nonzero_weights"]):
        raise ValueError("P3 native weight nonzero count mismatch")
    return LoadedNativeRoute(
        button=button,
        state=str(row["state"]),
        weights=weights,
        buckets=buckets,
        p2_route_file_sha256=str(row["source_route_file_sha256"]),
        route_sha256=route_bytes.hex(),
        snapshot_sha256=snapshot_bytes.hex(),
        model_sha256=model_bytes.hex(),
        weights_file_sha256=str(row["weights_file_sha256"]),
    )


def load_native_export(
    manifest_path: Path,
    *,
    expected_manifest_sha256: str,
    p2_bundle: LoadedPlayableManifest | None = None,
) -> LoadedNativeExport:
    if not SHA256_PATTERN.fullmatch(expected_manifest_sha256):
        raise ValueError("expected P3 native manifest identity must be SHA-256")
    path = Path(manifest_path)
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("P3 native manifest root must be an object")
    raw = _verify_native_manifest(payload)
    manifest_sha = str(payload["sha256"])
    if manifest_sha != expected_manifest_sha256:
        raise ValueError("loaded P3 native manifest differs from the pinned identity")
    p2_manifest_sha = str(raw.get("p2_manifest_sha256", ""))
    p2_source_commit = str(raw.get("p2_source_commit", ""))
    if not SHA256_PATTERN.fullmatch(p2_manifest_sha) or not re.fullmatch(
        r"[0-9a-f]{40}", p2_source_commit
    ):
        raise ValueError("P3 native manifest has invalid P2 source identity")

    feature = raw.get("feature_contract")
    if not isinstance(feature, dict) or feature != {
        "schema": FEATURE_SCHEMA,
        "feature_dimension": FEATURE_DIMENSION,
        "offset_action": OFFSET_ACTION,
        "action_size": ACTION_SIZE,
        "interaction_buckets": 1 << 16,
        "prediction_dimension": 1 + ACTION_SIZE + (1 << 16),
        "hash": "splitmix64-finalizer-v1",
        "policy": "normalize-positive-advantage-or-uniform",
    }:
        raise ValueError("P3 native feature contract mismatch")

    header = raw.get("binary_header")
    if not isinstance(header, dict) or header != {
        "format": WEIGHT_FORMAT,
        "magic_ascii": WEIGHT_MAGIC.decode("ascii"),
        "version": WEIGHT_VERSION,
        "size_bytes": WEIGHT_HEADER.size,
        "layout": (
            "magic[8],version:u32,button:u32,buckets:u32,dimension:u32,"
            "p2_manifest[32],model[32],snapshot[32],route[32],weights:f64[]"
        ),
        "byte_order": "little-endian",
    }:
        raise ValueError("P3 native binary-header contract mismatch")

    rows = raw.get("routes")
    if not isinstance(rows, list) or len(rows) != 2:
        raise ValueError("P3 native manifest requires B0/B1 route rows")
    expected_fields = {
        "button",
        "state",
        "source_route_file_sha256",
        "route_sha256",
        "policy_snapshot_sha256",
        "model_sha256",
        "weights_file",
        "weights_file_sha256",
        "weights_format",
        "weights_count",
        "nonzero_weights",
    }
    loaded: dict[int, LoadedNativeRoute] = {}
    for row in rows:
        if not isinstance(row, dict) or set(row) != expected_fields:
            raise ValueError("P3 native route row fields differ from schema")
        button = int(row["button"])
        if button not in (0, 1) or button in loaded:
            raise ValueError("P3 native routes must uniquely cover B0/B1")
        if row["weights_format"] != WEIGHT_FORMAT:
            raise ValueError("P3 native route weight format mismatch")
        filename = str(row["weights_file"])
        if Path(filename).name != filename or filename != _route_filename(button):
            raise ValueError("P3 native weight filename is unsafe or unexpected")
        loaded[button] = _load_weight_file(
            path.parent / filename,
            row,
            p2_manifest_sha256=p2_manifest_sha,
        )
    if set(loaded) != {0, 1}:
        raise ValueError("P3 native manifest is missing a button route")

    result = LoadedNativeExport(
        manifest_sha256=manifest_sha,
        p2_manifest_sha256=p2_manifest_sha,
        p2_source_commit=p2_source_commit,
        routes=(loaded[0], loaded[1]),
    )
    if p2_bundle is not None:
        if (
            p2_bundle.manifest_sha256 != result.p2_manifest_sha256
            or p2_bundle.source_commit != result.p2_source_commit
        ):
            raise ValueError("P3 native export differs from supplied P2 bundle")
        for button in (0, 1):
            native = result.route_for_button(button)
            p2 = p2_bundle.route_for_button(button)
            if native.weights != _dense_weights(p2):
                raise ValueError("P3 native weights differ from P2 model weights")
            if (
                native.model_sha256 != p2.snapshot.model_sha256
                or native.snapshot_sha256 != p2.snapshot.sha256
                or native.route_sha256 != p2.route_sha256
                or native.p2_route_file_sha256
                != p2_bundle.file_sha256_for_button(button)
            ):
                raise ValueError("P3 native route identities differ from P2")
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--p2-manifest", type=Path, required=True)
    parser.add_argument("--expected-p2-manifest-sha256", required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    path = export_native_bundle(
        args.p2_manifest,
        args.output_dir,
        expected_p2_manifest_sha256=args.expected_p2_manifest_sha256,
    )
    payload = json.loads(path.read_text(encoding="utf-8"))
    print(f"OPENOFC_PLAYABLE_P3_NATIVE_EXPORT={path}")
    print(f"OPENOFC_PLAYABLE_P3_NATIVE_MANIFEST_SHA256={payload['sha256']}")


if __name__ == "__main__":
    main()
