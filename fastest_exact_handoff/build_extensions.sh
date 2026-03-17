#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd)"
SRC="$ROOT/source/handoff_network_model_20260312"
cd "$SRC"

python build_cython_cross_section.py build_ext --inplace
python build_cython_exact_kernels.py build_ext --inplace
python build_cpp_exact_kernels.py build_ext --inplace

echo "Build complete in: $SRC"
