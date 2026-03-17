from __future__ import annotations

import importlib

from experiments.io import read_csv
from scripts._plot_common import blank_image_audit


PLOT_MODULES = {
    'scripts.plot_stage_1d_compare': 'stage_1d_compare.png',
    'scripts.plot_stage_2d_compare': 'stage_2d_compare.png',
    'scripts.plot_q_exchange_compare': 'q_exchange_compare.png',
    'scripts.plot_mass_error_compare': 'mass_error_compare.png',
    'scripts.plot_rmse_vs_interval': 'rmse_vs_interval.png',
    'scripts.plot_peak_stage_error_vs_interval': 'peak_stage_error_vs_interval.png',
    'scripts.plot_arrival_time_error_vs_interval': 'arrival_time_error_vs_interval.png',
    'scripts.plot_phase_lag_vs_interval': 'phase_lag_vs_interval.png',
    'scripts.plot_runtime_vs_interval': 'runtime_vs_interval.png',
    'scripts.plot_coupling_type_compare': 'coupling_type_compare.png',
    'scripts.plot_mesh_sensitivity_stage': 'mesh_sensitivity_stage.png',
    'scripts.plot_mesh_sensitivity_mass': 'mesh_sensitivity_mass.png',
    'scripts.plot_mesh_sensitivity_runtime': 'mesh_sensitivity_runtime.png',
    'scripts.plot_timing_breakdown': 'timing_breakdown.png',
    'scripts.plot_summary_dashboard': 'summary_dashboard.png',
}


CHAPTER_PLOT_MODULES = {
    'scripts.plot_coupling_schematic': 'coupling_schematic.png',
    'scripts.plot_test7_geometry_and_mesh': 'test7_geometry_and_mesh.png',
    'scripts.plot_scheduler_timeline_schematic': 'scheduler_timeline_schematic.png',
    'scripts.plot_stage_hydrographs_1d': 'stage_hydrographs_1d.png',
    'scripts.plot_discharge_hydrographs_1d': 'discharge_hydrographs_1d.png',
    'scripts.plot_xt_stage_river': 'xt_stage_river.png',
    'scripts.plot_xt_discharge_river': 'xt_discharge_river.png',
    'scripts.plot_exchange_q_timeseries': 'exchange_q_timeseries.png',
    'scripts.plot_exchange_deta_timeseries': 'exchange_deta_timeseries.png',
    'scripts.plot_exchange_volume_cumulative': 'exchange_volume_cumulative.png',
    'scripts.plot_exchange_event_alignment': 'exchange_event_alignment.png',
    'scripts.plot_2d_snapshots_depth': '2d_snapshots_depth.png',
    'scripts.plot_2d_snapshots_velocity': '2d_snapshots_velocity.png',
    'scripts.plot_2d_max_depth_map': '2d_max_depth_map.png',
    'scripts.plot_2d_arrival_time_map': '2d_arrival_time_map.png',
    'scripts.plot_2d_difference_map': '2d_difference_map.png',
    'scripts.plot_flood_front_overlay': 'flood_front_overlay.png',
    'scripts.plot_rmse_vs_interval': 'rmse_vs_interval.png',
    'scripts.plot_peak_error_vs_interval': 'peak_error_vs_interval.png',
    'scripts.plot_arrival_time_error_vs_interval': 'arrival_time_error_vs_interval.png',
    'scripts.plot_phase_lag_vs_interval': 'phase_lag_vs_interval.png',
    'scripts.plot_interval_normalized_axes': 'interval_normalized_axes.png',
    'scripts.plot_cost_share_stacked': 'cost_share_stacked.png',
    'scripts.plot_relative_cost_vs_accuracy': 'relative_cost_vs_accuracy.png',
    'scripts.plot_floodplain_partition_compare': 'floodplain_partition_compare.png',
    'scripts.plot_summary_dashboard': 'summary_dashboard.png',
}


def test_plot_scripts_generate_nonempty_pngs(coupling_sweep_artifacts):
    plot_dir = coupling_sweep_artifacts / 'plots'
    for module_name, png_name in PLOT_MODULES.items():
        module = importlib.import_module(module_name)
        module.main(coupling_sweep_artifacts)
        png_path = plot_dir / png_name
        assert png_path.exists(), f'{module_name} did not create {png_name}'
        assert png_path.stat().st_size > 0, f'{png_name} is empty'


def test_chapter_plot_scripts_generate_nonempty_pngs(chapter_analysis_artifacts):
    plot_dir = chapter_analysis_artifacts / 'plots'
    for module_name, png_name in CHAPTER_PLOT_MODULES.items():
        module = importlib.import_module(module_name)
        module.main(chapter_analysis_artifacts)
        png_path = plot_dir / png_name
        assert png_path.exists(), f'{module_name} did not create {png_name}'
        assert png_path.stat().st_size > 0, f'{png_name} is empty'
        is_2d_map = png_name.startswith('2d_') or png_name in {'flood_front_overlay.png', 'test7_geometry_and_mesh.png'}
        audit = blank_image_audit(png_path, is_2d_map=is_2d_map)
        assert not audit['is_approximately_blank'], f'{png_name} is blank or near-blank'
        assert audit['width_px'] >= 1000
        assert audit['height_px'] >= 500

    figure_manifest = chapter_analysis_artifacts / 'summaries' / 'figure_manifest.csv'
    table_manifest = chapter_analysis_artifacts / 'summaries' / 'table_manifest.csv'
    assert figure_manifest.exists()
    assert table_manifest.exists()
    rows = read_csv(figure_manifest)
    assert rows
    required_columns = {
        'figure_id',
        'script_path',
        'geometry_source',
        'render_mode',
        'blank_check_status',
        'regenerated_at',
    }
    assert required_columns.issubset(rows[0].keys())
