# 1D–2D 耦合时间离散、空间耦合与计算成本占比分析

## 研究问题
- 本章关注的是模型内部比较，而不是实测验证。
- 核心问题有三类：
  - exchange 时间离散如何影响 early arrival、peak/phase 与回流阶段误差；
  - frontal / lateral / mixed 接口指标如何解释误差来源；
  - 成本节省主要来自哪里，是 1D、2D kernel，还是 boundary/exchange 管理。

## 算例分工
- 大算例：
  - `official_test7_overtopping_only_variant` 或 `surrogate_test7_overtopping_only_variant`
  - 角色：提供接近论文主场景的全域、Floodplain 1/2/3、代表断面、代表 link 与代表 2D 子域比较。
- 小算例：
  - `frontal_basin_fill`
  - `lateral_overtopping_return`
  - `early_arrival_pulse`
  - `regime_switch_backwater_or_mixed`
  - 角色：把 frontal、lateral、首次 exchange 前冻结、回水/流态切换等机理拆开分析。

## 为什么只做 overtopping-only Test 7 variant
- 当前仓库的耦合框架重点是 1D 河道–2D 洪泛区紧耦合。
- culvert / other pathways 不在本轮实现范围内。
- 因此本章采用 scope-restricted Test 7 variant：
  - 保留 overtopping 主路径；
  - 去除设施路径；
  - 文档中明确区分 official variant 与 surrogate variant。

## 为什么不讨论绝对耗时优劣
- 当前 1D 河网实现不是最终优化版。
- 因此本章只讨论：
  - 各模块成本占比；
  - 相对成本指数 `T_case / T_strict`；
  - 不同 scheduler / interval 下成本从哪里省出来。

## 参考解策略
- 大算例：
  - `strict_global_min_dt + finest practical mesh`
- 小算例：
  - 默认 `strict_global_min_dt`
  - 如需要更细 reference，则只通过更细 mesh / 更细 exchange 完成，不引入新的求解器。

## 输出指标
- 1D：
  - stage / discharge RMSE
  - peak stage / discharge error
  - peak time error
  - arrival time error
  - phase lag
  - hydrograph NSE
- 2D：
  - max depth map difference
  - arrival time map difference
  - inundated area difference
  - wet-area IoU / CSI
- 接口级：
  - `Q_ex(t)`
  - `Δη(t)`
  - `V_ex(t)`
  - sign-flip count
  - link-wise mass closure error
  - exchange event count
  - first-exchange offset
- 成本级：
  - total / normalized mass error
  - 1D advance share
  - 2D GPU kernel share
  - boundary update share
  - exchange manager share
  - misc / io share

## 主要图表与表格
- 几何/示意：
  - coupling schematic
  - Test 7 geometry and mesh
  - scheduler timeline schematic
- 过程图：
  - 1D stage/discharge hydrographs
  - x–t river stage/discharge
- 接口诊断：
  - exchange Q / Δη / cumulative volume
  - exchange event alignment
- 2D 图组：
  - snapshots
  - max-depth map
  - arrival-time map
  - difference map
  - flood-front overlay
- interval / 成本：
  - RMSE / arrival / phase / normalized-axis plots
  - cost-share stacked
  - relative-cost-vs-accuracy
  - floodplain partition compare

## 当前实现约束
- 2D 侧只允许新版 GPU fast mode。
- coupling 主路径中不允许 legacy `apply_inlets_gpu()`。
- 默认测试不允许 skip-based 逃避。
- 所有图脚本都必须独立可重跑。
- 当前 chapter 新的 A/B 结果目录为：
  - `artifacts/chapter_coupling_analysis_fastest_exact/`
  - 该目录保留原 chapter 结果不变，同时用 `fastest_exact` 作为默认 1D backend 复跑选定 benchmark / small cases。

## 2D 论文图渲染与空白图修复
- 本章所有 2D 区域图现在统一采用：
  - 全网格面着色；
  - 细灰色网格线叠加；
  - equal aspect；
  - 多 panel 对比时共享色标范围；
  - difference map 使用对称色标；
  - NaN / no-data 采用浅灰色而不是纯白。
- 受影响的图包括：
  - `2d_snapshots_depth`
  - `2d_snapshots_velocity`
  - `2d_max_depth_map`
  - `2d_arrival_time_map`
  - `2d_difference_map`
  - `flood_front_overlay`
  - `test7_geometry_and_mesh`
- 这轮修复前，chapter 结果中的“近似空白图”主要来自两类原因：
  - 2D 主图使用 centroid scatter / wet-point overlay，视觉上只占据很少像素；
  - 某些标量场近乎常数，例如当前 surrogate benchmark 的 arrival time map 全域均为 `0.0 s`，导致旧图在稀疏散点和默认色标下近似单色。
- 修复后，plotting 主路径变为 mesh-based renderer：
  - cell scalar 使用 face-colored `PolyCollection`；
  - 如有 vertex scalar，可转为 triangulation-based 渲染；
  - flood front 采用 mesh 背景 + 前沿边界叠置，而不是点云。
- 同时新增 blank-image QA：
  - chapter plots 会输出 `blank_plot_audit.csv/json`；
  - plotting 脚本在数据为空或缺列时 fail-fast，不再静默生成白图。

## Geometry Cache 与可重复性
- chapter 2D 图现在不再依赖运行时读取未跟踪的 `.msh` 文件。
- 每个需要 2D 渲染的 case 会导出一个轻量 `plot_cache`：
  - `mesh_geometry.npz`
  - `mesh_geometry.json`
- cache 中至少保存：
  - vertices
  - triangles
  - bounds
  - centroids
  - segments / neighbors 等绘图所需网格信息
- 绘图时的几何读取优先级固定为：
  - `plot_cache`
  - 若本地仍有 `.msh`，可一次性导出 cache
  - cache 与 `.msh` 同时缺失时直接报错
- 因此，论文图的再生成现在依赖：
  - `cases/<case_name>/plot_cache/`
  - `two_d_snapshots.csv`
  - `two_d_field_summary.csv`
  - 以及现有 summary / manifest 文件

## 结果解读位置
- 定量 summary 表位于：
  - `artifacts/chapter_coupling_analysis/summaries/summary_table.csv`
  - `artifacts/chapter_coupling_analysis/summaries/summary_table_small_cases.csv`
  - `artifacts/chapter_coupling_analysis/summaries/summary_table_test7_partitions.csv`
  - `artifacts/chapter_coupling_analysis/summaries/timing_breakdown.csv`
  - `artifacts/chapter_coupling_analysis/summaries/exchange_link_summary.csv`
- `fastest_exact` A/B 结果对应位于：
  - `artifacts/chapter_coupling_analysis_fastest_exact/summaries/summary_table.csv`
  - `artifacts/chapter_coupling_analysis_fastest_exact/summaries/timing_breakdown.csv`
  - `artifacts/chapter_coupling_analysis_fastest_exact/summaries/one_d_backend_timing.csv`
- 这些结果会在实验完成后支撑以下结论：
  - 哪些 interval 对 early arrival 最敏感；
  - 哪些 interval 在 peak / phase 上开始明显失真；
  - strict / yield / fixed interval 的差异；
  - interface 指标如何解释误差来源；
  - Floodplain 1/2/3 的差异；
  - 成本占比变化的来源。

## 当前运行所使用的 benchmark 变体
- 当前仓库产物使用的是：
  - `surrogate_test7_overtopping_only_variant`
- 原因见：
  - `artifacts/chapter_coupling_analysis/logs/test7_provenance.json`
- 当前 provenance 记录为：
  - 未找到官方缓存；
  - 本轮运行禁用了下载；
  - 因此自动切换到 documented surrogate，而不是静默跳过 benchmark。

## 大算例主要结果
- 在 surrogate Test 7 overtopping-only benchmark 中，`strict_global_min_dt` 仍是主参考解。
- `yield_schedule` 的相对成本约为 `0.54`，但 1D stage RMSE 已升到 `0.255 m`，phase lag 约 `-34 s`，说明 yield event 过稀时会把 later-stage correction 明显推前。
- `fixed_interval=2 s` 几乎贴合参考解：
  - stage RMSE `0.00469 m`
  - phase lag `-0.5 s`
  - hydrograph NSE `0.9996`
  - 但相对成本约 `1.41`，并不比 strict 更省。
- `fixed_interval=3–5 s` 是当前 benchmark family 中更合理的折中区间：
  - `3 s` RMSE `0.00813 m`，relative cost `1.02`
  - `5 s` RMSE `0.01723 m`，relative cost `0.88`
- 从 `10 s` 开始，later-stage 误差已明显上升：
  - `10 s` RMSE `0.07035 m`
  - `15 s` RMSE `0.14722 m`，phase lag `-40.5 s`
  - `30 s` RMSE `0.41379 m`
  - `60 s` RMSE `0.66172 m`
  - `300 s` RMSE `0.92320 m`
- 对当前 benchmark 的主 1D 控制量而言，arrival-time error 基本为零，这说明该 case 的关键到达发生在首次 exchange 之前，benchmark 上的主要误差来源不是首到达，而是峰值和后段相位修正。

## 小算例规则化结论
- `early_arrival_pulse` 给出了最清晰的时间离散阈值结论。
- 当 `Δt_ex / t_arr_ref` 仍处于 `0.25–0.64` 量级时：
  - `2 s` arrival error 约 `-0.225 s`
  - `5 s` arrival error 约 `+0.134 s`
  - 误差仍可控。
- 当 `Δt_ex / t_arr_ref` 提高到约 `1.91`，且 `Δt_ex / t_rise_ref` 提高到约 `3.60` 时，arrival error 开始锁死：
  - `15 s` arrival error `0.969 s`
  - `60 s` 与 `300 s` 仍保持同样的 `0.969 s`
- 这说明在 early-arrival 场景里，一旦 exchange interval 超过参考到达时间量级，后续继续放大 interval 不再改变首到达误差，而是只会继续牺牲后续阶段的精度或成本结构。
- `frontal_basin_fill` 的鲁棒性最高。即使 `Δt_ex / t_arr_ref` 很大，1D stage RMSE 仍在 `7e-4 m` 量级，说明近单调的 frontal fill 对 coarse exchange 更不敏感。
- `lateral_overtopping_return` 对 coarse interval 更敏感，但主要体现在 later-stage stage RMSE：
  - `60 s` RMSE `0.0615 m`
  - `300 s` RMSE `0.0794 m`
- `regime_switch_backwater_or_mixed` 在 `2–15 s` 范围内仍较稳，但到 `60–300 s` 时 RMSE 已升到 `0.007–0.010 m`，说明 mixed/backwater 场景对 coarse interval 的容忍度低于单调 frontal fill。

## 接口与成本占比解释
- 当前 benchmark 的主要成本节省不是来自 GPU kernel 本身，而是来自 boundary/exchange 管理频次下降。
- 在 benchmark strict case 中：
  - 1D advance share `0.242`
  - 2D GPU kernel share `0.115`
  - boundary share `0.208`
  - exchange manager share `0.436`
- `yield_schedule` 和大 interval fixed cases 都显著压低了 exchange/boundary 触发次数，因此 relative cost 下降，但代价是 phase/hydrograph 误差快速放大。
- 这与接口级诊断是一致的：
  - 当 exchange event 稀疏化后，`Q_ex(t)` 和 `Δη(t)` 的修正被推迟到更粗的 bucket 中；
  - benchmark 上由此首先表现为 later-stage hydrograph 失真，而不是首到达偏移。

## Floodplain 分区与 mesh 敏感性
- Floodplain 1/2/3 的 partition summary 已写入：
  - `artifacts/chapter_coupling_analysis/summaries/summary_table_test7_partitions.csv`
- 当前 surrogate benchmark 中，partition arrival map difference 基本保持为零，进一步说明该 case 的主差异集中在水位过程与接口交换，而不是洪泛区首次到达。
- mesh sensitivity 表明“朝向”本身不是主要误差源，“corridor refinement 设计”更关键。
- 以 `aligned_mesh_fine` 为参考：
  - `aligned_mesh_coarse` RMSE `4.67e-4 m`
  - `rotated_mesh_fine` RMSE `4.12e-4 m`
  - `rotated_mesh_coarse` RMSE `4.81e-4 m`
  - 都只表现出很小的差异。
- 真正的 outlier 是 `narrow_corridor_refine`：
  - triangle count `465`
  - wall clock `40.63 s`
  - RMSE `0.00707 m`
  - peak time error `11 s`
- 这说明对当前 river-aware mesh builder 而言，corridor 宽度与局部 refinement density 比整体旋转更能改变交换带数值响应与成本。

## 本章建议结论
- 对当前 overtopping-only Test 7 family，推荐的 fixed interval 区间是：
  - `3–5 s`
- 若目标更偏向严格贴合参考解，可用 `2 s`，但当前实现下它的 relative cost 甚至高于 strict。
- 对 early-arrival 主导的场景，不建议让 `Δt_ex / t_arr_ref` 超过 `1`；一旦接近或超过 `2`，arrival error 会开始锁死。
- 对 mixed/backwater 或 later-stage correction 主导的场景，不建议使用 `15 s` 及以上的 exchange interval。
- 对当前 benchmark family，主要成本节省来自：
  - boundary updates 减少；
  - exchange manager 调度减少；
  - 而不是 GPU kernel 本身突然更快。

## Fastest-Exact Backend A/B
- 当前仓库已新增 `fastest_exact_handoff` 作为 chapter/coupling 默认 1D backend。
- 在 `artifacts/chapter_coupling_analysis_fastest_exact/summaries/one_d_backend_timing.csv` 中，
  同一 benchmark strict case 的 1D-only 对比结果显示：
  - `legacy` wall clock 约 `0.166 s`
  - `fastest_exact` wall clock 约 `0.136 s`
  - `fastest_exact / legacy ≈ 0.819`
- 因此，本轮切换至少在当前 test-profile benchmark strict case 上，已经把 1D-only 网络推进时间压低到 legacy 的约 `82%`，同时保持现有 coupling/plotting 工作流不变。
