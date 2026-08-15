import json
import re
from pathlib import Path

from deepofc.tablemap_verify import parse_tablemap, validate_hu_replay_tablemap
from tests.test_tablemap import _source_tm
from tools.build_joker_hu_tablemap import build


ROOT = Path(__file__).resolve().parents[1]
GEOMETRY = ROOT / "tablemaps" / "joker_ultimate_hu_450x830_geometry_v1.json"
CALIBRATION = ROOT / "tablemaps" / "joker_ultimate_hu_450x830_calibration_v1.json"
FANTASY15_GEOMETRY = ROOT / "tablemaps" / "joker_ultimate_hu_fantasy15_450x830_geometry_v1.json"


def _inputs():
    return (
        json.loads(GEOMETRY.read_text(encoding="utf-8")),
        json.loads(CALIBRATION.read_text(encoding="utf-8")),
        json.loads(FANTASY15_GEOMETRY.read_text(encoding="utf-8")),
    )


def _region_record(text: str, name: str) -> tuple[tuple[int, int, int, int], str]:
    prefix = f"r${name}"
    line = next(
        (raw for raw in text.splitlines() if raw.startswith(prefix) and raw[len(prefix):len(prefix)+1].isspace()),
        None,
    )
    if line is None:
        raise AssertionError(f"missing generated region {name}")
    # Builder format: name left top right bottom color radius transform ...
    match = re.match(
        r"^r\$\S+\s+(-?\d+)\s+(-?\d+)\s+(-?\d+)\s+(-?\d+)\s+\S+\s+-?\d+\s+(\S+)",
        line,
    )
    if not match:
        raise AssertionError(f"cannot parse generated region line: {line}")
    return tuple(int(match.group(i)) for i in range(1, 5)), match.group(5)


def test_repository_geometry_and_calibration_build_the_current_contract():
    geometry, calibration, _ = _inputs()

    result = build(_source_tm(), geometry, calibration)
    assert validate_hu_replay_tablemap(result) == []
    audit = parse_tablemap(result)

    assert audit.target_size == (450, 830)
    assert "ofc_fantasy_active" in audit.regions
    assert audit.symbols["ofc_fantasy_recognizer_calibrated"] == "0"
    assert audit.symbols["ofc_fantasy15_geometry_measured"] == "0"
    assert "ofc_fantasy15_src00" not in audit.regions
    assert "ofc_p0_top0joker1" in audit.regions
    assert "ofc_p0_top0joker2" in audit.regions
    assert "ofc_p0_top0joker" not in audit.regions


def test_repository_fantasy15_geometry_can_be_embedded_without_enabling_recognition_or_clicks():
    geometry, calibration, fantasy15 = _inputs()

    result = build(_source_tm(), geometry, calibration, fantasy15)
    assert validate_hu_replay_tablemap(result) == []
    audit = parse_tablemap(result)

    # Geometry presence is a distinct fact from recognition/action authority.
    assert audit.symbols["ofc_fantasy15_geometry_measured"] == "1"
    assert audit.symbols["ofc_fantasy_recognizer_calibrated"] == "0"
    assert audit.symbols["ofc_joker_detector_calibrated"] == "0"
    assert audit.symbols["ofc_drag_targets_calibrated"] == "0"
    assert audit.symbols["ofc_executor_enabled"] == "0"

    expected = {
        *(f"ofc_fantasy15_src{i:02d}" for i in range(15)),
        *(f"ofc_fantasy15_arrange_top{i}" for i in range(3)),
        *(f"ofc_fantasy15_arrange_middle{i}" for i in range(5)),
        *(f"ofc_fantasy15_arrange_bottom{i}" for i in range(5)),
        "ofc_fantasy15_unused_span",
    }
    assert expected <= set(audit.regions)

    # These are deliberately geometry-only N regions. No T/C/H transform may
    # accidentally turn measured rectangles into a card classifier.
    first_rect, first_transform = _region_record(result, "ofc_fantasy15_src00")
    last_rect, last_transform = _region_record(result, "ofc_fantasy15_src14")
    assert first_rect == tuple(fantasy15["fan_slots_left_to_right"][0]["identity_patch"])
    assert last_rect == tuple(fantasy15["fan_slots_left_to_right"][14]["identity_patch"])
    assert first_transform == "N"
    assert last_transform == "N"

    top0, top0_transform = _region_record(result, "ofc_fantasy15_arrange_top0")
    bottom4, bottom4_transform = _region_record(result, "ofc_fantasy15_arrange_bottom4")
    unused, unused_transform = _region_record(result, "ofc_fantasy15_unused_span")
    measured = fantasy15["arrangement_state_frame53"]
    assert top0 == tuple(measured["hero_rows_measured_bright_card_bounds"]["top"][0])
    assert bottom4 == tuple(measured["hero_rows_measured_bright_card_bounds"]["bottom"][4])
    assert unused == tuple(measured["unused_loose_combined_bright_span"])
    assert {top0_transform, bottom4_transform, unused_transform} == {"N"}


def test_repository_fantasy_detector_is_the_replay_measured_arc_pixel():
    _, calibration, _ = _inputs()
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
    _, calibration, _ = _inputs()
    joker = calibration["joker_detector"]
    assert joker["persistent_identity_evidence"] is True
    assert joker["placeholder1_rgb"].lower() == "ff00ff"
    assert joker["placeholder2_rgb"].lower() == "00ffff"
    assert joker["joker1_visual_identity"].startswith("orange/red")
    assert joker["joker2_visual_identity"].startswith("gray/black")
