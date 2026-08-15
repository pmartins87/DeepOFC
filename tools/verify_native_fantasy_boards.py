from __future__ import annotations

from pathlib import Path
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from deepofc.scoring import pairwise_points_standard
from deepofc.state import Card, PlayerBoard


def C(code: str) -> Card:
    return Card.from_code(code)


def cards(text: str):
    return tuple(C(code) for code in text.split()) if text.strip() else ()


def parse_cases(path: Path):
    cases = {}
    current = None
    for raw in path.read_text(encoding="utf-8").splitlines():
        if not raw:
            continue
        if raw.startswith("CASE\t"):
            name = raw.split("\t", 1)[1]
            current = {"name": name}
            cases[name] = current
        elif raw == "END":
            current = None
        else:
            if current is None:
                raise ValueError(f"field outside CASE: {raw}")
            key, value = raw.split("\t", 1)
            current[key] = value
    return cases


def main() -> None:
    binary = ROOT / "native" / "fantasy_exact"
    case_path = ROOT / "native" / "fantasy_exact_cases.txt"
    completed = subprocess.run(
        [str(binary), str(case_path)],
        check=True,
        text=True,
        capture_output=True,
    )
    print(completed.stdout, end="")

    source_cases = parse_cases(case_path)
    current_name = None
    parsed = {}
    for line in completed.stdout.splitlines():
        if line.startswith("CASE="):
            match = re.match(r"CASE=(\S+) value=(-?\d+) expected=(-?\d+) seconds=([0-9.]+)", line)
            if not match:
                raise AssertionError(f"unparseable native CASE line: {line}")
            current_name = match.group(1)
            parsed[current_name] = {
                "value": int(match.group(2)),
                "expected": int(match.group(3)),
            }
        elif current_name and line.startswith(" top="):
            parsed[current_name]["top"] = line.split("=", 1)[1]
        elif current_name and line.startswith(" middle="):
            parsed[current_name]["middle"] = line.split("=", 1)[1]
        elif current_name and line.startswith(" bottom="):
            parsed[current_name]["bottom"] = line.split("=", 1)[1]

    if set(parsed) != set(source_cases):
        raise AssertionError("native output case set differs from frozen case file")

    for name, output in parsed.items():
        src = source_cases[name]
        hero = PlayerBoard(
            top=cards(output["top"]),
            middle=cards(output["middle"]),
            bottom=cards(output["bottom"]),
        )
        opponent = PlayerBoard(
            top=cards(src["OPP_TOP"]),
            middle=cards(src["OPP_MIDDLE"]),
            bottom=cards(src["OPP_BOTTOM"]),
        )
        py_score = pairwise_points_standard(hero, opponent)
        if py_score.hero_foul:
            raise AssertionError(f"native selected fouled board in {name}")
        if py_score.total_points != output["value"]:
            raise AssertionError(
                f"native/Python score mismatch in {name}: "
                f"native={output['value']} python={py_score.total_points}"
            )
        if output["value"] != output["expected"]:
            raise AssertionError(f"native expected-value mismatch in {name}")
        print(f"PYTHON RESCORE {name}: {py_score.total_points} PASS")

    print("NATIVE -> PYTHON BOARD RESCORE: PASS")


if __name__ == "__main__":
    main()
