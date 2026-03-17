# Experiment Matrix

## Scheduler Group
- `mixed_bidirectional_pulse_strict_global_min_dt`
- `mixed_bidirectional_pulse_yield_schedule`
- `mixed_bidirectional_pulse_fixed_interval_001s`
- `mixed_bidirectional_pulse_fixed_interval_003s`
- `mixed_bidirectional_pulse_fixed_interval_005s`
- `mixed_bidirectional_pulse_fixed_interval_010s`
- `mixed_bidirectional_pulse_fixed_interval_015s`
- `mixed_bidirectional_pulse_fixed_interval_030s`
- `mixed_bidirectional_pulse_fixed_interval_060s`
- `mixed_bidirectional_pulse_fixed_interval_300s`

## Coupling-Type Group
- `lateral_only_river_to_floodplain_quasi_steady_strict_global_min_dt`
- `frontal_only_river_to_floodplain_quasi_steady_strict_global_min_dt`
- `mixed_river_to_floodplain_quasi_steady_strict_global_min_dt`

## Direction Group
- `mixed_river_to_floodplain_pulse_strict_global_min_dt`
- `mixed_floodplain_to_river_pulse_strict_global_min_dt`
- `mixed_bidirectional_pulse_strict_global_min_dt`

## Waveform Group
- `mixed_river_to_floodplain_quasi_steady_strict_global_min_dt`
- `mixed_river_to_floodplain_pulse_strict_global_min_dt`
- `mixed_river_to_floodplain_triangle_or_square_strict_global_min_dt`

## Artifacts
- Root directory: `artifacts/coupling_sweep/`
- Per-case files:
  - `config.json`
  - `exchange_history.csv`
  - `mass_balance.csv`
  - `stage_timeseries_1d.csv`
  - `stage_timeseries_2d.csv`
  - `discharge_timeseries.csv`
  - `summary_metrics.json`
- Global summaries:
  - `summary_table.csv`
  - `summary_table.json`
- Plot directory:
  - `artifacts/coupling_sweep/plots/`

## Metrics
- `wall_clock_seconds`
- `simulated_duration`
- `exchange_count`
- `cumulative_exchange_volume`
- `final_total_mass_error`
- `max_abs_mass_error`
- `peak_stage_1d`
- `peak_stage_2d`
- `peak_Q_exchange`
- `RMSE_stage_vs_reference`
- `max_abs_stage_diff_vs_reference`
- `arrival_time_diff_vs_reference`

## Reading The Results
- Start with the scheduler group to compare `yield_schedule` and fixed intervals against `strict_global_min_dt`.
- Use the coupling-type group to separate lateral-only, frontal-only, and mixed behavior.
- Use the direction and waveform groups to see how backflow and transient forcing change exchange magnitudes and timing errors.
- Check runtime plots against RMSE/arrival-time plots to pick a practical interval range for future production cases.
