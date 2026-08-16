from __future__ import annotations

"""Replay probe for dynamic KKPoker Fantasy loose-card objects.

Unlike the original Fantasy-15 slot probe, reflow/upright modes discover rank
anchors from the current pixels and attach recognition to current rectangles.
The output is therefore directly shaped like the OpenHoldem visual observation
contract: physical card + current source geometry + confidence evidence.

This remains replay evidence.  It never enables the OpenHoldem runtime gate.
"""

import argparse
import copy
import hashlib
import json
from pathlib import Path

from PIL import Image

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
from tools.probe_fantasy15_pixels import classify_patch, connected_components
from tools.probe_fantasy53_state_pixels import _recognize_card


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _is_ink(rgb: tuple[int, int, int]) -> bool:
    r, g, b = rgb
    maximum = max(rgb)
    minimum = min(rgb)
    return (
        (r > g + 35 and r > b + 35 and r > 100)
        or (g > r + 25 and g > b + 20 and g > 80)
        or (b > g + 25 and b > r + 25 and b > 100)
        or (maximum < 120 and maximum - minimum < 45)
    )


def _white_density(image: Image.Image, x: int, y: int, radius: int = 4) -> float:
    left = max(0, x - radius)
    top = max(0, y - radius)
    right = min(image.width, x + radius + 1)
    bottom = min(image.height, y + radius + 1)
    total = max(1, (right - left) * (bottom - top))
    white = 0
    for py in range(top, bottom):
        for px in range(left, right):
            r, g, b = image.getpixel((px, py))
            if min(r, g, b) > 175 and max(r, g, b) - min(r, g, b) < 55:
                white += 1
    return white / total


def locate_rank_anchors(image: Image.Image, roi: list[int]):
    left, top, right, bottom = map(int, roi)
    cropped = image.crop((left, top, right, bottom)).convert("RGB")
    pixels = cropped.load()
    mask = [
        [_is_ink(pixels[x, y]) for x in range(cropped.width)]
        for y in range(cropped.height)
    ]
    components: list[InkComponent] = []
    for points in connected_components(mask):
        xs = [point[0] for point in points]
        ys = [point[1] for point in points]
        bounds = BoundingBox(
            left + min(xs),
            top + min(ys),
            left + max(xs) + 1,
            top + max(ys) + 1,
        )
        components.append(InkComponent(bounds, len(points)))
    upper_components = tuple(
        component
        for component in components
        if _white_density(
            image,
            round(component.bounds.center_x),
            round(component.bounds.center_y),
        ) >= 0.12
    )
    anchors = list(pair_rank_anchors(
        components,
        eligible_upper_components=upper_components,
    ))
    # A narrow rank+suit column can become one 8-connected component.  Recover
    # its upper rank bounds, but only when it fills an otherwise empty x band;
    # the regular-grid gate below still has to validate the complete layout.
    for component in upper_components:
        bounds = component.bounds
        if not (30 <= bounds.height <= 38 and bounds.width <= 20):
            continue
        if any(abs(bounds.center_x - anchor.center_x) < 12 for anchor in anchors):
            continue
        split = min(24, bounds.height - 10)
        anchors.append(
            RankAnchor(
                BoundingBox(bounds.left, bounds.top, bounds.right, bounds.top + split),
                component.area,
                BoundingBox(bounds.left, bounds.top + split, bounds.right, bounds.bottom),
            )
        )
    return tuple(sorted(anchors, key=lambda anchor: anchor.center_x))


def _interpolate(value: float, xs: list[float], ys: list[float]) -> float:
    if value <= xs[0]:
        return ys[0]
    if value >= xs[-1]:
        return ys[-1]
    for index in range(len(xs) - 1):
        if xs[index] <= value <= xs[index + 1]:
            fraction = (value - xs[index]) / (xs[index + 1] - xs[index])
            return ys[index] + fraction * (ys[index + 1] - ys[index])
    raise AssertionError("interpolation interval not found")


def _object(card: str, source: BoundingBox, detail: dict) -> dict:
    return {
        "card": card,
        "source_rect": source.as_list(),
        "drag_anchor": [round(source.center_x, 2), round(source.center_y, 2)],
        "detail": detail,
    }


def recognize_initial15(image: Image.Image, geometry: dict, bank: dict) -> list[dict]:
    objects = []
    angles = bank["deskew"]["angles_degrees"]
    for slot, angle in zip(geometry["fan_slots_left_to_right"], angles):
        rect = list(map(int, slot["identity_patch"]))
        card, detail = classify_patch(image, rect, float(angle), bank)
        if card is None:
            raise ValueError(f"initial fan recognition rejected at {rect}: {detail}")
        source = BoundingBox(rect[0], rect[1], rect[2], rect[3] + 20)
        objects.append(_object(card, source, detail))
    require_unique_physical_cards([item["card"] for item in objects])
    return objects


def recognize_reflow(
    image: Image.Image,
    roi: list[int],
    geometry: dict,
    bank: dict,
    original_fantasy_cards: set[str],
) -> tuple[list[dict], dict]:
    anchors = locate_rank_anchors(image, roi)
    grid = fit_regular_grid(anchors)
    reference_x = [
        (slot["identity_patch"][0] + slot["identity_patch"][2]) / 2.0
        for slot in geometry["fan_slots_left_to_right"]
    ]
    angle_values = bank.get("deskew", {}).get("angles_degrees")
    if angle_values is None:
        angle_values = bank["extraction"]["deskew_angles_degrees"]
    reference_angles = [float(value) for value in angle_values]
    # The dynamic crops use the v1 bicubic medoid bank.  The v2 bank is retained
    # for its calibrated bilinear initial-fan path; mixing their resampling
    # contracts changes the conservative rank/suit margins.
    dynamic_bank = copy.deepcopy(bank)
    dynamic_bank["extraction"]["rank_match"]["min_margin"] = 0.02
    objects = []
    for anchor in anchors:
        patch = recognition_patch(anchor)
        angle = 0.8 * _interpolate(anchor.center_x, reference_x, reference_angles)
        inclusive_rect = [patch.left, patch.top, patch.right - 1, patch.bottom - 1]
        card, detail = classify_patch(
            image,
            inclusive_rect,
            angle,
            dynamic_bank,
            resample=Image.Resampling.BICUBIC,
        )
        if card is None:
            raise ValueError(
                f"reflow recognition rejected at {inclusive_rect}: {detail}"
            )
        objects.append(_object(card, current_source_rect(anchor), detail))
    require_unique_physical_cards([item["card"] for item in objects])
    require_subset_of_physical_cards(
        [item["card"] for item in objects],
        original_fantasy_cards,
    )
    return objects, {
        "detected_count": len(anchors),
        "grid_center": grid.center,
        "grid_pitch": grid.pitch,
        "maximum_grid_residual": grid.maximum_residual,
    }


def recognize_upright(
    image: Image.Image,
    roi: list[int],
    upright_bank: dict,
    original_fantasy_cards: set[str],
) -> tuple[list[dict], dict]:
    anchors = locate_rank_anchors(image, roi)
    grid = fit_regular_grid(anchors)
    objects = []
    for anchor in anchors:
        source = current_source_rect(anchor)
        inclusive_rect = [source.left, source.top, source.right - 1, source.bottom - 1]
        card, detail = _recognize_card(
            image,
            inclusive_rect,
            upright_bank,
            size="large",
        )
        objects.append(_object(card, source, detail))
    require_unique_physical_cards([item["card"] for item in objects])
    require_subset_of_physical_cards(
        [item["card"] for item in objects],
        original_fantasy_cards,
    )
    return objects, {
        "detected_count": len(anchors),
        "grid_center": grid.center,
        "grid_pitch": grid.pitch,
        "maximum_grid_residual": grid.maximum_residual,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--frames-dir", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--geometry", type=Path, required=True)
    parser.add_argument("--fan-bank", type=Path, required=True)
    parser.add_argument("--reflow-bank", type=Path, required=True)
    parser.add_argument("--upright-bank", type=Path, required=True)
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()

    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    geometry = json.loads(args.geometry.read_text(encoding="utf-8"))
    fan_bank = json.loads(args.fan_bank.read_text(encoding="utf-8"))
    reflow_bank = json.loads(args.reflow_bank.read_text(encoding="utf-8"))
    upright_bank = json.loads(args.upright_bank.read_text(encoding="utf-8"))
    if any(
        config.get("runtime_authorized") is not False
        for config in (manifest, fan_bank, reflow_bank, upright_bank)
    ):
        raise SystemExit("dynamic replay input unexpectedly claims runtime authority")

    report = {
        "schema_version": 1,
        "runtime_authorized": False,
        "frames": [],
        "accepted_frames_exact": True,
        "transition_rejections_exact": True,
    }
    roi = manifest["scan_roi"]
    original_fantasy_cards: set[str] = set()
    for fixture in manifest["frames"]:
        frame_path = args.frames_dir / Path(fixture["path"]).name
        actual_hash = sha256(frame_path)
        if actual_hash != fixture["sha256"]:
            raise SystemExit(f"hash mismatch for {frame_path}")
        image = Image.open(frame_path).convert("RGB")
        if image.size != (450, 830):
            raise SystemExit(f"unsupported frame geometry {image.size}: {frame_path}")

        entry = {
            "path": fixture["path"],
            "sha256": actual_hash,
            "mode": fixture["mode"],
        }
        try:
            if fixture["mode"] == "initial15":
                objects = recognize_initial15(image, geometry, fan_bank)
                grid_detail = {"detected_count": len(objects)}
            elif fixture["mode"] == "reflow":
                objects, grid_detail = recognize_reflow(
                    image,
                    roi,
                    geometry,
                    reflow_bank,
                    original_fantasy_cards,
                )
            elif fixture["mode"] == "upright":
                objects, grid_detail = recognize_upright(
                    image,
                    roi,
                    upright_bank,
                    original_fantasy_cards,
                )
            elif fixture["mode"] == "transition":
                # Transition frames are allowed to produce candidates, but the
                # stability/grid contract must reject the whole observation.
                objects, grid_detail = recognize_reflow(
                    image,
                    roi,
                    geometry,
                    reflow_bank,
                    original_fantasy_cards,
                )
            else:
                raise ValueError(f"unknown mode {fixture['mode']}")
        except ValueError as exc:
            entry.update({"accepted": False, "reason": str(exc)})
            if fixture.get("expected_rejection"):
                entry["exact"] = True
            else:
                entry["exact"] = False
                report["accepted_frames_exact"] = False
            report["frames"].append(entry)
            continue

        recognized = [item["card"] for item in objects]
        if fixture["mode"] == "initial15":
            original_fantasy_cards = set(recognized)
        entry.update(
            {
                "accepted": True,
                "recognized": recognized,
                "objects": objects,
                "geometry": grid_detail,
            }
        )
        if fixture.get("expected_rejection"):
            entry["exact"] = False
            report["transition_rejections_exact"] = False
        else:
            entry["expected"] = fixture["expected"]
            entry["exact"] = recognized == fixture["expected"]
            report["accepted_frames_exact"] &= entry["exact"]
        report["frames"].append(entry)

    report["all_exact"] = (
        report["accepted_frames_exact"]
        and report["transition_rejections_exact"]
    )
    text = json.dumps(report, indent=2)
    if args.out:
        args.out.write_text(text, encoding="utf-8")
    print(text)
    if not report["all_exact"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
