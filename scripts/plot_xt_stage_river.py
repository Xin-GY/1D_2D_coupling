from __future__ import annotations

from pathlib import Path

import numpy as np

from scripts._plot_common import chapter_case_rows, ensure_plot_dir, load_chapter_summary_rows, plt, save_figure


def _benchmark_family(rows: list[dict[str, str]]) -> str:
    for row in rows:
        if 'test7' in row['scenario_family']:
            return row['scenario_family']
    raise KeyError('No Test7 family found')


def _pivot(rows: list[dict[str, str]], value_key: str):
    times = sorted({float(row['time']) for row in rows})
    xs = sorted({float(row['x']) for row in rows})
    grid = np.full((len(times), len(xs)), np.nan, dtype=float)
    time_index = {value: idx for idx, value in enumerate(times)}
    x_index = {value: idx for idx, value in enumerate(xs)}
    for row in rows:
        grid[time_index[float(row['time'])], x_index[float(row['x'])]] = float(row[value_key])
    return np.asarray(times), np.asarray(xs), grid


def main(root: Path | str | None = None) -> None:
    root = Path('artifacts/chapter_coupling_analysis') if root is None else Path(root)
    plot_dir = ensure_plot_dir(root)
    family = _benchmark_family(load_chapter_summary_rows(root))
    rows = chapter_case_rows(root, f'{family}_strict_global_min_dt', 'river_profile_stage.csv')
    times, xs, grid = _pivot(rows, 'stage')
    fig, ax = plt.subplots(figsize=(9, 4.5))
    mesh = ax.pcolormesh(xs, times, grid, shading='auto')
    fig.colorbar(mesh, ax=ax, label='水位 (m)')
    ax.set_title('河道水位 x-t 分布图')
    ax.set_xlabel('河道纵向位置 x')
    ax.set_ylabel('时间 (s)')
    save_figure(fig, plot_dir / 'xt_stage_river.png')


if __name__ == '__main__':
    main()
