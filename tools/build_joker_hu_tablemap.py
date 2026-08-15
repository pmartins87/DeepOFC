from __future__ import annotations

import argparse
import json
from pathlib import Path


def _region(
    name: str,
    rect: tuple[int, int, int, int],
    *,
    color: str = "ffffff",
    radius: int = -120,
    transform: str = "T1",
) -> str:
    l, t, r, b = rect
    return (
        f"r${name:<30} {l:4d} {t:4d} {r:4d} {b:4d} "
        f"ff{color.lower()} {radius:4d} {transform} 1 0 0 0 -1"
    )


def _point_region(name: str, point: tuple[int, int], *, color: str, radius: int) -> str:
    x, y = point
    return _region(name, (x, y, x, y), color=color, radius=radius, transform="C")


def _geometry_region(name: str, rect: list[int]) -> str:
    # Geometry-only region: R10/read-only probes consume only its rectangle. It
    # is not evaluated as a classifier and therefore carries neutral N semantics.
    return _region(name, tuple(rect), color="000000", radius=0, transform="N")


def _center(rect: list[int]) -> tuple[int, int]:
    l, t, r, b = rect
    return ((l + r) // 2, (t + b) // 2)


def _face_regions(base: str, rect: list[int], *, size: str) -> list[str]:
    l, t, r, b = rect
    if size == "small":
        rank = (l, t, min(r, l + 12), min(b, t + 16))
        suit = (l + 2, t + 18, min(r, l + 11), min(b, t + 27))
        transform = "T5"
    elif size == "large":
        rank = (l, t, min(r, l + 14), min(b, t + 21))
        suit = (l, t + 23, min(r, l + 13), min(b, t + 34))
        transform = "T1"
    else:
        raise ValueError(size)
    return [
        _region(base + "rank", rank, transform=transform),
        _region(base + "suit", suit, transform=transform),
    ]


def _joker_placeholder_rgb(joker_cfg: dict, joker_id: int) -> str:
    specific = joker_cfg.get(f"placeholder{joker_id}_rgb")
    if specific:
        return str(specific)
    if joker_cfg.get("placeholder_rgb"):
        return str(joker_cfg["placeholder_rgb"])
    if joker_cfg.get("legacy_placeholder_rgb"):
        return str(joker_cfg["legacy_placeholder_rgb"])
    raise ValueError(f"joker_detector has no placeholder RGB for JK{joker_id}")


def _slot_regions(
    base: str,
    rect: list[int],
    *,
    size: str,
    empty_cfg: dict,
    back_cfg: dict,
    joker_cfg: dict,
) -> list[str]:
    center = _center(rect)
    out = [
        _point_region(
            base + "empty",
            center,
            color=empty_cfg["rgb"],
            radius=int(empty_cfg["radius"]),
        ),
        _point_region(
            base + "back",
            center,
            color=back_cfg["rgb"],
            radius=int(back_cfg["radius"]),
        ),
        _point_region(
            base + "joker1",
            center,
            color=_joker_placeholder_rgb(joker_cfg, 1),
            radius=0,
        ),
        _point_region(
            base + "joker2",
            center,
            color=_joker_placeholder_rgb(joker_cfg, 2),
            radius=0,
        ),
    ]
    out.extend(_face_regions(base, rect, size=size))
    return out


def _replace_or_add_symbol(lines: list[str], name: str, value: str) -> None:
    prefix = f"s${name}"
    for i, line in enumerate(lines):
        if line.startswith(prefix) and (len(line) == len(prefix) or line[len(prefix)].isspace()):
            lines[i] = f"s${name:<28} {value}"
            return
    insert_at = next((i for i, line in enumerate(lines) if line.strip() == "// regions"), len(lines))
    lines.insert(insert_at, f"s${name:<28} {value}")


def _replace_target_size(lines: list[str], width: int, height: int) -> None:
    for i, line in enumerate(lines):
        if line.startswith("z$targetsize"):
            lines[i] = f"z$targetsize       {width}  {height}"
            return
    raise ValueError("source tablemap has no z$targetsize")


def _fantasy15_geometry_regions(fantasy15_geometry: dict) -> list[str]:
    """Emit measured Fantasy15 rectangles as non-classifying geometry only.

    These regions are intentionally useful before recognition is certified:
    - `ofc_fantasy15_srcXX` locates each exposed fan identity patch;
    - `ofc_fantasy15_arrange_*` records the measured frame53 tentative-board
      card bounds;
    - `ofc_fantasy15_unused_span` records the two-card loose span in frame53.

    None of them flips `ofc_fantasy_recognizer_calibrated`, drag-target
    calibration, or executor authority.
    """

    if fantasy15_geometry.get("variant") != "joker_ultimate":
        raise ValueError("Fantasy15 geometry variant must be joker_ultimate")
    if int(fantasy15_geometry.get("fantasy_card_count", 0)) != 15:
        raise ValueError("Fantasy15 geometry must describe exactly 15 cards")

    slots = fantasy15_geometry.get("fan_slots_left_to_right") or []
    if len(slots) != 15:
        raise ValueError("Fantasy15 geometry requires exactly 15 fan slots")

    out = ["", "// DeepOFC measured Fantasy15 geometry (N-transform; non-authoritative)"]
    for expected_index, slot in enumerate(slots):
        if int(slot.get("index", -1)) != expected_index:
            raise ValueError("Fantasy15 fan slot indices must be contiguous 0..14")
        rect = slot.get("identity_patch")
        if not isinstance(rect, list) or len(rect) != 4:
            raise ValueError("Fantasy15 fan identity patch must be a 4-int rectangle")
        out.append(_geometry_region(f"ofc_fantasy15_src{expected_index:02d}", rect))

    arrangement = fantasy15_geometry.get("arrangement_state_frame53") or {}
    row_bounds = arrangement.get("hero_rows_measured_bright_card_bounds") or {}
    expected_counts = {"top": 3, "middle": 5, "bottom": 5}
    for row, expected_count in expected_counts.items():
        rects = row_bounds.get(row) or []
        if len(rects) != expected_count:
            raise ValueError(f"Fantasy15 frame53 {row} requires {expected_count} measured rectangles")
        for idx, rect in enumerate(rects):
            out.append(
                _geometry_region(
                    f"ofc_fantasy15_arrange_{row}{idx}",
                    rect,
                )
            )

    unused = arrangement.get("unused_loose_combined_bright_span")
    if not isinstance(unused, list) or len(unused) != 4:
        raise ValueError("Fantasy15 frame53 requires measured unused loose span")
    out.append(_geometry_region("ofc_fantasy15_unused_span", unused))
    return out


def build(
    source_text: str,
    geometry: dict,
    calibration: dict,
    fantasy15_geometry: dict | None = None,
) -> str:
    lines = source_text.splitlines()
    width = int(geometry["client_size"]["width"])
    height = int(geometry["client_size"]["height"])
    _replace_target_size(lines, width, height)

    symbols = {
        "nchairs": "2",
        "titletext": "Joker Ultimate",
        "ofc_variant": "joker_ultimate",
        "ofc_players": "2",
        "ofc_hero_chair": "1",
        "ofc_tablemap_stage": "replay_draft_v1",
        "ofc_joker_detector_calibrated": "0",
        "ofc_fantasy_recognizer_calibrated": "0",
        "ofc_fantasy15_geometry_measured": "1" if fantasy15_geometry is not None else "0",
        "ofc_drag_targets_calibrated": "0",
        "ofc_executor_enabled": "0",
    }
    for name, value in symbols.items():
        _replace_or_add_symbol(lines, name, value)

    region_insert = next(
        (i for i, line in enumerate(lines) if line.strip() == "// fonts"),
        None,
    )
    if region_insert is None:
        raise ValueError("source tablemap has no // fonts section")

    g = geometry
    c = calibration
    empty = c["empty_background"]
    back = c["card_back"]
    joker = c["joker_detector"]
    fantasy_active = c.get("fantasy_active")
    if not fantasy_active:
        raise ValueError("calibration has no fantasy_active routing detector")

    new_regions: list[str] = []
    new_regions.append("")
    new_regions.append("// -----------------------------------------------------------------")
    new_regions.append("// DeepOFC Joker Ultimate 450x830 REPLAY-DRAFT regions")
    new_regions.append("// Generated. Do not hand-edit; see tools/build_joker_hu_tablemap.py")
    new_regions.append("// -----------------------------------------------------------------")

    new_regions.append(
        _point_region(
            "ofc_fantasy_active",
            tuple(fantasy_active["point"]),
            color=fantasy_active["rgb"],
            radius=int(fantasy_active["radius"]),
        )
    )

    for row in ("top", "middle", "bottom"):
        for idx, rect in enumerate(g["opponent"][row]):
            new_regions.extend(
                _slot_regions(
                    f"ofc_p0_{row}{idx}",
                    rect,
                    size="small",
                    empty_cfg=empty[f"opponent_{row}"],
                    back_cfg=back,
                    joker_cfg=joker,
                )
            )
        for idx, rect in enumerate(g["hero"][row]):
            new_regions.extend(
                _slot_regions(
                    f"ofc_p1_{row}{idx}",
                    rect,
                    size="large",
                    empty_cfg=empty[f"hero_{row}"],
                    back_cfg=back,
                    joker_cfg=joker,
                )
            )

    for idx, rect in enumerate(c["opponent_discard_rects"]):
        new_regions.extend(
            _slot_regions(
                f"ofc_p0_discard{idx}",
                rect,
                size="small",
                empty_cfg=empty[f"opponent_discard{idx}"],
                back_cfg=back,
                joker_cfg=joker,
            )
        )

    for idx, rect in enumerate(c["hero_discard_rects"]):
        new_regions.extend(
            _slot_regions(
                f"ofc_hero_discard{idx}",
                rect,
                size="small",
                empty_cfg=empty[f"hero_discard{idx}"],
                back_cfg=back,
                joker_cfg=joker,
            )
        )

    for idx, rect in enumerate(g["hero"]["normal_incoming"]):
        base = f"ofc_hero_in{idx}"
        new_regions.extend(
            _slot_regions(
                base,
                rect,
                size="large",
                empty_cfg=empty["hero_incoming"],
                back_cfg=back,
                joker_cfg=joker,
            )
        )
        new_regions.append(_geometry_region(base + "drag", rect))

    if fantasy15_geometry is not None:
        fantasy_size = fantasy15_geometry.get("client_size") or {}
        if int(fantasy_size.get("width", -1)) != width or int(fantasy_size.get("height", -1)) != height:
            raise ValueError("Fantasy15 geometry client size disagrees with base tablemap geometry")
        new_regions.extend(_fantasy15_geometry_regions(fantasy15_geometry))

    for p in (0, 1):
        turn = c["turn"][f"p{p}"]
        dealer = c["dealer"][f"p{p}"]
        new_regions.append(
            _point_region(
                f"ofc_p{p}_turn",
                tuple(turn["point"]),
                color=turn["rgb"],
                radius=int(turn["radius"]),
            )
        )
        new_regions.append(
            _point_region(
                f"ofc_p{p}_dealer",
                tuple(dealer["point"]),
                color=dealer["rgb"],
                radius=int(dealer["radius"]),
            )
        )

    confirm = c["confirm_visible"]
    new_regions.append(
        _point_region(
            "ofc_confirm_visible",
            tuple(confirm["point"]),
            color=confirm["rgb"],
            radius=int(confirm["radius"]),
        )
    )
    new_regions.append("")

    lines[region_insert:region_insert] = new_regions
    return "\n".join(lines) + "\n"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--source-tm", type=Path, required=True)
    ap.add_argument("--geometry", type=Path, required=True)
    ap.add_argument("--calibration", type=Path, required=True)
    ap.add_argument("--fantasy15-geometry", type=Path)
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()

    source = args.source_tm.read_text(encoding="utf-8", errors="replace")
    geometry = json.loads(args.geometry.read_text(encoding="utf-8"))
    calibration = json.loads(args.calibration.read_text(encoding="utf-8"))
    fantasy15_geometry = (
        json.loads(args.fantasy15_geometry.read_text(encoding="utf-8"))
        if args.fantasy15_geometry is not None
        else None
    )
    result = build(source, geometry, calibration, fantasy15_geometry)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(result, encoding="utf-8")
    print(args.out)


if __name__ == "__main__":
    main()
