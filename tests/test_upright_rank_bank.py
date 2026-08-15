import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BANK = ROOT / "tablemaps" / "joker_ultimate_hu_upright_rank_bank_v1.json"
FANTASY_GEOMETRY = ROOT / "tablemaps" / "joker_ultimate_hu_fantasy15_450x830_geometry_v1.json"


def test_upright_bank_has_two_complete_rank_alphabets_and_no_runtime_authority():
    bank = json.loads(BANK.read_text(encoding="utf-8"))
    assert bank["target_variant"] == "KKPoker OFC Joker Ultimate"
    assert bank["runtime_authorized"] is False
    assert "not_runtime_authority" in bank["status"]
    assert bank["normalized_mask"] == {"width": 16, "height": 24}
    assert bank["alignment_pixels"] == 2

    for size in ("large", "small"):
        entries = bank[size]
        assert [entry["rank"] for entry in entries] == list("23456789TJQKA")
        assert len({entry["rank"] for entry in entries}) == 13
        for entry in entries:
            assert len(entry["rank_mask_rows"]) == 24
            assert all(0 <= row < (1 << 16) for row in entry["rank_mask_rows"])
            assert len(entry["source_frame_sha256"]) == 64
            assert len(entry["source_rect"]) == 4


def test_frame53_geometry_freezes_individual_unused_cards_and_control_probes_without_authority():
    geometry = json.loads(FANTASY_GEOMETRY.read_text(encoding="utf-8"))
    arrangement = geometry["arrangement_state_frame53"]
    assert arrangement["unused_loose_card_bounds_left_to_right"] == [
        [183, 646, 231, 715],
        [213, 646, 266, 715],
    ]
    assert arrangement["unused_cards_left_to_right"] == ["3s", "2c"]
    controls = arrangement["control_probe_points"]
    assert controls["fantasy_active"]["point"] == [225, 760]
    assert controls["opponent_turn"]["expected"] is False
    assert controls["hero_turn"]["expected"] is True
    assert controls["opponent_dealer"]["expected"] is True
    assert controls["confirm_visible"]["expected"] is True
    assert "single-frame" in arrangement["control_probe_warning"]
