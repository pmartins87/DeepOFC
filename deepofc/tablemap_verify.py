from __future__ import annotations

from dataclasses import dataclass
import re
from pathlib import Path


@dataclass(frozen=True)
class TablemapAudit:
    symbols: dict[str, str]
    regions: frozenset[str]
    target_size: tuple[int, int]


_SYMBOL_RE = re.compile(r"^s\$([^\s]+)\s+(.*?)\s*$")
_REGION_RE = re.compile(r"^r\$([^\s]+)\s+")
_TARGET_RE = re.compile(r"^z\$targetsize\s+(\d+)\s+(\d+)\s*$")


def parse_tablemap(text: str) -> TablemapAudit:
    symbols: dict[str, str] = {}
    regions: set[str] = set()
    target: tuple[int, int] | None = None
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("//"):
            continue
        sm = _SYMBOL_RE.match(line)
        if sm:
            symbols[sm.group(1)] = sm.group(2).strip()
            continue
        rm = _REGION_RE.match(line)
        if rm:
            regions.add(rm.group(1))
            continue
        tm = _TARGET_RE.match(line)
        if tm:
            target = (int(tm.group(1)), int(tm.group(2)))
    if target is None:
        raise ValueError("tablemap has no z$targetsize")
    return TablemapAudit(symbols=symbols, regions=frozenset(regions), target_size=target)


def required_hu_replay_regions() -> set[str]:
    names: set[str] = set()
    suffixes = ("empty", "back", "joker", "rank", "suit")
    for chair, rows in (
        (0, {"top": 3, "middle": 5, "bottom": 5}),
        (1, {"top": 3, "middle": 5, "bottom": 5}),
    ):
        for row, count in rows.items():
            for i in range(count):
                base = f"ofc_p{chair}_{row}{i}"
                names.update(base + suffix for suffix in suffixes)
    for i in range(4):
        base = f"ofc_p0_discard{i}"
        names.update(base + suffix for suffix in suffixes)
        base = f"ofc_hero_discard{i}"
        names.update(base + suffix for suffix in suffixes)
    for i in range(3):
        base = f"ofc_hero_in{i}"
        names.update(base + suffix for suffix in suffixes)
    names.update(
        {
            "ofc_p0_turn",
            "ofc_p1_turn",
            "ofc_p0_dealer",
            "ofc_p1_dealer",
            "ofc_confirm_visible",
        }
    )
    return names


def validate_hu_replay_tablemap(text: str) -> list[str]:
    audit = parse_tablemap(text)
    errors: list[str] = []
    expected_symbols = {
        "ofc_variant": "joker_ultimate",
        "ofc_players": "2",
        "ofc_hero_chair": "1",
        "ofc_tablemap_stage": "replay_draft_v1",
        "ofc_joker_detector_calibrated": "0",
    }
    if audit.target_size != (450, 830):
        errors.append(f"target_size={audit.target_size}, expected (450, 830)")
    for key, value in expected_symbols.items():
        if audit.symbols.get(key) != value:
            errors.append(f"s${key}={audit.symbols.get(key)!r}, expected {value!r}")
    missing = sorted(required_hu_replay_regions() - set(audit.regions))
    if missing:
        errors.append("missing regions: " + ", ".join(missing))
    return errors


def main() -> None:
    import argparse

    ap = argparse.ArgumentParser()
    ap.add_argument("tablemap", type=Path)
    args = ap.parse_args()
    text = args.tablemap.read_text(encoding="utf-8", errors="replace")
    errors = validate_hu_replay_tablemap(text)
    if errors:
        for error in errors:
            print("ERROR:", error)
        raise SystemExit(1)
    print("PASS: DeepOFC HU replay tablemap contract")


if __name__ == "__main__":
    main()
