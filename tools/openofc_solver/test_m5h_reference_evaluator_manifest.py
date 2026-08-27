from __future__ import annotations

from dataclasses import replace

import pytest

from hu_continuation import KERNEL_NORMAL_FANTASY, KERNEL_NORMAL_NORMAL
from m5h_reference_evaluator_manifest import (
    CAPABILITY_CERTIFICATION_ELIGIBLE,
    CAPABILITY_SCREENING_ONLY,
    METHOD_EXACT_BEST_RESPONSE,
    METHOD_LEARNED_RESPONSE_LOWER_BOUND,
    METHOD_VALIDATED_EXPLOITABILITY_BOUND,
    freeze_reference_evaluator_manifest,
)

SHA_A = "a" * 64
SHA_B = "b" * 64


def screening_manifest():
    return freeze_reference_evaluator_manifest(
        evaluator_id="m5i-learned-response-screen",
        implementation_sha256=SHA_A,
        validation_evidence_sha256=SHA_B,
        method_class=METHOD_LEARNED_RESPONSE_LOWER_BOUND,
        capability=CAPABILITY_SCREENING_ONLY,
        validated_kernel_kinds=(KERNEL_NORMAL_NORMAL,),
        reference_authority="LOWER_BOUND_SCREENING_ONLY",
        validation_provenance="mechanical validation fixture",
    )


def test_manifest_is_deterministic_and_kernel_order_independent() -> None:
    first = freeze_reference_evaluator_manifest(
        evaluator_id="validated-bound",
        implementation_sha256=SHA_A,
        validation_evidence_sha256=SHA_B,
        method_class=METHOD_VALIDATED_EXPLOITABILITY_BOUND,
        capability=CAPABILITY_CERTIFICATION_ELIGIBLE,
        validated_kernel_kinds=(KERNEL_NORMAL_FANTASY, KERNEL_NORMAL_NORMAL),
        reference_authority="VALIDATED_BOUND",
        validation_provenance="independent validation artifact",
    )
    second = freeze_reference_evaluator_manifest(
        evaluator_id="validated-bound",
        implementation_sha256=SHA_A,
        validation_evidence_sha256=SHA_B,
        method_class=METHOD_VALIDATED_EXPLOITABILITY_BOUND,
        capability=CAPABILITY_CERTIFICATION_ELIGIBLE,
        validated_kernel_kinds=(KERNEL_NORMAL_NORMAL, KERNEL_NORMAL_FANTASY),
        reference_authority="VALIDATED_BOUND",
        validation_provenance="independent validation artifact",
    )
    assert first.sha256 == second.sha256
    assert first.validated_kernel_kinds == tuple(sorted(first.validated_kernel_kinds))
    assert first.certification_eligible


def test_learned_response_cannot_claim_certification_authority() -> None:
    with pytest.raises(ValueError, match="lower bounds"):
        freeze_reference_evaluator_manifest(
            evaluator_id="bad-learned-response",
            implementation_sha256=SHA_A,
            validation_evidence_sha256=SHA_B,
            method_class=METHOD_LEARNED_RESPONSE_LOWER_BOUND,
            capability=CAPABILITY_CERTIFICATION_ELIGIBLE,
            validated_kernel_kinds=(KERNEL_NORMAL_NORMAL,),
            reference_authority="INVALID",
            validation_provenance="must fail",
        )


def test_exact_best_response_may_be_explicitly_certification_eligible() -> None:
    manifest = freeze_reference_evaluator_manifest(
        evaluator_id="exact-br-fixture",
        implementation_sha256=SHA_A,
        validation_evidence_sha256=SHA_B,
        method_class=METHOD_EXACT_BEST_RESPONSE,
        capability=CAPABILITY_CERTIFICATION_ELIGIBLE,
        validated_kernel_kinds=(KERNEL_NORMAL_NORMAL,),
        reference_authority="EXACT_BR_TEST_AUTHORITY",
        validation_provenance="unit fixture only",
    )
    assert manifest.certification_eligible
    assert manifest.supports_kernel(KERNEL_NORMAL_NORMAL)
    assert not manifest.supports_kernel(KERNEL_NORMAL_FANTASY)


def test_manifest_tampering_is_detected() -> None:
    manifest = screening_manifest()
    with pytest.raises(ValueError, match="SHA-256 mismatch"):
        replace(manifest, validation_provenance="tampered")


def test_validation_evidence_is_sha_bound() -> None:
    first = screening_manifest()
    second = freeze_reference_evaluator_manifest(
        evaluator_id=first.evaluator_id,
        implementation_sha256=first.implementation_sha256,
        validation_evidence_sha256="c" * 64,
        method_class=first.method_class,
        capability=first.capability,
        validated_kernel_kinds=first.validated_kernel_kinds,
        reference_authority=first.reference_authority,
        validation_provenance=first.validation_provenance,
    )
    assert first.sha256 != second.sha256
