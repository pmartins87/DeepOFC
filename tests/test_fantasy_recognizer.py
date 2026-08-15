from deepofc.fantasy_recognizer import (
    BinaryTemplate,
    RANK_PROBE_MAX_DISTANCE,
    RANK_PROBE_MIN_MARGIN,
    SUIT_PROBE_MAX_DISTANCE,
    SUIT_PROBE_MIN_MARGIN,
    SUIT_RGB_PROTOTYPES,
    aligned_binary_distance,
    binary_union_xor_distance,
    classify_rank_mask,
    classify_suit_rgb,
)


def rows(*values: int) -> tuple[int, ...]:
    return tuple(values)


def test_binary_distance_is_zero_for_identity_and_translation_alignment():
    # Keep the glyph away from the mask edges so a 1-pixel translation does not
    # destroy information through clipping. The aligned metric must recover it.
    glyph = rows(0b0001000, 0b0011100, 0b0101010, 0b0001000, 0b0001000, 0)
    assert binary_union_xor_distance(glyph, glyph, width=7) == 0.0
    shifted = rows(0, 0b0010000, 0b0111000, 0b1010100, 0b0010000, 0b0010000)
    assert aligned_binary_distance(glyph, shifted, width=7, max_shift=1) == 0.0


def test_rank_classifier_requires_distance_and_margin_not_just_nearest_template():
    a = BinaryTemplate("A", rows(0b00100, 0b01010, 0b11111, 0b10001), width=5)
    k = BinaryTemplate("K", rows(0b10001, 0b10010, 0b11100, 0b10010), width=5)
    observed = a.rows
    accepted = classify_rank_mask(
        observed,
        (a, k),
        width=5,
        max_shift=0,
        max_distance=0.1,
        min_margin=0.1,
    )
    assert accepted.accepted
    assert accepted.value == "A"

    # Identical templates under different labels are maximally ambiguous. A
    # nearest-neighbor-only recognizer would make an arbitrary choice; DeepOFC
    # must reject it.
    ambiguous = classify_rank_mask(
        observed,
        (a, BinaryTemplate("K", a.rows, width=5)),
        width=5,
        max_shift=0,
        max_distance=0.1,
        min_margin=0.1,
    )
    assert not ambiguous.accepted
    assert ambiguous.value is None
    assert ambiguous.reason == "margin"


def test_rank_classifier_rejects_distant_noise_even_if_one_template_is_nearest():
    a = BinaryTemplate("A", rows(0b00100, 0b01010, 0b11111, 0b10001), width=5)
    k = BinaryTemplate("K", rows(0b10001, 0b10010, 0b11100, 0b10010), width=5)
    noise = rows(0b11111, 0b00000, 0b11111, 0b00000)
    result = classify_rank_mask(
        noise,
        (a, k),
        width=5,
        max_shift=0,
        max_distance=0.2,
        min_margin=0.01,
    )
    assert not result.accepted
    assert result.reason == "distance"


def test_suit_probe_prototypes_accept_each_observed_color_center():
    for suit, rgb in SUIT_RGB_PROTOTYPES.items():
        result = classify_suit_rgb(rgb)
        assert result.accepted
        assert result.value == suit
        assert result.best_distance == 0.0


def test_suit_classifier_rejects_ambiguous_midpoint():
    # Isolate two artificial prototypes so the geometric midpoint is an exact
    # tie. Using the real four-suit set here would make a third suit legitimately
    # closer to the c/d midpoint, which would test RGB geometry rather than the
    # intended ambiguity gate.
    prototypes = {
        "c": (0.0, 100.0, 0.0),
        "d": (100.0, 0.0, 0.0),
    }
    midpoint = (50.0, 50.0, 0.0)
    result = classify_suit_rgb(
        midpoint,
        prototypes=prototypes,
        max_distance=200,
        min_margin=1.0,
    )
    assert not result.accepted
    assert result.reason == "margin"


def test_probe_thresholds_remain_conservative_relative_to_measured_extrema():
    # The replay report measured max correct rank distance ~0.48062 and minimum
    # correct rank margin ~0.04043. The executable probe thresholds sit just
    # outside/inside those extrema and remain separate from runtime authority.
    assert RANK_PROBE_MAX_DISTANCE == 0.50
    assert RANK_PROBE_MIN_MARGIN == 0.04
    # Suit probe measured max correct distance ~31.90 and min margin ~89.55.
    assert SUIT_PROBE_MAX_DISTANCE == 40.0
    assert SUIT_PROBE_MIN_MARGIN == 80.0
