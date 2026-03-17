from __future__ import annotations

import argparse
from pathlib import Path

from coupling.runtime_env import repair_anuga_editable_build_env

repair_anuga_editable_build_env()

from experiments.backend_timing import write_one_d_backend_timing_comparison
from experiments.chapter_cases import generate_test7_cases
from experiments.chapter_suite import run_chapter_analysis
from experiments.test7_data import resolve_test7_data


def _selected_case_names(profile: str, provenance_case_variant: str) -> set[str]:
    benchmark_names = {
        f'{provenance_case_variant}_strict_global_min_dt',
        f'{provenance_case_variant}_yield_schedule',
        f'{provenance_case_variant}_fixed_interval_002s',
        f'{provenance_case_variant}_fixed_interval_003s',
        f'{provenance_case_variant}_fixed_interval_005s',
        f'{provenance_case_variant}_fixed_interval_010s',
        f'{provenance_case_variant}_fixed_interval_015s',
        f'{provenance_case_variant}_fixed_interval_030s',
        f'{provenance_case_variant}_fixed_interval_060s',
        f'{provenance_case_variant}_fixed_interval_300s',
    }
    small_names = {
        'frontal_basin_fill_strict_global_min_dt',
        'lateral_overtopping_return_strict_global_min_dt',
        'early_arrival_pulse_strict_global_min_dt',
        'regime_switch_backwater_or_mixed_strict_global_min_dt',
        'early_arrival_pulse_fixed_interval_005s',
        'frontal_basin_fill_fixed_interval_015s',
        'lateral_overtopping_return_fixed_interval_015s',
        'early_arrival_pulse_fixed_interval_015s',
        'regime_switch_backwater_or_mixed_fixed_interval_015s',
    }
    return benchmark_names | small_names


def main() -> None:
    parser = argparse.ArgumentParser(description='Run the selected fastest-exact chapter refresh cases.')
    parser.add_argument(
        '--output-root',
        default=str(Path('artifacts') / 'chapter_coupling_analysis_fastest_exact'),
    )
    parser.add_argument('--profile', default='paper', choices=['paper', 'test'])
    parser.add_argument('--disable-download', action='store_true')
    args = parser.parse_args()

    output_root = Path(args.output_root)
    provenance = resolve_test7_data(output_root / 'logs' / 'test7_cache', allow_download=not bool(args.disable_download))
    run_chapter_analysis(
        output_root=output_root,
        profile=args.profile,
        include_test7=True,
        include_small=True,
        allow_download=not bool(args.disable_download),
        run_mesh=False,
        generate_plots=True,
        selected_case_names=_selected_case_names(args.profile, provenance.case_variant),
        default_one_d_backend='fastest_exact',
        default_mesh_variant='refined_figures',
    )
    write_one_d_backend_timing_comparison(
        output_root,
        provenance,
        profile=args.profile,
        mesh_variant='refined_figures',
    )


if __name__ == '__main__':
    main()
