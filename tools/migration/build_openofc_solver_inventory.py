#!/usr/bin/env python3
"""Build a provenance/dependency inventory for the frozen OpenOFC solver staging tree."""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
import subprocess
from collections import Counter, deque
from pathlib import Path
from typing import Iterable

SCHEMA = "deepofc-openofc-solver-inventory-v2"
STAGING_PREFIX = "tools/openofc_solver/"
WORKFLOW_PREFIX = ".github/workflows/"


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def git_ls_tree(source_root: Path, commit: str, prefixes: Iterable[str]) -> dict[str, dict[str, object]]:
    cmd = ["git", "-C", str(source_root), "ls-tree", "-r", "-l", commit, "--", *prefixes]
    out = subprocess.check_output(cmd, text=True, encoding="utf-8")
    result: dict[str, dict[str, object]] = {}
    for line in out.splitlines():
        meta, path = line.split("\t", 1)
        mode, obj_type, blob_sha, size = meta.split()
        result[path] = {
            "git_mode": mode,
            "git_type": obj_type,
            "blob_sha": blob_sha,
            "size": int(size) if size != "-" else None,
        }
    return result


def role_for(path: str) -> str:
    name = Path(path).name
    lower = name.lower()
    if path.startswith(WORKFLOW_PREFIX) and lower.endswith((".yml", ".yaml")):
        return "workflow"
    if lower.endswith(".md") and "contract" in lower:
        return "contract"
    if lower.startswith("test_") and lower.endswith(".py"):
        return "test"
    if lower.endswith(".py") and lower.startswith(("run_", "audit_", "generate_", "train_", "plan_")):
        return "benchmark"
    if lower.endswith(".py") and lower.startswith(("check_", "extract_", "materialize_", "apply_")):
        return "helper"
    if lower.endswith(".py"):
        return "source"
    return "helper"


def parse_local_imports(path: Path, module_to_path: dict[str, str]) -> list[str]:
    if path.suffix != ".py":
        return []
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    except (UnicodeDecodeError, SyntaxError):
        return []
    imported: set[str] = set()
    for node in ast.walk(tree):
        names: list[str] = []
        if isinstance(node, ast.Import):
            names.extend(alias.name.split(".", 1)[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            names.append(node.module.split(".", 1)[0])
        for name in names:
            target = module_to_path.get(name)
            if target:
                imported.add(target)
    return sorted(imported)


def is_current_contract(path: str) -> bool:
    name = Path(path).name.upper()
    return name.startswith("M4") or name.startswith("M5")


def is_current_code_root(path: str) -> bool:
    stem = Path(path).stem.lower()
    roots = ("m4u_", "m4v_", "m4w_", "m4x_", "m4y_", "m4z_", "m5a_", "m5b_", "m5c_", "m5d_", "m5e_", "m5f_", "m5g_")
    if stem.startswith(roots):
        return True
    if stem.startswith("test_"):
        return stem[5:].startswith(roots)
    return False


def dependency_closure(start: Iterable[str], records: dict[str, dict[str, object]]) -> set[str]:
    closure = set(start)
    q = deque(sorted(closure))
    while q:
        p = q.popleft()
        for dep in records[p]["local_imports"]:  # type: ignore[index]
            if dep not in closure:
                closure.add(dep)
                q.append(dep)
    return closure


def fixed_point_migration_set(
    initial_closure: set[str], solver_paths: list[str], records: dict[str, dict[str, object]]
) -> set[str]:
    """Close migration over selected tests and their imports until stable.

    G1 v1 added tests for migrated modules after computing the dependency closure.
    Behavioral equivalence exposed the consequence: a newly selected test could
    import a helper/source module that never entered the migration set. v2 makes
    selection a fixed point: selected Python -> local imports, and every selected
    module -> its matching test, repeatedly until no new files appear.
    """
    selected = set(initial_closure)
    selected.update(p for p in solver_paths if p.endswith(".md") and is_current_contract(p))

    while True:
        before = set(selected)

        # Any local dependency of any selected Python file is part of the migration.
        selected |= dependency_closure(
            (p for p in selected if p.endswith(".py")), records
        )

        # Preserve the direct test for every migrated implementation/helper module.
        migrated_module_stems = {
            Path(p).stem
            for p in selected
            if p.endswith(".py") and not Path(p).name.startswith("test_")
        }
        for p in solver_paths:
            name = Path(p).name
            if name.startswith("test_") and p.endswith(".py") and Path(p).stem[5:] in migrated_module_stems:
                selected.add(p)

        # The newly selected tests may themselves pull further local dependencies.
        selected |= dependency_closure(
            (p for p in selected if p.endswith(".py")), records
        )

        if selected == before:
            return selected


def build(source_root: Path, commit: str) -> tuple[dict[str, object], str]:
    meta = git_ls_tree(source_root, commit, ["tools/openofc_solver", ".github/workflows"])
    solver_paths = sorted(p for p in meta if p.startswith(STAGING_PREFIX))
    workflow_paths = sorted(
        p for p in meta
        if p.startswith(WORKFLOW_PREFIX)
        and ("openofc-m4" in Path(p).name.lower() or "openofc-m5" in Path(p).name.lower())
    )

    module_to_path = {
        Path(p).stem: p
        for p in solver_paths
        if p.endswith(".py")
    }

    records: dict[str, dict[str, object]] = {}
    for p in solver_paths:
        disk = source_root / p
        raw = disk.read_bytes()
        rec = dict(meta[p])
        rec.update(
            {
                "source_path": p,
                "file_sha256": sha256_bytes(raw),
                "role": role_for(p),
                "local_imports": parse_local_imports(disk, module_to_path),
            }
        )
        records[p] = rec

    roots = sorted(p for p in solver_paths if is_current_code_root(p))
    initial_closure = dependency_closure(roots, records)
    selected = fixed_point_migration_set(initial_closure, solver_paths, records)

    for p in solver_paths:
        if p in initial_closure:
            disposition = "migrate"
            reason = "current M4/M5 lineage or initial transitive local dependency"
        elif p.endswith(".md") and is_current_contract(p):
            disposition = "migrate"
            reason = "current M4/M5 contract"
        elif p in selected:
            disposition = "migrate"
            reason = "fixed-point dependency/test closure of migrated strategic tree"
        else:
            disposition = "historical"
            reason = "preserved staging history; not in fixed-point M4U-M5G migration closure"
        records[p]["migration_disposition"] = disposition
        records[p]["disposition_reason"] = reason

    workflows: list[dict[str, object]] = []
    for p in workflow_paths:
        raw = (source_root / p).read_bytes()
        item = dict(meta[p])
        item.update(
            {
                "source_path": p,
                "file_sha256": sha256_bytes(raw),
                "role": "workflow",
                "migration_disposition": "migrate",
                "disposition_reason": "M4/M5 staging CI provenance",
            }
        )
        workflows.append(item)

    file_list = [records[p] for p in solver_paths]
    role_counts = Counter(str(x["role"]) for x in file_list)
    disposition_counts = Counter(str(x["migration_disposition"]) for x in file_list)
    files_digest = sha256_bytes(json.dumps(file_list, sort_keys=True, separators=(",", ":")).encode("utf-8"))
    final_python_count = sum(1 for p in selected if p.endswith(".py"))

    payload: dict[str, object] = {
        "schema": SCHEMA,
        "source_repo": "pmartins87/myoh_private",
        "source_commit": commit,
        "source_subtree": "tools/openofc_solver",
        "source_tree_sha": subprocess.check_output(
            ["git", "-C", str(source_root), "rev-parse", f"{commit}:tools/openofc_solver"],
            text=True,
            encoding="utf-8",
        ).strip(),
        "policy": {
            "roots": roots,
            "initial_root_dependency_closure_count": len(initial_closure),
            "final_python_dependency_test_closure_count": final_python_count,
            "dependency_closure_fixed_point": True,
            "all_m4_m5_contracts_migrate": True,
            "tests_for_migrated_modules_migrate": True,
            "selected_test_dependencies_migrate": True,
            "nonclosure_files_default": "historical",
            "v2_correction_reason": "old-vs-new equivalence exposed test_engine.py -> teacher_search.py missing from v1 post-test dependency closure",
        },
        "summary": {
            "solver_subtree_file_count": len(file_list),
            "workflow_count": len(workflows),
            "role_counts": dict(sorted(role_counts.items())),
            "disposition_counts": dict(sorted(disposition_counts.items())),
            "files_payload_sha256": files_digest,
        },
        "observations": {
            "m5d_present": "tools/openofc_solver/m5d_dynamic_certified_bellman.py" in records,
            "m5e_present": "tools/openofc_solver/m5e_fantasy_route_certification.py" in records,
            "m5f_present": "tools/openofc_solver/m5f_fantasy_heldout_evidence.py" in records,
            "m5g_present": "tools/openofc_solver/m5g_full_registry_factory.py" in records,
            "teacher_search_selected": "tools/openofc_solver/teacher_search.py" in selected,
            "strategic_quality_note": "M5D-M5G architecture/source presence does not imply real route evidence or production certification.",
        },
        "files": file_list,
        "related_workflows": workflows,
    }

    summary = payload["summary"]  # type: ignore[assignment]
    md = f"""# OpenOFC solver staging inventory — c21c3c4\n\nFrozen source: `pmartins87/myoh_private@{commit}`\n\nSchema: `{SCHEMA}`\n\nThis inventory is generated by `tools/migration/build_openofc_solver_inventory.py`. It is an ownership/provenance artifact, not a strategic certification.\n\n## Counts\n\n- solver-subtree files: **{summary['solver_subtree_file_count']}**\n- initial M4U–M5G root dependency closure: **{len(initial_closure)}**\n- final fixed-point selected Python/test closure: **{final_python_count}**\n- disposition migrate: **{disposition_counts.get('migrate', 0)}**\n- disposition historical: **{disposition_counts.get('historical', 0)}**\n- related M4/M5 workflows: **{len(workflows)}**\n- files payload SHA-256: `{files_digest}`\n\nRole counts: `{json.dumps(dict(sorted(role_counts.items())), sort_keys=True)}`\n\n## G1 v2 correction\n\nThe first behavioral old-vs-new gate passed 19/20 probes and exposed one inventory-closure bug: migrated `test_engine.py` imports `teacher_search.py`, while G1 v1 added tests after dependency closure and therefore failed to close dependencies introduced by those tests. v2 uses a fixed-point rule over **selected Python -> local imports** and **migrated module -> matching test** until the set is stable. This is a provenance correction, not a solver semantic change.\n\n## Material finding\n\nThe exact frozen tree contains implemented/tested **M5D, M5E, M5F and M5G** source/contracts in addition to M5C. Their presence does **not** mean strategic promotion has passed: M5G explicitly requires 50/50 real-certified exact-V routes, and the next strategic work remains real held-out evidence plus defensible thresholds before a real dynamic Bellman trace.\n\n## Migration rule\n\nFiles marked `migrate` are the fixed-point closure of current M4/M5 lineage, its local dependencies, associated M4/M5 contracts, matching tests, and dependencies introduced by those selected tests. Other preserved files remain `historical` for audit rather than being silently copied.\n"""
    return payload, md


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--source-root", type=Path, required=True)
    ap.add_argument("--source-commit", required=True)
    ap.add_argument("--json-output", type=Path, required=True)
    ap.add_argument("--md-output", type=Path, required=True)
    args = ap.parse_args()

    payload, md = build(args.source_root.resolve(), args.source_commit)
    args.json_output.parent.mkdir(parents=True, exist_ok=True)
    args.md_output.parent.mkdir(parents=True, exist_ok=True)
    args.json_output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    args.md_output.write_text(md, encoding="utf-8")


if __name__ == "__main__":
    main()
