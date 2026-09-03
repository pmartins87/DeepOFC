from __future__ import annotations

import gzip
import json
import random

import pytest

from m5b_adaptive_normal_oracles import AdaptiveNormalConfig
from playable_p2_candidate import (
    AUTHORITY,
    build_manifest,
    canonical_bytes,
    load_manifest,
    load_route,
    load_route_payload,
    payload_sha256,
    write_manifest,
)
from run_playable_p2_train_route import train_route
from strategic_cfr import HUState, sample_deal_plan
from strategic_suit_symmetry import canonical_node_view


SOURCE_COMMIT = "a" * 40


def tiny_config() -> AdaptiveNormalConfig:
    return AdaptiveNormalConfig(
        training_iterations=1,
        evaluation_samples=2,
        replay_capacity=128,
        fit_epochs=1,
        model_buckets=8,
        learning_rate=0.05,
        l2=0.0,
        huber_delta=1.0,
        epsilon=0.6,
        base_seed=24680,
    )


def _visible_root() -> tuple[str, tuple[str, ...]]:
    state = HUState(plan=sample_deal_plan(random.Random(112233)))
    key, pairs, _suit_map = canonical_node_view(state)
    return key, tuple(action_key for action_key, _action in pairs)


def test_route_roundtrip_reproduces_policy_and_action(tmp_path) -> None:
    path = tmp_path / "route_b0.json.gz"
    payload = train_route(
        button=0,
        source_commit=SOURCE_COMMIT,
        output=path,
        config=tiny_config(),
    )
    first_bytes = path.read_bytes()
    route = load_route(path)
    key, actions = _visible_root()
    policy = route.policy(key, actions)
    selected = route.select_action(key, actions)

    assert payload["authority"] == AUTHORITY
    assert payload["limitations"]["formal_certification"] is False
    assert payload["limitations"]["real_routes_certified"] == 0
    assert len(policy) == len(actions)
    assert abs(sum(policy) - 1.0) < 1e-12
    assert selected in actions

    # Same logical training input and mtime=0 gzip are byte-stable.
    train_route(
        button=0,
        source_commit=SOURCE_COMMIT,
        output=path,
        config=tiny_config(),
    )
    assert path.read_bytes() == first_bytes
    reloaded = load_route(path)
    assert reloaded.policy(key, actions) == policy
    assert reloaded.select_action(key, actions) == selected


def test_route_rejects_inner_tamper_even_if_outer_sha_is_recomputed(tmp_path) -> None:
    path = tmp_path / "route_b0.json.gz"
    train_route(
        button=0,
        source_commit=SOURCE_COMMIT,
        output=path,
        config=tiny_config(),
    )
    with gzip.open(path, "rb") as handle:
        payload = json.loads(handle.read().decode("utf-8"))
    payload["model"]["seed"] += 1
    unsigned = dict(payload)
    unsigned.pop("sha256")
    payload["sha256"] = payload_sha256(unsigned)
    with pytest.raises(ValueError, match="model SHA-256"):
        load_route_payload(payload)


def test_manifest_binds_both_button_routes(tmp_path) -> None:
    paths = []
    for button in (1, 0):
        path = tmp_path / f"route_b{button}.json.gz"
        train_route(
            button=button,
            source_commit=SOURCE_COMMIT,
            output=path,
            config=tiny_config(),
        )
        paths.append(path)
    manifest = build_manifest(paths)
    assert manifest["authority"] == AUTHORITY
    assert [row["button"] for row in manifest["routes"]] == [0, 1]
    assert manifest["verdict"] == "PASS_PLAYABLE_P2_ARTIFACT_IDENTITY"
    assert manifest["formal_certification"] is False
    assert manifest["real_routes_certified"] == 0
    unsigned = dict(manifest)
    expected = unsigned.pop("sha256")
    assert payload_sha256(unsigned) == expected
    assert canonical_bytes(manifest) == canonical_bytes(dict(manifest))


def test_manifest_loader_revalidates_both_route_files(tmp_path) -> None:
    paths = []
    for button in (0, 1):
        path = tmp_path / f"route_b{button}.json.gz"
        train_route(
            button=button,
            source_commit=SOURCE_COMMIT,
            output=path,
            config=tiny_config(),
        )
        paths.append(path)
    manifest_path = tmp_path / "manifest.json"
    written = write_manifest(manifest_path, paths)

    loaded = load_manifest(manifest_path)
    assert loaded.manifest_sha256 == written["sha256"]
    assert loaded.source_commit == SOURCE_COMMIT
    assert loaded.route_for_button(0).state.button == 0
    assert loaded.route_for_button(1).state.button == 1
    assert loaded.file_sha256_for_button(0) == written["routes"][0]["file_sha256"]

    # A route-file mutation must be rejected even though the manifest itself
    # still has a valid embedded SHA.
    paths[1].write_bytes(paths[1].read_bytes() + b"tamper")
    with pytest.raises(ValueError, match="manifest does not match"):
        load_manifest(manifest_path)
