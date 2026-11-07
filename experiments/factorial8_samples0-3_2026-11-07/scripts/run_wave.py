"""Stages 3-5: run one wave (all 8 setups for one seed), then check it.

    caffeinate -dims .venv/bin/python <exp>/scripts/run_wave.py --seed 42
    caffeinate -dims .venv/bin/python <exp>/scripts/run_wave.py --trial      (Stage 3: s1_amem, sample 0, seed 42)

Steps: input checks -> 8 evaluator processes side by side -> evaluator logs
renamed to <setup>_seed<N>.log -> result checks. A run that exits with an error
or leaves no result file is moved to invalid/ with reason.txt and the wave
stops with a non-zero exit code. Nothing is overwritten.
"""

from __future__ import annotations

import argparse
import datetime
import glob
import json
import os
import shutil
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import common  # noqa: E402

os.chdir(common.REPO)


def env():
    e = dict(os.environ)
    for line in open(".env", encoding="utf-8"):
        line = line.strip()
        if line.startswith("export "):
            line = line[len("export "):]
        if "=" in line and not line.startswith("#"):
            k, v = line.split("=", 1)
            e[k.strip()] = v.strip().strip('"').strip("'")
    e["HF_HUB_OFFLINE"] = "1"
    return e


def record(entry):
    m = common.load_manifest()
    m["attempts"].append(entry)
    common.save_manifest(m)


def invalidate(setup, seed, reason, files):
    n = len(glob.glob(os.path.join(common.INVALID_DIR, f"{setup}_seed{seed}_attempt*"))) + 1
    d = os.path.join(common.INVALID_DIR, f"{setup}_seed{seed}_attempt{n}")
    os.makedirs(d)
    for f in files:
        if os.path.exists(f):
            shutil.move(f, os.path.join(d, os.path.basename(f)))
    with open(os.path.join(d, "reason.txt"), "w") as handle:
        handle.write(reason + "\n")
    return d


def trial():
    """Stage 3: A-MEM, sample 0 only, seed 42, shared words. Output goes to trial/, never to results/."""
    out_dir = os.path.join(common.EXP, "trial")
    if os.path.exists(out_dir):
        sys.exit(f"STOP: {out_dir} exists")
    os.makedirs(out_dir)
    cmd = common.command("s1_amem", 42)
    cmd[cmd.index("--ratio") + 1] = "0.1"
    cmd[cmd.index("--output") + 1] = os.path.join(out_dir, "s1_amem_seed42_sample0.json")
    cmd[cmd.index("--run_tag") + 1] = "f8_trial"
    started = datetime.datetime.now().isoformat(timespec="seconds")
    with open(os.path.join(out_dir, "s1_amem_seed42_sample0.stdout"), "w") as so:
        code = subprocess.run(cmd, stdout=so, stderr=subprocess.STDOUT, env=env()).returncode
    logs = glob.glob("logs/eval_*_f8_trial_*.log")
    for f in logs:
        shutil.move(f, os.path.join(out_dir, "s1_amem_seed42_sample0.log"))
    record({"stage": "trial", "started": started, "finished": datetime.datetime.now().isoformat(timespec="seconds"),
            "exit_code": code, "command": cmd})
    print("trial exit code", code, "-> check it with: checks on trial/ (see REPORT)")
    sys.exit(code)


def wave(seed):
    chk = [common.PY, os.path.join(common.EXP, "scripts", "checks.py")]
    if subprocess.run(chk + ["inputs", "--seed", str(seed)]).returncode != 0:
        sys.exit(f"STOP: input checks failed for seed {seed}; nothing was started")
    os.makedirs(common.RESULTS_DIR, exist_ok=True)
    os.makedirs(common.LOGS_DIR, exist_ok=True)
    started = datetime.datetime.now().isoformat(timespec="seconds")
    t0 = time.time()
    procs = {}
    for setup in common.SETUPS:
        if os.path.exists(common.result_file(setup, seed)):
            sys.exit(f"STOP: {common.result_file(setup, seed)} exists")
        so = open(common.log_file(setup, seed)[:-4] + ".stdout", "w")
        procs[setup] = (subprocess.Popen(common.command(setup, seed), stdout=so, stderr=subprocess.STDOUT, env=env()), so)
    codes = {}
    for setup, (p, so) in procs.items():
        codes[setup] = p.wait()
        so.close()
    minutes = round((time.time() - t0) / 60, 1)
    failed = []
    for setup in common.SETUPS:
        logs = glob.glob(f"logs/eval_*_{common.run_tag(setup, seed)}_*.log")
        if len(logs) == 1:
            shutil.move(logs[0], common.log_file(setup, seed))
        problem = None
        if codes[setup] != 0:
            problem = f"exit code {codes[setup]}"
        elif not os.path.exists(common.result_file(setup, seed)):
            problem = "no result file"
        elif len(logs) != 1:
            problem = f"{len(logs)} evaluator logs found"
        if problem:
            d = invalidate(setup, seed, problem, [common.result_file(setup, seed), common.log_file(setup, seed),
                                                  common.log_file(setup, seed)[:-4] + ".stdout"] + logs)
            failed.append(f"{setup}: {problem} (moved to {d})")
    record({"stage": "wave", "seed": seed, "started": started, "finished": datetime.datetime.now().isoformat(timespec="seconds"),
            "minutes": minutes, "exit_codes": codes, "failed": failed})
    if failed:
        sys.exit("STOP: " + "; ".join(failed))
    code = subprocess.run(chk + ["results", "--seed", str(seed)]).returncode
    print(f"wave seed {seed}: {minutes} min, result checks {'PASSED' if code == 0 else 'FAILED'}")
    sys.exit(code)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--seed", type=int, choices=common.SEEDS)
    parser.add_argument("--trial", action="store_true")
    args = parser.parse_args()
    if args.trial:
        trial()
    elif args.seed:
        wave(args.seed)
    else:
        parser.error("give --seed or --trial")
