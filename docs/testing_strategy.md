# Testing Strategy

## Core Policy
- The active coupling suite is `no skip`: no `pytest.skip`, `skipif`, `importorskip`, or `xfail` is allowed in the target tests.
- The supported 2D coupling path is real ANUGA GPU plus `GPUInlet` fast mode only.
- Any failure in the GPU coupling tests is treated as a code-path or integration bug, not as an expected fallback scenario.

## Test Layers
- Pure logic tests cover scheduler events, link formulas, Picard relaxation, and manager bookkeeping.
- Real GPU integration tests cover:
  - fast-mode-only inlet registration
  - negative-`Q` signed exchange through `gpu_inlets.apply()`
  - real scheduler advancement on coupled 1D-2D cases
  - real frontal-boundary sampling
  - batch sweep artifact generation
  - independent plotting scripts
  - arrival-time interpolation diagnostics
  - mesh-orientation sensitivity sweep
  - timing-breakdown output auditing
- Batch-sweep tests share one session-scoped sweep run so the GPU cost is paid once per pytest session.
- Scheduler smoke tests that would otherwise reuse CUDA state run each mode in a subprocess to avoid GPU state contamination inside one pytest worker.

## GPU Rules
- `mode="fast"` is mandatory for every exchange region and GPU inlet registration.
- Legacy `apply_inlets_gpu()` is never a passing path for coupling tests.
- The sweep runner launches each case in a separate Python subprocess to avoid cross-case CUDA state contamination.

## Reference Metrics
- `strict_global_min_dt` is the reference solution for:
  - `RMSE_stage_vs_reference`
  - `max_abs_stage_diff_vs_reference`
  - `arrival_time_diff_vs_reference`
- `arrival_time_diff_vs_reference` is based on raw probe time series plus linear threshold-crossing interpolation. It never snaps to the nearest exchange time or sample bucket.
- Comparative stage metrics are evaluated on a common `0.5 s` analysis grid built from raw internal-step probe series.
- `phase_lag_seconds` is computed from demeaned, normalized cross-correlation on that common grid, with short-overlap edge lags rejected so the phase metric cannot saturate on one- or two-point overlaps.
- Fixed-interval and `yield_schedule` cases are compared against the reference case with the same coupling type, direction, and waveform family.
