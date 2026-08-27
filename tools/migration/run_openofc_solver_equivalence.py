#!/usr/bin/env python3
"""Run deterministic old-vs-new behavioral equivalence for migrated OpenOFC solver.

The frozen myoh_private staging tree and the DeepOFC migration tree are executed
as separate checkouts under the same Python process environment. Each test must
pass independently and produce the same normalized stdout/stderr transcript.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

SCHEMA = "deepofc-openofc-solver-equivalence-v1"
FROZEN_SOURCE_REPO = "pmartins87/myoh_private"
FROZEN_SOURCE_COMMIT = "c21c3c4f1017c83df07eb22230318a8131bf40d1"
SUITE_VERSION = "openofc-migration-equivalence-2026-08-27-v1"

# Deliberately predeclared against SOLVER_MIGRATION_PLAN.md. This covers the
# engine/evaluation base, continuation serialization/boundary, M4V-W-X-Y-Z,
# M5A/B policy adapters/probes, M5C-G certification/registry machinery, and the
# Normal/Fantasy and Fantasy/Fantasy kernels/payoff paths.
TESTS = (
    "test_engine.py",
    "test_hu_continuation.py",
    "test_m4u_continuation_boundary.py",
    "test_m4v_continuation_targets.py",
    "test_m4w_outcome_model.py",
    "test_m4x_robust_support.py",
    "test_m4y_bellman_trace.py",
    "test_m4z_outer_bellman.py",
    "test_m5a_component_adapters.py",
    "test_m5a_normal_fantasy_oracle.py",
    "test_m5b_fantasy_selfplay.py",
    "test_m5c_route_certification.py",
    "test_m5c_normal_route_certification.py",
    "test_m5d_dynamic_certified_bellman.py",
    "test_m5e_fantasy_route_certification.py",
    "test_m5f_fantasy_heldout_evidence.py",
    "test_m5g_full_registry_factory.py",
    "test_normal_fantasy_kernel.py",
    "test_fantasy_fantasy_kernel.py",
    "test_fantasy_fantasy_payoff.py",
)


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def canonical_sha256(payload: object) -> str:
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return sha256_text(raw)


def normalize_transcript(text: str, roots: tuple[Path, ...], temp_root: Path) -> str:
    out = text.replace("\r\n", "\n").replace("\r", "\n")
    replacements = [str(p.resolve()) for p in roots]
    replacements += [str(p.resolve()).replace("\\", "/") for p in roots]
    replacements += [str(temp_root.resolve()), str(temp_root.resolve()).replace("\\", "/")]
    for value in sorted(set(replacements), key=len, reverse=True):
        if value:
            out = out.replace(value, "<ROOT>")
    # Defensive normalization for stdlib TemporaryDirectory names if a test
    # surfaces them despite the controlled TMPDIR.
    out = re.sub(r"/tmp/tmp[A-Za-z0-9_.-]+", "<TMP>", out)
    out = re.sub(r"\\Temp\\tmp[A-Za-z0-9_.-]+", r"\\Temp\\<TMP>", out)
    return out


def run_one(solver_root: Path, test_name: str, temp_dir: Path, timeout: int) -> dict[str, object]:
    test_path = solver_root / test_name
    if not test_path.is_file():
        return {
            "returncode": 127,
            "stdout": "",
            "stderr": f"missing test: {test_name}\n",
            "duration_seconds": 0.0,
        }
    if temp_dir.exists():
        shutil.rmtree(temp_dir)
    temp_dir.mkdir(parents=True)
    env = os.environ.copy()
    env.update(
        {
            "PYTHONHASHSEED": "0",
            "PYTHONDONTWRITEBYTECODE": "1",
            "TMPDIR": str(temp_dir.resolve()),
            "TMP": str(temp_dir.resolve()),
            "TEMP": str(temp_dir.resolve()),
            "OMP_NUM_THREADS": "1",
            "OPENBLAS_NUM_THREADS": "1",
            "MKL_NUM_THREADS": "1",
            "NUMEXPR_NUM_THREADS": "1",
            "LC_ALL": "C.UTF-8",
            "LANG": "C.UTF-8",
        }
    )
    started = time.monotonic()
    try:
        proc = subprocess.run(
            [sys.executable, test_name],
            cwd=solver_root,
            env=env,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=timeout,
            check=False,
        )
        duration = time.monotonic() - started
        return {
            "returncode": proc.returncode,
            "stdout": proc.stdout,
            "stderr": proc.stderr,
            "duration_seconds": round(duration, 6),
        }
    except subprocess.TimeoutExpired as exc:
        duration = time.monotonic() - started
        stdout = exc.stdout.decode() if isinstance(exc.stdout, bytes) else (exc.stdout or "")
        stderr = exc.stderr.decode() if isinstance(exc.stderr, bytes) else (exc.stderr or "")
        return {
            "returncode": 124,
            "stdout": stdout,
            "stderr": stderr + f"\nTIMEOUT_AFTER={timeout}\n",
            "duration_seconds": round(duration, 6),
        }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--source-root", type=Path, required=True)
    ap.add_argument("--target-root", type=Path, required=True)
    ap.add_argument("--target-commit", required=True)
    ap.add_argument("--report-json", type=Path, required=True)
    ap.add_argument("--summary-md", type=Path, required=True)
    ap.add_argument("--temp-root", type=Path, required=True)
    ap.add_argument("--timeout-per-test", type=int, default=120)
    args = ap.parse_args()

    source_solver = args.source_root.resolve() / "tools" / "openofc_solver"
    target_solver = args.target_root.resolve() / "tools" / "openofc_solver"
    if not source_solver.is_dir() or not target_solver.is_dir():
        raise SystemExit("both source and target solver directories must exist")

    try:
        import numpy as np  # type: ignore
        numpy_version = np.__version__
    except Exception as exc:  # pragma: no cover - workflow dependency contract
        raise SystemExit(f"NumPy unavailable: {exc}")

    rows: list[dict[str, object]] = []
    all_match = True
    for test_name in TESTS:
        print(f"=== EQUIVALENCE {test_name} ===", flush=True)
        src_tmp = args.temp_root / "source" / test_name.removesuffix(".py")
        dst_tmp = args.temp_root / "target" / test_name.removesuffix(".py")
        src = run_one(source_solver, test_name, src_tmp, args.timeout_per_test)
        dst = run_one(target_solver, test_name, dst_tmp, args.timeout_per_test)

        src_stdout = normalize_transcript(str(src["stdout"]), (args.source_root, args.target_root), args.temp_root)
        src_stderr = normalize_transcript(str(src["stderr"]), (args.source_root, args.target_root), args.temp_root)
        dst_stdout = normalize_transcript(str(dst["stdout"]), (args.source_root, args.target_root), args.temp_root)
        dst_stderr = normalize_transcript(str(dst["stderr"]), (args.source_root, args.target_root), args.temp_root)
        src_transcript = src_stdout + "\n<STDERR>\n" + src_stderr
        dst_transcript = dst_stdout + "\n<STDERR>\n" + dst_stderr
        source_pass = int(src["returncode"]) == 0
        target_pass = int(dst["returncode"]) == 0
        transcript_equal = src_transcript == dst_transcript
        match = source_pass and target_pass and transcript_equal
        all_match = all_match and match
        row = {
            "test": test_name,
            "source_returncode": src["returncode"],
            "target_returncode": dst["returncode"],
            "source_pass": source_pass,
            "target_pass": target_pass,
            "normalized_transcript_equal": transcript_equal,
            "source_transcript_sha256": sha256_text(src_transcript),
            "target_transcript_sha256": sha256_text(dst_transcript),
            "source_duration_seconds": src["duration_seconds"],
            "target_duration_seconds": dst["duration_seconds"],
            "match": match,
        }
        rows.append(row)
        print(
            f"{test_name}: source={src['returncode']} target={dst['returncode']} "
            f"transcript_equal={transcript_equal} match={match}",
            flush=True,
        )
        if not match:
            print("--- normalized source stdout ---")
            print(src_stdout[-4000:])
            print("--- normalized target stdout ---")
            print(dst_stdout[-4000:])
            print("--- normalized source stderr ---")
            print(src_stderr[-4000:])
            print("--- normalized target stderr ---")
            print(dst_stderr[-4000:])

    report: dict[str, object] = {
        "schema": SCHEMA,
        "suite_version": SUITE_VERSION,
        "source_repo": FROZEN_SOURCE_REPO,
        "source_commit": FROZEN_SOURCE_COMMIT,
        "target_repo": "pmartins87/DeepOFC",
        "target_commit_at_gate_start": args.target_commit,
        "python_version": platform.python_version(),
        "numpy_version": numpy_version,
        "pythonhashseed": "0",
        "test_count": len(rows),
        "matched_count": sum(1 for row in rows if row["match"]),
        "all_source_pass": all(bool(row["source_pass"]) for row in rows),
        "all_target_pass": all(bool(row["target_pass"]) for row in rows),
        "all_normalized_transcripts_equal": all(bool(row["normalized_transcript_equal"]) for row in rows),
        "equivalence_pass": all_match,
        "tests": rows,
    }
    report_sha = canonical_sha256(report)
    report["canonical_sha256_without_this_field"] = report_sha
    args.report_json.parent.mkdir(parents=True, exist_ok=True)
    args.summary_md.parent.mkdir(parents=True, exist_ok=True)
    args.report_json.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    status = "PASS" if all_match else "FAIL"
    table = ["| Test | Source | Target | Transcript | Result |", "|---|---:|---:|---|---|"]
    for row in rows:
        table.append(
            f"| `{row['test']}` | {row['source_returncode']} | {row['target_returncode']} | "
            f"{'equal' if row['normalized_transcript_equal'] else 'DIFF'} | "
            f"{'PASS' if row['match'] else 'FAIL'} |"
        )
    summary = f"""# OpenOFC solver old-vs-new equivalence\n\nStatus: **{status}**\n\n- suite: `{SUITE_VERSION}`\n- frozen source: `{FROZEN_SOURCE_REPO}@{FROZEN_SOURCE_COMMIT}`\n- target gate-start commit: `{args.target_commit}`\n- Python: `{platform.python_version()}`\n- NumPy: `{numpy_version}`\n- tests: **{len(rows)}**\n- matched: **{sum(1 for row in rows if row['match'])}**\n- canonical report SHA-256: `{report_sha}`\n\n""" + "\n".join(table) + "\n\nThe comparison runs the two repositories independently with fixed process/thread environment and requires zero exit status plus byte-identical normalized stdout/stderr for every predeclared test.\n"
    args.summary_md.write_text(summary, encoding="utf-8")

    print(f"OPENOFC_SOLVER_EQUIVALENCE_MATCHED={sum(1 for row in rows if row['match'])}/{len(rows)}")
    print(f"OPENOFC_SOLVER_EQUIVALENCE_REPORT_SHA256={report_sha}")
    print(f"OPENOFC_SOLVER_EQUIVALENCE={status}")
    if not all_match:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
