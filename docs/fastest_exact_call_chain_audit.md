# Fastest Exact Handoff Call-Chain Audit

## Scope

This note records the solver/coupling call chains before the backend swap and
the exact replacement points used for the `fastest_exact_handoff` backend.
The goal is to preserve the existing coupling manager contract while switching
the underlying 1D river-network solver from the legacy `demo` implementation to
the optimized handoff model.

## 1. Legacy 1D Solver Call Chain

The current legacy experiment path is:

1. `experiments.cases.generate_*cases()` or `experiments.chapter_cases.generate_*cases()`
2. `prepare_case(...)` / `prepare_chapter_case(...)`
3. `demo.Rivernet.Rivernet(topology, model_data, verbos=False)`
4. `OneDNetworkAdapter(network)`
5. `CouplingManager.run()`

Inside the legacy coupling lifecycle, the adapter expects the network to
provide:

- `initialize_for_coupling(save_outputs=False)`
- `predict_cfl_dt()`
- `advance_one_step(dt)`
- `advance_to(target_time, mode=None)`
- `snapshot()`, `restore()`
- `get_total_volume()`
- `get_river(name)`

River objects are also expected to provide:

- `apply_cellwise_side_inflow(cell_ids, side_qs)`
- `get_total_volume()`
- `snapshot()`, `restore()`

## 2. Fastest Exact Solver Call Chain

The optimized handoff model lives under:

- `fastest_exact_handoff/source/handoff_network_model_20260312/`

The exact solver chain is centered around:

1. `Rivernet.Caculate_global_CFL()`
2. `Rivernet.Update_boundary_conditions()`
3. network-level evolve orchestration
4. `River.Caculate_face_U_C()`
5. `River.Caculate_Roe_matrix()`
6. `River.Caculate_source_term_2()`
7. `River.Caculate_Roe_Flux_2()`
8. `River.Assemble_Flux_2()` / implicit branch assembly
9. `River.Update_cell_proprity2()`

Optimized bridges and kernels are used through:

- `cython_cross_section`
- `cython_node_iteration`
- `cython_river_kernels`
- `cython_cpp_bridge`
- `cpp/evolve_core.cpp`
- `cpp/river_kernels.cpp`

The accepted exact backend also carries environment-sensitive runtime toggles,
so the coupling entrypoint should configure the network explicitly rather than
relying on module-level scripts.

## 3. Current Coupling Call Chain

The coupling path itself remains:

1. case builder prepares topology, 2D domain, and scheduler config
2. `OneDNetworkAdapter` wraps a network backend
3. `TwoDAnugaGpuAdapter` wraps ANUGA GPU fast-mode stepping
4. `CouplingManager` drives:
   - boundary exchange
   - lateral source injection
   - strict/yield/fixed interval scheduling
   - diagnostics and plot artifacts

Crucially, `CouplingManager` does not know which 1D backend is underneath the
adapter. The swap therefore happens at the case-construction layer plus the 1D
backend contract.

## 4. Replacement Points

The backend swap is implemented at two levels:

### 4.1 Import / packaging

`fastest_exact_handoff.source.handoff_network_model_20260312` is treated as a
regular importable package with relative imports, so experiments can import it
without mutating `sys.path`.

### 4.2 Coupling contract shim

The optimized backend is extended with the adapter-facing lifecycle methods:

- network-level:
  - `initialize_for_coupling`
  - `predict_cfl_dt`
  - `advance_one_step`
  - `advance_to`
  - `get_total_volume`
  - `snapshot`
  - `restore`
  - `get_river`
- river-level:
  - `apply_cellwise_side_inflow`
  - `get_total_volume`
  - `snapshot`
  - `restore`

This keeps `OneDNetworkAdapter` unchanged as the coupling contract boundary.

## 5. Builder / Factory Strategy

The new coupling-safe construction path is:

1. `experiments.one_d_backends.create_oned_network(...)`
2. `fastest_exact_handoff...coupling_factory.build_fastest_exact_network(...)`
3. factory-level network option setup
4. boundary attachment in `prepare_case(...)` / `prepare_chapter_case(...)`
5. `OneDNetworkAdapter(network)`

This avoids using `Islam.py`'s module-level `net` object in coupling.

## 6. Build and Import Notes

The handoff extensions must be built before running the optimized backend:

- `build_cython_cross_section.py`
- `build_cython_exact_kernels.py`
- `build_cpp_exact_kernels.py`

The build scripts now force execution from the repository root so that the
fully-qualified extension names install in place correctly regardless of the
current working directory.

## 7. Remaining Integration Risks

- The backend swap must preserve strict time alignment for coupling. The
  network-level `advance_one_step(dt)` must not overrun the requested step.
- Legacy benchmark/chapter outputs should remain untouched; new A/B outputs
  belong under `artifacts/chapter_coupling_analysis_fastest_exact/`.
- Plot QA remains mandatory because denser 2D meshes can change layout,
  normalization, and blank-image behavior even if the simulation completes.
