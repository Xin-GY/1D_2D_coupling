# Benchmark Case Notes

## Scope
- 本轮 chapter 分析只使用 Environment Agency benchmark family 中的 `Test 7: River and floodplain linking`。
- 由于当前仓库的 1D–2D 紧耦合框架不包含 culvert、闸门、桥梁或其它离散设施路径，因此这里构造的是 `overtopping-only` 变体。
- 该变体保留 1D 河道、2D 洪泛区、bank/embankment/levee overtopping，以及 frontal/lateral 的主要接口关系；显式去除了 culvert / other pathways。

## Provenance Policy
- 优先查找仓库内或本地缓存中的官方 Test 7 technical report 与 benchmark model zip。
- 若缓存不存在且允许联网，则尝试从 GOV.UK 官方 benchmark 页面自动解析 PDF/ZIP 链接并下载。
- 若下载失败或被禁用，则自动退回 `surrogate_test7_overtopping_only_variant`。
- 所有 provenance 都会写入：
  - `artifacts/chapter_coupling_analysis/logs/test7_provenance.json`
  - 每个 case 目录下的 `provenance.json`

## Current Chapter Run
- 当前仓库内已完成的 chapter 产物使用：
  - `surrogate_test7_overtopping_only_variant`
- 直接原因见 `artifacts/chapter_coupling_analysis/logs/test7_provenance.json`：
  - `download_attempted = false`
  - `download_succeeded = false`
  - `fallback_reason = official_data_not_found_and_download_disabled`
- 因此本轮论文级内部比较是在 documented surrogate 上完成的，而不是官方 assets 的 silent partial run。
- 目前仓库同时保留两套 chapter 结果根目录：
  - `artifacts/chapter_coupling_analysis/`
    - 原 chapter 基线结果
  - `artifacts/chapter_coupling_analysis_fastest_exact/`
    - 切换到 `fastest_exact` 1D backend、并对 figure-driving cases 使用 `refined_figures` mesh preset 的 A/B 结果

## Official vs Surrogate Naming
- `official_test7_overtopping_only_variant`
  - 表示成功发现或下载到官方 benchmark assets，并在当前仓库能力下构造 scope-restricted overtopping-only 版本。
- `surrogate_test7_overtopping_only_variant`
  - 表示官方 assets 不可用时，用文档化的 Test 7-like 三分区洪泛平原几何替代。
  - surrogate 保留了：
    - 单主河道 1D 主槽
    - Floodplain 1/2/3 三分区
    - lateral overtopping / return links
    - frontal connection boundary
    - river-aware breakline / refinement 设计思路

## Reference Policy
- 大算例 reference 固定为：
  - `strict_global_min_dt + finest practical mesh`
- 当前 chapter `paper` profile 中，benchmark 会跑完整 scheduler / interval 矩阵。
- `test` profile 用于自动化验证与真实 GPU regression，保留 strict / yield 与代表性 fixed-interval 子集。

## What This Benchmark Is For
- 这不是实测校验任务。
- 这也不是 HEC-RAS 对照任务。
- 该 benchmark 的角色是：
  - 提供一个接近论文场景的大尺度 overtopping-only 耦合环境；
  - 用于比较 scheduler、fixed interval、partition response、interface diagnostics 与成本占比；
  - 支撑 chapter 中的“时间离散、空间耦合与计算成本占比分析”。

## Fastest-Exact A/B Notes
- `artifacts/chapter_coupling_analysis_fastest_exact/` 不覆盖原 chapter 基线结果。
- 新目录只重跑了选定 benchmark / small cases：
  - benchmark:
    - `strict_global_min_dt`
    - `yield_schedule`
    - `fixed_interval_002s`
    - `fixed_interval_003s`
    - `fixed_interval_005s`
    - `fixed_interval_010s`
    - `fixed_interval_015s`
    - `fixed_interval_030s`
    - `fixed_interval_060s`
    - `fixed_interval_300s`
  - small mechanism:
    - 四个 family 的 strict
    - `early_arrival_pulse_fixed_interval_005s`
    - 四个 family 的 `fixed_interval_015s`
- 所有新图已通过 blank-image QA，2D 图仍保持：
  - full-mesh face coloring
  - gray mesh lines
  - geometry cache redraw
