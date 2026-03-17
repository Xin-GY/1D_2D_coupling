from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from coupling.config import CouplingConfig, LateralLinkConfig, SchedulerConfig
from coupling.links import LateralWeirLink
from coupling.manager import CouplingManager

from tests.test_frontal_coupling import FakeOneDAdapter, FakeTwoDAdapter


@dataclass
class SequenceOneDAdapter(FakeOneDAdapter):
    stage_sequence: list[float] = field(default_factory=list)
    _stage_index: int = 0

    def sample_stage(self, river_name, s_or_cell) -> float:
        if self.stage_sequence:
            idx = min(self._stage_index, len(self.stage_sequence) - 1)
            return float(self.stage_sequence[idx])
        return super().sample_stage(river_name, s_or_cell)

    def advance_one_step(self, dt: float) -> float:
        used = super().advance_one_step(dt)
        if self.stage_sequence:
            self._stage_index = min(self._stage_index + 1, len(self.stage_sequence) - 1)
        return used


@dataclass
class SequenceTwoDAdapter(FakeTwoDAdapter):
    stage_sequence: list[float] = field(default_factory=list)
    _stage_index: int = 0

    def sample_stage(self, region) -> float:
        if self.stage_sequence:
            idx = min(self._stage_index, len(self.stage_sequence) - 1)
            return float(self.stage_sequence[idx])
        return super().sample_stage(region)

    def advance_one_step(self, dt: float) -> float:
        used = super().advance_one_step(dt)
        if self.stage_sequence:
            self._stage_index = min(self._stage_index + 1, len(self.stage_sequence) - 1)
        return used


def _run_lateral_case(tmp_path: Path, case_name: str, one_d_stages: list[float], two_d_stages: list[float]) -> CouplingManager:
    one_d = SequenceOneDAdapter(stage=one_d_stages[0], stage_sequence=one_d_stages, volume=100.0)
    two_d = SequenceTwoDAdapter(boundary_stage=two_d_stages[0], stage_sequence=two_d_stages, volume=50.0)
    link = LateralWeirLink.from_config(
        LateralLinkConfig(
            link_id='lat',
            river_name='river',
            region_id='lat_region',
            river_cells=[2],
            segment_lengths=[1.5],
            crest_levels=[0.6],
            discharge_coefficient=0.7,
            two_d_sample=[[0]],
        )
    )
    manager = CouplingManager(
        one_d=one_d,
        two_d=two_d,
        config=CouplingConfig(
            start_time=0.0,
            end_time=3.0,
            scheduler=SchedulerConfig(mode='fixed_interval', exchange_interval=1.0),
            diagnostics_dir=str(tmp_path / case_name),
        ),
        lateral_links=[link],
        frontal_links=[],
    )
    manager.run()
    return manager


def test_lateral_exchange_conserves_mass_for_both_directions_and_reversal(tmp_path: Path):
    managers = [
        _run_lateral_case(tmp_path, 'river_to_2d', [1.2, 1.1, 1.0], [0.4, 0.5, 0.6]),
        _run_lateral_case(tmp_path, 'twod_to_river', [0.5, 0.55, 0.6], [1.1, 1.0, 0.9]),
        _run_lateral_case(tmp_path, 'bidirectional', [1.0, 0.8, 0.6], [0.5, 0.8, 1.0]),
    ]

    for manager in managers:
        initial_volume = manager.initial_one_d_volume + manager.initial_two_d_volume
        final_volume = manager.one_d.get_total_volume() + manager.two_d.get_total_volume()
        assert abs(final_volume - initial_volume) < 1.0e-9

    river_to_2d_q = [float(row['Q_exchange']) for row in managers[0].exchange_history]
    twod_to_river_q = [float(row['Q_exchange']) for row in managers[1].exchange_history]
    bidirectional_q = [float(row['Q_exchange']) for row in managers[2].exchange_history]
    assert all(q >= 0.0 for q in river_to_2d_q)
    assert all(q <= 0.0 for q in twod_to_river_q)
    assert min(bidirectional_q) < 0.0 < max(bidirectional_q)
