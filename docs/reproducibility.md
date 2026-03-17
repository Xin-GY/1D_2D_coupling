# Reproducibility

## Environment
- Conda environment:
  - `/home/xin/miniconda3/envs/anuga_GPU_sync_audit`
- 2D path:
  - ANUGA GPU fast mode only
- Supported exchange path:
  - `domain.gpu_inlets.add_inlet(..., mode="fast")`
  - `domain.gpu_inlets.apply()`

## Runtime Assumptions
- 当前 chapter 分析默认依赖真实 GPU。
- 在受限沙箱环境中，CuPy 可能无法枚举 GPU；此时需要在可访问 GPU 的非沙箱上下文中运行。
- 这不改变仓库实现约束：代码路径仍然只允许新版 fast-mode GPU inlet。
- 当前环境中的 `anuga` 采用 editable 安装，仓库运行时会在 `import anuga` 之前自动修复 meson-python 临时 build-env 的 `ninja/meson/cython/numpy include` 链接，避免 standalone wrapper 因失效的 `/tmp/pip-build-env...` 路径而失败。
- 对于这台机器，真实 GPU 运行仍建议保留已有的用户级 CuPy kernel cache：
  - `~/.cupy/kernel_cache`
  - 这样 chapter 子进程不会被不必要的冷编译拖慢。

## Main Commands
- Build the `fastest_exact_handoff` extensions:
```bash
/home/xin/miniconda3/envs/anuga_GPU_sync_audit/bin/python fastest_exact_handoff/source/handoff_network_model_20260312/build_cython_cross_section.py build_ext --inplace
/home/xin/miniconda3/envs/anuga_GPU_sync_audit/bin/python fastest_exact_handoff/source/handoff_network_model_20260312/build_cython_exact_kernels.py build_ext --inplace
/home/xin/miniconda3/envs/anuga_GPU_sync_audit/bin/python fastest_exact_handoff/source/handoff_network_model_20260312/build_cpp_exact_kernels.py build_ext --inplace
```
- Chapter total analysis:
```bash
/home/xin/miniconda3/envs/anuga_GPU_sync_audit/bin/python -m experiments.run_coupling_sweep --suite chapter
```
- Fastest-exact chapter A/B refresh:
```bash
/home/xin/miniconda3/envs/anuga_GPU_sync_audit/bin/python -m experiments.run_fastest_exact_refresh --profile test --disable-download --output-root artifacts/chapter_coupling_analysis_fastest_exact
```
- Test 7 suite only:
```bash
/home/xin/miniconda3/envs/anuga_GPU_sync_audit/bin/python -m experiments.run_test7_suite
```
- Small mechanism suite only:
```bash
/home/xin/miniconda3/envs/anuga_GPU_sync_audit/bin/python -m experiments.run_small_mechanism_suite
```
- Legacy sweep retained for regression:
```bash
/home/xin/miniconda3/envs/anuga_GPU_sync_audit/bin/python -m experiments.run_coupling_sweep --suite legacy
```

## Artifact Layout
- `artifacts/chapter_coupling_analysis/cases/`
- `artifacts/chapter_coupling_analysis/summaries/`
- `artifacts/chapter_coupling_analysis/plots/`
- `artifacts/chapter_coupling_analysis/tables/`
- `artifacts/chapter_coupling_analysis/logs/`
- `artifacts/chapter_coupling_analysis_fastest_exact/cases/`
- `artifacts/chapter_coupling_analysis_fastest_exact/summaries/`
- `artifacts/chapter_coupling_analysis_fastest_exact/plots/`
- `artifacts/chapter_coupling_analysis_fastest_exact/tables/`
- `artifacts/chapter_coupling_analysis_fastest_exact/logs/`

## Deterministic Policies
- `strict_global_min_dt` is the reference policy.
- Arrival-time metrics use linear threshold-crossing interpolation.
- Comparative series metrics are evaluated on a common analysis grid.
- Plot scripts read only from artifacts, so figures are reproducible from saved CSV/JSON outputs.

## Plot Regeneration Without `.msh`
- Chapter-level 2D figures no longer depend on untracked `.msh` files at redraw time.
- Each chapter case now carries a committed `plot_cache/` directory containing:
  - `mesh_geometry.npz`
  - `mesh_geometry.json`
- The cache stores the lightweight plotting geometry needed for paper figures:
  - vertices
  - triangles / connectivity
  - bounds
  - centroids
  - basic segment / neighbor metadata
- Plotting code resolves geometry in this order:
  - existing `plot_cache`
  - local `.msh` only for one-time cache export
  - otherwise fail-fast with a clear geometry-missing error
- This means a fresh clone can redraw the chapter figures from the tracked artifacts alone, without recovering ignored mesh files.

## Fastest-Exact Backend Notes
- The default 1D backend for new coupling/chapter runs is now:
  - `fastest_exact`
- The legacy backend is still available for A/B timing and regression via:
  - `--one-d-backend legacy`
- The backend swap contract is documented in:
  - `docs/fastest_exact_call_chain_audit.md`
- The fastest-exact chapter refresh writes an additional timing table:
  - `artifacts/chapter_coupling_analysis_fastest_exact/summaries/one_d_backend_timing.csv`
  - This table compares legacy vs fastest-exact on a 1D-only benchmark strict case.

## Refreshing Chapter Plots Only
- To refresh chapter figures, manifests, plot QA, and geometry caches without rerunning chapter simulations:
```bash
/home/xin/miniconda3/envs/anuga_GPU_sync_audit/bin/python -m experiments.refresh_chapter_plots --output-root artifacts/chapter_coupling_analysis
```
- This command:
  - exports any missing `plot_cache` from locally available `.msh` once;
  - redraws chapter plots from existing artifacts only;
  - writes `logs/blank_plot_audit.csv/json`;
  - updates `summaries/figure_manifest.csv` with geometry/render/blank-check metadata.

## Plot QA
- Blank / near-blank auditing is part of the plotting toolchain.
- The chapter artifact log directory now includes:
  - `blank_plot_audit_before.csv/json`
  - `blank_plot_audit.csv/json`
  - `plot_geometry_cache_index.csv/json`
- The 2D chapter figures are expected to use full-mesh face coloring with gray mesh edges, rather than centroid scatter or point-only flood-front overlays.
