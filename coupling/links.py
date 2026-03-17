from __future__ import annotations

from dataclasses import dataclass, field
import math

import numpy as np

from .config import FrontalLinkConfig, LateralLinkConfig


@dataclass(slots=True)
class LateralWeirSegment:
    segment_id: str
    length: float
    crest_level: float
    river_cell: int
    two_d_sample: object | None = None


@dataclass(slots=True)
class LateralWeirLink:
    link_id: str
    river_name: str
    region_id: str
    segments: list[LateralWeirSegment]
    discharge_coefficient: float = 1.0
    normal_direction: tuple[float, float] = (1.0, 0.0)
    wet_dry_threshold: float = 1.0e-4
    lumped: bool = False
    current_Q: float = 0.0
    current_dV: float = 0.0
    cumulative_dV: float = 0.0
    mass_balance_accumulator: float = 0.0
    last_eta_1d: list[float] = field(default_factory=list)
    last_eta_2d: list[float] = field(default_factory=list)
    last_segment_Q: list[float] = field(default_factory=list)
    last_mode: str = ''

    @classmethod
    def from_config(cls, config: LateralLinkConfig) -> 'LateralWeirLink':
        two_d_sample = list(config.two_d_sample) if config.two_d_sample else [None] * len(config.river_cells)
        segments = []
        for idx, (cell, seg_length, crest) in enumerate(zip(config.river_cells, config.segment_lengths, config.crest_levels)):
            sample_ref = two_d_sample[min(idx, len(two_d_sample) - 1)] if two_d_sample else None
            segments.append(
                LateralWeirSegment(
                    segment_id=f'{config.link_id}_seg{idx}',
                    length=float(seg_length),
                    crest_level=float(crest),
                    river_cell=int(cell),
                    two_d_sample=sample_ref,
                )
            )
        return cls(
            link_id=config.link_id,
            river_name=config.river_name,
            region_id=config.region_id,
            segments=segments,
            discharge_coefficient=float(config.discharge_coefficient),
            normal_direction=tuple(float(v) for v in config.river_to_twod_normal),
            wet_dry_threshold=float(config.wet_dry_threshold),
            lumped=bool(config.lumped),
        )

    def compute_exchange(self, river_stages: list[float], two_d_stages: list[float], gravity: float = 9.81) -> float:
        if len(river_stages) != len(self.segments) or len(two_d_stages) != len(self.segments):
            raise ValueError('river_stages / two_d_stages 必须与 segments 数量一致')

        total_Q = 0.0
        self.last_eta_1d = [float(v) for v in river_stages]
        self.last_eta_2d = [float(v) for v in two_d_stages]
        self.last_segment_Q = []
        sqrt_2g = math.sqrt(2.0 * gravity)
        for segment, eta_river, eta_2d in zip(self.segments, river_stages, two_d_stages):
            deta = float(eta_river) - float(eta_2d)
            if abs(deta) <= self.wet_dry_threshold:
                self.last_segment_Q.append(0.0)
                continue
            h_up = max(max(float(eta_river), float(eta_2d)) - float(segment.crest_level), 0.0)
            if h_up <= self.wet_dry_threshold:
                self.last_segment_Q.append(0.0)
                continue
            q_seg = math.copysign(
                self.discharge_coefficient * float(segment.length) * sqrt_2g * (h_up ** 1.5),
                deta,
            )
            total_Q += q_seg
            self.last_segment_Q.append(float(q_seg))
        self.current_Q = float(total_Q)
        return float(total_Q)

    def finalize_exchange(self, t: float, dt_exchange: float, mode: str) -> dict[str, float | str]:
        self.current_dV = float(self.current_Q * dt_exchange)
        self.cumulative_dV += self.current_dV
        self.last_mode = mode
        return {
            'link_id': self.link_id,
            'time': float(t),
            'dt_exchange': float(dt_exchange),
            'eta_1d': float(np.mean(self.last_eta_1d)) if self.last_eta_1d else np.nan,
            'eta_2d': float(np.mean(self.last_eta_2d)) if self.last_eta_2d else np.nan,
            'Q_exchange': float(self.current_Q),
            'dV_exchange': float(self.current_dV),
            'cumulative_dV': float(self.cumulative_dV),
            'mass_error': float(self.mass_balance_accumulator),
            'mode': mode,
            'iteration_count': 1,
        }


@dataclass(slots=True)
class FrontalBoundaryLink:
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
    current_Q: float = 0.0
    current_stage: float = 0.0
    current_dV: float = 0.0
    cumulative_dV: float = 0.0
    mass_balance_accumulator: float = 0.0
    last_mode: str = 'sub'
    iteration_count: int = 1

    @classmethod
    def from_config(cls, config: FrontalLinkConfig) -> 'FrontalBoundaryLink':
        return cls(
            link_id=config.link_id,
            river_name=config.river_name,
            river_boundary_side=config.river_boundary_side,
            river_boundary_node=config.river_boundary_node,
            two_d_boundary_tag=config.two_d_boundary_tag,
            boundary_length=float(config.boundary_length),
            outward_normal=tuple(float(v) for v in config.outward_normal),
            wet_dry_threshold=float(config.wet_dry_threshold),
            max_iter=int(config.max_iter),
            relax_factor=float(config.relax_factor),
            tol_stage=float(config.tol_stage),
            tol_Q=float(config.tol_Q),
        )

    def build_two_d_boundary_state(self, stage: float, discharge: float) -> np.ndarray:
        if self.boundary_length <= 0.0:
            raise ValueError(f'{self.link_id} boundary_length 必须大于 0')
        qn = -float(discharge) / float(self.boundary_length)
        nx, ny = self.outward_normal
        return np.asarray([float(stage), qn * float(nx), qn * float(ny)], dtype=float)

    def relax_guess(self, stage_guess: float, q_guess: float, stage_new: float, q_new: float) -> tuple[float, float]:
        r = float(np.clip(self.relax_factor, 0.0, 1.0))
        return (
            (1.0 - r) * float(stage_guess) + r * float(stage_new),
            (1.0 - r) * float(q_guess) + r * float(q_new),
        )

    def converged(self, stage_guess: float, q_guess: float, stage_new: float, q_new: float) -> bool:
        return abs(float(stage_new) - float(stage_guess)) <= self.tol_stage and abs(float(q_new) - float(q_guess)) <= self.tol_Q

    def finalize_exchange(self, t: float, dt_exchange: float, mode: str) -> dict[str, float | str]:
        self.current_dV = float(self.current_Q * dt_exchange)
        self.cumulative_dV += self.current_dV
        self.last_mode = mode
        return {
            'link_id': self.link_id,
            'time': float(t),
            'dt_exchange': float(dt_exchange),
            'eta_1d': float(self.current_stage),
            'eta_2d': float(self.current_stage),
            'Q_exchange': float(self.current_Q),
            'dV_exchange': float(self.current_dV),
            'cumulative_dV': float(self.cumulative_dV),
            'mass_error': float(self.mass_balance_accumulator),
            'mode': mode,
            'iteration_count': int(self.iteration_count),
        }
