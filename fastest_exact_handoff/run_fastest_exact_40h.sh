#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd)"
SRC="$ROOT/source/handoff_network_model_20260312"
OUT="$SRC/result/handoff_fastest_exact_40h"
mkdir -p "$OUT"
cd "$SRC"

export ISLAM_USE_CPP_EVOLVE=1
export ISLAM_CPP_THREADS=0
export ISLAM_USE_CYTHON_NODECHAIN=1
export ISLAM_USE_CYTHON_NODECHAIN_DIRECT_FAST=1
export ISLAM_USE_CYTHON_NODECHAIN_PREBOUND_FAST=1
export ISLAM_CPP_USE_NODECHAIN_DEEP_APPLY=1
export ISLAM_CPP_USE_NODECHAIN_COMMIT_DEEP=1
export ISLAM_USE_CYTHON_ROE_FLUX=1
export ISLAM_CPP_USE_ROE_FLUX_DEEP=1
export ISLAM_CPP_USE_ROE_FLUX_RECT_DEEP=1
export ISLAM_CPP_USE_UPDATE_CELL=1
export ISLAM_CPP_USE_ASSEMBLE=1
export ISLAM_CPP_USE_ASSEMBLE_DEEP=1
export ISLAM_CPP_USE_ROE_MATRIX=1
export ISLAM_CPP_USE_FACE_UC=1
export ISLAM_CPP_USE_GLOBAL_CFL_DEEP=1
export ISLAM_USE_CPP_BRIDGE_DIRECT_DISPATCH=0
export ISLAM_CPP_USE_NODECHAIN_REFRESH_DEEP=0

python tools/profile_cpp_exact_serial.py   --case-name exact_40h_fastest   --summary-json "$OUT/exact_40h_fastest_summary.json"   --perf-json "$OUT/exact_40h_fastest_perf.json"   --output-dir "$OUT/run"   --sim-end-time "2024-01-02 16:00:00"   --use-cpp-evolve   --use-cython-nodechain   --use-cython-nodechain-direct-fast   --use-cython-nodechain-prebound-fast   --use-cpp-nodechain-deep-apply   --use-cpp-nodechain-commit-deep   --use-cython-roe-flux   --use-cpp-roe-flux-deep   --use-cpp-roe-flux-rect-deep   --use-cpp-update-cell   --use-cpp-assemble   --use-cpp-assemble-deep   --use-cpp-roe-matrix   --use-cpp-face-uc   --use-cpp-global-cfl-deep
