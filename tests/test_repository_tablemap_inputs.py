import json
from pathlib import Path

from deepofc.tablemap_verify import parse_tablemap, validate_hu_replay_tablemap
from tests.test_tablemap import _source_tm
from tools.build_joker_hu_tablemap import build


ROOT = Path(__file__).resolve().parents[1]
GEOMETRY = ROOT / "tablemaps" / "joker_ultimate_hu_450x830_geometry_v1.json"
CALIBRATION = ROOT / "tablemaps" / "joker_ultimate_hu_450x830_calibration_v1.json"


def test_repository_geometry_and_calibration_build_the_current_contract():
    geometry = json.loads(GEOMETRY.read_text(encoding="utf-8"))
    calibration = json.loads(CALIBRATION.read_text(encoding="utf-8"))

    result = build(_source_tm(), geometry, calibration)
    assert validate_hu_replay_tablemap(result) == []
    audit = parse_tablemap(result)

    assert audit.target_size == (450, 830)
    assert "ofc_fantasy_active" in audit.regions
    assert "ofc_p0_top0joker1" in audit.regions
    assert "ofc_p0_top0joker2" in audit.regions
    assert "ofc_p0_top0joker" not in audit.regions


def test_repository_fantasy_detector_is_the_replay_measured_arc_pixel():
    calibration = json.loads(CALIBRATION.read_text(encoding="utf-8"))
    fantasy = calibration["fantasy_active"]
    assert fantasy["point"] == [225, 760]
    assert fantasy["rgb"].lower() == "874c00"
    assert 52 in fantasy["true_frames"]
    assert 53 in fantasy["true_frames"]
    assert 55 in fantasy["true_frames"]
    assert 60 in fantasy["true_frames"]
    assert 29 in fantasy["false_frames"]
    assert 54 in fantasy["false_frames"]


def test_repository_joker_placeholders_match_persistent_identity_schema():
    calibration = json.loads(CALIBRATION.read_text(encoding="utf-8"))
    joker = calibration["joker_detector"]
    assert joker["persistent_identity_evidence"] is True
    assert joker["placeholder1_rgb"].lower() == "ff00ff"
    assert joker["placeholder2_rgb"].lower() == "00ffff"
    assert joker["joker1_visual_identity"].startswith("orange/red")
    assert joker["joker2_visual_identity"].startswith("gray/black")
