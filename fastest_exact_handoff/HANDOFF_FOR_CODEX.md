# Handoff for another Codex

## What this bundle is for

Use this bundle when you want to continue exact-only optimization from the **currently fastest accepted exact path** without re-traversing the already-rejected branch families.

## Current best exact path

- branch: `feature/cpp-exact-after-globalcfl-assemble-reaudit-v2`
- commit: `445c2c9` (as supplied in the latest accepted state)
- exact gate:
  - 10m strict compare: pass
  - 2h strict compare: pass
  - 40h strict compare: pass
  - 40h compare: allclose = true
- 40h evolve/model time:
  - `47.05382442474365 s`

## Files to start from

The core code path is in:
- `source/handoff_network_model_20260312/Islam.py`
- `source/handoff_network_model_20260312/Rivernet.py`
- `source/handoff_network_model_20260312/river_for_net.py`
- `source/handoff_network_model_20260312/cython_node_iteration.pyx`
- `source/handoff_network_model_20260312/cython_river_kernels.pyx`
- `source/handoff_network_model_20260312/cython_cpp_bridge.pyx`
- `source/handoff_network_model_20260312/cpp/evolve_core.hpp`
- `source/handoff_network_model_20260312/cpp/evolve_core.cpp`
- `source/handoff_network_model_20260312/cpp/river_kernels.hpp`
- `source/handoff_network_model_20260312/cpp/river_kernels.cpp`

## Do not reopen blindly

Do not prioritize these directions again unless you first produce materially new evidence:
- `_refresh_cell_state` deeper ownership old variants
- residual / Jacobian deep as a primary path
- fullstep / dispatch shape experiments
- `-march=native`
- FAST_MODE
- Python-layer multi-process / multi-thread benchmark line
- external-boundary-deep exact family in its current form

## What changed latest

The current accepted candidate adds:
- `ISLAM_CPP_USE_ASSEMBLE_DEEP=1`

and deepens native ownership of `Assemble_Flux_2` on top of the accepted global-CFL baseline.

## Best immediate use of this bundle

- reproduce the current exact fastest path
- audit the current hotspot distribution again from this accepted point
- if you later explore deterministic C++ threads, the first credible target is the deep assemble kernel
- do not start with nodechain threads

## Included reports worth reading first

- `source/handoff_network_model_20260312/reports/branch_matrix_for_github.md`
- `source/handoff_network_model_20260312/reports/branch_push_handoff.md`
- `source/handoff_network_model_20260312/reports/final_cpp_after_globalcfl_assemble_v2_recommendation.md`
- `source/handoff_network_model_20260312/reports/assemble_threads_recheck.md`
- `source/handoff_network_model_20260312/reports/final_cpp_after_global_cfl_recommendation.md`
- `source/handoff_network_model_20260312/reports/final_cpp_accepted_reaudit_recommendation.md`
