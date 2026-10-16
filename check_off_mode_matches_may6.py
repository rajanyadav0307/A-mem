"""
Check that consolidation_mode="off" gives exactly the May 6 retrieval.

Exports the memory-layer modules from the May 6 commit, dumps every
retrieval context with that code on the original cache, then dumps them with
the current code in "off" mode on (a) the original cache and (b) a
consolidated cache. All three must match hash-for-hash.

Example:
    .venv/bin/python check_off_mode_matches_may6.py \
        --consolidated_cache cached_memories_robust_openai_gpt-4o-mini_consolidated_tau0.80_v3
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tempfile

MAY6_COMMIT = "24ad98fa"
MODULES = ("load_dataset.py", "memory_layer.py", "memory_layer_robust.py",
           "memory_layer_tmem_robust.py", "llm_text_parsers.py")


def export_commit(commit: str, target: str) -> None:
    for module in MODULES:
        source = subprocess.run(
            ["git", "show", f"{commit}:{module}"], check=True, capture_output=True, text=True
        ).stdout
        with open(os.path.join(target, module), "w", encoding="utf-8") as handle:
            handle.write(source)


def dump(output: str, cache_dir: str, samples, code_dir=None, mode=None) -> dict:
    cmd = [sys.executable, "dump_retrieval_contexts.py", "--cache_dir", cache_dir,
           "--samples", *map(str, samples), "--output", output]
    if code_dir:
        cmd += ["--code_dir", code_dir]
    if mode:
        cmd += ["--mode", mode]
    run = subprocess.run(cmd, capture_output=True, text=True)
    if run.returncode != 0:
        raise RuntimeError(run.stderr[-2000:])
    with open(output, encoding="utf-8") as handle:
        return json.load(handle)


def compare(reference: dict, candidate: dict) -> list:
    ref = {(r["system"], r["sample"], r["question_index"]): r["sha256"] for r in reference["records"]}
    cand = {(r["system"], r["sample"], r["question_index"]): r["sha256"] for r in candidate["records"]}
    if ref.keys() != cand.keys():
        return ["different question sets"]
    return [key for key in ref if ref[key] != cand[key]]


def main():
    parser = argparse.ArgumentParser(description=__doc__.strip().splitlines()[0])
    parser.add_argument("--cache_dir", default="cached_memories_robust_openai_gpt-4o-mini")
    parser.add_argument("--consolidated_cache", default=None)
    parser.add_argument("--samples", type=int, nargs="+", default=[0, 1])
    parser.add_argument("--output", default="analysis/off_mode_check.json")
    args = parser.parse_args()

    with tempfile.TemporaryDirectory() as tmp:
        code_dir = os.path.join(tmp, "may6")
        os.makedirs(code_dir)
        export_commit(MAY6_COMMIT, code_dir)
        reference = dump(os.path.join(tmp, "may6.json"), args.cache_dir, args.samples, code_dir=code_dir)
        if not reference["memory_layer_robust_file"].startswith(code_dir):
            raise RuntimeError("May 6 dump did not import the exported code")

        checks = {"current code, off, original cache": (args.cache_dir, "off")}
        if args.consolidated_cache:
            checks["current code, off, consolidated cache"] = (args.consolidated_cache, "off")

        report = {"reference": f"May 6 code ({MAY6_COMMIT}) on {args.cache_dir}",
                  "contexts": len(reference["records"]), "checks": {}}
        ok = True
        for name, (cache, mode) in checks.items():
            candidate = dump(os.path.join(tmp, "candidate.json"), cache, args.samples, mode=mode)
            mismatches = compare(reference, candidate)
            ok &= not mismatches
            report["checks"][name] = {"cache_dir": cache, "mismatches": len(mismatches),
                                      "examples": [list(m) for m in mismatches[:10]]}
            print(f"{name}: {len(reference['records'])} contexts, {len(mismatches)} mismatches")

    report["identical"] = ok
    with open(args.output, "w", encoding="utf-8") as handle:
        json.dump(report, handle, indent=2)
    print(("PASS" if ok else "FAIL") + f" -> {args.output}")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
