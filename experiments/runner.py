from __future__ import annotations

import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from experiments.io import ensure_dir, write_csv, write_json
from experiments.metrics import compute_summary_metrics


@dataclass(slots=True)
class TimeSeriesCollector:
    control_point_1d: tuple[str, str, int]
    control_region_2d: tuple[str, Any]
    stage_1d_rows: list[dict[str, Any]] = field(default_factory=list)
    stage_2d_rows: list[dict[str, Any]] = field(default_factory=list)
    discharge_rows: list[dict[str, Any]] = field(default_factory=list)

    def capture(self, manager, time_value: float) -> None:
        control_id_1d, river_name, cell_id = self.control_point_1d
        control_id_2d, region = self.control_region_2d
        self.stage_1d_rows.append(
            {
                'time': float(time_value),
                'control_id': control_id_1d,
                'stage': float(manager.one_d.sample_stage(river_name, cell_id)),
            }
        )
        self.stage_2d_rows.append(
            {
                'time': float(time_value),
                'control_id': control_id_2d,
                'stage': float(manager.two_d.sample_stage(region)),
            }
        )
        exchange_q = sum(float(link.current_Q) for link in list(manager.lateral_links) + list(manager.frontal_links))
        self.discharge_rows.append(
            {
                'time': float(time_value),
                'series_id': 'exchange_q_total',
                'discharge': float(exchange_q),
            }
        )
        if manager.frontal_links:
            link = manager.frontal_links[0]
            self.discharge_rows.append(
                {
                    'time': float(time_value),
                    'series_id': 'mainstem_right_q',
                    'discharge': float(manager.one_d.sample_discharge(link.river_name, link.river_boundary_side)),
                }
            )

    def __call__(self, manager, exchange_time: float, dt_exchange: float) -> None:
        self.capture(manager, exchange_time)


def run_case(case, output_root: Path, prepare_case, reference: dict[str, Any] | None = None) -> dict[str, Any]:
    output_dir = ensure_dir(output_root / case.case_name)
    prepared = prepare_case(case, output_dir)
    manager = prepared['manager']
    collector = TimeSeriesCollector(prepared['control_point_1d'], prepared['control_region_2d'])
    manager.register_exchange_observer(collector)

    manager.initialize()
    collector.capture(manager, 0.0)

    started = time.perf_counter()
    manager.run()
    wall_clock_seconds = time.perf_counter() - started

    write_json(output_dir / 'config.json', prepared['config_payload'])
    write_csv(output_dir / 'exchange_history.csv', manager.exchange_history)
    write_csv(output_dir / 'mass_balance.csv', manager.mass_balance_rows)
    write_csv(output_dir / 'stage_timeseries_1d.csv', collector.stage_1d_rows)
    write_csv(output_dir / 'stage_timeseries_2d.csv', collector.stage_2d_rows)
    write_csv(output_dir / 'discharge_timeseries.csv', collector.discharge_rows)

    summary_metrics = compute_summary_metrics(
        case_name=case.case_name,
        wall_clock_seconds=wall_clock_seconds,
        simulated_duration=case.duration,
        exchange_history=manager.exchange_history,
        mass_balance_rows=manager.mass_balance_rows,
        stage_1d_rows=collector.stage_1d_rows,
        stage_2d_rows=collector.stage_2d_rows,
        discharge_rows=collector.discharge_rows,
        reference=reference,
    )
    write_json(output_dir / 'summary_metrics.json', summary_metrics)
    return {
        'summary': summary_metrics,
        'reference_payload': {
            'stage_1d_rows': collector.stage_1d_rows,
            'stage_2d_rows': collector.stage_2d_rows,
            'discharge_rows': collector.discharge_rows,
        },
    }
