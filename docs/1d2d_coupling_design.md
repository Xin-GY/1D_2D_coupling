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
- Sweep artifacts also write `config.json`, `exchange_history.csv`, `mass_balance.csv`, `stage_timeseries_1d.csv`, `stage_timeseries_2d.csv`, `discharge_timeseries.csv`, `crossing_diagnostics.csv`, and `summary_metrics.json` for each case.
- Selected large-interval cases (`15s`, `30s`, `60s`, `300s`) additionally write `stage_diff_vs_reference.csv` on the common `0.5 s` analysis grid for auditability.
- Root-level sweep outputs include `summary_table.csv/json`, `summary_table_mesh.csv/json`, and `timing_breakdown.csv`.

## Testing And Reference Strategy
- `strict_global_min_dt` is treated as the reference solution for interval and scheduler comparisons.
- Default `pytest tests` coverage is no-skip: there is no `skip`, `skipif`, `importorskip`, or `xfail` escape hatch in the active coupling test suite.
- GPU-facing regression tests run against the real ANUGA GPU path in the target conda environment; adapter-only regressions additionally assert that the coupling code never falls back to legacy inlet APIs.
- The experiment sweep is executed through per-case subprocess isolation to prevent cross-case CUDA state contamination when many ANUGA GPU domains are created in one batch.
- Real-GPU scheduler smoke tests also use subprocess isolation because repeated direct GPU domain creation inside a single pytest worker can corrupt CUDA state after failures.

## Audit Metrics
- Arrival time is measured on the raw internal-step `mainstem_mid` probe series by linear threshold-crossing interpolation. The threshold is the reference-case 50% rise level, reused for both reference and candidate.
- `RMSE_stage_vs_reference` and `max_abs_stage_diff_vs_reference` are computed on a common `0.5 s` analysis grid obtained by linearly interpolating each raw stage series.
- `phase_lag_seconds` uses demeaned, normalized cross-correlation on the same grid, with a minimum-overlap guard to prevent edge-only correlations from masquerading as physical phase shifts.
- `peak_stage_error` and `peak_time_error` are taken from the same `mainstem_mid` analysis signal, while `hydrograph_NSE` compares the total exchange hydrograph against the reference.
- `cumulative_mass_error` is the time integral of `|system_mass_error|`, and `normalized_mass_error` divides that integral by `initial_system_volume * simulated_duration`.

## Mesh Sensitivity
- The mesh sweep uses the same mixed bidirectional pulse forcing and strict scheduler for all six mesh variants.
- `aligned/rotated` cases audit orientation sensitivity; `fine/coarse` audit bulk resolution; `narrow/wide corridor` audit river-aware corridor width sensitivity.
- The rotated variants intentionally keep the rotated centerline breakline but disable the rotated river-corridor polygonal refinement band, because that specific `breakline + corridor polygon` combination triggers a low-level `meshpy` failure after rotation. Lateral and frontal refinement polygons remain active, so the rotated cases still exercise breaklines plus interior regions through the production path.

## Known Limits
- `demo/Islam.py` remains untouched and is not used as the runnable coupled entrypoint because this repository does not include its external forcing assets.
- GPU negative-`Q` sink support is assumed and exercised directly through the new `GPUInlet` path; the regression tests are there to catch accidental regressions back to legacy inlet APIs.
- The current mesh builder is intentionally “river-aware” rather than a full GIS preprocessing system.
- The automated sweep uses a deliberately small self-contained river-aware geometry so the real-GPU experiment matrix stays practical in CI and local test runs. It preserves centerline/lateral/direct geometry relationships, but it is still an audit harness rather than a production GIS preprocessing chain.
