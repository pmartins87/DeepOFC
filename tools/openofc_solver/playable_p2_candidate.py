from __future__ import annotations

"""Immutable deployable package for the first PLAYABLE Normal/Normal candidate.

This is an engineering artifact, not a formal equilibrium certificate.  It
packages the bounded visible-information model distilled from the promoted
external-sampling MCCFR architecture, together with every identity needed to
reproduce and audit a deterministic decision.
"""

from dataclasses import asdict, dataclass
import gzip
import hashlib
import json
from pathlib import Path
import re
from typing import Mapping, Sequence

from hu_continuation import (
    BOTH_FOUL_NET_ZERO_INFERENCE,
    HUContinuationState,
    KERNEL_NORMAL_NORMAL,
    hand_kernel_kind,
)
from m5a_normal_normal_oracle import (
    NormalNormalPolicySnapshot,
    model_fingerprint,
    policy_for_visible_node,
)
from m5b_adaptive_normal_oracles import (
    AUTHORITY_NN,
    CONFIG_SCHEMA,
    MATERIALIZATION_SCHEMA,
    AdaptiveNormalConfig,
    NormalNormalMaterialization,
)
from fantasy_fantasy_payoff import continuation_fingerprint
from strategic_advantage_model import SparseActionAdvantageModel
from strategic_continuation_cfr import ContinuationObjective

ROUTE_SCHEMA = "openofc-playable-p2-normal-normal-route-v1"
MANIFEST_SCHEMA = "openofc-playable-p2-normal-normal-manifest-v1"
AUTHORITY = "PLAYABLE_CANDIDATE_NOT_FORMALLY_CERTIFIED"
SELECTION_RULE = "MAX_PROBABILITY_THEN_LEXICAL_CANONICAL_ACTION_KEY"
SOURCE_COMMIT_PATTERN = re.compile(r"^[0-9a-f]{40}$")


def canonical_bytes(payload: object) -> bytes:
    return json.dumps(
        payload, sort_keys=True, separators=(",", ":"), allow_nan=False
    ).encode("utf-8")


def payload_sha256(payload: object) -> str:
    return hashlib.sha256(canonical_bytes(payload)).hexdigest()


def file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _verify_embedded_sha(
    payload: Mapping[str, object], *, label: str
) -> dict[str, object]:
    raw = dict(payload)
    expected = str(raw.pop("sha256", ""))
    actual = payload_sha256(raw)
    if expected != actual:
        raise ValueError(f"{label} SHA-256 mismatch")
    return raw


def _snapshot_payload(snapshot: NormalNormalPolicySnapshot) -> dict[str, str]:
    payload = snapshot.unsigned_payload()
    payload["sha256"] = snapshot.sha256
    return payload


def build_route_payload(
    materialized: NormalNormalMaterialization,
    *,
    state: HUContinuationState,
    config: AdaptiveNormalConfig,
    objective: ContinuationObjective,
    source_commit: str,
) -> dict[str, object]:
    if hand_kernel_kind(state) != KERNEL_NORMAL_NORMAL:
        raise ValueError("P2 route only supports Normal/Normal states")
    if not SOURCE_COMMIT_PATTERN.fullmatch(str(source_commit)):
        raise ValueError("P2 source commit must be a lowercase 40-hex Git SHA")
    if objective.current_state != state:
        raise ValueError("P2 objective/state mismatch")
    if objective.both_foul_policy != BOTH_FOUL_NET_ZERO_INFERENCE:
        raise ValueError("P2 route requires the explicit both-foul net-zero inference")
    if any(float(value) != 0.0 for value in objective.values.values()):
        raise ValueError("P2 first candidate must bind the frozen zero continuation vector")

    fixed = materialized.fixed_oracle
    report = materialized.report
    model_payload = fixed.model.payload()
    model_sha = model_fingerprint(fixed.model)
    if fixed.snapshot.model_sha256 != model_sha:
        raise ValueError("P2 model/snapshot identity mismatch")
    if fixed.snapshot.both_foul_policy != objective.both_foul_policy:
        raise ValueError("P2 snapshot/objective both-foul policy mismatch")
    if report.config_sha256 != config.sha256:
        raise ValueError("P2 materialization/config identity mismatch")
    if report.state != state.as_key():
        raise ValueError("P2 materialization/state mismatch")
    if report.policy_snapshot_sha256 != fixed.snapshot.sha256:
        raise ValueError("P2 materialization/snapshot identity mismatch")

    base: dict[str, object] = {
        "schema": ROUTE_SCHEMA,
        "authority": AUTHORITY,
        "source_commit": source_commit,
        "state": state.as_key(),
        "button": state.button,
        "selection_rule": SELECTION_RULE,
        "training_config": {
            "payload": config.payload(),
            "sha256": config.sha256,
        },
        "continuation_objective": objective.payload(),
        "policy_snapshot": _snapshot_payload(fixed.snapshot),
        "model": model_payload,
        "model_sha256": model_sha,
        "materialization": asdict(report),
        "limitations": {
            "formal_certification": False,
            "production_certification_eligible": False,
            "real_routes_certified": 0,
            "fantasy_continuation_solved": False,
            "current_hand_only_zero_continuation": True,
            "both_foul_rule_is_inference_not_officially_source_frozen": True,
        },
    }
    base["sha256"] = payload_sha256(base)
    return base


def write_route(path: Path, payload: Mapping[str, object]) -> None:
    # Validate before writing so malformed packages never become artifacts.
    load_route_payload(payload)
    path.parent.mkdir(parents=True, exist_ok=True)
    raw = canonical_bytes(payload)
    if path.suffix == ".gz":
        with path.open("wb") as raw_handle:
            with gzip.GzipFile(
                fileobj=raw_handle, mode="wb", compresslevel=6, mtime=0
            ) as handle:
                handle.write(raw)
    else:
        path.write_bytes(raw)


@dataclass(frozen=True)
class LoadedPlayableRoute:
    source_commit: str
    state: HUContinuationState
    model: SparseActionAdvantageModel
    snapshot: NormalNormalPolicySnapshot
    route_sha256: str

    def policy(
        self, canonical_key: str, canonical_action_keys: Sequence[str]
    ) -> tuple[float, ...]:
        keys = tuple(str(key) for key in canonical_action_keys)
        if not keys or len(set(keys)) != len(keys):
            raise ValueError("P2 policy requires a non-empty unique legal action set")
        return policy_for_visible_node(
            self.model, canonical_key, keys
        )

    def select_action(
        self, canonical_key: str, canonical_action_keys: Sequence[str]
    ) -> str:
        keys = tuple(str(key) for key in canonical_action_keys)
        probabilities = self.policy(canonical_key, keys)
        maximum = max(probabilities)
        winners = [
            key
            for key, probability in zip(keys, probabilities)
            if probability == maximum
        ]
        return min(winners)


def _state_from_route(payload: Mapping[str, object]) -> HUContinuationState:
    button = int(payload["button"])
    state = HUContinuationState(button, 0, 0)
    if payload.get("state") != state.as_key():
        raise ValueError("P2 route state/button mismatch")
    return state


def load_route_payload(payload: Mapping[str, object]) -> LoadedPlayableRoute:
    raw = _verify_embedded_sha(payload, label="P2 route")
    if raw.get("schema") != ROUTE_SCHEMA or raw.get("authority") != AUTHORITY:
        raise ValueError("unsupported P2 route schema/authority")
    if raw.get("selection_rule") != SELECTION_RULE:
        raise ValueError("unsupported P2 deterministic selection rule")
    source_commit = str(raw.get("source_commit", ""))
    if not SOURCE_COMMIT_PATTERN.fullmatch(source_commit):
        raise ValueError("invalid P2 source commit")
    state = _state_from_route(raw)

    limitations = raw.get("limitations")
    if not isinstance(limitations, dict) or limitations != {
        "formal_certification": False,
        "production_certification_eligible": False,
        "real_routes_certified": 0,
        "fantasy_continuation_solved": False,
        "current_hand_only_zero_continuation": True,
        "both_foul_rule_is_inference_not_officially_source_frozen": True,
    }:
        raise ValueError("P2 authority firewall mismatch")

    config_block = raw.get("training_config")
    if not isinstance(config_block, dict) or not isinstance(
        config_block.get("payload"), dict
    ):
        raise ValueError("P2 training config is missing")
    config_payload = config_block["payload"]
    config_sha = str(config_block.get("sha256", ""))
    expected_config_keys = set(AdaptiveNormalConfig.__dataclass_fields__) | {"schema"}
    if set(config_payload) != expected_config_keys or config_payload.get(
        "schema"
    ) != CONFIG_SCHEMA:
        raise ValueError("P2 training config schema/fields mismatch")
    config = AdaptiveNormalConfig(
        **{
            key: value
            for key, value in config_payload.items()
            if key != "schema"
        }
    )
    if config.payload() != config_payload or config.sha256 != config_sha:
        raise ValueError("P2 training config SHA-256 mismatch")

    objective_payload = raw.get("continuation_objective")
    if not isinstance(objective_payload, dict):
        raise ValueError("P2 continuation objective is missing")
    objective = ContinuationObjective.from_payload(objective_payload)
    if objective.current_state != state:
        raise ValueError("P2 continuation objective/state mismatch")
    if objective.both_foul_policy != BOTH_FOUL_NET_ZERO_INFERENCE:
        raise ValueError("P2 both-foul inference identity mismatch")
    if any(float(value) != 0.0 for value in objective.values.values()):
        raise ValueError("P2 continuation objective is not the zero vector")
    if config_payload.get("both_foul_policy") != objective.both_foul_policy:
        raise ValueError("P2 config/objective both-foul policy mismatch")

    model_payload = raw.get("model")
    if not isinstance(model_payload, dict):
        raise ValueError("P2 model payload is missing")
    model = SparseActionAdvantageModel.from_payload(model_payload)
    model_sha = model_fingerprint(model)
    if raw.get("model_sha256") != model_sha:
        raise ValueError("P2 model SHA-256 mismatch")

    snapshot_payload = raw.get("policy_snapshot")
    if not isinstance(snapshot_payload, dict):
        raise ValueError("P2 policy snapshot is missing")
    snapshot = NormalNormalPolicySnapshot(
        model_sha256=str(snapshot_payload.get("model_sha256", "")),
        training_continuation_sha256=str(
            snapshot_payload.get("training_continuation_sha256", "")
        ),
        provenance=str(snapshot_payload.get("provenance", "")),
        both_foul_policy=str(snapshot_payload.get("both_foul_policy", "")),
        sha256=str(snapshot_payload.get("sha256", "")),
        schema=str(snapshot_payload.get("schema", "")),
        authority=str(snapshot_payload.get("authority", "")),
    )
    if snapshot.model_sha256 != model_sha:
        raise ValueError("P2 model/snapshot identity mismatch")
    if snapshot.both_foul_policy != objective.both_foul_policy:
        raise ValueError("P2 snapshot/objective both-foul policy mismatch")
    _checked, continuation_sha = continuation_fingerprint(objective.values)
    if snapshot.training_continuation_sha256 != continuation_sha:
        raise ValueError("P2 snapshot/objective continuation identity mismatch")

    materialization = raw.get("materialization")
    if not isinstance(materialization, dict):
        raise ValueError("P2 materialization report is missing")
    materialization_unsigned = dict(materialization)
    materialization_sha = str(materialization_unsigned.pop("sha256", ""))
    if payload_sha256(materialization_unsigned) != materialization_sha:
        raise ValueError("P2 materialization report SHA-256 mismatch")
    if (
        materialization.get("state") != state.as_key()
        or materialization.get("config_sha256") != config_sha
        or materialization.get("policy_snapshot_sha256") != snapshot.sha256
        or materialization.get("schema") != MATERIALIZATION_SCHEMA
        or materialization.get("authority") != AUTHORITY_NN
    ):
        raise ValueError("P2 materialization identity mismatch")

    return LoadedPlayableRoute(
        source_commit=source_commit,
        state=state,
        model=model,
        snapshot=snapshot,
        route_sha256=str(payload["sha256"]),
    )


def load_route(path: Path) -> LoadedPlayableRoute:
    if path.suffix == ".gz":
        with gzip.open(path, "rb") as handle:
            payload = json.loads(handle.read().decode("utf-8"))
    else:
        payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("P2 route root must be an object")
    return load_route_payload(payload)


def build_manifest(route_paths: Sequence[Path]) -> dict[str, object]:
    paths = tuple(Path(path) for path in route_paths)
    if len(paths) != 2:
        raise ValueError("P2 manifest requires exactly two route artifacts")
    rows: list[dict[str, object]] = []
    source_commits: set[str] = set()
    buttons: set[int] = set()
    for path in paths:
        route = load_route(path)
        source_commits.add(route.source_commit)
        buttons.add(route.state.button)
        rows.append(
            {
                "button": route.state.button,
                "state": route.state.as_key(),
                "file": path.name,
                "file_sha256": file_sha256(path),
                "route_sha256": route.route_sha256,
                "policy_snapshot_sha256": route.snapshot.sha256,
                "model_sha256": route.snapshot.model_sha256,
            }
        )
    if buttons != {0, 1} or len(source_commits) != 1:
        raise ValueError("P2 routes must cover B0/B1 from one source commit")
    base: dict[str, object] = {
        "schema": MANIFEST_SCHEMA,
        "authority": AUTHORITY,
        "source_commit": next(iter(source_commits)),
        "routes": sorted(rows, key=lambda row: int(row["button"])),
        "formal_certification": False,
        "production_certification_eligible": False,
        "real_routes_certified": 0,
        "verdict": "PASS_PLAYABLE_P2_ARTIFACT_IDENTITY",
    }
    base["sha256"] = payload_sha256(base)
    return base


def write_manifest(path: Path, route_paths: Sequence[Path]) -> dict[str, object]:
    payload = build_manifest(route_paths)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    return payload
