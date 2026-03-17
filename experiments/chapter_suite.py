from __future__ import annotations

import argparse
import subprocess
import sys
from dataclasses import replace
from pathlib import Path
from typing import Any

from experiments.cases import generate_mesh_sensitivity_cases
from experiments.chapter_cases import ChapterExperimentCase, generate_small_mechanism_cases, generate_test7_cases
from experiments.chapter_metrics import rebuild_chapter_case_outputs
from experiments.io import ensure_dir, read_csv, read_json, write_csv, write_json
from experiments.chapter_plotting import refresh_chapter_plot_outputs
from experiments.metrics import compute_case_analysis
from experiments.test7_data import Test7DataProvenance, resolve_test7_data


CHAPTER_PLOT_SPECS: list[dict[str, str]] = [
    {
        'figure_id': 'Fig-CTD-01',
        'module_name': 'scripts.plot_coupling_schematic',
        'output_png_path': 'plots/coupling_schematic.png',
        'input_data_paths': 'cases/*/config.json',
        'caption_draft_cn': '图示 frontal、lateral 与 mixed 三类 1D–2D 耦合接口。',
        'caption_draft_en': 'Schematic view of frontal, lateral, and mixed 1D–2D coupling modes.',
        'chapter_section': '8.1',
    },
    {
        'figure_id': 'Fig-CTD-02',
        'module_name': 'scripts.plot_test7_geometry_and_mesh',
        'output_png_path': 'plots/test7_geometry_and_mesh.png',
        'input_data_paths': 'cases/*test7*_strict_global_min_dt/geometry.json; cases/*test7*_strict_global_min_dt/two_d_field_summary.csv',
        'caption_draft_cn': 'Test 7 overtopping-only 变体的 1D 河道、2D 洪泛区、分区与网格示意。',
        'caption_draft_en': 'Geometry and mesh for the overtopping-only Test 7 variant, including river, floodplain partitions, and 2D centroids.',
        'chapter_section': '8.1',
    },
    {
        'figure_id': 'Fig-CTD-03',
        'module_name': 'scripts.plot_scheduler_timeline_schematic',
        'output_png_path': 'plots/scheduler_timeline_schematic.png',
        'input_data_paths': 'summaries/summary_table.csv',
        'caption_draft_cn': 'strict、yield 与 fixed-interval 调度的 exchange 时序示意。',
        'caption_draft_en': 'Schematic exchange timelines for strict, yield-schedule, and fixed-interval coupling.',
        'chapter_section': '8.1',
    },
    {
        'figure_id': 'Fig-CTD-04',
        'module_name': 'scripts.plot_stage_hydrographs_1d',
        'output_png_path': 'plots/stage_hydrographs_1d.png',
        'input_data_paths': 'cases/*test7*/stage_timeseries_1d.csv; summaries/summary_table.csv',
        'caption_draft_cn': '大算例代表性 1D 断面的水位过程线比较。',
        'caption_draft_en': 'Comparison of stage hydrographs at representative 1D sections for the benchmark case.',
        'chapter_section': '8.2',
    },
    {
        'figure_id': 'Fig-CTD-05',
        'module_name': 'scripts.plot_discharge_hydrographs_1d',
        'output_png_path': 'plots/discharge_hydrographs_1d.png',
        'input_data_paths': 'cases/*test7*/discharge_timeseries.csv; summaries/summary_table.csv',
        'caption_draft_cn': '大算例代表性 1D 断面的流量过程线比较。',
        'caption_draft_en': 'Comparison of discharge hydrographs at representative 1D sections for the benchmark case.',
        'chapter_section': '8.2',
    },
    {
        'figure_id': 'Fig-CTD-06',
        'module_name': 'scripts.plot_xt_stage_river',
        'output_png_path': 'plots/xt_stage_river.png',
        'input_data_paths': 'cases/*test7*_strict_global_min_dt/river_profile_stage.csv',
        'caption_draft_cn': '沿主河道的 x–t 水位图。',
        'caption_draft_en': 'x–t stage diagram along the benchmark river corridor.',
        'chapter_section': '8.2',
    },
    {
        'figure_id': 'Fig-CTD-07',
        'module_name': 'scripts.plot_xt_discharge_river',
        'output_png_path': 'plots/xt_discharge_river.png',
        'input_data_paths': 'cases/*test7*_strict_global_min_dt/river_profile_discharge.csv',
        'caption_draft_cn': '沿主河道的 x–t 流量图。',
        'caption_draft_en': 'x–t discharge diagram along the benchmark river corridor.',
        'chapter_section': '8.2',
    },
    {
        'figure_id': 'Fig-CTD-08',
        'module_name': 'scripts.plot_exchange_q_timeseries',
        'output_png_path': 'plots/exchange_q_timeseries.png',
        'input_data_paths': 'cases/*test7*_fixed_interval_015s/exchange_link_timeseries.csv',
        'caption_draft_cn': '代表性 links 的交换流量过程线。',
        'caption_draft_en': 'Exchange discharge time series for representative lateral and frontal links.',
        'chapter_section': '8.3',
    },
    {
        'figure_id': 'Fig-CTD-09',
        'module_name': 'scripts.plot_exchange_deta_timeseries',
        'output_png_path': 'plots/exchange_deta_timeseries.png',
        'input_data_paths': 'cases/*test7*_fixed_interval_015s/exchange_link_timeseries.csv',
        'caption_draft_cn': '代表性 links 的水位差过程线。',
        'caption_draft_en': 'Time series of water-level difference across representative exchange links.',
        'chapter_section': '8.3',
    },
    {
        'figure_id': 'Fig-CTD-10',
        'module_name': 'scripts.plot_exchange_volume_cumulative',
        'output_png_path': 'plots/exchange_volume_cumulative.png',
        'input_data_paths': 'cases/*test7*_fixed_interval_015s/exchange_link_timeseries.csv',
        'caption_draft_cn': '累计交换体积曲线。',
        'caption_draft_en': 'Cumulative exchanged-volume curves for representative links.',
        'chapter_section': '8.3',
    },
    {
        'figure_id': 'Fig-CTD-11',
        'module_name': 'scripts.plot_exchange_event_alignment',
        'output_png_path': 'plots/exchange_event_alignment.png',
        'input_data_paths': 'cases/*test7*_fixed_interval_015s/exchange_link_timeseries.csv; cases/*test7*_fixed_interval_015s/crossing_diagnostics.csv',
        'caption_draft_cn': '首次 exchange 与关键到达时刻对齐诊断。',
        'caption_draft_en': 'Diagnostic alignment between the first exchange event and the key arrival threshold crossing.',
        'chapter_section': '8.3',
    },
    {
        'figure_id': 'Fig-CTD-12',
        'module_name': 'scripts.plot_2d_snapshots_depth',
        'output_png_path': 'plots/2d_snapshots_depth.png',
        'input_data_paths': 'cases/*test7*/two_d_snapshots.csv',
        'caption_draft_cn': '关键时刻 2D 水深快照对比。',
        'caption_draft_en': 'Side-by-side 2D depth snapshots at representative times.',
        'chapter_section': '8.4',
    },
    {
        'figure_id': 'Fig-CTD-13',
        'module_name': 'scripts.plot_2d_snapshots_velocity',
        'output_png_path': 'plots/2d_snapshots_velocity.png',
        'input_data_paths': 'cases/*test7*/two_d_snapshots.csv',
        'caption_draft_cn': '关键时刻 2D 流速快照对比。',
        'caption_draft_en': 'Side-by-side 2D velocity snapshots at representative times.',
        'chapter_section': '8.4',
    },
    {
        'figure_id': 'Fig-CTD-14',
        'module_name': 'scripts.plot_2d_max_depth_map',
        'output_png_path': 'plots/2d_max_depth_map.png',
        'input_data_paths': 'cases/*test7*_strict_global_min_dt/two_d_field_summary.csv',
        'caption_draft_cn': '参考解的最大水深空间分布。',
        'caption_draft_en': 'Maximum-depth map for the benchmark reference solution.',
        'chapter_section': '8.4',
    },
    {
        'figure_id': 'Fig-CTD-15',
        'module_name': 'scripts.plot_2d_arrival_time_map',
        'output_png_path': 'plots/2d_arrival_time_map.png',
        'input_data_paths': 'cases/*test7*_strict_global_min_dt/two_d_field_summary.csv',
        'caption_draft_cn': '参考解的到达时间空间分布。',
        'caption_draft_en': 'Arrival-time map for the benchmark reference solution.',
        'chapter_section': '8.4',
    },
    {
        'figure_id': 'Fig-CTD-16',
        'module_name': 'scripts.plot_2d_difference_map',
        'output_png_path': 'plots/2d_difference_map.png',
        'input_data_paths': 'cases/*test7*_strict_global_min_dt/two_d_field_summary.csv; cases/*test7*_fixed_interval_015s/two_d_field_summary.csv',
        'caption_draft_cn': '固定交换间隔相对参考解的 2D 差值图。',
        'caption_draft_en': '2D difference map of a fixed-interval case against the benchmark reference.',
        'chapter_section': '8.4',
    },
    {
        'figure_id': 'Fig-CTD-17',
        'module_name': 'scripts.plot_flood_front_overlay',
        'output_png_path': 'plots/flood_front_overlay.png',
        'input_data_paths': 'cases/*test7*_strict_global_min_dt/two_d_snapshots.csv; cases/*test7*_fixed_interval_015s/two_d_snapshots.csv',
        'caption_draft_cn': '不同策略下洪泛前沿线的叠置比较。',
        'caption_draft_en': 'Overlay of flood-front positions for the reference and fixed-interval solutions.',
        'chapter_section': '8.4',
    },
    {
        'figure_id': 'Fig-CTD-18',
        'module_name': 'scripts.plot_rmse_vs_interval',
        'output_png_path': 'plots/rmse_vs_interval.png',
        'input_data_paths': 'summaries/summary_table.csv',
        'caption_draft_cn': '交换间隔与 1D 水位 RMSE 的关系。',
        'caption_draft_en': 'Relationship between exchange interval and 1D stage RMSE.',
        'chapter_section': '8.5',
    },
    {
        'figure_id': 'Fig-CTD-19',
        'module_name': 'scripts.plot_peak_error_vs_interval',
        'output_png_path': 'plots/peak_error_vs_interval.png',
        'input_data_paths': 'summaries/summary_table.csv',
        'caption_draft_cn': '交换间隔与峰值误差的关系。',
        'caption_draft_en': 'Relationship between exchange interval and peak-stage / peak-discharge errors.',
        'chapter_section': '8.5',
    },
    {
        'figure_id': 'Fig-CTD-20',
        'module_name': 'scripts.plot_arrival_time_error_vs_interval',
        'output_png_path': 'plots/arrival_time_error_vs_interval.png',
        'input_data_paths': 'summaries/summary_table.csv',
        'caption_draft_cn': '交换间隔与到达时间误差的关系。',
        'caption_draft_en': 'Relationship between exchange interval and arrival-time error.',
        'chapter_section': '8.5',
    },
    {
        'figure_id': 'Fig-CTD-21',
        'module_name': 'scripts.plot_phase_lag_vs_interval',
        'output_png_path': 'plots/phase_lag_vs_interval.png',
        'input_data_paths': 'summaries/summary_table.csv',
        'caption_draft_cn': '交换间隔与相位滞后的关系。',
        'caption_draft_en': 'Relationship between exchange interval and phase lag.',
        'chapter_section': '8.5',
    },
    {
        'figure_id': 'Fig-CTD-22',
        'module_name': 'scripts.plot_interval_normalized_axes',
        'output_png_path': 'plots/interval_normalized_axes.png',
        'input_data_paths': 'summaries/summary_table.csv',
        'caption_draft_cn': '以 Δt_ex/t_arr_ref 与 Δt_ex/t_rise_ref 为横轴的归一化误差图。',
        'caption_draft_en': 'Normalized error plot using Δt_ex/t_arr_ref and Δt_ex/t_rise_ref as abscissae.',
        'chapter_section': '8.5',
    },
    {
        'figure_id': 'Fig-CTD-23',
        'module_name': 'scripts.plot_cost_share_stacked',
        'output_png_path': 'plots/cost_share_stacked.png',
        'input_data_paths': 'summaries/timing_breakdown.csv',
        'caption_draft_cn': '不同策略下的计算成本占比。',
        'caption_draft_en': 'Stacked cost-share breakdown across coupling strategies.',
        'chapter_section': '8.5',
    },
    {
        'figure_id': 'Fig-CTD-24',
        'module_name': 'scripts.plot_relative_cost_vs_accuracy',
        'output_png_path': 'plots/relative_cost_vs_accuracy.png',
        'input_data_paths': 'summaries/summary_table.csv; summaries/timing_breakdown.csv',
        'caption_draft_cn': '相对成本指数与误差指标的折中关系。',
        'caption_draft_en': 'Trade-off between relative cost ratio and accuracy indicators.',
        'chapter_section': '8.5',
    },
    {
        'figure_id': 'Fig-CTD-25',
        'module_name': 'scripts.plot_floodplain_partition_compare',
        'output_png_path': 'plots/floodplain_partition_compare.png',
        'input_data_paths': 'summaries/summary_table_test7_partitions.csv',
        'caption_draft_cn': 'Floodplain 1/2/3 分区误差对比。',
        'caption_draft_en': 'Partition-wise comparison across Floodplain 1, 2, and 3.',
        'chapter_section': '8.5',
    },
    {
        'figure_id': 'Fig-CTD-26',
        'module_name': 'scripts.plot_summary_dashboard',
        'output_png_path': 'plots/summary_dashboard.png',
        'input_data_paths': 'summaries/summary_table.csv; summaries/timing_breakdown.csv',
        'caption_draft_cn': '耦合时间离散分析的总览仪表板。',
        'caption_draft_en': 'Summary dashboard for the coupling time-discretization analysis.',
        'chapter_section': '8.5',
    },
]


def chapter_dirs(root: Path) -> dict[str, Path]:
    root = ensure_dir(root)
    return {
        'root': root,
        'cases': ensure_dir(root / 'cases'),
        'summaries': ensure_dir(root / 'summaries'),
        'plots': ensure_dir(root / 'plots'),
        'tables': ensure_dir(root / 'tables'),
        'logs': ensure_dir(root / 'logs'),
    }


def _write_table(outputs: dict[str, Path], stem: str, rows: list[dict[str, Any]]) -> None:
    write_csv(outputs['summaries'] / f'{stem}.csv', rows)
    write_json(outputs['summaries'] / f'{stem}.json', rows)
    write_csv(outputs['tables'] / f'{stem}.csv', rows)
    write_json(outputs['tables'] / f'{stem}.json', rows)


def _write_root_table(outputs: dict[str, Path], stem: str, rows: list[dict[str, Any]]) -> None:
    write_csv(outputs['root'] / f'{stem}.csv', rows)
    write_json(outputs['root'] / f'{stem}.json', rows)


def _run_case_subprocess(
    case: ChapterExperimentCase,
    outputs: dict[str, Path],
    provenance_path: Path,
    profile: str,
    *,
    one_d_backend: str | None = None,
    mesh_variant: str | None = None,
) -> None:
    command = [
        sys.executable,
        '-u',
        '-m',
        'experiments.run_single_case',
        case.case_name,
        '--registry',
        'chapter',
        '--profile',
        profile,
        '--chapter-provenance',
        str(provenance_path),
        '--output-root',
        str(outputs['root']),
    ]
    if one_d_backend is not None:
        command.extend(['--one-d-backend', one_d_backend])
    if mesh_variant is not None:
        command.extend(['--mesh-variant', mesh_variant])
    subprocess.run(command, check=True)


def _timing_row(case: ChapterExperimentCase, case_dir: Path) -> dict[str, Any]:
    timing = read_json(case_dir / 'timing_breakdown.json')
    wall = float(timing.get('wall_clock_seconds', 0.0))
    one_d = float(timing.get('one_d_advance_time', 0.0))
    two_d = float(timing.get('two_d_gpu_kernel_time', 0.0))
    boundary = float(timing.get('boundary_update_time', 0.0))
    coupling = float(timing.get('scheduler_manager_overhead', 0.0))
    inlets = float(timing.get('gpu_inlets_apply_time', 0.0))
    misc = max(wall - one_d - two_d - boundary - coupling - inlets, 0.0)
    denominator = max(wall, 1.0e-9)
    return {
        'case_name': case.case_name,
        'scenario_family': case.scenario_family,
        'one_d_backend': case.one_d_backend,
        'mesh_variant': case.mesh_variant,
        'wall_clock_seconds': wall,
        'one_d_advance_time': one_d,
        'two_d_gpu_kernel_time': two_d,
        'boundary_update_time': boundary,
        'exchange_manager_time': coupling + inlets,
        'misc_io_time': misc,
        'one_d_share': one_d / denominator,
        'two_d_share': two_d / denominator,
        'boundary_share': boundary / denominator,
        'exchange_manager_share': (coupling + inlets) / denominator,
        'misc_io_share': misc / denominator,
    }


def _mesh_reference_payload(case_dir: Path) -> dict[str, Any]:
    return {
        'stage_1d_rows': read_csv(case_dir / 'stage_timeseries_1d.csv'),
        'stage_2d_rows': read_csv(case_dir / 'stage_timeseries_2d.csv'),
        'discharge_rows': read_csv(case_dir / 'discharge_timeseries.csv'),
    }


def _run_mesh_cases(outputs: dict[str, Path]) -> list[dict[str, Any]]:
    mesh_root = ensure_dir(outputs['root'] / 'mesh_sensitivity')
    mesh_cases = generate_mesh_sensitivity_cases()
    for idx, case in enumerate(mesh_cases, start=1):
        print(f'[chapter mesh {idx}/{len(mesh_cases)}] running {case.case_name}', flush=True)
        subprocess.run(
            [
                sys.executable,
                '-u',
                '-m',
                'experiments.run_single_case',
                case.case_name,
                '--output-root',
                str(mesh_root),
            ],
            check=True,
        )
    reference_payload = _mesh_reference_payload(mesh_root / 'aligned_mesh_fine')
    summary_rows: list[dict[str, Any]] = []
    for case in mesh_cases:
        case_dir = mesh_root / case.case_name
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
        summary_rows.append(analysis['summary'])
    _write_table(outputs, 'summary_table_mesh', summary_rows)
    _write_root_table(outputs, 'summary_table_mesh', summary_rows)
    return summary_rows


def _reference_dirs(cases: list[ChapterExperimentCase], outputs: dict[str, Path]) -> dict[str, Path]:
    refs: dict[str, Path] = {}
    for case in cases:
        if case.scheduler_mode != 'strict_global_min_dt':
            continue
        refs[case.scenario_family] = outputs['cases'] / case.case_name
    return refs


def _aggregate_chapter_tables(cases: list[ChapterExperimentCase], outputs: dict[str, Path]) -> dict[str, list[dict[str, Any]]]:
    refs = _reference_dirs(cases, outputs)
    summary_rows: list[dict[str, Any]] = []
    small_rows: list[dict[str, Any]] = []
    partition_rows: list[dict[str, Any]] = []
    exchange_rows: list[dict[str, Any]] = []
    timing_rows: list[dict[str, Any]] = []
    for case in cases:
        case_dir = outputs['cases'] / case.case_name
        reference_dir = refs.get(case.scenario_family)
        rebuilt = rebuild_chapter_case_outputs(case_dir, reference_dir=reference_dir)
        write_json(case_dir / 'summary_metrics.json', rebuilt['summary'])
        write_csv(case_dir / 'crossing_diagnostics.csv', rebuilt['crossing_diagnostics'])
        if rebuilt['stage_diff_rows']:
            write_csv(case_dir / 'stage_diff_vs_reference.csv', rebuilt['stage_diff_rows'])
        if rebuilt['partition_rows']:
            write_csv(case_dir / 'partition_summary.csv', rebuilt['partition_rows'])
        if rebuilt['exchange_summary_rows']:
            write_csv(case_dir / 'exchange_link_summary.csv', rebuilt['exchange_summary_rows'])
        summary_rows.append(rebuilt['summary'])
        if case.scenario_family in {
            'frontal_basin_fill',
            'lateral_overtopping_return',
            'early_arrival_pulse',
            'regime_switch_backwater_or_mixed',
        }:
            small_rows.append(rebuilt['summary'])
        partition_rows.extend(rebuilt['partition_rows'])
        exchange_rows.extend(rebuilt['exchange_summary_rows'])
        timing_rows.append(_timing_row(case, case_dir))
    _write_table(outputs, 'summary_table', summary_rows)
    _write_table(outputs, 'summary_table_small_cases', small_rows)
    _write_table(outputs, 'summary_table_test7_partitions', partition_rows)
    _write_table(outputs, 'exchange_link_summary', exchange_rows)
    _write_table(outputs, 'timing_breakdown', timing_rows)
    return {
        'summary_rows': summary_rows,
        'small_rows': small_rows,
        'partition_rows': partition_rows,
        'exchange_rows': exchange_rows,
        'timing_rows': timing_rows,
    }


def _run_plot_scripts(outputs: dict[str, Path]) -> list[dict[str, Any]]:
    refresh_payload = refresh_chapter_plot_outputs(outputs['root'], CHAPTER_PLOT_SPECS)
    return list(refresh_payload['figure_rows'])


def _table_manifest_rows(outputs: dict[str, Path]) -> list[dict[str, Any]]:
    return [
        {
            'table_id': 'Table-CTD-01',
            'source_csv_or_json': 'summaries/summary_table.csv',
            'key_columns': 'case_name,scenario_family,scheduler_mode,exchange_interval,stage_rmse,arrival_time_error,phase_lag,relative_cost_ratio',
            'caption_draft_cn': 'chapter 分析总汇总表。',
            'caption_draft_en': 'Master summary table for the chapter coupling analysis.',
            'chapter_section': '9',
        },
        {
            'table_id': 'Table-CTD-02',
            'source_csv_or_json': 'summaries/summary_table_mesh.csv',
            'key_columns': 'case_name,triangle_count,RMSE_stage_vs_reference,wall_clock_seconds',
            'caption_draft_cn': 'mesh sensitivity 汇总表。',
            'caption_draft_en': 'Summary table for mesh-sensitivity runs.',
            'chapter_section': '9',
        },
        {
            'table_id': 'Table-CTD-03',
            'source_csv_or_json': 'summaries/summary_table_test7_partitions.csv',
            'key_columns': 'case_name,partition,max_depth_map_difference,arrival_time_map_difference,wet_area_iou',
            'caption_draft_cn': 'Test 7 Floodplain 分区结果汇总表。',
            'caption_draft_en': 'Partition summary table for the Test 7 benchmark floodplains.',
            'chapter_section': '9',
        },
        {
            'table_id': 'Table-CTD-04',
            'source_csv_or_json': 'summaries/summary_table_small_cases.csv',
            'key_columns': 'case_name,scenario_family,stage_rmse,arrival_time_error,phase_lag,hydrograph_NSE',
            'caption_draft_cn': '小型机理算例结果汇总表。',
            'caption_draft_en': 'Summary table for the small mechanism cases.',
            'chapter_section': '9',
        },
        {
            'table_id': 'Table-CTD-05',
            'source_csv_or_json': 'summaries/timing_breakdown.csv',
            'key_columns': 'case_name,one_d_share,two_d_share,boundary_share,exchange_manager_share,misc_io_share',
            'caption_draft_cn': '不同策略的成本占比分解表。',
            'caption_draft_en': 'Cost-share breakdown table across coupling strategies.',
            'chapter_section': '9',
        },
        {
            'table_id': 'Table-CTD-06',
            'source_csv_or_json': 'summaries/exchange_link_summary.csv',
            'key_columns': 'case_name,link_id,peak_Q_exchange,cumulative_exchange_volume,sign_flip_count,link_mass_closure_error',
            'caption_draft_cn': '接口级 exchange link 诊断汇总表。',
            'caption_draft_en': 'Interface-level diagnostic summary for the exchange links.',
            'chapter_section': '9',
        },
    ]


def _default_provenance(cache_root: Path, allow_download: bool) -> Test7DataProvenance:
    return resolve_test7_data(cache_root, allow_download=allow_download)


def _warmup_gpu_cache(outputs: dict[str, Path], provenance: Test7DataProvenance) -> None:
    warmup_cases = generate_test7_cases(provenance, profile='test')
    warmup_case = next(case for case in warmup_cases if case.scheduler_mode == 'strict_global_min_dt')
    warmup_root = ensure_dir(outputs['logs'] / 'gpu_warmup')
    print(f'[chapter warmup] {warmup_case.case_name}', flush=True)
    _run_case_subprocess(warmup_case, {'root': warmup_root}, outputs['logs'] / 'test7_provenance.json', 'test')


def run_chapter_analysis(
    *,
    output_root: Path,
    profile: str = 'paper',
    include_test7: bool = True,
    include_small: bool = True,
    allow_download: bool = True,
    run_mesh: bool = True,
    generate_plots: bool = True,
    selected_case_names: set[str] | None = None,
    default_one_d_backend: str | None = None,
    default_mesh_variant: str | None = None,
) -> dict[str, Any]:
    outputs = chapter_dirs(output_root)
    provenance = _default_provenance(outputs['logs'] / 'test7_cache', allow_download=allow_download)
    provenance_path = outputs['logs'] / 'test7_provenance.json'
    write_json(provenance_path, provenance.to_payload())

    cases: list[ChapterExperimentCase] = []
    if include_test7:
        cases.extend(generate_test7_cases(provenance, profile=profile))
    if include_small:
        if not include_test7:
            _warmup_gpu_cache(outputs, provenance)
        cases.extend(generate_small_mechanism_cases(profile=profile))

    if selected_case_names is not None:
        cases = [case for case in cases if case.case_name in selected_case_names]

    if default_one_d_backend is not None or default_mesh_variant is not None:
        overridden_cases: list[ChapterExperimentCase] = []
        for case in cases:
            updates: dict[str, Any] = {}
            if default_one_d_backend is not None:
                updates['one_d_backend'] = default_one_d_backend
            if default_mesh_variant is not None:
                updates['mesh_variant'] = default_mesh_variant
            overridden_cases.append(replace(case, **updates) if updates else case)
        cases = overridden_cases

    for idx, case in enumerate(cases, start=1):
        print(f'[chapter {idx}/{len(cases)}] running {case.case_name}', flush=True)
        _run_case_subprocess(
            case,
            outputs,
            provenance_path,
            profile,
            one_d_backend=default_one_d_backend,
            mesh_variant=default_mesh_variant,
        )

    mesh_rows = _run_mesh_cases(outputs) if run_mesh else []
    if not run_mesh:
        _write_table(outputs, 'summary_table_mesh', [])
        _write_root_table(outputs, 'summary_table_mesh', [])
    tables = _aggregate_chapter_tables(cases, outputs)
    figure_rows = _run_plot_scripts(outputs) if generate_plots else []
    table_rows = _table_manifest_rows(outputs)
    if figure_rows or table_rows:
        _write_table(outputs, 'table_manifest', table_rows)
    return {
        'outputs': outputs,
        'provenance': provenance.to_payload(),
        'cases': [case.to_config_payload() for case in cases],
        'mesh_rows': mesh_rows,
        'figure_rows': figure_rows,
        'table_rows': table_rows,
        **tables,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description='Run chapter-level coupling analysis suites.')
    parser.add_argument('--output-root', default=str(Path('artifacts') / 'chapter_coupling_analysis'))
    parser.add_argument('--profile', default='paper', choices=['paper', 'test'])
    parser.add_argument('--disable-download', action='store_true')
    parser.add_argument('--skip-test7', action='store_true')
    parser.add_argument('--skip-small', action='store_true')
    return parser.parse_args()
