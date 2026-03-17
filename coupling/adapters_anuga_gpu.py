from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import numpy as np

from .runtime_env import configure_runtime_environment, require_fast_mode


@dataclass(slots=True)
class TwoDAnugaGpuAdapter:
    domain: Any
    multiprocessor_mode: int = 0
    time_eps: float = 1.0e-12
    default_inlet_mode: str = 'fast'
    _initialized: bool = False
    _prepared_dt: float | None = None
    _exchange_q: dict[str, float] = field(default_factory=dict)
    _exchange_regions: dict[str, Any] = field(default_factory=dict)
    _dynamic_boundary_registry: dict[str, dict[str, Any]] = field(default_factory=dict)

    def _has_gpu_inlet_manager(self) -> bool:
        gpu_inlets = getattr(self.domain, 'gpu_inlets', None)
        return gpu_inlets is not None and hasattr(gpu_inlets, 'add_inlet') and hasattr(gpu_inlets, 'apply')

    def _validate_existing_fast_mode(self) -> None:
        if not self._has_gpu_inlet_manager():
            return
        gpu_inlets = self.domain.gpu_inlets
        default_mode = getattr(gpu_inlets, 'default_mode', None)
        if default_mode is not None:
            require_fast_mode(default_mode)
        for inlet in getattr(gpu_inlets, 'inlets', []):
            inlet_mode = getattr(inlet, 'mode', None)
            if inlet_mode is not None:
                require_fast_mode(inlet_mode)

    @staticmethod
    def _require_mapping_entry(mapping: Any, key: str, kind: str) -> Any:
        if key not in mapping:
            raise KeyError(f'未注册的{kind}: {key!r}')
        return mapping[key]

    @staticmethod
    def _quantity_alias(name: str) -> tuple[str, str]:
        mapping = {
            'stage': ('stage', 'stage'),
            'height': ('height', 'height'),
            'xmomentum': ('xmomentum', 'xmom'),
            'ymomentum': ('ymomentum', 'ymom'),
        }
        if name not in mapping:
            raise KeyError(f'Unsupported quantity alias: {name}')
        return mapping[name]

    def initialize_gpu(self) -> None:
        configure_runtime_environment()
        if hasattr(self.domain, 'set_multiprocessor_mode'):
            self.domain.set_multiprocessor_mode(self.multiprocessor_mode)
        if not hasattr(self.domain, 'gpu_interface'):
            self.domain.set_gpu_interface()
        if not hasattr(self.domain, 'relative_time'):
            self.domain.relative_time = 0.0
        if not self._has_gpu_inlet_manager():
            self.domain.gpu_interface.init_gpu_inlets(default_mode=require_fast_mode(self.default_inlet_mode))
        self._validate_existing_fast_mode()
        self.domain.gpu_interface.init_gpu_boundary_conditions()
        self._initialized = True

    def _ensure_initialized(self) -> None:
        if not self._initialized:
            self.initialize_gpu()

    def register_dynamic_boundary(self, tag: str, provider: Any) -> None:
        self._ensure_initialized()
        import anuga

        boundary_map = dict(getattr(self.domain, 'boundary_map', {}) or {})
        fallback = anuga.Transmissive_boundary(self.domain)
        state_holder = np.asarray(provider(0.0), dtype=float) if callable(provider) else np.asarray(provider, dtype=float)

        def boundary_function(t: float, _tag: str = tag) -> np.ndarray:
            registry = self._dynamic_boundary_registry[_tag]
            if callable(registry['provider']):
                return np.asarray(registry['provider'](t), dtype=float)
            return np.asarray(registry['state'], dtype=float)

        time_boundary = anuga.Time_boundary(self.domain, function=boundary_function)
        self._dynamic_boundary_registry[tag] = {
            'provider': provider if callable(provider) else None,
            'state': np.asarray(state_holder, dtype=float),
            'time_boundary': time_boundary,
            'fallback': fallback,
            'active': False,
        }
        boundary_map[tag] = fallback
        self.domain.set_boundary(boundary_map)
        self.domain.gpu_interface.init_gpu_boundary_conditions()

    def activate_dynamic_boundary(self, tag: str, active: bool) -> None:
        self._ensure_initialized()
        registry = self._require_mapping_entry(self._dynamic_boundary_registry, tag, '动态边界 tag')
        boundary_map = dict(getattr(self.domain, 'boundary_map', {}) or {})
        boundary_map[tag] = registry['time_boundary'] if active else registry['fallback']
        registry['active'] = bool(active)
        self.domain.set_boundary(boundary_map)
        self.domain.gpu_interface.init_gpu_boundary_conditions()

    def set_dynamic_boundary_state(self, tag: str, state: Any) -> None:
        registry = self._require_mapping_entry(self._dynamic_boundary_registry, tag, '动态边界 tag')
        registry['state'] = np.asarray(state, dtype=float)

    def register_exchange_region(self, link_id: str, region: Any, mode: str | None = None) -> None:
        self._ensure_initialized()
        if not self._has_gpu_inlet_manager():
            raise RuntimeError('新版 GPUInletManager 未初始化，不能注册 exchange region')
        inlet_mode = require_fast_mode(self.default_inlet_mode if mode is None else mode)
        self._exchange_q.setdefault(link_id, 0.0)
        # Keep lateral exchange on the new GPUInlet API so signed Q reaches the
        # dedicated dV>=0 / dV<0 branches inside GPUInlet.apply().
        self._exchange_regions[link_id] = self.domain.gpu_inlets.add_inlet(
            region,
            Q=lambda t, _link_id=link_id: self._exchange_q.get(_link_id, 0.0),
            label=link_id,
            mode=inlet_mode,
        )

    def clear_exchange_Q(self) -> None:
        for link_id in list(self._exchange_q):
            self._exchange_q[link_id] = 0.0

    def set_exchange_Q(self, link_id: str, discharge: float) -> None:
        if link_id not in self._exchange_q:
            raise KeyError(f'link {link_id!r} 尚未注册 exchange region')
        self._exchange_q[link_id] = float(discharge)

    def refresh_boundary_values(self) -> None:
        self._ensure_initialized()
        gpu = self.domain.gpu_interface
        gpu.protect_against_infinitesimal_and_negative_heights_kernal(
            transfer_gpu_results=False,
            transfer_from_cpu=False,
        )
        gpu.extrapolate_second_order_edge_sw_kernel(
            transfer_gpu_results=False,
            transfer_from_cpu=False,
        )
        gpu.update_boundary_values_gpu()

    def _prepare_gpu_step(self) -> float:
        self._ensure_initialized()
        gpu = self.domain.gpu_interface
        self.refresh_boundary_values()
        dt = gpu.compute_fluxes_ext_central_kernel(
            self.domain.evolve_max_timestep,
            transfer_from_cpu=False,
            transfer_gpu_results=False,
            return_domain_timestep=True,
        )
        dt_value = float(np.asarray(dt).reshape(-1)[0])
        gpu.protect_against_infinitesimal_and_negative_heights_kernal(
            transfer_gpu_results=False,
            transfer_from_cpu=False,
        )
        self._prepared_dt = dt_value
        return dt_value

    def predict_cfl_dt(self) -> float:
        return float(self._prepare_gpu_step())

    def advance_one_step(self, dt: float) -> float:
        predicted = self._prepare_gpu_step() if self._prepared_dt is None else float(self._prepared_dt)
        remaining_dt = min(float(dt), predicted)
        if remaining_dt <= self.time_eps:
            remaining_dt = max(float(dt), 0.0)
        self.domain.timestep = remaining_dt
        self.domain.gpu_interface.set_gpu_update_timestep(self.domain.timestep)
        self.domain.relative_time += remaining_dt
        self.domain.gpu_interface.compute_forcing_terms_manning_friction_flat(
            transfer_from_cpu=False,
            transfer_gpu_results=False,
        )
        if not self._has_gpu_inlet_manager():
            raise RuntimeError('缺少新版 GPUInletManager；耦合交换不能退回 legacy apply_inlets_gpu 路径')
        self.domain.gpu_inlets.apply()
        self.domain.gpu_interface.update_conserved_quantities_kernal(
            transfer_from_cpu=False,
            transfer_gpu_results=False,
        )
        self._prepared_dt = None
        return float(remaining_dt)

    def advance_to(self, target_time: float, mode: str | None = None) -> float:
        target = float(target_time)
        while self.domain.relative_time + self.time_eps < target:
            remaining = target - float(self.domain.relative_time)
            dt = min(float(self.predict_cfl_dt()), remaining)
            if dt <= self.time_eps:
                dt = max(remaining, 0.0)
            used_dt = self.advance_one_step(dt)
            if used_dt <= 0.0:
                break
        return float(self.domain.relative_time)

    def _boundary_arrays(self, name: str) -> np.ndarray:
        quantity_name, gpu_prefix = self._quantity_alias(name)
        gpu = getattr(self.domain, 'gpu_interface', None)
        gpu_name = f'gpu_{gpu_prefix}_boundary_values'
        if gpu is not None and hasattr(gpu, gpu_name):
            arr = getattr(gpu, gpu_name)
            try:
                import cupy as cp  # type: ignore

                if isinstance(arr, cp.ndarray):
                    return cp.asnumpy(arr)
            except Exception:
                pass
        return np.asarray(getattr(self.domain.quantities[quantity_name], 'boundary_values'))

    def _centroid_array(self, name: str) -> np.ndarray:
        quantity_name, gpu_prefix = self._quantity_alias(name)
        gpu = getattr(self.domain, 'gpu_interface', None)
        gpu_name = f'gpu_{gpu_prefix}_centroid_values'
        if gpu is not None and hasattr(gpu, gpu_name):
            arr = getattr(gpu, gpu_name)
            try:
                import cupy as cp  # type: ignore

                if isinstance(arr, cp.ndarray):
                    return cp.asnumpy(arr)
            except Exception:
                pass
        return np.asarray(self.domain.quantities[quantity_name].centroid_values)

    def sample_stage(self, region_or_points: Any) -> float:
        stage = self._centroid_array('stage')
        if hasattr(region_or_points, 'get_indices'):
            ids = np.asarray(region_or_points.get_indices(full_only=True), dtype=int)
            return float(np.mean(stage[ids]))
        if (
            isinstance(region_or_points, (list, tuple))
            and region_or_points
            and isinstance(region_or_points[0], (list, tuple))
            and len(region_or_points[0]) == 2
        ):
            try:
                import anuga

                region = anuga.Region(domain=self.domain, poly=region_or_points, expand_polygon=True)
                ids = np.asarray(region.get_indices(full_only=True), dtype=int)
                return float(np.mean(stage[ids]))
            except Exception:
                pass
        ids = np.asarray(region_or_points, dtype=int)
        return float(np.mean(stage[ids]))

    def sample_boundary_stage(self, tag: str) -> float:
        self.refresh_boundary_values()
        self._require_mapping_entry(getattr(self.domain, 'tag_boundary_cells', {}), tag, '2D boundary tag')
        ids = np.asarray(self.domain.tag_boundary_cells[tag], dtype=int)
        stage = self._boundary_arrays('stage')[ids]
        vol_ids = np.asarray(self.domain.boundary_cells, dtype=int)[ids]
        edge_ids = np.asarray(self.domain.boundary_edges, dtype=int)[ids]
        lengths = np.asarray(self.domain.mesh.edgelengths[vol_ids, edge_ids], dtype=float)
        return float(np.average(stage, weights=lengths))

    def sample_boundary_flux(self, tag: str) -> float:
        self.refresh_boundary_values()
        self._require_mapping_entry(getattr(self.domain, 'tag_boundary_cells', {}), tag, '2D boundary tag')
        ids = np.asarray(self.domain.tag_boundary_cells[tag], dtype=int)
        xmom = self._boundary_arrays('xmomentum')[ids]
        ymom = self._boundary_arrays('ymomentum')[ids]
        vol_ids = np.asarray(self.domain.boundary_cells, dtype=int)[ids]
        edge_ids = np.asarray(self.domain.boundary_edges, dtype=int)[ids]
        normals = np.asarray(self.domain.normals[vol_ids], dtype=float)
        lengths = np.asarray(self.domain.mesh.edgelengths[vol_ids, edge_ids], dtype=float)
        nx = normals[np.arange(len(ids)), 2 * edge_ids]
        ny = normals[np.arange(len(ids)), 2 * edge_ids + 1]
        flow = -(xmom * nx + ymom * ny) * lengths
        return float(np.sum(flow))

    def snapshot(self) -> dict[str, Any]:
        state = {
            'stage': self._centroid_array('stage').copy(),
            'xmomentum': self._centroid_array('xmomentum').copy(),
            'ymomentum': self._centroid_array('ymomentum').copy(),
            'height': self._centroid_array('height').copy(),
            'relative_time': float(self.domain.relative_time),
            'timestep': float(getattr(self.domain, 'timestep', 0.0)),
            'exchange_q': dict(self._exchange_q),
            'dynamic_boundary_state': {
                tag: {
                    'state': np.asarray(registry['state'], dtype=float).copy(),
                    'active': bool(registry['active']),
                }
                for tag, registry in self._dynamic_boundary_registry.items()
            },
        }
        return state

    def restore(self, snapshot: dict[str, Any]) -> None:
        self._ensure_initialized()
        gpu = self.domain.gpu_interface
        gpu.gpu_stage_centroid_values[...] = snapshot['stage']
        gpu.gpu_xmom_centroid_values[...] = snapshot['xmomentum']
        gpu.gpu_ymom_centroid_values[...] = snapshot['ymomentum']
        gpu.gpu_height_centroid_values[...] = snapshot['height']
        self.domain.relative_time = float(snapshot['relative_time'])
        self.domain.timestep = float(snapshot['timestep'])
        gpu.set_gpu_update_timestep(self.domain.timestep)
        self._exchange_q = dict(snapshot.get('exchange_q', {}))
        for tag, boundary_state in snapshot.get('dynamic_boundary_state', {}).items():
            self.set_dynamic_boundary_state(tag, boundary_state['state'])
            self.activate_dynamic_boundary(tag, bool(boundary_state['active']))
        self._prepared_dt = None

    def get_total_volume(self) -> float:
        height = self._centroid_array('height')
        areas = np.asarray(self.domain.areas, dtype=float)
        return float(np.sum(height * areas))
