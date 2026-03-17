from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

from experiments.cases import ExperimentCase, generate_case_matrix
from experiments.io import ensure_dir, read_csv, read_json, write_json, write_summary_tables
from experiments.metrics import compute_summary_metrics


def _reference_key(case: ExperimentCase) -> str:
    return f'{case.coupling_type}_{case.direction}_{case.waveform}'


def _reference_payload(case_dir: Path) -> dict[str, object]:
    return {
        'stage_1d_rows': read_csv(case_dir / 'stage_timeseries_1d.csv'),
        'stage_2d_rows': read_csv(case_dir / 'stage_timeseries_2d.csv'),
        'discharge_rows': read_csv(case_dir / 'discharge_timeseries.csv'),
    }


def _rebuild_case_summary(case: ExperimentCase, output_root: Path, reference_payload: dict[str, object] | None) -> dict[str, object]:
    case_dir = output_root / case.case_name
    summary = compute_summary_metrics(
        case_name=case.case_name,
        wall_clock_seconds=float(read_json(case_dir / 'summary_metrics.json')['wall_clock_seconds']),
        simulated_duration=case.duration,
        exchange_history=read_csv(case_dir / 'exchange_history.csv'),
        mass_balance_rows=read_csv(case_dir / 'mass_balance.csv'),
        stage_1d_rows=read_csv(case_dir / 'stage_timeseries_1d.csv'),
        stage_2d_rows=read_csv(case_dir / 'stage_timeseries_2d.csv'),
        discharge_rows=read_csv(case_dir / 'discharge_timeseries.csv'),
        reference=reference_payload,
    )
    write_json(case_dir / 'summary_metrics.json', summary)
    return summary


def main(output_root: Path | None = None) -> None:
    output_root = ensure_dir(Path('artifacts') / 'coupling_sweep' if output_root is None else output_root)
    cases = generate_case_matrix()
    reference_payloads: dict[str, dict[str, object]] = {}
    summary_rows: list[dict[str, object]] = []

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

    for case in strict_cases:
        key = _reference_key(case)
        reference_payloads[key] = _reference_payload(output_root / case.case_name)
        summary_rows.append(_rebuild_case_summary(case, output_root, reference_payloads[key]))

    for case in non_strict_cases:
        key = _reference_key(case)
        summary_rows.append(_rebuild_case_summary(case, output_root, reference_payloads.get(key)))

    write_summary_tables(output_root, summary_rows)

    plot_modules = [
        'scripts.plot_stage_1d_compare',
        'scripts.plot_stage_2d_compare',
        'scripts.plot_q_exchange_compare',
        'scripts.plot_mass_error_compare',
        'scripts.plot_rmse_vs_interval',
        'scripts.plot_peak_stage_error_vs_interval',
        'scripts.plot_arrival_time_error_vs_interval',
        'scripts.plot_runtime_vs_interval',
        'scripts.plot_coupling_type_compare',
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
