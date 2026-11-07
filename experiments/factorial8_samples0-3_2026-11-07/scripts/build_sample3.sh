#!/bin/bash
# Stage 1: build the sample 3 memory, exactly as sample 2 was built on 2026-10-26:
#   1. A-MEM notes with the author's unchanged code (build_memory_bank.py)
#   2. merged notes, v3 settings (build_consolidated_cache.py defaults: 0.80, groups of 5, same speaker, 2 retries, union)
#   3. timelines with "happened" dates (build_conflict_bank.py), fresh AI-answer cache folder
# Then the build checks (B1-B5) and, only if they pass, the copy into cache/shared.
#
# Run from the repository root:
#   caffeinate -dims bash experiments/factorial8_samples0-3_2026-11-07/scripts/build_sample3.sh

set -euo pipefail
EXP="experiments/factorial8_samples0-3_2026-11-07"
B="$EXP/cache/build_sample3"
PY=".venv/bin/python"
MODEL="gpt-4o-mini-2024-07-18"

if [ -e "$B" ]; then echo "STOP: $B exists; nothing is overwritten"; exit 1; fi
mkdir -p "$B/logs/conflict" "$EXP/build_logs"
caffeinate -dims -w $$ &   # keep the computer awake until this script ends
set -a; . ./.env; set +a
export HF_HUB_OFFLINE=1

date -u +%Y-%m-%dT%H:%M:%SZ > "$B/started_at.txt"
$PY build_memory_bank.py --samples 3 --output_dir "$B/base" --model "$MODEL" > "$B/logs/base.stdout" 2>&1
$PY build_consolidated_cache.py --source_cache "$B/base" --output_dir "$B/consolidated" --samples 3 \
    --model "$MODEL" --tag f8 --log_dir "$B/logs" > "$B/logs/consolidated.stdout" 2>&1
$PY build_conflict_bank.py --source_cache "$B/consolidated" --output_dir "$B/conflict" --samples 3 \
    --model "$MODEL" --tag f8 --log_dir "$B/logs/conflict" > "$B/logs/conflict.stdout" 2>&1
date -u +%Y-%m-%dT%H:%M:%SZ > "$B/finished_at.txt"

# small build records that go into git
cp "$B/base/build_report.json" "$EXP/build_logs/sample3_base_build_report.json"
cp "$B/logs/consolidation_log_sample_3_f8.json" "$EXP/build_logs/sample3_consolidation_log.json"
cp "$B/logs/conflict/conflict_log_sample_3.json" "$EXP/build_logs/sample3_conflict_log.json"
cp "$B/logs/conflict/build_summary.json" "$EXP/build_logs/sample3_conflict_build_summary.json"
cp "$B/started_at.txt" "$EXP/build_logs/sample3_started_at.txt"
cp "$B/finished_at.txt" "$EXP/build_logs/sample3_finished_at.txt"

$PY "$EXP/scripts/checks.py" build
$PY "$EXP/scripts/preflight.py" register-sample3
echo "Stage 1 done"
