from __future__ import annotations

import csv
from dataclasses import dataclass, field
from pathlib import Path
import time
from typing import Any

from .adapters_anuga_gpu import TwoDAnugaGpuAdapter
from .adapters_rivernet import OneDNetworkAdapter
from .config import CouplingConfig
from .links import FrontalBoundaryLink, LateralWeirLink
from .scheduler import ExchangeScheduler


@dataclass(slots=True)
class CouplingManager:
    one_d: OneDNetworkAdapter
    two_d: TwoDAnugaGpuAdapter
    config: CouplingConfig
    lateral_links: list[LateralWeirLink]
    frontal_links: list[FrontalBoundaryLink]
    scheduler: ExchangeScheduler = field(init=False)
    exchange_history: list[dict[str, Any]] = field(default_factory=list)
    dt_history: list[dict[str, Any]] = field(default_factory=list)
    mass_balance_rows: list[dict[str, Any]] = field(default_factory=list)
    initial_one_d_volume: float = 0.0
    initial_two_d_volume: float = 0.0
    initial_system_volume: float = 0.0
    cumulative_exchange_volume: float = 0.0
    exchange_observers: list[Any] = field(default_factory=list)
    timing_stats: dict[str, float] = field(default_factory=lambda: {'frontal_boundary_update_time': 0.0})
    _initialized: bool = False

    def __post_init__(self) -> None:
        self.scheduler = ExchangeScheduler(self.config.scheduler)

    def initialize(self) -> None:
        if self._initialized:
            return
        self.one_d.initialize(save_outputs=False)
        self.two_d.initialize_gpu()
        self.initial_one_d_volume = self.one_d.get_total_volume()
        self.initial_two_d_volume = self.two_d.get_total_volume()
        self.initial_system_volume = self.initial_one_d_volume + self.initial_two_d_volume
        for frontal_link in self.frontal_links:
            self.two_d.register_dynamic_boundary(
                frontal_link.two_d_boundary_tag,
                frontal_link.build_two_d_boundary_state(frontal_link.current_stage, frontal_link.current_Q),
            )
            self.two_d.activate_dynamic_boundary(frontal_link.two_d_boundary_tag, False)
        exchange_regions = getattr(self.two_d, '_exchange_regions', {})
        for lateral_link in self.lateral_links:
            if lateral_link.region_id not in exchange_regions:
                continue
        self._initialized = True

    def register_exchange_observer(self, observer: Any) -> None:
        self.exchange_observers.append(observer)

    def _notify_exchange_observers(self, exchange_time: float, dt_exchange: float) -> None:
        for observer in self.exchange_observers:
            observer(self, float(exchange_time), float(dt_exchange))

    def _sample_lateral_link(self, link: LateralWeirLink) -> tuple[list[float], list[float]]:
        river_eta = [self.one_d.sample_stage(link.river_name, segment.river_cell) for segment in link.segments]
        two_d_eta = []
        for segment in link.segments:
            if segment.two_d_sample is None:
                region = self.two_d._exchange_regions.get(link.link_id)
                if region is None:
                    raise KeyError(f'link {link.link_id} 尚未注册 2D exchange region')
                two_d_eta.append(self.two_d.sample_stage(region))
            else:
                two_d_eta.append(self.two_d.sample_stage(segment.two_d_sample))
        return river_eta, two_d_eta

    def _apply_lateral_exchange(self, current_time: float, dt_exchange: float, mode: str) -> None:
        self.one_d.clear_lateral_sources()
        self.two_d.clear_exchange_Q()
        for link in self.lateral_links:
            river_eta, two_d_eta = self._sample_lateral_link(link)
            q_exchange = link.compute_exchange(river_eta, two_d_eta, gravity=self.config.gravity)
            for segment, q_seg in zip(link.segments, link.last_segment_Q):
                self.one_d.apply_lateral_source(
                    link.link_id,
                    link.river_name,
                    {segment.river_cell: 1.0},
                    -q_seg,
                )
            self.two_d.set_exchange_Q(link.link_id, q_exchange)

    def _finalize_lateral_history(self, exchange_time: float, dt_exchange: float, mode: str) -> None:
        for link in self.lateral_links:
            self.exchange_history.append(link.finalize_exchange(exchange_time, dt_exchange, mode))

    def _sample_frontal_guesses(self) -> dict[str, dict[str, Any]]:
        guesses = {}
        for link in self.frontal_links:
            stage_guess = self.two_d.sample_boundary_stage(link.two_d_boundary_tag)
            q_guess = self.one_d.sample_discharge(link.river_name, link.river_boundary_side)
            regime = self.one_d.sample_regime(link.river_name, link.river_boundary_side)
            guesses[link.link_id] = {
                'stage': stage_guess,
                'Q': q_guess,
                'regime': regime,
            }
        return guesses

    def _apply_frontal_guesses(self, guesses: dict[str, dict[str, Any]]) -> None:
        started = time.perf_counter()
        for link in self.frontal_links:
            guess = guesses[link.link_id]
            link.current_stage = float(guess['stage'])
            link.current_Q = float(guess['Q'])
            link.last_mode = str(guess['regime'])
            if guess['regime'] == 'sub':
                self.one_d.apply_stage_bc(link.river_boundary_node, guess['stage'])
                self.two_d.set_dynamic_boundary_state(
                    link.two_d_boundary_tag,
                    link.build_two_d_boundary_state(guess['stage'], guess['Q']),
                )
                self.two_d.activate_dynamic_boundary(link.two_d_boundary_tag, True)
            elif guess['regime'] == 'super_out':
                self.two_d.set_dynamic_boundary_state(
                    link.two_d_boundary_tag,
                    link.build_two_d_boundary_state(guess['stage'], guess['Q']),
                )
                self.two_d.activate_dynamic_boundary(link.two_d_boundary_tag, True)
            else:
                self.one_d.apply_stage_bc(link.river_boundary_node, guess['stage'])
                self.two_d.activate_dynamic_boundary(link.two_d_boundary_tag, False)
        self.timing_stats['frontal_boundary_update_time'] += time.perf_counter() - started

    def exchange_all_links(self, current_time: float, dt_exchange: float, mode: str) -> dict[str, dict[str, Any]]:
        self._apply_lateral_exchange(current_time, dt_exchange, mode)
        guesses = self._sample_frontal_guesses()
        self._apply_frontal_guesses(guesses)
        return guesses

    def step_until_exchange(self, target_time: float, shared_dt: float | None = None) -> None:
        if shared_dt is not None:
            self.one_d.advance_one_step(shared_dt)
            self.two_d.advance_one_step(shared_dt)
            return
        self.one_d.advance_to(target_time, mode=self.config.scheduler.mode)
        self.two_d.advance_to(target_time, mode=self.config.scheduler.mode)

    def _finalize_frontal_history(self, exchange_time: float, dt_exchange: float, guesses: dict[str, dict[str, Any]]) -> None:
        for link in self.frontal_links:
            sampled_stage = self.two_d.sample_boundary_stage(link.two_d_boundary_tag)
            sampled_q = self.one_d.sample_discharge(link.river_name, link.river_boundary_side)
            link.current_stage = sampled_stage
            link.current_Q = sampled_q
            link.iteration_count = max(1, link.iteration_count)
            self.exchange_history.append(link.finalize_exchange(exchange_time, dt_exchange, link.last_mode))

    def _current_exchange_volume(self) -> float:
        links = list(self.lateral_links) + list(self.frontal_links)
        return float(sum(abs(float(link.current_dV)) for link in links))

    def _run_picard_interval(self, current_time: float, next_time: float, guesses: dict[str, dict[str, Any]]) -> None:
        snap_1d = self.one_d.snapshot()
        snap_2d = self.two_d.snapshot()
        dt_exchange = next_time - current_time
        active_links = [link for link in self.frontal_links if link.max_iter > 1]
        if not active_links or self.config.scheduler.mode == 'strict_global_min_dt':
            self.step_until_exchange(next_time)
            self._finalize_lateral_history(next_time, dt_exchange, self.config.scheduler.mode)
            self._finalize_frontal_history(next_time, dt_exchange, guesses)
            return

        for link in active_links:
            link.iteration_count = 1

        for iter_idx in range(1, max(link.max_iter for link in active_links) + 1):
            if iter_idx > 1:
                self.one_d.restore(snap_1d)
                self.two_d.restore(snap_2d)
                self._apply_lateral_exchange(current_time, dt_exchange, self.config.scheduler.mode)
            self._apply_frontal_guesses(guesses)
            self.step_until_exchange(next_time)

            converged = True
            for link in active_links:
                stage_new = self.two_d.sample_boundary_stage(link.two_d_boundary_tag)
                q_new = self.one_d.sample_discharge(link.river_name, link.river_boundary_side)
                stage_guess = float(guesses[link.link_id]['stage'])
                q_guess = float(guesses[link.link_id]['Q'])
                if not link.converged(stage_guess, q_guess, stage_new, q_new):
                    converged = False
                relaxed_stage, relaxed_q = link.relax_guess(stage_guess, q_guess, stage_new, q_new)
                guesses[link.link_id]['stage'] = relaxed_stage
                guesses[link.link_id]['Q'] = relaxed_q
                link.iteration_count = iter_idx
            if converged:
                break

        self._finalize_lateral_history(next_time, dt_exchange, self.config.scheduler.mode)
        self._finalize_frontal_history(next_time, dt_exchange, guesses)

    def run(self) -> None:
        self.initialize()
        current = float(self.config.start_time)
        end_time = float(self.config.end_time)
        while current + self.scheduler.time_eps < end_time:
            if self.config.scheduler.mode == 'strict_global_min_dt':
                dt_1d = self.one_d.predict_cfl_dt()
                dt_2d = self.two_d.predict_cfl_dt()
                next_time = self.scheduler.next_exchange_time(current, end_time, one_d_dt=dt_1d, two_d_dt=dt_2d)
                dt_exchange = next_time - current
                guesses = self.exchange_all_links(current, dt_exchange, self.config.scheduler.mode)
                self.step_until_exchange(next_time, shared_dt=dt_exchange)
                self._finalize_lateral_history(next_time, dt_exchange, self.config.scheduler.mode)
                self._finalize_frontal_history(next_time, dt_exchange, guesses)
            else:
                next_time = self.scheduler.next_exchange_time(current, end_time)
                dt_exchange = next_time - current
                guesses = self.exchange_all_links(current, dt_exchange, self.config.scheduler.mode)
                self._run_picard_interval(current, next_time, guesses)

            one_d_volume = self.one_d.get_total_volume()
            two_d_volume = self.two_d.get_total_volume()
            system_volume = float(one_d_volume + two_d_volume)
            system_mass_error = float(system_volume - self.initial_system_volume)
            current_exchange_volume = self._current_exchange_volume()
            self.cumulative_exchange_volume += current_exchange_volume
            self.dt_history.append(
                {
                    'time': float(next_time),
                    'dt_exchange': float(dt_exchange),
                    'mode': self.config.scheduler.mode,
                }
            )
            self.mass_balance_rows.append(
                {
                    'time': float(next_time),
                    'one_d_volume': float(one_d_volume),
                    'two_d_volume': float(two_d_volume),
                    'system_volume': system_volume,
                    'system_volume_change': float((one_d_volume - self.initial_one_d_volume) + (two_d_volume - self.initial_two_d_volume)),
                    'system_mass_error': system_mass_error,
                    'current_exchange_volume': current_exchange_volume,
                    'cumulative_exchange_volume': float(self.cumulative_exchange_volume),
                    'exchange_count': len(self.dt_history),
                }
            )
            self._notify_exchange_observers(next_time, dt_exchange)
            current = next_time
        self.write_diagnostics()

    def write_diagnostics(self) -> None:
        out_dir = Path(self.config.diagnostics_dir)
        out_dir.mkdir(parents=True, exist_ok=True)
        self._write_csv(out_dir / 'coupling_exchange_history.csv', self.exchange_history)
        self._write_csv(out_dir / 'coupling_dt_history.csv', self.dt_history)
        self._write_csv(out_dir / 'coupling_mass_balance.csv', self.mass_balance_rows)

    def get_timing_breakdown(self, wall_clock_seconds: float) -> dict[str, float]:
        one_d_advance_time = float(getattr(self.one_d, 'timing_stats', {}).get('advance_time', 0.0))
        boundary_update_time = float(getattr(self.two_d, 'timing_stats', {}).get('boundary_update_time', 0.0))
        boundary_update_time += float(self.timing_stats.get('frontal_boundary_update_time', 0.0))
        two_d_gpu_kernel_time = float(getattr(self.two_d, 'timing_stats', {}).get('kernel_time', 0.0))
        gpu_inlets_apply_time = float(getattr(self.two_d, 'timing_stats', {}).get('gpu_inlets_apply_time', 0.0))
        scheduler_manager_overhead = float(
            max(
                float(wall_clock_seconds)
                - (one_d_advance_time + boundary_update_time + two_d_gpu_kernel_time + gpu_inlets_apply_time),
                0.0,
            )
        )
        return {
            'one_d_advance_time': one_d_advance_time,
            'two_d_gpu_kernel_time': two_d_gpu_kernel_time,
            'boundary_update_time': boundary_update_time,
            'gpu_inlets_apply_time': gpu_inlets_apply_time,
            'scheduler_manager_overhead': scheduler_manager_overhead,
        }

    @staticmethod
    def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
        if not rows:
            return
        with path.open('w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
            writer.writeheader()
            writer.writerows(rows)
