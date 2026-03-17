from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
import time
from typing import Any

import numpy as np


@dataclass(slots=True)
class OneDNetworkAdapter:
    network: Any
    time_eps: float = 1.0e-12
    _pending_lateral_sources: dict[str, dict[str, dict[int, float]]] = field(default_factory=dict)
    diagnostic_callbacks: list[Any] = field(default_factory=list)
    timing_stats: dict[str, float] = field(default_factory=lambda: {'advance_time': 0.0})

    def initialize(self, save_outputs: bool = False) -> float:
        self.reset_timing_stats()
        return float(self.network.initialize_for_coupling(save_outputs=save_outputs))

    def predict_cfl_dt(self) -> float:
        return float(self.network.predict_cfl_dt())

    def register_diagnostic_callback(self, callback: Any) -> None:
        self.diagnostic_callbacks.append(callback)

    def reset_timing_stats(self) -> None:
        self.timing_stats = {'advance_time': 0.0}

    def _notify_diagnostic_callbacks(self) -> None:
        current_time = float(self.network.current_sim_time)
        for callback in self.diagnostic_callbacks:
            callback(self, current_time)

    def _set_constant_boundary(self, node: str, btype: str, value: float) -> None:
        if node not in self.network.boundaries:
            self.network.set_boundary(node, btype, float(value))
            return
        self.network.update_type(node, btype)
        item = self.network.boundaries[node]
        if '_val' in item:
            self.network.update_const(node, float(value))
        else:
            self.network.set_boundary(node, btype, float(value))

    def apply_stage_bc(self, node: str, stage: float) -> None:
        self._set_constant_boundary(node, 'fix_level', float(stage))

    def apply_flow_bc(self, node: str, discharge: float) -> None:
        self._set_constant_boundary(node, 'flow', float(discharge))

    def clear_lateral_sources(self) -> None:
        self._pending_lateral_sources.clear()

    def apply_lateral_source(
        self,
        link_id: str,
        river_name: str,
        cell_weights: Mapping[int, float] | list[tuple[int, float]] | list[int],
        discharge: float,
    ) -> None:
        if isinstance(cell_weights, Mapping):
            items = list(cell_weights.items())
        elif cell_weights and isinstance(cell_weights[0], tuple):
            items = list(cell_weights)  # type: ignore[index]
        else:
            weights = np.ones(len(cell_weights), dtype=float)
            weights /= np.sum(weights)
            items = list(zip(cell_weights, weights.tolist()))  # type: ignore[arg-type]

        weights_sum = sum(float(weight) for _, weight in items)
        if weights_sum <= 0.0:
            raise ValueError('cell_weights 的总和必须大于 0')

        source_map = self._pending_lateral_sources.setdefault(link_id, {}).setdefault(river_name, {})
        for cell_id, weight in items:
            source_map[int(cell_id)] = source_map.get(int(cell_id), 0.0) + float(discharge) * float(weight) / weights_sum

    def _materialize_lateral_sources(self) -> None:
        for river_sources in self._pending_lateral_sources.values():
            for river_name, source_map in river_sources.items():
                river = self.network.get_river(river_name)
                cell_ids = list(source_map.keys())
                side_qs = list(source_map.values())
                river.apply_cellwise_side_inflow(cell_ids, side_qs)

    def advance_one_step(self, dt: float) -> float:
        self._materialize_lateral_sources()
        started = time.perf_counter()
        used_dt = float(self.network.advance_one_step(dt))
        self.timing_stats['advance_time'] += time.perf_counter() - started
        if used_dt > 0.0:
            self._notify_diagnostic_callbacks()
        return used_dt

    def advance_to(self, target_time: float, mode: str | None = None) -> float:
        target = float(target_time)
        while self.network.current_sim_time + self.time_eps < target:
            remaining = target - float(self.network.current_sim_time)
            dt = min(float(self.predict_cfl_dt()), remaining)
            if dt <= self.time_eps:
                dt = max(remaining, 0.0)
            used_dt = self.advance_one_step(dt)
            if used_dt <= 0.0:
                break
        return float(self.network.current_sim_time)

    def sample_stage(self, river_name: str, s_or_cell: int | float) -> float:
        river = self.network.get_river(river_name)
        if isinstance(s_or_cell, int):
            return float(river.water_level[int(s_or_cell)])
        coords = river.cell_pos[:, 0]
        idx = int(np.argmin(np.abs(coords - float(s_or_cell))))
        idx = min(max(idx, 1), river.cell_num)
        return float(river.water_level[idx])

    def sample_discharge(self, river_name: str, side: str) -> float:
        river = self.network.get_river(river_name)
        if side.lower().startswith('l'):
            face_q = getattr(river, 'boundary_face_discharge_left', None)
            return float(river.Q[0] if face_q is None else face_q)
        face_q = getattr(river, 'boundary_face_discharge_right', None)
        return float(river.Q[-1] if face_q is None else face_q)

    def sample_regime(self, river_name: str, side: str) -> str:
        river = self.network.get_river(river_name)
        if side.lower().startswith('l'):
            idx = 1
            flow_dir_sign = -1
        else:
            idx = -2
            flow_dir_sign = 1
        area = float(max(river.S[idx], 1.0e-12))
        width = float(max(river.cross_section_table.get_width_by_area(river.cell_sections[idx], area), 1.0e-8))
        discharge = float(river.Q[idx])
        regime, _, _, _ = self.network._branch_regime(area, width, discharge, flow_dir_sign=flow_dir_sign)
        return str(regime)

    def snapshot(self) -> dict[str, Any]:
        return {
            'network': self.network.snapshot(),
            'pending_lateral_sources': {
                link_id: {
                    river_name: dict(source_map)
                    for river_name, source_map in river_sources.items()
                }
                for link_id, river_sources in self._pending_lateral_sources.items()
            },
        }

    def restore(self, snapshot: dict[str, Any]) -> None:
        self.network.restore(snapshot['network'])
        self._pending_lateral_sources = {
            link_id: {
                river_name: dict(source_map)
                for river_name, source_map in river_sources.items()
            }
            for link_id, river_sources in snapshot.get('pending_lateral_sources', {}).items()
        }

    def get_total_volume(self) -> float:
        return float(self.network.get_total_volume())
