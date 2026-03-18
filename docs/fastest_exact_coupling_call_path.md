# Fastest-Exact Coupling Call Path

本文档基于当前分支 `feature/fastest-exact-coupling-swap` 的真实代码路径梳理 `fastest_exact` 1D backend 下 chapter/experiment/coupling 的调用链、耦合契约与计算原理。它是对 `docs/fastest_exact_call_chain_audit.md` 的代码级展开，不替代后者的高层审计结论，但把“谁调用谁、在哪里写出 artifacts”写得更精确。

## 1. 总入口与 backend 选择

### 1.1 chapter 入口
- chapter 级最快 exact A/B 入口是 [experiments/run_fastest_exact_refresh.py](experiments/run_fastest_exact_refresh.py)。
- `main()` 先调用 `resolve_test7_data(...)` 解析 benchmark provenance，然后调用 `run_chapter_analysis(...)`。
- 这个入口强制传入：
  - `default_one_d_backend='fastest_exact'`
  - `default_mesh_variant='refined_figures'`
  - `selected_case_names=_selected_case_names(...)`
- 所以它不会重跑整套 chapter，而是只重跑选定 benchmark/small cases。

### 1.2 backend 选择点
- 1D backend 的唯一选择入口是 [experiments/one_d_backends.py](experiments/one_d_backends.py)。
- `DEFAULT_ONE_D_BACKEND = "fastest_exact"`。
- `create_oned_network(...)` 的分支逻辑是：
  - `legacy` -> `demo.Rivernet.Rivernet(...)`
  - `fastest_exact` -> `fastest_exact_handoff...coupling_factory.build_fastest_exact_network(...)`
- case builder 并不直接 import `Islam.py` 的模块级 `net`，而是显式调用 `create_oned_network(...)` 创建网络对象。

### 1.3 chapter case builder / suite / runner 的位置
- chapter case 构造在 [experiments/chapter_cases.py](experiments/chapter_cases.py)。
  - `generate_test7_cases(...)`
  - `generate_small_mechanism_cases(...)`
  - `prepare_chapter_case(...)`
- chapter suite orchestration 在 [experiments/chapter_suite.py](experiments/chapter_suite.py)。
  - `run_chapter_analysis(...)`
  - `_run_case_subprocess(...)`
  - `_aggregate_chapter_tables(...)`
  - `_run_plot_scripts(...)`
- 单 case 子进程入口在 [experiments/run_single_case.py](experiments/run_single_case.py)。
  - 这里把 `case_name + registry + profile + backend override + mesh override` 解析成真正的 case 对象。

### 1.4 会影响 backend、mesh、scheduler、interval 的参数
- backend 相关：
  - CLI: `--one-d-backend`
  - case field: `ChapterExperimentCase.one_d_backend`
- mesh 相关：
  - CLI: `--mesh-variant`
  - case field: `ChapterExperimentCase.mesh_variant`
  - `refined_figures` 会在 [experiments/chapter_cases.py](experiments/chapter_cases.py) 的 `_apply_mesh_variant(...)` 中把 `maximum_triangle_area` 与局部 refinement area 减半。
- scheduler / interval 相关：
  - case field: `scheduler_mode`
  - case field: `exchange_interval`
  - 这些字段在 `prepare_chapter_case(...)` 中被转成 `SchedulerConfig(...)` 并交给 `CouplingManager`。

## 2. 1D–2D 耦合主调用链

### 2.1 伪调用栈总览
```text
experiments/run_fastest_exact_refresh.py:main
  -> experiments/chapter_suite.py:run_chapter_analysis
    -> experiments/chapter_suite.py:_run_case_subprocess
      -> python -m experiments.run_single_case <case_name> --registry chapter
        -> experiments/run_single_case.py:main
          -> experiments/chapter_cases.py:prepare_chapter_case
            -> experiments/one_d_backends.py:create_oned_network
              -> fastest_exact_handoff...coupling_factory.build_fastest_exact_network
            -> coupling.adapters_rivernet.OneDNetworkAdapter
            -> coupling.adapters_anuga_gpu.TwoDAnugaGpuAdapter
            -> coupling.manager.CouplingManager
          -> experiments/chapter_runner.py:run_chapter_case
            -> CouplingManager.initialize
            -> CouplingManager.run
            -> write case CSV/JSON artifacts
    -> experiments/chapter_suite.py:_aggregate_chapter_tables
      -> experiments/chapter_metrics.py:rebuild_chapter_case_outputs
    -> experiments/chapter_suite.py:_run_plot_scripts
      -> experiments/chapter_plotting.py:refresh_chapter_plot_outputs
```

### 2.2 chapter suite 到 case 构建
1. [experiments/run_fastest_exact_refresh.py](experiments/run_fastest_exact_refresh.py)
   - 通过 `_selected_case_names(...)` 限定 benchmark 和 small mechanism 的子集。
   - 调用 `run_chapter_analysis(...)`。
2. [experiments/chapter_suite.py](experiments/chapter_suite.py) `run_chapter_analysis(...)`
   - 调用 `resolve_test7_data(...)` 并写出 `logs/test7_provenance.json`。
   - 用 `generate_test7_cases(...)` / `generate_small_mechanism_cases(...)` 生成 `ChapterExperimentCase` 列表。
   - 把 `default_one_d_backend='fastest_exact'` 和 `default_mesh_variant='refined_figures'` 覆盖到 case 上。
   - 对每个 case 调用 `_run_case_subprocess(...)`。
3. `_run_case_subprocess(...)`
   - 实际执行：
     - `python -m experiments.run_single_case <case_name> --registry chapter ...`
   - 也就是说，chapter suite 自己不在当前进程里直接推进耦合，而是把每个 case 放到独立 Python 子进程。

### 2.3 单 case 运行链
1. [experiments/run_single_case.py](experiments/run_single_case.py) `main()`
   - 用 `_chapter_provenance(...)` 解析 provenance。
   - 用 `_find_chapter_case(...)` 从 `generate_all_chapter_cases(...)` 里找到指定 case。
   - 调用 `run_chapter_case(case, output_root, prepare_chapter_case, reference=None)`。
2. [experiments/chapter_cases.py](experiments/chapter_cases.py) `prepare_chapter_case(...)`
   - `_scenario_spec(case)` 生成该 case 的：
     - 1D 河道长度、cell 数、河床坡降、断面宽度
     - 2D floodplain polygon
     - centerline / levee_lines / lateral_lines / direct_connection_lines
     - lateral / frontal link configs
     - probes / snapshot times / partition defs
   - `_build_topology(...)` 生成 1D `topology + model_data`。
   - `create_oned_network(...)` 创建 1D backend。
   - 对 1D 网络显式施加边界：
     - `network.set_boundary('n1', 'flow', _flow_boundary(case))`
     - `network.set_boundary('n2', 'fix_level', _downstream_stage_boundary(case))`
   - `_make_domain(...)` 构造 2D domain、mesh、lateral regions、probe regions、partition regions、geometry payload。
   - 包装成：
     - `OneDNetworkAdapter(network)`
     - `TwoDAnugaGpuAdapter(domain, multiprocessor_mode=4)`
   - 对每个 lateral link 调用：
     - `two_d.initialize_gpu()`
     - `two_d.register_exchange_region(link_id, region, mode='fast')`
   - 构造 `SchedulerConfig(...)` 和 `CouplingManager(...)`。
3. [experiments/chapter_runner.py](experiments/chapter_runner.py) `run_chapter_case(...)`
   - 创建 `ChapterDiagnosticsCollector(...)`。
   - 注册：
     - exchange observer -> `collector.capture_exchange(...)`
     - 1D diagnostic callback -> `collector.capture_one_d(...)`
     - 2D diagnostic callback -> `collector.capture_two_d(...)`
   - 调用：
     - `manager.initialize()`
     - `collector.capture_one_d(..., 0.0)`
     - `collector.capture_two_d(..., 0.0)`
     - `collector.capture_exchange(..., 0.0)`
     - `manager.run()`
   - 运行后把 case 原始产物写出到 `cases/<case_name>/`。

### 2.4 CouplingManager 的推进链
在 [coupling/manager.py](coupling/manager.py) 中：

1. `initialize()`
   - `one_d.initialize(save_outputs=False)`
   - `two_d.initialize_gpu()`
   - 记录初始 1D/2D/system volume
   - 对每个 frontal link：
     - `two_d.register_dynamic_boundary(...)`
     - `two_d.activate_dynamic_boundary(..., False)`
2. `run()`
   - 根据 `scheduler.mode` 循环推进到 `end_time`。
   - `strict_global_min_dt`：
     - `dt_1d = one_d.predict_cfl_dt()`
     - `dt_2d = two_d.predict_cfl_dt()`
     - `next_time = scheduler.next_exchange_time(current, end, one_d_dt=dt_1d, two_d_dt=dt_2d)`
     - `exchange_all_links(...)`
     - `step_until_exchange(next_time, shared_dt=dt_exchange)`
   - `yield_schedule` / `fixed_interval`：
     - `next_time = scheduler.next_exchange_time(current, end)`
     - `exchange_all_links(...)`
     - `_run_picard_interval(...)`
3. 每个 exchange 结束后：
   - 记录 `dt_history`
   - 记录 `mass_balance_rows`
   - 通知 exchange observers
   - 最后 `write_diagnostics()` 写出：
     - `coupling_exchange_history.csv`
     - `coupling_dt_history.csv`
     - `coupling_mass_balance.csv`

## 3. fastest_exact 新 1D backend 的耦合契约

### 3.1 backend 构建链
`fastest_exact` 后端由 [experiments/one_d_backends.py](experiments/one_d_backends.py) 调用 [fastest_exact_handoff/source/handoff_network_model_20260312/coupling_factory.py](fastest_exact_handoff/source/handoff_network_model_20260312/coupling_factory.py) 完成：

1. `build_fastest_exact_network(...)`
2. `apply_fastest_exact_env_defaults()`
3. `Rivernet(topology, model_data, verbos=...)`
4. `configure_network_for_coupling(net)`
5. `initialize_rivers_for_coupling(net, initial_stage=...)`

`configure_network_for_coupling(...)` 的关键作用是：
- 保留 accepted exact helper kernels
- 关闭 monolithic `cpp evolve` 主循环
- 把网络切到“可单步推进、可交换、可回滚”的 coupling-safe 形态

### 3.2 网络级 coupling 生命周期方法
这些方法定义在 [fastest_exact_handoff/source/handoff_network_model_20260312/Rivernet.py](fastest_exact_handoff/source/handoff_network_model_20260312/Rivernet.py)。

#### `initialize_for_coupling(save_outputs=False)`
- 被 [coupling/adapters_rivernet.py](coupling/adapters_rivernet.py) `OneDNetworkAdapter.initialize()` 调用。
- 做的事：
  - `Fine_cell_property_net()`（若 `Fine_flag`）
  - `Init_water_surface_net()`
  - `Init_cell_property_net()`
  - 可选写基本输出
  - `Caculate_global_CFL()`
  - 设置 `self.DT = self.cfl_allowed_dt`
  - `self._coupling_initialized = True`
  - `_sync_river_runtime(...)`
- 返回值：
  - 首个可用 CFL `dt`

#### `predict_cfl_dt()`
- 被 `OneDNetworkAdapter.predict_cfl_dt()` 调用。
- 直接调用 `Caculate_global_CFL()` 并返回 `self.cfl_allowed_dt`。

#### `advance_one_step(dt)`
- 被 `OneDNetworkAdapter.advance_one_step(dt)` 调用。
- 是 network-level 显式单步推进接口。
- 当前 exact backend 的真实执行顺序是：
  - 检查 `_coupling_initialized`
  - 计算 `used_dt = min(dt, remaining)`
  - 写入 `self.DT`
  - 推进 `self.current_sim_time`
  - `_sync_river_runtime(...)`
  - `Update_boundary_conditions()`
  - `Caculate_face_U_C_net()`
  - `Caculate_Roe_matrix_net()`
  - `Caculate_Source_term_net()`
  - `Caculate_Roe_flux_net()`
  - `Assemble_flux_net()` 或 implicit 分支
  - `Update_cell_property_net()`
  - 可选 `Save_step_result_net()`
  - 重新 `Caculate_global_CFL()`
- 返回值：
  - 实际使用的 `used_dt`

#### `advance_to(target_time, mode=None, time_eps=1e-12)`
- 被 `OneDNetworkAdapter.advance_to(...)` 调用，也能被网络自身直接使用。
- 逻辑是：
  - while `current_sim_time < target_time`
  - 用 `min(predict_cfl_dt(), remaining)` 子循环推进
  - 最后一小步精确裁剪到 `target_time`

#### `get_total_volume()`
- 被：
  - `OneDNetworkAdapter.get_total_volume()`
  - `CouplingManager.initialize()`
  - `CouplingManager.run()`
  调用。
- 作用：
  - 对 `self._river_edges` 中每条河道调用 `river.get_total_volume()` 并求和。

#### `snapshot()` / `restore()`
- 被：
  - `OneDNetworkAdapter.snapshot()`
  - `OneDNetworkAdapter.restore()`
  - `CouplingManager._run_picard_interval(...)`
  调用。
- 作用：
  - 为 Picard 小迭代保留 network-level rollback 能力。
- `snapshot()` 保存：
  - network scalars
  - boundary values
  - per-river snapshots
  - internal node caches / history
- `restore()` 会：
  - 还原 network scalars
  - 还原 boundary values
  - 对每条河道调用 `self.get_river(name).restore(...)`
  - 同步 runtime 状态

#### `get_river(name)`
- 被 `OneDNetworkAdapter.sample_*()` 与 `_materialize_lateral_sources()` 调用。
- 作用：
  - 让 adapter 可以通过 river name 访问具体支路对象，而不需要知道图结构内部细节。

### 3.3 河道级 coupling 生命周期方法
这些方法定义在 [fastest_exact_handoff/source/handoff_network_model_20260312/river_for_net.py](fastest_exact_handoff/source/handoff_network_model_20260312/river_for_net.py)。

#### `apply_cellwise_side_inflow(cell_ids, side_qs)`
- 被 `OneDNetworkAdapter._materialize_lateral_sources()` 调用。
- 逻辑：
  - 对每个真实单元 `cell_id`
  - 把 `side_q / cell_length` 累加到 `self.QIN[cell_id]`
- 这让 lateral coupling 能直接复用河道内部现有的侧向源项路径。

#### `get_total_volume()`
- 返回 `_compute_total_volume()`。
- 被 network-level `get_total_volume()` 聚合。

#### `snapshot()` / `restore()`
- 被 network-level `snapshot()` / `restore()` 级联调用。
- 保存/恢复：
  - 水位、深度、流量、面积、源项、边界面诊断等数组
  - `DT`、`current_sim_time`、`boundary_face_*` 等标量
  - diagnostics histories

### 3.4 为什么不需要重写 CouplingManager
- `CouplingManager` 只依赖 `OneDNetworkAdapter` 暴露的网络契约。
- `OneDNetworkAdapter` 只依赖 backend 是否提供：
  - `initialize_for_coupling`
  - `predict_cfl_dt`
  - `advance_one_step`
  - `advance_to`
  - `snapshot` / `restore`
  - `get_total_volume`
  - `get_river`
- fastest_exact backend 通过补齐这些方法，保持了 adapter 契约不变，因此 `CouplingManager`、scheduler、link 逻辑都无需改写。

## 4. 2D 侧实际调用路径

### 4.1 初始化顺序
定义在 [coupling/adapters_anuga_gpu.py](coupling/adapters_anuga_gpu.py)。

`TwoDAnugaGpuAdapter.initialize_gpu()` 的顺序是：
1. `configure_runtime_environment()`
2. `_patch_anuga_gpu_compile()`
3. `set_multiprocessor_mode(4)`（如果 domain 支持）
4. `domain.set_gpu_interface()`
5. `domain.gpu_interface.init_gpu_inlets(default_mode='fast')`
6. `_validate_existing_fast_mode()`
7. `domain.gpu_interface.init_gpu_boundary_conditions()`
8. `protect_against_infinitesimal_and_negative_heights_kernal(...)`

### 4.2 fast-mode-only 与 legacy 禁止点
- `default_inlet_mode = 'fast'`
- `register_exchange_region(..., mode=None)` 内部调用：
  - `require_fast_mode(...)`
  - `domain.gpu_inlets.add_inlet(..., mode='fast')`
- `advance_one_step(...)` 明确检查：
  - 必须存在新版 `gpu_inlets.add_inlet / apply`
  - 否则直接抛错：
    - “不能退回 legacy apply_inlets_gpu 路径”

### 4.3 每个 2D 子步的真实顺序
`TwoDAnugaGpuAdapter.advance_one_step(dt)` 的主路径是：
1. 若 `_prepared_dt is None`，先 `_prepare_gpu_step()`：
   - `refresh_boundary_values()`
     - `protect_against_infinitesimal_and_negative_heights_kernal`
     - `extrapolate_second_order_edge_sw_kernel`
     - `update_boundary_values_gpu`
   - `compute_fluxes_ext_central_kernel(... return_domain_timestep=True)`
   - 再做一次 `protect_against_infinitesimal_and_negative_heights_kernal`
2. `remaining_dt = min(requested_dt, predicted_dt)`
3. `set_gpu_update_timestep(...)`
4. `domain.relative_time += remaining_dt`
5. `compute_forcing_terms_manning_friction_flat(...)`
6. `domain.gpu_inlets.apply()`
7. `update_conserved_quantities_kernal(...)`
8. 触发 2D diagnostic callbacks

### 4.4 exchange 前后的 boundary / inlet 更新
- frontal coupling:
  - 通过 `register_dynamic_boundary(...)`
  - `activate_dynamic_boundary(...)`
  - `set_dynamic_boundary_state(...)`
- lateral coupling:
  - 通过 `register_exchange_region(...)`
  - `set_exchange_Q(link_id, discharge)`
  - `domain.gpu_inlets.apply()`

## 5. 计算原理

### 5.1 lateral coupling
- lateral link 定义在 [coupling/links.py](coupling/links.py) 的 `LateralWeirLink`。
- 当前实现是 broad-crested weir 型的体积交换：
  - 对每个 segment 计算 `deta = eta_1d - eta_2d`
  - `h_up = max(max(eta_1d, eta_2d) - crest, 0)`
  - `Q_seg = sign(deta) * Cd * L * sqrt(2g) * h_up^(3/2)`
  - 总流量 `Q = sum(Q_seg)`
- 在 `CouplingManager._apply_lateral_exchange(...)` 中：
  - 1D 侧对每个 river cell 施加 `-q_seg`
  - 2D 侧对 region 施加 `+Q`
- 这样保证：
  - 1D 与 2D 两边都真实加/扣体积
  - 不会出现“只给 1D 加水，不从 2D 扣水”的假交换

### 5.2 frontal / direct coupling
- frontal link 定义在 `FrontalBoundaryLink`。
- 当前实现不是直接拼接两个求解器，而是：
  - 1D 通过 `apply_stage_bc(...)` 接收 2D 给出的 stage
  - 2D 通过 `set_dynamic_boundary_state(...)` 接收 1D 给出的 discharge/stage 组合
- `CouplingManager._sample_frontal_guesses()` 会采样：
  - 2D boundary stage
  - 1D boundary discharge
  - 1D regime
- `_apply_frontal_guesses(...)` 根据 `sample_regime(...)` 结果分三类处理：
  - `sub`
  - `super_out`
  - 其他上游主导模式
- 非 strict 模式下，`_run_picard_interval(...)` 通过：
  - `snapshot()`
  - `restore()`
  - 欠松弛 `relax_guess(...)`
  实现小步 Picard 一致化。

### 5.3 scheduler 三种模式
- 实现在 [coupling/scheduler.py](coupling/scheduler.py)。
- `strict_global_min_dt`
  - `next_exchange_time = min(current + dt_1d, current + dt_2d, end)`
  - 每个微步都交换
- `yield_schedule`
  - `event_series = union(one_d_yields, two_d_yields, end)`
  - 两边各自推进到事件点后交换
- `fixed_interval`
  - `event_series = start + k * exchange_interval`
  - 两边在区间内按各自子步推进，到事件点再交换

### 5.4 为什么 boundary / exchange management 主导成本变化
- timing 分解由 `CouplingManager.get_timing_breakdown(...)` 给出。
- 当前计时桶包括：
  - `one_d_advance_time`
  - `two_d_gpu_kernel_time`
  - `boundary_update_time`
  - `gpu_inlets_apply_time`
  - `scheduler_manager_overhead`
- scheduler 越稀疏：
  - boundary re-activation / re-sampling 越少
  - frontal/lateral link 管理频次越低
  - GPU kernel 本身并不会按同样比例变快
- 因此 chapter 里的 cost reduction 首先反映为：
  - boundary update 和 exchange management 次数下降
  - 而不是单次 GPU kernel 突然更高效

### 5.5 snapshot / restore 的作用
- snapshot/restore 主要服务两个目标：
  1. frontal Picard 小迭代
  2. backend A/B 与 scheduler A/B 的可重复对比
- 在 `_run_picard_interval(...)` 中：
  - 先保存 1D 和 2D snapshot
  - 每轮迭代从同一个 interval 起点重新推进
  - 用 relaxed boundary guess 再算一遍
- 这保证比较的是“同一个 interval 上不同边界猜测”，而不是累积误差叠加后的不同轨迹。

## 6. legacy vs fastest_exact 的差异

### 6.1 变化点
- backend 选择点变了：
  - `experiments/one_d_backends.py:create_oned_network(...)`
- 1D 网络构造链变了：
  - `legacy` -> `demo.Rivernet.Rivernet`
  - `fastest_exact` -> `build_fastest_exact_network(...)`
- 1D 内部单步求解链变了：
  - `fastest_exact` 使用 handoff exact 的网络/河道内核与 accepted exact runtime toggles

### 6.2 不变点
- `CouplingManager` 不变
- `OneDNetworkAdapter` 主体不变
- `TwoDAnugaGpuAdapter` 不变
- scheduler / link / diagnostics / chapter metrics / plot 链路不变
- 所以 chapter A/B 本质上是：
  - 同一 coupling 框架
  - 同一 2D GPU fast path
  - 只替换 1D backend

### 6.3 当前 timing 数据能下什么结论
- `artifacts/chapter_coupling_analysis_fastest_exact/summaries/one_d_backend_timing.csv`
  给出的只是：
  - 同一 benchmark strict case
  - 1D-only
  - `legacy` vs `fastest_exact`
  的对照。
- 当前可下的 backend 层结论是：
  - 在这个 test-profile benchmark strict case 上，`fastest_exact` 1D-only wall-clock 比 `legacy` 更低。

### 6.4 目前不能下什么结论
- 不能把当前 test-profile 1D-only timing 夸大为：
  - 全 paper profile 普遍结论
  - 全耦合 chapter 的绝对性能定论
  - “fastest_exact 全面最优”的论文级性能结论
- 要下更强结论，仍需要：
  - paper profile
  - 更完整的 A/B benchmark/small suite
  - 与当前 chapter 成本分解一起看

## 7. 与已有审计文档的关系

### 7.1 一致性检查结果
- [docs/fastest_exact_call_chain_audit.md](docs/fastest_exact_call_chain_audit.md) 与当前真实代码主干是一致的。
- 它没有与当前代码冲突的地方，但粒度更高，省略了：
  - `run_single_case` 子进程层
  - `run_chapter_case` 的 diagnostics / artifact writers
  - 2D adapter 的具体 GPU 调用顺序
  - `run_fastest_exact_refresh` 的 case 选择与 A/B timing 输出

### 7.2 当前处理方式
- 本轮没有改写旧 audit 的核心结论。
- 新文档的作用是：
  - 把旧 audit 中的高层描述，补成可直接引用到论文方法章节或技术附录的真实调用链说明。
