from __future__ import annotations

import os
from typing import Any

from .Rivernet import Rivernet


ACCEPTED_EXACT_ENV_DEFAULTS: dict[str, str] = {
    "ISLAM_USE_CYTHON_TABLE": "1",
    "ISLAM_USE_CPP_EVOLVE": "1",
    "ISLAM_CPP_THREADS": "0",
    "ISLAM_USE_CYTHON_NODECHAIN": "1",
    "ISLAM_USE_CYTHON_NODECHAIN_DIRECT_FAST": "1",
    "ISLAM_USE_CYTHON_NODECHAIN_PREBOUND_FAST": "1",
    "ISLAM_CPP_USE_NODECHAIN_DEEP_APPLY": "1",
    "ISLAM_CPP_USE_NODECHAIN_COMMIT_DEEP": "1",
    "ISLAM_CPP_USE_GLOBAL_CFL_DEEP": "1",
}


def apply_fastest_exact_env_defaults() -> None:
    for key, value in ACCEPTED_EXACT_ENV_DEFAULTS.items():
        os.environ.setdefault(key, value)


def configure_network_for_coupling(net: Rivernet) -> Rivernet:
    # Coupling needs per-step exchange and rollback, so we keep the accepted
    # exact helper kernels enabled but do not hand control to the monolithic
    # cpp evolve loop.
    net.use_parallel_workers = False
    net.use_cpp_evolve = False
    net.cpp_threads = False
    net.use_cython_nodechain = True
    net.use_cython_nodechain_direct_fast = True
    net.use_cython_nodechain_prebound_fast = True
    net.use_cpp_nodechain_deep_apply = True
    net.use_cpp_nodechain_commit_deep = True
    net.use_cpp_global_cfl_deep = True
    net.external_flow_bc_use_characteristic = True
    net.external_bc_respect_supercritical = True
    net.internal_bc_respect_supercritical = True
    net.use_fix_level_bc_v2 = False
    net.internal_use_ac_v2 = True
    net.internal_use_paper_ac = True
    net.internal_level_predict_from_last = True
    net.internal_sync_branch_end_Q = False
    net.internal_node_use_face_discharge = False
    net.internal_node_prefer_boundary_face_discharge = False
    net.internal_node_use_boundary_face_ac = False
    net.internal_node_use_face_flux_residual = False
    net.perf_profile_enabled = False
    return net


def initialize_rivers_for_coupling(net: Rivernet, initial_stage: float) -> None:
    for _, _, data in net.G.edges(data=True):
        river = data["river"]
        river.Set_init_water_level(float(initial_stage))
        river.swap_moc_sign = False
        river.swap_moc_sign_flow = False
        river.swap_moc_sign_stage = False
        river.swap_moc_sign_stage_in = False
        river.swap_moc_sign_stage_out = False
        river.bc_use_order2_extrap = True
        river.bc_use_order2_extrap_flow = True
        river.bc_use_order2_extrap_stage = True
        river.bc_order2_boundary_face = False
        river.bc_stage_on_face = False
        river.bc_stage_store_face_state = False
        river.bc_stage_ghost_q_from_face = False
        river.bc_stage_reconstruct_ghost_u = False
        river.bc_stage_reconstruct_ghost_q = False
        river.bc_stage_char_on_face = False
        river.bc_stage_on_face_use_depth = False
        river.bc_use_general_chi = True
        river.bc_use_general_chi_flow = True
        river.bc_use_general_chi_stage = True
        river.bc_general_chi_candidate_mode = "guarded_clamp"
        river.bc_general_chi_guard_selector = "closure_q_delta"
        river.bc_general_chi_guard_q_delta = 0.005
        river.bc_moc_with_source = False
        river.bc_moc_with_source_flow = False
        river.bc_moc_with_source_stage = False
        river.bc_moc_dt_fraction = 0.5
        river.bc_moc_source_scale = 1.0
        river.use_boundary_face_flux_override = False
        river.use_boundary_face_mass_flux_override = False
        river.refined_section_table = False
        river.save_with_ghost = False


def build_fastest_exact_network(
    topology: dict[tuple[str, str], dict[str, Any]],
    model_data: dict[str, Any],
    *,
    initial_stage: float,
    verbos: bool = False,
) -> Rivernet:
    apply_fastest_exact_env_defaults()
    network = Rivernet(topology, model_data, verbos=verbos)
    configure_network_for_coupling(network)
    initialize_rivers_for_coupling(network, initial_stage=initial_stage)
    return network
