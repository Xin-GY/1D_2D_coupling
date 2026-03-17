from __future__ import annotations

import csv
from collections import defaultdict
from pathlib import Path
from typing import Any

from coupling.runtime_env import configure_runtime_environment


configure_runtime_environment(Path('/tmp/1d_2d_coupling_plots'))

import matplotlib

matplotlib.use('Agg')
import matplotlib.pyplot as plt


def load_csv_rows(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open('r', encoding='utf-8', newline='') as handle:
        reader = csv.DictReader(handle)
        return list(reader)


def load_summary_rows(root: Path) -> list[dict[str, str]]:
    return load_csv_rows(root / 'summary_table.csv')


def case_rows(root: Path, case_name: str, filename: str) -> list[dict[str, str]]:
    return load_csv_rows(root / case_name / filename)


def ensure_plot_dir(root: Path) -> Path:
    plot_dir = root / 'plots'
    plot_dir.mkdir(parents=True, exist_ok=True)
    return plot_dir


def scheduler_case_names(summary_rows: list[dict[str, str]]) -> list[str]:
    return sorted(
        [
            row['case_name']
            for row in summary_rows
            if row['case_name'].startswith('mixed_bidirectional_pulse_')
        ]
    )


def fixed_interval_rows(summary_rows: list[dict[str, str]]) -> list[dict[str, str]]:
    rows = [row for row in summary_rows if 'fixed_interval_' in row['case_name'] and row['case_name'].startswith('mixed_bidirectional_pulse_')]
    return sorted(rows, key=lambda row: int(row['case_name'].split('fixed_interval_')[1].split('s')[0]))


def series_from_rows(rows: list[dict[str, str]], x_key: str, y_key: str, filter_key: str | None = None, filter_value: str | None = None) -> tuple[list[float], list[float]]:
    filtered = rows
    if filter_key is not None:
        filtered = [row for row in rows if row.get(filter_key) == filter_value]
    pairs = sorted((float(row[x_key]), float(row[y_key])) for row in filtered)
    return [pair[0] for pair in pairs], [pair[1] for pair in pairs]


def aggregate_exchange_series(rows: list[dict[str, str]]) -> tuple[list[float], list[float]]:
    grouped: dict[float, float] = defaultdict(float)
    for row in rows:
        grouped[float(row['time'])] += float(row['Q_exchange'])
    times = sorted(grouped)
    return times, [grouped[t] for t in times]


def save_figure(fig, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)
