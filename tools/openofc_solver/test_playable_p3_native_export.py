from __future__ import annotations

import json
from pathlib import Path
import random
import shutil

import pytest

from playable_p2_candidate import load_manifest
from playable_p3_native_export import (
    AUTHORITY,
    WEIGHT_HEADER,
    export_native_bundle,
    load_native_export,
)
from strategic_cfr import HUState, child_state, sample_deal_plan
from strategic_suit_symmetry import canonical_node_view

ROOT = Path(__file__).resolve().parents[2]
P2_MANIFEST = (
    ROOT
    / "artifacts"
    / "playable_p2_normal_normal_candidate_20260902"
    / "playable_p2_manifest.json"
)
P2_MANIFEST_SHA256 = (
    "f10c079a61ba08832cfc334afb9c055e023dfc9c23a24140d02b2f7bd8413898"
)
NATIVE_DIR = ROOT / "artifacts" / "playable_p3_native_policy_export_20260902"
NATIVE_MANIFEST = NATIVE_DIR / "playable_p3_native_manifest.json"
NATIVE_MANIFEST_SHA256 = (
    "ff880a76bce9885f19b7297952a9d182d0ba2c54e10681baa74937f66b4691bc"
)


def test_native_export_reloads_with_exact_p2_weights_and_identities() -> None:
    p2 = load_manifest(P2_MANIFEST)
    native = load_native_export(
        NATIVE_MANIFEST,
        expected_manifest_sha256=NATIVE_MANIFEST_SHA256,
        p2_bundle=p2,
    )
    assert native.p2_manifest_sha256 == P2_MANIFEST_SHA256
    assert native.p2_source_commit == p2.source_commit
    assert len(native.route_for_button(0).weights) == 65_753
    assert len(native.route_for_button(1).weights) == 65_753


def test_native_policy_matches_p2_on_a_complete_hand_for_each_button() -> None:
    p2 = load_manifest(P2_MANIFEST)
    native = load_native_export(
        NATIVE_MANIFEST,
        expected_manifest_sha256=NATIVE_MANIFEST_SHA256,
        p2_bundle=p2,
    )
    for button in (0, 1):
        p2_route = p2.route_for_button(button)
        native_route = native.route_for_button(button)
        state = HUState(plan=sample_deal_plan(random.Random(2026090400 + button)))
        decisions = 0
        while not state.terminal():
            key, pairs, _suit_map = canonical_node_view(state)
            action_keys = tuple(action_key for action_key, _action in pairs)
            assert native_route.policy(key, action_keys) == p2_route.policy(
                key, action_keys
            )
            selected = native_route.select_action(key, action_keys)
            assert selected == p2_route.select_action(key, action_keys)
            state = child_state(
                state,
                next(action for action_key, action in pairs if action_key == selected),
            )
            decisions += 1
        assert decisions == 10


def test_native_export_is_byte_deterministic(tmp_path: Path) -> None:
    generated_manifest = export_native_bundle(
        P2_MANIFEST,
        tmp_path,
        expected_p2_manifest_sha256=P2_MANIFEST_SHA256,
    )
    for filename in (
        "playable_p3_b0_weights.f64le",
        "playable_p3_b1_weights.f64le",
        "playable_p3_native_manifest.json",
    ):
        assert (tmp_path / filename).read_bytes() == (NATIVE_DIR / filename).read_bytes()
    assert generated_manifest == tmp_path / "playable_p3_native_manifest.json"


def test_native_files_strip_optimizer_state_and_stay_bounded() -> None:
    payload = json.loads(NATIVE_MANIFEST.read_text(encoding="utf-8"))
    assert payload["authority"] == AUTHORITY
    assert payload["physical_execution_authorized"] is False
    assert "grad_sq" not in NATIVE_MANIFEST.read_text(encoding="utf-8")
    for row in payload["routes"]:
        path = NATIVE_DIR / row["weights_file"]
        assert path.stat().st_size == WEIGHT_HEADER.size + row["weights_count"] * 8
        assert path.stat().st_size < (P2_MANIFEST.parent / (
            "playable_p2_route_b0.json.gz" if row["button"] == 0
            else "playable_p2_route_b1.json.gz"
        )).stat().st_size


def test_native_weight_tamper_and_wrong_pin_fail_closed(tmp_path: Path) -> None:
    for path in NATIVE_DIR.iterdir():
        shutil.copy2(path, tmp_path / path.name)
    weight_path = tmp_path / "playable_p3_b0_weights.f64le"
    raw = bytearray(weight_path.read_bytes())
    raw[-1] ^= 0x01
    weight_path.write_bytes(raw)
    with pytest.raises(ValueError, match="weight-file SHA-256 mismatch"):
        load_native_export(
            tmp_path / "playable_p3_native_manifest.json",
            expected_manifest_sha256=NATIVE_MANIFEST_SHA256,
        )
    with pytest.raises(ValueError, match="differs from the pinned"):
        load_native_export(
            NATIVE_MANIFEST,
            expected_manifest_sha256="0" * 64,
        )
