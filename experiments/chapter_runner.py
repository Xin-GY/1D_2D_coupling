from __future__ import annotations

import math
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import numpy as np
from shapely.geometry import Point, Polygon

from experiments.io import ensure_dir, write_csv, write_json


@dataclass(slots=True)
class ChapterDiagnosticsCollector:
    one_d_probes: list[dict[str, Any]]
    two_d_probes: list[dict[str, Any]]
    discharge_probes: list[dict[str, Any]]
    partition_defs: dict[str, list[list[float]]]
    snapshot_times: list[float]
    xt_river_name: str
    wet_threshold: float = 0.01
    stage_1d_rows: list[dict[str, Any]] = field(default_factory=list)
    stage_2d_rows: list[dict[str, Any]] = field(default_factory=list)
    discharge_rows: list[dict[str, Any]] = field(default_factory=list)
    exchange_link_rows: list[dict[str, Any]] = field(default_factory=list)
    river_profile_stage_rows: list[dict[str, Any]] = field(default_factory=list)
    river_profile_discharge_rows: list[dict[str, Any]] = field(default_factory=list)
    two_d_snapshot_rows: list[dict[str, Any]] = field(default_factory=list)
    _last_one_d_time: float | None = None
    _last_two_d_time: float | None = None
    _last_exchange_time: float | None = None
    _next_snapshot_index: int = 0
    _last_xt_capture_time: float | None = None
    _xt_sample_interval: float = 2.0
    _field_initialized: bool = False
    _cell_ids: np.ndarray | None = None
    _cell_x: np.ndarray | None = None
    _cell_y: np.ndarray | None = None
    _cell_area: np.ndarray | None = None
    _cell_partition: list[str] = field(default_factory=list)
    _max_depth: np.ndarray | None = None
    _arrival_time: np.ndarray | None = None
    _last_stage: np.ndarray | None = None
    _last_depth: np.ndarray | None = None
    _last_velocity: np.ndarray | None = None

    @staticmethod
    def _is_duplicate(last_time: float | None, time_value: float) -> bool:
        return last_time is not None and abs(float(last_time) - float(time_value)) <= 1.0e-12

    def _xt_interval_for_duration(self, duration: float) -> float:
        return 2.0 if float(duration) >= 120.0 else 1.0

    def initialize_field_tracker(self, manager, duration: float) -> None:
        if self._field_initialized:
            return
        domain = manager.two_d.domain
        self._cell_ids = np.arange(len(domain), dtype=int)
        self._cell_x = np.asarray(domain.centroid_coordinates[:, 0], dtype=float)
        self._cell_y = np.asarray(domain.centroid_coordinates[:, 1], dtype=float)
        self._cell_area = np.asarray(domain.areas, dtype=float)
        partition_polygons = {name: Polygon(coords) for name, coords in self.partition_defs.items()}
        self._cell_partition = []
        for x, y in zip(self._cell_x, self._cell_y):
            point = Point(float(x), float(y))
            match = 'unpartitioned'
            for name, polygon in partition_polygons.items():
                if polygon.buffer(1.0e-9).contains(point):
                    match = name
                    break
            self._cell_partition.append(match)
        self._max_depth = np.zeros(len(domain), dtype=float)
        self._arrival_time = np.full(len(domain), np.nan, dtype=float)
        self._last_stage = np.zeros(len(domain), dtype=float)
        self._last_depth = np.zeros(len(domain), dtype=float)
        self._last_velocity = np.zeros(len(domain), dtype=float)
        self._xt_sample_interval = self._xt_interval_for_duration(duration)
        self._field_initialized = True

    def capture_one_d(self, manager, time_value: float) -> None:
        if self._is_duplicate(self._last_one_d_time, time_value):
            return
        for probe in self.one_d_probes:
            self.stage_1d_rows.append(
                {
                    'time': float(time_value),
                    'probe_id': probe['probe_id'],
                    'stage': float(manager.one_d.sample_stage(probe['river_name'], probe['cell_id'])),
                }
            )
        for probe in self.discharge_probes:
            self.discharge_rows.append(
                {
                    'time': float(time_value),
                    'series_id': probe['probe_id'],
                    'discharge': float(manager.one_d.sample_discharge(probe['river_name'], probe['side'])),
                }
            )
        if self._last_xt_capture_time is None or (float(time_value) - float(self._last_xt_capture_time)) >= self._xt_sample_interval - 1.0e-12:
            river = manager.one_d.network.get_river(self.xt_river_name)
            x_coords = np.asarray(river.cell_pos[:, 0], dtype=float)
            water_level = np.asarray(river.water_level, dtype=float)
            discharge = np.asarray(river.Q, dtype=float)
            cell_num = int(river.cell_num)
            for idx in range(1, cell_num + 1):
                x_val = float(x_coords[min(idx, len(x_coords) - 1)])
                stage_val = float(water_level[min(idx, len(water_level) - 1)])
                q_idx = min(max(idx - 1, 0), len(discharge) - 1)
                self.river_profile_stage_rows.append(
                    {'time': float(time_value), 'cell_id': idx, 'x': x_val, 'stage': stage_val}
                )
                self.river_profile_discharge_rows.append(
                    {'time': float(time_value), 'cell_id': idx, 'x': x_val, 'discharge': float(discharge[q_idx])}
                )
            self._last_xt_capture_time = float(time_value)
        self._last_one_d_time = float(time_value)

    def _capture_snapshot(self, manager, time_value: float, snapshot_id: str) -> None:
        stage = np.asarray(manager.two_d._centroid_array('stage'), dtype=float)
        depth = np.asarray(manager.two_d._centroid_array('height'), dtype=float)
        xmom = np.asarray(manager.two_d._centroid_array('xmomentum'), dtype=float)
        ymom = np.asarray(manager.two_d._centroid_array('ymomentum'), dtype=float)
        velocity = np.where(depth > 1.0e-8, np.sqrt(xmom**2 + ymom**2) / np.maximum(depth, 1.0e-8), 0.0)
        assert self._cell_ids is not None
        assert self._cell_x is not None
        assert self._cell_y is not None
        assert self._cell_partition
        for cell_id, x, y, partition, stage_val, depth_val, vel_val in zip(
            self._cell_ids,
            self._cell_x,
            self._cell_y,
            self._cell_partition,
            stage,
            depth,
            velocity,
        ):
            self.two_d_snapshot_rows.append(
                {
                    'snapshot_id': snapshot_id,
                    'time': float(time_value),
                    'cell_id': int(cell_id),
                    'x': float(x),
                    'y': float(y),
                    'partition': partition,
                    'stage': float(stage_val),
                    'depth': float(depth_val),
                    'velocity': float(vel_val),
                }
            )

    def capture_two_d(self, manager, time_value: float) -> None:
        if self._is_duplicate(self._last_two_d_time, time_value):
            return
        self.initialize_field_tracker(manager, manager.config.end_time - manager.config.start_time)
        for probe in self.two_d_probes:
            self.stage_2d_rows.append(
                {
                    'time': float(time_value),
                    'probe_id': probe['probe_id'],
                    'stage': float(manager.two_d.sample_stage(probe['region'])),
                }
            )
        stage = np.asarray(manager.two_d._centroid_array('stage'), dtype=float)
        depth = np.asarray(manager.two_d._centroid_array('height'), dtype=float)
        xmom = np.asarray(manager.two_d._centroid_array('xmomentum'), dtype=float)
        ymom = np.asarray(manager.two_d._centroid_array('ymomentum'), dtype=float)
        velocity = np.where(depth > 1.0e-8, np.sqrt(xmom**2 + ymom**2) / np.maximum(depth, 1.0e-8), 0.0)
        assert self._max_depth is not None
        assert self._arrival_time is not None
        self._max_depth = np.maximum(self._max_depth, depth)
        dry_to_wet = np.isnan(self._arrival_time) & (depth >= float(self.wet_threshold))
        self._arrival_time[dry_to_wet] = float(time_value)
        self._last_stage = stage
        self._last_depth = depth
        self._last_velocity = velocity
        while self._next_snapshot_index < len(self.snapshot_times) and float(time_value) + 1.0e-12 >= float(self.snapshot_times[self._next_snapshot_index]):
            snapshot_id = f'snapshot_{self._next_snapshot_index + 1}'
            self._capture_snapshot(manager, time_value, snapshot_id)
            self._next_snapshot_index += 1
        self._last_two_d_time = float(time_value)

    def capture_exchange(self, manager, time_value: float) -> None:
        if self._is_duplicate(self._last_exchange_time, time_value):
            return
        recent = [row for row in manager.exchange_history if abs(float(row['time']) - float(time_value)) <= 1.0e-12]
        total_q = 0.0
        total_deta = 0.0
        total_dv = 0.0
        for row in recent:
            q_val = float(row['Q_exchange'])
            deta = float(row['eta_1d']) - float(row['eta_2d'])
            total_q += q_val
            total_deta += deta
            total_dv += float(row['dV_exchange'])
            self.exchange_link_rows.append(
                {
                    'time': float(time_value),
                    'link_id': row['link_id'],
                    'Q_exchange': q_val,
                    'deta': deta,
                    'dV_exchange': float(row['dV_exchange']),
                    'cumulative_dV': float(row['cumulative_dV']),
                    'eta_1d': float(row['eta_1d']),
                    'eta_2d': float(row['eta_2d']),
                    'mode': row['mode'],
                    'iteration_count': int(row['iteration_count']),
                }
            )
        self.discharge_rows.append({'time': float(time_value), 'series_id': 'exchange_q_total', 'discharge': float(total_q)})
        self.discharge_rows.append({'time': float(time_value), 'series_id': 'exchange_deta_total', 'discharge': float(total_deta)})
        self.discharge_rows.append({'time': float(time_value), 'series_id': 'exchange_volume_total', 'discharge': float(total_dv)})
        self._last_exchange_time = float(time_value)

    def __call__(self, manager, exchange_time: float, dt_exchange: float) -> None:
        self.capture_exchange(manager, exchange_time)

    def field_summary_rows(self) -> list[dict[str, Any]]:
        if not self._field_initialized:
            return []
        assert self._cell_ids is not None
        assert self._cell_x is not None
        assert self._cell_y is not None
        assert self._cell_area is not None
        assert self._max_depth is not None
        assert self._arrival_time is not None
        assert self._last_stage is not None
        assert self._last_depth is not None
        assert self._last_velocity is not None
        rows: list[dict[str, Any]] = []
        for idx, x, y, area, partition, max_depth, arrival, stage, depth, velocity in zip(
            self._cell_ids,
            self._cell_x,
            self._cell_y,
            self._cell_area,
            self._cell_partition,
            self._max_depth,
            self._arrival_time,
            self._last_stage,
            self._last_depth,
            self._last_velocity,
        ):
            rows.append(
                {
                    'cell_id': int(idx),
                    'x': float(x),
                    'y': float(y),
                    'area': float(area),
                    'partition': partition,
                    'max_depth': float(max_depth),
                    'arrival_time': float(arrival) if not np.isnan(arrival) else np.nan,
                    'final_stage': float(stage),
                    'final_depth': float(depth),
                    'final_velocity': float(velocity),
                }
            )
        return rows


def run_chapter_case(case, output_root: Path, prepare_case, reference: dict[str, Any] | None = None) -> dict[str, Any]:
    case_root = ensure_dir(output_root / 'cases' / case.case_name)
    prepared = prepare_case(case, case_root)
    manager = prepared['manager']
    collector = ChapterDiagnosticsCollector(
        one_d_probes=list(prepared['one_d_probes']),
        two_d_probes=list(prepared['two_d_probes']),
        discharge_probes=list(prepared['discharge_probes']),
        partition_defs=dict(prepared['partition_defs']),
        snapshot_times=list(prepared['snapshot_times']),
        xt_river_name=str(prepared['xt_river_name']),
        wet_threshold=float(prepared['field_wet_threshold']),
    )
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
    timing_breakdown['wall_clock_seconds'] = float(wall_clock_seconds)

    write_json(case_root / 'config.json', prepared['config_payload'])
    write_json(case_root / 'provenance.json', dict(prepared['data_provenance']))
    write_json(case_root / 'geometry.json', dict(prepared['geometry_payload']))
    write_csv(case_root / 'exchange_history.csv', manager.exchange_history)
    write_csv(case_root / 'mass_balance.csv', manager.mass_balance_rows)
    write_csv(case_root / 'stage_timeseries_1d.csv', collector.stage_1d_rows)
    write_csv(case_root / 'stage_timeseries_2d.csv', collector.stage_2d_rows)
    write_csv(case_root / 'discharge_timeseries.csv', collector.discharge_rows)
    write_csv(case_root / 'exchange_link_timeseries.csv', collector.exchange_link_rows)
    write_csv(case_root / 'river_profile_stage.csv', collector.river_profile_stage_rows)
    write_csv(case_root / 'river_profile_discharge.csv', collector.river_profile_discharge_rows)
    write_csv(case_root / 'two_d_snapshots.csv', collector.two_d_snapshot_rows)
    write_csv(case_root / 'two_d_field_summary.csv', collector.field_summary_rows())
    write_json(case_root / 'timing_breakdown.json', timing_breakdown)
    return {
        'wall_clock_seconds': wall_clock_seconds,
        'timing_breakdown': timing_breakdown,
        'primary_stage_probe': prepared['primary_stage_probe'],
        'primary_discharge_probe': prepared['primary_discharge_probe'],
    }
