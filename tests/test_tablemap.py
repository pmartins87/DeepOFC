from tools.build_joker_hu_tablemap import build
from deepofc.tablemap_verify import parse_tablemap, validate_hu_replay_tablemap


def _source_tm() -> str:
    return """.osdb2

// sizes
z$clientsizemax    2000  2000
z$clientsizemin    100  100
z$targetsize       500  700

// strings
s$nchairs                   4
s$titletext                 OFC
s$t1type                    fuzzy
s$t5type                    fuzzy

// regions
r$legacy                    0 0 0 0 ff000000 0 N 1 0 0 0 -1

// fonts
// enough for builder unit test
"""


def _geometry() -> dict:
    # Tiny synthetic geometry with real slot cardinalities; exact coordinates do
    # not matter to the contract test.
    def row(count, y, w=20, h=30):
        return [[10 + i * 22, y, 10 + i * 22 + w, y + h] for i in range(count)]

    return {
        "client_size": {"width": 450, "height": 830},
        "opponent": {
            "top": row(3, 10),
            "middle": row(5, 50),
            "bottom": row(5, 90),
        },
        "hero": {
            "top": row(3, 200, 30, 40),
            "middle": row(5, 250, 30, 40),
            "bottom": row(5, 300, 30, 40),
            "normal_incoming": row(3, 360, 30, 40),
        },
    }


def _calibration() -> dict:
    empty = {
        "opponent_top": {"rgb": "22704c", "radius": 24},
        "opponent_middle": {"rgb": "257650", "radius": 24},
        "opponent_bottom": {"rgb": "297b55", "radius": 24},
        "hero_top": {"rgb": "2a7852", "radius": 24},
        "hero_middle": {"rgb": "1f6d49", "radius": 24},
        "hero_bottom": {"rgb": "1b6242", "radius": 24},
        "hero_incoming": {"rgb": "196e49", "radius": 24},
    }
    for prefix in ("opponent_discard", "hero_discard"):
        for i in range(4):
            empty[f"{prefix}{i}"] = {"rgb": "145938", "radius": 22}
    return {
        "empty_background": empty,
        "card_back": {"rgb": "d4ae4e", "radius": 46},
        "turn": {
            "p0": {"point": [10, 10], "rgb": "eaec09", "radius": 28},
            "p1": {"point": [20, 20], "rgb": "eaec09", "radius": 28},
        },
        "dealer": {
            "p0": {"point": [30, 30], "rgb": "cfcfcf", "radius": 20},
            "p1": {"point": [40, 40], "rgb": "cfcfcf", "radius": 20},
        },
        "confirm_visible": {"point": [50, 50], "rgb": "9f8945", "radius": 28},
        "hero_discard_rects": row4(400),
        "opponent_discard_rects": row4(450),
        "joker_detector": {"calibrated": False, "placeholder_rgb": "ff00ff"},
    }


def row4(y: int):
    return [[10 + i * 22, y, 30 + i * 22, y + 30] for i in range(4)]


def test_builder_output_passes_hu_replay_contract_verifier():
    result = build(_source_tm(), _geometry(), _calibration())
    assert validate_hu_replay_tablemap(result) == []
    assert "s$ofc_variant" in result
    assert "joker_ultimate" in result
    assert "r$ofc_p0_top0empty" in result
    assert "r$ofc_p1_bottom4rank" in result
    assert "r$ofc_hero_in2suit" in result
    assert "r$ofc_hero_in0drag" in result
    assert "r$ofc_hero_in1drag" in result
    assert "r$ofc_hero_in2drag" in result


def test_every_card_slot_uses_two_persistent_joker_identity_regions():
    result = build(_source_tm(), _geometry(), _calibration())
    audit = parse_tablemap(result)
    for base in (
        "ofc_p0_top0",
        "ofc_p1_bottom4",
        "ofc_p0_discard0",
        "ofc_hero_discard3",
        "ofc_hero_in2",
    ):
        assert base + "joker1" in audit.regions
        assert base + "joker2" in audit.regions
        assert base + "joker" not in audit.regions


def test_verifier_rejects_legacy_single_joker_contract_even_if_other_regions_exist():
    result = build(_source_tm(), _geometry(), _calibration())
    legacy = result.replace("r$ofc_p0_top0joker1", "r$ofc_p0_top0joker")
    errors = validate_hu_replay_tablemap(legacy)
    assert any("missing regions" in error and "joker1" in error for error in errors)
    assert any("legacy single-Joker" in error for error in errors)


def test_normal_incoming_drag_regions_preserve_visual_geometry_but_not_action_authority():
    result = build(_source_tm(), _geometry(), _calibration())
    audit = parse_tablemap(result)
    assert {"ofc_hero_in0drag", "ofc_hero_in1drag", "ofc_hero_in2drag"} <= set(audit.regions)
    # Source geometry can be known while destination/action calibration remains
    # deliberately disabled. This separation prevents scraper progress from
    # accidentally enabling the autoplayer.
    assert audit.symbols["ofc_drag_targets_calibrated"] == "0"


def test_replay_draft_is_explicitly_non_actionable_even_if_future_drop_regions_exist():
    result = build(_source_tm(), _geometry(), _calibration())
    audit = parse_tablemap(result)
    assert audit.symbols["ofc_drag_targets_calibrated"] == "0"

    # A guessed/future rectangle must never silently flip replay evidence into
    # an actionable runtime map. Calibration is a separate deliberate gate.
    result_with_drop_rects = result.replace(
        "// fonts",
        "r$ofc_drop_top 100 200 140 240 ff000000 0 N 1 0 0 0 -1\n"
        "r$ofc_drop_middle 100 300 140 340 ff000000 0 N 1 0 0 0 -1\n"
        "r$ofc_drop_bottom 100 400 140 440 ff000000 0 N 1 0 0 0 -1\n"
        "// fonts",
    )
    audit = parse_tablemap(result_with_drop_rects)
    assert audit.symbols["ofc_drag_targets_calibrated"] == "0"
    assert {"ofc_drop_top", "ofc_drop_middle", "ofc_drop_bottom"} <= set(audit.regions)


def test_verifier_rejects_unmodified_holdem_style_tablemap():
    errors = validate_hu_replay_tablemap(_source_tm())
    assert errors
    assert any("target_size" in error for error in errors)
    assert any("missing regions" in error for error in errors)
    assert any("ofc_drag_targets_calibrated" in error for error in errors)
