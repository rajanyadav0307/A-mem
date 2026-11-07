"""Inputs and manifest for the 8-setup test.

    preflight.py init               copy the sample 0-2 banks, start manifest.json, record computer + served model
    preflight.py register-sample3   after a passing build check: copy the sample 3 bank in, record fingerprints
    preflight.py register-keywords  record keyword file fingerprints
    preflight.py freeze-code        record the code commit every run must match

Nothing is ever overwritten: copying stops if a target file exists.
"""

from __future__ import annotations

import argparse
import datetime
import json
import os
import pickle
import platform
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import common  # noqa: E402

sys.path.insert(0, common.REPO)
os.chdir(common.REPO)


def env_key():
    if os.environ.get("OPENAI_API_KEY"):
        return os.environ["OPENAI_API_KEY"]
    for line in open(".env", encoding="utf-8"):
        line = line.strip()
        if line.startswith("export "):
            line = line[len("export "):]
        if line.startswith("OPENAI_API_KEY="):
            return line.split("=", 1)[1].strip().strip('"').strip("'")
    raise SystemExit("STOP: no OPENAI_API_KEY")


def copy_once(src, dst):
    """Copy, never overwrite. An existing identical copy is accepted; a different one stops."""
    if os.path.exists(dst):
        if common.sha256(dst) == common.sha256(src):
            return
        raise SystemExit(f"STOP: {dst} exists and differs from {src}; nothing is overwritten")
    shutil.copy2(src, dst)


def bank_record(sample):
    files = common.bank_files(sample)
    notes = list(pickle.load(open(files[0], "rb")).values())
    out = {}
    for f in files:
        out[f] = {"sha256": common.sha256(f)}
    out[files[0]].update({"notes": len(notes), "raw_notes": sum(n.note_type == "raw" for n in notes),
                          "merged_notes": sum(n.note_type == "consolidated" for n in notes),
                          "timeline_notes": sum(n.timeline_id is not None for n in notes),
                          "happened_dates": sum(bool(n.event_time) for n in notes)})
    return out


def computer():
    sysctl = lambda k: subprocess.run(["sysctl", "-n", k], capture_output=True, text=True).stdout.strip()  # noqa: E731
    return {"cpu": sysctl("machdep.cpu.brand_string"), "cores": int(sysctl("hw.ncpu")),
            "performance_cores": sysctl("hw.perflevel0.physicalcpu"), "efficiency_cores": sysctl("hw.perflevel1.physicalcpu"),
            "memory_gb": int(sysctl("hw.memsize")) // 2**30, "os": platform.platform(),
            "python": platform.python_version()}


def served_model():
    from openai import OpenAI
    client = OpenAI(api_key=env_key())
    r = client.chat.completions.create(model=common.MODEL, messages=[{"role": "user", "content": "Reply with the word OK."}],
                                       max_tokens=3, temperature=0)
    return {"requested": common.MODEL, "served": r.model, "checked": datetime.datetime.now().isoformat(timespec="seconds"),
            "tokens": r.usage.total_tokens}


def init():
    if os.path.exists(common.MANIFEST):
        raise SystemExit(f"STOP: {common.MANIFEST} exists")
    os.makedirs(common.SHARED_BANK, exist_ok=True)
    for s in (0, 1, 2):
        names = [os.path.basename(f) for f in common.bank_files(s)]
        src = [os.path.join(common.SOURCE_BANK_0_2, n) for n in names]
        if not common.sha256(src[0]).startswith(common.SOURCE_SHA_PREFIX[s]):
            raise SystemExit(f"STOP: source bank for sample {s} is not the expected one")
        for a, b in zip(src, common.bank_files(s)):
            copy_once(a, b)
            if common.sha256(a) != common.sha256(b):
                raise SystemExit(f"STOP: copy of {a} differs")
    manifest = {
        "plan": "PLAN.md", "plan_sha256": common.sha256(os.path.join(common.EXP, "PLAN.md")),
        "created": datetime.datetime.now().isoformat(timespec="seconds"),
        "branch": subprocess.check_output(["git", "branch", "--show-current"]).decode().strip(),
        "code_commit": None,
        "model": common.MODEL, "served_model": served_model(),
        "samples": list(common.SAMPLES), "questions": {str(k): v for k, v in common.QUESTIONS.items()},
        "seeds": list(common.SEEDS), "setups": {k: dict(zip(("time_ranking", "consolidation", "conflict"), v))
                                                for k, v in common.SETUPS.items()},
        "commands": {f"{s}_seed{seed}": common.command(s, seed) for s in common.SETUPS for seed in common.SEEDS},
        "computer": computer(),
        "banks": {}, "bank_sources": {str(s): common.SOURCE_BANK_0_2 for s in (0, 1, 2)},
        "keywords": {}, "attempts": [], "changes": [],
    }
    for s in (0, 1, 2):
        manifest["banks"].update(bank_record(s))
    common.save_manifest(manifest)
    print(json.dumps({k: manifest[k] for k in ("served_model", "computer")}, indent=1))
    print(f"banks 0-2 copied to {common.SHARED_BANK}; manifest written")


def register_sample3():
    m = common.load_manifest()
    check = json.load(open(os.path.join(common.CHECKS_DIR, "build_sample3.json")))
    if not check["ok"]:
        raise SystemExit("STOP: build checks did not pass")
    src_dir = os.path.join(common.SAMPLE3_BUILD, "conflict")
    for f in common.bank_files(3):
        copy_once(os.path.join(src_dir, os.path.basename(f)), f)
    m["banks"].update(bank_record(3))
    m["bank_sources"]["3"] = src_dir
    m["sample3_build"] = {k: common.sha256(os.path.join(common.SAMPLE3_BUILD, k, "memory_cache_sample_3.pkl"))
                          for k in ("base", "consolidated", "conflict")}
    common.save_manifest(m)
    print("sample 3 registered:", m["banks"][common.bank_files(3)[0]])


def register_keywords():
    m = common.load_manifest()
    for seed in common.SEEDS:
        path = common.keywords_file(seed)
        if os.path.exists(path):
            data = json.load(open(path))
            m["keywords"][str(seed)] = {"file": path, "sha256": common.sha256(path), "questions": len(data["keywords"]),
                                        "made_with": data["made_with"], "finished": data["finished"]}
    common.save_manifest(m)
    print("keywords registered:", sorted(m["keywords"]))


def freeze_code():
    if common.python_files_dirty():
        raise SystemExit("STOP: uncommitted Python changes")
    m = common.load_manifest()
    m["code_commit"] = common.git_commit()
    common.save_manifest(m)
    print("code frozen at", m["code_commit"])


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("what", choices=["init", "register-sample3", "register-keywords", "freeze-code"])
    args = parser.parse_args()
    {"init": init, "register-sample3": register_sample3, "register-keywords": register_keywords,
     "freeze-code": freeze_code}[args.what]()
