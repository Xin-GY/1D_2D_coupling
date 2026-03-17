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
    _last_one_d_time: float | None = None
    _last_two_d_time: float | None = None
    _last_exchange_time: float | None = None

    @staticmethod
    def _is_duplicate(last_time: float | None, time_value: float) -> bool:
        return last_time is not None and abs(float(last_time) - float(time_value)) <= 1.0e-12

    def capture_one_d(self, manager, time_value: float) -> None:
        if self._is_duplicate(self._last_one_d_time, time_value):
            return
        control_id_1d, river_name, cell_id = self.control_point_1d
        self.stage_1d_rows.append(
            {
                'time': float(time_value),
                'control_id': control_id_1d,
                'stage': float(manager.one_d.sample_stage(river_name, cell_id)),
            }
        )
        self._last_one_d_time = float(time_value)

    def capture_two_d(self, manager, time_value: float) -> None:
        if self._is_duplicate(self._last_two_d_time, time_value):
            return
        control_id_2d, region = self.control_region_2d
        self.stage_2d_rows.append(
            {
                'time': float(time_value),
                'control_id': control_id_2d,
                'stage': float(manager.two_d.sample_stage(region)),
            }
        )
        self._last_two_d_time = float(time_value)

    def capture_exchange(self, manager, time_value: float) -> None:
        if self._is_duplicate(self._last_exchange_time, time_value):
            return
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
        self._last_exchange_time = float(time_value)

    def __call__(self, manager, exchange_time: float, dt_exchange: float) -> None:
        self.capture_exchange(manager, exchange_time)


def run_case(case, output_root: Path, prepare_case, reference: dict[str, Any] | None = None) -> dict[str, Any]:
    output_dir = ensure_dir(output_root / case.case_name)
    prepared = prepare_case(case, output_dir)
    manager = prepared['manager']
    collector = TimeSeriesCollector(prepared['control_point_1d'], prepared['control_region_2d'])
    manager.register_exchange_observer(collector)
    manager.one_d.register_diagnostic_callback(lambda adapter, time_value: collector.capture_one_d(manager, time_value))
    manager.two_d.register_diagnostic_callback(lambda adapter, time_value: collector.capture_two_d(manager, time_value))

    manager.initialize()
    collector.capture_one_d(manager, 0.0)
    collector.capture_two_d(manager, 0.0)
    collector.capture_exchange(manager, 0.0)

    started = time.perf_counter()
    manager.run()
    wall_clock_seconds = time.perf_counter() - started
    timing_breakdown = manager.get_timing_breakdown(wall_clock_seconds)

    write_json(output_dir / 'config.json', prepared['config_payload'])
    write_csv(output_dir / 'exchange_history.csv', manager.exchange_history)
    write_csv(output_dir / 'mass_balance.csv', manager.mass_balance_rows)
    write_csv(output_dir / 'stage_timeseries_1d.csv', collector.stage_1d_rows)
    write_csv(output_dir / 'stage_timeseries_2d.csv', collector.stage_2d_rows)
    write_csv(output_dir / 'discharge_timeseries.csv', collector.discharge_rows)
    write_json(output_dir / 'timing_breakdown.json', timing_breakdown)

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
        triangle_count=int(len(manager.two_d.domain)),
    )
    write_json(output_dir / 'summary_metrics.json', summary_metrics)
    return {
        'summary': summary_metrics,
        'timing_breakdown': timing_breakdown,
        'reference_payload': {
            'stage_1d_rows': collector.stage_1d_rows,
            'stage_2d_rows': collector.stage_2d_rows,
            'discharge_rows': collector.discharge_rows,
        },
    }
