# Coupling README

本文档面向当前分支上的“现实现实装”，详细说明 1D–2D 耦合路径是如何在仓库中落地的，包括 backend 选择、case 构造、适配层契约、调度逻辑、交换链路、2D GPU 调用顺序、诊断与 artifacts 写出路径。文档以当前代码为准，重点说明“谁调用谁、在哪一层决定什么、结果最后写到哪里”。

## 1. 目标与边界

当前仓库实现的是河道一维网络与洪泛区二维浅水域之间的紧耦合模拟，主要针对以下场景：

- 河岸漫顶导致的侧向交换；
- 河道端部与二维区域之间的正向/直连边界互供；
- 同时存在正向耦合与侧向耦合的复合洪水传播；
- 以 overtopping 为主的 benchmark 与小机理算例。

当前实现不覆盖桥涵、闸门、泵站或复杂局部三维水工结构。chapter 文档中出现的 Test 7 结果，当前主要使用 `surrogate_test7_overtopping_only_variant` 这一 documented surrogate benchmark，而不是官方全设施版模型。

## 2. 目录层次与职责

### 2.1 `coupling/`

- `adapters_rivernet.py`
  - 1D backend 适配器，向 `CouplingManager` 提供统一接口。
- `adapters_anuga_gpu.py`
  - 2D ANUGA GPU fast-mode 适配器，负责 boundary refresh、GPU inlet 应用、快照采样与 timing 统计。
- `manager.py`
  - 耦合主控，组织初始化、时间推进、exchange event、Picard 小迭代、diagnostics。
- `scheduler.py`
  - strict / yield / fixed interval 三种调度策略的下一交换时刻逻辑。
- `links.py`
  - `LateralWeirLink`、`FrontalBoundaryLink` 等交换链路实现，负责根据 1D/2D 状态计算区间交换通量并写历史。
- `mesh_builder.py`
  - river-aware 2D 几何、breaklines、局部 refinement 区域构造。
- `config.py`
  - 耦合配置结构体。
- `runtime_env.py`
  - 运行时环境配置，特别是 plotting 与 ANUGA build 环境修复。

### 2.2 `experiments/`

- `one_d_backends.py`
  - 统一的 1D backend 选择器，默认 `fastest_exact`。
- `cases.py` / `chapter_cases.py`
  - legacy case 与 chapter case 的生成、prepare 与 backend 注入。
- `chapter_runner.py`
  - 单个 chapter case 的执行与 case 级 artifacts 写出。
- `chapter_metrics.py`
  - 从 case 级原始 CSV/JSON 重建 summary、timing、field metrics、exchange summary。
- `chapter_plotting.py`
  - chapter 图表刷新与 plot QA 入口。
- `chapter_suite.py`
  - chapter 级 orchestration：批量运行、汇总、绘图。
- `run_single_case.py`
  - 单 case CLI 入口。
- `run_fastest_exact_refresh.py`
  - fastest_exact A/B 结果的选定 case 刷新入口。

### 2.3 `fastest_exact_handoff/`

- `source/handoff_network_model_20260312/`
  - 最新导入的 optimized handoff 河网实现。
- `coupling_factory.py`
  - fastest_exact backend 的显式工厂构造入口。
- `Rivernet.py` / `river_for_net.py`
  - fastest_exact 网络与河道对象；已补齐 coupling 所需生命周期接口。

## 3. backend 选择是在哪里发生的

### 3.1 默认后端

当前 1D backend 的唯一选择入口在 `experiments/one_d_backends.py`：

- `DEFAULT_ONE_D_BACKEND = "fastest_exact"`
- `create_oned_network(...)` 负责分支：
  - `legacy` -> `demo.Rivernet.Rivernet(...)`
  - `fastest_exact` -> `fastest_exact_handoff...coupling_factory.build_fastest_exact_network(...)`

这意味着 `CouplingManager` 本身并不知道底层是 legacy 还是 fastest_exact。backend 的切换点在 case prepare 阶段，而不是在 manager 内部。

### 3.2 CLI / case 字段如何影响 backend

- CLI：`python -m experiments.run_single_case ... --one-d-backend fastest_exact`
- case 字段：`one_d_backend`
- chapter 级默认：`run_fastest_exact_refresh.py` 会把 `default_one_d_backend='fastest_exact'` 覆盖到选定 case 上。

## 4. 从 chapter 入口到耦合主循环的调用链

### 4.1 入口链

```text
experiments/run_fastest_exact_refresh.py:main
  -> experiments/chapter_suite.py:run_chapter_analysis
    -> experiments/chapter_suite.py:_run_case_subprocess
      -> python -m experiments.run_single_case <case_name> --registry chapter
        -> experiments/run_single_case.py:main
          -> experiments/chapter_cases.py:prepare_chapter_case
            -> experiments/one_d_backends.py:create_oned_network
            -> coupling.adapters_rivernet.OneDNetworkAdapter
            -> coupling.adapters_anuga_gpu.TwoDAnugaGpuAdapter
            -> coupling.manager.CouplingManager
          -> experiments/chapter_runner.py:run_chapter_case
            -> CouplingManager.initialize()
            -> CouplingManager.run()
            -> write case-level CSV/JSON artifacts
    -> experiments/chapter_suite.py:_aggregate_chapter_tables
      -> experiments/chapter_metrics.py:rebuild_chapter_case_outputs
    -> experiments/chapter_suite.py:_run_plot_scripts
      -> experiments/chapter_plotting.py:refresh_chapter_plot_outputs
```

### 4.2 case prepare 阶段做了什么

`experiments/chapter_cases.py:prepare_chapter_case(...)` 是耦合前最关键的装配点。它负责：

1. 根据 case family 生成一维河道和二维洪泛区几何规范；
2. 调用 `create_oned_network(...)` 实例化 1D backend；
3. 构造 2D domain 与 mesh；
4. 生成 lateral / frontal link 配置；
5. 包装成：
   - `OneDNetworkAdapter(network)`
   - `TwoDAnugaGpuAdapter(domain)`
6. 将 scheduler mode、exchange interval、snapshot times、probe defs、link ids、mesh variant 等字段塞进 `CouplingManager` 所需配置。

### 4.3 单 case 执行阶段写出什么

`experiments/chapter_runner.py:run_chapter_case(...)` 会在 case 运行结束后写出以下原始 artifacts：

- `config.json`
- `provenance.json`
- `stage_timeseries_1d.csv`
- `stage_timeseries_2d.csv`
- `discharge_timeseries.csv`
- `mass_balance.csv`
- `exchange_history.csv`
- `exchange_link_timeseries.csv`
- `two_d_field_summary.csv`
- `two_d_snapshots.csv`
- `timing_breakdown.json`
- `geometry.json`
- `plot_cache/mesh_geometry.npz` 与 `plot_cache/mesh_geometry.json`

这些文件是后续 summary、论文图件、blank QA 与 geometry cache 重绘的基础。

## 5. 1D adapter 契约与 fastest_exact 为什么能无缝接上

### 5.1 `OneDNetworkAdapter` 期待什么

`coupling/adapters_rivernet.py` 将底层河网对象视作一个满足统一契约的 network。它会调用网络级方法：

- `initialize_for_coupling(save_outputs=False)`
- `predict_cfl_dt()`
- `advance_one_step(dt)`
- `advance_to(target_time, mode=None)`
- `get_total_volume()`
- `snapshot()` / `restore()`
- `get_river(name)`

并在河道级调用：

- `apply_cellwise_side_inflow(cell_ids, side_qs)`
- `get_total_volume()`
- `snapshot()` / `restore()`

### 5.2 fastest_exact 补了哪些生命周期方法

在 `fastest_exact_handoff/source/handoff_network_model_20260312/` 中，当前实现已经为 `Rivernet` / `River` 补齐了这些 coupling-facing 方法。这样做的意义是：

- `CouplingManager` 不需要知道新旧 backend 的差别；
- `OneDNetworkAdapter` 可以继续扮演唯一的 contract boundary；
- backend 替换被收敛在 `create_oned_network(...)` 与 `coupling_factory.py`。

### 5.3 为什么不用 `Islam.py` 的模块级 `net`

当前实现明确避免在 coupling 路径里依赖 `Islam.py` 的模块级 `net`。原因是：

- chapter / benchmark case 需要多 case、可参数化、可批量运行；
- 模块级单例不利于 CLI 子进程隔离；
- 明确工厂函数更适合 A/B backend 切换与回归。

因此最快 exact backend 的推荐构造方式是：

```text
experiments.one_d_backends.create_oned_network(...)
  -> fastest_exact_handoff...coupling_factory.build_fastest_exact_network(...)
```

## 6. 2D adapter 的真实调用顺序

### 6.1 只允许 fast-mode

`coupling/adapters_anuga_gpu.py` 当前严格要求 2D 侧使用新版 GPUInlet fast-mode 主路径。非 fast mode 不应被静默接受。历史 legacy `apply_inlets_gpu()` 调用路径在 production coupling 中已被禁止。

### 6.2 2D 典型推进顺序

在每个耦合区间内，2D adapter 的关键步骤是：

1. boundary state refresh；
2. 根据当前 exchange / frontal boundary 状态更新 dynamic boundary；
3. 执行 GPU shallow-water kernels；
4. 应用 `domain.gpu_inlets.apply()`；
5. 更新 conserved quantities；
6. 在诊断时刻写出 probe、field summary、snapshot 和 timing。

在 timing breakdown 中，对应的桶为：

- `two_d_gpu_kernel_time`
- `boundary_update_time`
- `gpu_inlets_apply_time`
- 其余管理开销进入 `scheduler_manager_overhead` 或 exchange manager 桶

## 7. scheduler 如何决定下一次交换

`scheduler.py` 提供三种模式：

### 7.1 `strict_global_min_dt`

- 每次按 1D/2D 中更严格的稳定步长对齐推进；
- exchange 频率最高；
- 数值最接近 reference，但 exchange manager 开销最大。

### 7.2 `yield_schedule`

- 根据预设的一维/二维 yield 时刻推进；
- 只有到达 yield 时刻才真正触发一次 exchange；
- 更适合做“事件触发式”开销对比。

### 7.3 `fixed_interval`

- 以固定耦合时间间隔推进；
- scheduler 给出的 exchange 事件序列从 `start + interval` 开始；
- 这意味着 `t=0` 的界面状态用于计算第一个区间的交换，但 exchange history 的 finalize time 记在区间末端，例如 `300 s`。

这一点在长历时综合案例里非常重要：`300 s` 工况不是前 300 s 完全没有耦合，而是使用 `0 s` 的边界状态冻结整个第一个区间，并在 `t=300 s` 记一条 exchange 事件。

## 8. lateral 与 frontal 耦合分别怎么实现

### 8.1 lateral coupling

`coupling/links.py` 中的 `LateralWeirLink` 负责侧向漫顶交换。典型逻辑是：

1. 从 1D 河道采样界面附近 stage；
2. 从 2D polygon / interface 区域采样洪泛区 stage；
3. 根据界面水位差与 link 参数计算该区间交换通量；
4. 将区间总交换量一方面作为 1D 河道的侧向源项注入，另一方面转换为 2D inlet 应用；
5. 调用 `finalize_exchange(...)` 记下：
   - time
   - dt_exchange
   - Q_exchange
   - cumulative volume
   - eta_1d / eta_2d
   - sign 等信息。

它的重点是守恒：1D 失水与 2D 受水必须在同一 exchange interval 内闭合，link 级诊断会把这种闭合关系单独记录下来。

### 8.2 frontal/direct coupling

`FrontalBoundaryLink` 负责一维端部与二维边界的直连互供。典型使用场景是：

- 一维河道端部 stage 影响二维动态边界；
- 二维边界反馈又会影响一维边界闭合；
- 在需要时触发简单 Picard 小迭代，以避免边界条件在同一个耦合区间内出现过大不一致。

为了支持这种小迭代，1D backend 与 river 对象都要提供 `snapshot()` / `restore()`。这也是 fastest_exact 被补齐 coupling 生命周期接口的原因之一。

## 9. `CouplingManager` 在一个耦合区间里到底做什么

`coupling/manager.py` 是整个耦合流程的组织者。高层过程可以概括为：

1. `initialize()`
   - 初始化 1D、2D、scheduler、links、timers、diagnostics。
2. `run()`
   - 循环直到总时长结束；
   - 从 scheduler 取下一交换时刻；
   - 在当前区间内分别推进 1D 与 2D；
   - 到达区间末端后调用 `exchange_all_links(...)`；
   - 对需要的小迭代 boundary/link 执行 snapshot/restore + Picard 修正；
   - 记录 exchange history、mass balance、timeseries 与 snapshot。
3. `finalize`
   - 输出 case 级 artifacts，返回用于 chapter aggregation 的执行信息。

简化伪码：

```text
manager.initialize()
while t < t_end:
    next_t = scheduler.next_exchange_time(t)
    advance_1d_to(next_t)
    advance_2d_to(next_t)
    exchange_all_links(current=t, target=next_t)
    maybe_picard_iterate_and_restore()
    capture_timeseries_and_mass_balance(next_t)
    t = next_t
write_case_outputs()
```

## 10. 为什么 boundary / exchange management 常常主导成本变化

当前 chapter 与 1200 s rerun 的 timing 数据都表明：

- 粗时间间隔虽然减少了 exchange 次数，但节省的主要是 boundary refresh、exchange bookkeeping、scheduler/manager 相关开销；
- 二维 GPU kernel 本身并不会因为 interval 变粗就同量级下降；
- 因此时间成本的主要可压缩部分往往不是 GPU 计算，而是耦合管理频率。

这也是 `cost_share_stacked.png` 与 `timing_breakdown.csv` 中经常看到 `exchange_manager` 占比较高的原因。

## 11. summary、plots 和 geometry cache 是怎么来的

### 11.1 summary rebuild

`experiments/chapter_metrics.py:rebuild_chapter_case_outputs(...)` 会从 case 级原始 CSV/JSON 重建：

- `summary_table.csv`
- `summary_table_small_cases.csv`
- `summary_table_test7_partitions.csv`
- `timing_breakdown.csv`
- `exchange_link_summary.csv`
- `figure_manifest.csv`
- `table_manifest.csv`

这里使用统一分析网格、线性插值 crossing 与 field-by-cell 对比逻辑，保证不同图表口径一致。

### 11.2 geometry cache

为了避免 2D 绘图运行时依赖未提交的 `.msh`，当前 chapter results 会在每个 case 下写：

- `plot_cache/mesh_geometry.npz`
- `plot_cache/mesh_geometry.json`

绘图时优先从 cache 恢复：

- vertices
- triangles
- bounds
- centroids
- segments
- 邻接关系

这使得 2D 图可以仅依赖 artifacts 重绘，而不需要重新生成网格。

### 11.3 中文论文图脚本

当前仓库里已经有一套面向第 4.5 节的中文重绘脚本，例如：

- `scripts/plot_ch4_5_hydrographs_cn.py`
- `scripts/plot_ch4_5_2d_maps_cn.py`
- `scripts/plot_ch4_5_exchange_cn.py`
- `scripts/plot_ch4_5_interval_summary_cn.py`

这些脚本都遵守同一原则：

- 不重跑求解器；
- 只基于现有 summary、case CSV/JSON 与 plot cache 重绘；
- 缺文件时 fail-fast；
- 2D 主图必须 `full-mesh face coloring + gray mesh lines`。

## 12. 1200 s 综合案例 rerun 在仓库中的位置

为了长历时验证综合案例对粗耦合时间间隔的敏感性，当前仓库还包含一个最小 rerun 根目录：

- `artifacts/chapter_case_reruns/benchmark_1200_legacy/`

它包含：

- `strict`
- `2 s`
- `5 s`
- `15 s`
- `60 s`
- `300 s`

这套 rerun 数据已经被用于：

- 重绘 `stage_hydrographs_1d_cn.png` 的 1200 s 长历时图；
- 重算 `cost_share_stacked.png` 与 `relative_cost_vs_accuracy.png` 的最新成本结论；
- 验证 `300 s` 工况在长历时下虽有多次 exchange 机会，但仍不足以有效追踪持续演化的界面状态。

## 13. 当前最重要的代码入口速查

- 1D backend 选择：`experiments/one_d_backends.py`
- fastest_exact 工厂：`fastest_exact_handoff/source/handoff_network_model_20260312/coupling_factory.py`
- 1D adapter：`coupling/adapters_rivernet.py`
- 2D adapter：`coupling/adapters_anuga_gpu.py`
- manager：`coupling/manager.py`
- scheduler：`coupling/scheduler.py`
- links：`coupling/links.py`
- chapter case prepare：`experiments/chapter_cases.py`
- chapter run：`experiments/chapter_runner.py`
- summary rebuild：`experiments/chapter_metrics.py`
- chapter plot refresh：`experiments/chapter_plotting.py`

## 14. 建议的维护原则

1. backend 替换尽量收敛在 `create_oned_network(...)` 和工厂层，不要把 backend 分支撒到 manager 内部。
2. 2D GPU path 继续坚持 fast-mode-only，不要重新引入 legacy inlet 调用。
3. 所有论文图优先从 artifacts + plot cache 重绘，不要把绘图脚本绑回 `.msh`。
4. 当需要新 benchmark 口径时，优先新增独立 rerun summary，再让 plotting 脚本读取它，而不是覆写旧 chapter summary。

## 15. 一句话总结

当前实现的核心思想是：**在不改 `CouplingManager` 主体的前提下，通过统一的 1D adapter 契约和 2D fast-mode GPU 适配层，把不同 backend、不同 scheduler、不同 benchmark/small-case 配置收敛到同一条可批量运行、可后处理重建、可论文级重绘的耦合流水线里。**
