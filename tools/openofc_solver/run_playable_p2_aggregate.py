from __future__ import annotations

import argparse
import json
from pathlib import Path

from playable_p2_candidate import write_manifest


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--route", type=Path, action="append", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    payload = write_manifest(args.output, args.route)
    print(json.dumps(payload, sort_keys=True))


if __name__ == "__main__":
    main()
