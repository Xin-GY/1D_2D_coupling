from __future__ import annotations

import datetime as dt
import math
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from coupling.adapters_anuga_gpu import TwoDAnugaGpuAdapter
from coupling.adapters_rivernet import OneDNetworkAdapter
from coupling.config import CouplingConfig, FrontalLinkConfig, LateralLinkConfig, MeshRefinementConfig, SchedulerConfig
from coupling.links import FrontalBoundaryLink, LateralWeirLink
from coupling.manager import CouplingManager
from coupling.mesh_builder import RiverAwareMeshBuilder
from coupling.runtime_env import configure_runtime_environment
from demo.Rivernet import Rivernet


configure_runtime_environment(Path('/tmp/1d_2d_coupling_experiments'))

import anuga


SIM_START = dt.datetime(2024, 1, 1, 0, 0, 0)


@dataclass(slots=True)
class ExperimentCase:
    case_name: str
    scheduler_mode: str
    exchange_interval: float | None
    coupling_type: str
    direction: str
    waveform: str
    duration: float = 120.0
    one_d_yields: list[float] | None = None
    two_d_yields: list[float] | None = None

    def to_config_payload(self) -> dict[str, Any]:
        payload = asdict(self)
        payload['reference_case_name'] = f'{self.coupling_type}_{self.direction}_{self.waveform}_strict_global_min_dt'
        return payload


def _format_end_time(duration: float) -> str:
    end = SIM_START + dt.timedelta(seconds=float(duration))
    return end.strftime('%Y-%m-%d %H:%M:%S')


def _flow_boundary(case: ExperimentCase):
    duration = float(case.duration)

    def quasi_steady(t: float) -> float:
        if case.direction == 'river_to_floodplain':
            return 2.5 + 0.3 * (t / duration)
        if case.direction == 'floodplain_to_river':
            return 0.25
        return 1.2 + 0.4 * math.sin(2.0 * math.pi * t / duration)

    def pulse(t: float) -> float:
        if case.direction == 'floodplain_to_river':
            return 0.25 + 0.1 * math.exp(-((t - 0.4 * duration) ** 2) / (2.0 * (0.1 * duration) ** 2))
        return 1.0 + 2.5 * math.exp(-((t - 0.35 * duration) ** 2) / (2.0 * (0.08 * duration) ** 2))

    def triangle_or_square(t: float) -> float:
        phase = (t % 120.0) / 120.0
        if case.direction == 'bidirectional':
            triangle = 1.0 - abs(2.0 * phase - 1.0)
            return 0.8 + 1.4 * triangle
        return 2.0 if phase < 0.5 else 0.8

    mapping = {
        'quasi_steady': quasi_steady,
        'pulse': pulse,
        'triangle_or_square': triangle_or_square,
    }
    return mapping[case.waveform]


def _downstream_stage_boundary(case: ExperimentCase):
    if case.direction == 'river_to_floodplain':
        return lambda t: 0.85
    if case.direction == 'floodplain_to_river':
        return lambda t: 0.35
    return lambda t: 0.75 + 0.05 * math.sin(2.0 * math.pi * t / 180.0)


def _initial_levels(case: ExperimentCase) -> tuple[float, float]:
    if case.direction == 'river_to_floodplain':
        return 1.05, 0.55
    if case.direction == 'floodplain_to_river':
        return 0.45, 1.10
    return 0.78, 0.82


def _make_topology(output_path: str, duration: float) -> tuple[dict[tuple[str, str], dict[str, Any]], dict[str, Any]]:
    model_data = {
        'model_name': 'coupling_sweep',
        'sim_start_time': SIM_START.strftime('%Y-%m-%d %H:%M:%S'),
        'sim_end_time': _format_end_time(duration),
        'time_step': 10.0,
        'output_path': output_path,
        'CFL': 0.3,
    }
    river_data = {
        'cell_num': 4,
        'pos': [[i * 5.0, 0.0, 1.0 - 0.02 * i] for i in range(5)],
        'section_name': [f'se{i + 1}' for i in range(4)],
    }
    section_data = {
        name: [[0.0, 2.0], [0.0, 0.0], [3.0, 0.0], [3.0, 2.0]]
        for name in river_data['section_name']
    }
    section_pos = {
        name: [2.5 + idx * 5.0, 0.0]
        for idx, name in enumerate(river_data['section_name'])
    }
    topology = {
        ('n1', 'n2'): {
            'name': 'mainstem',
            'river_data': river_data,
            'section_data': section_data,
            'section_pos': section_pos,
            'model_data': model_data,
            'manning': 0.025,
        }
    }
    return topology, model_data


def _make_domain(mesh_path: Path, case: ExperimentCase, initial_2d_stage: float):
    builder = RiverAwareMeshBuilder(
        MeshRefinementConfig(
            maximum_triangle_area=4.0,
            channel_exclusion_half_width=1.0,
            river_refinement_half_width=2.0,
            river_refinement_area=2.0,
            frontal_refinement_half_width=1.5,
            frontal_refinement_area=1.5,
            lateral_region_half_width=1.5,
            lateral_region_area=1.5,
            prefer_channel_hole=False,
        )
    )
    mesh = builder.build(
        floodplain_polygon=[[0.0, 0.0], [20.0, 0.0], [20.0, 20.0], [0.0, 20.0]],
        centerline=[[2.0, 10.0], [18.0, 10.0]],
        direct_connection_lines={'front': [[18.0, 8.0], [18.0, 12.0]]},
        lateral_links={'lateral_demo': [[8.0, 12.0], [12.0, 12.0]]},
    )
    boundary_tags = {'bottom': [0], 'front_tag': [1], 'top': [2], 'left': [3]}
    domain = anuga.create_domain_from_regions(
        mesh.bounding_polygon,
        boundary_tags=boundary_tags,
        maximum_triangle_area=4.0,
        mesh_filename=str(mesh_path),
        minimum_triangle_angle=28.0,
        use_cache=True,
        verbose=False,
    )
    domain.set_name(case.case_name)
    domain.set_minimum_storable_height(0.001)
    domain.set_minimum_allowed_height(0.001)
    domain.set_quantity('elevation', lambda x, y: 0.2 + 0.02 * (x / 20.0) + 0.05 * (y > 10.0))
    domain.set_quantity('friction', 0.03, location='centroids')
    domain.set_quantity('stage', initial_2d_stage, location='centroids')
    boundary = anuga.Reflective_boundary(domain)
    domain.set_boundary({'left': boundary, 'top': boundary, 'bottom': boundary, 'front_tag': anuga.Transmissive_boundary(domain)})
    lateral_regions = {
        link_id: anuga.Region(domain=domain, poly=poly, expand_polygon=True)
        for link_id, poly in mesh.lateral_exchange_regions.items()
    }
    return domain, mesh, lateral_regions


def prepare_case(case: ExperimentCase, output_dir: Path) -> dict[str, Any]:
    topology, model_data = _make_topology(str(output_dir), case.duration)
    network = Rivernet(topology, model_data, verbos=False)
    initial_1d_stage, initial_2d_stage = _initial_levels(case)
    for _, _, data in network.G.edges(data=True):
        data['river'].Set_init_water_level(initial_1d_stage)

    network.set_boundary('n1', 'flow', _flow_boundary(case))
    network.set_boundary('n2', 'fix_level', _downstream_stage_boundary(case))

    mesh_path = output_dir / f'{case.case_name}.msh'
    domain, mesh, lateral_regions = _make_domain(mesh_path, case, initial_2d_stage)
    one_d = OneDNetworkAdapter(network)
    two_d = TwoDAnugaGpuAdapter(domain, multiprocessor_mode=4)

    lateral_links: list[LateralWeirLink] = []
    frontal_links: list[FrontalBoundaryLink] = []
    if case.coupling_type in {'lateral_only', 'mixed'}:
        two_d.initialize_gpu()
        two_d.register_exchange_region('lateral_demo', lateral_regions['lateral_demo'], mode='fast')
        lateral_links.append(
            LateralWeirLink.from_config(
                LateralLinkConfig(
                    link_id='lateral_demo',
                    river_name='mainstem',
                    region_id='lateral_demo',
                    river_cells=[2, 3, 4],
                    segment_lengths=[2.0, 2.0, 2.0],
                    crest_levels=[0.78, 0.78, 0.78],
                    discharge_coefficient=0.7,
                    two_d_sample=[lateral_regions['lateral_demo']] * 3,
                )
            )
        )

    if case.coupling_type in {'frontal_only', 'mixed'}:
        frontal_links.append(
            FrontalBoundaryLink.from_config(
                FrontalLinkConfig(
                    link_id='front',
                    river_name='mainstem',
                    river_boundary_side='right',
                    river_boundary_node='n2',
                    two_d_boundary_tag='front_tag',
                    boundary_length=20.0,
                    outward_normal=(1.0, 0.0),
                    max_iter=2 if case.scheduler_mode != 'strict_global_min_dt' else 1,
                )
            )
        )

    scheduler = SchedulerConfig(
        mode=case.scheduler_mode,
        exchange_interval=case.exchange_interval,
        one_d_yields=list(case.one_d_yields or []),
        two_d_yields=list(case.two_d_yields or []),
    )
    manager = CouplingManager(
        one_d=one_d,
        two_d=two_d,
        config=CouplingConfig(
            start_time=0.0,
            end_time=float(case.duration),
            scheduler=scheduler,
            diagnostics_dir=str(output_dir),
        ),
        lateral_links=lateral_links,
        frontal_links=frontal_links,
    )
    return {
        'manager': manager,
        'mesh': mesh,
        'config_payload': case.to_config_payload(),
        'control_point_1d': ('mainstem_mid', 'mainstem', 2),
        'control_region_2d': ('floodplain_probe', lateral_regions['lateral_demo']),
    }


def generate_case_matrix() -> list[ExperimentCase]:
    cases: list[ExperimentCase] = []
    base_type = 'mixed'
    base_direction = 'bidirectional'
    base_waveform = 'pulse'
    scheduler_cases = [
        ('strict_global_min_dt', None),
        ('yield_schedule', None),
        ('fixed_interval', 1.0),
        ('fixed_interval', 3.0),
        ('fixed_interval', 5.0),
        ('fixed_interval', 10.0),
        ('fixed_interval', 15.0),
        ('fixed_interval', 30.0),
        ('fixed_interval', 60.0),
        ('fixed_interval', 300.0),
    ]
    for mode, interval in scheduler_cases:
        name = mode if interval is None else f'fixed_interval_{int(interval):03d}s'
        cases.append(
            ExperimentCase(
                case_name=f'{base_type}_{base_direction}_{base_waveform}_{name}',
                scheduler_mode=mode,
                exchange_interval=interval,
                coupling_type=base_type,
                direction=base_direction,
                waveform=base_waveform,
                one_d_yields=[20.0, 50.0, 80.0, 110.0],
                two_d_yields=[30.0, 60.0, 90.0],
            )
        )

    for coupling_type in ('lateral_only', 'frontal_only', 'mixed'):
        cases.append(
            ExperimentCase(
                case_name=f'{coupling_type}_river_to_floodplain_quasi_steady_strict_global_min_dt',
                scheduler_mode='strict_global_min_dt',
                exchange_interval=None,
                coupling_type=coupling_type,
                direction='river_to_floodplain',
                waveform='quasi_steady',
            )
        )

    for direction in ('river_to_floodplain', 'floodplain_to_river', 'bidirectional'):
        cases.append(
            ExperimentCase(
                case_name=f'mixed_{direction}_pulse_strict_global_min_dt',
                scheduler_mode='strict_global_min_dt',
                exchange_interval=None,
                coupling_type='mixed',
                direction=direction,
                waveform='pulse',
            )
        )

    for waveform in ('quasi_steady', 'pulse', 'triangle_or_square'):
        cases.append(
            ExperimentCase(
                case_name=f'mixed_river_to_floodplain_{waveform}_strict_global_min_dt',
                scheduler_mode='strict_global_min_dt',
                exchange_interval=None,
                coupling_type='mixed',
                direction='river_to_floodplain',
                waveform=waveform,
            )
        )
    unique_cases: list[ExperimentCase] = []
    seen: set[str] = set()
    for case in cases:
        if case.case_name in seen:
            continue
        seen.add(case.case_name)
        unique_cases.append(case)
    return unique_cases
