# Fastest exact handoff bundle for River_net_parallel

This bundle extracts the **current fastest accepted exact code path** from the repository lineage and packages the source files, build scripts, run scripts, and provenance reports needed for another Codex (or another engineer) to reuse or continue the work.

## Selected upstream state

- Latest accepted exact candidate used for this handoff:
  - branch: `feature/cpp-exact-after-globalcfl-assemble-reaudit-v2`
  - commit: `445c2c9`
- Accepted exact gate:
  - 10m strict compare: pass
  - 2h strict compare: pass
  - 40h strict compare: pass
  - 40h compare: `allclose = true`
- 40h evolve/model time:
  - `47.05382442474365 s`

## What is inside

- `source/handoff_network_model_20260312/`
  - curated source files for the fastest accepted exact path
  - selected upstream reports copied for provenance
- `CODE_APPLICATION_PATHS.md`
  - where the fast path is applied and how the call chain works
- `CHANGELOG_ACCEPTED_PATH.md`
  - what changed compared with earlier accepted baselines
- `HANDOFF_FOR_CODEX.md`
  - concise rules / do-not-reopen list for another Codex
- `build_extensions.sh`
  - build Cython/C++ extensions in the correct order
- `run_fastest_exact_40h.sh`
  - benchmark / reproduce the 40h fastest exact path with the accepted flags
- `fastest_exact_env.example`
  - environment variable template
- `FILE_MANIFEST.md`
  - included file list

## Minimal build steps

From inside `source/handoff_network_model_20260312/`:

```bash
python build_cython_cross_section.py build_ext --inplace
python build_cython_exact_kernels.py build_ext --inplace
python build_cpp_exact_kernels.py build_ext --inplace
```

## Minimal run steps

You can either:

1. use the shell script in the bundle root

```bash
bash run_fastest_exact_40h.sh
```

2. or call the profiler directly

```bash
cd source/handoff_network_model_20260312
python tools/profile_cpp_exact_serial.py   --case-name exact_40h_fastest   --summary-json result/exact_40h_fastest_summary.json   --perf-json result/exact_40h_fastest_perf.json   --output-dir result/exact_40h_fastest   --sim-end-time "2024-01-02 16:00:00"   --use-cpp-evolve   --use-cython-nodechain   --use-cython-nodechain-direct-fast   --use-cython-nodechain-prebound-fast   --use-cpp-nodechain-deep-apply   --use-cpp-nodechain-commit-deep   --use-cython-roe-flux   --use-cpp-roe-flux-deep   --use-cpp-roe-flux-rect-deep   --use-cpp-update-cell   --use-cpp-assemble   --use-cpp-assemble-deep   --use-cpp-roe-matrix   --use-cpp-face-uc   --use-cpp-global-cfl-deep
```

## Python API call path

The runtime entry is:

- `Islam.build_net(export_png=False)`
- `Islam.maybe_run_warmup(net)`
- `Islam.prepare_net_for_evolve(net, yield_step=1800)`
- `Islam.run_prepared_evolve(net, yield_step=1800, print_progress=False)`

The accepted fast exact path is enabled by environment flags before import / configuration.

## Important limits

This bundle intentionally excludes approximate or rejected lines:

- no FAST_MODE
- no external-boundary-deep exact family
- no refresh-deep old variants
- no residual / Jacobian deep primary path
- no fullstep / dispatch reshaping line
- no `-march=native`
- no Python multi-process / multi-thread benchmark path

See `HANDOFF_FOR_CODEX.md` for the detailed no-go list and next-step recommendation.
