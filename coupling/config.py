from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class SchedulerConfig:
    mode: str = 'fixed_interval'
    exchange_interval: float | None = 60.0
    one_d_yields: list[float] = field(default_factory=list)
    two_d_yields: list[float] = field(default_factory=list)
    time_eps: float = 1.0e-12


@dataclass(slots=True)
class MeshRefinementConfig:
    maximum_triangle_area: float = 100.0
    minimum_triangle_angle: float = 28.0
    channel_exclusion_half_width: float = 5.0
    river_refinement_half_width: float = 20.0
    river_refinement_area: float = 25.0
    levee_refinement_half_width: float = 8.0
    levee_refinement_area: float = 16.0
    frontal_refinement_half_width: float = 12.0
    frontal_refinement_area: float = 9.0
    lateral_region_half_width: float = 8.0
    lateral_region_area: float = 9.0
    prefer_channel_hole: bool = True


@dataclass(slots=True)
class LateralLinkConfig:
    link_id: str
    river_name: str
    region_id: str
    river_cells: list[int]
    segment_lengths: list[float]
    crest_levels: list[float]
    river_to_twod_normal: tuple[float, float] = (1.0, 0.0)
    discharge_coefficient: float = 1.0
    wet_dry_threshold: float = 1.0e-4
    lumped: bool = False
    two_d_sample: list[Any] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class FrontalLinkConfig:
    link_id: str
    river_name: str
    river_boundary_side: str
    river_boundary_node: str
    two_d_boundary_tag: str
    boundary_length: float
    outward_normal: tuple[float, float]
    wet_dry_threshold: float = 1.0e-4
    max_iter: int = 1
    relax_factor: float = 0.5
    tol_stage: float = 1.0e-4
    tol_Q: float = 1.0e-4
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class CouplingConfig:
    start_time: float
    end_time: float
    scheduler: SchedulerConfig
    lateral_links: list[LateralLinkConfig] = field(default_factory=list)
    frontal_links: list[FrontalLinkConfig] = field(default_factory=list)
    mesh: MeshRefinementConfig = field(default_factory=MeshRefinementConfig)
    diagnostics_dir: str = 'result'
    gravity: float = 9.81
    strict_mass_tolerance: float = 1.0e-6
