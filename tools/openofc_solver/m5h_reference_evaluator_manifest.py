from __future__ import annotations

"""Immutable authority manifest for M5H Normal-route reference evaluators.

The manifest exists to prevent a learned response/search procedure from silently
becoming a low-exploitability certification oracle.  A screening method may
produce useful held-out lower-bound evidence, but only a method class whose own
validation evidence supports an upper/exact strategic guarantee can be marked
certification eligible.
"""

from dataclasses import dataclass
import hashlib
import json
from typing import Sequence

from hu_continuation import KERNEL_NORMAL_FANTASY, KERNEL_NORMAL_NORMAL

MANIFEST_SCHEMA = "openofc-m5h-reference-evaluator-manifest-v1"
AUTHORITY = "SHA_BOUND_REFERENCE_EVALUATOR_AUTHORITY_MANIFEST"

METHOD_LEARNED_RESPONSE_LOWER_BOUND = "LEARNED_RESPONSE_LOWER_BOUND"
METHOD_EXACT_BEST_RESPONSE = "EXACT_BEST_RESPONSE"
METHOD_VALIDATED_EXPLOITABILITY_BOUND = "VALIDATED_EXPLOITABILITY_BOUND"

CAPABILITY_SCREENING_ONLY = "SCREENING_LOWER_BOUND_ONLY"
CAPABILITY_CERTIFICATION_ELIGIBLE = "LOW_EXPLOITABILITY_CERTIFICATION_ELIGIBLE"

SUPPORTED_METHODS = (
    METHOD_LEARNED_RESPONSE_LOWER_BOUND,
    METHOD_EXACT_BEST_RESPONSE,
    METHOD_VALIDATED_EXPLOITABILITY_BOUND,
)
SUPPORTED_CAPABILITIES = (
    CAPABILITY_SCREENING_ONLY,
    CAPABILITY_CERTIFICATION_ELIGIBLE,
)
SUPPORTED_KERNELS = (KERNEL_NORMAL_NORMAL, KERNEL_NORMAL_FANTASY)


def _canonical_bytes(payload: object) -> bytes:
    return json.dumps(
        payload, sort_keys=True, separators=(",", ":"), allow_nan=False
    ).encode("utf-8")


def _sha(payload: object) -> str:
    return hashlib.sha256(_canonical_bytes(payload)).hexdigest()


def _require_sha256(value: object, label: str) -> str:
    text = str(value).lower()
    if len(text) != 64:
        raise ValueError(f"{label} must be a SHA-256")
    try:
        int(text, 16)
    except ValueError as exc:
        raise ValueError(f"{label} must be a SHA-256") from exc
    return text


@dataclass(frozen=True)
class ReferenceEvaluatorManifest:
    evaluator_id: str
    implementation_sha256: str
    validation_evidence_sha256: str
    method_class: str
    capability: str
    validated_kernel_kinds: tuple[str, ...]
    reference_authority: str
    validation_provenance: str
    sha256: str
    schema: str = MANIFEST_SCHEMA
    authority: str = AUTHORITY

    def __post_init__(self) -> None:
        if self.schema != MANIFEST_SCHEMA or self.authority != AUTHORITY:
            raise ValueError("unsupported M5H reference evaluator manifest")
        if not str(self.evaluator_id).strip():
            raise ValueError("reference evaluator id must be non-empty")
        _require_sha256(self.implementation_sha256, "implementation_sha256")
        _require_sha256(
            self.validation_evidence_sha256, "validation_evidence_sha256"
        )
        if self.method_class not in SUPPORTED_METHODS:
            raise ValueError("unsupported reference evaluator method class")
        if self.capability not in SUPPORTED_CAPABILITIES:
            raise ValueError("unsupported reference evaluator capability")
        if not self.validated_kernel_kinds:
            raise ValueError("reference evaluator must validate at least one kernel")
        if tuple(sorted(set(self.validated_kernel_kinds))) != self.validated_kernel_kinds:
            raise ValueError("validated kernel kinds must be unique and sorted")
        if any(kind not in SUPPORTED_KERNELS for kind in self.validated_kernel_kinds):
            raise ValueError("reference evaluator manifest contains unsupported kernel")
        if not str(self.reference_authority).strip() or not str(
            self.validation_provenance
        ).strip():
            raise ValueError("reference evaluator authority/provenance must be non-empty")

        if (
            self.method_class == METHOD_LEARNED_RESPONSE_LOWER_BOUND
            and self.capability != CAPABILITY_SCREENING_ONLY
        ):
            raise ValueError(
                "learned-response lower bounds can only have screening capability"
            )
        if (
            self.capability == CAPABILITY_CERTIFICATION_ELIGIBLE
            and self.method_class
            not in (METHOD_EXACT_BEST_RESPONSE, METHOD_VALIDATED_EXPLOITABILITY_BOUND)
        ):
            raise ValueError(
                "certification capability requires exact/validated bound method"
            )
        if self.sha256 != _sha(self.unsigned_payload()):
            raise ValueError("reference evaluator manifest SHA-256 mismatch")

    @property
    def certification_eligible(self) -> bool:
        return self.capability == CAPABILITY_CERTIFICATION_ELIGIBLE

    def unsigned_payload(self) -> dict[str, object]:
        return {
            "schema": self.schema,
            "authority": self.authority,
            "evaluator_id": self.evaluator_id,
            "implementation_sha256": self.implementation_sha256,
            "validation_evidence_sha256": self.validation_evidence_sha256,
            "method_class": self.method_class,
            "capability": self.capability,
            "validated_kernel_kinds": list(self.validated_kernel_kinds),
            "reference_authority": self.reference_authority,
            "validation_provenance": self.validation_provenance,
        }

    def supports_kernel(self, kernel_kind: str) -> bool:
        return kernel_kind in self.validated_kernel_kinds


def freeze_reference_evaluator_manifest(
    *,
    evaluator_id: str,
    implementation_sha256: str,
    validation_evidence_sha256: str,
    method_class: str,
    capability: str,
    validated_kernel_kinds: Sequence[str],
    reference_authority: str,
    validation_provenance: str,
) -> ReferenceEvaluatorManifest:
    kernels = tuple(sorted(set(str(kind) for kind in validated_kernel_kinds)))
    payload: dict[str, object] = {
        "schema": MANIFEST_SCHEMA,
        "authority": AUTHORITY,
        "evaluator_id": str(evaluator_id).strip(),
        "implementation_sha256": str(implementation_sha256).lower(),
        "validation_evidence_sha256": str(validation_evidence_sha256).lower(),
        "method_class": str(method_class),
        "capability": str(capability),
        "validated_kernel_kinds": list(kernels),
        "reference_authority": str(reference_authority).strip(),
        "validation_provenance": str(validation_provenance).strip(),
    }
    return ReferenceEvaluatorManifest(
        evaluator_id=str(payload["evaluator_id"]),
        implementation_sha256=str(payload["implementation_sha256"]),
        validation_evidence_sha256=str(payload["validation_evidence_sha256"]),
        method_class=str(payload["method_class"]),
        capability=str(payload["capability"]),
        validated_kernel_kinds=kernels,
        reference_authority=str(payload["reference_authority"]),
        validation_provenance=str(payload["validation_provenance"]),
        sha256=_sha(payload),
    )
