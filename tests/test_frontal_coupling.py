from dataclasses import dataclass, field
from pathlib import Path

from experiments.cases import ExperimentCase, prepare_case
from coupling.config import CouplingConfig, FrontalLinkConfig, SchedulerConfig
from coupling.links import FrontalBoundaryLink
from coupling.manager import CouplingManager


@dataclass
class FakeOneDAdapter:
    stage: float = 1.0
    discharge: float = 2.0
    regime: str = 'sub'
    volume: float = 100.0
    current_time: float = 0.0
    stage_bc_calls: list[tuple[str, float]] = field(default_factory=list)
    pending_lateral: float = 0.0
    discharge_sequence: list[float] = field(default_factory=list)
    _seq_index: int = 0

    def initialize(self, save_outputs: bool = False) -> float:
        return 1.0

    def predict_cfl_dt(self) -> float:
        return 1.0

    def clear_lateral_sources(self) -> None:
        self.pending_lateral = 0.0

    def apply_lateral_source(self, link_id, river_name, cell_weights, discharge) -> None:
        self.pending_lateral += float(discharge)

    def advance_one_step(self, dt: float) -> float:
        self.volume += self.pending_lateral * dt
        self.current_time += dt
        if self.discharge_sequence:
            self.discharge = self.discharge_sequence[min(self._seq_index, len(self.discharge_sequence) - 1)]
            self._seq_index += 1
        return dt

    def advance_to(self, target_time: float, mode=None) -> float:
        return self.advance_one_step(target_time - self.current_time)

    def sample_stage(self, river_name, s_or_cell) -> float:
        return self.stage

    def sample_discharge(self, river_name, side) -> float:
        return self.discharge

    def sample_regime(self, river_name, side) -> str:
        return self.regime

    def apply_stage_bc(self, node: str, stage: float) -> None:
        self.stage_bc_calls.append((node, float(stage)))

    def snapshot(self):
        return {
            'stage': self.stage,
            'discharge': self.discharge,
            'volume': self.volume,
            'current_time': self.current_time,
            'pending_lateral': self.pending_lateral,
            'stage_bc_calls': list(self.stage_bc_calls),
            '_seq_index': self._seq_index,
        }

    def restore(self, snapshot) -> None:
        self.stage = snapshot['stage']
        self.discharge = snapshot['discharge']
        self.volume = snapshot['volume']
        self.current_time = snapshot['current_time']
        self.pending_lateral = snapshot['pending_lateral']
        self.stage_bc_calls = list(snapshot['stage_bc_calls'])
        self._seq_index = snapshot['_seq_index']

    def get_total_volume(self) -> float:
        return self.volume


@dataclass
class FakeTwoDAdapter:
    boundary_stage: float = 1.2
    volume: float = 50.0
    relative_time: float = 0.0
    exchange_q: dict[str, float] = field(default_factory=dict)
    dynamic_state: dict[str, list[float]] = field(default_factory=dict)
    active_boundary: dict[str, bool] = field(default_factory=dict)
    stage_sequence: list[float] = field(default_factory=list)
    _seq_index: int = 0

    def initialize_gpu(self) -> None:
        return None

    def predict_cfl_dt(self) -> float:
        return 1.0

    def register_dynamic_boundary(self, tag, provider) -> None:
        self.dynamic_state[tag] = list(provider if not callable(provider) else provider(0.0))
        self.active_boundary[tag] = False

    def activate_dynamic_boundary(self, tag, active: bool) -> None:
        self.active_boundary[tag] = bool(active)

    def set_dynamic_boundary_state(self, tag, state) -> None:
        self.dynamic_state[tag] = list(state)

    def clear_exchange_Q(self) -> None:
        self.exchange_q = {key: 0.0 for key in self.exchange_q}

    def set_exchange_Q(self, link_id: str, discharge: float) -> None:
        self.exchange_q[link_id] = float(discharge)

    def advance_one_step(self, dt: float) -> float:
        self.volume += sum(self.exchange_q.values()) * dt
        self.relative_time += dt
        if self.stage_sequence:
            self.boundary_stage = self.stage_sequence[min(self._seq_index, len(self.stage_sequence) - 1)]
            self._seq_index += 1
        return dt

    def advance_to(self, target_time: float, mode=None) -> float:
        return self.advance_one_step(target_time - self.relative_time)

    def sample_boundary_stage(self, tag: str) -> float:
        return self.boundary_stage

    def sample_boundary_flux(self, tag: str) -> float:
        return 0.0

    def sample_stage(self, region) -> float:
        return self.boundary_stage

    def snapshot(self):
        return {
            'boundary_stage': self.boundary_stage,
            'volume': self.volume,
            'relative_time': self.relative_time,
            'exchange_q': dict(self.exchange_q),
            'dynamic_state': dict(self.dynamic_state),
            'active_boundary': dict(self.active_boundary),
            '_seq_index': self._seq_index,
        }

    def restore(self, snapshot) -> None:
        self.boundary_stage = snapshot['boundary_stage']
        self.volume = snapshot['volume']
        self.relative_time = snapshot['relative_time']
        self.exchange_q = dict(snapshot['exchange_q'])
        self.dynamic_state = dict(snapshot['dynamic_state'])
        self.active_boundary = dict(snapshot['active_boundary'])
        self._seq_index = snapshot['_seq_index']

    def get_total_volume(self) -> float:
        return self.volume


def make_manager(regime='sub', max_iter=1, one_d=None, two_d=None):
    one_d = FakeOneDAdapter(regime=regime) if one_d is None else one_d
    two_d = FakeTwoDAdapter() if two_d is None else two_d
    link = FrontalBoundaryLink.from_config(
        FrontalLinkConfig(
            link_id='front',
            river_name='river',
            river_boundary_side='right',
            river_boundary_node='n2',
            two_d_boundary_tag='front_tag',
            boundary_length=10.0,
            outward_normal=(1.0, 0.0),
            max_iter=max_iter,
            relax_factor=0.5,
            tol_stage=0.05,
            tol_Q=0.1,
        )
    )
    config = CouplingConfig(
        start_time=0.0,
        end_time=1.0,
        scheduler=SchedulerConfig(mode='fixed_interval', exchange_interval=1.0),
        frontal_links=[],
        lateral_links=[],
        diagnostics_dir='result/test_front',
    )
    manager = CouplingManager(one_d=one_d, two_d=two_d, config=config, lateral_links=[], frontal_links=[link])
    manager.initialize()
    return manager, link, one_d, two_d


def test_frontal_boundary_state_maps_q_to_normal_momentum():
    link = FrontalBoundaryLink.from_config(
        FrontalLinkConfig(
            link_id='front',
            river_name='river',
            river_boundary_side='right',
            river_boundary_node='n2',
            two_d_boundary_tag='front_tag',
            boundary_length=10.0,
            outward_normal=(1.0, 0.0),
        )
    )
    state = link.build_two_d_boundary_state(stage=2.0, discharge=20.0)
    assert state.tolist() == [2.0, -2.0, -0.0]


def test_subcritical_coupling_applies_stage_and_dynamic_boundary():
    manager, link, one_d, two_d = make_manager(regime='sub')
    guesses = manager.exchange_all_links(0.0, 1.0, 'fixed_interval')
    assert guesses['front']['regime'] == 'sub'
    assert one_d.stage_bc_calls[-1] == ('n2', two_d.boundary_stage)
    assert two_d.active_boundary['front_tag'] is True


def test_supercritical_in_deactivates_2d_dynamic_boundary():
    manager, link, one_d, two_d = make_manager(regime='super_in')
    guesses = manager.exchange_all_links(0.0, 1.0, 'fixed_interval')
    assert guesses['front']['regime'] == 'super_in'
    assert two_d.active_boundary['front_tag'] is False
    assert one_d.stage_bc_calls[-1] == ('n2', two_d.boundary_stage)


def test_frontal_link_relax_and_convergence_predicate():
    link = FrontalBoundaryLink.from_config(
        FrontalLinkConfig(
            link_id='front',
            river_name='river',
            river_boundary_side='right',
            river_boundary_node='n2',
            two_d_boundary_tag='front_tag',
            boundary_length=10.0,
            outward_normal=(1.0, 0.0),
            relax_factor=0.5,
            tol_stage=0.05,
            tol_Q=0.1,
        )
    )
    relaxed_stage, relaxed_q = link.relax_guess(1.0, 4.0, 1.2, 3.0)
    assert relaxed_stage == 1.1
    assert relaxed_q == 3.5
    assert link.converged(1.1, 3.5, 1.12, 3.45) is True
    assert link.converged(1.1, 3.5, 1.3, 3.45) is False


def test_picard_iteration_stops_at_protection_limit_when_not_converged():
    one_d = FakeOneDAdapter(regime='sub', discharge=4.0, discharge_sequence=[2.0, 3.05])
    two_d = FakeTwoDAdapter(boundary_stage=1.0, stage_sequence=[1.4, 1.23])
    manager, link, _, _ = make_manager(regime='sub', max_iter=3, one_d=one_d, two_d=two_d)
    guesses = manager.exchange_all_links(0.0, 1.0, 'fixed_interval')
    manager._run_picard_interval(0.0, 1.0, guesses)
    assert link.iteration_count == 3
    assert abs(link.current_stage - 1.4) < 1.0e-9
    assert abs(link.current_Q - 2.0) < 1.0e-9


def test_real_gpu_frontal_case_samples_boundary_stage_and_flux(tmp_path: Path):
    case = ExperimentCase(
        case_name='test_real_gpu_frontal',
        scheduler_mode='fixed_interval',
        exchange_interval=2.0,
        coupling_type='frontal_only',
        direction='river_to_floodplain',
        waveform='pulse',
        duration=6.0,
    )
    prepared = prepare_case(case, tmp_path / case.case_name)
    manager = prepared['manager']
    manager.run()
    stage = manager.two_d.sample_boundary_stage('front_tag')
    flux = manager.two_d.sample_boundary_flux('front_tag')
    assert isinstance(stage, float)
    assert isinstance(flux, float)
    assert any(row['link_id'] == 'front' for row in manager.exchange_history)
