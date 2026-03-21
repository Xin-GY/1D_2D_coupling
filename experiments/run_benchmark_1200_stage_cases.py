from __future__ import annotations

import argparse
from dataclasses import replace
from pathlib import Path

from experiments.chapter_cases import generate_test7_cases, prepare_chapter_case
from experiments.chapter_runner import run_chapter_case
from experiments.io import ensure_dir, read_json, write_json
from experiments.test7_data import Test7DataProvenance

SELECTED_SUFFIXES = [
    'strict_global_min_dt',
    'fixed_interval_002s',
    'fixed_interval_005s',
    'fixed_interval_015s',
    'fixed_interval_060s',
    'fixed_interval_300s',
]
DEFAULT_SNAPSHOT_TIMES = [300.0, 600.0, 900.0, 1200.0]


def _load_provenance(path: Path) -> Test7DataProvenance:
    payload = read_json(path)
    return Test7DataProvenance(**payload)


def _prepare_with_snapshot_times(snapshot_times: list[float]):
    def _inner(case, output_dir: Path):
        prepared = prepare_chapter_case(case, output_dir)
        prepared['snapshot_times'] = list(snapshot_times)
        prepared['config_payload']['snapshot_times'] = list(snapshot_times)
        return prepared

    return _inner


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description='Rerun the benchmark composite case for 1200 s with selected intervals only.')
    parser.add_argument('--output-root', default='artifacts/chapter_case_reruns/benchmark_1200_legacy')
    parser.add_argument('--provenance-json', default='artifacts/chapter_coupling_analysis/logs/test7_provenance.json')
    parser.add_argument('--duration', type=float, default=1200.0)
    parser.add_argument('--one-d-backend', default='legacy')
    parser.add_argument('--mesh-variant', default='baseline')
    parser.add_argument('--snapshot-times', nargs='*', type=float, default=DEFAULT_SNAPSHOT_TIMES)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    output_root = ensure_dir(Path(args.output_root))
    provenance = _load_provenance(Path(args.provenance_json))
    all_cases = generate_test7_cases(provenance, profile='paper')
    selected_names = {f'{provenance.case_variant}_{suffix}' for suffix in SELECTED_SUFFIXES}
    cases = []
    for case in all_cases:
        if case.case_name not in selected_names:
            continue
        cases.append(
            replace(
                case,
                duration=float(args.duration),
                one_d_backend=str(args.one_d_backend),
                mesh_variant=str(args.mesh_variant),
            )
        )
    if not cases:
        raise RuntimeError('No selected benchmark cases were found for rerun')

    logs_dir = ensure_dir(output_root / 'logs')
    write_json(
        logs_dir / 'rerun_manifest.json',
        {
            'output_root': str(output_root),
            'duration': float(args.duration),
            'one_d_backend': str(args.one_d_backend),
            'mesh_variant': str(args.mesh_variant),
            'snapshot_times': [float(item) for item in args.snapshot_times],
            'selected_cases': [case.case_name for case in cases],
            'provenance': provenance.to_payload(),
        },
    )

    prepare_case = _prepare_with_snapshot_times([float(item) for item in args.snapshot_times])
    for case in cases:
        print(f'[benchmark_1200_rerun] running {case.case_name} duration={case.duration} backend={case.one_d_backend}')
        run_chapter_case(case, output_root, prepare_case, reference=None)


if __name__ == '__main__':
    main()
