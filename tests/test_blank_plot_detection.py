from __future__ import annotations

from pathlib import Path

import numpy as np
from PIL import Image

from experiments.io import read_csv
from scripts._plot_common import blank_image_audit


def test_blank_image_audit_detects_truly_blank_images(tmp_path: Path):
    blank_path = tmp_path / 'blank.png'
    textured_path = tmp_path / 'textured.png'

    Image.fromarray(np.full((200, 300, 3), 255, dtype=np.uint8)).save(blank_path)
    image = np.full((200, 300, 3), 255, dtype=np.uint8)
    image[20:180, 40:260, :] = np.array([180, 200, 230], dtype=np.uint8)
    image[::10, :, :] = 160
    image[:, ::10, :] = 160
    Image.fromarray(image).save(textured_path)

    blank_audit = blank_image_audit(blank_path, is_2d_map=True)
    textured_audit = blank_image_audit(textured_path, is_2d_map=True)

    assert blank_audit['is_approximately_blank']
    assert not textured_audit['is_approximately_blank']


def test_blank_image_audit_detects_axis_only_near_blank_images(tmp_path: Path):
    axis_only_path = tmp_path / 'axis_only.png'
    with_data_path = tmp_path / 'with_data.png'

    axis_only = np.full((320, 480, 3), 255, dtype=np.uint8)
    axis_only[40:280, 60:63, :] = 0
    axis_only[277:280, 60:420, :] = 0
    axis_only[40:280:24, 60:63, :] = 0
    axis_only[277:280, 60:420:36, :] = 0
    Image.fromarray(axis_only).save(axis_only_path)

    with_data = axis_only.copy()
    for offset in range(0, 240, 6):
        y = 250 - int(0.6 * offset)
        x = 90 + offset
        with_data[max(y - 2, 0):min(y + 2, with_data.shape[0]), max(x - 2, 0):min(x + 2, with_data.shape[1]), :] = np.array([220, 80, 80], dtype=np.uint8)
    Image.fromarray(with_data).save(with_data_path)

    axis_only_audit = blank_image_audit(axis_only_path, is_2d_map=False)
    with_data_audit = blank_image_audit(with_data_path, is_2d_map=False)

    assert axis_only_audit['is_near_blank']
    assert axis_only_audit['is_approximately_blank']
    assert not with_data_audit['is_approximately_blank']


def test_chapter_blank_plot_audit_reports_zero_failures(chapter_analysis_artifacts: Path):
    audit_rows = read_csv(chapter_analysis_artifacts / 'logs' / 'blank_plot_audit.csv')
    assert audit_rows, 'blank plot audit is missing'
    assert all(str(row['is_approximately_blank']).lower() in {'false', '0'} for row in audit_rows)


def test_fastest_exact_blank_plot_audit_reports_zero_failures(fastest_exact_chapter_artifacts: Path):
    audit_rows = read_csv(fastest_exact_chapter_artifacts / 'logs' / 'blank_plot_audit.csv')
    assert audit_rows, 'blank plot audit is missing'
    assert all(str(row['is_approximately_blank']).lower() in {'false', '0'} for row in audit_rows)


def test_combined_blank_plot_audit_reports_zero_failures(fastest_exact_chapter_artifacts: Path):
    audit_rows = read_csv(fastest_exact_chapter_artifacts / 'logs' / 'blank_plot_audit_all.csv')
    assert audit_rows, 'combined blank plot audit is missing'
    assert all(str(row['is_approximately_blank']).lower() in {'false', '0'} for row in audit_rows)
    roots = {str(row['root']) for row in audit_rows}
    assert any('chapter_coupling_analysis_fastest_exact' in root for root in roots)
    assert any('chapter_coupling_analysis' in root for root in roots)



def test_chapter_cn_blank_plot_audit_targets_are_nonblank(chapter_analysis_artifacts: Path, fastest_exact_chapter_artifacts: Path):
    targets = {
        'coupling_schematic_cn.png',
        'composite_case_geometry_mesh_cn.png',
        'front_fill_case_schematic_cn.png',
        'front_fill_stage_compare_cn.png',
        'lateral_overtop_return_exchange_diag_cn.png',
        'front_fast_arrival_zoom_cn.png',
        'mixed_backwater_switch_phase_lag_vs_interval_cn.png',
        'stage_hydrographs_1d_cn.png',
        'discharge_hydrographs_1d_cn.png',
        'max_depth_map_cn.png',
        'max_depth_difference_map_cn.png',
        'flood_front_overlay_cn.png',
        'exchange_q_timeseries_cn.png',
        'exchange_deta_timeseries_cn.png',
        'exchange_volume_cumulative_cn.png',
        'rmse_vs_interval_cn.png',
        'phase_lag_vs_interval_cn.png',
        'arrival_time_error_vs_interval_cn.png',
    }
    for artifacts_root in (chapter_analysis_artifacts, fastest_exact_chapter_artifacts):
        for png_name in targets:
            png_path = artifacts_root / 'plots' / png_name
            assert png_path.exists(), f'missing {png_name}'
            is_2d_map = png_name in {
                'composite_case_geometry_mesh_cn.png',
                'max_depth_map_cn.png',
                'max_depth_difference_map_cn.png',
                'flood_front_overlay_cn.png',
            }
            audit = blank_image_audit(png_path, is_2d_map=is_2d_map)
            assert not audit['is_approximately_blank'], f'{png_name} is blank or near-blank'
