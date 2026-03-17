# Code application paths and call chain

## 1. Top-level entry

The accepted exact path is orchestrated from:

- `source/handoff_network_model_20260312/Islam.py`

Key functions:
- `build_net(...)`
- `maybe_run_warmup(net)`
- `prepare_net_for_evolve(net, yield_step=1800)`
- `run_prepared_evolve(net, yield_step=1800, print_progress=False)`

`configure_net_options(...)` reads the environment variables that enable the fastest exact path.

## 2. Network-level runtime owner

- `source/handoff_network_model_20260312/Rivernet.py`

Important routing points:
- imports the Cython nodechain layer and the Cython/C++ evolve bridge
- `Caculate_global_CFL()` can route through `calculate_global_cfl_exact_cpp(...)`
- `_run_prepared_evolve(...)` / `Evolve(...)` can route through `run_cpp_network_evolve_serial(...)`
- the current accepted path keeps `ISLAM_CPP_THREADS=0`

## 3. River-level stage owner

- `source/handoff_network_model_20260312/river_for_net.py`

The fastest accepted exact path reaches the river stages through these flags:
- `ISLAM_USE_CYTHON_ROE_FLUX=1`
- `ISLAM_CPP_USE_ROE_FLUX_DEEP=1`
- `ISLAM_CPP_USE_ROE_FLUX_RECT_DEEP=1`
- `ISLAM_CPP_USE_UPDATE_CELL=1`
- `ISLAM_CPP_USE_ASSEMBLE=1`
- `ISLAM_CPP_USE_ASSEMBLE_DEEP=1`
- `ISLAM_CPP_USE_ROE_MATRIX=1`
- `ISLAM_CPP_USE_FACE_UC=1`

Important stage routing:
- `River.Caculate_Roe_Flux_2()`
- `River.Assemble_Flux_2()`
- `River.Update_cell_proprity2()`

Current deep assemble route:
- `River.Assemble_Flux_2()` first checks `ISLAM_CPP_USE_ASSEMBLE_DEEP=1`
- if the deep native path succeeds, it returns immediately
- otherwise it falls back to the older split path

## 4. Cython / C++ ownership layers

### Nodechain
- `source/handoff_network_model_20260312/cython_node_iteration.pyx`

### River-stage kernels
- `source/handoff_network_model_20260312/cython_river_kernels.pyx`
- `source/handoff_network_model_20260312/cpp/river_kernels.hpp`
- `source/handoff_network_model_20260312/cpp/river_kernels.cpp`

### Network evolve bridge and global CFL
- `source/handoff_network_model_20260312/cython_cpp_bridge.pyx`
- `source/handoff_network_model_20260312/cpp/evolve_core.hpp`
- `source/handoff_network_model_20260312/cpp/evolve_core.cpp`
- `source/handoff_network_model_20260312/cpp/output_buffer.hpp`
- `source/handoff_network_model_20260312/cpp/output_buffer.cpp`

### Cross-section support
- `source/handoff_network_model_20260312/cython_cross_section.pyx`
- `source/handoff_network_model_20260312/cython_cross_section.pxd`

## 5. Exact accepted environment flags

```bash
ISLAM_USE_CPP_EVOLVE=1
ISLAM_CPP_THREADS=0
ISLAM_USE_CYTHON_NODECHAIN=1
ISLAM_USE_CYTHON_NODECHAIN_DIRECT_FAST=1
ISLAM_USE_CYTHON_NODECHAIN_PREBOUND_FAST=1
ISLAM_CPP_USE_NODECHAIN_DEEP_APPLY=1
ISLAM_CPP_USE_NODECHAIN_COMMIT_DEEP=1
ISLAM_USE_CYTHON_ROE_FLUX=1
ISLAM_CPP_USE_ROE_FLUX_DEEP=1
ISLAM_CPP_USE_ROE_FLUX_RECT_DEEP=1
ISLAM_CPP_USE_UPDATE_CELL=1
ISLAM_CPP_USE_ASSEMBLE=1
ISLAM_CPP_USE_ASSEMBLE_DEEP=1
ISLAM_CPP_USE_ROE_MATRIX=1
ISLAM_CPP_USE_FACE_UC=1
ISLAM_CPP_USE_GLOBAL_CFL_DEEP=1
ISLAM_USE_CPP_BRIDGE_DIRECT_DISPATCH=0
ISLAM_CPP_USE_NODECHAIN_REFRESH_DEEP=0
```

## 6. Accepted run path summary

1. `Islam.build_net()` creates the network and rivers
2. `configure_net_options()` wires env flags into `Rivernet` / `River`
3. `prepare_net_for_evolve(...)` initializes the evolve state
4. `run_prepared_evolve(...)` enters the accepted exact evolve loop
5. network-level C++ path handles prepared evolve orchestration
6. nodechain, Roe-flux, rectangular Roe-flux, global CFL, update-cell, assemble, Roe-matrix, and face-UC all use their accepted deep/native routes
7. strict-compare-accepted 40h path yields `47.05382442474365 s`
