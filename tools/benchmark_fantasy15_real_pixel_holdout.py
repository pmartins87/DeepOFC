from __future__ import annotations

import argparse
import hashlib
import io
import json
import math
import zipfile
from pathlib import Path

from PIL import Image

STANDARD_MAX_DISTANCE = 2.25
STANDARD_MIN_MARGIN = 0.15
JOKER_MIN_DISTANCE = 3.20


def rank_hog(patch: Image.Image) -> list[float]:
    """Small deterministic HOG descriptor for the exposed fan rank strip."""
    rgb = patch.convert("RGB")
    src = list(rgb.getdata())
    in_w, in_h = rgb.size
    crop_h = min(30, in_h)
    binary = [[0.0] * 32 for _ in range(32)]
    for y in range(32):
        sy = min(int(y * crop_h / 32), crop_h - 1)
        for x in range(32):
            sx = min(int(x * in_w / 32), in_w - 1)
            r, g, b = src[sy * in_w + sx]
            gray = 0.299 * r + 0.587 * g + 0.114 * b
            binary[y][x] = 1.0 if gray < 200.0 else 0.0

    mag = [[0.0] * 32 for _ in range(32)]
    bins = [[0] * 32 for _ in range(32)]
    for y in range(1, 31):
        for x in range(1, 31):
            gx = binary[y][x + 1] - binary[y][x - 1]
            gy = binary[y + 1][x] - binary[y - 1][x]
            mag[y][x] = math.hypot(gx, gy)
            bins[y][x] = int((math.degrees(math.atan2(gy, gx)) % 180.0) / 20.0) % 9

    cells = [[[0.0] * 9 for _ in range(4)] for _ in range(4)]
    for cy in range(4):
        for cx in range(4):
            bucket = cells[cy][cx]
            for y in range(cy * 8, (cy + 1) * 8):
                for x in range(cx * 8, (cx + 1) * 8):
                    bucket[bins[y][x]] += mag[y][x]

    out: list[float] = []
    for cy in range(3):
        for cx in range(3):
            v: list[float] = []
            for yy in (cy, cy + 1):
                for xx in (cx, cx + 1):
                    v.extend(cells[yy][xx])
            norm = math.sqrt(sum(z * z for z in v)) + 1e-9
            out.extend(z / norm for z in v)
    return out


def ink_counts(patch: Image.Image) -> dict[str, int]:
    """KKPoker color signatures: hearts red, clubs green, diamonds blue, spades neutral/dark."""
    counts = {"h": 0, "c": 0, "d": 0, "s": 0}
    for r, g, b in patch.convert("RGB").getdata():
        if r > g + 35 and r > b + 35 and r > 100:
            counts["h"] += 1
        if g > r + 25 and g > b + 20 and g > 80:
            counts["c"] += 1
        if b > g + 25 and b > r + 25 and b > 100:
            counts["d"] += 1
        mx, mn = max(r, g, b), min(r, g, b)
        if mx < 120 and (mx - mn) < 45:
            counts["s"] += 1
    return counts


def squared_distance(a: list[float], b: list[float]) -> float:
    return sum((x - y) ** 2 for x, y in zip(a, b))


def centroid(vectors: list[list[float]]) -> list[float]:
    return [sum(v[i] for v in vectors) / len(vectors) for i in range(len(vectors[0]))]


def frame_number(path: str) -> int:
    return int(Path(path).stem.replace("frame", ""))


def main() -> None:
    ap = argparse.ArgumentParser(
        description="Replay-only Fantasy15 real-pixel holdout recognizer gate."
    )
    ap.add_argument("--zip", type=Path, required=True, help="User-supplied OFC Fantasy replay ZIP")
    ap.add_argument(
        "--geometry",
        type=Path,
        default=Path("tablemaps/joker_ultimate_hu_fantasy15_450x830_geometry_v1.json"),
    )
    ap.add_argument("--report", type=Path)
    args = ap.parse_args()

    geometry = json.loads(args.geometry.read_text(encoding="utf-8"))
    slots = [tuple(x["identity_patch"]) for x in geometry["fan_slots_left_to_right"]]
    source = {frame_number(x["path"]): x for x in geometry["source_frames"]}
    train_frames = (32, 60)
    holdout = 52
    if len(slots) != 15 or any(fr not in source for fr in (*train_frames, holdout)):
        raise SystemExit("Fantasy15 source geometry is incomplete")

    images: dict[int, Image.Image] = {}
    with zipfile.ZipFile(args.zip) as zf:
        for fr in (*train_frames, holdout):
            rec = source[fr]
            data = zf.read(rec["path"])
            got = hashlib.sha256(data).hexdigest()
            if got != rec["sha256"]:
                raise SystemExit(f"SHA256 mismatch for frame {fr}: {got}")
            im = Image.open(io.BytesIO(data)).convert("RGB")
            if im.size != (450, 830):
                raise SystemExit(f"unexpected frame size {fr}: {im.size}")
            images[fr] = im

    # Frames 32 and 60 are calibration only. Frame 52 is never allowed to
    # contribute a standard-card rank template to its own holdout evaluation.
    by_rank: dict[str, list[list[float]]] = {}
    for fr in train_frames:
        for i, card in enumerate(source[fr]["cards_left_to_right"]):
            if card.startswith("JK"):
                raise SystemExit("training frames unexpectedly contain Joker")
            by_rank.setdefault(card[:-1], []).append(rank_hog(images[fr].crop(slots[i])))
    centers = {rank: centroid(vs) for rank, vs in by_rank.items()}
    if set(centers) != set("23456789TJQKA"):
        raise SystemExit("training frames do not cover every rank")

    expected = source[holdout]["cards_left_to_right"]
    predicted: list[str] = []
    details = []
    for i, truth in enumerate(expected):
        patch = images[holdout].crop(slots[i])
        feat = rank_hog(patch)
        ranked = sorted((squared_distance(feat, c), rank) for rank, c in centers.items())
        best, rank = ranked[0]
        margin = ranked[1][0] - best
        counts = ink_counts(patch)
        suit = max(counts, key=counts.get)

        if best >= JOKER_MIN_DISTANCE:
            # The rank recognizer rejects the vertical JOKER face. The persistent
            # physical mapping is then recovered from the evidence-backed color:
            # JK1 orange/red, JK2 gray/black.
            card = "JK1" if counts["h"] > counts["s"] else "JK2"
            mode = "joker_rank_reject_plus_persistent_color"
        elif best <= STANDARD_MAX_DISTANCE and margin >= STANDARD_MIN_MARGIN:
            card = rank + suit
            mode = "standard_hog_rank_plus_color_suit"
        else:
            card = "AMBIGUOUS"
            mode = "fail_closed"

        predicted.append(card)
        details.append(
            {
                "slot": i,
                "expected": truth,
                "predicted": card,
                "mode": mode,
                "rank_best": rank,
                "rank_distance": round(best, 9),
                "rank_margin": round(margin, 9),
                "ink_counts": counts,
            }
        )

    exact = sum(a == b for a, b in zip(expected, predicted))
    standard = sum(
        a == b for a, b in zip(expected, predicted) if not a.startswith("JK")
    )
    jokers = sum(a == b for a, b in zip(expected, predicted) if a.startswith("JK"))
    report = {
        "gate": "fantasy15_real_pixel_holdout_v1",
        "status": "PASS" if exact == 15 else "FAIL",
        "training_frames": list(train_frames),
        "holdout_frame": holdout,
        "training_policy": "rank centroids from frames 32+60 only; frame52 excluded",
        "thresholds": {
            "standard_max_distance": STANDARD_MAX_DISTANCE,
            "standard_min_margin": STANDARD_MIN_MARGIN,
            "joker_min_distance": JOKER_MIN_DISTANCE,
        },
        "standard_cards_exact": f"{standard}/13",
        "persistent_jokers_exact": f"{jokers}/2",
        "full_fan_exact": f"{exact}/15",
        "expected": expected,
        "predicted": predicted,
        "details": details,
        "runtime_authority_change": False,
        "notes": [
            "Replay-only evidence; not live certification.",
            "Only measured 15-card HU hero-chair-1 fan geometry is exercised.",
            "14/16/17 Fantasy, 3-player and post-drag reflow remain separate gates.",
            "No click/action path is exercised or enabled.",
        ],
    }
    text = json.dumps(report, ensure_ascii=False, indent=2)
    print(text)
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(text + "\n", encoding="utf-8")
    if exact != 15:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
