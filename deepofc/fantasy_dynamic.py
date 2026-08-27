from __future__ import annotations

"""Geometry kernel for dynamic KKPoker Fantasy loose-card detection.

The module is intentionally pixel-library agnostic.  Replay tools and the
OpenHoldem port may use different image backends, but they must agree on the
important contract: every scrape creates a NEW set of physical-card objects
and current source rectangles.  No visual slot survives a drag/reflow.
"""

from dataclasses import dataclass
from statistics import median
from typing import Iterable, Sequence


@dataclass(frozen=True)
class BoundingBox:
    left: int
    top: int
    right: int
    bottom: int

    def __post_init__(self) -> None:
        if self.right <= self.left or self.bottom <= self.top:
            raise ValueError("bounding box must have positive area")

    @property
    def width(self) -> int:
        return self.right - self.left

    @property
    def height(self) -> int:
        return self.bottom - self.top

    @property
    def center_x(self) -> float:
        return (self.left + self.right) / 2.0

    @property
    def center_y(self) -> float:
        return (self.top + self.bottom) / 2.0

    def as_list(self) -> list[int]:
        return [self.left, self.top, self.right, self.bottom]


@dataclass(frozen=True)
class InkComponent:
    bounds: BoundingBox
    area: int

    def __post_init__(self) -> None:
        if self.area <= 0:
            raise ValueError("component area must be positive")


@dataclass(frozen=True)
class RankAnchor:
    bounds: BoundingBox
    area: int
    suit_bounds: BoundingBox

    @property
    def center_x(self) -> float:
        return self.bounds.center_x

    @property
    def center_y(self) -> float:
        return self.bounds.center_y


@dataclass(frozen=True)
class GridFit:
    centers: tuple[float, ...]
    center: float
    pitch: float
    maximum_residual: float


def pair_rank_anchors(
    components: Iterable[InkComponent],
    *,
    eligible_upper_components: Iterable[InkComponent] | None = None,
    minimum_area: int = 20,
    maximum_area: int = 350,
    minimum_width: int = 3,
    maximum_width: int = 30,
    minimum_height: int = 10,
    maximum_height: int = 36,
    minimum_suit_dy: float = 13.0,
    maximum_suit_dy: float = 42.0,
    maximum_suit_dx: float = 8.0,
    maximum_rank_center_y: float = 696.0,
    nonmaximum_x_distance: float = 12.0,
) -> tuple[RankAnchor, ...]:
    """Select upper rank glyphs that have a plausible lower suit glyph.

    KKPoker colors both rank and suit.  Requiring a second ink component below
    the rank removes table/UI text and most isolated noise without assuming a
    fixed number of cards or fixed source positions.
    """

    items = tuple(components)
    upper_items = (
        items
        if eligible_upper_components is None
        else tuple(eligible_upper_components)
    )
    eligible = [
        component
        for component in upper_items
        if minimum_area <= component.area <= maximum_area
        and minimum_width <= component.bounds.width <= maximum_width
        and minimum_height <= component.bounds.height <= maximum_height
        and component.bounds.center_y <= maximum_rank_center_y
    ]
    candidates: list[RankAnchor] = []
    for upper in eligible:
        lower = [
            component
            for component in items
            if minimum_suit_dy
            <= component.bounds.center_y - upper.bounds.center_y
            <= maximum_suit_dy
            and abs(component.bounds.center_x - upper.bounds.center_x)
            <= maximum_suit_dx
        ]
        if not lower:
            continue
        suit = min(
            lower,
            key=lambda component: (
                component.bounds.center_y - upper.bounds.center_y,
                abs(component.bounds.center_x - upper.bounds.center_x),
                -component.area,
            ),
        )
        candidates.append(
            RankAnchor(upper.bounds, upper.area, suit.bounds)
        )

    # Rank glyphs such as 8 can split into nearby candidates.  Preserve the
    # stronger upper glyph and reject the weaker candidate in the same x band.
    selected: list[RankAnchor] = []
    for candidate in sorted(
        candidates,
        key=lambda anchor: (-anchor.area, anchor.center_y, anchor.center_x),
    ):
        if any(
            abs(candidate.center_x - kept.center_x) < nonmaximum_x_distance
            for kept in selected
        ):
            continue
        selected.append(candidate)
    return tuple(sorted(selected, key=lambda anchor: anchor.center_x))


def fit_regular_grid(
    anchors: Sequence[RankAnchor],
    *,
    minimum_pitch: float = 24.0,
    maximum_pitch: float = 42.0,
    maximum_residual: float = 3.5,
) -> GridFit:
    """Fit and validate the current reflow grid without retaining slot IDs."""

    if len(anchors) < 2:
        raise ValueError("at least two anchors are required for a grid fit")
    centers = tuple(sorted(anchor.center_x for anchor in anchors))
    pitch = median(
        centers[index + 1] - centers[index]
        for index in range(len(centers) - 1)
    )
    if not minimum_pitch <= pitch <= maximum_pitch:
        raise ValueError(f"reflow pitch out of range: {pitch:.3f}")
    center = median(
        value - (index - (len(centers) - 1) / 2.0) * pitch
        for index, value in enumerate(centers)
    )
    expected = tuple(
        center + (index - (len(centers) - 1) / 2.0) * pitch
        for index in range(len(centers))
    )
    residual = max(abs(observed - fitted) for observed, fitted in zip(centers, expected))
    if residual > maximum_residual:
        raise ValueError(f"reflow grid residual too high: {residual:.3f}")
    return GridFit(centers, center, float(pitch), float(residual))


def recognition_patch(anchor: RankAnchor) -> BoundingBox:
    """Build the current exposed identity strip around a detected rank glyph."""

    return BoundingBox(
        left=anchor.bounds.left - 8,
        top=anchor.bounds.top - 2,
        right=anchor.bounds.left - 8 + 34,
        bottom=anchor.bounds.top - 2 + 46,
    )


def current_source_rect(anchor: RankAnchor) -> BoundingBox:
    """Return a conservative current drag source around the visible card head."""

    patch = recognition_patch(anchor)
    return BoundingBox(
        left=patch.left,
        top=patch.top,
        right=patch.right,
        bottom=patch.bottom + 20,
    )


def require_unique_physical_cards(cards: Sequence[str]) -> None:
    if not cards:
        raise ValueError("dynamic Fantasy detector returned no cards")
    if any(not card for card in cards):
        raise ValueError("dynamic Fantasy detector returned an ambiguous card")
    if len(set(cards)) != len(cards):
        raise ValueError("dynamic Fantasy detector returned duplicate physical cards")


def require_subset_of_physical_cards(
    cards: Sequence[str],
    original_fantasy_cards: Iterable[str],
) -> None:
    """Reject a visually plausible card that was never in this Fantasy deal."""

    allowed = frozenset(original_fantasy_cards)
    unexpected = sorted(set(cards) - allowed)
    if unexpected:
        raise ValueError(
            "dynamic Fantasy detector violated physical-card lineage: "
            + ", ".join(unexpected)
        )
