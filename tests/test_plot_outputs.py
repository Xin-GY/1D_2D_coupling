from __future__ import annotations

import importlib


PLOT_MODULES = {
    'scripts.plot_stage_1d_compare': 'stage_1d_compare.png',
    'scripts.plot_stage_2d_compare': 'stage_2d_compare.png',
    'scripts.plot_q_exchange_compare': 'q_exchange_compare.png',
    'scripts.plot_mass_error_compare': 'mass_error_compare.png',
    'scripts.plot_rmse_vs_interval': 'rmse_vs_interval.png',
    'scripts.plot_peak_stage_error_vs_interval': 'peak_stage_error_vs_interval.png',
    'scripts.plot_arrival_time_error_vs_interval': 'arrival_time_error_vs_interval.png',
    'scripts.plot_runtime_vs_interval': 'runtime_vs_interval.png',
    'scripts.plot_coupling_type_compare': 'coupling_type_compare.png',
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
