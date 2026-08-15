from __future__ import annotations

"""Replay-only pixel probe for the measured KKPoker Fantasy-15 fan.

This tool deliberately does NOT grant runtime authority. It consumes the
user-supplied replay BMPs, verifies their frozen SHA256 hashes, deskews the 15
measured fan patches, recognizes physical cards, and compares them with the
frozen evidence sequences.

Current authority remains `ofc_fantasy_recognizer_calibrated=0` because the
three frames used here are also calibration evidence, rank 8 has only one
observed exemplar, JK1/JK2 each have one fan exemplar, and 14/16/17 layouts are
still unobserved.
"""

import argparse
import hashlib
import json
import math
from pathlib import Path
from statistics import median

from PIL import Image


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def connected_components(mask: list[list[bool]]) -> list[list[tuple[int, int]]]:
    height = len(mask)
    width = len(mask[0])
    seen = [[False] * width for _ in range(height)]
    components: list[list[tuple[int, int]]] = []
    for y in range(height):
        for x in range(width):
            if not mask[y][x] or seen[y][x]:
                continue
            stack = [(x, y)]
            seen[y][x] = True
            points: list[tuple[int, int]] = []
            while stack:
                px, py = stack.pop()
                points.append((px, py))
                for dy in (-1, 0, 1):
                    for dx in (-1, 0, 1):
                        if dx == 0 and dy == 0:
                            continue
                        nx, ny = px + dx, py + dy
                        if (
                            0 <= nx < width
                            and 0 <= ny < height
                            and mask[ny][nx]
                            and not seen[ny][nx]
                        ):
                            seen[ny][nx] = True
                            stack.append((nx, ny))
            components.append(points)
    return components


def select_rank_component(rotated: Image.Image, config: dict):
    width, _ = rotated.size
    roi_config = config["rank_roi"]
    roi_width = int(roi_config["width"])
    roi_height = int(roi_config["height"])
    left = (
        width // 2
        + int(roi_config["center_x_offset"])
        - roi_width // 2
    )
    top = int(roi_config["y0"])
    roi = rotated.crop((left, top, left + roi_width, top + roi_height)).convert("RGB")
    pixels = roi.load()

    threshold_description = str(config.get("foreground_threshold", ""))
    if "140" not in threshold_description:
        raise ValueError("template bank no longer matches the frozen <140 foreground probe")
    mask = [
        [min(pixels[x, y]) < 140 for x in range(roi_width)]
        for y in range(roi_height)
    ]

    candidates = []
    for points in connected_components(mask):
        area = len(points)
        if area < 5:
            continue
        cx = sum(x for x, _ in points) / area
        cy = sum(y for _, y in points) / area
        if cy >= 0.82 * roi_height:
            continue
        score = area - 2 * abs(cx - roi_width / 2) - max(0, cy - 13.2)
        xs = [x for x, _ in points]
        ys = [y for _, y in points]
        candidates.append(
            (
                score,
                points,
                min(xs),
                min(ys),
                max(xs) + 1,
                max(ys) + 1,
                area,
                cx,
                cy,
            )
        )
    if not candidates:
        raise ValueError("no rank/Joker glyph component in measured fan patch")

    _, points, x1, y1, x2, y2, area, cx, cy = max(candidates, key=lambda item: item[0])
    component_width = x2 - x1
    component_height = y2 - y1

    # KKPoker colors the rank glyph by suit. Therefore the selected rank glyph
    # itself yields a very clean suit-color feature and avoids lower-patch table
    # background triangles at the extreme fan angles.
    rgbs = [pixels[x, y] for x, y in points]
    rgb = tuple(float(median([pixel[channel] for pixel in rgbs])) for channel in range(3))

    target_width = 16
    target_height = 24
    padding = 1
    scale = min(
        (target_width - 2 * padding) / component_width,
        (target_height - 2 * padding) / component_height,
    )
    normalized_width = max(1, round(component_width * scale))
    normalized_height = max(1, round(component_height * scale))

    source = [[False] * component_width for _ in range(component_height)]
    for x, y in points:
        source[y - y1][x - x1] = True
    resized = [[False] * normalized_width for _ in range(normalized_height)]
    for y in range(normalized_height):
        source_y = min(component_height - 1, int(y * component_height / normalized_height))
        for x in range(normalized_width):
            source_x = min(component_width - 1, int(x * component_width / normalized_width))
            resized[y][x] = source[source_y][source_x]

    canvas = [[False] * target_width for _ in range(target_height)]
    offset_x = (target_width - normalized_width) // 2
    offset_y = (target_height - normalized_height) // 2
    for y in range(normalized_height):
        for x in range(normalized_width):
            canvas[offset_y + y][offset_x + x] = resized[y][x]

    rows: list[int] = []
    for row in canvas:
        value = 0
        for x, enabled in enumerate(row):
            if enabled:
                value |= 1 << x
        rows.append(value)

    return rows, rgb, {
        "area": area,
        "width": component_width,
        "height": component_height,
        "cx": cx,
        "cy": cy,
    }


def translate_rows(rows: list[int], width: int, dx: int, dy: int) -> list[int]:
    output = [0] * len(rows)
    mask = (1 << width) - 1
    for source_y, row in enumerate(rows):
        target_y = source_y + dy
        if not 0 <= target_y < len(rows):
            continue
        output[target_y] = ((row << dx) & mask) if dx >= 0 else (row >> (-dx))
    return output


def binary_distance(left: list[int], right: list[int], width: int = 16) -> float:
    xor = sum(int(a ^ b).bit_count() for a, b in zip(left, right))
    union = sum(int(a | b).bit_count() for a, b in zip(left, right))
    return 0.0 if union == 0 else xor / union


def aligned_distance(left: list[int], right: list[int], width: int, shift: int) -> float:
    return min(
        binary_distance(left, translate_rows(right, width, dx, dy), width)
        for dy in range(-shift, shift + 1)
        for dx in range(-shift, shift + 1)
    )


def classify_rank(rows: list[int], bank: dict):
    config = bank["extraction"]["rank_match"]
    distances = [
        (
            template["rank"],
            aligned_distance(
                rows,
                template["rank_mask_rows"],
                16,
                int(config["max_translation_pixels"]),
            ),
        )
        for template in bank["rank_templates"]
    ]
    distances.sort(key=lambda item: (item[1], item[0]))
    best, second = distances[0], distances[1]
    margin = second[1] - best[1]
    accepted = (
        best[1] <= float(config["max_distance"])
        and margin >= float(config["min_margin"])
    )
    return (best[0] if accepted else None), best[1], margin


def classify_suit(rgb: tuple[float, float, float], bank: dict):
    prototypes = bank["extraction"]["suit_prototypes"]
    config = bank["extraction"]["suit_match"]
    distances = []
    for suit, prototype in prototypes.items():
        distance = math.sqrt(sum((rgb[i] - prototype[i]) ** 2 for i in range(3)))
        distances.append((suit, distance))
    distances.sort(key=lambda item: (item[1], item[0]))
    best, second = distances[0], distances[1]
    margin = second[1] - best[1]
    accepted = (
        best[1] <= float(config["max_distance"])
        and margin >= float(config["min_margin"])
    )
    return (best[0] if accepted else None), best[1], margin


def classify_patch(image: Image.Image, rect: list[int], angle: float, bank: dict):
    left, top, right, bottom = map(int, rect)
    crop = image.crop((left, top, right + 1, bottom + 1)).convert("RGB")
    rotated = crop.rotate(
        -float(angle),
        resample=Image.Resampling.BICUBIC,
        expand=True,
        fillcolor=(255, 255, 255),
    )
    rows, rgb, geometry = select_rank_component(rotated, bank["extraction"])

    # Replay-backed Joker pre-detector. The observed Joker word strip produces a
    # much smaller selected component than every one of the 43 standard-card
    # glyphs. This is deliberately calibration-only until independent Joker fan
    # occurrences are captured.
    if geometry["area"] < 60 and geometry["width"] <= 8 and geometry["height"] <= 10:
        spread = max(rgb) - min(rgb)
        if rgb[0] - max(rgb[1], rgb[2]) > 100:
            return "JK1", {"kind": "joker_probe", "rgb": rgb, "geometry": geometry}
        if spread < 25 and 50 <= sum(rgb) / 3 <= 160:
            return "JK2", {"kind": "joker_probe", "rgb": rgb, "geometry": geometry}
        return None, {"kind": "joker_ambiguous", "rgb": rgb, "geometry": geometry}

    rank, rank_distance, rank_margin = classify_rank(rows, bank)
    suit, suit_distance, suit_margin = classify_suit(rgb, bank)
    detail = {
        "kind": "standard" if rank is not None and suit is not None else "standard_rejected",
        "rgb": rgb,
        "geometry": geometry,
        "rank_distance": rank_distance,
        "rank_margin": rank_margin,
        "suit_distance": suit_distance,
        "suit_margin": suit_margin,
    }
    return (rank + suit if rank is not None and suit is not None else None), detail


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--frames-dir", type=Path, required=True)
    parser.add_argument("--geometry", type=Path, required=True)
    parser.add_argument("--bank", type=Path, required=True)
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()

    geometry = load_json(args.geometry)
    bank = load_json(args.bank)
    if bank.get("runtime_authorized") is not False:
        raise SystemExit("replay probe bank unexpectedly claims runtime authority")
    slots = geometry["fan_slots_left_to_right"]
    angles = bank["extraction"]["deskew_angles_degrees"]

    report = {
        "schema_version": 1,
        "calibration_only": True,
        "runtime_authorized": False,
        "frames": [],
        "all_exact": True,
    }
    for source in geometry["source_frames"]:
        frame_path = args.frames_dir / Path(source["path"]).name
        actual_hash = sha256(frame_path)
        if actual_hash != source["sha256"]:
            raise SystemExit(
                f"hash mismatch {frame_path}: expected {source['sha256']}, got {actual_hash}"
            )
        image = Image.open(frame_path).convert("RGB")
        recognized = []
        details = []
        for slot, angle in zip(slots, angles):
            card, detail = classify_patch(image, slot["identity_patch"], angle, bank)
            recognized.append(card)
            details.append(detail)
        exact = recognized == source["cards_left_to_right"]
        report["all_exact"] = report["all_exact"] and exact
        report["frames"].append(
            {
                "path": source["path"],
                "sha256": actual_hash,
                "expected": source["cards_left_to_right"],
                "recognized": recognized,
                "exact": exact,
                "details": details,
            }
        )

    text = json.dumps(report, indent=2)
    if args.out:
        args.out.write_text(text, encoding="utf-8")
    print(text)
    if not report["all_exact"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
