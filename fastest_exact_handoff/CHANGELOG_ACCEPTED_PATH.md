# Accepted-path changelog vs earlier baselines

This file summarizes the accepted improvements that lead to the current fastest exact bundle.

## A. Earlier accepted baseline: `feature/cpp-exact-accepted-reaudit-next@9a7c094`

Key addition:
- `ISLAM_CPP_USE_ROE_FLUX_RECT_DEEP=1`

Main ownership change:
- rectangular-HR Roe flux moved from Python-owned per-face orchestration to a deeper native per-face stage

Key files:
- `river_for_net.py`
- `cython_river_kernels.pyx`
- `cpp/river_kernels.hpp`
- `cpp/river_kernels.cpp`

Reported 40h change:
- `91.32992911338806 s -> 65.23701047897339 s`

## B. Accepted candidate after global CFL: `feature/cpp-exact-accepted-after-global-cfl@689ae0b`

Key addition:
- `ISLAM_CPP_USE_GLOBAL_CFL_DEEP=1`

Main ownership change:
- per-river CFL candidate generation and fixed-order global dt/CFL reduction moved from Python/NumPy ownership into the native bridge/core

Key files:
- `Rivernet.py`
- `Islam.py`
- `cython_cpp_bridge.pyx`
- `cpp/evolve_core.hpp`
- `cpp/evolve_core.cpp`
- `tools/profile_cpp_exact_serial.py`

Reported 40h change:
- `65.23701047897339 s -> 60.74310255050659 s`

## C. Current fastest accepted candidate: `feature/cpp-exact-after-globalcfl-assemble-reaudit-v2@445c2c9`

Key addition:
- `ISLAM_CPP_USE_ASSEMBLE_DEEP=1`

Main ownership change:
- `Assemble_Flux_2` deeper ownership pushdown on top of the accepted global-CFL baseline
- the deep kernel now owns:
  - conservative flux increment
  - exact Manning / friction post-step
  - conservative dry admissibility
  - stage-local write-back
- derived-state refresh still stays in the accepted update-cell path

Key files:
- `river_for_net.py`
- `cython_river_kernels.pyx`
- `cpp/river_kernels.hpp`
- `cpp/river_kernels.cpp`
- `tools/profile_cpp_exact_serial.py`

Reported 40h change:
- `60.74310255050659 s -> 47.05382442474365 s`

## Why the old assemble prototype did not pass when first built

Old preserved prototype:
- branch: `feature/cpp-exact-accepted-after-assemble-reaudit`
- commit: `6680275`

It was exact, but it lost against the then-current accepted baseline because:
- nodechain / boundary shells still dominated
- global CFL had not yet been pushed down

Once the global CFL deep path was accepted in `689ae0b`, re-running the assemble deeper-ownership push on the new baseline allowed the local assemble gain to survive at 40h scale.

## Included provenance reports

See the copied upstream reports in:
- `source/handoff_network_model_20260312/reports/`

Especially:
- `final_cpp_accepted_reaudit_recommendation.md`
- `final_cpp_after_global_cfl_recommendation.md`
- `final_cpp_after_globalcfl_assemble_v2_recommendation.md`
- `cpp_roe_flux_rect_deep_impl.md`
- `global_cfl_deep_impl.md`
- `assemble_deep_v2_impl.md`
