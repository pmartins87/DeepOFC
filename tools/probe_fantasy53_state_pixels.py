from __future__ import annotations

"""Replay-only frame53 pixels -> RawOFCObservation -> canonical-state gate.

This tool closes the semantic plumbing for the supplied 15-card Fantasy
arrangement frame without granting live runtime authority. Card identity comes
from pixels and frozen replay-derived template banks; the golden fixture is used
only as the expected answer.

Current runtime authority remains OFF:

    ofc_fantasy_recognizer_calibrated = 0
    ofc_drag_targets_calibrated = 0
    ofc_executor_enabled = 0
"""

import argparse
import hashlib
import json
import math
from pathlib import Path
from statistics import median
from typing import Iterable, Sequence

from PIL import Image

from deepofc.observation import RawOFCObservation, RawPlayerObservation
from deepofc.reconstruct import reconstruct_observation
from deepofc.serde import state_from_dict
from deepofc.state import Card, PlayerBoard, Row


SUIT_PROTOTYPES = {
    "c": (30.0, 148.0, 1.0),
    "d": (20.0, 97.25, 192.0),
    "h": (227.0, 11.0, 24.5),
    "s": (48.0, 48.0, 48.0),
}


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _components(mask: list[list[bool]]) -> list[list[tuple[int, int]]]:
    height = len(mask)
    width = len(mask[0])
    seen: set[tuple[int, int]] = set()
    result: list[list[tuple[int, int]]] = []
    for y in range(height):
        for x in range(width):
            if not mask[y][x] or (x, y) in seen:
                continue
            stack = [(x, y)]
            seen.add((x, y))
            points: list[tuple[int, int]] = []
            while stack:
                px, py = stack.pop()
                points.append((px, py))
                for dy in (-1, 0, 1):
                    for dx in (-1, 0, 1):
                        if dx == 0 and dy == 0:
                            continue
                        q = (px + dx, py + dy)
                        if (
                            0 <= q[0] < width
                            and 0 <= q[1] < height
                            and mask[q[1]][q[0]]
                            and q not in seen
                        ):
                            seen.add(q)
                            stack.append(q)
            result.append(points)
    return result


def _normalize_component(
    points: Sequence[tuple[int, int]],
    *,
    width: int = 16,
    height: int = 24,
    padding: int = 1,
) -> tuple[int, ...]:
    x1 = min(x for x, _ in points)
    x2 = max(x for x, _ in points) + 1
    y1 = min(y for _, y in points)
    y2 = max(y for _, y in points) + 1
    source_width = x2 - x1
    source_height = y2 - y1
    scale = min(
        (width - 2 * padding) / source_width,
        (height - 2 * padding) / source_height,
    )
    normalized_width = max(1, round(source_width * scale))
    normalized_height = max(1, round(source_height * scale))

    source = [[False] * source_width for _ in range(source_height)]
    for x, y in points:
        source[y - y1][x - x1] = True

    resized = [[False] * normalized_width for _ in range(normalized_height)]
    for y in range(normalized_height):
        sy = min(source_height - 1, int(y * source_height / normalized_height))
        for x in range(normalized_width):
            sx = min(source_width - 1, int(x * source_width / normalized_width))
            resized[y][x] = source[sy][sx]

    canvas = [[False] * width for _ in range(height)]
    offset_x = (width - normalized_width) // 2
    offset_y = (height - normalized_height) // 2
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
    return tuple(rows)


def _extract_rank_feature(
    image: Image.Image,
    rect: Sequence[int],
    *,
    size: str,
) -> tuple[tuple[int, ...], tuple[float, float, float], dict]:
    left, top, right, bottom = map(int, rect)
    if size == "large":
        patch_width, patch_height = 27, 47
        threshold = 140
        center_x = 8.0
        max_cy = 0.82 * 24
        cy_penalty_start = 13.2
    elif size == "small":
        patch_width, patch_height = 20, 25
        threshold = 150
        center_x = 7.0
        max_cy = 17.0
        cy_penalty_start = 11.0
    else:
        raise ValueError(size)

    roi = image.crop(
        (
            left,
            top,
            min(right + 1, left + patch_width),
            min(bottom + 1, top + patch_height),
        )
    ).convert("RGB")
    pixels = roi.load()
    width, height = roi.size
    mask = [
        [min(pixels[x, y]) < threshold for x in range(width)]
        for y in range(height)
    ]

    candidates = []
    for points in _components(mask):
        area = len(points)
        if area < 5:
            continue
        cx = sum(x for x, _ in points) / area
        cy = sum(y for _, y in points) / area
        if cy >= max_cy:
            continue
        score = area - 2 * abs(cx - center_x) - max(0.0, cy - cy_penalty_start)
        xs = [x for x, _ in points]
        ys = [y for _, y in points]
        rgbs = [pixels[x, y] for x, y in points]
        rgb = tuple(
            float(median([pixel[channel] for pixel in rgbs]))
            for channel in range(3)
        )
        candidates.append(
            (
                score,
                points,
                rgb,
                {
                    "area": area,
                    "width": max(xs) - min(xs) + 1,
                    "height": max(ys) - min(ys) + 1,
                    "cx": cx,
                    "cy": cy,
                },
            )
        )
    if not candidates:
        raise ValueError(f"no rank/Joker glyph component found at {rect}")
    _, points, rgb, geometry = max(candidates, key=lambda item: item[0])
    return _normalize_component(points), rgb, geometry


def _translate_rows(
    rows: Sequence[int],
    *,
    dx: int,
    dy: int,
    width: int = 16,
) -> tuple[int, ...]:
    output = [0] * len(rows)
    mask = (1 << width) - 1
    for source_y, row in enumerate(rows):
        target_y = source_y + dy
        if not 0 <= target_y < len(rows):
            continue
        output[target_y] = ((row << dx) & mask) if dx >= 0 else row >> (-dx)
    return tuple(output)


def _binary_distance(left: Sequence[int], right: Sequence[int]) -> float:
    xor = sum(int(a ^ b).bit_count() for a, b in zip(left, right))
    union = sum(int(a | b).bit_count() for a, b in zip(left, right))
    return 0.0 if union == 0 else xor / union


def _aligned_distance(
    observed: Sequence[int],
    template: Sequence[int],
    *,
    shift: int,
) -> float:
    return min(
        _binary_distance(
            observed,
            _translate_rows(template, dx=dx, dy=dy),
        )
        for dy in range(-shift, shift + 1)
        for dx in range(-shift, shift + 1)
    )


def _classify_rank(
    rows: Sequence[int],
    bank: dict,
    *,
    size: str,
) -> tuple[str | None, float, float]:
    thresholds = {
        # Replay-probe thresholds. They are not live authority.
        "large": (0.36, 0.04),
        "small": (0.38, 0.02),
    }
    max_distance, min_margin = thresholds[size]
    shift = int(bank["alignment_pixels"])
    distances = sorted(
        (
            _aligned_distance(rows, entry["rank_mask_rows"], shift=shift),
            entry["rank"],
        )
        for entry in bank[size]
    )
    best, second = distances[0], distances[1]
    margin = second[0] - best[0]
    accepted = best[0] <= max_distance and margin >= min_margin
    return (best[1] if accepted else None), best[0], margin


def _classify_suit(
    rgb: Sequence[float],
) -> tuple[str | None, float, float]:
    distances = sorted(
        (
            math.sqrt(sum((float(rgb[i]) - prototype[i]) ** 2 for i in range(3))),
            suit,
        )
        for suit, prototype in SUIT_PROTOTYPES.items()
    )
    best, second = distances[0], distances[1]
    margin = second[0] - best[0]
    accepted = best[0] <= 40.0 and margin >= 80.0
    return (best[1] if accepted else None), best[0], margin


def _recognize_card(
    image: Image.Image,
    rect: Sequence[int],
    bank: dict,
    *,
    size: str,
) -> tuple[str, dict]:
    rows, rgb, geometry = _extract_rank_feature(image, rect, size=size)

    # Persistent physical Joker replay probe. Frame52 and frame53 independently
    # show the same orange/red JK1 and gray/black JK2 visual identities. The
    # thresholds remain replay-only until more independent Joker samples exist.
    if (
        size == "large"
        and geometry["area"] < 60
        and geometry["width"] <= 8
        and geometry["height"] <= 10
    ):
        spread = max(rgb) - min(rgb)
        if rgb[0] - max(rgb[1], rgb[2]) > 100:
            return "JK1", {"kind": "joker_probe", "rgb": rgb, "geometry": geometry}
        if spread < 25 and 50 <= sum(rgb) / 3 <= 160:
            return "JK2", {"kind": "joker_probe", "rgb": rgb, "geometry": geometry}
        raise ValueError(f"ambiguous Joker-like glyph at {rect}: rgb={rgb}, geometry={geometry}")

    rank, rank_distance, rank_margin = _classify_rank(rows, bank, size=size)
    suit, suit_distance, suit_margin = _classify_suit(rgb)
    if rank is None or suit is None:
        raise ValueError(
            f"card recognition rejected at {rect}: "
            f"rank={rank} d={rank_distance:.6f} m={rank_margin:.6f}; "
            f"suit={suit} d={suit_distance:.6f} m={suit_margin:.6f}"
        )
    return rank + suit, {
        "kind": "standard",
        "rank_distance": rank_distance,
        "rank_margin": rank_margin,
        "suit_distance": suit_distance,
        "suit_margin": suit_margin,
        "rgb": rgb,
        "geometry": geometry,
    }


def _color_probe(image: Image.Image, config: dict) -> tuple[bool, tuple[int, int, int]]:
    x, y = map(int, config["point"])
    observed = image.getpixel((x, y))
    rgb_text = str(config["rgb"])
    target = tuple(int(rgb_text[i : i + 2], 16) for i in (0, 2, 4))
    radius = int(config["radius"])
    matched = max(abs(observed[i] - target[i]) for i in range(3)) <= radius
    return matched, observed


def _board_from_codes(rows: dict[str, list[str]]) -> PlayerBoard:
    return PlayerBoard(
        top=tuple(Card.from_code(code) for code in rows["top"]),
        middle=tuple(Card.from_code(code) for code in rows["middle"]),
        bottom=tuple(Card.from_code(code) for code in rows["bottom"]),
    )


def _state_signature(state) -> dict:
    return {
        "round": state.round_index,
        "actor": state.acting_chair,
        "dealer": state.dealer_chair,
        "hero": state.hero_chair,
        "boards": {
            player.chair: {
                row.value: frozenset(card.code for card in player.board.row(row))
                for row in Row
            }
            for player in state.players
        },
        "fantasy": {player.chair: player.fantasy for player in state.players},
        "hidden_incoming": {
            player.chair: player.hidden_incoming_count for player in state.players
        },
        "hidden_discards": {
            player.chair: player.hidden_discard_count for player in state.players
        },
        "incoming": frozenset(card.code for card in state.hero_incoming),
        "discards": frozenset(card.code for card in state.hero_discards),
        "pending": frozenset(
            (placement.card.code, placement.row.value)
            for placement in state.hero_pending
        ),
        "prepare": state.hero_can_prepare,
        "confirm": state.hero_can_confirm,
        "required": state.action_required,
        "mode": state.mode,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--frame53", type=Path, required=True)
    parser.add_argument("--base-geometry", type=Path, required=True)
    parser.add_argument("--fantasy15-geometry", type=Path, required=True)
    parser.add_argument("--upright-bank", type=Path, required=True)
    parser.add_argument("--golden", type=Path, required=True)
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()

    base = json.loads(args.base_geometry.read_text(encoding="utf-8"))
    fantasy = json.loads(args.fantasy15_geometry.read_text(encoding="utf-8"))
    bank = json.loads(args.upright_bank.read_text(encoding="utf-8"))
    golden_data = json.loads(args.golden.read_text(encoding="utf-8"))
    golden = state_from_dict(golden_data["state"])

    if bank.get("runtime_authorized") is not False:
        raise SystemExit("upright replay bank unexpectedly claims runtime authority")

    arrangement = fantasy["arrangement_state_frame53"]
    actual_hash = _sha256(args.frame53)
    if actual_hash != arrangement["sha256"]:
        raise SystemExit(
            f"frame53 hash mismatch: expected {arrangement['sha256']}, got {actual_hash}"
        )
    image = Image.open(args.frame53).convert("RGB")
    if image.size != (450, 830):
        raise SystemExit(f"unexpected frame53 size: {image.size}")

    control = arrangement["control_probe_points"]
    control_results = {
        name: _color_probe(image, config)
        for name, config in control.items()
    }
    if not control_results["fantasy_active"][0]:
        raise SystemExit("frame53 Fantasy-active pixel rejected")
    if control_results["opponent_turn"][0]:
        raise SystemExit("frame53 opponent turn probe unexpectedly active")
    if not control_results["hero_turn"][0]:
        raise SystemExit("frame53 Hero turn probe rejected")
    if not control_results["opponent_dealer"][0]:
        raise SystemExit("frame53 opponent dealer probe rejected")
    if not control_results["confirm_visible"][0]:
        raise SystemExit("frame53 Confirm probe rejected")

    opponent_rows: dict[str, list[str]] = {}
    details: dict[str, list[dict]] = {"opponent": [], "hero": [], "unused": []}
    for row in ("top", "middle", "bottom"):
        recognized = []
        for rect in base["opponent"][row]:
            code, detail = _recognize_card(image, rect, bank, size="small")
            recognized.append(code)
            details["opponent"].append({"row": row, "card": code, "detail": detail})
        opponent_rows[row] = recognized

    hero_rows: dict[str, list[str]] = {}
    measured_rows = arrangement["hero_rows_measured_bright_card_bounds"]
    for row in ("top", "middle", "bottom"):
        recognized = []
        for rect in measured_rows[row]:
            code, detail = _recognize_card(image, rect, bank, size="large")
            recognized.append(code)
            details["hero"].append({"row": row, "card": code, "detail": detail})
        hero_rows[row] = recognized

    unused = []
    for rect in arrangement["unused_loose_card_bounds_left_to_right"]:
        code, detail = _recognize_card(image, rect, bank, size="large")
        unused.append(code)
        details["unused"].append({"card": code, "detail": detail})

    # Pixel recognition must agree with the independent golden board/incoming
    # state before we even invoke reconstruction.
    golden_opponent = golden.player(0).board
    expected_opponent = {
        row.value: [card.code for card in golden_opponent.row(row)]
        for row in Row
    }
    if opponent_rows != expected_opponent:
        raise SystemExit(
            f"opponent pixel cards disagree with golden: {opponent_rows} != {expected_opponent}"
        )

    expected_pending = {row.value: [] for row in Row}
    for placement in golden.hero_pending:
        expected_pending[placement.row.value].append(placement.card.code)
    for row in expected_pending:
        expected_pending[row].sort()
        hero_rows[row].sort()
    if hero_rows != expected_pending:
        raise SystemExit(
            f"Hero tentative pixel rows disagree with golden: {hero_rows} != {expected_pending}"
        )

    expected_unused = sorted(card.code for card in golden.unassigned_incoming())
    if sorted(unused) != expected_unused:
        raise SystemExit(
            f"unused Fantasy pixel cards disagree with golden: {unused} != {expected_unused}"
        )

    raw = RawOFCObservation(
        players=(
            RawPlayerObservation(
                chair=0,
                visual_board=_board_from_codes(opponent_rows),
                hidden_incoming_count=0,
                hidden_discard_count=0,
                fantasy=False,
            ),
            RawPlayerObservation(
                chair=1,
                visual_board=_board_from_codes(hero_rows),
                hidden_incoming_count=0,
                hidden_discard_count=0,
                fantasy=True,
            ),
        ),
        hero_chair=1,
        dealer_chair=0,
        acting_chair=1,
        round_index=-1,
        hero_loose_cards=tuple(Card.from_code(code) for code in unused),
        hero_discard_tracker=(),
        hero_can_prepare=True,
        confirm_visible=True,
        mode="joker_ultimate",
    )
    rebuilt = reconstruct_observation(raw, previous=None)
    exact_semantic_state = _state_signature(rebuilt) == _state_signature(golden)
    if not exact_semantic_state:
        raise SystemExit("frame53 pixels reconstructed a canonical state different from golden")

    report = {
        "schema_version": 1,
        "frame": arrangement["path"],
        "sha256": actual_hash,
        "runtime_authorized": False,
        "control_results": {
            name: {"matched": matched, "observed_rgb": list(rgb)}
            for name, (matched, rgb) in control_results.items()
        },
        "opponent_rows": opponent_rows,
        "hero_tentative_rows": hero_rows,
        "hero_unused": unused,
        "pixel_cards_exact": True,
        "canonical_semantic_state_exact": True,
        "details": details,
        "authority": {
            "ofc_fantasy_recognizer_calibrated": 0,
            "ofc_drag_targets_calibrated": 0,
            "ofc_executor_enabled": 0,
        },
    }
    text = json.dumps(report, indent=2, default=list)
    if args.out:
        args.out.write_text(text, encoding="utf-8")
    print(text)


if __name__ == "__main__":
    main()
