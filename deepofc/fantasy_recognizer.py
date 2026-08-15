from __future__ import annotations

from dataclasses import dataclass
from math import sqrt
from typing import Iterable, Mapping, Sequence


# These are REPLAY-PROBE thresholds, not live runtime certification.
# They are deliberately separated from the tablemap authority gate
# `ofc_fantasy_recognizer_calibrated`, which remains 0.
#
# Supplied 15-card Fantasy probe evidence:
# - rank leave-one-sample-out: 42/43 correct; only sole 8 exemplar cannot be
#   independently identified once withheld;
# - max correct aligned rank distance ~= 0.48062;
# - minimum correct best-vs-second-rank margin ~= 0.04043;
# - suit: 43/43; max correct RGB distance ~= 31.90;
# - minimum suit best-vs-second margin ~= 89.55.
RANK_PROBE_MAX_DISTANCE = 0.50
RANK_PROBE_MIN_MARGIN = 0.04
RANK_ALIGNMENT_PIXELS = 2
SUIT_PROBE_MAX_DISTANCE = 40.0
SUIT_PROBE_MIN_MARGIN = 80.0

# RGB medians derived from all 43 observed standard-card fan samples after
# slot-specific deskew. They are evidence features, not a substitute for exact
# card recognition or for 14/16/17-layout calibration.
SUIT_RGB_PROTOTYPES: Mapping[str, tuple[float, float, float]] = {
    "c": (30.0, 148.0, 1.0),
    "d": (20.0, 97.25, 192.0),
    "h": (227.0, 11.0, 24.5),
    "s": (48.0, 48.0, 48.0),
}


@dataclass(frozen=True)
class BinaryTemplate:
    label: str
    rows: tuple[int, ...]
    width: int = 16

    def __post_init__(self) -> None:
        if not self.label:
            raise ValueError("template label must be non-empty")
        if self.width <= 0:
            raise ValueError("template width must be positive")
        limit = 1 << self.width
        if not self.rows:
            raise ValueError("template must contain at least one row")
        if any(row < 0 or row >= limit for row in self.rows):
            raise ValueError("template row bitset exceeds declared width")

    @property
    def height(self) -> int:
        return len(self.rows)


@dataclass(frozen=True)
class RecognitionResult:
    value: str | None
    accepted: bool
    best_distance: float
    second_distance: float
    margin: float
    reason: str


def _popcount(value: int) -> int:
    return int(value).bit_count()


def _translate_rows(
    rows: Sequence[int],
    *,
    width: int,
    dx: int,
    dy: int,
) -> tuple[int, ...]:
    height = len(rows)
    out = [0] * height
    mask = (1 << width) - 1
    for src_y, row in enumerate(rows):
        dst_y = src_y + dy
        if dst_y < 0 or dst_y >= height:
            continue
        if dx >= 0:
            shifted = (row << dx) & mask
        else:
            shifted = row >> (-dx)
        out[dst_y] = shifted
    return tuple(out)


def binary_union_xor_distance(
    a: Sequence[int],
    b: Sequence[int],
    *,
    width: int = 16,
) -> float:
    """XOR / union distance for equal-size binary glyph masks."""

    if len(a) != len(b):
        raise ValueError("binary masks must have equal height")
    if width <= 0:
        raise ValueError("width must be positive")
    xor = 0
    union = 0
    mask = (1 << width) - 1
    for ra, rb in zip(a, b):
        ra &= mask
        rb &= mask
        xor += _popcount(ra ^ rb)
        union += _popcount(ra | rb)
    return 0.0 if union == 0 else xor / union


def aligned_binary_distance(
    observed: Sequence[int],
    template: Sequence[int],
    *,
    width: int = 16,
    max_shift: int = RANK_ALIGNMENT_PIXELS,
) -> float:
    """Best XOR/union distance over small integer translations.

    Slot-specific deskew removes most geometry differences; ±2 pixels absorbs
    residual crop/antialias offsets without allowing arbitrary deformation.
    """

    if len(observed) != len(template):
        raise ValueError("binary masks must have equal height")
    if max_shift < 0:
        raise ValueError("max_shift must be non-negative")
    best = 1.0
    for dy in range(-max_shift, max_shift + 1):
        for dx in range(-max_shift, max_shift + 1):
            shifted = _translate_rows(template, width=width, dx=dx, dy=dy)
            best = min(
                best,
                binary_union_xor_distance(observed, shifted, width=width),
            )
    return best


def classify_rank_mask(
    observed: Sequence[int],
    templates: Iterable[BinaryTemplate],
    *,
    width: int = 16,
    max_shift: int = RANK_ALIGNMENT_PIXELS,
    max_distance: float = RANK_PROBE_MAX_DISTANCE,
    min_margin: float = RANK_PROBE_MIN_MARGIN,
) -> RecognitionResult:
    """Classify a normalized rank mask, rejecting weak/ambiguous matches.

    Multiple templates for the same rank collapse to that rank's best distance.
    The function never returns the nearest rank as authoritative unless BOTH a
    maximum-distance gate and a best-vs-second-class margin gate pass.
    """

    per_label: dict[str, float] = {}
    for template in templates:
        if template.width != width or template.height != len(observed):
            raise ValueError("observed/template mask dimensions disagree")
        distance = aligned_binary_distance(
            observed,
            template.rows,
            width=width,
            max_shift=max_shift,
        )
        previous = per_label.get(template.label)
        if previous is None or distance < previous:
            per_label[template.label] = distance

    if not per_label:
        return RecognitionResult(None, False, 1.0, 1.0, 0.0, "no_templates")
    ordered = sorted(per_label.items(), key=lambda item: (item[1], item[0]))
    label, best = ordered[0]
    second = ordered[1][1] if len(ordered) > 1 else 1.0
    margin = second - best
    if best > max_distance:
        return RecognitionResult(None, False, best, second, margin, "distance")
    if margin < min_margin:
        return RecognitionResult(None, False, best, second, margin, "margin")
    return RecognitionResult(label, True, best, second, margin, "accepted")


def _rgb_distance(
    a: Sequence[float],
    b: Sequence[float],
) -> float:
    if len(a) != 3 or len(b) != 3:
        raise ValueError("RGB features must have three channels")
    return sqrt(sum((float(x) - float(y)) ** 2 for x, y in zip(a, b)))


def classify_suit_rgb(
    observed_rgb: Sequence[float],
    *,
    prototypes: Mapping[str, Sequence[float]] = SUIT_RGB_PROTOTYPES,
    max_distance: float = SUIT_PROBE_MAX_DISTANCE,
    min_margin: float = SUIT_PROBE_MIN_MARGIN,
) -> RecognitionResult:
    """Classify KKPoker's four-colored suit glyph, failing closed on ambiguity."""

    if not prototypes:
        return RecognitionResult(None, False, float("inf"), float("inf"), 0.0, "no_prototypes")
    distances = sorted(
        ((suit, _rgb_distance(observed_rgb, rgb)) for suit, rgb in prototypes.items()),
        key=lambda item: (item[1], item[0]),
    )
    suit, best = distances[0]
    second = distances[1][1] if len(distances) > 1 else float("inf")
    margin = second - best
    if best > max_distance:
        return RecognitionResult(None, False, best, second, margin, "distance")
    if margin < min_margin:
        return RecognitionResult(None, False, best, second, margin, "margin")
    return RecognitionResult(suit, True, best, second, margin, "accepted")
