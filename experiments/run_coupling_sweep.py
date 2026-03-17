from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

from experiments.cases import ExperimentCase, generate_case_matrix, generate_mesh_sensitivity_cases
from experiments.io import ensure_dir, read_csv, read_json, write_csv, write_json, write_summary_tables
from experiments.metrics import compute_case_analysis, should_write_stage_diff


def _reference_key(case: ExperimentCase) -> str:
    return f'{case.coupling_type}_{case.direction}_{case.waveform}'


def _reference_payload(case_dir: Path) -> dict[str, object]:
    return {
        'stage_1d_rows': read_csv(case_dir / 'stage_timeseries_1d.csv'),
        'stage_2d_rows': read_csv(case_dir / 'stage_timeseries_2d.csv'),
        'discharge_rows': read_csv(case_dir / 'discharge_timeseries.csv'),
    }


def _rebuild_case_outputs(case: ExperimentCase, output_root: Path, reference_payload: dict[str, object] | None) -> dict[str, object]:
    case_dir = output_root / case.case_name
    previous_summary = read_json(case_dir / 'summary_metrics.json')
    analysis = compute_case_analysis(
        case_name=case.case_name,
        wall_clock_seconds=float(previous_summary['wall_clock_seconds']),
        simulated_duration=case.duration,
        exchange_history=read_csv(case_dir / 'exchange_history.csv'),
        mass_balance_rows=read_csv(case_dir / 'mass_balance.csv'),
        stage_1d_rows=read_csv(case_dir / 'stage_timeseries_1d.csv'),
        stage_2d_rows=read_csv(case_dir / 'stage_timeseries_2d.csv'),
        discharge_rows=read_csv(case_dir / 'discharge_timeseries.csv'),
        reference=reference_payload,
        triangle_count=int(previous_summary.get('triangle_count', 0)),
    )
    write_json(case_dir / 'summary_metrics.json', analysis['summary'])
    write_csv(case_dir / 'crossing_diagnostics.csv', analysis['crossing_diagnostics'])
    if reference_payload is not None and should_write_stage_diff(case.case_name):
        write_csv(case_dir / 'stage_diff_vs_reference.csv', analysis['stage_diff_rows'])
    return analysis['summary']


def _timing_row(case_label: str, case_name: str, case_dir: Path) -> dict[str, object]:
    timing = read_json(case_dir / 'timing_breakdown.json')
    wall_clock = float(read_json(case_dir / 'summary_metrics.json')['wall_clock_seconds'])
    return {
        'case_label': case_label,
        'case_name': case_name,
        'wall_clock_seconds': wall_clock,
        'one_d_advance_time': float(timing['one_d_advance_time']),
        'two_d_gpu_kernel_time': float(timing['two_d_gpu_kernel_time']),
        'boundary_update_time': float(timing['boundary_update_time']),
        'gpu_inlets_apply_time': float(timing['gpu_inlets_apply_time']),
        'scheduler_manager_overhead': float(timing['scheduler_manager_overhead']),
    }


def main(output_root: Path | None = None) -> None:
    output_root = ensure_dir(Path('artifacts') / 'coupling_sweep' if output_root is None else output_root)
    cases = generate_case_matrix()
    mesh_cases = generate_mesh_sensitivity_cases()
    mesh_output_root = ensure_dir(output_root / 'mesh_sensitivity')
    reference_payloads: dict[str, dict[str, object]] = {}
    summary_rows: list[dict[str, object]] = []
    mesh_summary_rows: list[dict[str, object]] = []
    timing_rows: list[dict[str, object]] = []

    strict_cases = [case for case in cases if case.scheduler_mode == 'strict_global_min_dt']
    non_strict_cases = [case for case in cases if case.scheduler_mode != 'strict_global_min_dt']

    ordered_cases = strict_cases + non_strict_cases
    for idx, case in enumerate(ordered_cases, start=1):
        print(f'[{idx}/{len(ordered_cases)}] running {case.case_name}', flush=True)
        try:
            subprocess.run(
                [
                    sys.executable,
                    '-u',
                    '-m',
                    'experiments.run_single_case',
                    case.case_name,
                    '--output-root',
                    str(output_root),
                ],
                check=True,
            )
        except Exception as exc:
            raise RuntimeError(f'Case {case.case_name} failed during sweep execution') from exc

    for idx, case in enumerate(mesh_cases, start=1):
        print(f'[mesh {idx}/{len(mesh_cases)}] running {case.case_name}', flush=True)
        try:
            subprocess.run(
                [
                    sys.executable,
                    '-u',
                    '-m',
                    'experiments.run_single_case',
                    case.case_name,
                    '--output-root',
                    str(mesh_output_root),
                ],
                check=True,
            )
        except Exception as exc:
            raise RuntimeError(f'Mesh case {case.case_name} failed during sweep execution') from exc

    for case in strict_cases:
        key = _reference_key(case)
        reference_payloads[key] = _reference_payload(output_root / case.case_name)
        summary_rows.append(_rebuild_case_outputs(case, output_root, reference_payloads[key]))

    for case in non_strict_cases:
        key = _reference_key(case)
        summary_rows.append(_rebuild_case_outputs(case, output_root, reference_payloads.get(key)))

    mesh_reference = _reference_payload(mesh_output_root / 'aligned_mesh_fine')
    for case in mesh_cases:
        mesh_summary_rows.append(_rebuild_case_outputs(case, mesh_output_root, mesh_reference))

    write_summary_tables(output_root, summary_rows)
    write_csv(output_root / 'summary_table_mesh.csv', mesh_summary_rows)
    write_json(output_root / 'summary_table_mesh.json', mesh_summary_rows)

    timing_case_map = {
        'strict': 'mixed_bidirectional_pulse_strict_global_min_dt',
        'yield': 'mixed_bidirectional_pulse_yield_schedule',
        '3s': 'mixed_bidirectional_pulse_fixed_interval_003s',
        '5s': 'mixed_bidirectional_pulse_fixed_interval_005s',
        '10s': 'mixed_bidirectional_pulse_fixed_interval_010s',
    }
    for label, case_name in timing_case_map.items():
        timing_rows.append(_timing_row(label, case_name, output_root / case_name))
    write_csv(output_root / 'timing_breakdown.csv', timing_rows)

    plot_modules = [
        'scripts.plot_stage_1d_compare',
        'scripts.plot_stage_2d_compare',
        'scripts.plot_q_exchange_compare',
        'scripts.plot_mass_error_compare',
        'scripts.plot_rmse_vs_interval',
        'scripts.plot_peak_stage_error_vs_interval',
        'scripts.plot_arrival_time_error_vs_interval',
        'scripts.plot_phase_lag_vs_interval',
        'scripts.plot_runtime_vs_interval',
        'scripts.plot_coupling_type_compare',
        'scripts.plot_mesh_sensitivity_stage',
        'scripts.plot_mesh_sensitivity_mass',
        'scripts.plot_mesh_sensitivity_runtime',
        'scripts.plot_timing_breakdown',
        'scripts.plot_summary_dashboard',
    ]
    for module_name in plot_modules:
        module = __import__(module_name, fromlist=['main'])
        module.main(output_root)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Run the full 1D-2D coupling sweep.')
    parser.add_argument('--output-root', default=str(Path('artifacts') / 'coupling_sweep'))
    args = parser.parse_args()
    main(Path(args.output_root))
