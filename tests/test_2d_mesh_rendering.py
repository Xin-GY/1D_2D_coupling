from __future__ import annotations

import importlib
from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.collections import PolyCollection
import numpy as np

from scripts._plot_common import render_scalar_field_on_mesh


def test_render_scalar_field_on_mesh_uses_polycollection_for_cell_values():
    fig, ax = plt.subplots()
    geometry = {
        'vertices': np.asarray([[0.0, 0.0], [1.0, 0.0], [0.0, 1.0], [1.0, 1.0]], dtype=float),
        'triangles': np.asarray([[0, 1, 2], [1, 3, 2]], dtype=np.int32),
        'centroids': np.asarray([[1.0 / 3.0, 1.0 / 3.0], [2.0 / 3.0, 2.0 / 3.0]], dtype=float),
        'bounds': np.asarray([0.0, 1.0, 0.0, 1.0], dtype=float),
    }
    geometry['polygons'] = geometry['vertices'][geometry['triangles']]
    collection = render_scalar_field_on_mesh(ax, geometry, np.asarray([0.2, 0.8]), cmap='Blues')
    assert isinstance(collection, PolyCollection)
    plt.close(fig)


def test_chapter_2d_plot_modules_do_not_use_scatter(monkeypatch, chapter_analysis_artifacts: Path):
    import matplotlib.axes

    def _forbid_scatter(*args, **kwargs):  # pragma: no cover - exercised via monkeypatch
        raise AssertionError('2D mesh rendering should not call Axes.scatter')

    monkeypatch.setattr(matplotlib.axes.Axes, 'scatter', _forbid_scatter)
    for module_name in (
        'scripts.plot_test7_geometry_and_mesh',
        'scripts.plot_2d_snapshots_depth',
        'scripts.plot_2d_snapshots_velocity',
        'scripts.plot_2d_max_depth_map',
        'scripts.plot_2d_arrival_time_map',
        'scripts.plot_2d_difference_map',
        'scripts.plot_flood_front_overlay',
    ):
        module = importlib.import_module(module_name)
        module.main(chapter_analysis_artifacts)
