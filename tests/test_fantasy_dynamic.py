import json
from pathlib import Path

import pytest

from deepofc.fantasy_dynamic import (
    BoundingBox,
    InkComponent,
    RankAnchor,
    current_source_rect,
    fit_regular_grid,
    pair_rank_anchors,
    recognition_patch,
    require_subset_of_physical_cards,
    require_unique_physical_cards,
)


def component(left, top, right, bottom, area):
    return InkComponent(BoundingBox(left, top, right, bottom), area)


def anchor(x: int) -> RankAnchor:
    return RankAnchor(
        BoundingBox(x, 650, x + 8, 668),
        70,
        BoundingBox(x, 678, x + 8, 690),
    )


def test_rank_anchor_pairing_uses_current_pixels_not_fixed_slots():
    components = []
    for x in (75, 108, 140, 173):
        components.extend(
            (
                component(x, 650, x + 8, 668, 72),
                component(x + 1, 679, x + 9, 691, 38),
            )
        )
    components.append(component(300, 650, 310, 668, 70))  # no suit -> reject
    anchors = pair_rank_anchors(components)
    assert [item.bounds.left for item in anchors] == [75, 108, 140, 173]


def test_grid_fit_accepts_reflow_and_rejects_animation_geometry():
    fitted = fit_regular_grid(tuple(anchor(x) for x in (76, 108, 141, 173, 206, 238)))
    assert fitted.pitch == pytest.approx(32.0)
    assert fitted.maximum_residual <= 1.0

    with pytest.raises(ValueError, match="residual"):
        fit_regular_grid(tuple(anchor(x) for x in (76, 108, 141, 181, 206, 238)))


def test_current_rect_is_derived_from_current_anchor():
    item = anchor(173)
    assert recognition_patch(item).as_list() == [165, 648, 199, 694]
    assert current_source_rect(item).as_list() == [165, 648, 199, 714]


def test_physical_identity_must_be_complete_and_unique():
    require_unique_physical_cards(("Ah", "JK1", "2s"))
    with pytest.raises(ValueError, match="ambiguous"):
        require_unique_physical_cards(("Ah", "", "2s"))
    with pytest.raises(ValueError, match="duplicate"):
        require_unique_physical_cards(("Ah", "Ah"))


def test_reflow_card_must_belong_to_original_fantasy_deal():
    require_subset_of_physical_cards(("Ah", "3c"), ("Ah", "3c", "2s"))
    with pytest.raises(ValueError, match="lineage.*5c"):
        require_subset_of_physical_cards(("Ah", "5c"), ("Ah", "3c", "2s"))


def test_dynamic_replay_manifest_never_claims_runtime_authority():
    root = Path(__file__).resolve().parents[1]
    manifest = json.loads(
        (
            root
            / "tablemaps"
            / "joker_ultimate_hu_fantasy_dynamic_replay_v1.json"
        ).read_text(encoding="utf-8")
    )
    assert manifest["runtime_authorized"] is False
    assert manifest["client_size"] == {"width": 450, "height": 830}
    assert len(manifest["frames"]) == 12
    rejected = {
        Path(frame["path"]).name: frame["rejection_kind"]
        for frame in manifest["frames"]
        if frame.get("expected_rejection")
    }
    assert rejected == {
        "frame000035.bmp": "transition_geometry",
        "frame000037.bmp": "physical_card_lineage",
        "frame000041.bmp": "rank_margin",
    }
