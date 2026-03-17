from __future__ import annotations

import datetime as dt
import math
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

import numpy as np

from coupling.adapters_anuga_gpu import TwoDAnugaGpuAdapter
from coupling.adapters_rivernet import OneDNetworkAdapter
from coupling.config import CouplingConfig, FrontalLinkConfig, LateralLinkConfig, MeshRefinementConfig, SchedulerConfig
from coupling.links import FrontalBoundaryLink, LateralWeirLink
from coupling.manager import CouplingManager
from coupling.mesh_builder import RiverAwareMeshBuilder
from coupling.runtime_env import configure_runtime_environment, repair_anuga_editable_build_env
from experiments.io import ensure_dir
from experiments.one_d_backends import DEFAULT_ONE_D_BACKEND, create_oned_network
from experiments.test7_data import Test7DataProvenance


repair_anuga_editable_build_env()
configure_runtime_environment(Path('/tmp/1d_2d_coupling_chapter_cases'))

import anuga


SIM_START = dt.datetime(2024, 1, 1, 0, 0, 0)
FIXED_INTERVALS = [0.5, 1.0, 2.0, 3.0, 5.0, 7.5, 10.0, 15.0, 20.0, 30.0, 60.0, 120.0, 300.0]
TEST7_TEST_PROFILE_INTERVALS = [2.0, 3.0, 5.0, 10.0, 15.0, 30.0, 60.0, 300.0]
SMALL_TEST_PROFILE_INTERVALS = [2.0, 5.0, 15.0, 60.0, 300.0]


@dataclass(slots=True)
class OneDProbeDef:
    probe_id: str
    river_name: str
    cell_id: int


@dataclass(slots=True)
class TwoDProbeDef:
    probe_id: str
    polygon: list[list[float]]


@dataclass(slots=True)
class DischargeProbeDef:
    probe_id: str
    river_name: str
    side: str


@dataclass(slots=True)
class ChapterExperimentCase:
    case_name: str
    scenario_family: str
    scheduler_mode: str
    exchange_interval: float | None
    coupling_type: str
    direction: str
    waveform: str
    duration: float
    reference_policy: str
    partition_defs: dict[str, list[list[float]]] = field(default_factory=dict)
    probe_defs: dict[str, Any] = field(default_factory=dict)
    link_probe_ids: list[str] = field(default_factory=list)
    analysis_raster: dict[str, Any] = field(default_factory=dict)
    case_variant: str = 'synthetic'
    data_provenance: dict[str, Any] = field(default_factory=dict)
    runtime_profile: str = 'paper'
    one_d_yields: list[float] = field(default_factory=list)
    two_d_yields: list[float] = field(default_factory=list)
    mesh_variant: str = 'baseline'
    one_d_backend: str = DEFAULT_ONE_D_BACKEND

    def reference_case_name(self) -> str:
        return f'{self.scenario_family}_strict_global_min_dt'

    def to_config_payload(self) -> dict[str, Any]:
        payload = asdict(self)
        payload['reference_case_name'] = self.reference_case_name()
        return payload


def _format_end_time(duration: float) -> str:
    end = SIM_START + dt.timedelta(seconds=float(duration))
    return end.strftime('%Y-%m-%d %H:%M:%S')


def _fixed_interval_label(interval: float) -> str:
    interval_f = float(interval)
    if float(interval_f).is_integer():
        return f'fixed_interval_{int(interval_f):03d}s'
    whole = int(interval_f)
    frac = str(interval_f).split('.')[1].rstrip('0')
    return f'fixed_interval_{whole:03d}p{frac}s'


def _cell_index_from_fraction(cell_num: int, fraction: float) -> int:
    return int(min(max(round(float(fraction) * float(cell_num)), 1), int(cell_num)))


def _square(cx: float, cy: float, half_size: float) -> list[list[float]]:
    return [
        [float(cx - half_size), float(cy - half_size)],
        [float(cx + half_size), float(cy - half_size)],
        [float(cx + half_size), float(cy + half_size)],
        [float(cx - half_size), float(cy + half_size)],
    ]


def _rectangle(x0: float, y0: float, x1: float, y1: float) -> list[list[float]]:
    return [[float(x0), float(y0)], [float(x1), float(y0)], [float(x1), float(y1)], [float(x0), float(y1)]]


def _build_topology(
    *,
    output_path: str,
    duration: float,
    model_name: str,
    river_name: str,
    length: float,
    cell_num: int,
    bed_elev_upstream: float,
    bed_drop: float,
    section_width: float,
) -> tuple[dict[tuple[str, str], dict[str, Any]], dict[str, Any]]:
    model_data = {
        'model_name': model_name,
        'sim_start_time': SIM_START.strftime('%Y-%m-%d %H:%M:%S'),
        'sim_end_time': _format_end_time(duration),
        'time_step': 10.0,
        'output_path': output_path,
        'CFL': 0.3,
    }
    dx = float(length) / float(cell_num)
    pos = []
    for idx in range(cell_num + 1):
        x = float(idx) * dx
        z = float(bed_elev_upstream) - float(bed_drop) * (float(idx) / float(cell_num))
        pos.append([x, 0.0, z])
    river_data = {
        'cell_num': int(cell_num),
        'pos': pos,
        'section_name': [f'{river_name}_se{idx + 1}' for idx in range(cell_num)],
    }
    section_data = {
        name: [[0.0, 4.0], [0.0, 0.0], [float(section_width), 0.0], [float(section_width), 4.0]]
        for name in river_data['section_name']
    }
    section_pos = {
        name: [dx * (idx + 0.5), 0.0]
        for idx, name in enumerate(river_data['section_name'])
    }
    topology = {
        ('n1', 'n2'): {
            'name': river_name,
            'river_data': river_data,
            'section_data': section_data,
            'section_pos': section_pos,
            'model_data': model_data,
            'manning': 0.028,
        }
    }
    return topology, model_data


def _flow_boundary(case: ChapterExperimentCase):
    duration = float(case.duration)

    if case.scenario_family == 'official_test7_overtopping_only_variant' or case.scenario_family == 'surrogate_test7_overtopping_only_variant':
        def benchmark_pulse(t: float) -> float:
            base = 18.0
            wave1 = 16.0 * math.exp(-((t - 0.22 * duration) ** 2) / (2.0 * (0.08 * duration) ** 2))
            wave2 = 8.0 * math.exp(-((t - 0.58 * duration) ** 2) / (2.0 * (0.12 * duration) ** 2))
            return base + wave1 + wave2

        return benchmark_pulse

    if case.scenario_family == 'frontal_basin_fill':
        return lambda t: 1.2 + 1.8 * (1.0 - math.exp(-t / max(duration * 0.18, 1.0)))

    if case.scenario_family == 'lateral_overtopping_return':
        return lambda t: 0.8 + 2.8 * math.exp(-((t - 0.30 * duration) ** 2) / (2.0 * (0.10 * duration) ** 2))

    if case.scenario_family == 'early_arrival_pulse':
        return lambda t: 0.4 + 4.0 * math.exp(-((t - 0.08 * duration) ** 2) / (2.0 * (0.04 * duration) ** 2))

    return lambda t: 0.9 + 1.6 * math.sin(2.0 * math.pi * t / max(duration, 1.0)) + 1.2 * math.exp(-((t - 0.55 * duration) ** 2) / (2.0 * (0.12 * duration) ** 2))


def _downstream_stage_boundary(case: ChapterExperimentCase):
    duration = float(case.duration)

    if case.scenario_family == 'official_test7_overtopping_only_variant' or case.scenario_family == 'surrogate_test7_overtopping_only_variant':
        return lambda t: 1.05 + 0.08 * math.sin(2.0 * math.pi * t / max(duration, 1.0))

    if case.scenario_family == 'frontal_basin_fill':
        return lambda t: 0.45

    if case.scenario_family == 'lateral_overtopping_return':
        return lambda t: 0.55 + 0.06 * math.sin(2.0 * math.pi * t / max(duration * 0.75, 1.0))

    if case.scenario_family == 'early_arrival_pulse':
        return lambda t: 0.40

    return lambda t: 0.90 + 0.18 * math.sin(2.0 * math.pi * t / max(duration * 0.60, 1.0))


def _initial_levels(case: ChapterExperimentCase) -> tuple[float, float]:
    if case.scenario_family == 'official_test7_overtopping_only_variant' or case.scenario_family == 'surrogate_test7_overtopping_only_variant':
        return 1.28, 0.42
    if case.scenario_family == 'frontal_basin_fill':
        return 0.92, 0.38
    if case.scenario_family == 'lateral_overtopping_return':
        return 0.98, 0.56
    if case.scenario_family == 'early_arrival_pulse':
        return 0.82, 0.24
    return 0.88, 0.74


def _base_mesh_config(scale: str) -> MeshRefinementConfig:
    if scale == 'benchmark':
        return MeshRefinementConfig(
            maximum_triangle_area=1800.0,
            channel_exclusion_half_width=18.0,
            river_refinement_half_width=45.0,
            river_refinement_area=600.0,
            levee_refinement_half_width=18.0,
            levee_refinement_area=280.0,
            frontal_refinement_half_width=28.0,
            frontal_refinement_area=220.0,
            lateral_region_half_width=24.0,
            lateral_region_area=220.0,
            prefer_channel_hole=False,
        )
    return MeshRefinementConfig(
        maximum_triangle_area=18.0,
        channel_exclusion_half_width=2.0,
        river_refinement_half_width=5.0,
        river_refinement_area=4.0,
        levee_refinement_half_width=2.0,
        levee_refinement_area=2.0,
        frontal_refinement_half_width=3.0,
        frontal_refinement_area=2.0,
        lateral_region_half_width=3.0,
        lateral_region_area=2.0,
        prefer_channel_hole=False,
    )


def _apply_mesh_variant(mesh_config: MeshRefinementConfig, mesh_variant: str) -> MeshRefinementConfig:
    if mesh_variant != 'refined_figures':
        return mesh_config
    mesh_config.maximum_triangle_area *= 0.5
    mesh_config.river_refinement_area *= 0.5
    mesh_config.levee_refinement_area *= 0.5
    mesh_config.frontal_refinement_area *= 0.5
    mesh_config.lateral_region_area *= 0.5
    return mesh_config


def _scenario_spec(case: ChapterExperimentCase) -> dict[str, Any]:
    if case.scenario_family in {'official_test7_overtopping_only_variant', 'surrogate_test7_overtopping_only_variant'}:
        benchmark_scale = 'benchmark'
        paper = case.runtime_profile == 'paper'
        length = 1200.0 if paper else 720.0
        height = 360.0 if paper else 240.0
        cell_num = 24 if paper else 16
        center_y = height * 0.50
        floodplain_polygon = _rectangle(0.0, 0.0, length, height)
        centerline = [[40.0, center_y], [length - 50.0, center_y]]
        levee_lines: list[list[list[float]]] = []
        lateral_lines = {
            'fp1_overtop': [[length * 0.16, center_y + 32.0], [length * 0.24, center_y + 32.0]],
            'fp2_return': [[length * 0.46, center_y - 36.0], [length * 0.56, center_y - 36.0]],
            'fp3_overtop': [[length * 0.74, center_y + 30.0], [length * 0.84, center_y + 30.0]],
        }
        partition_defs = {
            'Floodplain_1': _rectangle(0.0, 0.0, length * 0.33, height),
            'Floodplain_2': _rectangle(length * 0.33, 0.0, length * 0.66, height),
            'Floodplain_3': _rectangle(length * 0.66, 0.0, length, height),
        }
        frontal_boundary_tag = 'front_tag'
        direct_connection_lines = {'front_main': [[length - 70.0, center_y - 42.0], [length - 70.0, center_y + 42.0]]}
        mesh_config = _apply_mesh_variant(_base_mesh_config(benchmark_scale), case.mesh_variant)
        if not paper:
            mesh_config.maximum_triangle_area = 1200.0
            mesh_config.river_refinement_area = 420.0
            mesh_config.frontal_refinement_area = 180.0
            mesh_config.lateral_region_area = 180.0
            if case.mesh_variant == 'refined_figures':
                mesh_config = _apply_mesh_variant(mesh_config, case.mesh_variant)

        one_d_probes = [
            OneDProbeDef('upstream_1d', 'mainstem', _cell_index_from_fraction(cell_num, 0.20)),
            OneDProbeDef('mainstem_mid', 'mainstem', _cell_index_from_fraction(cell_num, 0.52)),
            OneDProbeDef('downstream_1d', 'mainstem', _cell_index_from_fraction(cell_num, 0.82)),
        ]
        two_d_probes = [
            TwoDProbeDef('fp1_probe', _square(length * 0.18, center_y + 74.0, 18.0 if paper else 12.0)),
            TwoDProbeDef('fp2_probe', _square(length * 0.50, center_y - 84.0, 18.0 if paper else 12.0)),
            TwoDProbeDef('fp3_probe', _square(length * 0.82, center_y + 72.0, 18.0 if paper else 12.0)),
        ]
        discharge_probes = [
            DischargeProbeDef('mainstem_left_q', 'mainstem', 'left'),
            DischargeProbeDef('mainstem_right_q', 'mainstem', 'right'),
        ]
        lateral_configs = [
            LateralLinkConfig(
                link_id='fp1_overtop',
                river_name='mainstem',
                region_id='fp1_overtop',
                river_cells=[_cell_index_from_fraction(cell_num, 0.16), _cell_index_from_fraction(cell_num, 0.18), _cell_index_from_fraction(cell_num, 0.20)],
                segment_lengths=[18.0, 18.0, 18.0],
                crest_levels=[1.06, 1.04, 1.02],
                discharge_coefficient=0.68,
                metadata={'partition': 'Floodplain_1', 'link_type': 'lateral_overtopping'},
            ),
            LateralLinkConfig(
                link_id='fp2_return',
                river_name='mainstem',
                region_id='fp2_return',
                river_cells=[_cell_index_from_fraction(cell_num, 0.48), _cell_index_from_fraction(cell_num, 0.50), _cell_index_from_fraction(cell_num, 0.52)],
                segment_lengths=[20.0, 20.0, 20.0],
                crest_levels=[0.92, 0.92, 0.92],
                discharge_coefficient=0.72,
                metadata={'partition': 'Floodplain_2', 'link_type': 'lateral_return'},
            ),
            LateralLinkConfig(
                link_id='fp3_overtop',
                river_name='mainstem',
                region_id='fp3_overtop',
                river_cells=[_cell_index_from_fraction(cell_num, 0.76), _cell_index_from_fraction(cell_num, 0.79), _cell_index_from_fraction(cell_num, 0.82)],
                segment_lengths=[18.0, 18.0, 18.0],
                crest_levels=[1.00, 1.00, 0.98],
                discharge_coefficient=0.70,
                metadata={'partition': 'Floodplain_3', 'link_type': 'lateral_overtopping'},
            ),
        ]
        frontal_configs = [
            FrontalLinkConfig(
                link_id='front_main',
                river_name='mainstem',
                river_boundary_side='right',
                river_boundary_node='n2',
                two_d_boundary_tag=frontal_boundary_tag,
                boundary_length=height * 0.28,
                outward_normal=(1.0, 0.0),
                max_iter=2 if case.scheduler_mode != 'strict_global_min_dt' else 1,
                metadata={'partition': 'Floodplain_3', 'link_type': 'frontal_direct'},
            )
        ]
        snapshot_times = [duration * ratio for duration, ratio in [(case.duration, 0.18), (case.duration, 0.38), (case.duration, 0.62), (case.duration, 0.88)]]
        return {
            'model_name': case.scenario_family,
            'river_name': 'mainstem',
            'length': length,
            'cell_num': cell_num,
            'bed_elev_upstream': 0.95,
            'bed_drop': 0.32,
            'section_width': 18.0,
            'floodplain_polygon': floodplain_polygon,
            'centerline': centerline,
            'levee_lines': levee_lines,
            'lateral_lines': lateral_lines,
            'direct_connection_lines': direct_connection_lines,
            'mesh_config': mesh_config,
            'partition_defs': partition_defs,
            'one_d_probes': one_d_probes,
            'two_d_probes': two_d_probes,
            'discharge_probes': discharge_probes,
            'lateral_configs': lateral_configs,
            'frontal_configs': frontal_configs,
            'snapshot_times': snapshot_times,
            'primary_stage_probe': 'mainstem_mid',
            'primary_discharge_probe': 'mainstem_right_q',
            'field_wet_threshold': 0.02,
        }

    if case.scenario_family == 'frontal_basin_fill':
        length = 160.0 if case.runtime_profile == 'paper' else 110.0
        height = 60.0 if case.runtime_profile == 'paper' else 48.0
        cell_num = 12 if case.runtime_profile == 'paper' else 10
        center_y = height * 0.48
        return {
            'model_name': case.scenario_family,
            'river_name': 'mainstem',
            'length': length,
            'cell_num': cell_num,
            'bed_elev_upstream': 0.78,
            'bed_drop': 0.10,
            'section_width': 8.0,
            'floodplain_polygon': _rectangle(0.0, 0.0, length, height),
            'centerline': [[0.0, center_y], [length, center_y]],
            'levee_lines': [],
            'lateral_lines': {},
            'direct_connection_lines': {'front_main': [[length - 8.0, center_y - 10.0], [length - 8.0, center_y + 10.0]]},
            'mesh_config': _apply_mesh_variant(_base_mesh_config('small'), case.mesh_variant),
            'partition_defs': {'basin': _rectangle(length * 0.55, 0.0, length, height)},
            'one_d_probes': [
                OneDProbeDef('upstream_1d', 'mainstem', _cell_index_from_fraction(cell_num, 0.20)),
                OneDProbeDef('mainstem_mid', 'mainstem', _cell_index_from_fraction(cell_num, 0.55)),
            ],
            'two_d_probes': [TwoDProbeDef('basin_probe', _square(length * 0.78, center_y + 10.0, 6.0))],
            'discharge_probes': [DischargeProbeDef('mainstem_right_q', 'mainstem', 'right')],
            'lateral_configs': [],
            'frontal_configs': [
                FrontalLinkConfig(
                    link_id='front_main',
                    river_name='mainstem',
                    river_boundary_side='right',
                    river_boundary_node='n2',
                    two_d_boundary_tag='front_tag',
                    boundary_length=height * 0.35,
                    outward_normal=(1.0, 0.0),
                    max_iter=3 if case.scheduler_mode != 'strict_global_min_dt' else 1,
                    metadata={'partition': 'basin', 'link_type': 'frontal_direct'},
                )
            ],
            'snapshot_times': [case.duration * 0.15, case.duration * 0.35, case.duration * 0.6, case.duration * 0.9],
            'primary_stage_probe': 'mainstem_mid',
            'primary_discharge_probe': 'mainstem_right_q',
            'field_wet_threshold': 0.01,
            # Keep the breakline-aligned frontal geometry, but avoid the
            # additional interior refinement polygons that can stall Triangle
            # on this very small direct-connection benchmark.
            'use_interior_regions': False,
        }

    if case.scenario_family == 'lateral_overtopping_return':
        length = 200.0 if case.runtime_profile == 'paper' else 140.0
        height = 80.0 if case.runtime_profile == 'paper' else 56.0
        cell_num = 14 if case.runtime_profile == 'paper' else 10
        center_y = height * 0.52
        return {
            'model_name': case.scenario_family,
            'river_name': 'mainstem',
            'length': length,
            'cell_num': cell_num,
            'bed_elev_upstream': 0.82,
            'bed_drop': 0.12,
            'section_width': 8.0,
            'floodplain_polygon': _rectangle(0.0, 0.0, length, height),
            'centerline': [[0.0, center_y], [length, center_y]],
            'levee_lines': [[[length * 0.28, center_y + 10.0], [length * 0.52, center_y + 10.0]]],
            'lateral_lines': {'return_link': [[length * 0.32, center_y + 12.0], [length * 0.48, center_y + 12.0]]},
            'direct_connection_lines': {},
            'mesh_config': _apply_mesh_variant(_base_mesh_config('small'), case.mesh_variant),
            'partition_defs': {'storage_plain': _rectangle(length * 0.25, center_y + 8.0, length * 0.75, height)},
            'one_d_probes': [
                OneDProbeDef('upstream_1d', 'mainstem', _cell_index_from_fraction(cell_num, 0.24)),
                OneDProbeDef('mainstem_mid', 'mainstem', _cell_index_from_fraction(cell_num, 0.46)),
            ],
            'two_d_probes': [TwoDProbeDef('floodplain_probe', _square(length * 0.45, center_y + 22.0, 6.0))],
            'discharge_probes': [DischargeProbeDef('mainstem_right_q', 'mainstem', 'right')],
            'lateral_configs': [
                LateralLinkConfig(
                    link_id='return_link',
                    river_name='mainstem',
                    region_id='return_link',
                    river_cells=[_cell_index_from_fraction(cell_num, 0.34), _cell_index_from_fraction(cell_num, 0.40), _cell_index_from_fraction(cell_num, 0.46)],
                    segment_lengths=[6.0, 6.0, 6.0],
                    crest_levels=[0.86, 0.86, 0.86],
                    discharge_coefficient=0.72,
                    metadata={'partition': 'storage_plain', 'link_type': 'lateral_overtopping_return'},
                )
            ],
            'frontal_configs': [],
            'snapshot_times': [case.duration * 0.12, case.duration * 0.35, case.duration * 0.58, case.duration * 0.88],
            'primary_stage_probe': 'mainstem_mid',
            'primary_discharge_probe': 'mainstem_right_q',
            'field_wet_threshold': 0.01,
            'use_interior_regions': False,
        }

    if case.scenario_family == 'early_arrival_pulse':
        length = 150.0 if case.runtime_profile == 'paper' else 120.0
        height = 72.0 if case.runtime_profile == 'paper' else 52.0
        cell_num = 14 if case.runtime_profile == 'paper' else 10
        center_y = height * 0.50
        return {
            'model_name': case.scenario_family,
            'river_name': 'mainstem',
            'length': length,
            'cell_num': cell_num,
            'bed_elev_upstream': 0.75,
            'bed_drop': 0.08,
            'section_width': 7.0,
            'floodplain_polygon': _rectangle(0.0, 0.0, length, height),
            'centerline': [[0.0, center_y], [length * 0.72, center_y], [length, center_y + 4.0]],
            'levee_lines': [[[length * 0.18, center_y + 10.0], [length * 0.46, center_y + 10.0]]],
            'lateral_lines': {'early_link': [[length * 0.22, center_y + 10.0], [length * 0.40, center_y + 10.0]]},
            'direct_connection_lines': {'front_main': [[length - 10.0, center_y - 10.0], [length - 10.0, center_y + 10.0]]},
            'mesh_config': _apply_mesh_variant(_base_mesh_config('small'), case.mesh_variant),
            'partition_defs': {'arrival_plain': _rectangle(length * 0.18, center_y + 6.0, length * 0.92, height)},
            'one_d_probes': [
                OneDProbeDef('arrival_upstream', 'mainstem', _cell_index_from_fraction(cell_num, 0.16)),
                OneDProbeDef('mainstem_mid', 'mainstem', _cell_index_from_fraction(cell_num, 0.34)),
                OneDProbeDef('arrival_downstream', 'mainstem', _cell_index_from_fraction(cell_num, 0.78)),
            ],
            'two_d_probes': [TwoDProbeDef('arrival_plain_probe', _square(length * 0.55, center_y + 18.0, 5.0))],
            'discharge_probes': [DischargeProbeDef('mainstem_right_q', 'mainstem', 'right')],
            'lateral_configs': [
                LateralLinkConfig(
                    link_id='early_link',
                    river_name='mainstem',
                    region_id='early_link',
                    river_cells=[_cell_index_from_fraction(cell_num, 0.20), _cell_index_from_fraction(cell_num, 0.26), _cell_index_from_fraction(cell_num, 0.32)],
                    segment_lengths=[5.0, 5.0, 5.0],
                    crest_levels=[0.78, 0.78, 0.78],
                    discharge_coefficient=0.70,
                    metadata={'partition': 'arrival_plain', 'link_type': 'lateral_early_arrival'},
                )
            ],
            'frontal_configs': [
                FrontalLinkConfig(
                    link_id='front_main',
                    river_name='mainstem',
                    river_boundary_side='right',
                    river_boundary_node='n2',
                    two_d_boundary_tag='front_tag',
                    boundary_length=height * 0.28,
                    outward_normal=(1.0, 0.0),
                    max_iter=2 if case.scheduler_mode != 'strict_global_min_dt' else 1,
                    metadata={'partition': 'arrival_plain', 'link_type': 'frontal_direct'},
                )
            ],
            'snapshot_times': [case.duration * 0.08, case.duration * 0.18, case.duration * 0.42, case.duration * 0.75],
            'primary_stage_probe': 'mainstem_mid',
            'primary_discharge_probe': 'mainstem_right_q',
            'field_wet_threshold': 0.01,
            'use_interior_regions': False,
        }

    length = 220.0 if case.runtime_profile == 'paper' else 160.0
    height = 90.0 if case.runtime_profile == 'paper' else 64.0
    cell_num = 16 if case.runtime_profile == 'paper' else 12
    center_y = height * 0.48
    return {
        'model_name': case.scenario_family,
        'river_name': 'mainstem',
        'length': length,
        'cell_num': cell_num,
        'bed_elev_upstream': 0.88,
        'bed_drop': 0.16,
        'section_width': 9.0,
        'floodplain_polygon': _rectangle(0.0, 0.0, length, height),
        'centerline': [[0.0, center_y], [length * 0.45, center_y - 4.0], [length, center_y + 3.0]],
        'levee_lines': [
            [[length * 0.24, center_y + 14.0], [length * 0.52, center_y + 14.0]],
            [[length * 0.58, center_y - 18.0], [length * 0.78, center_y - 18.0]],
        ],
        'lateral_lines': {
            'backwater_link': [[length * 0.28, center_y + 14.0], [length * 0.46, center_y + 14.0]],
            'mixed_return_link': [[length * 0.62, center_y - 16.0], [length * 0.74, center_y - 16.0]],
        },
        'direct_connection_lines': {'front_main': [[length - 12.0, center_y - 14.0], [length - 12.0, center_y + 14.0]]},
        'mesh_config': _apply_mesh_variant(_base_mesh_config('small'), case.mesh_variant),
        'partition_defs': {
            'upper_backwater_plain': _rectangle(length * 0.20, center_y + 10.0, length * 0.62, height),
            'lower_return_plain': _rectangle(length * 0.56, 0.0, length * 0.88, center_y - 8.0),
        },
        'one_d_probes': [
            OneDProbeDef('upstream_1d', 'mainstem', _cell_index_from_fraction(cell_num, 0.20)),
            OneDProbeDef('mainstem_mid', 'mainstem', _cell_index_from_fraction(cell_num, 0.48)),
            OneDProbeDef('downstream_1d', 'mainstem', _cell_index_from_fraction(cell_num, 0.78)),
        ],
        'two_d_probes': [
            TwoDProbeDef('upper_plain_probe', _square(length * 0.44, center_y + 22.0, 6.0)),
            TwoDProbeDef('lower_plain_probe', _square(length * 0.72, center_y - 24.0, 6.0)),
        ],
        'discharge_probes': [DischargeProbeDef('mainstem_right_q', 'mainstem', 'right')],
        'lateral_configs': [
            LateralLinkConfig(
                link_id='backwater_link',
                river_name='mainstem',
                region_id='backwater_link',
                river_cells=[_cell_index_from_fraction(cell_num, 0.28), _cell_index_from_fraction(cell_num, 0.34), _cell_index_from_fraction(cell_num, 0.40)],
                segment_lengths=[7.0, 7.0, 7.0],
                crest_levels=[0.94, 0.94, 0.94],
                discharge_coefficient=0.72,
                metadata={'partition': 'upper_backwater_plain', 'link_type': 'lateral_backwater'},
            ),
            LateralLinkConfig(
                link_id='mixed_return_link',
                river_name='mainstem',
                region_id='mixed_return_link',
                river_cells=[_cell_index_from_fraction(cell_num, 0.62), _cell_index_from_fraction(cell_num, 0.68), _cell_index_from_fraction(cell_num, 0.74)],
                segment_lengths=[6.0, 6.0, 6.0],
                crest_levels=[0.84, 0.84, 0.84],
                discharge_coefficient=0.74,
                metadata={'partition': 'lower_return_plain', 'link_type': 'lateral_return'},
            ),
        ],
        'frontal_configs': [
            FrontalLinkConfig(
                link_id='front_main',
                river_name='mainstem',
                river_boundary_side='right',
                river_boundary_node='n2',
                two_d_boundary_tag='front_tag',
                boundary_length=height * 0.32,
                outward_normal=(1.0, 0.0),
                max_iter=3 if case.scheduler_mode != 'strict_global_min_dt' else 1,
                metadata={'partition': 'lower_return_plain', 'link_type': 'frontal_direct'},
            )
        ],
        'snapshot_times': [case.duration * 0.14, case.duration * 0.32, case.duration * 0.58, case.duration * 0.88],
        'primary_stage_probe': 'mainstem_mid',
        'primary_discharge_probe': 'mainstem_right_q',
        'field_wet_threshold': 0.01,
        'use_interior_regions': False,
    }


def _make_domain(mesh_path: Path, case: ChapterExperimentCase, spec: dict[str, Any], initial_2d_stage: float):
    builder = RiverAwareMeshBuilder(spec['mesh_config'])
    mesh = builder.build(
        floodplain_polygon=spec['floodplain_polygon'],
        centerline=spec['centerline'],
        levee_lines=list(spec.get('levee_lines', [])),
        direct_connection_lines=dict(spec.get('direct_connection_lines', {})),
        lateral_links=dict(spec.get('lateral_lines', {})),
    )
    boundary_tags = {'bottom': [0], 'front_tag': [1], 'top': [2], 'left': [3]}
    domain_kwargs: dict[str, Any] = {
        'boundary_tags': boundary_tags,
        'maximum_triangle_area': float(spec['mesh_config'].maximum_triangle_area),
        'mesh_filename': str(mesh_path),
        'minimum_triangle_angle': float(spec['mesh_config'].minimum_triangle_angle),
        'use_cache': False,
        'verbose': False,
    }
    if mesh.breaklines:
        domain_kwargs['breaklines'] = mesh.breaklines
    if spec.get('use_interior_regions', True) and mesh.interior_regions:
        domain_kwargs['interior_regions'] = mesh.interior_regions
    if mesh.interior_holes:
        domain_kwargs['interior_holes'] = mesh.interior_holes
    domain = anuga.create_domain_from_regions(mesh.bounding_polygon, **domain_kwargs)
    domain.set_name(case.case_name)
    domain.set_minimum_storable_height(0.001)
    domain.set_minimum_allowed_height(0.001)
    length = float(spec['length'])
    height = float(spec['floodplain_polygon'][2][1])

    def elevation_fn(x, y):
        return 0.18 + 0.12 * (x / max(length, 1.0)) + 0.05 * (np.asarray(y) > (height * 0.55))

    domain.set_quantity('elevation', elevation_fn)
    domain.set_quantity('friction', 0.032 if 'test7' in case.scenario_family else 0.028, location='centroids')
    domain.set_quantity('stage', initial_2d_stage, location='centroids')
    reflective = anuga.Reflective_boundary(domain)
    domain.set_boundary(
        {
            'left': reflective,
            'top': reflective,
            'bottom': reflective,
            'front_tag': anuga.Transmissive_boundary(domain),
        }
    )
    lateral_regions = {
        link_id: anuga.Region(domain=domain, poly=poly, expand_polygon=True)
        for link_id, poly in mesh.lateral_exchange_regions.items()
    }
    probe_regions = {
        probe.probe_id: anuga.Region(domain=domain, poly=probe.polygon, expand_polygon=True)
        for probe in spec['two_d_probes']
    }
    partition_regions = {
        name: anuga.Region(domain=domain, poly=polygon, expand_polygon=True)
        for name, polygon in spec['partition_defs'].items()
    }
    geometry_payload = {
        'floodplain_polygon': spec['floodplain_polygon'],
        'centerline': spec['centerline'],
        'levee_lines': list(spec.get('levee_lines', [])),
        'lateral_lines': dict(spec.get('lateral_lines', {})),
        'direct_connection_lines': dict(spec.get('direct_connection_lines', {})),
        'breaklines': mesh.breaklines,
        'partitions': spec['partition_defs'],
        'one_d_probes': [asdict(probe) for probe in spec['one_d_probes']],
        'two_d_probes': [asdict(probe) for probe in spec['two_d_probes']],
    }
    return domain, mesh, lateral_regions, probe_regions, partition_regions, geometry_payload


def prepare_chapter_case(case: ChapterExperimentCase, output_dir: Path) -> dict[str, Any]:
    output_dir = ensure_dir(Path(output_dir))
    spec = _scenario_spec(case)
    topology, model_data = _build_topology(
        output_path=str(output_dir),
        duration=case.duration,
        model_name=spec['model_name'],
        river_name=spec['river_name'],
        length=spec['length'],
        cell_num=spec['cell_num'],
        bed_elev_upstream=spec['bed_elev_upstream'],
        bed_drop=spec['bed_drop'],
        section_width=spec['section_width'],
    )
    initial_1d_stage, initial_2d_stage = _initial_levels(case)
    network = create_oned_network(
        case.one_d_backend,
        topology,
        model_data,
        initial_stage=initial_1d_stage,
        verbos=False,
    )
    network.set_boundary('n1', 'flow', _flow_boundary(case))
    network.set_boundary('n2', 'fix_level', _downstream_stage_boundary(case))

    mesh_path = output_dir / f'{case.case_name}.msh'
    domain, mesh, lateral_regions, probe_regions, partition_regions, geometry_payload = _make_domain(mesh_path, case, spec, initial_2d_stage)
    one_d = OneDNetworkAdapter(network)
    two_d = TwoDAnugaGpuAdapter(domain, multiprocessor_mode=4)

    lateral_links: list[LateralWeirLink] = []
    frontal_links: list[FrontalBoundaryLink] = []

    if spec['lateral_configs']:
        two_d.initialize_gpu()
        for link_config in spec['lateral_configs']:
            two_d.register_exchange_region(link_config.link_id, lateral_regions[link_config.region_id], mode='fast')
            link_config.two_d_sample = [lateral_regions[link_config.region_id]] * len(link_config.river_cells)
            lateral_links.append(LateralWeirLink.from_config(link_config))

    if spec['frontal_configs']:
        frontal_links = [FrontalBoundaryLink.from_config(config) for config in spec['frontal_configs']]

    scheduler = SchedulerConfig(
        mode=case.scheduler_mode,
        exchange_interval=case.exchange_interval,
        one_d_yields=list(case.one_d_yields),
        two_d_yields=list(case.two_d_yields),
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
        'one_d_probes': [asdict(probe) for probe in spec['one_d_probes']],
        'two_d_probes': [{'probe_id': probe.probe_id, 'region': probe_regions[probe.probe_id], 'polygon': probe.polygon} for probe in spec['two_d_probes']],
        'discharge_probes': [asdict(probe) for probe in spec['discharge_probes']],
        'partition_regions': partition_regions,
        'partition_defs': spec['partition_defs'],
        'snapshot_times': list(spec['snapshot_times']),
        'geometry_payload': geometry_payload,
        'case_variant': case.case_variant,
        'data_provenance': dict(case.data_provenance),
        'primary_stage_probe': str(spec['primary_stage_probe']),
        'primary_discharge_probe': str(spec['primary_discharge_probe']),
        'field_wet_threshold': float(spec['field_wet_threshold']),
        'xt_river_name': spec['river_name'],
    }


def _scheduler_cases(profile: str = 'paper', *, benchmark_family: bool = False) -> list[tuple[str, float | None]]:
    cases: list[tuple[str, float | None]] = [('strict_global_min_dt', None), ('yield_schedule', None)]
    if profile == 'paper':
        fixed_intervals = FIXED_INTERVALS
    elif benchmark_family:
        fixed_intervals = TEST7_TEST_PROFILE_INTERVALS
    else:
        fixed_intervals = SMALL_TEST_PROFILE_INTERVALS
    cases.extend(('fixed_interval', interval) for interval in fixed_intervals)
    return cases


def _scheduler_case_name(interval: float | None, mode: str) -> str:
    return mode if interval is None else _fixed_interval_label(float(interval))


def _yield_schedule(case_duration: float) -> tuple[list[float], list[float]]:
    return (
        [case_duration * ratio for ratio in (0.18, 0.42, 0.66, 0.88)],
        [case_duration * ratio for ratio in (0.24, 0.50, 0.74)],
    )


def generate_test7_cases(provenance: Test7DataProvenance, profile: str = 'paper') -> list[ChapterExperimentCase]:
    duration = 180.0 if profile == 'paper' else 120.0
    one_d_yields, two_d_yields = _yield_schedule(duration)
    cases: list[ChapterExperimentCase] = []
    scenario_family = provenance.case_variant
    probe_defs = {
        'primary_stage_probe': 'mainstem_mid',
        'primary_discharge_probe': 'mainstem_right_q',
    }
    partition_defs = _scenario_spec(
        ChapterExperimentCase(
            case_name='template',
            scenario_family=scenario_family,
            scheduler_mode='strict_global_min_dt',
            exchange_interval=None,
            coupling_type='mixed',
            direction='river_to_floodplain',
            waveform='benchmark_pulse',
            duration=duration,
            reference_policy='strict_global_min_dt_plus_finest_practical_mesh',
            case_variant=provenance.case_variant,
            data_provenance=provenance.to_payload(),
            runtime_profile=profile,
        )
    )['partition_defs']
    for mode, interval in _scheduler_cases(profile, benchmark_family=True):
        cases.append(
            ChapterExperimentCase(
                case_name=f'{scenario_family}_{_scheduler_case_name(interval, mode)}',
                scenario_family=scenario_family,
                scheduler_mode=mode,
                exchange_interval=interval,
                coupling_type='mixed',
                direction='river_to_floodplain',
                waveform='benchmark_pulse',
                duration=duration,
                reference_policy='strict_global_min_dt_plus_finest_practical_mesh',
                partition_defs=partition_defs,
                probe_defs=probe_defs,
                link_probe_ids=['fp1_overtop', 'fp2_return', 'fp3_overtop', 'front_main'],
                analysis_raster={'mode': 'centroids'},
                case_variant=provenance.case_variant,
                data_provenance=provenance.to_payload(),
                runtime_profile=profile,
                one_d_yields=list(one_d_yields),
                two_d_yields=list(two_d_yields),
            )
        )
    return cases


def generate_small_mechanism_cases(profile: str = 'paper') -> list[ChapterExperimentCase]:
    family_specs = {
        'frontal_basin_fill': {'duration': 120.0 if profile == 'paper' else 80.0, 'coupling_type': 'frontal_only', 'direction': 'river_to_floodplain', 'waveform': 'basin_fill'},
        'lateral_overtopping_return': {'duration': 120.0 if profile == 'paper' else 80.0, 'coupling_type': 'lateral_only', 'direction': 'bidirectional', 'waveform': 'return_pulse'},
        'early_arrival_pulse': {'duration': 60.0 if profile == 'paper' else 40.0, 'coupling_type': 'mixed', 'direction': 'river_to_floodplain', 'waveform': 'early_pulse'},
        'regime_switch_backwater_or_mixed': {'duration': 150.0 if profile == 'paper' else 100.0, 'coupling_type': 'mixed', 'direction': 'bidirectional', 'waveform': 'backwater_mixed'},
    }
    cases: list[ChapterExperimentCase] = []
    for family, meta in family_specs.items():
        one_d_yields, two_d_yields = _yield_schedule(float(meta['duration']))
        spec = _scenario_spec(
            ChapterExperimentCase(
                case_name='template',
                scenario_family=family,
                scheduler_mode='strict_global_min_dt',
                exchange_interval=None,
                coupling_type=str(meta['coupling_type']),
                direction=str(meta['direction']),
                waveform=str(meta['waveform']),
                duration=float(meta['duration']),
                reference_policy='strict_global_min_dt',
                case_variant='mechanism',
                runtime_profile=profile,
            )
        )
        probe_defs = {
            'primary_stage_probe': spec['primary_stage_probe'],
            'primary_discharge_probe': spec['primary_discharge_probe'],
        }
        for mode, interval in _scheduler_cases(profile, benchmark_family=False):
            cases.append(
                ChapterExperimentCase(
                    case_name=f'{family}_{_scheduler_case_name(interval, mode)}',
                    scenario_family=family,
                    scheduler_mode=mode,
                    exchange_interval=interval,
                    coupling_type=str(meta['coupling_type']),
                    direction=str(meta['direction']),
                    waveform=str(meta['waveform']),
                    duration=float(meta['duration']),
                    reference_policy='strict_global_min_dt',
                    partition_defs=spec['partition_defs'],
                    probe_defs=probe_defs,
                    link_probe_ids=[config.link_id for config in spec['lateral_configs']] + [config.link_id for config in spec['frontal_configs']],
                    analysis_raster={'mode': 'centroids'},
                    case_variant='mechanism',
                    data_provenance={'mode': 'synthetic_mechanism'},
                    runtime_profile=profile,
                    one_d_yields=list(one_d_yields),
                    two_d_yields=list(two_d_yields),
                )
            )
    return cases


def generate_all_chapter_cases(provenance: Test7DataProvenance, profile: str = 'paper') -> list[ChapterExperimentCase]:
    return generate_test7_cases(provenance, profile=profile) + generate_small_mechanism_cases(profile=profile)
