# 1D-2D Coupling Design

## Architecture
- `OneDNetworkAdapter` wraps the existing `Rivernet`/`River` solver without rewriting Roe fluxes or source terms.
- `TwoDAnugaGpuAdapter` wraps the new ANUGA GPU stepping order from `demo/demo.py`.
- `CouplingManager` owns the simulation loop and delegates exchange timing to `ExchangeScheduler`.
- `LateralWeirLink` handles lateral mass exchange with a broad-crested weir formula.
- `FrontalBoundaryLink` handles direct boundary coupling with `Q from 1D` and `stage from 2D`.

## Time Control
- `strict_global_min_dt`: both sides use the same minimum CFL step and exchange every micro-step.
- `yield_schedule`: exchange times are the sorted union of 1D and 2D checkpoint/yield events.
- `fixed_interval`: exchange is frozen over a user-specified interval and both solvers subcycle internally.
- All modes use `TIME_EPS = 1e-12` and clip the last sub-step to hit the event exactly.

## Exchange Rules
- Global sign convention: `Q_exchange > 0` means `1D -> 2D`.
- Lateral links conserve mass exactly and leave momentum handling to the native 1D/2D solvers.
- The coupling path is fast-mode only: `domain.gpu_inlets.add_inlet(..., mode="fast")` plus `domain.gpu_inlets.apply()` is the only supported 2D exchange route.
- Negative `Q`/suction depends on the new `GPUInlet` signed-volume semantics. Legacy `apply_inlets_gpu()` is explicitly excluded from the coupling path.
- Frontal links use dynamic `Time_boundary` objects on the 2D side because the GPU boundary updater currently supports `Reflective`, `Transmissive`, and `Time_boundary`.
- Subcritical frontal mode applies both `Q from 1D` and `stage from 2D`; supercritical modes drop one side to avoid over-constraint.
- Picard iterations are limited to 1-3 fixed-point corrections and rely on explicit 1D/2D snapshots plus GPU state restore.

## Diagnostics
- `coupling_exchange_history.csv`: per-link `eta_1d`, `eta_2d`, `Q_exchange`, `dV_exchange`, `cumulative_dV`, `mode`, `iteration_count`.
- `coupling_dt_history.csv`: exchange time and interval history.
- `coupling_mass_balance.csv`: 1D, 2D, and system volume summaries over time.
- Sweep artifacts also write `config.json`, `exchange_history.csv`, `mass_balance.csv`, `stage_timeseries_1d.csv`, `stage_timeseries_2d.csv`, `discharge_timeseries.csv`, and `summary_metrics.json` for each case.

## Testing And Reference Strategy
- `strict_global_min_dt` is treated as the reference solution for interval and scheduler comparisons.
- Default `pytest tests` coverage is no-skip: there is no `skip`, `skipif`, `importorskip`, or `xfail` escape hatch in the active coupling test suite.
- GPU-facing regression tests run against the real ANUGA GPU path in the target conda environment; adapter-only regressions additionally assert that the coupling code never falls back to legacy inlet APIs.
- The experiment sweep is executed through per-case subprocess isolation to prevent cross-case CUDA state contamination when many ANUGA GPU domains are created in one batch.

## Known Limits
- `demo/Islam.py` remains untouched and is not used as the runnable coupled entrypoint because this repository does not include its external forcing assets.
- GPU negative-`Q` sink support is assumed and exercised directly through the new `GPUInlet` path; the regression tests are there to catch accidental regressions back to legacy inlet APIs.
- The current mesh builder is intentionally “river-aware” rather than a full GIS preprocessing system.
- The automated sweep uses a deliberately small self-contained river-aware geometry so the real-GPU experiment matrix stays practical in CI and local test runs. It preserves centerline/lateral/direct geometry relationships, but it does not yet turn every breakline/refinement polygon into the production sweep mesh.
