"""Single source of truth for the 8-setup test (see ../PLAN.md).

Every script imports the setups, settings, seeds and paths from here, so a
setting can only be defined once.
"""

from __future__ import annotations

import hashlib
import json
import os
import subprocess

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
EXP = os.path.relpath(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")), REPO)  # relative to REPO
PY = os.path.join(REPO, ".venv", "bin", "python")

MODEL = "gpt-4o-mini-2024-07-18"
SAMPLES = (0, 1, 2, 3)
RATIO = "0.4"                      # first 4 LoCoMo samples
QUESTIONS = {0: 199, 1: 105, 2: 193, 3: 260}
TOTAL_QUESTIONS = sum(QUESTIONS.values())  # 757
SEEDS = (42, 43, 44, 45, 46)
RETRIEVE_K = "10"

SHARED_BANK = os.path.join(EXP, "cache", "shared")
KEYWORDS_DIR = os.path.join(EXP, "keywords")
RESULTS_DIR = os.path.join(EXP, "results")
LOGS_DIR = os.path.join(EXP, "logs")
CHECKS_DIR = os.path.join(EXP, "checks")
INVALID_DIR = os.path.join(EXP, "invalid")
MANIFEST = os.path.join(EXP, "manifest.json")

# Source of the final banks for samples 0-2 (checked identical to A-MEM's own notes on 2026-11-06).
SOURCE_BANK_0_2 = "experiments/e2e_samples0-2_2026-10-26_14-31_two_dates/cache/conflict"
SOURCE_SHA_PREFIX = {0: "1e56b339f9f5", 1: "60e6feb3f5c3", 2: "17053435f4aa"}
SAMPLE3_BUILD = os.path.join(EXP, "cache", "build_sample3")

# setup id: (time ranking, consolidation, conflict handling)
SETUPS = {
    "s1_amem": (False, False, False),
    "s2_t": (True, False, False),
    "s3_c": (False, True, False),
    "s4_h": (False, False, True),
    "s5_tc": (True, True, False),
    "s6_th": (True, False, True),
    "s7_ch": (False, True, True),
    "s8_tch": (True, True, True),
}

TEMPORAL_DEFAULTS = {  # thesis V2 defaults, as written by the T-MEM evaluator into its results
    "decay_lambda": 0.1, "blend_alpha": 0.9, "decay_age_unit": "months_equiv",
    "use_decay_only_temporal": True, "reinforce_beta": 0.5, "link_gamma": 0.3,
    "update_access_stats": False, "candidate_pool_size": 20, "semantic_anchor_count": 2,
    "semantic_margin_to_skip_temporal": 0.05, "temporal_score_floor": 0.25, "temporal_categories": [2],
}


def setup_flags(setup: str):
    return SETUPS[setup]


def keywords_file(seed: int) -> str:
    return os.path.join(KEYWORDS_DIR, f"keywords_seed{seed}.json")


def result_file(setup: str, seed: int) -> str:
    return os.path.join(RESULTS_DIR, f"{setup}_seed{seed}.json")


def log_file(setup: str, seed: int) -> str:
    return os.path.join(LOGS_DIR, f"{setup}_seed{seed}.log")


def run_tag(setup: str, seed: int) -> str:
    return f"f8_{setup}_s{seed}"


def command(setup: str, seed: int):
    """The exact evaluator command for one run."""
    t, c, h = SETUPS[setup]
    script = "test_tmem_advanced_robust.py" if t else "test_advanced_robust.py"
    cmd = [PY, script, "--model", MODEL, "--backend", "openai", "--ratio", RATIO, "--retrieve_k", RETRIEVE_K,
           "--memories_dir", SHARED_BANK, "--seed", str(seed), "--run_tag", run_tag(setup, seed),
           "--keywords_file", keywords_file(seed), "--output", result_file(setup, seed)]
    if c:
        cmd += ["--consolidation_mode", "primary_expand", "--consolidated_top_k_cap", "1"]
    if h:
        cmd += ["--conflict_mode", "annotate_demote", "--demote_penalty", "0.10", "--timeline_date_style", "two_dates"]
    return cmd


def sha256(path: str) -> str:
    with open(os.path.join(REPO, path) if not os.path.isabs(path) else path, "rb") as handle:
        return hashlib.sha256(handle.read()).hexdigest()


def bank_files(sample: int):
    return [os.path.join(SHARED_BANK, f"memory_cache_sample_{sample}.pkl"),
            os.path.join(SHARED_BANK, f"retriever_cache_sample_{sample}.pkl"),
            os.path.join(SHARED_BANK, f"retriever_cache_embeddings_sample_{sample}.npy")]


def git_commit() -> str:
    return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=REPO).decode().strip()


def python_files_dirty() -> str:
    return subprocess.check_output(["git", "status", "--porcelain", "--", "*.py"], cwd=REPO).decode().strip()


def load_manifest():
    with open(os.path.join(REPO, MANIFEST), encoding="utf-8") as handle:
        return json.load(handle)


def save_manifest(manifest):
    path = os.path.join(REPO, MANIFEST)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as handle:
        json.dump(manifest, handle, indent=1)
    os.replace(tmp, path)
